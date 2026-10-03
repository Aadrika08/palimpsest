# Fixed puck student development: source preparation

This prospective headless stage follows the [reviewed four-owner mechanism](../reports/m6-puck-student-mechanism.md).
The [fixed protocol](m6-puck-student-development-v1.json) admits exactly layouts
6100–6103, in that order, with models 21, 22 and 23 for each scene. Each owner
executes one natural episode of at most 600 control ticks. No development rollout
has run under this source, and held-out layouts 6200–6207 remain locked.

The existing standalone owner loads each immutable bundle through the unchanged
strict reader and uses the existing nine-input MLP decision, float64 action,
contact classification, task dwell and record loop. Its own BEFORE-mode is the
ninth input; both continuous actions come from one prediction per interval. No
teacher fields, analytic fallback or private-world input enters inference. Model,
learning, teacher, task, production snapshots, Engine and UI modules are unchanged.

Development has a distinct fresh-only configuration, application and record
identity. Restore, native continuation and replay fields are rejected before
construction. Only the initial snapshot is saved. The existing mechanism envelope
and its replay behavior remain available unchanged; the new workflow cannot be
misidentified as that historical mechanism. Historical teacher provenance and all
three fitting bundles retain their original source pins.

Before native construction/reset, this development path seeds Python and NumPy
with the scene ID. Each scene's model 21 establishes its initial fingerprint.
Models 22 and 23 bind that completed sibling owner's result and initial snapshot
hashes. Their own initial snapshot is saved **before** comparing defined native
integration state (enum 8191, finite float64[440]), full native model/runtime/profile
identity, environment caches, task/world/contact, float32 sensors[8], prepared
BEFORE inputs[9], initial approach/tick-0 cursor, and Python/NumPy/environment/space
RNG state. The authored yaw is checked through the exact existing quaternion→yaw
projection, not by assuming the input decimal survives that conversion bitwise.
Any mismatch terminates before the first prediction or action; the raw SNP and
comparison receipt remain retained.

Only model-specific checkpoint/report identity and Torch RNG are separately
identified instead of paired. Raw native allocation/diagnostic bytes remain in
every snapshot but are not the across-constructor scientific fingerprint. No raw
bytes are zeroed or changed, and no production native-restoration criterion is
relaxed. Torch runtime settings are compared; Torch is the sole random-state
exclusion. Cameras are retained in the native snapshot and numeric records but do
not enter this eight-sensor policy or its input-match criterion.

All twelve natural outcomes are retained, including task failure and time limit.
Operational `status: completed` and exit 0 mean that the entire fixed batch and
cleanup completed correctly. `admission.status` separately requires **at least
3/4 goals for each of models 21, 22 and 23**. Future capability controls must require
that gate as well as clean operational completion; a failed goal gate cannot be
promoted by exit 0. There is no winning-seed selection, tuning, retry, replacement
or early stopping based on outcomes. A protocol, initial-match, model, record,
watchdog or infrastructure error stops the batch with all unstarted rows retained.
Held-out remains locked even after passed admission until independent review and
explicit runtime authorization.

The existing `supervised_owner` supplies the 180 s owner, 60 s startup and 30 s
progress bounds, identity-checked cleanup, 1 MiB logs and drained process result.
Each owner has a 160 MiB record/snapshot allowance; all twelve total 1.875 GiB within
the 3 GiB stage cap. Initial SNPs remain capped at 8 MiB, JSON at 4 MiB, free space
at 1 GiB, and total retained runs at 16 GiB. The 1200 s internal clock begins at
function entry, including protocol/source/bundle admission, and is checked after
final validation, publication and lease exit immediately before return. The
future retained launcher must preserve TERM 1260 s plus 15 s grace inside the
1280 s enclosing bound with independent descendant containment. No ignored
launcher or development execution controls are supplied by this source slice.

Pure fixtures exercise real application/record files with fake model/native
owners, including same-scene matching, a non-Torch RNG mismatch with zero calls
or steps, exact seed setup, invalid-action cursor preservation, typed envelope
rejection, each-model threshold, all twelve natural outcomes, first-failure
unstarted rows and late admission/finalization/lease-exit failure. These fixtures
are source checks, not native task qualification. Public task/UI integration remains
separate project work after successful fixed development and review.

Source validation: 109 focused development/student/teacher/mechanics/profile/
learning/numeric-reader checks passed in 9.310 s with no skips. The explicit Torch
mechanism test was not selected; no model/native job ran. The retained NumPy-only
source check at `runs/puck-development-source-checks/admission.json` re-admitted
all 20 original teacher sources (5710 train / 1314 recorded-dev ticks) and the
three unchanged bundles in 8.418 s. Its result equals the prior student source
receipt except elapsed time; SHA256
`aac2630e8ca56c1d04c2d717a7a35ec19c7a7d1156e9aad1b2ade19cf4949ce1`.
The existing student, model, learning, teacher and task module bytes are unchanged.
