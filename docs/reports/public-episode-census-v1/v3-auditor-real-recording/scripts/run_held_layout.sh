#!/bin/sh
# usage: run_held_layout.sh <label> <source|replay> <source-run-id> <replay-run-id> <ticks>
# Diagnostic only. Empty tmpfs root with read-only /usr,/etc and interpreter; held paths:
# /puck/source (ae9bd81 tree), /puck/staged/inputs/root-0000 (held site), /puck/control/egl-vendor.json,
# /output (rw), /puck/source-run (replay, ro), /scratch tmpfs, /tmp -> scratch/tmp. Exact held ENVIRONMENT.
V=/tmp/claude-1000/-home-utkarsh-Work-shraddha-brain/ea2ee336-67d3-44c2-9213-2883eff1b2e7/scratchpad/episode-census/v3
SITE=/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-install-01/site
PYROOT=/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu
PY=$PYROOT/bin/python3.11
STAGED=/puck/staged/inputs/root-0000
LABEL=$1 PHASE=$2 SID=$3 RID=$4 TICKS=$5
OUTD=$V/out/$LABEL/$PHASE-output; DIAG=$V/out/$LABEL/$PHASE-diag; mkdir -p "$OUTD" "$DIAG"
if [ "$PHASE" = replay ]; then SRCBIND="--ro-bind $V/out/$LABEL/source-output /puck/source-run"; SR=/puck/source-run; else SRCBIND=""; SR=/output; fi
START=$(date +%s.%N)
bwrap --unshare-all --die-with-parent --clearenv \
  --ro-bind /usr /usr --symlink usr/lib /lib --symlink usr/lib /lib64 --symlink usr/bin /bin --symlink usr/bin /sbin \
  --ro-bind /etc /etc --ro-bind $PYROOT $PYROOT \
  --ro-bind $SITE $STAGED --ro-bind $V/root /puck/source --ro-bind $V/control /puck/control --ro-bind $V/probe /puck/probe \
  $SRCBIND --bind "$OUTD" /output --bind "$DIAG" /diag \
  --tmpfs /scratch --dir /scratch/home --dir /scratch/tmp --dir /scratch/assets --symlink scratch/tmp /tmp \
  --proc /proc --dev /dev \
  --setenv PYTHONDONTWRITEBYTECODE 1 --setenv LC_ALL C.UTF-8 --setenv LANG C.UTF-8 \
  --setenv HOME /scratch/home --setenv TMPDIR /scratch/tmp --setenv PWD /puck/source --setenv PATH /nonexistent --setenv TZ UTC \
  --setenv CUDA_VISIBLE_DEVICES '' --setenv MUJOCO_GL egl --setenv PYOPENGL_PLATFORM egl \
  --setenv MPLBACKEND Agg --setenv OMP_NUM_THREADS 1 --setenv MKL_NUM_THREADS 1 \
  --setenv OPENBLAS_NUM_THREADS 1 --setenv OPENBLAS_MAIN_FREE 1 --setenv GOTOBLAS_MAIN_FREE 1 \
  --setenv TORCH_DEVICE_BACKEND_AUTOLOAD 0 \
  --setenv PYGLFW_LIBRARY $STAGED/glfw/x11/libglfw.so --setenv MESA_SHADER_CACHE_DISABLE true \
  --setenv PYGAME_HIDE_SUPPORT_PROMPT hide --setenv __EGL_VENDOR_LIBRARY_FILENAMES /puck/control/egl-vendor.json \
  --chdir /puck/source \
  /usr/bin/timeout -s KILL 400 $PY -I -S -B /puck/probe/held_episode_probe.py $STAGED /puck/source /puck/probe/inputs.json /output $PHASE $SID $RID $SR $TICKS \
  > "$DIAG/stdout.txt" 2> "$DIAG/stderr.txt"
RC=$?
END=$(date +%s.%N)
echo "exit=$RC wall_seconds=$(echo "$END - $START" | bc)" > "$DIAG/process.txt"
cat "$DIAG/process.txt"
