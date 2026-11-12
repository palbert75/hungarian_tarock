"""Counting tarokks: which ones can still be in another hand."""

from typing import List

from models.card import Card
from bots.view import SeatView

SKIZ, XXI, PAGAT = 22, 21, 1


def played_cards(view: SeatView) -> List[Card]:
    done = [card for trick in view.trick_history for _, card in trick]
    return done + [card for _, card in view.current_trick]


def tarokks_out(view: SeatView) -> List[int]:
    """Tarokk values that are not in my hand, not in my skart and not yet played, highest first."""
    seen = {c.tarokk_value() for c in view.hand + view.own_discards + played_cards(view) if c.is_tarokk()}
    return [value for value in range(SKIZ, 0, -1) if value not in seen]


def skiz_out(view: SeatView) -> bool:
    return SKIZ in tarokks_out(view)


def xxi_out(view: SeatView) -> bool:
    return XXI in tarokks_out(view)


def xxi_played(view: SeatView) -> bool:
    return any(c.is_tarokk() and c.tarokk_value() == XXI for c in played_cards(view))


def observed_voids(view: SeatView) -> set:
    """(seat, suit) pairs proven by a player failing to follow the suit led."""
    out = set()
    for trick in view.trick_history + ([view.current_trick] if view.current_trick else []):
        led = trick[0][1].suit
        for seat, card in trick[1:]:
            if card.suit != led:
                out.add((seat, led))
    return out
