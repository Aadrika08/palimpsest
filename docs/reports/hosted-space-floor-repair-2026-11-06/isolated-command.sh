#!/usr/bin/env bash
set -u
cd /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite || exit
report=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/ci-isolated-first-20261106/runs/ci-isolated-first-repair-20261106
[ ! -e /home/utkarsh/.cache/palimpsest-pytest/source-ci-isolated-first-20261106-01/isolated ] || exit 2
env -i PATH=/usr/bin:/bin HOME=/home/utkarsh LANG=C.UTF-8 LC_ALL=C.UTF-8 TMPDIR=/tmp \
  PYTHONDONTWRITEBYTECODE=1 \
  PYTHONPATH=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/src:/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts:/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/tests \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  MUJOCO_GL=egl CUDA_VISIBLE_DEVICES= \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q -p no:cacheprovider \
  --basetemp /home/utkarsh/.cache/palimpsest-pytest/source-ci-isolated-first-20261106-01/isolated \
  -m process_isolated \
  tests/test_male_navigation_v3.py \
  tests/test_puck_bundle_provenance.py \
  tests/test_puck_cpu_held_runtime_audit.py \
  tests/test_puck_retained_installation.py \
  tests/test_puck_python_louvain_build.py > "$report/isolated.log" 2>&1
status=$?
printf '%s\n' "$status" > "$report/isolated.exit-code"
cat "$report/isolated.log"
exit "$status"
