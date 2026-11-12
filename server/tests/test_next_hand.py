"""Next hand at the same table: rotating dealer, starter, running totals (design 9)."""

import pytest

from models.bid import Bid, BidType
from models.game_state import GamePhase

from tests.service_helpers import make_service, play_out_with_fallback, seed, table_of_four


async def to_bidding(dealer: int):
    service, manager, recorder = make_service()
    room = table_of_four(manager)
    room.game_state.dealer_position = dealer
    await service.start_game(room)
    return service, room, recorder


@pytest.mark.asyncio
@pytest.mark.parametrize("dealer", [0, 1, 2, 3])
async def test_first_bidder_and_first_leader_follow_dealer(dealer):
    """The seat after the dealer bids first and leads the first trick, whoever wins the bidding."""
    seed(dealer)
    service, room, _ = await to_bidding(dealer)
    gs = room.game_state
    starter = (dealer + 1) % 4
    assert gs.current_turn == starter

    # Make a seat other than the starter the declarer
    declarer = (dealer + 3) % 4
    gs.bid_history.clear()
    for seat in range(4):
        pos = (starter + seat) % 4
        gs.current_turn = pos
        gs.bid_history.append(Bid(
            player_position=pos, bid_type=BidType.THREE if pos == declarer else BidType.PASS))
    gs.end_bidding()
    assert gs.declarer_position == declarer
    await service._distribute_talon(room)
    await service.after_action(room)

    while gs.phase != GamePhase.PLAYING:
        position = service.turn_position(room)
        await service.apply_decision(room, gs.get_player(position), service.decide(gs, position))

    assert gs.trick_leader == starter
    assert gs.current_turn == starter


@pytest.mark.asyncio
async def test_dealer_rotates_and_totals_accumulate():
    seed(7)
    service, room, recorder = await to_bidding(dealer=0)
    gs = room.game_state
    await play_out_first_hand(service, room)

    assert gs.phase == GamePhase.GAME_END
    over = recorder.of("game_over")[-1]["data"]
    assert over["hand_number"] == 1
    assert sum(over["player_scores"].values()) == 200
    totals_after_one = [p.total_score for p in gs.players]
    assert totals_after_one == over["total_scores"]
    assert sum(totals_after_one) == 0

    for p in room.players:
        p.ready_next = True
    assert room.can_start_next_hand()
    await service.start_next_hand(room)

    assert gs.dealer_position == 1
    assert gs.hand_number == 2
    assert gs.phase == GamePhase.BIDDING
    assert gs.current_turn == 2
    assert all(len(p.hand) == 9 for p in gs.players)
    assert gs.trick_history == [] and gs.announcements == [] and gs.declarer_position is None
    assert [p.total_score for p in gs.players] == totals_after_one


async def play_out_first_hand(service, room):
    """Play with the fallback; if everyone passes the hand is redealt, so force a bid."""
    gs = room.game_state
    for _ in range(600):
        if gs.phase == GamePhase.GAME_END:
            return
        position = service.turn_position(room)
        player = gs.get_player(position)
        if gs.phase == GamePhase.BIDDING and player.has_honour() and gs.get_highest_bid() is None:
            await service.act_bid(room, player, BidType.THREE)
        else:
            await service.apply_decision(room, player, service.decide(gs, position))
    raise AssertionError("hand did not finish")


@pytest.mark.asyncio
async def test_next_hand_waits_for_all_humans():
    seed(3)
    service, room, _ = await to_bidding(dealer=0)
    await play_out_first_hand(service, room)
    players = room.players
    for p in players[:3]:
        p.ready_next = True
    assert not room.can_start_next_hand()
    players[3].ready_next = True
    assert room.can_start_next_hand()


@pytest.mark.asyncio
async def test_bots_do_not_block_next_hand():
    seed(4)
    service, manager, _ = make_service()
    room = manager.create_room("s0", "Anna")
    room.fill_bots()
    room.player_at(0).is_ready = True
    await service.start_game(room)
    await play_out_first_hand(service, room)
    assert not room.can_start_next_hand()
    room.player_at(0).ready_next = True
    assert room.can_start_next_hand()


@pytest.mark.asyncio
async def test_all_pass_keeps_dealer():
    seed(5)
    service, room, recorder = await to_bidding(dealer=2)
    gs = room.game_state
    first_game_id_hands = [tuple(c.id for c in p.hand) for p in gs.players]
    for _ in range(4):
        await service.act_bid(room, gs.get_player(gs.current_turn), BidType.PASS)
    assert gs.dealer_position == 2
    assert gs.hand_number == 1
    assert gs.phase == GamePhase.BIDDING
    assert gs.current_turn == 3
    assert [tuple(c.id for c in p.hand) for p in gs.players] != first_game_id_hands
    assert any(d.get("code") == "ALL_PASSED" for d in recorder.of("game_state"))
