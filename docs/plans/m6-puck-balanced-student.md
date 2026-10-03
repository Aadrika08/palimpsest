# Balanced puck student: mechanism preparation

This fixed research adapter admits the three [balanced fits](../reports/m6-puck-balanced-training-v1.md)
through their exact report, protocol and numeric checkpoint hashes. The prior
retained-array diagnostic remains negative: 104–105 of 106 recorded-dev turn-only
rows predict velocity magnitude above .05, and both aggregate and turn-only joint
losses worsen. Mechanical compatibility is a separate question; no task improvement,
development admission or public UI qualification follows from this source slice.

The [new mechanism protocol](m6-puck-balanced-student-mechanism-v1.json) pins the
[balanced model manifest](m6-puck-balanced-student-models-v1.json), objective,
historical decision source and existing task/native protocols. It fixes model 21
and already observed training layout 6000 before any rollout. Models 22 and 23
remain separately identified; this does not select a winning model.

`puck_balanced_student` admits only the balanced bundle reader and exact
`learning_student_balanced` owner envelope. Its `action` and `decide` are the
original `puck_student` function objects. There is no new prediction, scaling,
sensor, cursor or task arithmetic. One MLP prediction supplies both continuous
actions from declared float32 sensors plus the own BEFORE-mode input. Existing
finite float64 output guards and commit-after-completed-record semantics apply.
There is no teacher input, analytic fallback or clipping.

The existing standalone owner selects this adapter only for that explicit
envelope. Mixed teacher, historical student or development envelopes reject.
The new record schema is `puck-balanced-student-v1`; the new application kind is
`puck-balanced-student-application-v1`. They bind the objective, adapter and shared
decision source, supervisor, task, feature, model and bundle identities without
rewriting them into historical schemas. Old records/applications reject. The
default historical student and development bindings remain byte-for-byte unchanged.

The four owners and limits equal the historical mechanism protocol: source at
most 120 intervals, native continuation for the four successors after tick 1,
then complete recorded-action and policy replays. The source must have at least
five intervals. All four owners construct the same pinned CPU MLP before native
capture/restore, preserving the exact Torch profile and RNG contract. Saved-action
replay makes zero predictions; native continuation and policy replay predict once
per interval. All numeric fields compare exactly to the new source, retaining
full raw native snapshots. This makes no cross-model trajectory equality claim.

Limits remain 180 s per owner, startup 60 s, progress 30 s, 1 MiB logs, 8 MiB
snapshots, 224 MiB total owner allowances, 1 GiB stage storage, 1 GiB free floor,
16 GiB retention, 600 s internal / TERM 660 s plus 15 s / 680 s supervision.
Frozen controls, independent source review and a separate runtime GO are still
required. This commit supplies no launcher or actual native/model validation.

Pure verification ran 49 focused adapter, historical student, development,
balanced-objective, numeric-reader and learning tests in 3.468 s with no skips.
The fixtures use fake native/model resources with real record files; they exercise
all four actual owner paths, exact replay fields, zero action-replay predictions,
invalid-output/record-failure rollback and rejection before restore/model creation.
The existing real restore/RNG-boundary sentinel fixture remains part of that run.
An initial fixture reached the uninitialized upstream XML and failed; only its
mock inventory boundary was corrected, and the failed log is retained.

The real upstream was then checked out from local objects at clean `8d964599`.
Before/after NumPy-only admission passed in 9.775859142 s and 6.103595864 s:
all 20 historical teacher sources, 5710 train / 1314 recorded-dev rows, unchanged
ordering/feature/target identities and all three original bundles. The after-check
also admitted all three balanced bundles through the new adapter. The 15 protected source/protocol hashes
match exactly. No Torch, native compilation, predictions, global writer lease or
training was used. Receipts and both fixture logs are retained under
`runs/puck-balanced-student-source-checks/`; their hashes are included in the
source handoff. These checks do not qualify native restoration or model loading.

Development/evaluator/UI integration is excluded. A later separate proposal must
retain scenes 6100–6103 × all three models, at least 3/4 goals for **each** model,
all results and failures, and the original finite bounds. Held-out 6200–6207 remains
locked. Negative residual evidence does not authorize that rollout automatically.
