#!/bin/bash
set -uo pipefail
ulimit -n 65536
unset PALIMPSEST_SIMULATION_TESTS PALIMPSEST_MALE_TORCH_CHECKS PALIMPSEST_MALE_RUNTIME_TESTS PALIMPSEST_MALE_RUNTIME_OUTPUT PALIMPSEST_TEST_ASSETS PALIMPSEST_TEST_PUCK_TORCH PALIMPSEST_BUILD_NAMESPACE_TEST PALIMPSEST_INSTALL_FIXTURE
export PALIMPSEST_PYTHON=/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python
export PATH="/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/runs/runtime-reference-v1-canonical-20261106/bin:/usr/bin:/bin"
date -u +%FT%TZ
git rev-parse HEAD > "/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/runs/runtime-reference-v1-canonical-20261106/frozen-head.txt"
bash scripts/run_tests.sh
result=$?
printf '%s\n' "$result" > "/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/runs/runtime-reference-v1-canonical-20261106/canonical-test-exit-code"
tar -cf "/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/runs/runtime-reference-v1-canonical-20261106/tmpfs-authored-fixtures.tar" -C /tmp .
copy_result=$?
printf '%s\n' "$copy_result" > "/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/runs/runtime-reference-v1-canonical-20261106/artifact-copy-exit-code"
if [ "$copy_result" -ne 0 ] && [ "$result" -eq 0 ]; then result=$copy_result; fi
printf '%s\n' "$result" > "/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/runs/runtime-reference-v1-canonical-20261106/exit-code"
date -u +%FT%TZ
exit "$result"
