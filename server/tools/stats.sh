#!/bin/bash
# Played hands per day on the live server.
#   cd server; tools/stats.sh [days]        (default 30)
# The token is read from the cluster, so this works for whoever may use the cluster.
set -euo pipefail
CONTEXT="${KUBE_CONTEXT:-do-ams3-general}"
DAYS="${1:-30}"
TOKEN=$(kubectl --context "$CONTEXT" -n tarokk get secret tarokk-stats -o jsonpath='{.data.token}' | base64 -d)
curl -fsS -H "Authorization: Bearer $TOKEN" "https://tarokk.onbased.cloud/stats?days=$DAYS" | python3 -c '
import json, sys
s = json.load(sys.stdin)
n = s["now"]
print("Now: %d table(s) with people, %d in a hand, %d people connected" % (
    n["tables_with_people"], n["tables_in_a_hand"], n["people_connected"]))
print()
print("%-11s %6s %7s %7s %9s %8s  %s" % ("day", "hands", "tables", "people", "2+people", "min/hand", "who"))
for d in s["per_day"]:
    print("%-11s %6d %7d %7d %9d %8s  %s" % (
        d["day"], d["hands"], d["tables"], d["people"], d["hands_with_two_or_more_people"],
        d["median_hand_minutes"] if d["median_hand_minutes"] is not None else "-", ", ".join(d["player_names"])))
t = s["total"]
print()
print("Last %d days (%s): %d hands at %d tables, %d different people" % (
    s["days"], s["time_zone"], t["hands"], t["tables"], t["people"]))
'
