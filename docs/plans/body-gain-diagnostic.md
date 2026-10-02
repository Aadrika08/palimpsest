# Fixed wheel-response development diagnostic

Protocol v2 preparation only: no actual collection has run for this version. This diagnostic
does not change Engine, task profiles, odometry, physical wheel dimensions, or
controls. Acceptance is a prerequisite for reviewing any compensation proposal;
it does not authorize integration.

Protocol v1 ran once at `27b9990` and was **rejected** in 30.3621 seconds:
[`report.json`](../../runs/m6-body-gain-diagnostic-20261002/report.json), SHA256
`7f8c14fd1d68ecfd484b9ac4744b3be6f6af2de505e4d24147d0cef9e3a5b523`.
All eight trials retained one settling interval, each with ten complete timed
callback packets and cleanup, and exited 1. The global contact rule rejected
4,800 floor–obstacle support pairs across 80 stages; there were no unexpected
rover contacts in those packets. Thus there is no accepted fit or gain contrast.
The obstacle bodies have three soft-limited slide joints, including z; observed
support distances change during the interval, so they are not exactly stationary.
V2 corrects the structural scope to **unexpected robot-incident contacts** while
retaining every world-only contact. It does not change commands, scene, settling,
trial count, or fit limits. The original rejection and all packets remain immutable.

[`verify_body_gains.py`](../../scripts/verify_body_gains.py) declares eight fresh
manual CPU trials: baseline and left-motor scalar gear multiplied by `0.8`, each
with straight actions `[-.2,0]`, `[-.4,0]`, `[.2,0]`, `[.4,0]`. The frozen script
declares the exact forward-then-reverse execution order. Each child has a 120-second
watchdog and 64 MiB recording limit. Every trial takes 120 control ticks; the first
20 are excluded from fitting, with all 100 remaining intervals retained. There
are no retries, relocations after startup, response-based command changes, or
changes to acceptance thresholds after a failure.

The driver receives only its fixed action. The evaluator reads raw shaft angles,
actual `data.ctrl`, measured simulation time, and derived pose caches; true pose
never affects commands or fitted wheel response. The exact nominal two-motor
ordering and gear rows `[3,0,0,0,0,0]` are required before the override. Only the
left row's scalar is multiplied. The original and actual world, gear matrix,
immutable-model digests, physical radius/track, and initial sample are recorded.
The original seeded episode remains history. A separate authored event and
manifest identify the override before an initial native snapshot is registered.

The lane uses the existing authored memory-world obstacle layout, no schedule or
task/memory supervisor, start `[-3.5,0,0]`, and goal `[-3.5,3]`. The goal is away
from the nominal straight path in both directions. Startup geometry is validated;
this choice does not guarantee a perturbed trajectory is collision-free. Early
termination or contact rejection fails that trial rather than moving the rover.
These are standalone calibration records. Generic reproduction/playback and
restoration of the gear-perturbed initial snapshot are not qualified by this gate.

The existing `fit_wheel_gains` fits zero-intercept rate/control slopes per wheel
for each 100-interval trial and for each condition's 400 pooled intervals. Frozen
development limits are gain `[1,100]` rad/s/control, control magnitude at most 2,
dt `.02 ± 1e-9` seconds, rate at most 100 rad/s, excitation at least 1 (sum of
squared controls per wheel), per-sample absolute residual at most 2 rad/s, and
relative RMS at most 20%. Four trial gains within a condition must also have
range/mean at most 20% per wheel. Missing support, nonpositive direction response,
contact, or any failed limit rejects the fit. These are development rejection
limits, not physical safety specifications or universal torque-to-velocity laws.
Neither an accepted slope nor an observed gain ratio is applied to controls.

## Contact packet contract

One child owns the global callback. It rejects an existing `mjcb_control` before
environment construction or installation and removes its own callback in
`finally`, before closing Engine. An unexpected replacement is rejected and is
not silently overwritten. The probe requires MuJoCo 3.3.6, Euler enum 0, timestep
`.002`, frame skip 10, and enabled contacts/actuation; installed enum values and
local header hashes are retained. Model/data native addresses must match each
callback. Every interval must have ten packets at `start + i*.002`, invariant
finite actual controls, and an end time `start+.02`.

Ownership is derived from the native model's complete body ancestry below `base`,
with cycle/address bounds, not geom-name prefixes. The exact pinned five robot
bodies and seven robot geoms (including caster fork and camera markers) are
required. Every model geometry is recorded with ID/name, body ID/name, and
robot/world ownership, bound to the immutable model digest. A missing/detached
robot descendant or robot name outside the subtree rejects setup. Thus no robot
geometry can enter the world-only exclusion.

Each packet copies contact geom IDs/names, finite signed distances, and its
classification, never contact forces or contact/control mutations. The sole rover
support allowlist is floor
paired with `left_wheel_geom`, `right_wheel_geom`, or `caster_wheel_geom`, resolved
to known model IDs and verified ownership. Every other robot-incident pair,
including base/fork-floor, robot-wall/obstacle, and self-contact, rejects the
trial, including during settling. Unnamed/unknown contact geometry rejects
coverage. Known pairs with neither geometry owned by the robot are retained as
`world_only`, including moving soft-constrained obstacle support. They do not
set the fit contact flag. This measures wheel response absent unexpected rover
contact, not a static world or a whole-world no-contact state.
At most 128 contacts are accepted per
packet. All observed stages of a rejected interval are retained. Missing packets
or instrumentation errors reject coverage; they never imply contact-free motion.

The [3.3.6 control callback contract](https://mujoco.readthedocs.io/en/3.3.6/APIreference/APIglobals.html#mjcb-control)
and [pinned Euler pipeline](https://github.com/google-deepmind/mujoco/blob/3.3.6/src/engine/engine_forward.c#L1010-L1104)
place the callback after position/velocity stages and collision generation, before
actuation/integration. The upstream pinned environment calls `mj_step` ten times
and then renders without another `mj_forward`. End `data.contact` therefore
describes the last pre-integration stage at `start+.018`, not a fresh endpoint at
`start+.020`; the script labels this timestamp and checks equality with the last
packet. No extra forward call refreshes it. This covers discrete pipeline stages,
not continuous collision detection or contacts arising between stages. The
installed `mjmodel.h`/`mujoco.h` and upstream environment/XML hashes are evidence
for the observed pipeline, not an independently rebuilt MuJoCo binary.

## Checks and deferred actual command

Pure checks exercise gain support/contact/residual rejection, existing callback
preservation, stage coverage, cached endpoint labeling, enum/pointer mismatch,
finite distance guards, cleanup, and exact float64 manual action representation.
V2 checks additionally retain world-only pairs, reject contact involving every
robot geom and self-contact, and reject detachment that could otherwise move a
robot geometry into the exclusion.
They use small boundary fixtures and do not prove actual physics behavior.

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python -m unittest discover -s tests -p test_verify_body_gains.py
```

Only after review, frozen source, and an exclusive runtime window:

```sh
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 ../lab-hardening/.venv/bin/python scripts/verify_body_gains.py --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn --output runs/m6-body-gain-diagnostic-v2-20261002
```

The output is exclusive. Protocol/source/harness hashes precede collection and
are rechecked at the end; each child result, native initial snapshot, bounded
native logs, supervisor disposition, and rejected packets are retained. The
final report indexes child hashes without duplicating raw rows. No actual result,
held-out behavior, learned policy, physical hardware, compensation, inverse
control conversion, or adaptation qualification is claimed by preparation.
