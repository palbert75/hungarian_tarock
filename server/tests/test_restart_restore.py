"""A server restart must not end a game: every table comes back exactly as it was saved."""

import copy
import json
import random

import pytest

from bots.strategy import decide_for_seat
from models.game_state import GamePhase
from networking.room_manager import RoomManager
from persistence.persistence_manager import PersistenceManager
from tests.service_helpers import make_service, seed


def saved_form(room) -> dict:
    """Everything a table needs after a restart."""
    # As JSON, which is how it is stored and how it goes to the clients
    return json.loads(json.dumps(_form(room)))


def _form(room) -> dict:
    return {
        "game": room.game_state.to_dict(include_all_hands=True),
        "owner_id": room.owner_id,
        "bot_speed": room.bot_speed,
        "last_game_over": room.last_game_over,
        "decision_log": room.decision_log,
        "hand_started_at": room.hand_started_at,
        "seats": [[p.id, p.name, p.position, p.is_bot, p.bot_controlled, p.vacant] for p in room.players],
    }


async def restart(room, tmp_path, name: str):
    """Save the table, then load it into a server that knows nothing."""
    store = PersistenceManager(str(tmp_path / f"{name}.db"))
    await store.save_room_complete(room)
    store.close()

    store = PersistenceManager(str(tmp_path / f"{name}.db"))
    manager = RoomManager()
    assert await store.load_all_rooms(manager) == 1
    store.close()
    return manager, manager.rooms[room.room_id]


async def table_with_two_people(n: int):
    seed(n)
    service, manager, recorder = make_service(decide=decide_for_seat)
    room = manager.create_room("s0", "Anna")
    manager.join_room(room.room_id, "s1", "Bela")
    room.fill_bots()
    room.bot_speed = "fast"
    for p in room.humans():
        p.is_ready = True
    await service.start_game(room)
    return service, room, recorder


async def step(service, room) -> None:
    position = service.turn_position(room)
    player = room.game_state.get_player(position)
    await service.apply_decision(room, player, decide_for_seat(room.game_state, position))


@pytest.mark.asyncio
@pytest.mark.parametrize("n", range(6))
async def test_table_is_the_same_after_a_restart_at_any_moment(n, tmp_path):
    service, room, _ = await table_with_two_people(n)
    actions = 0
    while True:
        _, restored = await restart(room, tmp_path, f"t{actions}")
        expected, got = saved_form(room), saved_form(restored)
        # Nobody is connected right after a restart
        for form in (expected, got):
            for p in form["game"]["players"]:
                p.pop("is_connected")
        assert got == expected, f"seed {n}, after {actions} actions"
        if room.game_state.phase == GamePhase.GAME_END:
            break
        await step(service, room)
        actions += 1
        assert actions <= 200


@pytest.mark.asyncio
@pytest.mark.parametrize("n", range(6))
async def test_restored_game_plays_on_to_the_same_result(n, tmp_path):
    service, room, recorder = await table_with_two_people(n)
    for _ in range(10 + 5 * n):
        if room.game_state.phase == GamePhase.GAME_END:
            break
        await step(service, room)

    manager, restored = await restart(room, tmp_path, "mid")
    service2, _, recorder2 = make_service(decide=decide_for_seat)
    service2.rooms = manager

    state = random.getstate()
    while room.game_state.phase != GamePhase.GAME_END:
        await step(service, room)
    random.setstate(state)
    while restored.game_state.phase != GamePhase.GAME_END:
        await step(service2, restored)

    original = copy.deepcopy(recorder.of("game_over")[-1])
    again = copy.deepcopy(recorder2.of("game_over")[-1])
    assert again == original


@pytest.mark.asyncio
async def test_people_get_their_seats_back_after_a_restart(tmp_path):
    service, room, _ = await table_with_two_people(1)
    for _ in range(12):
        await step(service, room)
    anna, bela = room.humans()
    owner = room.owner_id

    manager, restored = await restart(room, tmp_path, "seats")
    assert restored.owner_id == owner
    assert [p.is_connected for p in restored.humans()] == [False, False]

    # The client comes back with its player id and the room id it remembers
    _, player, was_away = manager.join_room(room.room_id, "new-socket", "Anna", player_id=anna.id)
    assert player.id == anna.id and was_away
    assert player.is_connected
    assert [c.id for c in player.hand] == [c.id for c in anna.hand]
    assert restored.game_state.get_player_by_id(bela.id).is_connected is False
