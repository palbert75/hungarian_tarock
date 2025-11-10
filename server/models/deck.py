"""Deck model for Hungarian Tarokk - 42 card deck."""

import random
from typing import List
from pydantic import BaseModel

from models.card import Card, Suit, TarokkRank, SuitRank, CardType


class Deck(BaseModel):
    """
    Represents a 42-card Hungarian Tarokk deck (Industrie und Glück).

    Composition:
    - 22 Tarokk (trump) cards: skíz, XXI down to II, and pagát (I)
    - 20 Suit cards: 4 suits × 5 cards (K, Q, C, J, 10)

    Total points: 94
    """
    cards: List[Card] = []

    def __init__(self, **data):
        super().__init__(**data)
        if not self.cards:
            self.cards = self._generate_deck()

    def _generate_deck(self) -> List[Card]:
        """Generate a complete 42-card Hungarian Tarokk deck."""
        cards = []

        # Add 22 Tarokk cards
        cards.extend(self._generate_tarokk_cards())

        # Add 20 Suit cards (4 suits × 5 cards)
        for suit in [Suit.HEARTS, Suit.DIAMONDS, Suit.SPADES, Suit.CLUBS]:
            cards.extend(self._generate_suit_cards(suit))

        return cards

    def _generate_tarokk_cards(self) -> List[Card]:
        """Generate all 22 tarokk (trump) cards."""
        tarokk_cards = []

        # Honours (5 points each)
        honours = [
            (TarokkRank.SKIZ, 5, CardType.HONOUR),
            (TarokkRank.XXI, 5, CardType.HONOUR),
            (TarokkRank.PAGAT, 5, CardType.HONOUR),
        ]

        for rank, points, card_type in honours:
            tarokk_cards.append(Card(
                suit=Suit.TAROKK,
                rank=rank.value,
                points=points,
                card_type=card_type
            ))

        # Numbered tarokks (1 point each) - XX down to II
        numbered_tarokks = [
            TarokkRank.XX, TarokkRank.XIX, TarokkRank.XVIII, TarokkRank.XVII,
            TarokkRank.XVI, TarokkRank.XV, TarokkRank.XIV, TarokkRank.XIII,
            TarokkRank.XII, TarokkRank.XI, TarokkRank.X, TarokkRank.IX,
            TarokkRank.VIII, TarokkRank.VII, TarokkRank.VI, TarokkRank.V,
            TarokkRank.IV, TarokkRank.III, TarokkRank.II
        ]

        for rank in numbered_tarokks:
            tarokk_cards.append(Card(
                suit=Suit.TAROKK,
                rank=rank.value,
                points=1,
                card_type=CardType.TAROKK
            ))

        return tarokk_cards

    def _generate_suit_cards(self, suit: Suit) -> List[Card]:
        """Generate 5 cards for a given suit."""
        suit_cards = []

        suit_ranks = [
            (SuitRank.KING, 5, CardType.KING),
            (SuitRank.QUEEN, 4, CardType.SUIT),
            (SuitRank.CAVALIER, 3, CardType.SUIT),
            (SuitRank.JACK, 2, CardType.SUIT),
            (SuitRank.TEN, 1, CardType.SUIT),
        ]

        for rank, points, card_type in suit_ranks:
            suit_cards.append(Card(
                suit=suit,
                rank=rank.value,
                points=points,
                card_type=card_type
            ))

        return suit_cards

    def shuffle(self) -> None:
        """Shuffle the deck."""
        random.shuffle(self.cards)

    def deal(self, num_cards: int) -> List[Card]:
        """
        Deal a specified number of cards from the top of the deck.

        Args:
            num_cards: Number of cards to deal

        Returns:
            List of dealt cards

        Raises:
            ValueError: If not enough cards in deck
        """
        if num_cards > len(self.cards):
            raise ValueError(f"Not enough cards in deck. Requested: {num_cards}, Available: {len(self.cards)}")

        dealt = self.cards[:num_cards]
        self.cards = self.cards[num_cards:]
        return dealt

    def remaining_cards(self) -> int:
        """Get the number of cards remaining in the deck."""
        return len(self.cards)

    def reset(self) -> None:
        """Reset the deck to a fresh 42-card state."""
        self.cards = self._generate_deck()

    def validate_deck(self) -> bool:
        """
        Validate that the deck has exactly 42 cards and totals 94 points.

        Returns:
            True if valid, False otherwise
        """
        if len(self.cards) != 42:
            return False

        total_points = sum(card.points for card in self.cards)
        if total_points != 94:
            return False

        # Check for 22 tarokks
        tarokk_count = sum(1 for card in self.cards if card.is_tarokk())
        if tarokk_count != 22:
            return False

        # Check for 20 suit cards (5 per suit)
        for suit in [Suit.HEARTS, Suit.DIAMONDS, Suit.SPADES, Suit.CLUBS]:
            suit_count = sum(1 for card in self.cards if card.suit == suit)
            if suit_count != 5:
                return False

        return True

    @classmethod
    def create_and_shuffle(cls) -> "Deck":
        """Create a new deck and shuffle it."""
        deck = cls()
        deck.shuffle()
        return deck
