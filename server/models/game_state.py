"""Game state model for Hungarian Tarokk."""

from enum import Enum
from typing import List, Optional, Tuple, Dict
from pydantic import BaseModel, Field
from uuid import uuid4

from models.card import Card, TarokkRank
from models.deck import Deck
from models.player import Player
from models.bid import Bid, BidType
from models.announcement import Announcement


def highest_bid_of(bid_history: List[Bid]) -> Optional[Bid]:
    """Highest non-pass bid; among equal values the latest one wins."""
    best = None
    for b in bid_history:
        if b.bid_type == BidType.PASS:
            continue
        if best is None or b.game_value >= best.game_value:
            best = b
    return best


def can_hold(position: int, bid_history: List[Bid]) -> bool:
    """
    Only a player who bid earlier may hold a later, higher bid.

    The bid being held must be a real bid (not itself a hold) by someone
    else, and the holder's own last bid must be lower.
    """
    if any(b.player_position == position and b.bid_type == BidType.PASS for b in bid_history):
        return False
    highest = highest_bid_of(bid_history)
    if highest is None or highest.bid_type == BidType.HOLD or highest.player_position == position:
        return False
    own = [b for b in bid_history if b.player_position == position and b.bid_type != BidType.PASS]
    return bool(own) and own[-1].game_value < highest.game_value


class GamePhase(str, Enum):
    """Game phases in Hungarian Tarokk."""
    WAITING = "waiting"              # Waiting for players
    DEALING = "dealing"              # Dealing cards
    BIDDING = "bidding"              # Auction phase
    TALON_DISTRIBUTION = "talon_distribution"  # Distributing talon cards
    DISCARDING = "discarding"        # Players discarding to 9 cards
    PARTNER_CALL = "partner_call"    # Declarer calling partner
    ANNOUNCEMENTS = "announcements"  # Optional bonus announcements
    PLAYING = "playing"              # Trick-taking phase
    SCORING = "scoring"              # Counting points
    GAME_END = "game_end"            # Hand complete


class GameState(BaseModel):
    """
    Central game state for Hungarian Tarokk.

    Tracks all game information including players, cards, bids, and current phase.
    """
    game_id: str = Field(default_factory=lambda: str(uuid4()))
    phase: GamePhase = GamePhase.WAITING
    players: List[Player] = Field(default_factory=list)
    deck: Optional[Deck] = None
    talon: List[Card] = Field(default_factory=list)

    # Position tracking (0-3)
    dealer_position: int = 0
    current_turn: int = 0

    # Bidding
    bid_history: List[Bid] = Field(default_factory=list)
    declarer_position: Optional[int] = None
    winning_bid: Optional[Bid] = None

    # Partner
    called_card_rank: Optional[str] = None  # e.g., "XX"
    partner_position: Optional[int] = None
    partner_revealed: bool = False

    # Trick-taking
    current_trick: List[Tuple[int, Card]] = Field(default_factory=list)  # (player_position, card)
    trick_leader: Optional[int] = None
    trick_number: int = 0
    previous_trick_winner: Optional[int] = None
    trick_history: List[dict] = Field(default_factory=list)  # Complete history of all tricks

    # Discard phase tracking
    players_who_discarded: List[int] = Field(default_factory=list)

    # Announcements
    announcements: List[Announcement] = Field(default_factory=list)
    announcement_history: List[Optional[Announcement]] = Field(default_factory=list)  # Track all actions (announcement or None for pass)
    announcement_turn_log: List[dict] = Field(default_factory=list)  # One entry per turn: {"position", "passed"}

    # Declarer alone (called card lies in the skart) and kontra on the game
    declarer_alone: bool = False
    called_card_discarded_by: Optional[int] = None
    game_contra: bool = False

    # Hands played at this table
    hand_number: int = 1

    def add_player(self, player: Player) -> None:
        """Add a player to the game."""
        if len(self.players) >= 4:
            raise ValueError("Game already has 4 players")
        player.position = len(self.players)
        self.players.append(player)

    def get_player(self, position: int) -> Optional[Player]:
        """Get player by position."""
        if 0 <= position < len(self.players):
            return self.players[position]
        return None

    def get_player_by_id(self, player_id: str) -> Optional[Player]:
        """Get player by ID."""
        return next((p for p in self.players if p.id == player_id), None)

    def all_players_ready(self) -> bool:
        """Check if all 4 players are ready."""
        return len(self.players) == 4 and all(p.is_ready for p in self.players)

    def dealer_right_position(self) -> int:
        """Get position to the dealer's right (counter-clockwise)."""
        return (self.dealer_position + 1) % 4

    def next_position(self, current: int) -> int:
        """Get next position counter-clockwise."""
        return (current + 1) % 4

    def start_dealing(self) -> None:
        """Initialize dealing phase."""
        self.phase = GamePhase.DEALING
        self.deck = Deck.create_and_shuffle()

        # Reset all players for new hand
        for player in self.players:
            player.reset_for_new_hand()

        # Deal cards: 9 to each player, 6 to talon
        # Deal order: 6 to talon, 5 to each player, 4 to each player
        self.talon = self.deck.deal(6)

        # Deal 5 cards to each player (counter-clockwise from dealer's right)
        start_pos = self.dealer_right_position()
        for _ in range(5):
            for i in range(4):
                pos = (start_pos + i) % 4
                cards = self.deck.deal(1)
                self.players[pos].add_cards_to_hand(cards)

        # Deal 4 more cards to each player
        for _ in range(4):
            for i in range(4):
                pos = (start_pos + i) % 4
                cards = self.deck.deal(1)
                self.players[pos].add_cards_to_hand(cards)

    def start_bidding(self) -> None:
        """Start the bidding phase."""
        self.phase = GamePhase.BIDDING
        self.bid_history.clear()
        self.current_turn = self.dealer_right_position()

    def place_bid(self, player_position: int, bid_type: BidType) -> Bid:
        """
        Place a bid for a player.

        Args:
            player_position: Position of bidding player
            bid_type: Type of bid

        Returns:
            The created bid

        Raises:
            ValueError: If bid is invalid
        """
        if player_position != self.current_turn:
            raise ValueError("Not this player's turn to bid")

        player = self.get_player(player_position)
        if not player:
            raise ValueError("Player not found")

        # Check if player has honour (required to bid)
        if bid_type not in [BidType.PASS, BidType.HOLD] and not player.has_honour():
            raise ValueError("Player must have at least one honour (skíz, XXI, or pagát) to bid")

        if player_position in self.passed_positions():
            raise ValueError("Player has already passed in this auction")

        # Check if HOLD is allowed
        if bid_type == BidType.HOLD and not can_hold(player_position, self.bid_history):
            raise ValueError("Cannot HOLD - only a player who has already bid may hold a later, higher bid")

        # Create bid
        bid = Bid(player_position=player_position, bid_type=bid_type)

        # For HOLD, match the highest bid's value
        if bid_type == BidType.HOLD:
            highest_bid = self.get_highest_bid()
            if highest_bid:
                bid.game_value = highest_bid.game_value
                bid.talon_cards = highest_bid.talon_cards

        # Validate bid is higher (except for PASS and HOLD)
        if bid_type not in [BidType.PASS, BidType.HOLD]:
            highest_bid = self.get_highest_bid()
            if not bid.is_higher_than(highest_bid):
                raise ValueError("Bid must be higher than current highest bid")

        self.bid_history.append(bid)

        # Solo ends the auction immediately
        if bid_type == BidType.SOLO:
            self.end_bidding()
        elif not self.is_bidding_complete():
            # Move to the next player who has not passed
            passed = self.passed_positions()
            nxt = self.next_position(self.current_turn)
            while nxt in passed:
                nxt = self.next_position(nxt)
            self.current_turn = nxt

        return bid

    def passed_positions(self) -> set:
        """Seats that have passed in this auction. A pass is final."""
        return {b.player_position for b in self.bid_history if b.bid_type == BidType.PASS}

    def get_highest_bid(self) -> Optional[Bid]:
        """Get the current highest bid (excluding PASS).

        Among bids of the same value the latest wins, so a player who
        holds a bid takes it over.
        """
        return highest_bid_of(self.bid_history)

    def is_bidding_complete(self) -> bool:
        """Check if bidding phase is complete."""
        if not self.bid_history:
            return False

        # Solo ends bidding
        if any(b.bid_type == BidType.SOLO for b in self.bid_history):
            return True

        active = [p for p in range(4) if p not in self.passed_positions()]

        # All 4 players have passed
        if not active:
            return True

        # One player left and that player owns the highest bid
        if len(active) == 1:
            highest = self.get_highest_bid()
            return highest is not None and highest.player_position == active[0]

        return False

    def end_bidding(self) -> None:
        """End bidding and determine declarer."""
        highest = self.get_highest_bid()
        if highest and highest.bid_type == BidType.HOLD:
            # Record the held bid under its real type
            real_type = next(t for t in (BidType.THREE, BidType.TWO, BidType.ONE, BidType.SOLO)
                             if Bid(player_position=0, bid_type=t).game_value == highest.game_value)
            highest = Bid(player_position=highest.player_position, bid_type=real_type)
        self.winning_bid = highest
        if self.winning_bid:
            self.declarer_position = self.winning_bid.player_position
            self.players[self.declarer_position].is_declarer = True

    def distribute_talon(self) -> Dict[int, List[Card]]:
        """
        Distribute talon cards based on winning bid.

        Returns:
            Dictionary mapping player positions to their talon cards
        """
        if not self.winning_bid or self.declarer_position is None:
            raise ValueError("No winning bid or declarer")

        self.phase = GamePhase.TALON_DISTRIBUTION

        distribution: Dict[int, List[Card]] = {}
        declarer_cards_count = self.winning_bid.talon_cards

        # Declarer takes their cards
        declarer_cards = self.talon[:declarer_cards_count]
        distribution[self.declarer_position] = declarer_cards
        self.players[self.declarer_position].add_cards_to_hand(declarer_cards)

        # Distribute remaining cards to other 3 players
        remaining_cards = self.talon[declarer_cards_count:]
        other_positions = [i for i in range(4) if i != self.declarer_position]

        # Distribute as equally as possible
        cards_per_player = len(remaining_cards) // 3
        extra_cards = len(remaining_cards) % 3

        card_index = 0
        for i, pos in enumerate(other_positions):
            cards_to_give = cards_per_player + (1 if i < extra_cards else 0)
            player_cards = remaining_cards[card_index:card_index + cards_to_give]
            distribution[pos] = player_cards
            self.players[pos].add_cards_to_hand(player_cards)
            card_index += cards_to_give

        # Clear the talon since all cards have been distributed to players' hands
        self.talon.clear()

        return distribution

    def start_discard_phase(self) -> None:
        """Start the discard phase."""
        self.phase = GamePhase.DISCARDING
        self.players_who_discarded.clear()
        # Start with dealer's right (or could be declarer's left - TBD)
        self.current_turn = self.dealer_right_position()

    def can_end_discard_phase(self) -> bool:
        """Check if all players have discarded."""
        # All 4 players must discard (including declarer)
        return len(self.players_who_discarded) == 4

    def call_partner(self, tarokk_rank: str) -> None:
        """
        Declarer calls a partner by specifying a tarokk card.

        Args:
            tarokk_rank: Rank of tarokk card to call (e.g., "XX")
        """
        if self.declarer_position is None:
            raise ValueError("No declarer")

        self.phase = GamePhase.PARTNER_CALL
        self.called_card_rank = tarokk_rank
        self.declarer_alone = False
        self.called_card_discarded_by = None

        # Find which player has this card
        for player in self.players:
            for card in player.hand:
                if card.is_tarokk() and card.rank == tarokk_rank:
                    self.partner_position = player.position
                    player.is_partner = True
                    return

        # The called card lies in the skart: the declarer plays alone.
        self.partner_position = None
        self.declarer_alone = True
        for player in self.players:
            if any(c.is_tarokk() and c.rank == tarokk_rank for c in player.discard_pile):
                if player.position != self.declarer_position:
                    # This player must kontra the game.
                    self.called_card_discarded_by = player.position
                return

        raise ValueError(f"Called card {tarokk_rank} not found")

    def apply_obligatory_contra_if_due(self) -> bool:
        """
        Apply the obligatory kontra on the game when the seat to move in the
        announcement round is the player who discarded the called card.

        Returns:
            True if the kontra was applied by this call
        """
        if (self.phase == GamePhase.ANNOUNCEMENTS
                and not self.game_contra
                and self.called_card_discarded_by is not None
                and self.current_turn == self.called_card_discarded_by):
            self.game_contra = True
            return True
        return False

    def start_announcement_phase(self) -> None:
        """Start the announcement phase."""
        self.phase = GamePhase.ANNOUNCEMENTS
        self.announcement_history.clear()
        self.announcements.clear()
        self.announcement_turn_log.clear()
        # Start with declarer (bid winner)
        self.current_turn = self.declarer_position

    def _end_announcement_turn(self, player_position: int, passed: bool) -> None:
        """Log one announcement turn and move to the next seat."""
        self.announcement_turn_log.append({"position": player_position, "passed": passed})
        self.current_turn = self.next_position(self.current_turn)

    def make_announcements(self, player_position: int, announcements: List[Announcement]) -> None:
        """
        Add one or more announcements made in a single turn.

        The turn moves on by one seat, however many announcements were made.
        """
        for announcement in announcements:
            self.announcements.append(announcement)
            self.announcement_history.append(announcement)
        self._end_announcement_turn(player_position, passed=False)

    def make_announcement(self, announcement: Announcement) -> None:
        """Add a single announcement (one turn)."""
        self.make_announcements(announcement.player_position, [announcement])

    def player_pass_announcement(self, player_position: int) -> None:
        """
        Mark that a player has passed on making announcements.

        Args:
            player_position: Position of player who passed
        """
        # None indicates a pass
        self.announcement_history.append(None)
        self._end_announcement_turn(player_position, passed=True)

    def record_contra_turn(self, player_position: int) -> None:
        """A kontra or rekontra uses the player's turn and is not a pass."""
        self.announcement_history.append(None)
        self._end_announcement_turn(player_position, passed=False)

    def is_announcement_phase_complete(self) -> bool:
        """
        Check if the announcement phase is complete.

        Every seat gets at least one turn; after that the phase ends on
        three passes in a row.
        """
        log = self.announcement_turn_log
        if len({t["position"] for t in log}) < 4:
            return False
        return all(t["passed"] for t in log[-3:])

    def start_playing(self) -> None:
        """Start the trick-taking phase."""
        self.phase = GamePhase.PLAYING
        self.trick_number = 1
        # First trick: dealer's right leads
        self.trick_leader = self.dealer_right_position()
        self.current_turn = self.trick_leader
        self.current_trick.clear()

    def play_card_to_trick(self, player_position: int, card_id: str) -> Card:
        """
        Play a card to the current trick.

        Args:
            player_position: Position of playing player
            card_id: ID of card to play

        Returns:
            The played card
        """
        if player_position != self.current_turn:
            raise ValueError("Not this player's turn")

        player = self.get_player(player_position)
        if not player:
            raise ValueError("Player not found")

        card = player.play_card(card_id)

        # Check if this is the called card being played
        if card.is_tarokk() and card.rank == self.called_card_rank and not self.partner_revealed:
            self.partner_revealed = True
            if self.partner_position is not None:
                self.players[self.partner_position].partner_revealed = True

        self.current_trick.append((player_position, card))

        # Move to next player or complete trick
        if len(self.current_trick) == 4:
            self.complete_trick()
        else:
            self.current_turn = self.next_position(self.current_turn)

        return card

    def complete_trick(self) -> int:
        """
        Complete the current trick and determine winner.

        Returns:
            Position of trick winner
        """
        if len(self.current_trick) != 4:
            raise ValueError("Trick not complete")

        # Determine lead suit (first card played)
        lead_card = self.current_trick[0][1]
        lead_suit = lead_card.suit

        # Find winning card
        winner_pos = self._determine_trick_winner(lead_suit)

        # Award cards to winner
        trick_cards = [card for _, card in self.current_trick]
        self.players[winner_pos].add_to_tricks(trick_cards)

        # Save trick to history BEFORE clearing
        self.trick_history.append({
            "trick_number": self.trick_number + 1,  # 1-indexed for display
            "cards": [
                {
                    "player_position": pos,
                    "card": card.to_dict()
                }
                for pos, card in self.current_trick
            ],
            "winner": winner_pos,
            "winner_name": self.players[winner_pos].name,
            "lead_suit": lead_suit.value if lead_suit else None
        })

        # Setup for next trick
        self.previous_trick_winner = winner_pos
        self.current_trick.clear()
        self.trick_number += 1

        if self.trick_number <= 9:
            # Winner leads next trick
            self.trick_leader = winner_pos
            self.current_turn = winner_pos
        else:
            # All tricks complete
            self.phase = GamePhase.SCORING

        return winner_pos

    def _determine_trick_winner(self, lead_suit) -> int:
        """Determine winner of current trick."""
        tarokk_plays = [(pos, card) for pos, card in self.current_trick if card.is_tarokk()]

        if tarokk_plays:
            # Highest tarokk wins
            winner_pos, _ = max(tarokk_plays, key=lambda x: x[1].tarokk_value())
            return winner_pos
        else:
            # Highest card of lead suit wins
            lead_suit_plays = [(pos, card) for pos, card in self.current_trick if card.suit == lead_suit]
            winner_pos, _ = max(lead_suit_plays, key=lambda x: x[1].suit_rank_value())
            return winner_pos

    def calculate_scores(self) -> Tuple[int, int]:
        """
        Calculate final scores for both teams.

        Hungarian Tarokk rules:
        - Declarer's team: Declarer's tricks + Partner's tricks + ONLY Declarer's discards
        - Opponents: Other players' tricks + ALL OTHER discards (including partner's!)

        Returns:
            Tuple of (declarer_team_points, opponent_team_points)
        """
        if self.declarer_position is None:
            raise ValueError("No declarer")

        declarer_team_points = 0
        opponent_team_points = 0

        for player in self.players:
            # Count tricks won
            tricks_points = sum(c.points for c in player.tricks_won)

            if player.position == self.declarer_position:
                # Declarer: tricks + discards go to declarer team
                discard_points = sum(c.points for c in player.discard_pile)
                declarer_team_points += tricks_points + discard_points
            elif player.position == self.partner_position:
                # Partner: tricks go to declarer team, but discards go to OPPONENTS!
                declarer_team_points += tricks_points
                discard_points = sum(c.points for c in player.discard_pile)
                opponent_team_points += discard_points
            else:
                # Opponents: tricks + discards go to opponent team
                discard_points = sum(c.points for c in player.discard_pile)
                opponent_team_points += tricks_points + discard_points

        return declarer_team_points, opponent_team_points

    def declarer_team_wins(self) -> bool:
        """Check if declarer's team won (48+ points)."""
        declarer_points, _ = self.calculate_scores()
        return declarer_points >= 48

    def to_dict(self, player_id: Optional[str] = None, include_all_hands: bool = False) -> dict:
        """
        Convert game state to dictionary for JSON serialization.

        Args:
            player_id: If provided, hide other players' hands (ignored if include_all_hands=True)
            include_all_hands: If True, include all players' hands (for persistence)

        Returns:
            Dictionary representation
        """
        player_pos = None
        if player_id and not include_all_hands:
            player = self.get_player_by_id(player_id)
            if player:
                player_pos = player.position

        result = {
            "game_id": self.game_id,
            "phase": self.phase.value,
            "players": [
                p.to_dict(hide_hand=(not include_all_hands and player_pos is not None and p.position != player_pos))
                for p in self.players
            ],
            "dealer_position": self.dealer_position,
            "current_turn": self.current_turn,
            "bid_history": [b.to_dict() for b in self.bid_history],
            "declarer_position": self.declarer_position,
            # Only reveal partner position after the called card is played (unless include_all_hands for persistence)
            "partner_position": self.partner_position if (self.partner_revealed or include_all_hands) else None,
            "partner_revealed": self.partner_revealed,
            "called_card_rank": self.called_card_rank,
            "trick_number": self.trick_number,
            "trick_leader": self.trick_leader,
            "previous_trick_winner": self.previous_trick_winner,
            "current_trick": [{"player_position": pos, "card": card.to_dict()} for pos, card in self.current_trick],
            "talon": [card.to_dict() for card in self.talon],
            "announcements": [a.to_dict() for a in self.announcements],
            "trick_history": self.trick_history,  # Full history of completed tricks
            "players_who_discarded": self.players_who_discarded,
            "announcement_history": [a.to_dict() if a else None for a in self.announcement_history],
            "announcement_turn_log": self.announcement_turn_log,
            "game_contra": self.game_contra,
            # Known to everyone only once the obligatory kontra has been said
            "declarer_alone": self.declarer_alone if (self.game_contra or include_all_hands) else False,
            "hand_number": self.hand_number,
        }
        if include_all_hands:
            result["called_card_discarded_by"] = self.called_card_discarded_by

        # Add winning bid if it exists
        if self.winning_bid:
            result["winning_bid"] = self.winning_bid.to_dict()
        else:
            result["winning_bid"] = None

        return result
