"""
Build the bot decision tree page and the table that lets a problem report name its boxes.

    cd server; python tools/decision_trees/build.py [--fragment out.html]

Reads   tools/decision_trees/trees.js   the trees: every check and action, in a small notation
        tools/decision_trees/page.html  the page around them
Writes  ../client/public/bot-decision-trees.html   the page in the app (Settings > How the bots play)
        bots/tree_nodes.json                       source line of a check -> number of its box

Run it again after every change to bots/strategy.py or trees.js: the box numbers and the
line numbers are worked out here. A test fails while tree_nodes.json is older than strategy.py.
Needs node (only here, not on the server).

In trees.js a check points at its code in one of two ways: L(n) is line n of strategy.py
as it was in commit BASE, carried over to today's file; LS(`text`) is the first line holding
that text; LA(`after`,`text`) the first such line below the line holding `after`.
"""

import difflib
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE.parent.parent
STRATEGY = SERVER / "bots" / "strategy.py"
BASE = "b000b61"


def strategy_digest() -> str:
    return hashlib.sha256(STRATEGY.read_bytes()).hexdigest()


def resolve_lines(js: str) -> str:
    old = subprocess.run(["git", "-C", str(SERVER), "show", f"{BASE}:server/bots/strategy.py"],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    new = STRATEGY.read_text(encoding="utf-8").splitlines()
    carried = {}
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        for k in range(i2 - i1):
            carried[i1 + k + 1] = (j1 + k if tag == "equal" else min(j1 + k, max(j2 - 1, j1))) + 1

    def by_text(match):
        text = match.group(1)
        for number, line in enumerate(new, 1):
            if text in line:
                return f"'strategy.py:{number}'"
        sys.exit(f"trees.js: no line of strategy.py holds: {text}")

    def by_text_after(match):
        after, text = match.group(1), match.group(2)
        start = next((number for number, line in enumerate(new, 1) if after in line), None)
        for number, line in enumerate(new, 1):
            if start is not None and number > start and text in line:
                return f"'strategy.py:{number}'"
        sys.exit(f"trees.js: no line of strategy.py holds: {text} (after: {after})")

    js = re.sub(r"LA\(`([^`]+)`,`([^`]+)`\)", by_text_after, js)
    js = re.sub(r"LS\(`([^`]+)`\)", by_text, js)
    return "const LM=" + json.dumps(carried, separators=(",", ":")) + ";\n" + js


def main() -> None:
    js = resolve_lines((HERE / "trees.js").read_text(encoding="utf-8"))
    page = (HERE / "page.html").read_text(encoding="utf-8")
    fragment = page + "<script>\n" + js + "</script>\n"

    if "--fragment" in sys.argv:
        Path(sys.argv[sys.argv.index("--fragment") + 1]).write_text(fragment, encoding="utf-8")

    # The page inside the app: a document of its own, and no requests to other sites
    web = re.sub(r'<meta name="claude:[^>]*>\n', "", fragment)
    web = re.sub(r'<link rel="stylesheet" href="https://fonts\.googleapis\.com[^>]*>\n', "", web)
    head_end = web.index("</style>") + len("</style>\n")
    head, body = web[:head_end], web[head_end:]
    head = head.replace("<style>\n", "<style>\nhtml{color-scheme:light}body{margin:0}\n", 1)
    title = "    <h1>Tarokk bot decision trees</h1>"
    assert title in body
    body = body.replace(title, '    <nav><a href="/">← Back to the game</a></nav>\n' + title, 1)
    (SERVER.parent / "client" / "public" / "bot-decision-trees.html").write_text(
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="robots" content="noindex">\n' + head + "</head>\n<body>\n" + body + "</body>\n</html>\n",
        encoding="utf-8")

    # Number the boxes the way the page does, and keep which code line is which box
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as handle:
        handle.write(js)
    contexts = json.loads(subprocess.run(
        ["node", "-e", "process.stdout.write(JSON.stringify(require(process.argv[1]).CONTEXTS))", handle.name],
        capture_output=True, text=True, check=True).stdout)
    Path(handle.name).unlink()
    (SERVER / "bots" / "tree_nodes.json").write_text(
        json.dumps({"strategy_sha256": strategy_digest(), "contexts": contexts}, indent=1, sort_keys=True) + "\n",
        encoding="utf-8")

    # Tell which boxes a report cannot name: their line is not an "if" the route records
    sys.path.insert(0, str(SERVER))
    from bots import route, strategy  # noqa: F401  (importing strategy registers its checks)
    known = {line for (_, line) in route._checks}
    boxes = sum(len(nodes) for lines in contexts.values() for nodes in lines.values())
    loose = sorted({node["id"] for lines in contexts.values() for line, nodes in lines.items()
                    if int(line) not in known for node in nodes}, key=lambda i: (i[0], int(i[1:])))
    print(f"{boxes} checks numbered; {len(loose)} of them do not sit on a recorded check: {' '.join(loose)}")


if __name__ == "__main__":
    main()
