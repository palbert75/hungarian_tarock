"""Problem reports: the whole table with the reporter's text."""

import json

import pytest

from models.game_state import GamePhase
from networking.reports import ReportThrottle, build_report, may_return_to_reporter, save_report
from tests.service_helpers import make_service, seed


async def table_in_play(with_person=False):
    seed(3)
    service, manager, recorder = make_service()
    room = manager.create_room("s0", "Anna")
    if with_person:
        manager.join_room(room.room_id, "s1", "Bela")
    room.fill_bots()
    for p in room.players:
        p.is_ready = True
    await service.start_game(room)
    await service.drive_bots(room)
    return service, room


@pytest.mark.asyncio
async def test_report_holds_every_hand_the_text_and_bot_reasons(tmp_path):
    service, room = await table_in_play()
    me = room.players[0]
    report = build_report(room, me, "  Bot Kati led a tarokk with the skíz  ", {"language": "hu"})
    assert report["text"] == "Bot Kati led a tarokk with the skíz"
    assert report["reporter"] == {"position": 0, "name": "Anna"}
    assert all("hand" in p for p in report["game"]["players"])
    assert report["client"] == {"language": "hu"}
    if any(p.bot_controlled for p in room.players) and room.decision_log:
        entry = report["bot_decisions"][0]
        assert entry["reason_key"].startswith("hint.") and "action" in entry and "position" in entry
    path = save_report(report, tmp_path)
    assert json.loads(path.read_text(encoding="utf-8"))["id"] == report["id"]


@pytest.mark.asyncio
async def test_bot_decisions_are_logged_and_cleared_for_the_next_hand():
    service, room = await table_in_play()
    # Play my seat with the same rules until the hand ends
    from bots.strategy import decide_for_seat
    while room.game_state.phase != GamePhase.GAME_END:
        position = service.turn_position(room)
        await service.apply_decision(room, room.game_state.get_player(position), decide_for_seat(room.game_state, position))
        await service.drive_bots(room)
    assert len(room.decision_log) > 20
    assert {d["position"] for d in room.decision_log} <= {1, 2, 3}
    await service.start_next_hand(room)
    assert all(d["hand_number"] == room.game_state.hand_number for d in room.decision_log)


def test_empty_or_long_text_is_refused():
    seed(1)
    service, manager, recorder = make_service()
    room = manager.create_room("s0", "Anna")
    with pytest.raises(ValueError):
        build_report(room, room.players[0], "   ")
    with pytest.raises(ValueError):
        build_report(room, room.players[0], "x" * 2001)


@pytest.mark.asyncio
async def test_report_goes_back_only_when_it_cannot_help_cheating():
    service, room = await table_in_play()
    assert may_return_to_reporter(room, room.players[0]) is True  # only bots beside me
    service, room = await table_in_play(with_person=True)
    if room.game_state.phase not in (GamePhase.GAME_END, GamePhase.SCORING, GamePhase.WAITING):
        assert may_return_to_reporter(room, room.players[0]) is False
    room.game_state.phase = GamePhase.GAME_END
    assert may_return_to_reporter(room, room.players[0]) is True


def test_throttle():
    throttle = ReportThrottle(seconds=60)
    throttle.check("p1")
    with pytest.raises(ValueError):
        throttle.check("p1")
    throttle.check("p2")
