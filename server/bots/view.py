"""What one seat can legitimately see. Bots and hints decide from this only."""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from game_logic.bidding import BiddingManager
from models.announcement import Announcement
from models.bid import Bid
from models.card import Card
from models.game_state import GameState, GamePhase, highest_bid_of
from validation.rules import get_legal_cards, get_valid_announcements

Play = Tuple[int, Card]  # (seat, card)


@dataclass
class SeatView:
    position: int
    phase: GamePhase
    hand: List[Card]
    own_discards: List[Card]
    dealer_position: int

    # Bidding
    bid_history: List[Bid] = field(default_factory=list)
    valid_bids: List[str] = field(default_factory=list)
    highest_bid: Optional[str] = None

    # Contract
    declarer_position: Optional[int] = None
    called_rank: Optional[str] = None
    partner_position: Optional[int] = None  # only once revealed
    i_am_partner: bool = False
    declarer_alone: bool = False  # only once the kontra on the game was shown

    # Announcements
    announcements: List[Announcement] = field(default_factory=list)
    valid_announcements: List[str] = field(default_factory=list)

    # Tricks
    current_trick: List[Play] = field(default_factory=list)
    trick_history: List[List[Play]] = field(default_factory=list)
    trick_number: int = 0
    legal_cards: List[Card] = field(default_factory=list)

    discard_count: int = 0

    # ---- derived -----------------------------------------------------------

    @property
    def tarokks(self) -> List[Card]:
        return [c for c in self.hand if c.is_tarokk()]

    def holds(self, rank: str) -> bool:
        return any(c.is_tarokk() and c.rank.lower() == rank.lower() for c in self.hand)

    @property
    def on_declarer_side(self) -> bool:
        return self.position == self.declarer_position or self.i_am_partner

    def teammates(self) -> set:
        """Seats I know to be on my side (never including me)."""
        others = {0, 1, 2, 3} - {self.position}
        if self.position == self.declarer_position:
            return {self.partner_position} if self.partner_position is not None else set()
        if self.i_am_partner:
            return {self.declarer_position}
        # Defender: the others are known once the partner shows, or when the declarer is alone
        if self.declarer_alone:
            return others - {self.declarer_position}
        if self.partner_position is not None:
            return others - {self.declarer_position, self.partner_position}
        return set()

    def opponents(self) -> set:
        """Seats I know to be against me."""
        others = {0, 1, 2, 3} - {self.position}
        if self.position == self.declarer_position:
            if self.declarer_alone:
                return others
            return others - {self.partner_position} if self.partner_position is not None else set()
        if self.i_am_partner:
            return others - {self.declarer_position}
        if self.declarer_position is None:
            return set()
        known = {self.declarer_position}
        if self.partner_position is not None:
            known.add(self.partner_position)
        return known

    def is_teammate(self, position: int) -> bool:
        return position in self.teammates()


def build_view(game_state: GameState, position: int) -> SeatView:
    player = game_state.get_player(position)
    if player is None:
        raise ValueError(f"No player on seat {position}")
    phase = game_state.phase
    hand = list(player.hand)
    called = game_state.called_card_rank

    partner_shown = game_state.partner_revealed and game_state.partner_position is not None
    holds_called = bool(called) and any(c.is_tarokk() and c.rank == called for c in hand)
    i_am_partner = position != game_state.declarer_position and (
        holds_called or (partner_shown and game_state.partner_position == position)
    )

    view = SeatView(
        position=position,
        phase=phase,
        hand=hand,
        own_discards=list(player.discard_pile),
        dealer_position=game_state.dealer_position,
        bid_history=list(game_state.bid_history),
        declarer_position=game_state.declarer_position,
        called_rank=called,
        partner_position=game_state.partner_position if partner_shown else None,
        i_am_partner=i_am_partner,
        declarer_alone=game_state.declarer_alone and game_state.game_contra,
        announcements=list(game_state.announcements),
        current_trick=list(game_state.current_trick),
        trick_history=[
            [(entry["player_position"], Card.from_dict(entry["card"])) for entry in trick["cards"]]
            for trick in game_state.trick_history
        ],
        trick_number=game_state.trick_number,
    )

    highest = highest_bid_of(game_state.bid_history)
    view.highest_bid = highest.bid_type.value if highest else None

    if phase == GamePhase.BIDDING:
        view.valid_bids = [b.value for b in BiddingManager.get_valid_bid_types(player, game_state.bid_history)]
    elif phase == GamePhase.DISCARDING:
        view.discard_count = max(len(hand) - 9, 0)
    elif phase == GamePhase.ANNOUNCEMENTS:
        already = {a.announcement_type for a in game_state.announcements}
        view.valid_announcements = [a.value for a in get_valid_announcements(hand) if a not in already]
    elif phase == GamePhase.PLAYING:
        is_first = len(game_state.current_trick) == 0
        lead_suit = None if is_first else game_state.current_trick[0][1].suit
        view.legal_cards = list(get_legal_cards(hand, lead_suit, is_first))
    return view
