# M7 frozen paired closed-loop evaluation v2

This protocol is frozen before running either existing male checkpoint on scene
seeds **128–135**. It evaluates eight new fixed scenes for each of the original and
degree-rewired models, trained with the one existing training seed. It is not a
new training/selection round, a topology-benefit test, a generalization claim, or
evidence of biological sensor mapping. The earlier recorded-input test used
112–115; the runtime and browser mechanism gates observed 116. The rejected v1
plan reserved 120–127 and observed 120. None is reused.

[The v1 batch remains rejected](../reports/m7-closed-loop-v1.md). Its first owner
completed a 268-tick stalled episode, but the evaluator hashed float64 initial
sensors against Engine's actual float32 recording. Its cleanup then queried a
Process handle after normal supervisor disposal, preventing later provenance
checks. These are evaluator defects. V2 corrects the exact projection and disposal
order, independently attempts every evidence-finalization stage, and reserves
fresh seeds. The old report, recordings and outcome remain unchanged; offline
diagnosis does not promote v1 into a complete or paired evaluation. V2 records
the rejected v1 protocol/report hashes and never automatically reruns its scenes.

The machine-readable contract is `PROTOCOL` in
`scripts/evaluate_male_closed_loop.py`. Its canonical hash, exact JSON, evaluator
copy, runtime source hashes and both complete model identities are retained with
each execution. Only `--repo`, `--assets` and an exclusive new `--output` directory
are arguments. There is no seed, controller, checkpoint, duration or retry override.
Changing the experiment requires a separately reviewed protocol, not tuning this
one after inspecting results.

## Runs and matching

Run seeds in ascending order, original then control for each seed: sixteen fresh
UUID LabSupervisor runs, CPU, reproduction/checker, both eyes enabled, exactly one
episode starting at tick zero. Each run stops on its first natural goal, collision,
stall or time-limit termination, or at the cap of 600 control ticks. The control
interval remains 0.02 seconds; a capped episode advances at most 12 simulated
seconds. There is no reset, padding, intervention, replay, branch, manual action,
model update, replacement scene, retry or checkpoint selection.

Use the existing two fixed controller IDs and tracked male model manifest in the
normal asset root. Resolve and retain the exact checkpoint, training-report,
training-protocol, graph, topology, ordered-ID, feature-protocol, raw-graph,
extraction-manifest, cell-source and model-manifest hashes. Asset pins do not
change. The learned RGB/contact/goal-bearing encoder remains artificial, with no
privileged world-coordinate input to either policy.

The initial registered native snapshot must show the expected seed, episode zero,
paused tick zero, correct model identity and zero float32 hidden state. Before the
control model's first step, compare exact typed-state hashes of:

- Initial world geometry and pose, MuJoCo integration state, environment fields,
  environment/runtime/model/renderer identity excluding the policy and Torch entry.
- Both actual 128 × 128 uint8 RGB cameras, the exact **float32** contact/relative-
  goal-bearing vector produced by Engine (including its angle-or-zero conversion),
  and its deterministic 388-feature projection. Match values and dtypes; do not
  weaken exact equality or silently cast the retained record to fit an expectation.
- Environment RNG state, its seed and observation/action-space RNG states.

Policy weights intentionally differ and are identified separately. Do not compare
native serialized bytes that may contain non-scientific details. The first model
has already completed by the time the serial control owner is created. If its
initial conditions do not match, do not advance the control; fail the batch and
retain the first run without claiming a valid paired outcome. First recorded
policy inputs must independently equal each run's initial snapshot inputs.

## Limits and failure contract

| Bound | Frozen value |
| --- | --- |
| Concurrent simulator/model owners | 1; close, reap and verify exit before next |
| Episode/tick count | 1 / at most 600 per run; at most 9,600 total |
| Owner/startup/progress deadlines | 180 / 60 / 30 wall seconds |
| Entire internal evaluation deadline | 900 wall seconds, including final validation |
| Required external parent bound | TERM at 960 seconds, KILL after 15 more seconds |
| Recording plus initial snapshot | 160 MiB per run admission estimate and final verified cap |
| Managed output storage | 3 GiB hard write budget, including reports; 1 GiB free-space floor |
| Snapshot count | Exactly the existing initial snapshot; no further capture |
| Report size | At most 4 MiB |

The existing LabSupervisor supplies per-user writer ownership, child process-group
watchdogs, progress checks, bounded native logs, single-owner admission and close
handling. The evaluator adds total/per-owner boundary deadlines and records normal
exit status before Process handles are disposed. An already retained clean-close
observation is reused; otherwise close/reap and capture it before shutdown.
No process attribute is queried after shutdown. Cleanup, each completed recording
fingerprint, source identity, each model identity and the final deadline are checked
independently, with a list of stage-specific errors. A failed cleanup never skips
the remaining provenance checks. Signals cause failure and shutdown. The parent must still supervise
the evaluator and verify no owner process survives; a Python boundary deadline
alone cannot bound a blocked native operation.

Admit all sixteen 160 MiB allowances before the first owner; the worker also uses
its existing raw/effective camera/neural recording estimate before stepping. The
per-run estimate includes its actual initial recording and snapshot, and the
final byte count is checked independently. The 160 MiB bound is an admission and
final verification bound, while the aggregate shared budget is enforced before
writes. Exhaustion is a failure, never permission to shorten or replace a scene.

Every planned seed/controller row exists before execution, initially
`not_started`. Stop on the first runtime, owner, storage, provenance, matching,
record-integrity or deadline failure; retain that failed row, prior completed rows
and all unattempted rows. Do not compute a complete-batch comparison from an
incomplete batch or interpret a runtime failure as a natural task outcome.

## Evidence and reporting

Exhaust the existing validated recording reader after each clean close. Require
one contiguous episode, manifest/event seed agreement, exact pinned identity,
recorded raw/effective camera agreement, both eyes enabled, finite bounded actions
and genuine encoded/raw-output telemetry, no fabricated neural populations, and
the exact post-step simulated-time contract. Reject any intervention or restored
lineage. Keep the actual terminal event and outcome. A paused episode at tick 600
without a natural terminal event is labeled `evaluation_tick_cap` distinctly.

For every completed run retain outcome, goal indicator, actual tick count,
cumulative reward, path length, contact ticks and final goal distance. Report
simulation duration, recorded inference latency, recorded physics latency and
whole-owner wall duration separately. Wall duration includes startup, pauses,
IPC, recording and validation; it is not policy latency or a real-time-factor
claim. Timing statistics use the mean, sum, maximum and nearest-rank p95.

Retain every recording/snapshot file size and SHA-256, run recording digest,
policy-input sequence digest, paired initial hashes, and one aggregate dataset
digest. Recheck all completed file fingerprints, source hashes and resolved model
identities before final publication. The source inventory includes package code,
lock/configuration, both data manifests, this evaluator/protocol, the reused
collector and all bounded upstream Python source files. Run manifests also retain
the runtime dependency/diagnostic and upstream provenance supplied by Engine.

Only a complete sixteen-run batch has the fixed eight-episode-per-model outcome
summary. Publish all paired rows, including null/equal outcomes. No statistical
significance, topology advantage, broad robustness or held-out generalization is
established by these eight scenes and one trained-model seed. Any later multi-seed
study needs a separate protocol and untouched evaluation scenes.

## Commands, deferred until the runtime window is released

Pure fixture verification (no Torch, EGL or owner processes):

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest test_male_evaluation -v
```

Actual evaluation, only after root reviews/freezes the source and grants the slot:

```sh
timeout --signal=TERM --kill-after=15s 960s env PYTHONPATH=src \
  ../lab-hardening/.venv/bin/python scripts/evaluate_male_closed_loop.py \
  --repo "$PWD" --assets "$PWD/data/assets/flynn" \
  --output "$PWD/runs/m7-male-closed-loop-v2"
```

The script never overwrites an existing output directory. Preserve failed output;
do not retry this frozen evaluation automatically. No actual evaluation evidence
exists merely because the fixture checks pass.
