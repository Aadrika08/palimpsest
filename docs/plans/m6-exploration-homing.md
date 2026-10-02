# Declared exploration and encoder-homing development profiles

This slice connects the M6 pure mechanisms to the existing single-owner Engine,
application snapshots, worker samples, replay comparison and recorded playback.
It adds no body-gain runtime, puck controller, new dependencies or UI framework.
Both profiles are development profiles: no actual functional, held-out, stopping,
calibration, native restore or runtime replay qualification has been claimed.

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
no-slip kinematics. This source-grounded sign convention still needs a measured
runtime direction/calibration trial. The adapter never reads base qpos as an
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
The actual replay runner has not been executed for these profiles. Mocked checks
exercise its tick/event comparators and both inference/override paths.

Run the focused pure/mock checks:

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest \
  test_task_mechanics test_task_profiles test_engine.EngineTests \
  test_profiles.ProfileTests test_worker.QueueContracts \
  test_worker.ReplayTransport test_replay.ReplayValidation
```

Pending actual gate: initialize the task worktree's pinned upstream checkout from
the already available local source; verify source/model identities; measure wheel
signs, quantum and dimensions; run both profiles with retained sensor/control
packets; pause during target approach/dwell and both homing phases; capture native
snapshots; continue original/restored runs; execute full actions/policy replay;
measure actual home closure versus estimate and dwell motion; then evaluate
held-out layouts/paths with explicit success/failure criteria. Use the existing
isolated runtime watchdog and quota controls. No model downloads, environment
changes or runtime jobs were performed by this slice. Learned competence and M6
release remain open even if manual or synthetic checks pass.

Root review on 2 October 2026 ran 70 checks in 1.319 seconds: 65 passed and five
asset-backed checks were skipped. The source remained unchanged. The retained
index is `runs/m6-runtime-pure-20261002/report.json`, SHA-256
`ab705f262bb3b3f56afbf48249a705dbcc5691a3a7f2478a504a731ba7e3a6af`.
This is fixture/runtime-contract evidence only; actual gates above remain open.
