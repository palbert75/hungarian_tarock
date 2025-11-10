"""Tests for bidding logic."""

import pytest
from server.models.player import Player
from server.models.card import Card, Suit, TarokkRank, CardType
from server.models.bid import Bid, BidType
from server.game_logic.bidding import BiddingManager


def create_player_with_honour():
    """Create a player with an honour card."""
    player = Player(name="Test", position=0)
    # Add skíz (honour)
    player.add_cards_to_hand([
        Card(suit=Suit.TAROKK, rank=TarokkRank.SKIZ.value, points=5, card_type=CardType.HONOUR)
    ])
    return player


def create_player_without_honour():
    """Create a player without honour cards."""
    player = Player(name="Test", position=0)
    # Add non-honour cards
    player.add_cards_to_hand([
        Card(suit=Suit.HEARTS, rank="K", points=5, card_type=CardType.KING),
        Card(suit=Suit.TAROKK, rank=TarokkRank.X.value, points=1, card_type=CardType.TAROKK)
    ])
    return player


def test_can_bid_with_honour():
    """Test player with honour can bid."""
    player = create_player_with_honour()
    can_bid, error = BiddingManager.can_player_bid(player, BidType.THREE, [])

    assert can_bid is True
    assert error == "OK"


def test_cannot_bid_without_honour():
    """Test player without honour cannot bid."""
    player = create_player_without_honour()
    can_bid, error = BiddingManager.can_player_bid(player, BidType.THREE, [])

    assert can_bid is False
    assert "honour" in error.lower()


def test_can_always_pass():
    """Test player can always pass."""
    player = create_player_without_honour()
    can_bid, error = BiddingManager.can_player_bid(player, BidType.PASS, [])

    assert can_bid is True


def test_bid_must_be_higher():
    """Test bid must be higher than current highest."""
    player = create_player_with_honour()
    bid_history = [
        Bid(player_position=1, bid_type=BidType.TWO)
    ]

    # Try to bid THREE (lower than TWO)
    can_bid, error = BiddingManager.can_player_bid(player, BidType.THREE, bid_history)

    assert can_bid is False
    assert "higher" in error.lower()


def test_hold_requires_previous_bid():
    """Test HOLD requires player to have bid before."""
    player = create_player_with_honour()
    bid_history = [
        Bid(player_position=1, bid_type=BidType.THREE)
    ]

    # Try to HOLD without having bid before
    can_bid, error = BiddingManager.can_player_bid(player, BidType.HOLD, bid_history)

    assert can_bid is False
    assert "already bid" in error.lower()


def test_hold_allowed_after_bidding():
    """Test HOLD is allowed after player has bid."""
    player = create_player_with_honour()
    bid_history = [
        Bid(player_position=0, bid_type=BidType.THREE),  # Player's bid
        Bid(player_position=1, bid_type=BidType.TWO),    # Higher bid
    ]

    can_bid, error = BiddingManager.can_player_bid(player, BidType.HOLD, bid_history)

    assert can_bid is True


def test_get_highest_bid():
    """Test getting highest bid."""
    bid_history = [
        Bid(player_position=0, bid_type=BidType.THREE),
        Bid(player_position=1, bid_type=BidType.PASS),
        Bid(player_position=2, bid_type=BidType.TWO),
    ]

    highest = BiddingManager.get_highest_bid(bid_history)

    assert highest is not None
    assert highest.bid_type == BidType.TWO


def test_auction_complete_solo():
    """Test auction completes on SOLO bid."""
    bid_history = [
        Bid(player_position=0, bid_type=BidType.THREE),
        Bid(player_position=1, bid_type=BidType.SOLO),
    ]

    assert BiddingManager.is_auction_complete(bid_history) is True


def test_auction_complete_all_pass():
    """Test auction completes when all pass."""
    bid_history = [
        Bid(player_position=0, bid_type=BidType.PASS),
        Bid(player_position=1, bid_type=BidType.PASS),
        Bid(player_position=2, bid_type=BidType.PASS),
        Bid(player_position=3, bid_type=BidType.PASS),
    ]

    assert BiddingManager.is_auction_complete(bid_history) is True


def test_auction_complete_three_passes_after_bid():
    """Test auction completes after 3 consecutive passes following a bid."""
    bid_history = [
        Bid(player_position=0, bid_type=BidType.THREE),
        Bid(player_position=1, bid_type=BidType.PASS),
        Bid(player_position=2, bid_type=BidType.PASS),
        Bid(player_position=3, bid_type=BidType.PASS),
    ]

    assert BiddingManager.is_auction_complete(bid_history) is True


def test_get_declarer():
    """Test getting declarer position."""
    bid_history = [
        Bid(player_position=0, bid_type=BidType.THREE),
        Bid(player_position=1, bid_type=BidType.TWO),
        Bid(player_position=2, bid_type=BidType.PASS),
    ]

    declarer = BiddingManager.get_declarer_position(bid_history)

    assert declarer == 1  # Player 1 had highest bid (TWO)
