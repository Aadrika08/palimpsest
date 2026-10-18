# Capability-first phase: implementation and exploratory readout

**EXPLORATORY — not gate evidence.** The approved
[phase contract](../plans/research-capability-phase.md) is implemented. It
produces two guarded offline runners, tests, complete recorded results, compact
checkpoints, memory-v1 retirement, and a memory-v2 design. It does not qualify
R2, R3, or learned puck control. No new native rollout, reserved-data access,
hardware operation, or model promotion occurs.

## What changed and what happened

| Track | Completed work | Measured result | Current decision |
|---|---|---|---|
| Puck | Exact historical reproduction; train-only conditioning; longer schedule; wider network; train-only 1NN; folded exports | All 3 historical fits match exactly. All 9 neural probes and 1NN fail the joint recorded-dev rule. Conditioning lowers dev MSE from about .053 to about .020. | No selected model; stop automatic fitting. |
| Navigation | Exact six-fit reproduction; grouped advice panels; recovery-label audit; matched original/rewired endpoint fits; MLP and GRU baselines; W-removal diagnostic | All 6 historical fits match exactly. All 12 probes fail the joint rule. Graph/MLP onset recall is 0%; GRU's better recall comes with 14–38% false reversals. | No selected model; conditional injection unattempted because no graph-free baseline passes. |
| Memory | Honest [v1 retirement](m5-v1-structural-null.md), independently reviewed [v2 design](../plans/m5-v2-decision-scene.md) | V1 retains 44/48 accepted cells and its observed development null. V2 has no runtime or pilot evidence. | R2 remains open; spec/runtime approval and feasibility pilot are separate work. |

The [puck report](m6-puck-fit-ladder.md) and
[navigation report](m7-nav-fit-ladder.md) retain every seed, failed threshold,
empty stratum, actual command, hash, recipe, selection and unattempted candidate.
Both publications passed independent audits of raw receipts, histories, metrics,
source identities and copied checkpoint/response bytes. The results do not
establish that either task is generally unlearnable, that teacher redesign is
necessary, or that topology has a behavioral advantage.

Memory v2 explicitly makes remembered passability affect route commitment under
one shared supervisor. Its review caught and corrected three material issues:
cameras/contact remain other controller inputs; condition resources must be
substituted after an identical base snapshot; deferred inspections of unchosen
routes must not suppress goal completion. Geometry, forward-visible retreat,
arrival sensing, and CPU FLYNN route feasibility remain unvalidated design
obligations. The design does not manufacture completed R2 evidence.

## Execution bounds and failure preservation

| Allocation | Cap | Supervised time used |
|---|---:|---:|
| Combined reproduction/admission |1,200s|353.23s|
| Puck exploration |2,400s|321.05s|
| Navigation exploration |3,000s|312.38s|
| Coordinator artifact readout |600s|.015s|

Supervised stages total 986.67s (16.44min). Coordinators total 986.73s; wall time
from the first stage through scientific completion, including the implementation
correction gap, is 1,079.45s. These are within the 7,200s aggregate ceiling.
Implementation, documentation and software verification are separate from the
exploratory compute allocation. Fits execute sequentially, CPU-only, one thread;
there is no cap transfer or scientific-fit retry.

Navigation's first preflight rejects an incorrect expected producer HEAD before
reading its corpus or fitting. All pinned reader/lock hashes still match the
retained publication checkout. A narrow, synthetically verified correction pins
the exact publication commit and keeps the training revision as provenance.
The refused preflight is preserved; the corrected run is the first scientific
navigation reproduction, within the remaining original allocation.

The retained run tree contains 5,360,584 bytes. Published puck arrays total 897,942
bytes, and navigation checkpoints/responses total 3,626,880 bytes. Reports and
receipts add only compact metadata; no source camera duplication occurs. The
outer admission reserves each serial runner's full 1GiB cap plus logs under the
shared 2GiB cap and 2GiB free floor. Inputs verify unchanged after successful
stages. A 21,280,722-byte existing local upstream checkout is populated for
software verification at the unchanged pinned submodule revision; this is not
a new simulation or asset download.

[The phase JSON](research-capability-phase.json) and
[execution evidence](research-capability-execution/) retain both coordinators,
exact invocations, stage supervisor results, byte/hash inventories, original
failure, and validation harness. Individual reports preserve all scientific
source identities. No evidence is erased or retroactively declared a pass.

## Verification and repository handoff

Focused root checks pass 33 puck/model/balanced tests and 14 navigation tests,
including explicit CPU synthetic checks. Tests cover source/receipt refusal,
train-only statistics, zero variance, folded export parity, grouped splits,
recurrence carry/reset, contact-phase alignment, matched budgets, finite values,
output overlap and deadlines. Independent code review fixed a recording-root
output guard and a mislabeled false-reversal denominator before fitting.

The fresh isolated checkout initially lacks its pinned upstream mapping CSV,
and the sandbox makes the real user's cache lock read-only. Verification
populates the unchanged upstream revision from an existing local checkout and
uses an owned temporary `Path.home` fixture, without changing `HOME` or any
production source/validation predicate. The partitioned default regression
accounts for all 836 tests: **812 passed, 24 skipped**, with the three API modules
run in fresh processes. The combined process still stalls in `TestClient`
startup and times out; its cause is unresolved. Standalone baseline/research
checks pass, but partitioning does not rule out shared-state bugs. The
[validation report](research-capability-execution/validation.md) and
[receipt](research-capability-execution/validation.json) preserve results and
this verification limit. No production lab fix is implied.

Repository-local identity remains Aadrika Maurya
`aadrikamaurya@gmail.com`. The provided SSH remote is
`git@github.com-shraddha:Aadrika08/palimpsest.git`. Main remains at `ee6bf61`;
there is no automatic merge. Reviewable lanes are:

- `research/phase-decisions`: approved contract, retirement and v2 design.
- `research/puck-fit-ladder`: runner, tests, report and compact puck evidence.
- `research/nav-fit-ladder`: runner, tests, report and compact navigation evidence.
- `research/capability-integration`: complete combined implementation and readout.

Branches are pushed. Draft PR creation cannot use the available API connection:
it identifies as `pro-utkarshM`, while the explicitly requested Aadrika08 API
credential is unavailable. No account is switched, and no PR is falsely reported
created. [Prepared PR descriptions](research-capability-execution/pr-handoff.md)
make the three lanes concrete for the requested account to submit.

The next research decision concerns a new development intervention or approval
of the v2 feasibility work. This phase authorizes neither more fitting on failure
nor reserved scenes. Hardware/operator qualification and confirmatory protocols
remain outside its scope.
