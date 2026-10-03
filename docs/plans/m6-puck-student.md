# Headless puck student: mechanism and development status

This source slice reuses the admitted learning-v2 inputs and the
[three audited fits](../reports/m6-puck-training-v2.md). It implements a fixed
research student in the existing standalone owner. No Engine, worker, controller
registry or UI integration is included. The [four-owner native/replay mechanism](../reports/m6-puck-student-mechanism.md)
passed on `6f1fda9`. The subsequent [fixed development gate](../reports/m6-puck-student-development.md)
failed on `77f4d49`: all three models scored 0/4. Held-out evaluation remains locked.

The [read-only diagnosis](../reports/m6-puck-student-diagnosis.md) and one bounded
NumPy residual audit found poor turn-only fit even on the original teacher
support, alongside limited recovery-state coverage. No runtime/model source or
weights changed. A possible regime-balanced training objective remains subject
to a separately frozen protocol and review; no further fitting or rollout is approved.

The [model manifest](m6-puck-student-models-v1.json) pins all three reports,
protocols and numeric checkpoints from producer `82e2bd9`. The
[mechanism protocol](m6-puck-student-mechanism-v1.json) selects model 21 and the
already observed training layout 6000 before any student rollout. This is a
mechanism check, not selection based on model performance. A reviewed launcher
supplies the read-only directory containing the three `seed-N` bundles; each
artifact must match the tracked manifest and existing strict `read_bundle`.
No arbitrary architecture or controller factory is admitted.

The decision boundary receives only float32[8] declared virtual puck sensors,
its own validated cursor, and the fixed MLP. It never receives private world
geometry or a teacher cursor. `puck_learning.prepare` reconstructs geometry
using the frozen float32→float64 rule, checks the .2 stop boundary before division,
and appends the own **BEFORE-mode** as the ninth feature. Exactly one existing
MLP prediction supplies both velocity and heading. Outputs must remain finite
float64[2] within exact ±.4. No analytic action fallback, clipping, additional
stop command or teacher call exists. The own cursor is committed only after the
native interval and its numeric row/event have been staged successfully. If
native execution or recording fails, the owner terminates; this does not claim
that native physics was rolled back.

All four owners construct the same pinned CPU MLP before capture/restore. This
establishes the same Torch profile and permits the existing snapshot code to
restore its exact RNG state. Action replay uses recorded actions with **zero MLP
predictions**, while independently validating sensors and own mode. Construction
is not counted as prediction. No controller-replacement exception is used, and
full raw native snapshots remain unchanged. Policy replay and native continuation
predict once per interval. Live parameter bytes must still equal the checkpoint
at shutdown; every bundle is re-admitted then. The shared model, trainer, learning
supervisor, task profile and production snapshot implementation remain unchanged.

Student records use `puck-student-v1`; applications use
`puck-student-application-v1`. They contain the own cursor and mode before/after,
virtual 8 / feature 9 vectors, exact float64 action, actual native/contact/task arrays,
model/report/checkpoint identity, current student runtime source hashes and
supervisor/feature/task/profile identities. They contain no teacher mode or
fabricated teacher diagnostic. The immutable teacher records retain their original
producer/source inventory. Current student source identity is distinct; neither
historical teacher provenance nor strict teacher-data admission is rewritten.

Before native restoration, the owner validates the complete student application,
its typed digest, nonterminal task/contact/world state, exact projected sensors,
completed own tick, all source/model identities and the fixed source receipt.
Historical teacher/mechanics applications are rejected. Full action/policy
replays must consume the source's entire recorded duration; the native branch
uses the four exact successor intervals after tick 1. Recorded scalar modes retain
the strict uint8 scalar boundary through the real record reader.

The prospective fixed plan is:

| Owner | Source boundary | Maximum new intervals | Record/snapshot cap |
| --- | --- | ---: | ---: |
| Model21/layout 6000 source | Authored reset | 120 | 64 MiB |
| Native continuation | Tick1 | 4 | 32 MiB |
| Recorded-action replay | Initial | Actual source duration, ≤120 | 64 MiB |
| Policy replay | Initial | Actual source duration, ≤120 | 64 MiB |

The source must retain at least five completed intervals, initial and tick 1
snapshots; a natural early task outcome remains recorded, not relabeled as
success. No later snapshot boundary may replace tick 1. Missing successor coverage
fails the gate. All replay numeric fields are compared exactly to this source,
including cursor, action, native arrays and contact/task state. This does not
compare native allocation scratch bytes across independent constructors.

The existing supervisor enforces 180 s per owner, 60 s startup, 30 s progress,
1 MiB logs and 8 MiB snapshots. The prospective stage retains 600 s internal,
TERM 660 s plus 15 s grace, 680 s enclosing supervision, 1 GiB stage storage,
1 GiB free floor and 16 GiB total retention. Four owner allowances sum 224 MiB.
No launcher or actual execution is authorized by this document; reviewed source,
frozen controls and a separate runtime slot remain required.

Pure fixtures exercise the actual modified owner with fake native/model resources
and real record files: source, continuation and both replays compare every numeric
field; action replay makes zero predictions; invalid outputs and record failure
leave the completed own cursor uncommitted; malformed/historical snapshots fail
before restore. A separate fixture calls the real `snapshots.restore` and
`_stage_rng` functions, showing absent-Torch profile rejection and matching-profile
RNG staging before a fake native-allocation sentinel. It is not native restore
qualification. The preexisting teacher/mechanics paths retain their fixtures.

The reviewed mechanism was followed by the unchanged
**6100–6103 × models 21/22/23** development plan: twelve matched-start owners,
one natural episode ≤600 ticks, **at least 3/4 goals for every model**, all results
reported, no winning-seed selection, tuning or replacement. Existing bounds remain
1200 s internal / TERM 1260+15 / 1280 s supervisor, 3 GiB stage and 160 MiB per owner.
All twelve development episodes ended at their 600-tick time limit with no goals;
this failed admission does not authorize another run or weaken the gate.
Held-out 6200–6207 remains locked. Public task/UI integration is explicit remaining
project work after successful fixed development, not supplied by this headless slice.

Source-only validation on this slice: 103 focused student/teacher/mechanics/profile/
learning/numeric-model-reader fixtures passed in 6.679 s with no skips. The pinned
upstream source was checked out locally at 8d964599; no native XML compilation
occurred. Before and after edits, all three actual bundles passed the unchanged
strict reader and all 20 historical teacher records were independently readmitted
(5710 train /1314 recorded-dev ticks), in 8.766923449 s and 8.523361062 s. Apart from
elapsed time, the retained reports match exactly, including all original training
source and model identities. The local `runs/puck-student-source-prep/` receipts
are SHA256: `admission.py` 78f4922e93d0ee6df93b9f00c65ec26f74fb7b56b4d7bf96fef6f0ac66560ba9,
`before.json` 7449eaca8b3286e36dbd1f66b8719af4a9011b0fe7e593d72b213269ed724b65,
`after.json` 0ec40c82dff3503011570c3d490e5722a51e7b33744ced3d51b5b1989fd63abb.
These are NumPy-only artifact checks, not student inference or native qualification.
