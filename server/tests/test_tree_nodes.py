"""The table that names the boxes of the decision tree page in problem reports."""
import hashlib
import json
from pathlib import Path

from bots import route
from bots.strategy import decide_for_seat
from models.game_state import GamePhase
from tests.helpers import make_state

BOTS = Path(__file__).resolve().parent.parent / "bots"


def test_box_table_was_built_from_todays_strategy():
    table = json.loads((BOTS / "tree_nodes.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256((BOTS / "strategy.py").read_bytes()).hexdigest()
    assert table["strategy_sha256"] == digest, (
        "bots/strategy.py changed: run  python tools/decision_trees/build.py  in server/ "
        "to renumber the decision tree page and bots/tree_nodes.json")


def test_route_names_the_boxes_of_the_page():
    gs = make_state(["XXI XX X IX hK hQ dC dJ sQ", "skiz hJ", "I cJ", "II cQ"])
    gs.phase = GamePhase.BIDDING
    d = decide_for_seat(gs, 0)
    # No honour? no. Any bid left? yes. ... Do I hold the XXI? yes. Solo? no: bid.
    assert d.boxes[:2] == ["A1", "A3"]
    assert d.boxes[-5:] == ["A13", "A14", "A16", "A30", "A32"]
    assert all(box.startswith("A") for box in d.boxes)
    assert [step["box"] for step in d.route if step["check"] == "if has_xxi:"] == ["A13"]


def test_stale_table_names_no_boxes(monkeypatch):
    monkeypatch.setattr(route, "_contexts", {})
    assert route.name_boxes([{"line": 1, "check": "if x:", "matched": True}], "A") == []
