"""WebSocket server for Hungarian Tarokk."""

import asyncio
import socketio
from typing import Dict, Any
import structlog

from networking.protocol import (
    MessageType, Message, create_error_message,
    JoinRoomMessage, PlaceBidMessage, DiscardCardsMessage,
    CallPartnerMessage, MakeAnnouncementMessage, PlayCardMessage
)
from networking.room_manager import RoomManager
from models.bid import BidType
from models.game_state import GamePhase
from models.announcement import Announcement, AnnouncementType
from game_logic.bidding import BiddingManager
from validation.rules import get_legal_cards, validate_discard, can_announce

logger = structlog.get_logger()

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # Configure appropriately for production
    logger=True,
    engineio_logger=True
)

# Room manager instance
room_manager = RoomManager()


@sio.event
async def connect(sid: str, environ: dict):
    """Handle client connection."""
    logger.info("=== CLIENT CONNECTING ===")
    logger.info("client_connected", sid=sid)
    logger.info("environ_keys", keys=list(environ.keys()))
    logger.info("http_method", method=environ.get('REQUEST_METHOD', 'unknown'))
    logger.info("path_info", path=environ.get('PATH_INFO', 'unknown'))
    logger.info("query_string", query=environ.get('QUERY_STRING', 'unknown'))
    logger.info("client_address", address=environ.get('REMOTE_ADDR', 'unknown'))
    logger.info("user_agent", ua=environ.get('HTTP_USER_AGENT', 'unknown'))

    # Don't emit "connect" - it's a reserved event name!
    # The Socket.IO client automatically receives the connect event
    # when the connection is established
    logger.info("client_connected_successfully", sid=sid)


@sio.event
async def disconnect(sid: str):
    """Handle client disconnection."""
    logger.info("=== CLIENT DISCONNECTING ===")
    logger.info("client_disconnected", sid=sid)

    # Remove player from room
    room = room_manager.leave_room(sid)
    if room:
        # Notify other players
        await broadcast_room_state(room.room_id)


@sio.event
async def list_rooms(sid: str, data: dict):
    """Handle list rooms request."""
    try:
        logger.info("list_rooms_request", sid=sid)

        available_rooms = room_manager.get_available_rooms()

        await sio.emit("rooms_list", {
            "rooms": available_rooms
        }, room=sid)

        logger.info("rooms_list_sent", sid=sid, count=len(available_rooms))

    except Exception as e:
        logger.error("list_rooms_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("LIST_ROOMS_ERROR", str(e)).to_dict(), room=sid)


@sio.event
async def create_room(sid: str, data: dict):
    """Handle create room request."""
    try:
        player_name = data.get("player_name", "Player")
        logger.info("create_room_request", sid=sid, player_name=player_name)

        room = room_manager.create_room(sid, player_name)

        # Join socket.io room
        await sio.enter_room(sid, room.room_id)

        # Send room state
        await broadcast_room_state(room.room_id)

    except Exception as e:
        logger.error("create_room_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("CREATE_ROOM_ERROR", str(e)).to_dict(), room=sid)


@sio.event
async def join_room(sid: str, data: dict):
    """Handle join room request (including reconnections)."""
    try:
        room_id = data.get("room_id")
        player_name = data.get("player_name", "Player")
        player_id = data.get("player_id")  # Client's stored player ID for reconnection

        logger.info("join_room_request", sid=sid, room_id=room_id,
                   player_name=player_name, player_id=player_id)

        if not room_id:
            # Create new room if no room_id provided
            room = room_manager.create_room(sid, player_name)
            logger.info("room_created", room_id=room.room_id, player_name=player_name)
        else:
            # Join existing room (may be reconnection or new player)
            # Pass player_id to allow reconnection by ID
            room = room_manager.join_room(room_id, sid, player_name, player_id)

            # Log the result
            player = room.get_player_by_name(player_name)
            if player and player_id:
                logger.info("player_reconnected", sid=sid, room_id=room_id,
                          player_name=player_name, player_id=player.id,
                          position=player.position)
            elif player:
                logger.info("player_joined", sid=sid, room_id=room_id,
                          player_name=player_name, player_id=player.id,
                          position=player.position)

        # Join socket.io room
        await sio.enter_room(sid, room.room_id)

        # Send room state to all players
        await broadcast_room_state(room.room_id)

        # If game is in progress, also send current game state
        if room.game_state.phase != GamePhase.WAITING:
            await broadcast_game_state(room.room_id)

    except Exception as e:
        logger.error("join_room_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("JOIN_ROOM_ERROR", str(e)).to_dict(), room=sid)


@sio.event
async def ready(sid: str, data: dict):
    """Handle player ready status."""
    try:
        logger.info("ready_request", sid=sid)

        room = room_manager.get_room_by_session(sid)
        if not room:
            raise ValueError("Not in a room")

        player = room.get_player_by_session(sid)
        if not player:
            raise ValueError("Player not found")

        room.set_player_ready(player.id, True)

        # Broadcast room state
        await broadcast_room_state(room.room_id)

        # Start game if all ready
        if room.can_start_game():
            await start_game(room)

    except Exception as e:
        logger.error("ready_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("READY_ERROR", str(e)).to_dict(), room=sid)


@sio.event
async def leave_room(sid: str, data: dict):
    """Handle player leaving room."""
    try:
        logger.info("leave_room_request", sid=sid)

        room = room_manager.get_room_by_session(sid)
        if not room:
            logger.warning("leave_room_not_in_room", sid=sid)
            return

        room_id = room.room_id

        # Remove player from room
        room_manager.leave_room(sid)

        # Broadcast updated room state to remaining players (if any)
        if room_id in room_manager.rooms:
            await broadcast_room_state(room_id)

        logger.info("player_left_room", sid=sid, room_id=room_id)

    except Exception as e:
        logger.error("leave_room_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("LEAVE_ROOM_ERROR", str(e)).to_dict(), room=sid)


@sio.event
async def place_bid(sid: str, data: dict):
    """Handle place bid action."""
    try:
        room = room_manager.get_room_by_session(sid)
        if not room:
            raise ValueError("Not in a room")

        player = room.get_player_by_session(sid)
        if not player:
            raise ValueError("Player not found")

        game_state = room.game_state

        if game_state.phase != GamePhase.BIDDING:
            raise ValueError("Not in bidding phase")

        if game_state.current_turn != player.position:
            raise ValueError("Not your turn")

        bid_type_str = data.get("bid_type")
        bid_type = BidType(bid_type_str)

        # Validate bid
        can_bid, error = BiddingManager.can_player_bid(player, bid_type, game_state.bid_history)
        if not can_bid:
            raise ValueError(error)

        # Place bid
        bid = game_state.place_bid(player.position, bid_type)

        # Notify all players
        await broadcast_to_room(room.room_id, MessageType.BID_PLACED, {
            "player_position": player.position,
            "bid_type": bid_type_str
        })

        # Check if bidding is complete
        if game_state.is_bidding_complete():
            game_state.end_bidding()

            if game_state.winning_bid:
                # Move to talon distribution
                await handle_talon_distribution(room)
            else:
                # All passed - throw in hand and deal new
                logger.info("all_players_passed", room_id=room.room_id)

                await broadcast_to_room(room.room_id, MessageType.GAME_STATE, {
                    "message": "All players passed. Dealing new hand..."
                })

                # Wait a moment for UI to show message
                await asyncio.sleep(2)

                # Deal new cards and start bidding again
                game_state.start_dealing()
                game_state.start_bidding()

                # Broadcast new game state
                await broadcast_game_state(room.room_id)

                # Notify first bidder
                await send_your_turn(room, game_state.current_turn)

                logger.info("new_hand_dealt", room_id=room.room_id)
        else:
            # Notify next player
            await send_your_turn(room, game_state.current_turn)

        # Broadcast game state
        await broadcast_game_state(room.room_id)

    except Exception as e:
        logger.error("place_bid_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("BID_ERROR", str(e)).to_dict(), room=sid)


@sio.event
async def discard_cards(sid: str, data: dict):
    """Handle discard cards action."""
    try:
        room = room_manager.get_room_by_session(sid)
        if not room:
            raise ValueError("Not in a room")

        player = room.get_player_by_session(sid)
        if not player:
            raise ValueError("Player not found")

        game_state = room.game_state

        if game_state.phase != GamePhase.DISCARDING:
            raise ValueError("Not in discarding phase")

        if game_state.current_turn != player.position:
            raise ValueError("Not your turn")

        card_ids = data.get("card_ids", [])

        # Calculate how many cards to discard
        target_hand_size = 9
        num_to_discard = player.get_hand_size() - target_hand_size

        if len(card_ids) != num_to_discard:
            raise ValueError(f"Must discard exactly {num_to_discard} cards")

        # Get cards to discard
        cards_to_discard = [c for c in player.hand if c.id in card_ids]

        # Validate discard
        is_valid, error = validate_discard(cards_to_discard)
        if not is_valid:
            raise ValueError(error)

        # Discard cards
        discarded = player.discard_cards(card_ids)
        tarokks_discarded = sum(1 for c in discarded if c.is_tarokk())

        # Mark player as having discarded
        game_state.players_who_discarded.append(player.position)

        # Notify all players
        await broadcast_to_room(room.room_id, MessageType.PLAYER_DISCARDED, {
            "player_position": player.position,
            "num_cards": len(discarded),
            "tarokks_discarded": tarokks_discarded
        })

        # Check if all players have discarded
        if game_state.can_end_discard_phase():
            # Move to partner call
            await handle_partner_call_phase(room)
        else:
            # Move to next player
            game_state.current_turn = game_state.next_position(game_state.current_turn)
            await send_your_turn(room, game_state.current_turn)

        await broadcast_game_state(room.room_id)

    except Exception as e:
        logger.error("discard_cards_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("DISCARD_ERROR", str(e)).to_dict(), room=sid)


@sio.event
async def call_partner(sid: str, data: dict):
    """Handle call partner action."""
    try:
        room = room_manager.get_room_by_session(sid)
        if not room:
            raise ValueError("Not in a room")

        player = room.get_player_by_session(sid)
        if not player:
            raise ValueError("Player not found")

        game_state = room.game_state

        if game_state.phase != GamePhase.PARTNER_CALL:
            raise ValueError("Not in partner call phase")

        if player.position != game_state.declarer_position:
            raise ValueError("Only declarer can call partner")

        tarokk_rank = data.get("tarokk_rank")
        if not tarokk_rank:
            raise ValueError("Must specify tarokk rank")

        # Call partner
        game_state.call_partner(tarokk_rank)

        # Notify all players
        await broadcast_to_room(room.room_id, MessageType.PARTNER_CALLED, {
            "called_card": tarokk_rank
        })

        # Start announcement phase
        await start_announcement_phase(room)

    except Exception as e:
        logger.error("call_partner_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("CALL_PARTNER_ERROR", str(e)).to_dict(), room=sid)


@sio.event
async def make_announcement(sid: str, data: dict):
    """Handle make announcement action (single or multiple)."""
    try:
        room = room_manager.get_room_by_session(sid)
        if not room:
            raise ValueError("Not in a room")

        player = room.get_player_by_session(sid)
        if not player:
            raise ValueError("Player not found")

        game_state = room.game_state

        if game_state.phase != GamePhase.ANNOUNCEMENTS:
            raise ValueError("Not in announcement phase")

        if game_state.current_turn != player.position:
            raise ValueError("Not your turn")

        # Support both single announcement and multiple announcements
        announcement_types = data.get("announcement_types")  # Array of types
        if announcement_types is None:
            # Fallback to single announcement for backward compatibility
            announcement_type_str = data.get("announcement_type")
            if not announcement_type_str:
                raise ValueError("Must specify announcement type(s)")
            announcement_types = [announcement_type_str]

        announced = data.get("announced", True)

        logger.info("make_announcement_request", sid=sid,
                   player_position=player.position,
                   announcement_types=announcement_types,
                   announced=announced,
                   count=len(announcement_types))

        # Process all announcements
        for announcement_type_str in announcement_types:
            announcement_type = AnnouncementType(announcement_type_str)

            # Validate announcement
            is_valid, error = can_announce(player.hand, announcement_type)
            if not is_valid:
                raise ValueError(f"{announcement_type_str}: {error}")

            # Create and add announcement
            announcement = Announcement(
                player_position=player.position,
                announcement_type=announcement_type,
                announced=announced
            )
            game_state.make_announcement(announcement)

            # Notify all players about this announcement
            await broadcast_to_room(room.room_id, MessageType.ANNOUNCEMENT_MADE, {
                "player_position": player.position,
                "announcement_type": announcement_type_str,
                "announced": announced
            })

        logger.info("announcements_processed", player_position=player.position,
                   count=len(announcement_types))

        # After all announcements are processed, check if phase is complete
        if game_state.is_announcement_phase_complete():
            await broadcast_to_room(room.room_id, MessageType.ANNOUNCEMENTS_COMPLETE, {})
            # Start trick-taking
            await start_trick_taking(room)
        else:
            # Notify next player (only after all announcements are processed)
            await send_your_turn(room, game_state.current_turn)

        await broadcast_game_state(room.room_id)

    except Exception as e:
        logger.error("make_announcement_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("ANNOUNCEMENT_ERROR", str(e)).to_dict(), room=sid)


@sio.event
async def pass_announcement(sid: str, data: dict):
    """Handle pass announcement action."""
    try:
        room = room_manager.get_room_by_session(sid)
        if not room:
            raise ValueError("Not in a room")

        player = room.get_player_by_session(sid)
        if not player:
            raise ValueError("Player not found")

        game_state = room.game_state

        if game_state.phase != GamePhase.ANNOUNCEMENTS:
            raise ValueError("Not in announcement phase")

        if game_state.current_turn != player.position:
            raise ValueError("Not your turn")

        # Mark player as passed
        game_state.player_pass_announcement(player.position)

        # Notify all players
        await broadcast_to_room(room.room_id, MessageType.PASS_ANNOUNCEMENT, {
            "player_position": player.position
        })

        # Check if announcement phase is complete
        if game_state.is_announcement_phase_complete():
            await broadcast_to_room(room.room_id, MessageType.ANNOUNCEMENTS_COMPLETE, {})
            # Start trick-taking
            await start_trick_taking(room)
        else:
            # Notify next player
            await send_your_turn(room, game_state.current_turn)

        await broadcast_game_state(room.room_id)

    except Exception as e:
        logger.error("pass_announcement_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("PASS_ANNOUNCEMENT_ERROR", str(e)).to_dict(), room=sid)


@sio.event
async def contra_announcement(sid: str, data: dict):
    """Handle contra on an announcement."""
    try:
        room = room_manager.get_room_by_session(sid)
        if not room:
            raise ValueError("Not in a room")

        player = room.get_player_by_session(sid)
        if not player:
            raise ValueError("Player not found")

        game_state = room.game_state

        if game_state.phase != GamePhase.ANNOUNCEMENTS:
            raise ValueError("Not in announcement phase")

        if game_state.current_turn != player.position:
            raise ValueError("Not your turn")

        announcement_type_str = data.get("announcement_type")
        if not announcement_type_str:
            raise ValueError("Must specify announcement type")

        # Find the announcement
        announcement = next(
            (a for a in game_state.announcements if a.announcement_type.value == announcement_type_str),
            None
        )
        if not announcement:
            raise ValueError(f"No announcement of type {announcement_type_str} found")

        if announcement.contra:
            raise ValueError("This announcement has already been contra'd")

        # Check if player is on opposing team
        is_declarer_team = player.position == game_state.declarer_position or player.position == game_state.partner_position
        is_announcement_by_declarer_team = (
            announcement.player_position == game_state.declarer_position or
            announcement.player_position == game_state.partner_position
        )

        if is_declarer_team == is_announcement_by_declarer_team:
            raise ValueError("Can only contra opponent announcements")

        # Apply contra
        announcement.contra = True
        announcement.contra_by = player.position

        # Add to announcement history
        game_state.player_pass_announcement(player.position)  # Move turn forward

        # Notify all players
        await broadcast_to_room(room.room_id, MessageType.CONTRA_MADE, {
            "player_position": player.position,
            "announcement_type": announcement_type_str
        })

        # Check if announcement phase is complete
        if game_state.is_announcement_phase_complete():
            await broadcast_to_room(room.room_id, MessageType.ANNOUNCEMENTS_COMPLETE, {})
            await start_trick_taking(room)
        else:
            await send_your_turn(room, game_state.current_turn)

        await broadcast_game_state(room.room_id)

    except Exception as e:
        logger.error("contra_announcement_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("CONTRA_ERROR", str(e)).to_dict(), room=sid)


@sio.event
async def recontra_announcement(sid: str, data: dict):
    """Handle recontra on a contra'd announcement."""
    try:
        room = room_manager.get_room_by_session(sid)
        if not room:
            raise ValueError("Not in a room")

        player = room.get_player_by_session(sid)
        if not player:
            raise ValueError("Player not found")

        game_state = room.game_state

        if game_state.phase != GamePhase.ANNOUNCEMENTS:
            raise ValueError("Not in announcement phase")

        if game_state.current_turn != player.position:
            raise ValueError("Not your turn")

        announcement_type_str = data.get("announcement_type")
        if not announcement_type_str:
            raise ValueError("Must specify announcement type")

        # Find the announcement
        announcement = next(
            (a for a in game_state.announcements if a.announcement_type.value == announcement_type_str),
            None
        )
        if not announcement:
            raise ValueError(f"No announcement of type {announcement_type_str} found")

        if not announcement.contra:
            raise ValueError("Can only recontra a contra'd announcement")

        if announcement.recontra:
            raise ValueError("This announcement has already been recontra'd")

        # Check if player is on the same team as the original announcer
        is_declarer_team = player.position == game_state.declarer_position or player.position == game_state.partner_position
        is_announcement_by_declarer_team = (
            announcement.player_position == game_state.declarer_position or
            announcement.player_position == game_state.partner_position
        )

        if is_declarer_team != is_announcement_by_declarer_team:
            raise ValueError("Can only recontra your own team's announcements")

        # Apply recontra
        announcement.recontra = True
        announcement.recontra_by = player.position

        # Add to announcement history
        game_state.player_pass_announcement(player.position)  # Move turn forward

        # Notify all players
        await broadcast_to_room(room.room_id, MessageType.RECONTRA_MADE, {
            "player_position": player.position,
            "announcement_type": announcement_type_str
        })

        # Check if announcement phase is complete
        if game_state.is_announcement_phase_complete():
            await broadcast_to_room(room.room_id, MessageType.ANNOUNCEMENTS_COMPLETE, {})
            await start_trick_taking(room)
        else:
            await send_your_turn(room, game_state.current_turn)

        await broadcast_game_state(room.room_id)

    except Exception as e:
        logger.error("recontra_announcement_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("RECONTRA_ERROR", str(e)).to_dict(), room=sid)


@sio.event
async def play_card(sid: str, data: dict):
    """Handle play card action."""
    try:
        room = room_manager.get_room_by_session(sid)
        if not room:
            raise ValueError("Not in a room")

        player = room.get_player_by_session(sid)
        if not player:
            raise ValueError("Player not found")

        game_state = room.game_state

        if game_state.phase != GamePhase.PLAYING:
            raise ValueError("Not in playing phase")

        if game_state.current_turn != player.position:
            raise ValueError("Not your turn")

        card_id = data.get("card_id")
        if not card_id:
            raise ValueError("Must specify card_id")

        # Validate card is legal
        card = next((c for c in player.hand if c.id == card_id), None)
        if not card:
            raise ValueError("Card not in hand")

        # Get legal cards
        is_first_card = len(game_state.current_trick) == 0
        lead_suit = game_state.current_trick[0][1].suit if not is_first_card else None
        legal_cards = get_legal_cards(player.hand, lead_suit, is_first_card)

        if card not in legal_cards:
            raise ValueError("Illegal card play - must follow suit or play tarokk if void")

        # Play card
        played_card = game_state.play_card_to_trick(player.position, card_id)

        # Notify all players
        await broadcast_to_room(room.room_id, MessageType.CARD_PLAYED, {
            "player_position": player.position,
            "card": played_card.to_dict()
        })

        # Check if partner was revealed
        if game_state.partner_revealed and played_card.rank == game_state.called_card_rank:
            await broadcast_to_room(room.room_id, MessageType.PARTNER_REVEALED, {
                "partner_position": game_state.partner_position
            })

        # Check if trick is complete
        if len(game_state.current_trick) == 0:  # Trick was completed and cleared
            # Trick complete - winner determined in game_state.complete_trick()
            winner = game_state.previous_trick_winner
            await broadcast_to_room(room.room_id, MessageType.TRICK_COMPLETE, {
                "winner": winner,
                "trick_number": game_state.trick_number - 1
            })

            # Check if game is over
            if game_state.phase == GamePhase.SCORING:
                await handle_game_over(room)
            else:
                # Next trick
                await send_your_turn(room, game_state.current_turn)
        else:
            # Notify next player
            await send_your_turn(room, game_state.current_turn)

        await broadcast_game_state(room.room_id)

    except Exception as e:
        logger.error("play_card_error", sid=sid, error=str(e))
        await sio.emit("error", create_error_message("PLAY_CARD_ERROR", str(e)).to_dict(), room=sid)


# Helper functions

async def broadcast_room_state(room_id: str):
    """Broadcast room state to all players in room."""
    room = room_manager.get_room(room_id)
    if room:
        room_info = room.get_room_info()
        await sio.emit("room_state", room_info, room=room_id)


async def broadcast_game_state(room_id: str):
    """Broadcast game state to all players in room."""
    room = room_manager.get_room(room_id)
    if not room:
        return

    # Send personalized game state to each player
    for player in room.game_state.players:
        session_id = room.player_sessions.get(player.id)
        if session_id:
            game_data = room.game_state.to_dict(player_id=player.id)
            await sio.emit("game_state", game_data, room=session_id)


async def broadcast_to_room(room_id: str, msg_type: MessageType, data: dict):
    """Broadcast a message to all players in room."""
    message = Message.create(msg_type, **data)
    await sio.emit(msg_type.value, message.to_dict(), room=room_id)


async def send_your_turn(room: Any, player_position: int):
    """Notify a player it's their turn."""
    player = room.game_state.get_player(player_position)
    if not player:
        return

    session_id = room.player_sessions.get(player.id)
    if not session_id:
        return

    game_state = room.game_state
    your_turn_data = {
        "valid_actions": []
    }

    if game_state.phase == GamePhase.BIDDING:
        your_turn_data["valid_actions"] = ["place_bid"]
        valid_bids = BiddingManager.get_valid_bid_types(player, game_state.bid_history)
        your_turn_data["valid_bids"] = [b.value for b in valid_bids]

    elif game_state.phase == GamePhase.DISCARDING:
        your_turn_data["valid_actions"] = ["discard_cards"]

    elif game_state.phase == GamePhase.PARTNER_CALL:
        your_turn_data["valid_actions"] = ["call_partner"]

    elif game_state.phase == GamePhase.ANNOUNCEMENTS:
        from validation.rules import get_valid_announcements
        your_turn_data["valid_actions"] = ["make_announcement", "pass_announcement"]
        valid_announcements = get_valid_announcements(player.hand)
        your_turn_data["valid_announcements"] = [a.value for a in valid_announcements]

    elif game_state.phase == GamePhase.PLAYING:
        your_turn_data["valid_actions"] = ["play_card"]
        # Get legal cards
        is_first_card = len(game_state.current_trick) == 0
        lead_suit = game_state.current_trick[0][1].suit if not is_first_card else None
        legal_cards = get_legal_cards(player.hand, lead_suit, is_first_card)
        your_turn_data["valid_cards"] = [c.id for c in legal_cards]

    await sio.emit("your_turn", your_turn_data, room=session_id)


async def start_game(room):
    """Start a new game."""
    logger.info("starting_game", room_id=room.room_id)

    game_state = room.game_state

    # Deal cards
    game_state.start_dealing()

    # Start bidding
    game_state.start_bidding()

    # Notify all players
    await broadcast_to_room(room.room_id, MessageType.GAME_STARTED, {})
    await broadcast_game_state(room.room_id)

    # Notify first bidder
    await send_your_turn(room, game_state.current_turn)


async def handle_talon_distribution(room):
    """Handle talon distribution phase."""
    game_state = room.game_state

    # Distribute talon
    distribution = game_state.distribute_talon()

    # Notify each player
    for player in game_state.players:
        session_id = room.player_sessions.get(player.id)
        if session_id:
            you_received = len(distribution.get(player.position, []))
            await sio.emit("talon_distributed", {
                "you_received": you_received,
                "your_hand_size": player.get_hand_size()
            }, room=session_id)

    # Start discard phase
    game_state.start_discard_phase()
    await broadcast_game_state(room.room_id)
    await send_your_turn(room, game_state.current_turn)


async def handle_partner_call_phase(room):
    """Handle partner call phase."""
    game_state = room.game_state
    game_state.phase = GamePhase.PARTNER_CALL

    await broadcast_game_state(room.room_id)

    # Notify declarer to call partner
    await send_your_turn(room, game_state.declarer_position)


async def start_announcement_phase(room):
    """Start the announcement phase."""
    game_state = room.game_state
    game_state.start_announcement_phase()

    await broadcast_game_state(room.room_id)
    # Notify first player (dealer's right)
    await send_your_turn(room, game_state.current_turn)


async def start_trick_taking(room):
    """Start the trick-taking phase."""
    game_state = room.game_state
    game_state.start_playing()

    await broadcast_to_room(room.room_id, MessageType.TRICK_STARTED, {
        "trick_number": 1,
        "leader": game_state.trick_leader
    })

    await broadcast_game_state(room.room_id)
    await send_your_turn(room, game_state.current_turn)


async def handle_game_over(room):
    """Handle game over."""
    game_state = room.game_state

    # Reveal partner at game end (if not already revealed)
    if not game_state.partner_revealed and game_state.partner_position is not None:
        game_state.partner_revealed = True
        game_state.players[game_state.partner_position].partner_revealed = True

    # Calculate scores
    declarer_points, opponent_points = game_state.calculate_scores()
    winner = "declarer_team" if game_state.declarer_team_wins() else "opponent_team"

    # Notify all players
    await broadcast_to_room(room.room_id, MessageType.GAME_OVER, {
        "declarer": game_state.declarer_position,
        "partner": game_state.partner_position,
        "declarer_team_points": declarer_points,
        "opponent_team_points": opponent_points,
        "winner": winner,
        "game_value": game_state.winning_bid.game_value if game_state.winning_bid else 0,
        "bonuses": [],
        "payments": {}
    })

    # Change phase to game end
    game_state.phase = GamePhase.GAME_END


# Export the Socket.IO app
app = socketio.ASGIApp(sio)
