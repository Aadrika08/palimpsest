# M4 memory mechanics evidence

M4 mechanics are complete on the default development world. M/E/U remain separate, U selects reinspection without rewriting facts, fresh declared observations establish values, and atomic U-only branches preserve world, M/E, controller, neural, RNG and supervisor state. This is not an R2 learned-transfer result.

The [development contract](../plans/m4-memory-mechanics.md) fixes the finite rule vocabulary, fitting/abstention thresholds and one-target bridge. The [world contract](../plans/m4-memory-world.md) defines independent geometric truth. Live M begins unknown, with empty E/U. Application schema v3 and exact typed hashes guard U-only restoration; action-replay snapshots and invalid guidance cannot allocate a live branch. Inspector and route annotations use recorded evidence and never feed policy inputs.

The runtime was measured at `23d5847`; later M3 documentation merging did not change its Python/lock hashes. The [JSON index](m4-memory-mechanics.json) binds the local retained reports and exact scope.

- **218 tests passed**, no skips, with actual MuJoCo/EGL enabled (67.757 seconds). Coverage includes rejection of unsupported certainty, missing/conflicting sensing, malformed U, state invariants, actual world changes and manual continuation/replay.
- **Full CPU FLYNN gate passed** in 200.164 seconds. An eight-tick source snapshot produced empty-U sham, local-rule and paired-rule branches. Invariant hashes matched for all three; the four-tick sham had zero maximum numerical difference. The authored rules selected their expected different inspection targets. Source recording and runtime files stayed unchanged.
- Both executable replays passed **four ticks and 33 events** each. Floating tolerance stayed 1e-6; cameras and integers were exact. Action replay bypassed inference. All six owners exited zero without survivors.
- UI build/typecheck passed. **Four actual manual browser workflows passed** (18.1/27.4/5.6/18.2 seconds): existing lab/replay/overlay flows plus memory inspection, rejected malformed upload, valid U-only branch, M/E preservation, evidence-linked keyboard navigation, overlay isolation and recorded playback. Four clean owner closes were retained; PID-only server SIGTERM left no listener. Desktop/mobile screenshots were inspected with no horizontal page overflow or browser exceptions.

The opt-in cadence benchmark was skipped intentionally; this is not a new frame-rate result. The first browser attempt is retained as failed: the disabled-option assertion was retargeted by the test framework, and cleanup incorrectly asserted an owner for the skipped benchmark. The corrected check reads the native option property; cleanup still requires a clean owner close for every successful workflow. No application behavior was weakened to pass those checks.

Scope: authored rules and one default world, not acquired training history, successful embodied reinspection, held-out transfer, CUDA or physical hardware. M5 retains those open gates. Raw bundles are ignored local artifacts under this worktree's `runs/`; the committed index preserves their identities.

Earlier pure integration evidence remains retained: [41 checks in 0.699 seconds](../../runs/m4-pure-integration-20261002/report.json), no skips, plus the Node route-annotation check. That fixture pass did not establish actual runtime behavior; the gates above now cover their stated native scopes.

Repeat the native gates from this worktree with the cached interpreter/assets and a fresh output directory:

```sh
PALIMPSEST_SIMULATION_TESTS=1 MUJOCO_GL=egl OMP_NUM_THREADS=2 PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest discover -s tests -v
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 ../lab-hardening/.venv/bin/python scripts/verify_memory.py --assets ../r0-reproduction/data/assets/flynn --controller flynn --output runs/new-memory-gate
```
