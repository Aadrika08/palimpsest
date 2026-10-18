#!/usr/bin/env bash
# Canonical source-test run for main; see docs/testing.md.
#
#   scripts/run_tests.sh                 # every non-integration test, two passes
#   scripts/run_tests.sh --integration   # the *_integration.py files (runs/ basetemp)
#   scripts/run_tests.sh -- tests/test_x.py -k name   # chosen tests, pass 1 rules
#
# Environment overrides: PALIMPSEST_PYTHON (default: <repo>/.venv, else the main
# checkout's .venv) and PALIMPSEST_TEST_BASETEMP (default: ~/.cache/palimpsest-pytest).
set -uo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
COMMON=$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || echo "$ROOT/.git")
MAIN=$(dirname "$COMMON")
PYTHON=${PALIMPSEST_PYTHON:-}
for candidate in "$ROOT/.venv/bin/python" "$MAIN/.venv/bin/python"; do
  [ -z "$PYTHON" ] && [ -x "$candidate" ] && PYTHON=$candidate
done
[ -n "$PYTHON" ] || { echo "No .venv python found; set PALIMPSEST_PYTHON" >&2; exit 2; }
NAME=$(basename "$ROOT")-$$
OUTSIDE=${PALIMPSEST_TEST_BASETEMP:-$HOME/.cache/palimpsest-pytest}/$NAME
INSIDE=$ROOT/runs/pytest-$NAME

run() {  # basetemp, pytest args...
  local basetemp=$1; shift
  mkdir -p "$(dirname "$basetemp")"
  (cd "$ROOT" && env -i PATH=/usr/bin:/bin HOME="$HOME" LANG=C.UTF-8 LC_ALL=C.UTF-8 TMPDIR=/tmp \
    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$ROOT/src:$ROOT/scripts:$ROOT/tests" \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
    MUJOCO_GL=egl CUDA_VISIBLE_DEVICES= \
    "$PYTHON" -B -m pytest -q -p no:cacheprovider --basetemp "$basetemp" "$@")
}

status=0
if [ "${1:-}" = "--integration" ]; then
  shift; run "$INSIDE-integration" "$@" "$ROOT"/tests/*_integration.py || status=$?
elif [ "${1:-}" = "--" ]; then
  shift; run "$OUTSIDE-selected" "$@" || status=$?
else
  mapfile -t files < <(ls "$ROOT"/tests/test_*.py | grep -v '_integration\.py$')
  run "$OUTSIDE" -m "not runs_basetemp" "$@" "${files[@]}" || status=$?
  run "$INSIDE" -m runs_basetemp "$@" "${files[@]}" || status=$?
fi
rm -rf "$OUTSIDE" "$OUTSIDE-selected" "$INSIDE" "$INSIDE-integration"
exit $status
