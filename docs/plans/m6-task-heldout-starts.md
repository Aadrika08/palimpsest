# TGT-HO-START-1: frozen held-out start/task cases

This prospective diagnostic tests two new starts with each unchanged declared task profile. It closes a narrow held-out **start** coverage gap after the [six task-phase continuations](../reports/m6-task-phases.md). It does not establish held-out layouts, new-body competence, adaptive-body/task composition, learned-policy competence or physical operation. No production profile, Engine, sensor, driver, odometry, task threshold or public case API changes are included. The original task and homing failures remain retained in the [task plan](m6-exploration-homing.md).

## Frozen cases and action protocol

| Standalone case ID | Seed | Actual authored start `[x m, y m, yaw rad]` | Task/driver |
|---|---:|---|---|
| `ho-start-north-1001` | 1001 | `[-2.75, 0.15, 0.1]` | Exploration `v1`, then homing `v2` |
| `ho-start-south-1002` | 1002 | `[-2.75, -0.15, -0.1]` | Exploration `v1`, then homing `v2` |

All four source cases use manual CPU, checker texture and the unchanged authored task layout/body. The seed's original upstream reset/episode event stays in history; the canonical task layout is configured by the existing task mechanism. This is one layout with two declared start/yaw changes, not four independent environments. The pure geometry preflight checks arena/obstacle clearance and initial visibility of both declared landmarks at both starts. These checks do not establish reachability, contact-free trajectories or task success.

The artificial manual cue-following drivers are imported unchanged from [verify_tasks.py](../../scripts/verify_tasks.py). Their sole input is the **previous recorded effective** `sensors[2:4]` bearing. Initial action is zero. Exploration uses `v1`; homing uses the previously frozen `v2` turn-in-place/forward protocol. No task selection, true pose, home distance, calibration estimate or evaluator measurement feeds back into the driver. No retries, per-case adjustments or tuning after observed outcomes are authorized. Source order is north exploration, north homing, south exploration, south homing; each source is followed by its one actions replay before starting the next case.

## Explicit standalone pose override and native identity

Before any numeric interval, the source owner must be a pristine paused episode 0: physics time, episode/total/task cursors, qvel, controls, manual/last action, speed and stall count are zero. Drawing state, planner occupancy/obstacle/clearance caches and grid dimensions/origin must be empty. Exploration visited bins must contain only the current initial bin, with `_prev_xy` matching that pose. These guards reject stale state rather than silently clearing it.

The verifier reuses pinned upstream `place_robot`, calls `mj_forward`, updates only the pose-dependent `_prev_xy` and fresh exploration bin through `_reset_exploration`, and obtains fresh raw observation. It checks the resulting declared XY/yaw, zero shaft angles, unchanged model digest and unchanged fresh task state, then repeats the tick-0 guards. There is no physics step, goal/model/gear change, borrowed sensor packet or true-pose correction to local encoder odometry. The task's local origin/yaw frame remains its genuine initial encoder state.

A bounded `task_start_authored` event and source manifest record exact case, old/new pose, old/new world, model/task-profile/protocol identity and canonical override SHA256. The manifest `initial_world` describes the override, while the original `episode_started` remains history. The fresh authoritative initial native snapshot is registered after this event and before the first step.

This is **standalone evidence**. Existing generic artifact/playback readers can derive the world from the earlier episode event; they have not been changed or qualified for these overrides. The replay result/wrapper binds the immutable source case and recomputed override SHA, existing destination `replay_source_run_id`, and exact normalized source/destination initial native snapshots. Only `application.source_run_id`, `event_prefix` and `execution_mode` transport fields are removed for comparison; native bytes/integration, observation, model/profile, RNG and task/application fields remain bound. Closed replay manifests are never rewritten and ordinary readers are not widened. The existing strict same-software replay source guards remain in force.

## Outcomes and isolated evaluator

Each source runs unchanged commands to a normal task outcome, at most 600 intervals. Completed collision, stall, task completion and time-limit recordings are valid observed outcomes. An unsuccessful **natural** outcome is retained and action-replayed, and the next planned case still runs. Runtime failure, invalid/missing recording, malformed task/sensor state, replay divergence, source mutation, storage exhaustion or watchdog/cleanup failure stops the gate; remaining owners stay `not_started`. A replay is never fabricated for an invalid recording.

Exploration capability requires natural `task_completed`, task phase `complete` and exactly the two declared completed landmark IDs. Homing additionally requires evaluator-only true XY distance from its **declared authored origin** at most the unchanged 0.25 m limit. The report names this `declared_origin_actual_home_distance_m`, retains the exact declared origin and copies the Engine's existing `evaluator_actual_home_distance_m` outcome field unchanged. That existing field uses the production default origin; it is not renamed, overwritten or treated as the new criterion. Encoder-versus-true displacement, signed motion and quantized-dwell translation/yaw remain isolated diagnostics under the actual start/yaw frame.

Overall capability pass requires all four task criteria. If all eight recordings/replays are valid but any task criterion fails, the report is `failed-functional` with completed protocol and actual attempted/completed/successful case counts; it exits 1. A clean exit 1 is accepted as this outcome only when all planned recordings completed and the supervisor reports no error or failure. A log-limit/final-drain failure, timeout, signal or incomplete protocol is infrastructure failure, even if return code is 1. There is no empirical population success-rate claim from these four authored cases.

## Exact admission and containment

The [verifier](../../scripts/verify_task_starts.py) reuses existing driver, native initial registration, full actions replay/comparator, record writer, finite descendant sampler, PID/start-checked cleanup, storage recount/admission and `bounded_process` helpers.

- Eight sequential owners: four sources and four actions replays; no policy replays or repeated phase continuations.
- At most 4,800 numeric intervals, checked by contiguous episode-0 recording cursors after each owner. Each source/replay has the existing 600-tick cap. Valid natural failures can shorten traces.
- Eight initial SNPs on completed protocol, at most one per owner, each at most 16 MiB. Each initial is checked immediately after registration, or at replay's existing `ready` callback before stepping. These are post-publication checks under aggregate quota, not new per-file pre-publication writer limits.
- 180 s per owner; 1,560 s bounded inner gate; prospective external launcher 1,620 s. No timeout extension or rerun. Exactly one existing writer lease belongs to the verifier; the outer launcher must not acquire a second lease.
- Fresh 2 GiB managed output; 1 GiB free-disk floor; 256 MiB per recording; 1 MiB per log/control JSON; 64 MiB per evaluator-row result; 8 MiB supervisor headroom. No quotas or native/event limits are increased.
- Actual cameras must be `uint8` 128×128×3. Admission is exactly **1,840,775,168 bytes**: 983,040,000 numeric bytes, 134,217,728 snapshot bytes, 536,870,912 row-result bytes, 18,874,368 native-log bytes, 25,165,824 control bytes, 134,217,728 atomic/native staging bytes and 8,388,608 headroom bytes. The per-recording estimate is 124,977,152 bytes. Whole-plan admission occurs in the first source before initial registration/stepping; later sources admit remaining recording/snapshot writes against fresh aggregate usage. Existing individual writer admission and fresh recounts remain active.
- Every started source closes in `finally`; first-failure numeric rows, raw task events, boundary cameras/state/outcome and precise errors are retained. Source recording bytes are checked unchanged after replay. Assets/runtime/helper identities are checked before/after. Forced containment, sampled survivors, sampler errors or identity changes fail capability qualification.
- Finite 0.25 s sampling binds up to 256 observed descendant PID/start identities. TERM/KILL is limited to owned identities still matching at the moment. This is bounded sampled cleanup evidence, not universal transient-process proof.

Before actual authorization, a fresh ignored launcher must inventory all tracked source/tests/docs excluding gitlinks, pinned clean upstream `8d964599119b420de67ee259434d273651a1a76d` tracked files and shared assets; bind clean HEAD, script/protocol/plan/helper hashes and exact argv. Write the exclusive after inventory before raising on mismatch regardless of gate result. Retain final external logs only with hashes computed after their writers exit. No launcher or native execution is authorized by this source preparation.

## Prepared invocation and current evidence

```sh
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 \
  ../lab-hardening/.venv/bin/python scripts/verify_task_starts.py \
  --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn \
  --output runs/m6-task-heldout-starts-development-20261003
```

The focused [pure fixtures](../../tests/test_verify_task_starts.py) cover actual pure layout/symbolic preflight, complete allowance arithmetic, isolated declared-origin metrics, pristine pose/cache rejection, exact native normalization, real fixture-Engine natural time-limit publication and subprocess-boundary orchestration of unsuccessful natural outcomes versus infrastructure stops. They are not native physics/task success evidence. The actual eight-owner gate remains **unexecuted**, pending frozen source/launcher review and exclusive runtime GO. Body parameter generalization, task/body composition and fixed-FLYNN/learned task behavior remain separate gates.

## Observed single invocation

The frozen `03a8476` gate subsequently [passed](../reports/m6-task-heldout-starts.md): all four task criteria and full actions replays, eight normal owners, 1,980 numeric ticks and eight native initials. Each symmetric start produced exploration 203 ticks and homing 292 ticks; declared-origin true closure was 0.16283366951741848 m under the unchanged 0.25 m gate. The preserved Engine default-origin field was 0.37574258496009155 m and was not the standalone criterion. Root independently checked all 444 inventory files, 151 indexed artifacts, eight snapshot containers, full semantic streams and reconstructed driver actions; all ten sampled union PID/start identities were absent. All actual tasks completed, so natural unsuccessful-outcome continuation remains fixture-only coverage. The [evidence index](../reports/m6-task-heldout-starts.json) retains exact sources/audits and standalone-reader limits. The unexecuted statement above describes the prospective authorization; no second invocation is authorized by this observation.
