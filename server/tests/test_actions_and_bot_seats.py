"""Shared actions, bot seats and the bot runner (design 5.1, 4.7)."""

import asyncio

import pytest

from models.bid import BidType
from models.game_state import GamePhase

from tests.service_helpers import make_service, seed, table_of_four
from tests.test_next_hand import play_out_first_hand


@pytest.mark.asyncio
async def test_full_hand_through_actions():
    seed(11)
    service, manager, recorder = make_service()
    room = table_of_four(manager)
    await service.start_game(room)
    await play_out_first_hand(service, room)

    names = recorder.names()
    for expected in ("game_started", "bid_placed", "talon_distributed", "player_discarded",
                     "partner_called", "announcements_complete", "trick_started",
                     "card_played", "trick_complete", "game_over", "your_turn"):
        assert expected in names, expected
    assert len(recorder.of("trick_complete")) == 9
    assert len(recorder.of("trick_complete")[0]["data"]["cards"]) == 4


@pytest.mark.asyncio
async def test_action_rejected_out_of_turn():
    seed(12)
    service, manager, _ = make_service()
    room = table_of_four(manager)
    await service.start_game(room)
    gs = room.game_state
    not_on_turn = gs.get_player((gs.current_turn + 1) % 4)
    with pytest.raises(ValueError):
        await service.act_bid(room, not_on_turn, BidType.PASS)
    with pytest.raises(ValueError):
        await service.act_play_card(room, gs.get_player(gs.current_turn), "x")


def test_add_remove_fill_bots():
    service, manager, _ = make_service()
    room = manager.create_room("s0", "Anna")
    bot = room.add_bot(2)
    assert bot.position == 2 and bot.is_bot and bot.bot_controlled and bot.is_ready
    with pytest.raises(ValueError):
        room.add_bot(2)
    room.remove_bot(2)
    assert room.free_seats() == [1, 2, 3]
    with pytest.raises(ValueError):
        room.remove_bot(0)                       # a person, not a bot
    bots = room.fill_bots()
    assert len(bots) == 3 and room.is_full()
    assert len({p.name for p in room.seated()}) == 4


def test_bots_cannot_be_added_mid_game():
    service, manager, _ = make_service()
    room = manager.create_room("s0", "Anna")
    room.game_state.phase = GamePhase.PLAYING
    with pytest.raises(ValueError):
        room.add_bot()


@pytest.mark.asyncio
async def test_one_person_with_three_bots_starts_and_bots_play():
    seed(13)
    service, manager, _ = make_service()
    room = manager.create_room("s0", "Anna")
    room.fill_bots()
    room.player_at(0).is_ready = True
    assert room.can_start_game()
    await service.start_game(room)

    # Bots act until it is the person's turn (or the hand is thrown in and redealt)
    await service.drive_bots(room)
    position = service.turn_position(room)
    assert position == 0
    assert not room.game_state.get_player(position).bot_controlled


@pytest.mark.asyncio
async def test_replace_requires_disconnected_then_bot_plays_and_human_takes_back():
    seed(14)
    service, manager, recorder = make_service()
    room = table_of_four(manager)
    await service.start_game(room)
    gs = room.game_state
    seat = gs.current_turn
    player = gs.get_player(seat)

    with pytest.raises(ValueError):
        room.replace_with_bot(seat)              # still connected

    manager.disconnect_session(f"s{seat}")
    assert not player.is_connected
    assert gs.current_turn == seat               # the game waits; nobody is removed
    assert len(room.seated()) == 4

    room.replace_with_bot(seat)
    assert player.bot_controlled and not player.is_bot
    acted = await service.bot_move(room)
    assert acted and gs.current_turn != seat

    # The player comes back and takes the seat over from the bot
    _, back, was_away = manager.join_room(room.room_id, "new-socket", player.name, player.id)
    assert back is player and was_away
    assert player.is_connected and not player.bot_controlled


@pytest.mark.asyncio
async def test_stale_bot_task_does_not_act():
    seed(15)
    service, manager, _ = make_service()
    room = manager.create_room("s0", "Anna")
    room.fill_bots()
    room.player_at(0).is_ready = True
    await service.start_game(room)
    await service.drive_bots(room)
    gs = room.game_state

    # A bot move is pending for a replaced seat, then the person returns
    manager.disconnect_session("s0")
    room.replace_with_bot(0)
    history_len = len(gs.bid_history)
    pending = asyncio.create_task(service._bot_move_later(room, room.turn_seq, 0.01))
    manager.join_room(room.room_id, "s0b", "Anna", room.player_at(0).id)
    await pending
    assert len(gs.bid_history) == history_len    # the stale task did nothing
    assert gs.current_turn == 0


@pytest.mark.asyncio
async def test_failing_strategy_falls_back_to_a_legal_move():
    seed(16)

    def broken(game_state, position):
        raise RuntimeError("boom")

    service, manager, _ = make_service(decide=broken)
    room = manager.create_room("s0", "Anna")
    room.fill_bots()
    room.player_at(0).is_ready = True
    await service.start_game(room)
    await service.drive_bots(room)
    assert service.turn_position(room) == 0      # the table did not stall


@pytest.mark.asyncio
async def test_your_turn_sent_only_to_people():
    seed(17)
    service, manager, recorder = make_service()
    room = manager.create_room("s0", "Anna")
    room.fill_bots()
    room.player_at(0).is_ready = True
    await service.start_game(room)
    await service.drive_bots(room)
    targets = {e[2] for e in recorder.events if e[0] == "your_turn"}
    assert targets <= {"s0"}
