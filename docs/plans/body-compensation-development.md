# Fixed-artifact body compensation development gate

Prepared, not executed. This gate uses the accepted
[v2 gain evidence](../reports/m6-body-gains-v2.md), whose raw report SHA256 is
`9d2cd4729d32f84b490db3a6726764111989fcc80be74c7a2ba44a97cb419331`.
It introduces no Engine/task-profile changes, online fitting, odometry changes,
true-pose corrections, or learned-policy claim. Earlier rejected v1 evidence and
the accepted v2 diagnostic remain immutable.

[`verify_body_compensation.py`](../../scripts/verify_body_compensation.py) freezes
six fresh manual CPU trials: baseline gear 3, left gear multiplied by 0.8 without
compensation, and left gear multiplied by 0.8 with compensation, each at nominal
straight action `[+.3,0]` or `[-.3,0]`. These amplitudes differ from the fitting
amplitudes `.2/.4`; they are development command checks, not held-out layouts or
generalization evidence. All trials use seed 1, the same authored scene, start
`[-3.5,0,0]`, goal `[-3.5,3]`, 120 ticks, and the predeclared first 20 settling
ticks. There are no retries, post-failure changes, or response-dependent commands.

The pinned pooled baseline gains are
`[14.878897911022118,14.878897948225164]` rad/s/control; measured perturbed gains
are `[11.851776561760323,14.374415787256368]`. The original diagnostic's direction
dependence (11.95% left-wheel gain range/mean) remains a limitation. Every owner
verifies the exact accepted report hash. `compensate_wheels` uses its unmodified
validation, ratio bound 1.5, and control limit 2, before collection. No samples
from this gate update those coefficients.

For compensation only, a small inverse uses `ctrlL=2v-heading` and
`ctrlR=2v+heading`, hence `v=(ctrlL+ctrlR)/4` and
`heading=(ctrlR-ctrlL)/2`. It explicitly rounds proposed controls to the float32
representation used upstream, records the rounding delta, and requires exact
forward-converter equality. Controls outside ±2 or any normalized/clipped branch
are rejected; no saturation is silently clamped. The owner calls Engine's normal
manual action/step path, never writes `data.ctrl` directly, and compares every
actual control with the declared target. Nominal/applied actions and controls,
the fixed artifact identity, and the original/overridden world/gear/model are
recorded before the initial native snapshot and in every collected row.

The existing shared diagnostic collector preserves its original seed-0/default
protocol when no command plan is supplied. Its v2 global callback, exact ownership
partition, 10 Euler pre-control stages per tick, cached end-packet labeling,
finite-value/interval/rate/control bounds, and unexpected robot-contact rejection
are reused unchanged. World-only contacts remain recorded and may move. No
whole-world no-contact, static-world, continuous-collision, generic playback, or
gear-perturbed snapshot restoration claim follows from this gate.

## Frozen comparisons

Each direction has its own newly collected nominal baseline. Align all 100
post-settling intervals by tick. Report the following raw values and errors:

- Wheel-rate error is the RMS of actual raw shaft rates minus that direction's
  baseline, over 100 intervals × two wheels; rates use measured increments/dt.
- Yaw drift is the sum of wrapped before/after yaw increments over those same
  intervals. Its error is the absolute difference from baseline's signed sum.
- Lateral drift is world-y displacement from the start of interval 20 to the end
  of interval 119. The authored lane heading is zero; no per-trial rotating frame
  hides accumulated turning. Its error is the absolute difference from baseline.

Acceptance requires compensated error to be **strictly smaller** than
uncompensated error for all three metrics independently in **both** directions.
No pooling, tolerance, baseline subtraction beyond the declared definitions, or
failed-direction suppression is allowed. Actual pose caches are evaluator-only;
their existing last-stage timing is preserved, and they never affect commands.
The comparison does not require zero drift and does not qualify physical motion.

## Bounds and checks

Each child has 120 seconds, 64 MiB recording, 64 MiB result JSON, and 1 MiB per
native log stream. The parent holds the existing single-writer storage lease and
shares a fresh-recount budget with its child: 1 GiB whole output root, 1 GiB free
disk floor, six runs, one initial snapshot per run, and 4 MiB control/log
headroom. Final report/protocol JSON is capped at 1 MiB; result reads at 64 MiB,
gain-report reads at 1 MiB. Outputs are exclusive and outside assets. All six
planned trial entries remain visible as `not_started` if artifact preflight
fails. Quota, timeout, artifact, collection, or comparison failures are retained;
exhausted storage may prevent a large result publication and is reported by
supervision/logs rather than invented packets. No additional writer framework or
cached accounting is introduced.

Pure checks validate exact converter parity against the pinned upstream function,
saturation and hash rejection, both-direction metric acceptance, missing support,
legacy collector seed/bounds and failure retention, and six-entry preflight
reporting without spawning. Boundary fixtures are not physics proof.

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python -m unittest discover -s tests -p 'test_verify_body*.py'
```

Deferred until reviewed/frozen and the exclusive runtime slot is released:

```sh
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 ../lab-hardening/.venv/bin/python scripts/verify_body_compensation.py --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn --gains-report runs/m6-body-gain-diagnostic-v2-20261002/report.json --output runs/m6-body-compensation-development-20261002
```

The final report binds start/end runtime and harness hashes, pinned gain identity,
raw child result hashes, supervisor dispositions, and per-direction comparisons.
An observed pass would support only this fixed-artifact, fixed-command development
comparison. Product adaptation, learned behavior, held-out scenes, native
continuation/replay integration, and hardware remain separate future gates.
