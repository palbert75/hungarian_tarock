"""Player model for Hungarian Tarokk."""

from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import uuid4

from models.card import Card


class Player(BaseModel):
    """
    Represents a player in Hungarian Tarokk.

    Attributes:
        id: Unique player identifier
        name: Player's display name
        position: Position at table (0-3)
        hand: Current cards in hand
        tricks_won: Cards won in tricks
        discard_pile: Cards discarded during discard phase
        is_connected: Connection status
        is_ready: Ready status in lobby
        is_declarer: Whether this player is the declarer
        is_partner: Whether this player is the partner
    """
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    position: int  # 0-3
    hand: List[Card] = Field(default_factory=list)
    tricks_won: List[Card] = Field(default_factory=list)
    discard_pile: List[Card] = Field(default_factory=list)
    is_connected: bool = True
    is_ready: bool = False
    is_declarer: bool = False
    is_partner: bool = False
    partner_revealed: bool = False  # Whether partner identity has been revealed

    def add_cards_to_hand(self, cards: List[Card]) -> None:
        """Add cards to player's hand."""
        self.hand.extend(cards)

    def remove_cards_from_hand(self, card_ids: List[str]) -> List[Card]:
        """
        Remove specified cards from hand and return them.

        Args:
            card_ids: List of card IDs to remove

        Returns:
            List of removed cards

        Raises:
            ValueError: If any card ID is not found in hand
        """
        removed_cards = []
        for card_id in card_ids:
            card = next((c for c in self.hand if c.id == card_id), None)
            if card is None:
                raise ValueError(f"Card {card_id} not found in hand")
            self.hand.remove(card)
            removed_cards.append(card)
        return removed_cards

    def play_card(self, card_id: str) -> Card:
        """
        Play a card from hand.

        Args:
            card_id: ID of card to play

        Returns:
            The played card

        Raises:
            ValueError: If card not found in hand
        """
        card = next((c for c in self.hand if c.id == card_id), None)
        if card is None:
            raise ValueError(f"Card {card_id} not found in hand")
        self.hand.remove(card)
        return card

    def add_to_tricks(self, cards: List[Card]) -> None:
        """Add won cards to tricks pile."""
        self.tricks_won.extend(cards)

    def discard_cards(self, card_ids: List[str]) -> List[Card]:
        """
        Discard cards from hand to discard pile.

        Args:
            card_ids: List of card IDs to discard

        Returns:
            List of discarded cards

        Raises:
            ValueError: If any card ID not found or cannot be discarded
        """
        cards_to_discard = []
        for card_id in card_ids:
            card = next((c for c in self.hand if c.id == card_id), None)
            if card is None:
                raise ValueError(f"Card {card_id} not found in hand")
            if not card.can_be_discarded():
                raise ValueError(f"Card {card} cannot be discarded (Kings and Honours are protected)")
            cards_to_discard.append(card)

        # Remove from hand and add to discard pile
        for card in cards_to_discard:
            self.hand.remove(card)
            self.discard_pile.append(card)

        return cards_to_discard

    def get_hand_size(self) -> int:
        """Get the number of cards in hand."""
        return len(self.hand)

    def has_card(self, card_id: str) -> bool:
        """Check if player has a specific card in hand."""
        return any(c.id == card_id for c in self.hand)

    def has_suit(self, suit) -> bool:
        """Check if player has any cards of a specific suit."""
        return any(c.suit == suit for c in self.hand)

    def has_tarokk(self) -> bool:
        """Check if player has any tarokk cards."""
        return any(c.is_tarokk() for c in self.hand)

    def has_honour(self) -> bool:
        """
        Check if player has at least one honour card.
        Honours are: skíz, XXI, or pagát.
        Required to place a bid.
        """
        return any(c.is_honour() for c in self.hand)

    def count_tarokks(self) -> int:
        """Count the number of tarokk cards in hand."""
        return sum(1 for c in self.hand if c.is_tarokk())

    def get_total_points(self) -> int:
        """
        Calculate total card points this player has accumulated.
        Includes: tricks won + discard pile.
        """
        tricks_points = sum(c.points for c in self.tricks_won)
        discard_points = sum(c.points for c in self.discard_pile)
        return tricks_points + discard_points

    def reset_for_new_hand(self) -> None:
        """Reset player state for a new hand."""
        self.hand.clear()
        self.tricks_won.clear()
        self.discard_pile.clear()
        self.is_declarer = False
        self.is_partner = False
        self.partner_revealed = False

    def to_dict(self, hide_hand: bool = False) -> dict:
        """
        Convert player to dictionary for JSON serialization.

        Args:
            hide_hand: If True, don't include hand cards (for other players' view)

        Returns:
            Dictionary representation
        """
        data = {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "hand_size": len(self.hand),
            "is_connected": self.is_connected,
            "is_ready": self.is_ready,
            "is_declarer": self.is_declarer,
            "total_points": self.get_total_points(),
            "tricks_won_count": len(self.tricks_won) // 4,  # Each trick has 4 cards
        }

        # Only reveal partner status if partner has been revealed
        if self.partner_revealed:
            data["is_partner"] = self.is_partner

        # Include actual hand cards only if not hiding
        if not hide_hand:
            data["hand"] = [card.to_dict() for card in self.hand]
            # Also include tricks_won and discard_pile for persistence
            data["tricks_won"] = [card.to_dict() for card in self.tricks_won]
            data["discard_pile"] = [card.to_dict() for card in self.discard_pile]
            data["partner_revealed"] = self.partner_revealed

        return data

    def __str__(self) -> str:
        """String representation of player."""
        return f"{self.name} (pos {self.position})"

    def __repr__(self) -> str:
        """Representation for debugging."""
        return f"Player(id={self.id}, name={self.name}, position={self.position}, hand_size={len(self.hand)})"
