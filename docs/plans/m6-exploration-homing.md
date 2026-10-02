# Declared exploration and encoder-homing development profiles

This slice connects the M6 pure mechanisms to the existing single-owner Engine,
application snapshots, worker samples, replay comparison and recorded playback.
It adds no body-gain runtime, puck controller, new dependencies or UI framework.
Both profiles remain development profiles. The bounded manual development gate
observed declared exploration completion, shaft/forward direction and executable
replay, but **actual homing failed**: estimated arrival was 0.0898 m while the robot
remained 1.5006 m from its true start. True stopping, held-out behavior and learned
competence remain unqualified. The raw verifier's `passed` label is its declared
estimated-state/mechanism gate, not true home closure or M6 release.

## Declared sensor/objective contracts

`exploration-landmarks` uses the reviewed authored memory-world layout without
running its hidden gate schedule. Two virtual landmarks lie at `[-1.75, 0]` and
`[-1, 0]`. Geometry is confined to the sensor acquisition boundary. The existing
`memory_task.capture_symbolic` producer supplies only visible IDs/bearings under
4 m range, +/-pi/2 field of view and circular-cylinder occlusion, including
tangency. A declared `near` bit is added only for visible landmarks at distance
<=0.25 m. No distance or coordinates enter the supervisor. This virtual proximity
channel is explicit; it is not a camera detector or physical range sensor.

The supervisor selects an unseen visible target deterministically and retains
its ID until inspection. It does not alternate targets each tick. A selected
target leaving visibility, or no visible unseen target after inspection, fails
without a hidden scan or replacement heading. `near` forces the actual command
to zero. Completion of an inspection requires five consecutive measured
intervals where both quantized shaft counts remain identical while that target
stays visible and near. Movement resets dwell. Only then is its ID recorded as
completed; both IDs must complete to end the task. ID/bearing selection counts
from the pure mechanism remain distinct from completed inspections.

`encoder-homing` never acquires base pose, goal coordinates or landmark geometry
in its task sensor adapter. It reads only the two named hinge angles and simulator
time. Reset initializes a local zero pose independent of true world coordinates.
During outbound travel the cue points toward local estimated `[1, 0]`; estimated
radial departure >=1 m switches permanently to home. Home bearing comes only
from the encoder estimate. Within 0.2 m estimated home distance, the cue is neutral
`[0,0]` and commands are held at zero. Five consecutive zero quantized increments
are required for completion. An episode cannot complete without its outbound
phase. Quantized apparent rest and estimated arrival do not prove actual rest,
true return, or lack of slip.

Both profiles retain the existing manual/FLYNN controller choices and exclude
the privileged geometry teacher. The supervisor replaces the upstream true-pose
goal bearing before FLYNN sees the existing allowed RGB/contact/bearing inputs.
It does not retrain the navigation checkpoint; competence on these new cues is
unqualified. During a hold, live inference still runs and finite raw outputs are
recorded consistently, but the supervisor forces the final action to zero.
Action replay bypasses inference and rejects a recorded nonzero hold action.

## Encoder/model grounding and bounded failures

The pinned upstream XML at `8d964599119b420de67ee259434d273651a1a76d` names
`left_hinge`/`right_hinge`, both with +Y axes; left/right wheel bodies are at
Y=+0.18/-0.18, with equal radius 0.06 m cylinders. The adapter reads radius and
track from the loaded body, checking cylinder/hinge types, unrotated symmetric
wheel bodies and the supported axes rather than substituting those values.
With body +X forward, positive +Y shaft rotation implies forward travel under
no-slip kinematics. The development fixture observed positive shaft and body
forward direction on straight intervals; its high-amplitude turn odometry failed
to match actual yaw. Broader calibration remains pending. The adapter never reads base qpos as an
encoder. It intentionally rejects unsupported body configurations.

The declared simulated encoder quantum is 0.001 rad; it emulates quantization,
not a purchased encoder specification. Packet tick/episode/time must match the
owned 0.02-second boundary, starting from the captured reset angles. Raw and
quantized jumps over 2pi rad/interval, nonfinite or missing angles, skipped/stale
packets, 600-tick or 20 m estimated wheel-travel exhaustion fail explicitly.
These are authored bounded experiment constants, not qualified physical safe
values or measured feasibility guarantees. Contact at acquisition halts before
another physics step; next-step contact, upstream stall and time limit terminate
without an invented success. Task failure/stop/disconnect clears control arrays.

Upstream goal-distance termination is ignored for these objectives. Its distance
is retained with an explicit upstream label. Homing termination additionally
reports true distance to the authored start as isolated evaluator data alongside
estimated home distance; this truth never corrects or drives the controller.

## State, replay and evidence boundary

Protocol identity binds thresholds, FOV, occlusion, encoder convention, objectives,
world identity and sensor/mechanism source hashes. Runtime task identity adds
loaded calibration. The manifest preserves both. Full bounded JSON task state
includes phase, target, completed IDs, dwell, selector counts, odometry and the
last acquisition tick. Engine application schema 4 persists/restores it with
episode/cursor/protocol checks. Existing schema 2/3 applications upgrade only
for older profiles; new tasks require their complete state. Native physics,
observation and neural/RNG restoration remain owned by the existing snapshot
layer and require separate actual continuation checks.

Authoritative `task_sensed`, `task_decision`, `task_cue` and `task_inspected` events
are compared in executable replay. Runtime provenance includes both new task
modules. Worker displays hide raw upstream bearing before the next owned task
tick; playback returns the retained task state from that tick's recorded event.
Both actual manual development sources were replayed in actions and policy modes
with matching recorded ticks/task events. This does not qualify a learned policy.
Mocked checks separately exercise comparators and inference/override paths.

Run the focused pure/mock checks:

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest \
  test_task_mechanics test_task_profiles test_engine.EngineTests \
  test_profiles.ProfileTests test_worker.QueueContracts \
  test_worker.ReplayTransport test_replay.ReplayValidation
```

The pinned upstream checkout is initialized locally. The actual development gate
below retained both sources, one progress snapshot per task, native continuation,
full manual actions/policy replay and evaluator measurements. Pending gates are
independent turning calibration, actual home closure, snapshots during target
dwell and both homing phases, and held-out layouts/paths with explicit criteria.
Use the existing isolated runtime watchdog and quota controls. Learned competence
and M6 release remain open.

Root review on 2 October 2026 ran 70 checks in 1.319 seconds: 65 passed and five
asset-backed checks were skipped. The source remained unchanged. The retained
index is `runs/m6-runtime-pure-20261002/report.json`, SHA-256
`ab705f262bb3b3f56afbf48249a705dbcc5691a3a7f2478a504a731ba7e3a6af`.
This is fixture/runtime-contract evidence only; actual gates above remain open.


## Actual manual development gate

[`scripts/verify_tasks.py`](../../scripts/verify_tasks.py) prepares two bounded,
sequential manual task demonstrations. Its fixed driver receives only the
previous recorded effective `sensors[2:4]` bearing: the first action is zero,
forward command is `0.5*clip(cos,0,1)`, and heading is `atan2(sin,cos)`. Neutral
bearing produces zero. The protocol and script hash are recorded before the
initial snapshot; no true pose, goal or task state is an input to the driver.
This is an artificial manual cue-following fixture, not a learned controller,
a trained adaptation result or a held-out evaluation. No tuning is permitted
inside the verifier.

After eight steps with measured encoder progress, it captures one paused native
snapshot. Four subsequent requested commands and task states are retained. A
fresh restored process repeats those commands and compares all recorded tick
fields except wall latency with the existing exact camera/integer and
`atol=rtol=1e-6` float profile, plus complete task JSON state. Action and policy
replay each start from the registered initial source snapshot; source hashes
must remain unchanged. Its declared mechanism pass requires `task_completed`, not
an operator stop, truncation or a selected target. That event is based on declared
estimated-state thresholds and cannot qualify true home closure. Each child has a hard watchdog
and recording byte quota, bounded native logs and explicit cleanup; outputs are
exclusive and failed outcomes remain retained.

Wheel dimensions/quantum, measured shaft direction, signed true forward motion,
encoder estimate versus true local displacement, and true displacement/yaw
during counted dwell are isolated evaluator measurements. They never correct
the cue or command. Quantized apparent rest can coexist with body motion;
commanded zero and estimated home arrival do not establish physical stopping
or true home closure. One progress snapshot does not cover target dwell or both
homing phases; those snapshots, additional layouts and held-out gates remain
pending despite the observed development mechanism/replay checks.

Run only after the actual runtime slot is released, using a fresh output:

```sh
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 \
  ../lab-hardening/.venv/bin/python scripts/verify_tasks.py \
  --assets ../r0-reproduction/data/assets/flynn \
  --output runs/m6-manual-tasks-development
```

Preparation checks are pure: six NumPy/comparator tests cover bounded declared
cue actions, isolation of the previous bearing, malformed cues, real completion
criteria, exact-image/fixed-float comparison and signed evaluator evidence.
A seventh check exercises the real Engine with SmallEnv fixture physics: action
application does not step; the idempotent receipt lookup and step helper produce
exactly one nonzero-action transition. This is helper-contract coverage, not a
physics proof. Syntax/help checks are separate from actual physics.

The single actual invocation at unchanged `05d788b` ran eight sequential owners
in 101.513572 seconds, exit 0. Exploration completed both declared inspections in
182 ticks. Homing completed its estimated arrival/dwell condition in 197 ticks,
but true home distance was 1.5006287 m versus estimated 0.0897618 m. Both paused
tick-8 snapshots matched four continuation ticks, and both full actions/policy
replays passed. All eight owners exited 0 and recording manifests completed;
sources/script stayed unchanged, with no semaphore warning or remaining scoped
worker command line observed. Cleanup does not include persisted PID/start-time
identities. See the [development evidence and next-step proposal](../reports/m6-task-development.md)
and [hashed index](../reports/m6-task-development.json). No retry or tuning was run.

The read-only audit exactly reproduced all 197 homing odometry states from raw
recorded angles. High-amplitude turns predicted −3.028027 rad cumulative yaw
against actual −1.565932 rad, with agreeing turn signs. Specific slip/contact
causality is unproven; independent low-amplitude calibration is proposed before
another demonstration. Actual homing remains failed and M6 remains open.

## Prepared separate bounded driver v2

The verifier retains driver `v1` as its default and preserves the failed
`runs/m6-tasks-development-20261002` evidence unchanged. Optional `--driver v2`
is a separately recorded manual protocol: first/neutral cue commands zero; when
the previous recorded cue angle has magnitude above 0.1 rad, it turns in place
with heading clipped to ±0.4 rad. Otherwise it commands forward 0.4 and the cue
angle. The driver still consumes only the previous effective bearing. It neither
reads true pose/goal nor changes the original nominal encoder odometry.

The independent [eight-trial calibration observation](body-calibration-development.md)
supported nominal dimensions over fixed low-amplitude commands after settling.
V2 stays within that measured command range, but mixed/transient generalization
is unproven. No fitted coefficient is integrated into the task or body.

For encoder homing, v2 must both emit `task_completed` and pass a separately
declared isolated evaluator true-home distance **<=0.25 m**. Missing/nonfinite
truth or larger distance fails; this measurement never feeds the cue or action.
V1 retains its old estimated-state gate. The native snapshot/replay comparison,
600-tick cap, watchdogs and byte quotas remain unchanged. Failed outcomes remain
retained, without retry or tuning.

Only after review/source freeze and release of the actual slot, run one fresh
homing validation:

```sh
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 \
  ../lab-hardening/.venv/bin/python scripts/verify_tasks.py \
  --assets ../r0-reproduction/data/assets/flynn \
  --output runs/m6-homing-driver-v2-development \
  --scenarios encoder-homing --driver v2
```

The added pure check covers zero/forward/alignment/clipped-turn commands and the
distinct true-home boundary, including preserving v1's estimate-only behavior.
No v2 actual run, held-out or learned-policy result is claimed.

## Limited actual browser observation

The root-run [browser index](../../runs/m6-browser-20261002/report.json), SHA-256
`01a72ff19e578f32ddd12716bc6e80332822ab75022758e31ed88c6ddc3f17a3`,
records two manual declared-task workflows passing (exploration 11.7 seconds,
homing 8.3 seconds; suite 21.6 seconds). Each accepts the loaded body calibration,
advances one source step, captures/restores a native snapshot, advances one
branch continuation step and displays matching recorded task state. Both final
owner responses are HTTP 200/closed. Runtime sources stayed unchanged; the
service exits SIGTERM −15 and its listener is absent. Copied browser results and
UI build log are retained in that directory. These are limited UI/state and
one-step continuation observations, not task completion, learned competence,
wheel-direction calibration, full replay or M6 release qualification.
