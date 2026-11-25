"""Four kings in hand: the player may throw the hand in until they play their first card."""

import pytest

from bots.strategy import decide_for_seat
from models.game_state import GamePhase

from tests.service_helpers import make_service, seed, table_of_four


async def drive_until(service, room, phase, max_actions=300):
    """Let every seat act (as the bots would) until the hand reaches this phase."""
    done = 0
    while room.game_state.phase != phase and done < max_actions:
        position = service.turn_position(room)
        player = room.game_state.get_player(position)
        await service.apply_decision(room, player, service.decide(room.game_state, position))
        done += 1
    assert room.game_state.phase == phase


def give_four_kings(gs, position):
    """Swap kings from the other hands into this seat's hand for non-king cards."""
    me = gs.players[position]
    for other in gs.players:
        if other.position == position:
            continue
        for king in [c for c in other.hand if c.is_king()]:
            mine = next(c for c in me.hand if not c.is_king() and not c.is_honour())
            other.hand.remove(king)
            me.hand.remove(mine)
            other.hand.append(mine)
            me.hand.append(king)
    assert sum(1 for c in me.hand if c.is_king()) == 4


async def started(phase):
    seed(7)
    service, manager, recorder = make_service(decide=decide_for_seat)
    room = table_of_four(manager)
    room.game_state.dealer_position = 0
    await service.start_game(room)
    await drive_until(service, room, phase)
    return service, room, recorder


@pytest.mark.asyncio
async def test_four_kings_throws_in_and_same_dealer_deals_again():
    service, room, recorder = await started(GamePhase.ANNOUNCEMENTS)
    gs = room.game_state
    give_four_kings(gs, 2)
    assert gs.can_throw_in(2)
    assert gs.to_dict(gs.players[2].id)["can_throw_in"] is True
    assert gs.to_dict(gs.players[1].id)["can_throw_in"] is False
    dealer, hand_number = gs.dealer_position, gs.hand_number

    await service.act_throw_in(room, gs.players[2])

    assert gs.phase == GamePhase.BIDDING
    assert (gs.dealer_position, gs.hand_number) == (dealer, hand_number)
    assert gs.declarer_position is None and gs.announcements == [] and gs.bid_history == []
    assert all(len(p.hand) == 9 and not p.discard_pile for p in gs.players)
    assert any(d and d.get("code") == "THROWN_IN" for d in recorder.of("game_state"))


@pytest.mark.asyncio
async def test_no_throw_in_without_four_kings():
    service, room, _ = await started(GamePhase.ANNOUNCEMENTS)
    gs = room.game_state
    seat = next(p for p in gs.players if sum(1 for c in p.hand if c.is_king()) < 4)
    with pytest.raises(ValueError):
        await service.act_throw_in(room, seat)
    assert gs.phase == GamePhase.ANNOUNCEMENTS


@pytest.mark.asyncio
async def test_throw_in_allowed_in_play_until_own_first_card():
    service, room, _ = await started(GamePhase.PLAYING)
    gs = room.game_state
    leader = gs.current_turn
    later = (leader + 1) % 4
    give_four_kings(gs, later)
    # The leader plays; the next seat has not played yet and may still throw in
    position = gs.current_turn
    await service.apply_decision(room, gs.players[position], service.decide(gs, position))
    assert gs.can_throw_in(later)
    # Once it has played its first card the chance is gone
    await service.apply_decision(room, gs.players[later], service.decide(gs, later))
    assert not gs.can_throw_in(later)
    with pytest.raises(ValueError):
        await service.act_throw_in(room, gs.players[later])


def test_not_before_own_skart():
    from models.game_state import GameState
    gs = GameState()
    gs.phase = GamePhase.BIDDING
    assert not gs.can_throw_in(0)
