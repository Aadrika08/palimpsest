#!/bin/sh
# usage: run_held.sh <label> <source|replay> <source-run-id> <replay-run-id> <ticks>
# Diagnostic only. Read-only root, clean env, offline, PATH=/nonexistent, qualification env + held additions.
V=/tmp/claude-1000/-home-utkarsh-Work-shraddha-brain/ea2ee336-67d3-44c2-9213-2883eff1b2e7/scratchpad/episode-census/v2
SITE=/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-install-01/site
PY=/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11
LABEL=$1 PHASE=$2 SID=$3 RID=$4 TICKS=$5
OUTD=$V/out/$LABEL/$PHASE; mkdir -p "$OUTD"
if [ "$PHASE" = replay ]; then SRCBIND="--ro-bind $V/out/$LABEL/source /tmp/source"; else SRCBIND=""; fi
START=$(date +%s.%N)
bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp \
  --ro-bind $V/scripts/held_episode_probe.py /tmp/p.py --ro-bind $V/root /tmp/root --ro-bind $V/inputs.json /tmp/inputs.json \
  --ro-bind $V/egl /tmp/egl $SRCBIND --bind "$OUTD" /tmp/out --unshare-all --die-with-parent --clearenv \
  --setenv PYTHONDONTWRITEBYTECODE 1 --setenv LC_ALL C.UTF-8 --setenv LANG C.UTF-8 \
  --setenv HOME /tmp/home --setenv TMPDIR /tmp/tmp --setenv PATH /nonexistent --setenv TZ UTC \
  --setenv CUDA_VISIBLE_DEVICES '' --setenv MUJOCO_GL egl --setenv PYOPENGL_PLATFORM egl \
  --setenv MPLBACKEND Agg --setenv OMP_NUM_THREADS 1 --setenv MKL_NUM_THREADS 1 \
  --setenv OPENBLAS_NUM_THREADS 1 --setenv OPENBLAS_MAIN_FREE 1 --setenv GOTOBLAS_MAIN_FREE 1 \
  --setenv TORCH_DEVICE_BACKEND_AUTOLOAD 0 \
  --setenv MESA_SHADER_CACHE_DISABLE true --setenv PYGAME_HIDE_SUPPORT_PROMPT hide \
  --setenv PYGLFW_LIBRARY $SITE/glfw/x11/libglfw.so --setenv __EGL_VENDOR_LIBRARY_FILENAMES /tmp/egl/50_mesa.json \
  --chdir /tmp \
  /usr/bin/sh -c "/usr/bin/mkdir -p /tmp/home /tmp/tmp /tmp/assets && exec /usr/bin/timeout -s KILL 400 $PY -I -S -B /tmp/p.py $SITE /tmp/root /tmp/inputs.json /tmp/out $PHASE $SID $RID /tmp/source $TICKS" \
  > "$OUTD/stdout.txt" 2> "$OUTD/stderr.txt"
RC=$?
END=$(date +%s.%N)
echo "exit=$RC wall_seconds=$(echo "$END - $START" | bc)" > "$OUTD/process.txt"
cat "$OUTD/process.txt"
