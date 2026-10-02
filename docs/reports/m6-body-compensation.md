# Fixed-artifact body compensation development result

The single predeclared six-trial gate **passes** at frozen source
`7154d843fb4c62b67b40af27b8ed41f4607d7ae2`. It took 66.7390 seconds internally;
the 780-second outer watchdog completed normally in 67.0588 seconds, exit 0.
The [raw report](../../runs/m6-body-compensation-development-20261002/report.json)
SHA256 is `f5a5d617ceb4dbddf32e7e589748f6245c041312f60dbb4147ac985b170d6856`.
The [evidence index](m6-body-compensation.json) binds 78 raw artifact hashes,
source/harness identity, control plans, ownership, assets, and independently
recomputed metrics; it does not duplicate raw contact/sample rows.

Six fresh manual CPU owners use seed 1 and nominal straight commands ±0.3:
baseline, left motor gear ×0.8 uncompensated, and the same perturbation with the
frozen [v2 fitted gains](m6-body-gains-v2.md). Each collects 120 ticks; the first
20 are excluded, leaving 100 aligned intervals per comparison. The command,
scene, settling, ratio bound 1.5, and comparisons follow the
[frozen protocol](../plans/body-compensation-development.md). There was no tuning
or retry. Prior v1 rejection and v2 fit evidence remain retained separately.

| Direction | Metric error versus same-direction baseline | Uncompensated | Compensated |
| --- | --- | ---: | ---: |
| Forward | Two-wheel rate RMSE (rad/s) | 1.081133369 | 0.200135523 |
| Forward | Cumulative yaw deviation (rad) | 0.401782361 | 0.061484936 |
| Forward | Authored-lane lateral deviation (m) | 0.257596949 | 0.044509620 |
| Reverse | Two-wheel rate RMSE (rad/s) | 1.631649162 | 0.553541417 |
| Reverse | Cumulative yaw deviation (rad) | 0.615552583 | 0.123907749 |
| Reverse | Authored-lane lateral deviation (m) | 0.207638136 | 0.023801910 |

All six errors strictly improve as required; neither direction is pooled away.
The independent audit recomputed these values directly from raw shaft
increments/dt and before/after pose caches, without calling `compare_trials`.
Baseline yaw/lateral drift is near zero. Compensated raw drift remains nonzero:
forward yaw +0.061484936 rad and lateral +0.044509620 m; reverse yaw
−0.123907749 rad and lateral −0.023801910 m. This is improvement, not exact
straight motion or a guarantee beyond the declared trials.

Nominal actual controls are ±`[0.6000000238418579,0.6000000238418579]`.
Compensated forward action is `[0.3435766398906708,-0.06609576940536499]`, with
actual controls `[0.7532490491867065,0.6210575103759766]`; reverse is the exact
negative pair. The audit recomputed fixed ratios, binary32 rounding, and the
inverse algebra independently. Every recorded action/control and timed stage
matches the declared plan exactly; normalization/clipping is never entered.
The owner uses the normal upstream step path, with no direct control writes.

All 7,200 pre-control stages and 720 cached-end packets have complete timing and
the pinned ownership partition. They retain 475,200 world-only pairs and 45,468
allowed rover-floor pairs, with zero unexpected robot contacts. The endpoint
contact cache is still the last pre-integration stage, not a new endpoint
evaluation; world-only support may move. Radius 0.06 m and track 0.36 m are
unchanged. Model identity matches within each condition, with only left motor
scalar gear changing from 3 to 2.4.

All six child supervisors return 0, callbacks are restored, Engines close, and
recording manifests are completed at 120 ticks. Fourteen child/outer log files
have no semaphore, resource-tracker, or traceback messages; normal TF32 warnings
remain. The audit finds no process with the owned script argv. Runtime/harness
and pinned gain hashes match start/end/current observations. Both asset files
were verified at all six startups and match their pinned hashes at audit.
These are finite boundary/process checks, not universal mutation/reaping proofs.
Output is 367,442,435 bytes, within the declared 1 GiB budget.

This passes only a fixed-artifact development compensation comparison on new
command amplitudes in one authored scene/seed. True pose is evaluator-only;
nominal odometry and product Engine/task profiles are unchanged. Learned
adaptation, held-out scenes, online calibration, native continuation, both replay
modes, product/UI integration, and physical hardware are **not evaluated** here
and are recorded as null where applicable in the index. The original fit's
direction dependence remains a limitation. Runtime integration requires its own
small contract and verification slice.
