# M6 pure mechanism slice

Base: `4cf9674`; upstream source inspected read-only at pinned
`8d964599119b420de67ee259434d273651a1a76d` in the `lab-hardening` worktree.
The new `task-profiles` worktree does not initialize or download that submodule.
Only `task_mechanics.py`, its pure checks, and this document change.

Run the checks without simulator/model imports:

```sh
PYTHONPATH=src python tests/test_task_mechanics.py
```

These are synthetic mechanism checks. They do not complete M6: the approved
implementation plan additionally requires functional demonstrations, failure
handling in the runtime, explicit lineage, and held-out evaluation for every
task, including a separately trained puck controller. No engine, profile, API,
UI, snapshot, training, or physical integration is implemented here. No model,
MuJoCo/EGL, training, or device job was run for this slice.

## Contracts and interpretation

All inputs and outputs are plain JSON dictionaries/lists/scalars. Exact fields,
finite numbers, numeric types (excluding booleans), versions, counters and list
lengths are validated. Functions do not mutate caller inputs. Structural caps
are 4096 landmark IDs of at most 128 characters, 8192 calibration samples,
signed encoder counts within `2**53 - 1`, and counters within `2**31 - 1`.
These caps bound storage; they are not physical safe values. Invalid or exhausted
inputs raise `MechanismError` before a new state or control is returned. The
caller owns protocol constants, calibration provenance, packet timing/freshness,
and runtime failure handling. JSON roundtripping is checked; snapshot integration
and continuation are unqualified.

`initial_exploration` stores caller budgets and an initially empty `visits` map.
`choose_landmark` accepts exactly `{"landmarks": [{"id": ..., "bearing_rad": ...}]}`.
Among declared visible IDs it chooses the smallest count, then lexical ID; unseen
IDs have count zero. It increments that ID's inspection count. A “visit” here is
one visible selection/inspection, not evidence of physical arrival, spatial
coverage, a visual detector, or a successful exploration policy. Missing cues
raise `CueUnavailable`; there is no hidden map, scan, or arbitrary replacement
heading. ID/bearing alone cannot establish landmark arrival.

`initial_odometry` captures the initial unwrapped encoder angles and defines
estimated local `(x, y, yaw) = (0, 0, 0)`. Caller inputs are fixed effective wheel
radius, track width, encoder quantum, step/travel budgets, and per-update jump
limit. Both wheel angles must be signed so positive means forward travel. The
initial angle values need not be zero. `quantized_encoder_increments` rounds
cumulative angles half away from zero, then differences counts; repeated
sub-quantum motion is retained across updates. `odometry_step` checks raw and
quantized jumps, applies the exact differential-drive arc, and tracks cumulative
absolute wheel travel. `home_bearing` points only toward the estimated local
origin and returns no bearing within the caller's arrival radius. There is no
true-pose correction, wheel slip observation, or independent test of encoder
truth. A plausible false stream produces a false estimate, explicitly exercised
by a fixture. The square fixture closes the estimate, not a physical trajectory.

`fit_wheel_gains` fits each wheel's measured angular rate as `gain * control`
through the origin. Samples contain two actual controls, measured encoder angle
increments, measured interval seconds, and an interval contact flag. Callers
declare sample bounds, excitation threshold, positive gain bounds, control/dt/
rate limits, absolute residual limit and relative RMSE limit. Weak excitation,
any contact, nonfinite data, out-of-protocol samples, residual outliers and poor
fit reject the whole fit. No silent filtering occurs. `compensate_wheels` scales
nominal controls by nominal/measured gains, bounded by a caller ratio. Exceeding
control limits raises `SaturationError`; it never silently clips. No measurement
noise model, confidence interval, adaptation success, or stable dynamic plant is
inferred from these fixtures. Calibration and evaluation samples must later be
separated; accepting a fit is not held-out compensation evidence.

## Smallest runtime hooks still needed

1. Exploration: adapt the visible `id`/`bearing_rad` entries produced by
   `memory_task.capture_symbolic` (line 48) into the exact packet above. That
   existing producer uses declared geometry with range/FOV/occlusion limits; it
   is not image recognition. Add an explicit episode supervisor in
   `Engine._step` (`engine.py`, line 407) to select an observed bearing, record
   its packet ID/tick and decision, and halt/pause when cues or budgets fail.
   Define a reached/inspection protocol before claiming waypoint visits.
2. Homing: pinned `MuJoCoTwoCamEnv` already resolves `left_hinge`/`right_hinge`
   (`environment/mujoco_two_cam_env_random_obstacles.py`, lines 135–136).
   Expose their unwrapped shaft angles through a declared encoder adapter,
   establishing forward sign and measured quantum; source fixed radius/track
   from the actual loaded body/calibration. Advance odometry at the owned tick,
   replacing the home cue with the estimate only. Upstream `_sensor_vec` (line
   700) derives `wind_direction` from true goal/base pose: it must not be reused
   for encoder-only homing. True pose may remain isolated evaluator data.
3. Body gains: upstream `step` (line 313) converts velocity/heading through
   `vel_angle_to_action`, normalizes wheel controls, scales by `_action_scale`,
   then writes `data.ctrl`. The XML actuators are torque motors, not velocity
   servos. Introduce a single explicit adapter at this wheel-control boundary;
   log controls in the exact units used by fitting and compensation, encoder
   increments, measured dt and any contact over the entire interval. A bounded
   steady-window calibration protocol must reject transient/dynamic poor fits;
   gains are protocol-specific. Do not identify them with radius, track or slip.
4. Lifecycle: `profiles.validate` presently exposes navigation scenarios and
   manual/teacher/FLYNN controllers. Add explicit task identities/protocol hashes
   before activating these mechanisms. Extend snapshot application state and
   identity for these versioned JSON states and calibration/protocol identities;
   qualify pause/restore continuation separately. Current `snapshots.py` owns
   complete runtime snapshots; serializable mechanism state alone is insufficient.

Stop a later pilot on absent/invalid/stale cues, malformed encoder packets,
budget exhaustion, contact in calibration, weak excitation, rejected fit,
compensation saturation, nonfinite inference, or unresolved sensor privilege.
Choose actual stop actions and physical limits only from a reviewed runtime or
hardware protocol. Functional and held-out demonstrations remain outstanding.

## Retained verification

Root reran all 12 synthetic checks with Python 3.11.15; all passed in
0.007 s with no skips. `runs/m6-mechanism-check-20261002/report.json`
records the command, unchanged before/after source hashes and log hash; its
SHA256 is `6eed63e46c3a04c0a95dcb4c4697c8bf31e590e2979054b092f595b8767c346a`.
The run directory is ignored local evidence, not a portable CI artifact.
