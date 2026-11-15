"""Limits per visitor, the cap on open tables, the sweep of abandoned tables, and the all-or-nothing save."""

import sqlite3
import time

import pytest

from networking import server
from networking.limits import RateLimit, Refused, client_address
from networking.room_manager import WAITING_GRACE_SECONDS, RoomManager
from persistence.persistence_manager import PersistenceManager


def test_rate_limit_allows_a_burst_then_refuses_until_time_passes():
    limit = RateLimit(count=3, seconds=10)
    for second in (0, 1, 2):
        limit.check("a", now=second)
    with pytest.raises(Refused) as refused:
        limit.check("a", now=3)
    assert refused.value.code == "RATE_LIMITED"
    limit.check("b", now=3)      # another visitor is not affected
    limit.check("a", now=10.5)   # the first hit is older than the window


def test_rate_limit_forgets_idle_keys():
    limit = RateLimit(count=3, seconds=10)
    limit.check("a", now=0)
    limit.check("b", now=8)
    limit.prune(now=12)
    assert list(limit.hits) == ["b"]


def test_visitor_address_comes_from_the_ingress_header():
    assert client_address({"HTTP_X_FORWARDED_FOR": "84.1.2.3, 10.244.0.9", "REMOTE_ADDR": "10.244.0.9"}) == "84.1.2.3"
    assert client_address({"REMOTE_ADDR": "127.0.0.1"}) == "127.0.0.1"
    assert client_address({}) == "unknown"


@pytest.fixture
def fresh_server(monkeypatch):
    monkeypatch.setattr(server, "room_manager", RoomManager())
    monkeypatch.setattr(server, "new_table_limit", RateLimit(count=10, seconds=60))
    monkeypatch.setattr(server, "addresses", {})
    monkeypatch.setattr(server, "persistence_manager", None)
    return server


def test_no_new_table_when_the_server_is_full(fresh_server, monkeypatch):
    monkeypatch.setattr(server.settings, "max_rooms", 2)
    fresh_server.open_table("s1", "Anna")
    fresh_server.open_table("s2", "Bela")
    with pytest.raises(Refused) as refused:
        fresh_server.open_table("s3", "Csaba")
    assert refused.value.code == "ROOMS_FULL"
    assert len(fresh_server.room_manager.rooms) == 2


def test_one_address_cannot_open_tables_without_end(fresh_server):
    for i in range(12):
        fresh_server.addresses[f"s{i}"] = "84.1.2.3"   # new sockets, same visitor
    for i in range(10):
        fresh_server.open_table(f"s{i}", "Anna")
    with pytest.raises(Refused) as refused:
        fresh_server.open_table("s10", "Anna")
    assert refused.value.code == "RATE_LIMITED"
    fresh_server.addresses["other"] = "91.5.6.7"
    fresh_server.open_table("other", "Bela")


@pytest.mark.asyncio
async def test_error_message_carries_the_reason_of_a_refusal(fresh_server, monkeypatch):
    sent = []

    async def emit(event, data=None, room=None, **kwargs):
        sent.append((event, data))

    monkeypatch.setattr(server.sio, "emit", emit)
    await server.send_error("s1", "CREATE_ROOM_ERROR", Refused("ROOMS_FULL", "full"))
    await server.send_error("s1", "CREATE_ROOM_ERROR", ValueError("other"))
    codes = [str(data) for _, data in sent]
    assert "ROOMS_FULL" in codes[0] and "CREATE_ROOM_ERROR" in codes[1]


@pytest.mark.asyncio
async def test_sweep_closes_only_tables_nobody_sits_at(fresh_server):
    manager = fresh_server.room_manager
    lively = manager.create_room("s1", "Anna")
    just_dropped = manager.create_room("s2", "Bela")
    abandoned = manager.create_room("s3", "Csaba")
    for room in (lively, just_dropped, abandoned):
        room.fill_bots()

    manager.disconnect_session("s2")                       # dropped now: the seat is still held
    manager.disconnect_session("s3")
    abandoned.dropped_at[abandoned.humans()[0].id] = time.time() - WAITING_GRACE_SECONDS - 5

    assert await fresh_server.sweep() == 1
    assert set(manager.rooms) == {lively.room_id, just_dropped.room_id}


@pytest.mark.asyncio
async def test_a_save_is_stored_whole_or_not_at_all(tmp_path, monkeypatch):
    store = PersistenceManager(str(tmp_path / "t.db"))
    manager = RoomManager()
    room = manager.create_room("s1", "Anna")
    room.fill_bots()
    await store.save_room_complete(room)

    room.players[0].name = "Changed"

    def broken(*args, **kwargs):
        raise sqlite3.OperationalError("disk full")

    monkeypatch.setattr(store.db, "save_game_state", broken)
    await store.save_room_complete(room)   # fails half way; the error is logged, not raised

    names = [r["name"] for r in store.db.conn.execute("SELECT name FROM players ORDER BY position")]
    assert names[0] == "Anna"   # the player rows written before the failure were taken back
    assert store.db._in_transaction is False


@pytest.mark.asyncio
async def test_old_closed_tables_leave_the_database_with_all_their_rows(tmp_path):
    store = PersistenceManager(str(tmp_path / "c.db"))
    manager = RoomManager()
    old, closed_today, open_table = (manager.create_room(f"s{i}", "Anna") for i in range(3))
    for room in (old, closed_today, open_table):
        room.fill_bots()
        await store.save_room_complete(room)
        store.save_chat_message(room.room_id, {"id": room.room_id, "player_name": "Anna", "message": "szia", "timestamp": 1})
    await store.delete_room(old.room_id)
    await store.delete_room(closed_today.room_id)
    store.db.conn.execute("UPDATE rooms SET last_activity = datetime('now', '-9 days') WHERE room_id = ?", (old.room_id,))
    store.db.conn.commit()

    await store.cleanup_old_rooms(7)

    for table in ("rooms", "players", "game_states", "chat_messages"):
        left = {r[0] for r in store.db.conn.execute(f"SELECT DISTINCT room_id FROM {table}")}
        assert left == {closed_today.room_id, open_table.room_id}, table
