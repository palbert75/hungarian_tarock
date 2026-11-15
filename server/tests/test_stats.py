"""Statistics: every finished hand leaves one row, and /stats sums them up per day."""

import json
import time

import pytest

from bots.strategy import decide_for_seat
from models.game_state import GamePhase
from networking.actions import GameService
from networking.room_manager import RoomManager
from persistence.persistence_manager import PersistenceManager
from persistence.stats import summarize
from tests.service_helpers import Recorder, play_out_with_fallback, seed


def service_with_stats(tmp_path):
    store = PersistenceManager(str(tmp_path / "stats.db"))
    manager = RoomManager()
    service = GameService(manager, Recorder(), decide=decide_for_seat, record_hand=store.record_hand)
    service.redeal_pause = service.trick_pause = 0
    service.auto_bots = False
    return service, manager, store


async def play_hands(service, room, hands: int) -> None:
    for p in room.humans():
        p.is_ready = True
    await service.start_game(room)
    await play_out_with_fallback(service, room)
    for _ in range(hands - 1):
        await service.start_next_hand(room)
        await play_out_with_fallback(service, room)
    assert room.game_state.phase == GamePhase.GAME_END


@pytest.mark.asyncio
async def test_every_finished_hand_leaves_one_row(tmp_path):
    seed(3)
    service, manager, store = service_with_stats(tmp_path)
    room = manager.create_room("s0", "Anna")
    manager.join_room(room.room_id, "s1", "Béla")
    room.fill_bots()
    await play_hands(service, room, 3)

    rows = store.db.load_hands_since(0)
    assert [r["hand_number"] for r in rows] == [1, 2, 3]
    row = rows[-1]
    assert (row["people"], row["bots"]) == (2, 2)
    assert json.loads(row["player_names"]) == ["Anna", "Béla"]
    assert row["room_id"] == room.room_id
    assert row["bid"] in ("three", "two", "one", "solo")
    assert row["winner"] == room.last_game_over["winner"]
    assert row["declarer_team_points"] == room.last_game_over["declarer_team_points"]
    assert row["duration_seconds"] is not None
    assert abs(row["finished_at"] - time.time()) < 5


@pytest.mark.asyncio
async def test_hands_stay_when_the_table_is_deleted(tmp_path):
    seed(4)
    service, manager, store = service_with_stats(tmp_path)
    room = manager.create_room("s0", "Anna")
    room.fill_bots()
    await play_hands(service, room, 1)
    await store.save_room_complete(room)
    await store.delete_room(room.room_id)
    store.db.hard_delete_room(room.room_id)
    assert len(store.db.load_hands_since(0)) == 1


@pytest.mark.asyncio
async def test_a_failing_statistic_does_not_stop_the_game(tmp_path):
    seed(5)
    service, manager, store = service_with_stats(tmp_path)
    store.db.conn.execute("DROP TABLE hands")
    room = manager.create_room("s0", "Anna")
    room.fill_bots()
    await play_hands(service, room, 1)
    assert room.last_game_over is not None


def hand(day_offset: float, room: str, names, now: float, minutes: int = 4) -> dict:
    return {"finished_at": int(now - day_offset * 86400), "room_id": room, "people": len(names),
            "player_names": json.dumps(names), "duration_seconds": minutes * 60}


def test_summary_counts_hands_tables_and_people_per_day():
    now = 1794830400  # 2026-11-16 12:00 UTC, 13:00 in Budapest
    rows = [
        hand(0, "t1", ["Albi"], now), hand(0, "t1", ["Albi"], now, minutes=6), hand(0, "t2", ["Robi", "Bertike"], now),
        hand(1, "t1", ["Albi"], now),
        hand(5, "t9", ["Zoli"], now),  # older than the days asked for
    ]
    result = summarize(rows, days=3, now=now)
    assert result["total"] == {"hands": 4, "tables": 2, "people": 3}
    today, yesterday, before = result["per_day"]
    assert today["day"] == "2026-11-16"
    assert (today["hands"], today["tables"], today["people"]) == (3, 2, 3)
    assert today["player_names"] == ["Albi", "Bertike", "Robi"]
    assert today["hands_with_two_or_more_people"] == 1
    assert today["median_hand_minutes"] == 4.0
    assert (yesterday["day"], yesterday["hands"]) == ("2026-11-15", 1)
    assert (before["day"], before["hands"], before["median_hand_minutes"]) == ("2026-11-14", 0, None)


def test_a_hand_just_after_midnight_in_budapest_counts_for_the_new_day():
    now = 1794830400
    late = {"finished_at": 1794785400, "room_id": "t", "people": 1,  # 2026-11-15 23:30 UTC = 16th 00:30 in Budapest
            "player_names": "[]", "duration_seconds": None}
    assert summarize([late], days=2, now=now)["per_day"][0]["hands"] == 1


class FakeRequest:
    def __init__(self, authorization=None):
        self.headers = {"authorization": authorization} if authorization else {}


async def status_of(main, request) -> int:
    from fastapi import HTTPException
    try:
        await main.played_hands(request, days=7)
    except HTTPException as e:
        return e.status_code
    return 200


@pytest.mark.asyncio
async def test_stats_endpoint_needs_the_token(tmp_path, monkeypatch):
    import main
    from networking import server

    monkeypatch.setattr(server, "persistence_manager", PersistenceManager(str(tmp_path / "e.db")))

    monkeypatch.setattr(main.settings, "stats_token", None)
    assert await status_of(main, FakeRequest("Bearer anything")) == 404  # no token set: the page does not exist

    monkeypatch.setattr(main.settings, "stats_token", "titok")
    assert await status_of(main, FakeRequest()) == 401
    assert await status_of(main, FakeRequest("Bearer wrong")) == 401
    assert await status_of(main, FakeRequest("titok")) == 401

    body = await main.played_hands(FakeRequest("Bearer titok"), days=7)
    assert len(body["per_day"]) == 7 and body["total"]["hands"] == 0
    assert body["now"] == {"tables_with_people": 0, "people_connected": 0, "tables_in_a_hand": 0}
