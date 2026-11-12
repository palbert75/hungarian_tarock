"""Tutorial hints: the same advice a bot would follow, with a text in both languages."""

import json
import re
from pathlib import Path

import pytest

from bots.strategy import decide, decide_for_seat
from bots.view import build_view
from models.game_state import GamePhase
from tests.service_helpers import make_service, seed, table_of_four

ROOT = Path(__file__).resolve().parents[2]
I18N = ROOT / "client" / "src" / "i18n"


def texts(language: str) -> dict:
    return json.loads((I18N / f"{language}.json").read_text(encoding="utf-8"))


def lookup(tree: dict, key: str):
    node = tree
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, str) else None


def hinting_service():
    service, manager, recorder = make_service(decide=decide_for_seat)
    service.hint = decide_for_seat
    return service, manager, recorder


@pytest.mark.asyncio
async def test_hint_equals_bot_decision_in_every_phase():
    phases = set()
    for n in range(12):
        seed(n)
        service, manager, _ = hinting_service()
        room = table_of_four(manager)
        await service.start_game(room)
        while room.game_state.phase != GamePhase.GAME_END:
            position = service.turn_position(room)
            player = room.game_state.get_player(position)
            expected = decide(build_view(room.game_state, position))
            payload = service.your_turn_payload(room, player)
            assert payload["hint"] == expected.to_dict()
            phases.add(room.game_state.phase)
            await service.apply_decision(room, player, expected)
    assert phases == {GamePhase.BIDDING, GamePhase.DISCARDING, GamePhase.PARTNER_CALL,
                      GamePhase.ANNOUNCEMENTS, GamePhase.PLAYING}


@pytest.mark.asyncio
async def test_hint_reaches_the_person_to_move():
    seed(3)
    service, manager, recorder = hinting_service()
    room = table_of_four(manager)
    await service.start_game(room)
    sent = recorder.of("your_turn")
    assert sent and sent[-1]["hint"]["action"] == "bid"
    assert sent[-1]["hint"]["reason_key"].startswith("hint.bid.")


@pytest.mark.asyncio
async def test_hint_absent_for_bots():
    seed(3)
    service, manager, recorder = hinting_service()
    room = manager.create_room("s0", "Anna")
    room.fill_bots()
    room.players[0].is_ready = True
    await service.start_game(room)
    bot = next(p for p in room.game_state.players if p.bot_controlled)
    assert "hint" not in service.your_turn_payload(room, bot)
    person = room.game_state.players[0]
    assert "hint" in service.your_turn_payload(room, person)


def test_all_reason_keys_have_text():
    source = (ROOT / "server" / "bots" / "strategy.py").read_text(encoding="utf-8")
    source += (ROOT / "server" / "bots" / "decision.py").read_text(encoding="utf-8")
    keys = set(re.findall(r'"(hint\.[a-z_.]+)"', source))
    assert len(keys) > 30
    for language in ("en", "hu"):
        tree = texts(language)
        missing = sorted(k for k in keys if lookup(tree, k) is None)
        assert missing == [], f"{language}: {missing}"
        # No text for a rule that no longer exists
        def leaves(node, prefix="hint"):
            for name, value in node.items():
                if isinstance(value, dict):
                    yield from leaves(value, f"{prefix}.{name}")
                else:
                    yield f"{prefix}.{name}"
        unused = sorted(k for k in leaves(tree["hint"]) if k not in keys)
        assert unused == [], f"{language}: {unused}"


@pytest.mark.asyncio
async def test_hint_texts_only_use_parameters_the_rule_sends():
    en, hu = texts("en"), texts("hu")
    seen = set()
    for n in range(60):
        seed(n)
        service, manager, _ = hinting_service()
        room = manager.create_room("s0", "Anna")
        room.fill_bots()
        room.players[0].is_ready = True
        await service.start_game(room)
        while room.game_state.phase != GamePhase.GAME_END:
            position = service.turn_position(room)
            player = room.game_state.get_player(position)
            decision = decide(build_view(room.game_state, position))
            seen.add(decision.reason_key)
            for tree in (en, hu):
                text = lookup(tree, decision.reason_key)
                assert text, decision.reason_key
                wanted = set(re.findall(r"\{\{(\w+)\}\}", text))
                assert wanted <= set(decision.reason_params), (decision.reason_key, wanted)
            await service.apply_decision(room, player, decision)
    assert len(seen) > 20
