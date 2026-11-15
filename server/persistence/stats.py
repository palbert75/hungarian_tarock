"""Statistics of played hands: one record per finished hand, summed up per day."""

import json
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    from zoneinfo import ZoneInfo
    LOCAL_ZONE = ZoneInfo("Europe/Budapest")
except Exception:  # no time zone data on this machine: days are counted in UTC
    LOCAL_ZONE = timezone.utc


def hand_record(room, result: dict, now: Optional[float] = None) -> Dict[str, Any]:
    """What is kept of a finished hand. `result` is the game-over message of the table."""
    now = time.time() if now is None else now
    game_state = room.game_state
    people = [p for p in game_state.players if not p.is_bot and not p.vacant]
    declarer = game_state.players[result["declarer"]] if result.get("declarer") is not None else None
    started = room.hand_started_at
    return {
        "finished_at": int(now),
        "room_id": room.room_id,
        "hand_number": game_state.hand_number,
        "people": len(people),
        "bots": len(game_state.players) - len(people),
        # A person whose seat a bot has taken over still counts as a person of the table
        "player_names": json.dumps([p.name for p in people], ensure_ascii=False),
        "bid": game_state.winning_bid.bid_type.value if game_state.winning_bid else None,
        "declarer_is_person": None if declarer is None else int(not declarer.bot_controlled),
        "declarer_alone": int(bool(result.get("declarer_alone"))),
        "winner": result.get("winner"),
        "declarer_team_points": result.get("declarer_team_points"),
        "game_value": result.get("final_game_value"),
        "announcements": json.dumps(sorted({a.announcement_type.value for a in game_state.announcements})),
        "duration_seconds": int(now - started) if started else None,
    }


def summarize(rows: List[Dict[str, Any]], days: int, now: Optional[float] = None) -> Dict[str, Any]:
    """Hands, tables and people per day (Budapest time), newest day first; days without play are listed with zeros."""
    now = time.time() if now is None else now
    today = datetime.fromtimestamp(now, LOCAL_ZONE).date()
    per_day: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    for back in range(days):
        per_day[(today - timedelta(days=back)).isoformat()] = {
            "hands": 0, "tables": set(), "people": set(), "hands_with_two_or_more_people": 0, "seconds": []}

    all_people, all_tables, hands = set(), set(), 0
    for row in rows:
        day = per_day.get(datetime.fromtimestamp(row["finished_at"], LOCAL_ZONE).date().isoformat())
        if day is None:
            continue
        names = json.loads(row["player_names"] or "[]")
        hands += 1
        day["hands"] += 1
        day["tables"].add(row["room_id"])
        day["people"].update(names)
        if row["people"] >= 2:
            day["hands_with_two_or_more_people"] += 1
        if row["duration_seconds"]:
            day["seconds"].append(row["duration_seconds"])
        all_people.update(names)
        all_tables.add(row["room_id"])

    return {
        "days": days,
        "time_zone": str(LOCAL_ZONE),
        "total": {"hands": hands, "tables": len(all_tables), "people": len(all_people)},
        "per_day": [
            {
                "day": name,
                "hands": d["hands"],
                "tables": len(d["tables"]),
                "people": len(d["people"]),
                "player_names": sorted(d["people"]),
                "hands_with_two_or_more_people": d["hands_with_two_or_more_people"],
                "median_hand_minutes": round(sorted(d["seconds"])[len(d["seconds"]) // 2] / 60, 1) if d["seconds"] else None,
            }
            for name, d in per_day.items()
        ],
    }
