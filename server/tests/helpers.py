"""Shared helpers for building game states in tests."""

from typing import List, Optional

from models.card import Card, CardType, Suit
from models.game_state import GameState, GamePhase
from models.player import Player

TAROKK_POINTS = {"skiz": 5, "XXI": 5, "I": 5}
SUIT_POINTS = {"K": 5, "Q": 4, "C": 3, "J": 2, "10": 1}
SUITS = {"h": Suit.HEARTS, "d": Suit.DIAMONDS, "s": Suit.SPADES, "c": Suit.CLUBS}


def card(code: str) -> Card:
    """Build a card from a short code: 'skiz', 'XXI', 'XX', 'I' or 'hK', 's10', 'dQ'."""
    if code[0] in SUITS and code[1:] in SUIT_POINTS:
        rank = code[1:]
        return Card(
            suit=SUITS[code[0]],
            rank=rank,
            points=SUIT_POINTS[rank],
            card_type=CardType.KING if rank == "K" else CardType.SUIT,
        )
    is_honour = code in TAROKK_POINTS
    return Card(
        suit=Suit.TAROKK,
        rank=code,
        points=TAROKK_POINTS.get(code, 1),
        card_type=CardType.HONOUR if is_honour else CardType.TAROKK,
    )


def cards(codes: str) -> List[Card]:
    return [card(c) for c in codes.split()]


def make_state(hands: Optional[List[str]] = None, dealer: int = 0) -> GameState:
    """Four players; hands given as space separated codes per seat."""
    gs = GameState()
    for i in range(4):
        gs.add_player(Player(name=f"P{i}", position=i))
    gs.dealer_position = dealer
    if hands:
        for i, h in enumerate(hands):
            gs.players[i].add_cards_to_hand(cards(h))
    return gs


def bidding_state(honour_seats=(0, 1, 2, 3), dealer: int = 3) -> GameState:
    """State in BIDDING where the given seats hold an honour. Seat 0 bids first by default."""
    honours = ["skiz", "XXI", "I", "skiz"]
    hands = []
    for i in range(4):
        hands.append(honours[i] if i in honour_seats else "hK")
    gs = make_state(hands, dealer=dealer)
    gs.start_bidding()
    return gs
