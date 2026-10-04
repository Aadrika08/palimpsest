# Verification of frozen implementation 235bd35

Pinned environment: Python 3.11.15, Torch 2.9.0, NumPy 2.2.5; upstream
`8d964599119b420de67ee259434d273651a1a76d`. Complete default suite: 896 passed,
24 skipped, 39 warnings, 122.47 seconds. No exclusions or partitions.

Reproduction uses the existing software verification helper:

```sh
timeout --signal=TERM --kill-after=5 300s env \
  PYTHONPATH=.:src:scripts OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  /home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python \
  docs/reports/research-capability-execution/validation-invocation.py \
  -q -o faulthandler_timeout=45
```

The helper supplies an owned temporary Path.home for cache tests; HOME and
production code stay unchanged. The actual scientific invocation used the real
per-user owner lease, without this test fixture:

```sh
timeout --signal=TERM --kill-after=5 7190s env \
  PYTHONPATH=.:src:scripts OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 \
  /home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python \
  -m scripts.memory_waypoint_study \
  --repo /home/utkarsh/Work/shraddha/brain/.worktrees/research-phase \
  --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn \
  --history-root /home/utkarsh/Work/shraddha/brain/.worktrees/memory-experiments \
  --output runs/memory-waypoint-20261004T120942Z
```

The output must be absent. This documents the single executed invocation; it is
not authorization to repeat it. The native prerequisite result failed. Scripted
exit 0 only acknowledges a completed bounded attempt. The retained-readout.py
script reads existing recordings and never allocates a native Engine. It requires
machine-local raw chunks/SNPs and the recorded monotonic readout deadline; the
publication copies alone cannot reproduce its raw audit.
