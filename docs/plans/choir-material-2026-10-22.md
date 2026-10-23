# Public Choir material allocation — 22 October 2026

User authorized the next bounded real-FLYNN recording in conversation. This is
artwork material generation, not a new scientific study or a retry of prior work.

- Reuse `Engine.open`, real FLYNN CPU, reproduction/checker and pinned public
  graph/checkpoint. EGL rendering; two Torch/OMP threads, one BLAS thread.
- One model owner; initial seed 0, reset seeds 1–63 in order. At most 64 episodes.
  Retain goals, collisions, stalls and time limits without selecting outcomes.
- Stop after the first naturally ended episode with at least 6,000 intervals.
  At most 6,600 source intervals and 2 GiB source bytes. The existing 600-step
  episode limit is unchanged. No action overrides, world edits or eye masks.
- Full source recording includes effective/raw cameras and population telemetry.
  No inference substitution, padding, looping or automatic retry.
- Recording child: 7,200-second wall deadline including loading. Offline export
  child: 300 seconds. Existing supervisor owns process-group TERM/KILL cleanup,
  caps each log at 1 MiB and retains failure diagnostics.
- One fresh output root, 3 GiB aggregate budget, 2 GiB free-space floor and 8 MiB
  control/log headroom. Parent holds the existing per-user writer lease; children
  share its storage contract without reacquiring the lease.
- Require committed clean source before invocation. Registration records source,
  plan and lock hashes, Git head, fresh run UUID and fixed limits. Native Engine
  recording retains actual assets, runtime diagnostics and upstream identities.
- Source exhaustion, timeout, malformed records, cleanup failure or byte-limit
  violation stops export. Preserve the failed allocation; do not rerun silently.
- Export the first 6,000 actual intervals through `sonify(..., episode=None)`;
  all three fixed voices, version-2 episode provenance, exactly 120 seconds.
- Before treating material as delivered, independently inspect registration,
  terminal counts, source/output hashes, native outcomes and supervisor cleanup.
  Browser packaging and listening/artistic acceptance remain separate gates.

Execution after fixture verification and source commit:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
  .venv/bin/python -B scripts/record_choir_material.py \
  --output runs/choir-material-2026-10-22-v1
```

This consumes one new allocation. Account quota telemetry is unavailable.
