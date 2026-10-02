# Independent body-calibration diagnostic protocol

This prepared experiment follows the retained [actual homing failure](../reports/m6-task-development.md).
It has not run. It fits diagnostic coefficients offline; it adds no runtime
calibration, learned policy, physical qualification or online true-pose correction.
The existing failed homing path is not used as fitting data.

[`verify_body_calibration.py`](../../scripts/verify_body_calibration.py) predeclares
eight fresh manual trials, each 120 control ticks at 0.02 seconds:

| Trial | Forward command | Heading command |
| --- | --- | --- |
| Straight low | 0.2 | 0 |
| Straight high | 0.4 | 0 |
| Left turns | 0 | +0.1, +0.2, +0.4 (three separate trials) |
| Right turns | 0 | −0.1, −0.2, −0.4 (three separate trials) |

These are existing body-level velocity/heading commands, not target wheel rates.
The upstream mapping, actuator scales, friction and body remain unchanged. The
driver applies one fixed command for its entire trial and never consumes pose,
goal, shaft readings or fitted coefficients. Each child is bounded to 120 seconds
and a 64 MiB recording; no retry, relocation or amplitude adjustment is allowed.
Contact or early navigation termination rejects the trial and retains evidence.

The first 20 intervals are settling and excluded; only the next 100 fit. Raw
shaft angles, true planar pose, 3D position/quaternion, contact count, action and
control are recorded before/after each interval as evaluator data. True forward
displacement is projected along the midpoint measured body heading; true yaw
increments are wrapped locally. Raw encoders are used here, without the homing
quantization layer. Fitting uses zero-intercept least squares for:

* forward displacement / mean left/right shaft increment, in m/rad;
* yaw change / (right minus left shaft increment), in rad/rad.

Support requires all 100 finite fit intervals, input RMS at least 0.0001 rad and
output RMS at least 0.00001 m (straight) or rad (turn). Positive coefficients and
cumulative measured input/output directions must agree with the fixed command.
Every trial and the pooled fit must have relative RMS residual
`sqrt(sum(residual²)/sum(measured_output²)) <= 0.20`. Within each straight/turn
group, `(largest coefficient − smallest coefficient)/mean coefficient <= 0.20`.
These are predeclared **development rejection thresholds**, not physical safety
limits. Both groups must pass; otherwise accepted coefficients are absent while
diagnostic slopes/reasons remain visible. No empirically adjusted track/radius is
written into the body or task protocol. Loaded physical dimensions stay separate.

## Standalone world override and initial state

Each owner uses `Engine.open(manual, reproduction)` with no task or memory
supervisor. Before stepping it explicitly authors the existing clear memory-world
layout without a gate schedule, then shifts the robot to `[-5.5,0,0]`. This gives
the fixed straight trials more separation from the goal at `[-1,0]`; reaching the
goal early still fails. Geometry validation runs after authoring. The original
seeded `episode_started` event remains historical. A `calibration_world_authored`
event records old/new worlds, exact protocol and override hashes, and revision;
the manifest explicitly labels the standalone override and actual initial world.
Observation is refreshed and the registered initial native snapshot captures the
authored model/data/application before any action or step.

Actual initial world/pose and each measured pose are retained in trial results.
This is standalone calibration evidence. Ordinary reproduction, playback or
artifact readers may select the original episode event; their interpretation of
this override is not qualified by this script. There is no hidden profile switch,
task hold, hidden navigation policy or pose correction.

## Prepared check and future invocation

One pure fitting check accepts supported consistent synthetic coefficients and
rejects excess residuals, cross-amplitude disagreement, reversed direction,
missing intervals and absent excitation. It does not prove physics or that a
constant coefficient will fit this body.

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python -m unittest discover \
  -s tests -p test_verify_body_calibration.py
```

Only after the exclusive runtime slot is released, with a frozen source and fresh
output, run:

```sh
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 \
  ../lab-hardening/.venv/bin/python scripts/verify_body_calibration.py \
  --assets ../r0-reproduction/data/assets/flynn \
  --output runs/body-calibration-development
```

The protocol/script/source identities are written before collection and checked
at the end. Eight owners execute sequentially. A rejected fit exits nonzero;
raw recordings and per-trial results are retained. Any later runtime integration
requires independent review, a new declared calibration identity and separate
validation paths. Held-out evaluation remains separate and pending.
