"""The rest of the talon goes to the defenders in playing order from the seat after the declarer."""

import pytest

from models.bid import Bid, BidType
from models.game_state import GameState
from models.player import Player


def table(declarer: int, bid: BidType) -> GameState:
    gs = GameState()
    for i in range(4):
        gs.add_player(Player(id=f"p{i}", name=f"P{i}", position=i))
    gs.dealer_position = 0
    gs.start_dealing()
    gs.winning_bid = Bid(player_position=declarer, bid_type=bid)
    gs.declarer_position = declarer
    return gs


@pytest.mark.parametrize("declarer", [0, 1, 2, 3])
def test_two_gives_the_extra_card_to_the_seat_after_the_declarer(declarer):
    gs = table(declarer, BidType.TWO)
    counts = {pos: len(cards) for pos, cards in gs.distribute_talon().items()}
    assert counts[declarer] == 2
    assert counts[(declarer + 1) % 4] == 2
    assert counts[(declarer + 2) % 4] == 1
    assert counts[(declarer + 3) % 4] == 1


@pytest.mark.parametrize("declarer", [0, 1, 2, 3])
def test_one_shorts_the_last_seat_before_the_declarer(declarer):
    gs = table(declarer, BidType.ONE)
    counts = {pos: len(cards) for pos, cards in gs.distribute_talon().items()}
    assert [counts[(declarer + k) % 4] for k in range(4)] == [1, 2, 2, 1]
