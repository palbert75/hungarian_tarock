"""Card model for Hungarian Tarokk."""

from enum import Enum
from typing import Optional
from uuid import uuid4
from pydantic import BaseModel, Field


class Suit(str, Enum):
    """Card suits."""
    HEARTS = "hearts"
    DIAMONDS = "diamonds"
    SPADES = "spades"
    CLUBS = "clubs"
    TAROKK = "tarokk"


class TarokkRank(str, Enum):
    """Tarokk (trump) card ranks."""
    SKIZ = "skiz"  # The Fool - highest
    XXI = "XXI"    # 21
    XX = "XX"      # 20
    XIX = "XIX"    # 19
    XVIII = "XVIII"  # 18
    XVII = "XVII"  # 17
    XVI = "XVI"    # 16
    XV = "XV"      # 15
    XIV = "XIV"    # 14
    XIII = "XIII"  # 13
    XII = "XII"    # 12
    XI = "XI"      # 11
    X = "X"        # 10
    IX = "IX"      # 9
    VIII = "VIII"  # 8
    VII = "VII"    # 7
    VI = "VI"      # 6
    V = "V"        # 5
    IV = "IV"      # 4
    III = "III"    # 3
    II = "II"      # 2
    PAGAT = "I"    # 1 (Pagát) - lowest but is an honour


class SuitRank(str, Enum):
    """Suit card ranks."""
    KING = "K"      # 5 points
    QUEEN = "Q"     # 4 points
    CAVALIER = "C"  # 3 points (Rider/Knight)
    JACK = "J"      # 2 points
    TEN = "10"      # 1 point


class CardType(str, Enum):
    """Card type classification."""
    HONOUR = "honour"  # skíz, XXI, pagát
    KING = "king"
    TAROKK = "tarokk"
    SUIT = "suit"


class Card(BaseModel):
    """
    Represents a single card in Hungarian Tarokk.

    A card can be either:
    - A tarokk (trump) card with a TarokkRank
    - A suit card with a Suit and SuitRank
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    suit: Suit
    rank: str  # Either TarokkRank or SuitRank value
    points: int
    card_type: CardType

    def is_tarokk(self) -> bool:
        """Check if this is a tarokk (trump) card."""
        return self.suit == Suit.TAROKK

    def is_honour(self) -> bool:
        """Check if this is an honour (skíz, XXI, or pagát)."""
        if not self.is_tarokk():
            return False
        return self.rank in [TarokkRank.SKIZ.value, TarokkRank.XXI.value, TarokkRank.PAGAT.value]

    def is_king(self) -> bool:
        """Check if this is a King."""
        return self.card_type == CardType.KING

    def can_be_discarded(self) -> bool:
        """Check if this card can be legally discarded."""
        # Cannot discard Kings or Honours
        return not (self.is_king() or self.is_honour())

    def tarokk_value(self) -> int:
        """
        Get the numerical value of a tarokk for comparison.
        Higher value = stronger tarokk.
        Skíz is highest, then XXI down to pagát (I).
        """
        if not self.is_tarokk():
            return 0

        tarokk_order = {
            TarokkRank.SKIZ.value: 22,
            TarokkRank.XXI.value: 21,
            TarokkRank.XX.value: 20,
            TarokkRank.XIX.value: 19,
            TarokkRank.XVIII.value: 18,
            TarokkRank.XVII.value: 17,
            TarokkRank.XVI.value: 16,
            TarokkRank.XV.value: 15,
            TarokkRank.XIV.value: 14,
            TarokkRank.XIII.value: 13,
            TarokkRank.XII.value: 12,
            TarokkRank.XI.value: 11,
            TarokkRank.X.value: 10,
            TarokkRank.IX.value: 9,
            TarokkRank.VIII.value: 8,
            TarokkRank.VII.value: 7,
            TarokkRank.VI.value: 6,
            TarokkRank.V.value: 5,
            TarokkRank.IV.value: 4,
            TarokkRank.III.value: 3,
            TarokkRank.II.value: 2,
            TarokkRank.PAGAT.value: 1,
        }
        return tarokk_order.get(self.rank, 0)

    def suit_rank_value(self) -> int:
        """
        Get the numerical value of a suit card's rank for comparison.
        King is highest, then Queen, Cavalier, Jack, Ten.
        """
        if self.is_tarokk():
            return 0

        suit_order = {
            SuitRank.KING.value: 5,
            SuitRank.QUEEN.value: 4,
            SuitRank.CAVALIER.value: 3,
            SuitRank.JACK.value: 2,
            SuitRank.TEN.value: 1,
        }
        return suit_order.get(self.rank, 0)

    def __str__(self) -> str:
        """String representation of the card."""
        if self.is_tarokk():
            return f"Tarokk {self.rank}"
        return f"{self.rank} of {self.suit.value}"

    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"Card({self.suit.value}, {self.rank}, {self.points}pts)"

    def to_dict(self) -> dict:
        """Convert card to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "suit": self.suit.value,
            "rank": self.rank,
            "points": self.points,
            "card_type": self.card_type.value,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Card":
        """Create card from dictionary."""
        return cls(**data)
