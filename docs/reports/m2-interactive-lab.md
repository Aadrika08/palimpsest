# M2 interactive lab evidence

M2 implements the local interactive workflow, actual-input inspection, six R1 scenarios, full-state branching, three replay modes, sequential comparison and SVG/PNG/bundle exports. **This is not the M3/R1 release qualification.** Aggregate storage hardening, endurance, operational recovery and performance gates remain separate.

## Observed results

- **145 Python tests passed**, with actual EGL checks enabled and no skips. Coverage includes lifecycle, masks, geometry, snapshots, registered-file hashes, command ordering, owner admission/eviction, disconnects, process-group watchdogs, replay, recording integrity and exports.
- The actual browser workflow exercised live obstacle relocation with one applied receipt, paused snapshots, two sequential branches with a declared world edit, comparison provenance, actual masked-eye pixels, manual blur clearing, reload recovery, playback and export. A separate browser workflow verified action/policy replay, disconnect pause, reload without fabricated display samples, explicit resume, cancellation and authenticated bundle checksums.
- The full FLYNN **CPU** owner gate passed: eight source ticks, four exactly matching continuation ticks, and a second branch with an obstacle relocation applied during travel at global tick 6. Action and policy replay each matched eight ticks and 22 lifecycle events. SVG, PNG and registered-snapshot bundle export completed. The complete gate took 143.917 seconds, including five sequential model loads; this is not an inference latency measurement.
- Manual and analytical-teacher owner gates also passed, including exact continuation, both executable replays and all export formats. The teacher retains privileged geometry access.
- A separate **30-tick masked FLYNN CPU continuation** matched all compared physics, camera, hidden/retinal and RNG values across fresh processes. Masked preprocessing matched the pinned upstream converter. Every measured maximum absolute error was zero; the registered tolerance remains `atol=rtol=1e-6`, with exact camera/integer comparisons.
- CLI playback, comparison, bounded action replay and bundle export were exercised. Every exported bundle member checked in the CLI gate matched its recorded SHA-256 and byte count.

Machine-readable evidence is indexed in [m2-interactive-lab.json](m2-interactive-lab.json). Raw bundles and screenshots remain under ignored `runs/` and `ui/.lab-test-runs/` in the interactive-lab worktree. The source identities in those bundles are retained; no source metadata is rewritten to hide development runs.

## Reproduce

Prepare the pinned Python simulation/lab extras, Node version and UI build described in [README](../../README.md), then run:

```sh
PALIMPSEST_SIMULATION_TESTS=1 MUJOCO_GL=egl OMP_NUM_THREADS=2 uv run --no-sync pytest -q
uv run --no-sync python scripts/verify_lab.py --controller flynn \
  --assets data/assets/flynn --output runs/new-lab-gate
uv run --no-sync python scripts/verify_execution.py --controller flynn --device cpu \
  --assets data/assets/flynn --mask-left --continuation 30 --output runs/new-mask-gate
```

Use a new output directory for each run. `verify_lab.py` creates and reaps one spawned owner at a time. Its live intervention is exploratory: the test does not require a particular behavioral effect or present different-duration traces as a controlled causal estimate. Browser commands and prerequisites are in [ui/README.md](../../ui/README.md).

## Contracts and limitations

The API binds to loopback, checks host/origin/session, bounds messages and uses generated registered IDs. One spawned process owns all mutable simulation/controller state. Only display samples may be replaced. Accepted commands receive an applied boundary or an explicit rejection. A completed owner is reaped before another starts; only eight recently completed owner descriptions remain in memory.

Snapshots bind the actual world, wrapper/controller/RNG/command state and durable event prefix. Branch, replay and bundle export verify the file against its authoritative registration hash. Explicit controller replacement starts fresh controller state and is recorded as such. Native snapshot decoding is for trusted compatible local artifacts, not hostile imports.

Playback invokes no simulation or inference. Action replay restores the compatible source profile, then advances with recorded actions while skipping inference. Policy replay reexecutes the recorded controller. Replay transport pause/resume never changes the source engine timeline. Failure, cancellation and first divergence remain explicit; the final `replay-report.json` includes close-time checks. Snapshot registration and all relevant runtime/lock/upstream hashes must match; older incompatible recordings fail clearly.

CUDA remains available only by explicit selection. Its upstream CSR numerical variation and strict-continuation failure are documented in [M1](m1-execution.md); M2 does not qualify CUDA repeatability. No original checkpoint training lineage, new learned navigation competence, memory effect, anatomy result, physical capability or release-endurance claim follows from these checks. Assets retain their original licence restrictions.
