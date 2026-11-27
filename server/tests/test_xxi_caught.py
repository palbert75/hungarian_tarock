"""The table is told when the XXI is caught, and its owner wears the mayor's hat."""

import pytest

from models.game_state import GamePhase
from tests.service_helpers import make_service, table_of_four


def trick(*plays):
    return {"winner": plays[0][0], "cards": [
        {"player_position": pos, "card": {"suit": "tarokk", "rank": rank}} for pos, rank in plays
    ]}


def playing_room(partner_revealed=True, partner=2):
    service, manager, recorder = make_service()
    room = table_of_four(manager)
    gs = room.game_state
    gs.phase = GamePhase.PLAYING
    gs.declarer_position = 0
    gs.partner_position = partner
    gs.partner_revealed = partner_revealed
    return service, room, recorder


@pytest.mark.asyncio
async def test_catch_is_told_once_and_the_xxi_owner_gets_the_hat():
    service, room, recorder = playing_room()
    room.game_state.trick_history = [trick((1, "skiz"), (0, "XXI"))]

    await service.show_xxi_catch(room)
    await service.show_xxi_catch(room)

    sent = recorder.of("xxi_caught")
    assert len(sent) == 1
    assert sent[0]["data"] == {"skiz_position": 1, "xxi_position": 0, "winners": [1, 3], "losers": [0, 2]}
    assert [p.polgarmester for p in room.game_state.players] == [True, False, False, False]
    assert room.get_room_info()["players"][0]["polgarmester"] is True


@pytest.mark.asyncio
async def test_hidden_partner_keeps_the_catch_back_until_the_hand_ends():
    service, room, recorder = playing_room(partner_revealed=False)
    room.game_state.trick_history = [trick((1, "skiz"), (0, "XXI"))]

    await service.show_xxi_catch(room)
    assert recorder.of("xxi_caught") == []

    room.game_state.phase = GamePhase.SCORING
    await service.show_xxi_catch(room)
    assert len(recorder.of("xxi_caught")) == 1


@pytest.mark.asyncio
async def test_skiz_on_a_teammates_xxi_is_no_catch_and_the_hat_stays():
    service, room, recorder = playing_room()
    room.game_state.players[3].polgarmester = True
    room.game_state.trick_history = [trick((0, "skiz"), (2, "XXI"))]

    await service.show_xxi_catch(room)

    assert recorder.of("xxi_caught") == []
    assert room.game_state.players[3].polgarmester is True


@pytest.mark.asyncio
async def test_the_hat_moves_to_the_next_xxi_caught_and_survives_the_next_hand():
    service, room, _ = playing_room()
    gs = room.game_state
    gs.players[3].polgarmester = True
    gs.trick_history = [trick((0, "skiz"), (1, "XXI"))]
    await service.show_xxi_catch(room)
    assert [p.polgarmester for p in gs.players] == [False, True, False, False]

    gs.reset_for_next_hand()
    assert gs.xxi_catch_shown is False
    assert gs.players[1].polgarmester is True


@pytest.mark.asyncio
async def test_declarer_alone_catch_names_the_three_defenders():
    service, room, recorder = playing_room(partner_revealed=False, partner=None)
    room.game_state.phase = GamePhase.SCORING
    room.game_state.trick_history = [trick((0, "skiz"), (3, "XXI"))]

    await service.show_xxi_catch(room)

    data = recorder.of("xxi_caught")[0]["data"]
    assert data["winners"] == [0] and data["losers"] == [1, 2, 3]


def between_hands_with_mayor():
    _, manager, _ = make_service()
    room = table_of_four(manager)
    room.game_state.phase = GamePhase.GAME_END
    room.game_state.players[1].polgarmester = True
    return manager, room


def test_the_hat_leaves_with_the_person_not_the_seat():
    manager, room = between_hands_with_mayor()
    room.vacate(room.player_at(1).id)

    newcomer = manager.join_room(room.room_id, "s9", "Elemer")[1]

    assert newcomer.position == 1 and newcomer.polgarmester is False
    assert not any(p.polgarmester for p in room.seated())


def test_the_hat_comes_back_when_the_polgarmester_rejoins():
    manager, room = between_hands_with_mayor()
    room.vacate(room.player_at(1).id)

    back = manager.join_room(room.room_id, "s9", "Bela")[1]

    assert back.polgarmester is True and room.away_mayor is None


@pytest.mark.asyncio
async def test_a_new_catch_while_the_polgarmester_is_away_takes_the_hat_for_good():
    service, room, _ = playing_room()
    room.away_mayor = "Bela"
    room.game_state.trick_history = [trick((0, "skiz"), (3, "XXI"))]

    await service.show_xxi_catch(room)

    assert room.away_mayor is None and room.game_state.players[3].polgarmester is True


def test_a_bot_takes_no_hat_from_the_seat():
    manager, room = between_hands_with_mayor()
    room.vacate(room.player_at(1).id)
    bot = room.add_bot(1)
    assert bot.polgarmester is False and room.away_mayor == "Bela"
