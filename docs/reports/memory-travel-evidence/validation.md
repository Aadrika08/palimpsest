# Validation against scientific frozen head 0f1f8ea

Complete default suite, no exclusions or partitions:

```sh
timeout --signal=TERM --kill-after=5 300s env \
  PYTHONPATH=.:src:scripts OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  /home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python \
  docs/reports/research-capability-execution/validation-invocation.py \
  -q -o faulthandler_timeout=45
```

915 passed, 24 skipped, 39 warnings in 132.62 s. The software invocation owns a
temporary Path.home cache fixture; HOME is unchanged. The actual scientific
invocation below used the real user lease and no Path.home substitution.

```sh
timeout --signal=TERM --kill-after=5 7190s env \
  PYTHONPATH=.:src:scripts OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  CUDA_VISIBLE_DEVICES= PYTHONDONTWRITEBYTECODE=1 \
  /home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python \
  -m scripts.memory_waypoint_study --amendment travel-handoff \
  --repo /home/utkarsh/Work/shraddha/brain/.worktrees/research-phase \
  --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn \
  --history-root /home/utkarsh/Work/shraddha/brain/.worktrees/memory-experiments \
  --output /home/utkarsh/Work/shraddha/brain/.worktrees/research-phase/runs/memory-travel-handoff-20261004T125507Z
```

Exactly one invocation. Exit 1, filesystem ENOSPC; no scientific task-failure
admission, no selected profile, no native retry. Do not rerun this command against
existing evidence. All eight prerequisites and the paired pilot are unattempted.

The recovery script is post-processing only. It operated within the original
600 s readout deadline using execution.json.pending because the canonical receipt
was stale. Its first software attempt called pre-allocation job validation against
an existing output and correctly refused that immutable output; the corrected
readout checked the retained job against the frozen candidate ledger instead.
It never launches an owner. It preserves the historical receipt and drafts.

Full-suite opt-in skips are not native qualification. Native partial recording
rows are readable but lack a terminal manifest and complete raw audit.
