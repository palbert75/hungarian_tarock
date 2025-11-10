"""Tests for game rules validation."""

import pytest
from server.models.card import Card, Suit, TarokkRank, SuitRank, CardType
from server.validation.rules import (
    get_legal_cards,
    validate_play,
    validate_discard,
    has_honour,
    has_trull,
    has_four_kings
)


def create_card(suit: Suit, rank: str, points: int, card_type: CardType) -> Card:
    """Helper to create a card."""
    return Card(suit=suit, rank=rank, points=points, card_type=card_type)


def test_get_legal_cards_leading():
    """Test legal cards when leading (first card)."""
    hand = [
        create_card(Suit.HEARTS, "K", 5, CardType.KING),
        create_card(Suit.DIAMONDS, "Q", 4, CardType.SUIT),
        create_card(Suit.TAROKK, TarokkRank.XXI.value, 5, CardType.HONOUR),
    ]

    legal = get_legal_cards(hand, Suit.HEARTS, is_first_card=True)

    # When leading, all cards are legal
    assert len(legal) == 3


def test_get_legal_cards_must_follow_suit():
    """Test must follow suit when able."""
    hand = [
        create_card(Suit.HEARTS, "K", 5, CardType.KING),
        create_card(Suit.HEARTS, "Q", 4, CardType.SUIT),
        create_card(Suit.DIAMONDS, "J", 2, CardType.SUIT),
    ]

    legal = get_legal_cards(hand, Suit.HEARTS, is_first_card=False)

    # Must play hearts
    assert len(legal) == 2
    assert all(c.suit == Suit.HEARTS for c in legal)


def test_get_legal_cards_must_play_tarokk_if_void():
    """Test must play tarokk when void in lead suit."""
    hand = [
        create_card(Suit.DIAMONDS, "K", 5, CardType.KING),
        create_card(Suit.TAROKK, TarokkRank.XXI.value, 5, CardType.HONOUR),
        create_card(Suit.TAROKK, TarokkRank.X.value, 1, CardType.TAROKK),
    ]

    legal = get_legal_cards(hand, Suit.HEARTS, is_first_card=False)

    # Void in hearts: must play tarokk
    assert len(legal) == 2
    assert all(c.is_tarokk() for c in legal)


def test_get_legal_cards_void_in_suit_and_tarokk():
    """Test can play any card when void in both lead suit and tarokk."""
    hand = [
        create_card(Suit.DIAMONDS, "K", 5, CardType.KING),
        create_card(Suit.CLUBS, "Q", 4, CardType.SUIT),
        create_card(Suit.SPADES, "J", 2, CardType.SUIT),
    ]

    legal = get_legal_cards(hand, Suit.HEARTS, is_first_card=False)

    # Void in hearts and no tarokk: can play anything
    assert len(legal) == 3


def test_validate_discard_cannot_discard_kings():
    """Test cannot discard Kings."""
    cards = [
        create_card(Suit.HEARTS, "K", 5, CardType.KING)
    ]

    is_valid, error = validate_discard(cards)

    assert is_valid is False
    assert "King" in error


def test_validate_discard_cannot_discard_honours():
    """Test cannot discard Honours."""
    cards = [
        create_card(Suit.TAROKK, TarokkRank.SKIZ.value, 5, CardType.HONOUR)
    ]

    is_valid, error = validate_discard(cards)

    assert is_valid is False
    assert "Honour" in error


def test_validate_discard_valid():
    """Test valid discard."""
    cards = [
        create_card(Suit.HEARTS, "Q", 4, CardType.SUIT),
        create_card(Suit.TAROKK, TarokkRank.X.value, 1, CardType.TAROKK)
    ]

    is_valid, error = validate_discard(cards)

    assert is_valid is True


def test_has_honour():
    """Test detecting honour in hand."""
    hand = [
        create_card(Suit.TAROKK, TarokkRank.XXI.value, 5, CardType.HONOUR),
        create_card(Suit.HEARTS, "K", 5, CardType.KING),
    ]

    assert has_honour(hand) is True


def test_has_no_honour():
    """Test detecting no honour in hand."""
    hand = [
        create_card(Suit.TAROKK, TarokkRank.X.value, 1, CardType.TAROKK),
        create_card(Suit.HEARTS, "K", 5, CardType.KING),
    ]

    assert has_honour(hand) is False


def test_has_trull():
    """Test detecting trull (all 3 honours)."""
    hand = [
        create_card(Suit.TAROKK, TarokkRank.SKIZ.value, 5, CardType.HONOUR),
        create_card(Suit.TAROKK, TarokkRank.XXI.value, 5, CardType.HONOUR),
        create_card(Suit.TAROKK, TarokkRank.PAGAT.value, 5, CardType.HONOUR),
    ]

    assert has_trull(hand) is True


def test_has_four_kings():
    """Test detecting all four Kings."""
    hand = [
        create_card(Suit.HEARTS, "K", 5, CardType.KING),
        create_card(Suit.DIAMONDS, "K", 5, CardType.KING),
        create_card(Suit.SPADES, "K", 5, CardType.KING),
        create_card(Suit.CLUBS, "K", 5, CardType.KING),
    ]

    assert has_four_kings(hand) is True
