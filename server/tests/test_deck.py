"""Tests for deck model."""

import pytest
from server.models.deck import Deck
from server.models.card import Suit


def test_deck_creation():
    """Test deck is created with 42 cards."""
    deck = Deck()
    assert len(deck.cards) == 42


def test_deck_validation():
    """Test deck validation."""
    deck = Deck()
    assert deck.validate_deck() is True


def test_deck_total_points():
    """Test deck has 94 total points."""
    deck = Deck()
    total_points = sum(card.points for card in deck.cards)
    assert total_points == 94


def test_deck_composition():
    """Test deck has correct composition."""
    deck = Deck()

    # Count tarokks
    tarokks = [c for c in deck.cards if c.is_tarokk()]
    assert len(tarokks) == 22

    # Count honours
    honours = [c for c in deck.cards if c.is_honour()]
    assert len(honours) == 3

    # Count each suit
    for suit in [Suit.HEARTS, Suit.DIAMONDS, Suit.SPADES, Suit.CLUBS]:
        suit_cards = [c for c in deck.cards if c.suit == suit]
        assert len(suit_cards) == 5

    # Count kings
    kings = [c for c in deck.cards if c.is_king()]
    assert len(kings) == 4


def test_deck_shuffle():
    """Test deck shuffling."""
    deck1 = Deck()
    deck2 = Deck()

    # Get card IDs in order
    deck1_order = [c.id for c in deck1.cards]
    deck2_order = [c.id for c in deck2.cards]

    # Before shuffle, decks should have different card IDs but same structure
    assert deck1_order != deck2_order  # Different IDs

    # Shuffle
    deck1.shuffle()

    # After shuffle, order should be different
    deck1_shuffled = [c.id for c in deck1.cards]
    # Note: Very small chance this could fail if shuffle results in same order
    assert deck1_shuffled != deck1_order or len(deck1_order) == 0


def test_deck_deal():
    """Test dealing cards."""
    deck = Deck()
    initial_count = deck.remaining_cards()

    dealt = deck.deal(5)

    assert len(dealt) == 5
    assert deck.remaining_cards() == initial_count - 5


def test_deck_deal_too_many():
    """Test dealing more cards than available."""
    deck = Deck()
    deck.deal(40)

    with pytest.raises(ValueError):
        deck.deal(5)


def test_deck_reset():
    """Test deck reset."""
    deck = Deck()
    deck.deal(20)

    assert deck.remaining_cards() == 22

    deck.reset()

    assert deck.remaining_cards() == 42
    assert deck.validate_deck() is True
