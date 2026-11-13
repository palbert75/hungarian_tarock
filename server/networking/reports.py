"""Problem reports: a player describes what went wrong, the server keeps the whole table with it.

A report holds every hand, so it never goes to a client while that could
help someone cheat: it is stored on the server, and handed back to the
reporter only when no other person sits at the table or the hand is over.
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from models.game_state import GamePhase
from models.player import Player
from networking.room_manager import Room

REPORT_DIR = Path("data/reports")
MAX_TEXT = 2000
MAX_CLIENT_INFO_BYTES = 20_000
MAX_REPORTS = 500
# Bot decisions kept per hand (a hand has about 60 actions)
MAX_DECISIONS = 200


def log_decision(room: Room, position: int, decision, fallback: bool = False) -> None:
    """Remember what a bot did and why, for a later report."""
    game_state = room.game_state
    room.decision_log.append({
        "hand_number": game_state.hand_number,
        "phase": game_state.phase.value,
        "trick_number": game_state.trick_number,
        "position": position,
        "action": decision.action,
        "payload": decision.payload,
        "reason_key": decision.reason_key,
        "reason_params": decision.reason_params,
        "fallback": fallback,
    })
    del room.decision_log[:-MAX_DECISIONS]


def may_return_to_reporter(room: Room, reporter: Player) -> bool:
    """Showing every hand is harmless once the hand is over or only bots sit with the reporter."""
    if room.game_state.phase in (GamePhase.GAME_END, GamePhase.SCORING, GamePhase.WAITING):
        return True
    return all(p.bot_controlled or p.vacant for p in room.players if p.id != reporter.id)


def build_report(room: Room, reporter: Player, text: str, client_info: Optional[dict] = None) -> dict:
    text = (text or "").strip()
    if not text:
        raise ValueError("Describe the problem")
    if len(text) > MAX_TEXT:
        raise ValueError(f"Description too long (max {MAX_TEXT} characters)")
    client_info = client_info if isinstance(client_info, dict) else {}
    if len(json.dumps(client_info, default=str)) > MAX_CLIENT_INFO_BYTES:
        client_info = {"dropped": "client info too large"}

    now = datetime.now(timezone.utc)
    report_id = f"{now.strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:6]}"
    return {
        "id": report_id,
        "created_at": now.isoformat(),
        "room_id": room.room_id,
        "reporter": {"position": reporter.position, "name": reporter.name},
        "text": text,
        "seats": [
            {"position": p.position, "name": p.name, "bot": bool(p.bot_controlled), "vacant": bool(p.vacant)}
            for p in room.players
        ],
        # Everything, including the hidden hands, skarts and won tricks
        "game": room.game_state.to_dict(include_all_hands=True),
        "bot_decisions": list(room.decision_log),
        "last_game_over": room.last_game_over,
        "client": client_info,
    }


def save_report(report: dict, directory: Path = REPORT_DIR) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    if len(list(directory.glob("*.json"))) >= MAX_REPORTS:
        raise ValueError("Too many stored reports")
    if not re.fullmatch(r"[0-9a-f-]+", report["id"]):
        raise ValueError("Bad report id")
    path = directory / f"{report['id']}.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return path


class ReportThrottle:
    """At most one report every few seconds per player."""

    def __init__(self, seconds: float = 5.0):
        self.seconds = seconds
        self.last: dict = {}

    def check(self, player_id: str) -> None:
        now = time.monotonic()
        if now - self.last.get(player_id, -1e9) < self.seconds:
            raise ValueError("Please wait a moment before sending another report")
        self.last[player_id] = now
