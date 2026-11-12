"""Four bots play whole hands through the same actions people use."""

import pytest

from bots.strategy import decide, decide_for_seat
from bots.view import build_view
from models.game_state import GamePhase
from tests.service_helpers import make_service, seed


def strict(game_state, position):
    """No fallback: a failing rule must fail the test."""
    return decide(build_view(game_state, position))


@pytest.mark.asyncio
async def test_bot_simulation():
    hands_played = 0
    for n in range(300):
        seed(n)
        service, manager, recorder = make_service(decide=strict)
        room = manager.create_room("s0", "Anna")
        room.fill_bots()
        room.players[0].is_ready = True
        await service.start_game(room)

        actions = 0
        while room.game_state.phase != GamePhase.GAME_END:
            position = service.turn_position(room)
            player = room.game_state.get_player(position)
            await service.apply_decision(room, player, strict(room.game_state, position))
            actions += 1
            assert actions <= 200, f"seed {n}: hand did not finish"

        result = recorder.of("game_over")[-1]
        result = result.get("data", result)
        assert result["declarer_team_points"] + result["opponent_team_points"] == 94, f"seed {n}"
        assert sum(result["player_scores"].values()) == 200, f"seed {n}"
        hands_played += 1
    assert hands_played == 300


def test_decide_for_seat_matches_decide():
    seed(7)
    from tests.helpers import make_state
    gs = make_state(["XXI XX X hK", "skiz II", "I III", "IV V"], dealer=3)
    gs.start_bidding()
    assert decide_for_seat(gs, 0).to_dict() == strict(gs, 0).to_dict()
