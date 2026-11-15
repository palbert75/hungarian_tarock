#!/bin/bash
# Deploy the server: test, build, push an image named after the git commit, roll it out.
#
#   cd server; ./deploy.sh              deploy the current commit
#   cd server; ./deploy.sh rollback     go back to the image that ran before
#
# Running games survive: the server tells the players, saves every table to the
# volume, and the new pod loads them again; the apps reconnect by themselves.
set -euo pipefail
cd "$(dirname "$0")"

CONTEXT="${KUBE_CONTEXT:-do-ams3-general}"
NAMESPACE=tarokk
IMAGE=palbert75/hungarian-tarokk-server
HEALTH_URL=https://tarokk.onbased.cloud/health
K="kubectl --context $CONTEXT -n $NAMESPACE"

if [ "${1:-}" = "rollback" ]; then
    $K rollout undo deploy/app
    $K rollout status deploy/app --timeout=180s
    $K get deploy app -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
    exit 0
fi

# The tag must say exactly what runs: no uncommitted server changes
if [ -n "$(git status --porcelain -- .)" ]; then
    echo "Uncommitted changes under server/ - commit them first:" >&2
    git status --short -- . >&2
    exit 1
fi
TAG=$(git rev-parse --short HEAD)
echo "== Deploying $IMAGE:$TAG"

echo "== Tests"
.venv/bin/python -m pytest -q -p no:cacheprovider 2>&1 | tail -1

echo "== Build"
docker build --platform linux/amd64 -t "$IMAGE:$TAG" -t "$IMAGE:latest" .

echo "== Trial start of the image"
CID=$(docker run -d -p 8001:8000 -e DEBUG=false "$IMAGE:$TAG")
trap 'docker rm -f "$CID" >/dev/null 2>&1 || true' EXIT
for i in $(seq 1 20); do
    curl -fs http://localhost:8001/health >/dev/null 2>&1 && break
    [ "$i" = 20 ] && { echo "The image does not answer on /health" >&2; docker logs "$CID" | tail -30 >&2; exit 1; }
    sleep 1
done
docker rm -f "$CID" >/dev/null
trap - EXIT

echo "== Push"
docker push "$IMAGE:$TAG"
docker push "$IMAGE:latest"

echo "== Roll out"
kubectl --context "$CONTEXT" apply -f k8s/pvc.yaml -f k8s/service.yaml -f k8s/ingress.yaml
sed "s|IMAGE_TAG|$TAG|" k8s/deployment.yaml | kubectl --context "$CONTEXT" apply -f -
$K rollout status deploy/app --timeout=240s

echo "== Check"
for i in $(seq 1 30); do
    curl -fs "$HEALTH_URL" && echo && break
    [ "$i" = 30 ] && { echo "$HEALTH_URL does not answer; go back with: ./deploy.sh rollback" >&2; exit 1; }
    sleep 2
done
$K logs deploy/app --tail=200 | grep -E 'rooms_loaded_on_startup|persistence_init_error|load_room_error' || true
echo "== Done: $IMAGE:$TAG"
