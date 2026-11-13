"""Print a problem report in a readable form: the text, every hand, the tricks, what the bots did.

    cd server; python tools/show_report.py data/reports/<id>.json
"""
import json
import sys

SUIT = {"hearts": "♥", "diamonds": "♦", "spades": "♠", "clubs": "♣"}


def name(card: dict) -> str:
    return card["rank"] if card["suit"] == "tarokk" else f"{SUIT.get(card['suit'], '?')}{card['rank']}"


def order(card: dict):
    ranks = ["skiz", "XXI", "XX", "XIX", "XVIII", "XVII", "XVI", "XV", "XIV", "XIII", "XII", "XI", "X",
             "IX", "VIII", "VII", "VI", "V", "IV", "III", "II", "I"]
    if card["suit"] == "tarokk":
        return (0, ranks.index(card["rank"]) if card["rank"] in ranks else 99)
    return (1, card["suit"], -card.get("points", 0))


def cards(items) -> str:
    return " ".join(name(c) for c in sorted(items or [], key=order)) or "–"


def main(path: str) -> None:
    report = json.load(open(path, encoding="utf-8"))
    game = report["game"]
    seat = {s["position"]: s["name"] + (" (bot)" if s["bot"] else "") for s in report["seats"]}
    print(f"Report {report['id']}  {report['created_at']}  room {report['room_id']}")
    print(f"From seat {report['reporter']['position']} ({report['reporter']['name']}):")
    print(f"  {report['text']}\n")
    print(f"Phase {game['phase']}, hand {game.get('hand_number')}, dealer {game.get('dealer_position')}, "
          f"declarer {game.get('declarer_position')}, called {game.get('called_card_rank')}, "
          f"partner {game.get('partner_position')}, turn {game.get('current_turn')}")
    bids = [f"{seat.get(b['player_position'])}: {b['bid_type']}" for b in game.get("bid_history", [])]
    if bids:
        print("Bids: " + ", ".join(bids))
    said = [f"{seat.get(a['player_position'])}: {a['announcement_type']}"
            + (" (rekontra)" if a.get("recontra") else " (kontra)" if a.get("contra") else "")
            for a in game.get("announcements", [])]
    if said:
        print("Announcements: " + ", ".join(said))
    print()
    for p in game["players"]:
        print(f"Seat {p['position']} {seat.get(p['position'])}")
        print(f"   hand:  {cards(p.get('hand'))}")
        played = [t["card"] for trick in game.get("trick_history", []) for t in trick["cards"] if t["player_position"] == p["position"]]
        if played:
            print(f"   played: {cards(played)}")
        print(f"   skart: {cards(p.get('discard_pile'))}")
    print()
    # Numbered from 1 here, like the bot decisions below (the stored trick_number runs one ahead)
    for number, trick in enumerate(game.get("trick_history", []), start=1):
        plays = "  ".join(f"{t['player_position']}:{name(t['card'])}" for t in trick["cards"])
        print(f"Trick {number}: {plays}   -> seat {trick['winner']}")
    if game.get("current_trick"):
        print("Now on the table: " + "  ".join(f"{t['player_position']}:{name(t['card'])}" for t in game["current_trick"]))
    print()
    ids = {c["id"]: name(c) for p in game["players"] for key in ("hand", "discard_pile", "tricks_won") for c in p.get(key) or []}
    for d in report.get("bot_decisions", []):
        what = d["payload"]
        if "card_id" in what:
            what = ids.get(what["card_id"], what["card_id"])
        elif "card_ids" in what:
            what = " ".join(ids.get(c, c) for c in what["card_ids"])
        print(f"[{d['phase']} t{d['trick_number']}] seat {d['position']} {d['action']} {what}  ({d['reason_key']})"
              + ("  FALLBACK" if d.get("fallback") else ""))
    if report.get("client"):
        print("\nClient: " + json.dumps(report["client"], ensure_ascii=False)[:600])


if __name__ == "__main__":
    main(sys.argv[1])
