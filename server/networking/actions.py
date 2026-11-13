"""
Game actions shared by human players (socket events) and bots.

Every action validates turn and phase, changes the game state, tells the
table, and then hands over to `after_action`, which notifies the next seat
and wakes a bot if that seat is played by one.
"""

import asyncio
from typing import Any, Awaitable, Callable, List, Optional

import structlog

from bots.decision import Decision, fallback_decision
from game_logic.bidding import BiddingManager
from game_logic.final_scoring import calculate_final_score
from models.announcement import Announcement, AnnouncementType
from models.bid import BidType
from models.game_state import GamePhase, TAROKK_DECLARATIONS, settle_tarokk_declarations
from models.player import Player
from networking.protocol import Message, MessageType
from networking.reports import log_decision
from networking.room_manager import Room, RoomManager
from validation.rules import can_announce, get_legal_cards, get_valid_announcements, validate_discard

logger = structlog.get_logger()

# Phases in which one seat has to act
TURN_PHASES = (
    GamePhase.BIDDING,
    GamePhase.DISCARDING,
    GamePhase.PARTNER_CALL,
    GamePhase.ANNOUNCEMENTS,
    GamePhase.PLAYING,
)

Emit = Callable[..., Awaitable[Any]]
DecideFn = Callable[[Any, int], Decision]


class GameService:
    """Runs the game for all rooms. `emit` has the signature of `sio.emit`."""

    def __init__(
        self,
        room_manager: RoomManager,
        emit: Emit,
        save: Optional[Callable[[Room], Awaitable[None]]] = None,
        decide: Optional[DecideFn] = None,
    ):
        self.room_manager = room_manager
        self.emit = emit
        self.save = save
        self.decide: DecideFn = decide or fallback_decision
        # Hints are computed with this when set (see bots.strategy)
        self.hint: Optional[DecideFn] = None
        # Pauses (seconds); tests set these to 0
        self.redeal_pause = 2.0
        self.trick_pause = 2.5
        # When False, bots are not started automatically (tests drive them)
        self.auto_bots = True

    # ------------------------------------------------------------ broadcasting

    async def broadcast_room_state(self, room: Room) -> None:
        await self.emit("room_state", room.get_room_info(), room=room.room_id)

    async def broadcast_game_state(self, room: Room) -> None:
        """Send each connected player their own view of the game."""
        for player in room.game_state.players:
            session_id = room.player_sessions.get(player.id)
            if session_id:
                await self.emit("game_state", room.game_state.to_dict(player_id=player.id), room=session_id)

    async def broadcast(self, room: Room, msg_type: MessageType, data: dict) -> None:
        message = Message.create(msg_type, **data)
        await self.emit(msg_type.value, message.to_dict(), room=room.room_id)

    async def announce_connection(self, room: Room, player: Player, connected: bool) -> None:
        """Tell the table that a player dropped out or is back."""
        await self.emit("player_connection", {
            "player_position": player.position,
            "player_name": player.name,
            "connected": connected,
            "bot_controlled": player.bot_controlled,
        }, room=room.room_id)

    # ------------------------------------------------------------------ turns

    @staticmethod
    def turn_position(room: Room) -> Optional[int]:
        """Seat that has to act now, or None."""
        if room.game_state.phase in TURN_PHASES:
            return room.game_state.current_turn
        return None

    def your_turn_payload(self, room: Room, player: Player) -> dict:
        game_state = room.game_state
        data: dict = {"valid_actions": []}

        if game_state.phase == GamePhase.BIDDING:
            data["valid_actions"] = ["place_bid"]
            data["valid_bids"] = [b.value for b in BiddingManager.get_valid_bid_types(player, game_state.bid_history)]
            data["invit_bids"] = BiddingManager.invit_bids(player, game_state.bid_history)
        elif game_state.phase == GamePhase.DISCARDING:
            data["valid_actions"] = ["discard_cards"]
            data["discard_count"] = player.get_hand_size() - 9
        elif game_state.phase == GamePhase.PARTNER_CALL:
            data["valid_actions"] = ["call_partner"]
        elif game_state.phase == GamePhase.ANNOUNCEMENTS:
            data["valid_actions"] = ["make_announcement", "pass_announcement"]
            data["valid_announcements"] = [a.value for a in self.valid_announcements(room, player)]
            declaration = room.game_state.tarokk_declaration_open(player.position)
            if declaration:
                data["valid_announcements"].append(declaration)
            if game_state.owes_pagat_ulti(player.position):
                data["must_announce"] = ["pagat_ultimo"]
        elif game_state.phase == GamePhase.PLAYING:
            data["valid_actions"] = ["play_card"]
            data["valid_cards"] = [c.id for c in self.legal_cards(room, player)]

        if self.hint is not None and not player.bot_controlled:
            try:
                data["hint"] = self.hint(game_state, player.position).to_dict()
            except Exception as e:  # a missing hint must never block the game
                logger.error("hint_error", error=str(e), room_id=room.room_id)
        return data

    @staticmethod
    def legal_cards(room: Room, player: Player):
        game_state = room.game_state
        is_first = len(game_state.current_trick) == 0
        lead_suit = None if is_first else game_state.current_trick[0][1].suit
        return get_legal_cards(player.hand, lead_suit, is_first)

    @staticmethod
    def valid_announcements(room: Room, player: Player) -> List[AnnouncementType]:
        """Announcements this player may still make (nothing is announced twice)."""
        already = {a.announcement_type for a in room.game_state.announcements}
        return [a for a in get_valid_announcements(player.hand) if a not in already]

    async def send_your_turn(self, room: Room, only_session: Optional[str] = None) -> None:
        """Notify the seat to move (if a person plays it)."""
        position = self.turn_position(room)
        if position is None:
            return
        player = room.game_state.get_player(position)
        if not player or player.bot_controlled:
            return
        session_id = room.player_sessions.get(player.id)
        if not session_id or (only_session and only_session != session_id):
            return
        await self.emit("your_turn", self.your_turn_payload(room, player), room=session_id)

    async def after_action(self, room: Room) -> None:
        """Common tail of every action."""
        room.turn_seq += 1
        game_state = room.game_state

        if game_state.apply_obligatory_contra_if_due():
            # The player who discarded the called card must kontra the game
            await self.broadcast(room, MessageType.CONTRA_MADE, {
                "player_position": game_state.current_turn,
                "announcement_type": "game",
                "obligatory": True,
            })

        await self.broadcast_game_state(room)
        await self.send_your_turn(room)
        if self.save:
            await self.save(room)
        self.schedule_bot(room)

    # ------------------------------------------------------------------- bots

    def schedule_bot(self, room: Room) -> None:
        """If a bot plays the seat to move, let it act after the table's delay."""
        if not self.auto_bots:
            return
        position = self.turn_position(room)
        if position is None:
            return
        player = room.game_state.get_player(position)
        if not player or not player.bot_controlled:
            return
        delay = room.bot_delay()
        game_state = room.game_state
        if (game_state.phase == GamePhase.PLAYING and not game_state.current_trick
                and game_state.trick_number > 1):
            delay += self.trick_pause  # let people see the finished trick
        asyncio.create_task(self._bot_move_later(room, room.turn_seq, delay))

    async def _bot_move_later(self, room: Room, seq: int, delay: float) -> None:
        await asyncio.sleep(delay)
        if self.room_manager.rooms.get(room.room_id) is not room or room.turn_seq != seq:
            return  # something else happened in the meantime
        try:
            await self.bot_move(room)
        except Exception as e:
            logger.error("bot_move_error", room_id=room.room_id, error=str(e))

    async def bot_move(self, room: Room) -> bool:
        """
        Let the bot on the seat to move act once.

        Returns:
            True if a bot acted
        """
        position = self.turn_position(room)
        if position is None:
            return False
        player = room.game_state.get_player(position)
        if not player or not player.bot_controlled:
            return False
        try:
            decision = self.decide(room.game_state, position)
            log_decision(room, position, decision)
            await self.apply_decision(room, player, decision)
        except Exception as e:
            # The strategy must never stall the table: fall back to any legal move
            logger.error("bot_decision_failed", room_id=room.room_id, position=position, error=str(e))
            decision = fallback_decision(room.game_state, position)
            log_decision(room, position, decision, fallback=True)
            await self.apply_decision(room, player, decision)
        return True

    async def drive_bots(self, room: Room, max_actions: int = 500) -> int:
        """Run bot moves back to back until a person has to act (tests, no delay)."""
        done = 0
        while done < max_actions and await self.bot_move(room):
            done += 1
        return done

    async def apply_decision(self, room: Room, player: Player, decision: Decision) -> None:
        payload = decision.payload
        if decision.action == "bid":
            await self.act_bid(room, player, BidType(payload["bid_type"]))
        elif decision.action == "discard":
            await self.act_discard(room, player, payload["card_ids"])
        elif decision.action == "call_partner":
            await self.act_call_partner(room, player, payload["tarokk_rank"])
        elif decision.action == "announce":
            await self.act_announce(room, player, payload["announcement_types"])
        elif decision.action == "pass_announcement":
            await self.act_pass_announcement(room, player)
        elif decision.action == "contra":
            await self.act_contra(room, player, payload["announcement_type"])
        elif decision.action == "play_card":
            await self.act_play_card(room, player, payload["card_id"])
        else:
            raise ValueError(f"Unknown action {decision.action}")

    # ------------------------------------------------------------ game start

    async def start_game(self, room: Room) -> None:
        """Deal the first hand."""
        logger.info("starting_game", room_id=room.room_id)
        await self._deal(room)

    async def start_next_hand(self, room: Room) -> None:
        """Deal the next hand at the same table; the dealer moves on one seat."""
        logger.info("starting_next_hand", room_id=room.room_id)
        room.game_state.reset_for_next_hand()
        room.last_game_over = None
        await self._deal(room)

    async def _deal(self, room: Room) -> None:
        game_state = room.game_state
        if [p.position for p in game_state.players] != [0, 1, 2, 3] or any(p.vacant for p in game_state.players):
            raise ValueError("Need four players to deal")
        room.decision_log.clear()
        game_state.start_dealing()
        game_state.start_bidding()
        await self.broadcast_room_state(room)
        await self.broadcast(room, MessageType.GAME_STARTED, {
            "hand_number": game_state.hand_number,
            "dealer_position": game_state.dealer_position,
        })
        await self.after_action(room)

    async def maybe_start(self, room: Room) -> None:
        """Start the first or the next hand if everyone needed is ready."""
        if room.can_start_game():
            await self.start_game(room)
        elif room.can_start_next_hand():
            await self.start_next_hand(room)

    # ---------------------------------------------------------------- actions

    @staticmethod
    def _require_turn(room: Room, player: Player, phase: GamePhase) -> None:
        if room.game_state.phase != phase:
            raise ValueError(f"Not in {phase.value} phase")
        if room.game_state.current_turn != player.position:
            raise ValueError("Not your turn")

    async def act_bid(self, room: Room, player: Player, bid_type: BidType) -> None:
        game_state = room.game_state
        self._require_turn(room, player, GamePhase.BIDDING)

        can_bid, error = BiddingManager.can_player_bid(player, bid_type, game_state.bid_history)
        if not can_bid:
            raise ValueError(error)

        game_state.place_bid(player.position, bid_type)
        await self.broadcast(room, MessageType.BID_PLACED, {
            "player_position": player.position,
            "bid_type": bid_type.value,
        })

        if game_state.is_bidding_complete():
            game_state.end_bidding()
            if game_state.winning_bid:
                await self._distribute_talon(room)
            else:
                # All passed: throw the hand in, the same dealer deals again
                logger.info("all_players_passed", room_id=room.room_id)
                await self.emit("game_state", {"message": "All players passed. Dealing new hand...",
                                               "code": "ALL_PASSED"}, room=room.room_id)
                await asyncio.sleep(self.redeal_pause)
                game_state.start_dealing()
                game_state.start_bidding()

        await self.after_action(room)

    async def _distribute_talon(self, room: Room) -> None:
        game_state = room.game_state
        distribution = game_state.distribute_talon()
        for p in game_state.players:
            received = distribution.get(p.position, [])
            p.talon_card_ids = [c.id for c in received]
            session_id = room.player_sessions.get(p.id)
            if session_id:
                await self.emit("talon_distributed", {
                    "you_received": len(received),
                    "your_hand_size": p.get_hand_size(),
                    "card_ids": p.talon_card_ids,
                }, room=session_id)
        game_state.start_discard_phase()

    async def act_discard(self, room: Room, player: Player, card_ids: List[str]) -> None:
        game_state = room.game_state
        self._require_turn(room, player, GamePhase.DISCARDING)

        num_to_discard = player.get_hand_size() - 9
        if len(card_ids) != num_to_discard or len(set(card_ids)) != len(card_ids):
            raise ValueError(f"Must discard exactly {num_to_discard} cards")

        cards_to_discard = [c for c in player.hand if c.id in card_ids]
        if len(cards_to_discard) != len(card_ids):
            raise ValueError("Card not in hand")
        is_valid, error = validate_discard(cards_to_discard)
        if not is_valid:
            raise ValueError(error)
        invit = game_state.invit()
        if invit and invit["by"] == player.position and any(
            c.is_tarokk() and c.rank == invit["card"] for c in cards_to_discard
        ):
            raise ValueError(f"The {invit['card']} you invited with cannot go into the skart")

        discarded = player.discard_cards(card_ids)
        game_state.players_who_discarded.append(player.position)

        await self.broadcast(room, MessageType.PLAYER_DISCARDED, {
            "player_position": player.position,
            "num_cards": len(discarded),
            "tarokks_discarded": sum(1 for c in discarded if c.is_tarokk()),
        })

        if game_state.can_end_discard_phase():
            game_state.phase = GamePhase.PARTNER_CALL
            game_state.current_turn = game_state.declarer_position
        else:
            game_state.current_turn = game_state.next_position(game_state.current_turn)

        await self.after_action(room)

    async def act_call_partner(self, room: Room, player: Player, tarokk_rank: str) -> None:
        game_state = room.game_state
        if game_state.phase != GamePhase.PARTNER_CALL:
            raise ValueError("Not in partner call phase")
        if player.position != game_state.declarer_position:
            raise ValueError("Only declarer can call partner")
        if not tarokk_rank:
            raise ValueError("Must specify tarokk rank")
        required = game_state.required_call()
        if required and tarokk_rank != required:
            raise ValueError(f"The bidding obliges you to call the {required}")

        game_state.call_partner(tarokk_rank)
        await self.broadcast(room, MessageType.PARTNER_CALLED, {"called_card": tarokk_rank})

        game_state.start_announcement_phase()
        await self.after_action(room)

    async def _finish_announcement_turn(self, room: Room) -> None:
        game_state = room.game_state
        if game_state.is_announcement_phase_complete():
            await self.broadcast(room, MessageType.ANNOUNCEMENTS_COMPLETE, {})
            game_state.start_playing()
            await self.broadcast(room, MessageType.TRICK_STARTED, {
                "trick_number": 1,
                "leader": game_state.trick_leader,
            })
        await self.after_action(room)

    async def act_announce(self, room: Room, player: Player, announcement_types: List[str],
                           announced: bool = True) -> None:
        game_state = room.game_state
        self._require_turn(room, player, GamePhase.ANNOUNCEMENTS)
        if not announcement_types:
            raise ValueError("Must specify announcement type(s)")
        if game_state.owes_pagat_ulti(player.position) and "pagat_ultimo" not in announcement_types:
            raise ValueError("You invited with the pagát: you must announce pagát ulti now")

        declarations = [t for t in announcement_types if t in TAROKK_DECLARATIONS]
        announcement_types = [t for t in announcement_types if t not in TAROKK_DECLARATIONS]
        if len(declarations) > 1 or (declarations
                                     and game_state.tarokk_declaration_open(player.position) != declarations[0]):
            raise ValueError("You can only declare eight or nine tarokks if you hold exactly that many")

        already = {a.announcement_type for a in game_state.announcements}
        made = []
        for type_str in announcement_types:
            announcement_type = AnnouncementType(type_str)
            is_valid, error = can_announce(player.hand, announcement_type)
            if not is_valid:
                raise ValueError(f"{type_str}: {error}")
            if announcement_type in already or any(m.announcement_type == announcement_type for m in made):
                raise ValueError(f"{type_str}: already announced")
            made.append(Announcement(
                player_position=player.position,
                announcement_type=announcement_type,
                announced=announced,
            ))

        for kind in declarations:
            game_state.declare_tarokks(player.position, kind)
        game_state.make_announcements(player.position, made)
        for kind in declarations:
            await self.broadcast(room, MessageType.ANNOUNCEMENT_MADE, {
                "player_position": player.position,
                "announcement_type": kind,
                "announced": True,
            })
        for announcement in made:
            await self.broadcast(room, MessageType.ANNOUNCEMENT_MADE, {
                "player_position": player.position,
                "announcement_type": announcement.announcement_type.value,
                "announced": announced,
            })
        await self._finish_announcement_turn(room)

    async def act_pass_announcement(self, room: Room, player: Player) -> None:
        self._require_turn(room, player, GamePhase.ANNOUNCEMENTS)
        if room.game_state.owes_pagat_ulti(player.position):
            raise ValueError("You invited with the pagát: you must announce pagát ulti now")
        room.game_state.player_pass_announcement(player.position)
        await self.broadcast(room, MessageType.PASS_ANNOUNCEMENT, {"player_position": player.position})
        await self._finish_announcement_turn(room)

    def _find_announcement(self, room: Room, type_str: str) -> Announcement:
        if not type_str:
            raise ValueError("Must specify announcement type")
        announcement = next(
            (a for a in room.game_state.announcements if a.announcement_type.value == type_str), None
        )
        if not announcement:
            raise ValueError(f"No announcement of type {type_str} found")
        return announcement

    @staticmethod
    def _same_side(room: Room, a: int, b: int) -> bool:
        game_state = room.game_state
        declarer_side = {game_state.declarer_position, game_state.partner_position}
        return (a in declarer_side) == (b in declarer_side)

    async def act_contra(self, room: Room, player: Player, type_str: str) -> None:
        self._require_turn(room, player, GamePhase.ANNOUNCEMENTS)
        if room.game_state.owes_pagat_ulti(player.position):
            raise ValueError("You invited with the pagát: you must announce pagát ulti now")
        announcement = self._find_announcement(room, type_str)
        if announcement.contra:
            raise ValueError("This announcement has already been contra'd")
        if self._same_side(room, player.position, announcement.player_position):
            raise ValueError("Can only contra opponent announcements")

        announcement.contra = True
        announcement.contra_by = player.position
        room.game_state.record_contra_turn(player.position)
        await self.broadcast(room, MessageType.CONTRA_MADE, {
            "player_position": player.position,
            "announcement_type": type_str,
        })
        await self._finish_announcement_turn(room)

    async def act_recontra(self, room: Room, player: Player, type_str: str) -> None:
        self._require_turn(room, player, GamePhase.ANNOUNCEMENTS)
        announcement = self._find_announcement(room, type_str)
        if not announcement.contra:
            raise ValueError("Can only recontra a contra'd announcement")
        if announcement.recontra:
            raise ValueError("This announcement has already been recontra'd")
        if not self._same_side(room, player.position, announcement.player_position):
            raise ValueError("Can only recontra your own team's announcements")

        announcement.recontra = True
        announcement.recontra_by = player.position
        room.game_state.record_contra_turn(player.position)
        await self.broadcast(room, MessageType.RECONTRA_MADE, {
            "player_position": player.position,
            "announcement_type": type_str,
        })
        await self._finish_announcement_turn(room)

    async def act_play_card(self, room: Room, player: Player, card_id: str) -> None:
        game_state = room.game_state
        self._require_turn(room, player, GamePhase.PLAYING)
        if not card_id:
            raise ValueError("Must specify card_id")

        card = next((c for c in player.hand if c.id == card_id), None)
        if not card:
            raise ValueError("Card not in hand")
        if card not in self.legal_cards(room, player):
            raise ValueError("Illegal card play - must follow suit or play tarokk if void")

        was_revealed = game_state.partner_revealed
        played_card = game_state.play_card_to_trick(player.position, card_id)

        await self.broadcast(room, MessageType.CARD_PLAYED, {
            "player_position": player.position,
            "card": played_card.to_dict(),
        })

        if game_state.partner_revealed and not was_revealed:
            await self.broadcast(room, MessageType.PARTNER_REVEALED, {
                "partner_position": game_state.partner_position,
            })

        if len(game_state.current_trick) == 0:
            # Trick was completed and cleared
            winner = game_state.previous_trick_winner
            last_trick = game_state.trick_history[-1]
            await self.broadcast(room, MessageType.TRICK_COMPLETE, {
                "winner": winner,
                "winner_name": game_state.players[winner].name,
                "trick_number": game_state.trick_number - 1,
                "cards": last_trick["cards"],
            })
            if game_state.phase == GamePhase.SCORING:
                await self._game_over(room)

        await self.after_action(room)

    async def _game_over(self, room: Room) -> None:
        """Score the hand, add it to the running totals and tell the table."""
        game_state = room.game_state

        if not game_state.partner_revealed and game_state.partner_position is not None:
            game_state.partner_revealed = True
            game_state.players[game_state.partner_position].partner_revealed = True

        result = calculate_final_score(
            players=game_state.players,
            declarer_position=game_state.declarer_position,
            partner_position=game_state.partner_position,
            winning_bid=game_state.winning_bid,
            announcements=game_state.announcements,
            trick_history=game_state.trick_history,
            game_contra=game_state.game_contra,
        )

        tarokk_lines = settle_tarokk_declarations(game_state.tarokk_declarations, result["player_scores"])

        # Every hand starts each player at 50; the change goes onto the running total
        for position, score in result["player_scores"].items():
            game_state.players[position].total_score += score - 50
        for p in game_state.players:
            p.ready_next = False

        payload = {
            "declarer": game_state.declarer_position,
            "partner": game_state.partner_position,
            "declarer_alone": game_state.declarer_alone,
            "declarer_team_points": result["declarer_team_points"],
            "opponent_team_points": result["opponent_team_points"],
            "winner": result["winner"],
            "base_game_value": result["base_game_value"],
            "game_multiplier": result["game_multiplier"],
            "final_game_value": result["final_game_value"],
            "game_contra": result["game_contra"],
            "player_scores": result["player_scores"],
            "total_scores": [p.total_score for p in game_state.players],
            "hand_number": game_state.hand_number,
            "achieved_announcements": result["achieved_announcements"],
            "failed_announcements": result["failed_announcements"],
            "announcement_details": result["announcement_details"],
            "tarokk_declarations": tarokk_lines,
        }
        game_state.phase = GamePhase.GAME_END
        room.last_game_over = payload
        await self.broadcast(room, MessageType.GAME_OVER, payload)
        await self.broadcast_room_state(room)

        logger.info("game_over", room_id=room.room_id, winner=result["winner"],
                    scores=result["player_scores"])
