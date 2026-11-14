"""
The route of a decision: which checks of the decision tree it went through.

The strategy is a list of "if" checks, the first match decides. While a decision
is made, the lines that run in the watched functions are recorded; every "if"
among them becomes one step: where it is, what it asks, and whether it matched.
The last step that matched is the rule that decided.
"""

import ast
import hashlib
import inspect
import json
import sys
import textwrap
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

MAX_CHECK_TEXT = 200

_watched: set = set()
# line of an "if" -> (last line of its condition, first and last line of its body, its text, file)
_checks: Dict[Tuple[str, int], Tuple[int, int, int, str]] = {}


NODES_FILE = Path(__file__).with_name("tree_nodes.json")
_contexts: Optional[dict] = None


def _box_table() -> dict:
    """
    Source line of a check -> the number of its box on the decision tree page, per tree.
    tools/decision_trees/build.py writes it; it only counts for the strategy.py it was built from.
    """
    global _contexts
    if _contexts is None:
        _contexts = {}
        try:
            table = json.loads(NODES_FILE.read_text(encoding="utf-8"))
            digest = hashlib.sha256(NODES_FILE.with_name("strategy.py").read_bytes()).hexdigest()
            if table.get("strategy_sha256") == digest:
                _contexts = table["contexts"]
        except (OSError, ValueError, KeyError):
            pass
    return _contexts


def name_boxes(steps: List[dict], tree: str) -> List[str]:
    """
    Put the box number on every step that has a box on the page, and return the route
    as box numbers: each check passed, and the action box where a check led to one.
    """
    lines = _box_table().get(tree, {})
    boxes: List[str] = []
    for step in steps:
        nodes = lines.get(str(step["line"]))
        if not nodes:
            continue
        node = nodes[0]
        step["box"] = node["id"]
        # The check, then the action it led to: right of it when it matched, below it when
        # it did not and nothing but that action is left
        for box in (node["id"], node["yes"] if step["matched"] else node["no"]):
            if box and (not boxes or boxes[-1] != box):
                boxes.append(box)
    return boxes


def watch(*functions: Callable) -> None:
    """Record the route through these functions."""
    for function in functions:
        code = function.__code__
        if code in _watched:
            continue
        _watched.add(code)
        lines, start = inspect.getsourcelines(function)
        tree = ast.parse(textwrap.dedent("".join(lines)))
        for node in ast.walk(tree):
            if not isinstance(node, ast.If):
                continue
            first, last = node.lineno, node.test.end_lineno
            text = " ".join(line.strip() for line in lines[first - 1:last])
            _checks[(code.co_filename, first + start - 1)] = (
                last + start - 1,
                node.body[0].lineno + start - 1,
                node.body[-1].end_lineno + start - 1,
                text[:MAX_CHECK_TEXT],
            )


def record(function: Callable, *args):
    """Call the function; return its result and the route it took."""
    ran: List[Tuple[str, int]] = []

    def local(frame, event, arg):
        if event == "line":
            ran.append((frame.f_code.co_filename, frame.f_lineno))
        return local

    def tracer(frame, event, arg):
        return local if frame.f_code in _watched else None

    before = sys.gettrace()
    sys.settrace(tracer)
    try:
        result = function(*args)
    finally:
        sys.settrace(before)
    return result, _steps(ran)


def _steps(ran: List[Tuple[str, int]]) -> List[dict]:
    steps = []
    for index, (filename, line) in enumerate(ran):
        check = _checks.get((filename, line))
        if check is None:
            continue
        condition_end, body_start, body_end, text = check
        if index and ran[index - 1][0] == filename and line < ran[index - 1][1] <= condition_end:
            continue  # still inside the same condition, which spans several lines
        after = next((n for f, n in ran[index + 1:] if f != filename or not line <= n <= condition_end), None)
        steps.append({
            "line": line,
            "check": text,
            "matched": after is not None and body_start <= after <= body_end,
        })
    return steps
