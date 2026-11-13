"""Fixed seats, table owner, held seats (design 4.4, 4.7)."""

import pytest

from models.game_state import GamePhase
from networking.room_manager import RoomManager

from tests.service_helpers import table_of_four


def three_at_table():
    manager = RoomManager()
    room = manager.create_room("s0", "Anna")
    manager.join_room(room.room_id, "s1", "Bela")
    manager.join_room(room.room_id, "s2", "Csaba")
    return manager, room


def names_by_seat(room):
    return {p.position: p.name for p in room.seated()}


def test_join_takes_lowest_free_seat():
    manager, room = three_at_table()
    assert names_by_seat(room) == {0: "Anna", 1: "Bela", 2: "Csaba"}
    manager.leave_room("s1")
    manager.join_room(room.room_id, "s9", "Dora")
    assert names_by_seat(room) == {0: "Anna", 1: "Dora", 2: "Csaba"}


def test_leave_keeps_other_positions():
    manager, room = three_at_table()
    manager.leave_room("s0")
    assert names_by_seat(room) == {1: "Bela", 2: "Csaba"}
    assert room.free_seats() == [0, 3]


def test_swap_occupied_seats():
    _, room = three_at_table()
    room.swap_seats(0, 2)
    assert names_by_seat(room) == {0: "Csaba", 1: "Bela", 2: "Anna"}
    assert [p.position for p in room.players] == [0, 1, 2]


def test_move_to_empty_seat():
    _, room = three_at_table()
    room.swap_seats(1, 3)
    assert names_by_seat(room) == {0: "Anna", 2: "Csaba", 3: "Bela"}


def test_swap_rejected_mid_game():
    manager = RoomManager()
    room = table_of_four(manager)
    room.game_state.phase = GamePhase.PLAYING
    with pytest.raises(ValueError):
        room.swap_seats(0, 1)


def test_owner_is_creator():
    _, room = three_at_table()
    assert room.is_owner(room.player_at(0).id)
    assert not room.is_owner(room.player_at(1).id)


def test_ownership_passes_to_next_human_when_owner_leaves():
    manager, room = three_at_table()
    room.add_bot(3)
    manager.leave_room("s0")
    assert room.is_owner(room.player_at(1).id)


def test_ownership_skips_bots_and_disconnected():
    manager, room = three_at_table()
    room.swap_seats(1, 3)        # Bela to seat 3
    room.add_bot(1)              # bot right after the owner
    room.player_at(2).is_connected = False
    manager.leave_room("s0")
    assert room.is_owner(room.player_at(3).id)


def test_owner_drop_in_waiting_room_keeps_ownership_until_seat_is_freed():
    manager, room = three_at_table()
    owner = room.player_at(0)
    manager.disconnect_session("s0")
    assert room.is_owner(owner.id)
    assert owner in room.seated()
    manager.expire_seat(room.room_id, owner.id)
    assert owner not in room.seated()
    assert room.is_owner(room.player_at(1).id)


def test_owner_drop_mid_game_passes_ownership_at_once():
    manager = RoomManager()
    room = table_of_four(manager)
    room.game_state.phase = GamePhase.PLAYING
    owner = room.player_at(0)
    manager.disconnect_session("s0")
    assert room.is_owner(room.player_at(1).id)
    assert owner in room.seated() and not owner.is_connected


def test_grace_expiry_does_nothing_if_player_is_back():
    manager, room = three_at_table()
    bela = room.player_at(1)
    manager.disconnect_session("s1")
    _, _, was_away = manager.join_room(room.room_id, "s1b", "Bela", bela.id)
    assert was_away is True
    manager.expire_seat(room.room_id, bela.id)
    assert bela in room.seated() and bela.is_connected


def test_room_deleted_when_no_humans():
    manager = RoomManager()
    room = manager.create_room("s0", "Anna")
    room.fill_bots()
    owner = room.player_at(0)
    manager.disconnect_session("s0")
    assert room.room_id in manager.rooms          # held seat keeps the table open
    assert manager.expire_seat(room.room_id, owner.id) is None
    assert room.room_id not in manager.rooms


def test_sharing_invite_does_not_close_table():
    """Owner alone at the table drops for a moment (switching apps) and returns."""
    manager = RoomManager()
    room = manager.create_room("s0", "Anna")
    owner = room.player_at(0)
    manager.disconnect_session("s0")
    assert manager.get_available_rooms()[0]["room_id"] == room.room_id
    manager.join_room(room.room_id, "s0b", "Anna", owner.id)
    assert room.is_owner(owner.id) and owner.is_connected


def test_second_socket_replaces_first():
    manager, room = three_at_table()
    bela = room.player_at(1)
    manager.join_room(room.room_id, "tab2", "Bela", bela.id)
    assert room.player_sessions[bela.id] == "tab2"
    # The old socket closing must not drop the player
    manager.disconnect_session("s1")
    assert bela.is_connected


def test_vacated_seat_between_hands_keeps_total():
    manager = RoomManager()
    room = table_of_four(manager)
    room.game_state.phase = GamePhase.GAME_END
    room.player_at(2).total_score = -7
    manager.leave_room("s2")
    assert room.free_seats() == [2]
    assert len(room.players) == 4                 # the seat is kept, marked vacant
    _, newcomer, _ = manager.join_room(room.room_id, "s9", "Eva")
    assert newcomer.position == 2 and newcomer.total_score == -7
    assert [p.position for p in room.players] == [0, 1, 2, 3]


def test_swap_between_hands_totals_follow_player():
    manager = RoomManager()
    room = table_of_four(manager)
    room.game_state.phase = GamePhase.GAME_END
    room.player_at(0).total_score = 5
    room.swap_seats(0, 3)
    assert room.player_at(3).name == "Anna" and room.player_at(3).total_score == 5
    assert [p.position for p in room.players] == [0, 1, 2, 3]


def test_room_info_has_owner_and_bot_flags():
    manager, room = three_at_table()
    room.add_bot()
    info = room.get_room_info()
    assert info["owner_id"] == room.player_at(0).id
    assert info["is_full"] is True
    bot = next(p for p in info["players"] if p["position"] == 3)
    assert bot["is_bot"] and bot["is_ready"] and bot["name"].startswith("Bot ")


def test_owner_leaving_mid_game_hands_the_table_to_the_next_person():
    manager = RoomManager()
    room = table_of_four(manager)
    room.game_state.phase = GamePhase.PLAYING
    assert manager.leave_room("s0") is room
    assert room.is_owner(room.player_at(1).id)


def test_last_person_leaving_mid_game_closes_the_table():
    manager = RoomManager()
    room = manager.create_room("s0", "Anna")
    room.fill_bots()
    room.game_state.phase = GamePhase.PLAYING
    assert manager.leave_room("s0") is None
    assert room.room_id not in manager.rooms


def test_table_stays_while_a_dropped_person_may_still_come_back():
    manager = RoomManager()
    room = table_of_four(manager)
    room.game_state.phase = GamePhase.PLAYING
    for sid in ("s2", "s3"):
        manager.leave_room(sid)
    manager.disconnect_session("s1")           # dropped a moment ago
    assert manager.leave_room("s0") is room    # Bela may be back
    bela = room.player_at(1)
    later = room.dropped_at[bela.id] + 1000
    assert manager.expire_seat(room.room_id, bela.id, now=later) is None
    assert room.room_id not in manager.rooms


def test_last_person_dropping_mid_game_closes_the_table_after_the_grace_period():
    manager = RoomManager()
    room = manager.create_room("s0", "Anna")
    room.fill_bots()
    room.game_state.phase = GamePhase.PLAYING
    owner = room.player_at(0)
    manager.disconnect_session("s0")
    assert manager.expire_seat(room.room_id, owner.id, now=room.dropped_at[owner.id] + 5) is room
    assert manager.expire_seat(room.room_id, owner.id, now=room.dropped_at[owner.id] + 1000) is None
    assert room.room_id not in manager.rooms


def test_dropped_person_mid_game_keeps_the_seat_while_others_play_on():
    manager = RoomManager()
    room = table_of_four(manager)
    room.game_state.phase = GamePhase.PLAYING
    bela = room.player_at(1)
    manager.disconnect_session("s1")
    assert manager.expire_seat(room.room_id, bela.id, now=room.dropped_at[bela.id] + 1000) is room
    assert bela in room.seated() and not bela.vacant
