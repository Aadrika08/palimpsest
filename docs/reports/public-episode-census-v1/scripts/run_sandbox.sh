#!/bin/sh
# usage: run_sandbox.sh <label> <MODE> <PATH-value> <extra-path-or-empty> <dri:0|1> <ABSENT> <HIDDEN> <EXTRA_REG-file-or-empty> ["K=V ..." extra env] [four-imports 1|0]
# Diagnostic only. Read-only root, clean env, offline, qualification environment values.
set -e
E=/tmp/claude-1000/-home-utkarsh-Work-shraddha-brain/ea2ee336-67d3-44c2-9213-2883eff1b2e7/scratchpad/episode-census
SITE=/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-install-01/site
REG=/home/utkarsh/.codex/worktrees/0071/brain/docs/reports/puck-cpu-held-qualification-10/raw/control/dependencies.json
PY=/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11
LABEL=$1 MODE=$2 PATHV=$3 EXTRA=$4 DRI=$5 ABSENT=$6 HIDDEN=$7 EXTRAREG=""
[ -n "$8" ] && EXTRAREG=$(cat "$8")
EXTRAENV=""; for kv in $9; do EXTRAENV="$EXTRAENV --setenv ${kv%%=*} ${kv#*=}"; done
FOUR=${10:-1}
OUTD=$E/out/$LABEL; rm -rf "$OUTD"; mkdir -p "$OUTD"
DRIARGS=""; [ "$DRI" = 1 ] && DRIARGS="--dev-bind /dev/dri /dev/dri"
START=$(date +%s.%N)
set +e
bwrap --ro-bind / / --dev /dev $DRIARGS --proc /proc --tmpfs /tmp \
  --ro-bind $E/scripts/episode_census_probe.py /tmp/p.py --ro-bind $E/root /tmp/root --ro-bind $E/meta /tmp/meta \
  --bind "$OUTD" /tmp/out --unshare-all --die-with-parent --clearenv \
  --setenv PYTHONDONTWRITEBYTECODE 1 --setenv LC_ALL C.UTF-8 --setenv LANG C.UTF-8 \
  --setenv HOME /tmp/home --setenv TMPDIR /tmp/tmp --setenv PATH "$PATHV" --setenv TZ UTC \
  --setenv CUDA_VISIBLE_DEVICES '' --setenv MUJOCO_GL egl --setenv PYOPENGL_PLATFORM egl \
  --setenv MPLBACKEND Agg --setenv OMP_NUM_THREADS 1 --setenv MKL_NUM_THREADS 1 \
  --setenv OPENBLAS_NUM_THREADS 1 --setenv OPENBLAS_MAIN_FREE 1 --setenv GOTOBLAS_MAIN_FREE 1 \
  --setenv TORCH_DEVICE_BACKEND_AUTOLOAD 0 $EXTRAENV --chdir /tmp \
  /usr/bin/sh -c "/usr/bin/mkdir -p /tmp/home /tmp/tmp /tmp/assets && exec /usr/bin/timeout -s KILL 300 $PY -I -S -B /tmp/p.py $SITE /tmp/root/src /tmp/root /tmp/assets /tmp/out $MODE $REG '$ABSENT' '$HIDDEN' '$EXTRAREG' '$EXTRA' 12 7 $FOUR" \
  > "$OUTD/stdout.txt" 2> "$OUTD/stderr.txt"
RC=$?
END=$(date +%s.%N)
echo "exit=$RC wall_seconds=$(echo "$END - $START" | bc)" > "$OUTD/process.txt"
cat "$OUTD/process.txt"
