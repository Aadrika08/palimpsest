# TGT-PHASE-1: native target-dwell and homing-phase continuation

This prospective development gate closes the six explicitly missing native snapshot phases in the existing exploration/homing mechanism. It does not test a learned policy, held-out task competence, a new body, adaptive-body/task composition or physical operation. The existing [task plan](m6-exploration-homing.md), [task verifier](../../scripts/verify_tasks.py) and prior reports remain authoritative for their original observations; their failures are retained. No production profile, sensor, driver, outcome threshold or odometry changes are included here.

The frozen fixture uses seed 0, checker texture, manual CPU and the unchanged authored task world/body. Exploration uses the original `v1` artificial manual cue-following driver; homing uses the independently declared bounded `v2` driver and its existing evaluator-only actual-home closure limit of 0.25 m. Driver input is solely the previous recorded effective `sensors[2:4]` bearing. The first action is zero. Task state schedules snapshot capture only; true pose, task selection and evaluator measurements cannot choose or correct actions.

## Prospective snapshot predicates

Each predicate selects its first eligible **paused** boundary, independently of the other windows. The observer does not change the source command timeline.

| Profile | Snapshot | Exact predicate |
|---|---|---|
| Exploration | `selected` | Active target, no completed IDs, dwell 0 and positive measured encoder travel. No claim of current true body movement. |
| Exploration | `first-dwell` | Active target, no completed IDs, dwell exactly 1. |
| Exploration | `second-dwell` | Active target, exactly one completed ID, dwell exactly 1. |
| Homing | `outbound` | Exactly 8 numeric ticks, phase `outbound`, positive measured encoder travel. A missed predicate fails rather than selecting a later substitute. |
| Homing | `home-turn` | Phase `home`, dwell 0, previous effective bearing requests a `v2` in-place turn with absolute heading greater than 0.1 rad. |
| Homing | `home-dwell` | Phase `home`, dwell exactly 1. |

For each snapshot, record the source's next **up to four** `set_action`/`step` pairs with the existing IDs, requested actions, numeric arrays/cameras, raw `task_sensed` packets, full task state, outcome and isolated evaluator measurements. Stop a window early only if a command legitimately produces `task_completed` and task phase `complete`; never step a terminal engine. A short nonterminal window, collision, stall, missing predicate or incomplete source fails. Natural completion exactly on the fourth command is also valid. The source still runs to its existing natural task/actual-home completion gate within 600 ticks.

After each source closes, three sequential fresh owners restore its native phase snapshots. They apply the **saved source commands** once; `restore_branch` correctly clears display `last_transition`, so the verifier must not regenerate the first restored action from absent cue history. Initial task state, successor cursor, full task/outcome/evaluator, raw task packets and all recorded numeric arrays are compared with the existing comparator: float absolute/relative tolerance `1e-6`, exact camera/integer arrays. No tolerance changes. The per-interval evaluator retains encoder-versus-true displacement error and actual translation/yaw during quantized dwell; these are measurements, not feedback or a requirement of exact body rest. Both executable action and policy replays cover every source tick and semantic event from its registered initial snapshot. Source recording and native snapshot bytes remain immutable.

## Fixed bounds and retention

The [verifier](../../scripts/verify_task_phases.py) is thin orchestration over the existing driver, command, evaluator, native snapshot, replay, recorder, storage budget and bounded-process helpers. Its protocol is emitted and hashed before native work.

- Exactly 12 sequential native owners: two sources, six fresh phase continuations and four executable replays. No concurrent native owners or browser/server.
- At most 3,624 numeric intervals: `2×600 + 6×4 + 4×600`. Legitimate early completion reduces this count. Actual record counts are checked after each owner.
- Exactly 18 snapshots on complete success: two source initials, six phase captures, six restored initials and four replay initials. At most four associated snapshots per source run; each file at most 16 MiB. Partial failure retains the actual subset without inventing missing captures. Source/restored initial SNP sizes are checked immediately after registration; replay initial sizes are checked in its existing `ready` progress callback before any numeric step. These are post-publication checks under the aggregate storage quota, not per-file pre-publication writer limits; phase captures have the same immediate post-publication check.
- 180 s per owner; bounded whole-gate child 2,280 s. No retry, timeout extension or parameter tuning after failure.
- 2 GiB fresh managed output, 1 GiB free-disk floor, 256 MiB per recording, 1 MiB per native log/control report, 64 MiB bounded evaluator-row read/write and 8 MiB supervisor headroom. Actual `uint8` 128×128 camera shapes are required. The preflight reserves twelve 64 MiB row results, 26 MiB of native logs, 32 MiB of bounded control/results and 128 MiB of atomic/native staging, in addition to numeric records, snapshots and headroom. The first source admits the whole prospective plan before its initial snapshot: exactly 2,052,915,200 estimated bytes, below the unchanged 2 GiB quota (94,568,448 bytes remaining before existing writer headroom and current small metadata). Each later source admits its own remaining recording/snapshot writes against the fresh aggregate recount, rather than reserving the entire already-partially-written plan again. Preflight counts effective plus raw cameras, numeric/event allowance, maximum snapshot files, logs/control/results before the initial snapshot. Aggregate fresh recounts and existing write admission remain active; no quotas are increased.
- The first failure closes its engine in `finally`, retains partial rows, raw task events, boundary cameras/state/outcome and precise error, and leaves later owners explicitly `not_started`. The output is exclusive; failures are never overwritten. Source/hash failures also fail the gate.
- Finite 0.25 s descendant sampling binds PID and start time. Only still-matching owned processes may receive bounded TERM/KILL cleanup. Any forced containment, surviving sampled process, sampler error or source/hash change fails the positive gate. This is finite sampled cleanup evidence, not universal proof about transient processes.

Before actual authorization, retain an independent ignored launcher inventory of all tracked files excluding gitlinks, the exact clean upstream `8d964599119b420de67ee259434d273651a1a76d` tracked files, shared assets, clean verifier HEAD, this plan, script/protocol/helper SHA256 and exact argv. Write the exclusive after inventory **before** raising on a mismatch, regardless of gate outcome. The verifier additionally checks runtime/helper source and assets before/after, all immutable source recordings, final counts and hashes. A final external launch log must be hashed after its writer exits, never claimed immutable from an inner prefix hash.

## Prepared invocation; actual gate unexecuted

From the frozen `.worktrees/task-phases` checkout, using the existing cached interpreter and assets:

```sh
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 \
  ../lab-hardening/.venv/bin/python scripts/verify_task_phases.py \
  --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn \
  --output runs/m6-task-phase-development-20261003
```

The invocation acquires the existing storage lease and uses the existing `bounded_process` around its entire 2,280 s gate; each owner is independently supervised. Root must review the frozen launcher/source inventories and grant the exclusive actual runtime slot before executing it. Current qualification is **source/fixture only**. The separately proposed body-command interpolation and held-out start/layout/body/task gates are outside this slice.

## Observed single development gate

The frozen `8a931cf` invocation subsequently [passed](../reports/m6-task-phases.md): 12 normal owner exits, 1,470 numeric ticks, 18 native files, all six four-step continuations and all four complete executable replays. Capture boundaries were exploration 3/76/168 and homing 8/78/279. Every actual window remained paused; early terminal shortening remains fixture-only evidence. Dwell counters reset in the captured dwell windows, as retained in the report. Homing actual closure was 0.152449 m under the unchanged 0.25 m gate. All 193 indexed hashes and before/after tracked/upstream/asset inventories matched; finite cleanup observed no surviving PID/start identity or explicit forced containment. The [evidence index](../reports/m6-task-phases.json) preserves exact sources, metrics and limits. The prospective protocol above describes the original authorization; its prior unexecuted statement is historical, and no second invocation is authorized by this observation.
