# M7 v2: longer demonstrations, three matched training seeds

This protocol is frozen before new collection or training. The [machine-readable
contract](m7-training-v2-protocol.json) fixes every scene, training/control seed,
selection rule and stage budget. The existing 388-feature artificial interface,
138-node/1,647-edge extraction, upstream cell/readout, positive-count recurrent
weights and action scaling remain unchanged. Production controller/asset pins and
all v1 artifacts remain unchanged. This preparation does not establish topology
benefit, biological sensor mapping, generalization or R3 completion.

## Evidence and hypothesis

The [retained train/dev-only diagnosis](../reports/m7-training-v2-rationale.json)
verified the old source hashes and read 1,200 training plus 600 dev ticks using
NumPy and the validated record iterator. No held-out raw rows or model runtime
were opened. All eight training trajectories stopped at 150 ticks without a
terminal task outcome; every training velocity label was 0.7 and every train/dev
contact input was zero. 850/1,200 training headings had magnitude below 0.1 rad.
Original dev loss fell from 0.074117 to 0.057095 over five epochs; both variants
selected epoch five. These observations support narrow coverage and a short
optimization budget, not a proven cause of navigation failure.

Longer demonstrations and more fixed optimization steps may help. They may still
lack recovery examples, and the privileged teacher accesses world geometry the
student cannot directly observe. Compounding imitation error, partial observability
and capacity remain hypotheses. Data and loss diagnostics must remain descriptive;
do not alter this frozen protocol after observing the new scenes or outcomes.

All previously inspected reports are development evidence for this new design,
including old recorded held-out seeds 112–115 and closed-loop seeds 128–135.
Their historical labels and original frozen claims are preserved, never rewritten.
The newly reserved seeds below are disjoint from them.

## Frozen stages and stopping

| Stage | Exact work | Maximum data/runtime |
| --- | --- | --- |
| A: development teacher collection | Train scenes 1000–1007; recorded-dev scenes 1008–1011 | 12 owners, 7,200 ticks; 1,200 s internal / 1,260 s external |
| B: paired training | Training seeds 10, 11, 12; matched rewiring seeds 10, 11, 12; original/control for each seed | Six models; three serialized pairs, 600 s internal / 660 s external per pair |
| C: closed-loop development | Scenes 1100–1103 for all six fixed models | 24 owners, 14,400 ticks; 1,800 s internal / 1,860 s external; 4 GiB |
| D: recorded held-out collection/evaluation | Teacher scenes 1012–1015; evaluate all six fixed checkpoints once | Four teacher owners, 2,400 ticks; 480 s collection / 540 s external; recorded evaluation 120 s / 180 s external |
| E: final closed-loop held-out | Scenes 1200–1207 for all six fixed models | 48 owners, 28,800 ticks; 3,600 s internal / 3,660 s external; 8 GiB |

Stages D and E remain unopened unless all six checkpoints are frozen, all 24
Stage C owners complete without infrastructure failure, and **each original
training seed reaches at least 2/4 development goals**. This is a prospective
engineering admission rule, not a statistical benefit test. Control outcomes stay
visible and receive exactly the same scenes and budgets. No winning seed is
selected, and no model is replaced after development results. Failure stops before
held-out data acquisition/evaluation. Final outcomes are reported for all six;
this protocol sets no post-outcome promotion rule or R3 qualification threshold.

Exactly one fresh root episode per teacher or evaluation owner, at most 600 control
ticks at 0.02 seconds each. Preserve natural goal/collision/stall/time-limit endings.
An episode reaching the collection cap is explicitly capped, not labelled a goal.
Never reset, pad, substitute a scene, retry a failure or discard a poor outcome.
Each training run needs at least 32 usable ticks; dev/held-out recordings need at
least one. Otherwise the stage fails as insufficient data. The retained report
contains every planned owner, including `not_started` rows after a first failure.

## Training and held-out separation

Twenty epochs, window 32, Adam 0.001, gradient norm cap 1.0. Keep the existing
`mean(0.5*((velocity_error/3)^2 + 1-cos(heading_error)))` loss. For each model, select
minimum recorded-dev loss across all twenty epochs; the earliest epoch wins ties.
Use the same ordered scenes/ticks and parameter initialization seed for each
original/control pair. Reset hidden state only at episode start; carry it and detach
at window boundaries. Retain all train/dev epoch metrics and selected checkpoint
identities. Do not inspect new held-out arrays, outcomes or losses for selection.

The control retains node/edge count, in/out degrees, weight multiset, types and
input/output IDs using the existing swap algorithm. Use the original graph's shared
normalization scalar. Do not screen or regenerate controls for desired reachability
or outcomes. All six models retain the same parameterization and training budget.
Three paired seed realizations are small; do not pool correlated ticks as independent
trials or interpret a descriptive control difference as a topology advantage.

Stage B training bundles are immutable once written. Stage D recorded-held-out
metrics are separate exclusive reports and do not modify training report hashes or
checkpoints. An explicit passed Stage C receipt binds all six checkpoint/report
hashes and the frozen protocol before either held-out stage is admitted. A missing,
failed or mismatched receipt is a hard refusal, not an operator override flag.

## Identity, ownership and bounds

Use the existing UUID LabSupervisor/Engine owner and validated records; preserve
exact source/model/graph/protocol/ordered-ID hashes, raw/effective inputs, state,
initial world/environment RNG and paired initial physical/input checks. Student
features remain the two actual RGB cameras, contact/angle and relative goal bearing;
no pose, outcome or privileged teacher state enters the model. Student Torch stays CPU
float32, deterministic algorithms and one thread. The privileged teacher keeps
the existing Engine setting of two Torch threads. No simulator/model/ML jobs may run
until source freeze and an explicit runtime slot.

Teacher sources: at most 16 runs/9,600 ticks, 160 MiB per run including initial
snapshots and 3 GiB aggregate. Training outputs: at most 64 MiB per pair, 8 MiB per
file and 192 MiB across all three pairs. Evaluations: 160 MiB per run including
initial snapshot, four/eight GiB stage roots above. Every stage retains a 1 GiB
free-space floor, 1 MiB stdout/stderr caps and 4 MiB reports. Preflight the complete
planned allowance before starting owners; subsequent writes remain quota-checked.

One owner/model job at a time. Reuse bounded process-group supervision and the
existing per-user writer lease. External deadlines use TERM then KILL after a
15-second grace. Owner/startup/progress limits are 180/60/30 seconds. Close/dispose
in the already corrected order and preserve cleanup evidence. Any data, finite,
source, time, storage or cleanup failure stops the stage and remains visible.

Expected maxima from simple scaling of prior local measurements are roughly
15 minutes for all sixteen teacher runs and 18 minutes for all training pairs.
These are estimates, not guarantees or deadline extensions. Feature/target arrays
are bounded to approximately 15 MiB; prior training did not record peak RSS, so no
measured process-memory claim is made. No dependency install, new architecture,
registry/UI or production asset replacement belongs to this pilot.

The current v1 loader pins the old training protocol and rewiring seed zero.
Research loading must retain strict completed-report, ZIP, tensor/graph/lineage
validation while admitting only the three explicit v2 paired identities. Runtime
binding of those identities must be reviewed before any Engine/worker/Lab API is
widened. Existing production IDs continue to resolve their unchanged v1 pins.

## Pre-execution scope clarification

Before any v2 collection, training or evaluation, the protocol explicitly scoped
`threads: 1` to student training/inference and added `teacher_threads: 2` to match
the unchanged Engine teacher path. No new outcomes were observed; seeds, models,
optimizer settings, stopping rules and resource budgets did not change. This is
a transparent pre-execution clarification of the first protocol commit `38a704c`,
whose JSON SHA256 was `25327bf82871d7b5453ab63d0a62341d5f545d5dcd747ce620a003eb24d28210`.
The clarified JSON SHA256 is `8f360289ce286f56e31051c7bcfc6932a8f413dce662b83ddb9817b3e509d69b`.

## Implementation and launch contract

The existing collector accepts `--research-stage development` or `held_out` with
this exact JSON. Stage A collects only twelve scenes. The existing trainer accepts
`--research-v2 --training-seed 10` (then 11 and 12) and no `--held-out` argument.
Its validated source lists must follow increasing declared seed order. Use three
exclusive sibling outputs named `seed-10`, `seed-11`, `seed-12`. Each pair retains
both model statuses on failure; the retained ordered parent launcher must list all
six models before starting, stop on the first failed pair, and leave subsequent
models `not_started`. No automatic loop in the product selects, replaces or retries
models. The unchanged one-pair trainer remains the unit of supervision.

After all three complete, `scripts/male_research.py publish` exclusively writes a
research manifest alongside those directories. Publication and resolution require
all pairs to bind identical teacher collection and training-source hashes. Each
pair is checked against its exact declared rewiring seed, twenty epoch history,
earliest minimum-dev checkpoint rule, source checks and unopened held-out status.
The standard production resolver still rejects these research bundles.

The existing evaluator accepts `--research-stage dev` or `held_out`, explicit
`--research-manifest PATH --research-manifest-sha256 SHA`, and uses the reviewed
Python-only `Binding`. The worker admits fresh CPU/reproduction/checker root runs
only. It rejects replay, native branches and interventions. Research provenance is
in the manifest and policy-loaded event before the initial snapshot. Initial
physical state, environment identity/RNG and exact declared inputs must match
across all six models for a scene before each later owner moves. There are no new
REST/UI flags, registries, arbitrary controller IDs or production asset pins.

Held-out collection, recorded evaluation and closed-loop evaluation additionally
require `--development-report PATH --development-sha256 SHA`. The admission code
checks every planned dev owner, all twelve matched pairs, each original seed's
2/4 threshold, exact model identities, successful cleanup/source checks and the
complete retained recording/snapshot inventories and hashes. Failed admission
occurs before any held-out source read or owner construction. Recorded held-out
metrics use `scripts/male_research.py held-out-recorded` with four ordered
`--held-out PATH` arguments and a new output directory; they never alter bundles.

Run commands with the locked shared interpreter, `PYTHONPATH=src:tests`, pinned
upstream source and the existing combined read-only asset root. The first actual
collection command, after regression/source review and explicit Stage A release,
is:

```sh
python scripts/collect_male_teachers.py \
  --repo . --assets ../project-integration/data/assets/flynn \
  --protocol docs/plans/m7-training-v2-protocol.json \
  --research-stage development --output runs/m7-v2-teachers-development
```

This is the child command, not an unsupervised launch instruction. Retain each
launch's exact command/environment, source/asset hashes, stdout/stderr and
`bounded_process` result. Wrap the child with GNU `timeout --signal=TERM
--kill-after=15s LIMITs`; supervise that command with `bounded_process` at
`LIMIT+20` seconds so its existing three-second emergency cleanup does not shorten
the declared fifteen-second grace. LIMIT is 1260 for Stage A, 660 per training
pair, 1860 for dev, 540 for held-out collection, 180 for recorded held-out, and
3660 for final rollouts. Log caps stay 1 MiB per stream. Parent launch logs require
a separate bounded allowance; no model or source quota is relaxed. At every
stage boundary retain failed artifacts and stop for review. This document grants
no actual runtime slot and no permission to open held-out stages early.

## Timing basis and uncertainty

The retained v1 watchdog measured **23.33608936699602 seconds** for the complete
paired training command, including source preparation/imports, both five-epoch
fits, checkpoint writes and final recorded-input evaluation. Its supervisor JSON
SHA256 is `7df03f23f3533bcd884584534cf8d2627480feb09f56d3323ac4672b32de2e1b`;
the completed training report SHA256 is
`594d4d330624ed1040ae2b3ffe2dedfbfacd6a2d360a29dcfcc6584d76b80e28`.
Those retained files are in the original `malecns-pilot/runs/` worktree under
`m7-training-watchdog-20261002/` and `m7-male-training-pilot-v1/`.

Each old variant processed 1,200 train and 600 dev ticks in each of five epochs:
18,000 tick-forwards across both fits, plus 1,200 final recorded-held-out forwards.
The new per-pair maximum is `2 × 20 × (4,800 + 2,400) = 288,000` epoch
tick-forwards. Scaling the whole old wall duration by 288,000/19,200 yields
350.04 seconds; scaling it by the epoch-only ratio 288,000/18,000 yields 373.38
seconds. Three pairs therefore suggest roughly 17.5–18.7 minutes under simple
linear scaling. The earlier rough eighteen-minute estimate used this scale.

These are estimates, not measured v2 throughput or a probabilistic upper bound.
The old run did not retain isolated fit/epoch timings or peak RSS. Backpropagation,
window tails, startup/I/O, graph realizations and machine load need not scale
linearly; natural shorter episodes may reduce work. **The frozen 600-second inner
and 660-second outer per-pair deadlines stay unchanged.** A timeout is retained as
a failure and stops the pilot, without a mid-run extension or replacement.
