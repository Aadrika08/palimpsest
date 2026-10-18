#!/usr/bin/env bash
# attempt.sh NAME PORT [TMPDIR-for-browser] [extra playwright args...]
# Fresh lab server (v3 flags) + probed Playwright lab workflow, then server stop.
set -u
NAME=$1; PORT=$2; BTMP=${3:-/tmp}; shift 3 || shift $#
ROOT=/home/utkarsh/Work/shraddha/brain/.worktrees/lab-chromium-resources-v1
PY=/home/utkarsh/Work/shraddha/brain/.venv/bin/python
W=$HOME/.cache/lab-chromium-resources-v1/$NAME
rm -rf "$W"; mkdir -p "$W"
cd "$ROOT"
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts MUJOCO_GL=egl OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  "$PY" -B -m palimpsest lab --port "$PORT" --runs "$W/runs" --exports "$W/exports" \
  --storage-max-bytes $((256*1024*1024)) --min-free-bytes $((2*1024*1024*1024)) \
  --max-runs 3 --max-snapshots 2 --max-exports 1 --log-max-bytes 1048576 > "$W/server.log" 2>&1 &
SERVER=$!
for _ in $(seq 60); do curl -sf "http://127.0.0.1:$PORT/api/v1/session" >/dev/null && break; sleep .5; done
cd "$ROOT/ui"
GREP=${GREP:-actual local manual workflow}
START=$(date -u +%FT%T.%3NZ)
WRAP=()
if [ -n "${SMALL:-}" ]; then mkdir -p "$BTMP"; WRAP=(unshare --user --map-root-user --mount sh -c 'mount -t tmpfs -o size='"$SMALL"' tmpfs "$0" && exec "$@"' "$BTMP"); fi
"${WRAP[@]}" env TMPDIR=$BTMP PALIMPSEST_LAB_URL=http://127.0.0.1:$PORT PALIMPSEST_BROWSER=${PALIMPSEST_BROWSER:-/usr/bin/chromium} \
  timeout ${OUTER:-300} "$PY" -I "$ROOT/scripts/lab_chromium_resource_probe.py" --out "$W/resources.jsonl" --shm-dir "${SHMDIR:-$BTMP}" --timeout ${OUTER:-300} --interval ${INTERVAL:-0.25} -- \
  /home/utkarsh/.local/share/mise/installs/node/24.21.0/bin/node node_modules/@playwright/test/cli.js test ${SPEC:-tests/lab.spec.ts} \
  --config playwright.config.ts --grep "$GREP" --workers 1 --retries 0 --timeout ${PWTIMEOUT:-180000} \
  --output "$W/test-results" "$@" > "$W/playwright.log" 2> "$W/probe.log"
RC=$?
echo "{\"name\":\"$NAME\",\"start\":\"$START\",\"end\":\"$(date -u +%FT%T.%3NZ)\",\"returncode\":$RC,\"browser_tmpdir\":\"$BTMP\"}" > "$W/attempt.json"
kill -INT $SERVER; wait $SERVER 2>/dev/null
echo "rc=$RC"; grep -E "passed|failed|ERR_|Failed to fetch" "$W/playwright.log" | head -8; cat "$W/probe.log" | tail -2
