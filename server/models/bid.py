"""Bid model for Hungarian Tarokk."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class BidType(str, Enum):
    """Types of bids in Hungarian Tarokk."""
    PASS = "pass"
    THREE = "three"  # 3 cards from talon, 1 game point
    TWO = "two"      # 2 cards from talon, 2 game points
    ONE = "one"      # 1 card from talon, 3 game points
    SOLO = "solo"    # 0 cards from talon, 4 game points
    HOLD = "hold"    # Match the highest bid (can only be used if player already bid)


class Bid(BaseModel):
    """
    Represents a bid in the auction phase.

    Attributes:
        player_position: Position (0-3) of the player making the bid
        bid_type: Type of bid
        game_value: Base game value (points for winning)
        talon_cards: Number of cards declarer takes from talon
    """
    player_position: int
    bid_type: BidType
    game_value: int = 0
    talon_cards: int = 0

    def __init__(self, player_position: int, bid_type: BidType, **data):
        super().__init__(player_position=player_position, bid_type=bid_type, **data)
        self.game_value = self._get_game_value()
        self.talon_cards = self._get_talon_cards()

    def _get_game_value(self) -> int:
        """Get the base game value for this bid type."""
        values = {
            BidType.PASS: 0,
            BidType.THREE: 1,
            BidType.TWO: 2,
            BidType.ONE: 3,
            BidType.SOLO: 4,
            BidType.HOLD: 0,  # Will be set to matched bid's value
        }
        return values.get(self.bid_type, 0)

    def _get_talon_cards(self) -> int:
        """Get the number of talon cards for this bid type."""
        cards = {
            BidType.PASS: 0,
            BidType.THREE: 3,
            BidType.TWO: 2,
            BidType.ONE: 1,
            BidType.SOLO: 0,
            BidType.HOLD: 0,  # Will be set to matched bid's value
        }
        return cards.get(self.bid_type, 0)

    def is_higher_than(self, other: Optional["Bid"]) -> bool:
        """
        Check if this bid is higher than another bid.

        Bid order (ascending): PASS < THREE < TWO < ONE < SOLO
        HOLD matches the highest bid, so it's not higher.

        Args:
            other: The bid to compare against (None means no previous bid)

        Returns:
            True if this bid is higher
        """
        if other is None:
            # Any non-pass bid is higher than no bid
            return self.bid_type != BidType.PASS

        if self.bid_type == BidType.PASS or self.bid_type == BidType.HOLD:
            return False

        if other.bid_type == BidType.PASS:
            return True

        return self.game_value > other.game_value

    def can_hold(self, player_has_bid_before: bool) -> bool:
        """
        Check if a player can use HOLD.

        Rules:
        - Can only HOLD if the player has already bid in this auction
        - Cannot HOLD as your first action

        Args:
            player_has_bid_before: Whether the player has already made a bid in this auction

        Returns:
            True if HOLD is allowed
        """
        if self.bid_type != BidType.HOLD:
            return True  # Not a hold, so no restriction

        return player_has_bid_before

    def __str__(self) -> str:
        """String representation of the bid."""
        return f"{self.bid_type.value}"

    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"Bid(player={self.player_position}, type={self.bid_type.value}, value={self.game_value})"

    def to_dict(self) -> dict:
        """Convert bid to dictionary for JSON serialization."""
        return {
            "player_position": self.player_position,
            "bid_type": self.bid_type.value,
            "game_value": self.game_value,
            "talon_cards": self.talon_cards,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Bid":
        """Create bid from dictionary."""
        return cls(
            player_position=data["player_position"],
            bid_type=BidType(data["bid_type"])
        )
