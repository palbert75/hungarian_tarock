#!/bin/bash
# Copy problem reports from the live server pod into server/data/reports.
# The pod has no volume, so reports are lost when it restarts: run this before a deploy.
#   cd server; tools/pull_reports.sh
set -e
CONTEXT="${KUBE_CONTEXT:-do-ams3-general}"
POD=$(kubectl --context "$CONTEXT" -n tarokk get pods -o jsonpath='{.items[0].metadata.name}')
mkdir -p data/reports
kubectl --context "$CONTEXT" -n tarokk exec "$POD" -- sh -c 'cd /app/data/reports 2>/dev/null && tar cf - . || true' | tar xf - -C data/reports
ls -1 data/reports | tail -20
