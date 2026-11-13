"""Declaring eight or nine tarokks: every other player pays the declarer 1 or 2 points."""
import pytest

from bots import strategy
from bots.strategy import decide_announcement
from bots.view import build_view
from models.game_state import GamePhase, settle_tarokk_declarations
from tests.helpers import make_state
from tests.service_helpers import make_service, seed

EIGHT = "XX XIX X IX VIII VII VI V hK"
NINE = "XX XIX X IX VIII VII VI V IV"
SEVEN = "XX XIX X IX VIII VII VI hK hQ"


def announcing(hands):
    gs = make_state(hands)
    gs.declarer_position = 0
    gs.called_card_rank = "XX"
    gs.start_announcement_phase()
    return gs


def test_declaration_is_open_only_with_exactly_that_many_tarokks():
    gs = announcing([EIGHT, NINE, SEVEN, "hJ"])
    assert gs.tarokk_declaration_open(0) == "eight_tarokks"
    assert gs.tarokk_declaration_open(1) == "nine_tarokks"
    assert gs.tarokk_declaration_open(2) is None
    with pytest.raises(ValueError):
        gs.declare_tarokks(2, "eight_tarokks")
    with pytest.raises(ValueError):
        gs.declare_tarokks(1, "eight_tarokks")      # nine in hand is not eight
    gs.declare_tarokks(0, "eight_tarokks")
    assert gs.tarokk_declarations == {0: 8}
    assert gs.tarokk_declaration_open(0) is None     # only once
    assert gs.to_dict()["tarokk_declarations"] == {"0": 8}


def test_every_other_player_pays_one_for_eight_and_two_for_nine():
    scores = {0: 50, 1: 50, 2: 50, 3: 50}
    lines = settle_tarokk_declarations({0: 8, 2: 9}, scores)
    assert scores == {0: 50 + 3 - 2, 1: 50 - 1 - 2, 2: 50 + 6 - 1, 3: 50 - 1 - 2}
    assert sum(scores.values()) == 200
    assert lines == [{"player_position": 0, "count": 8, "points": 1},
                     {"player_position": 2, "count": 9, "points": 2}]


def test_bot_declares_its_tarokks_on_either_side():
    gs = announcing([SEVEN, "hJ", "XIX XVIII X IX VIII VII VI V IV", "hQ"])
    view = build_view(gs, 2)                         # a defender
    assert "nine_tarokks" in view.valid_announcements
    d = decide_announcement(view)
    assert d.action == "announce" and d.payload["announcement_types"] == ["nine_tarokks"]
    assert d.reason_key == "hint.announce.tarokks"


async def play_hand(n):
    seed(n)
    decide = lambda game_state, position: strategy.decide(build_view(game_state, position))
    service, manager, rec = make_service(decide=decide)
    room = manager.create_room("s0", "Anna")
    room.fill_bots()
    room.players[0].is_ready = True
    await service.start_game(room)
    for _ in range(400):
        if room.game_state.phase == GamePhase.GAME_END:
            break
        position = service.turn_position(room)
        await service.apply_decision(room, room.game_state.get_player(position), decide(room.game_state, position))
    result = rec.of("game_over")[-1]
    return room, rec, result.get("data", result)


@pytest.mark.asyncio
async def test_declaration_is_paid_at_the_end_of_the_hand():
    for n in range(200):
        room, rec, result = await play_hand(n)
        lines = result["tarokk_declarations"]
        scores = {int(k): v for k, v in result["player_scores"].items()}
        assert sum(scores.values()) == 200
        if lines:
            break
    else:
        pytest.fail("no declaration in 200 hands")
    made = [m.get("data", m) for m in rec.of("announcement_made")]
    assert any(m["announcement_type"] in ("eight_tarokks", "nine_tarokks") for m in made)
    # Without the declarations the same hand scores differently by exactly the payments
    plain = dict(scores)
    for line in lines:
        for seat in plain:
            plain[seat] += line["points"] if seat != line["player_position"] else -3 * line["points"]
    assert sum(plain.values()) == 200 and plain != scores
