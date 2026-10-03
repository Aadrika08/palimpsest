# Counterbalanced development: staged plan

Current status: audited [C3](../reports/m5-counterbalance-stage-c-v3.md) and
[C4](../reports/m5-counterbalance-stage-c4.md) complete eight selected cells / all
nine conditions. [Frozen-observation A](../reports/m5-frozen-observation-wave-a.md)
and [B](../reports/m5-frozen-observation-wave-b.md), controller references and
reference replays are also retained. The full 48-cell development matrix and
held-out qualification remain open. The final section fixes the remaining-cell
continuation plan; it authorizes no source implementation, data acquisition,
held-out access, controls freeze or runtime launch.

## Historical initial A/B/C proposal

Stage A/B source preparation, based on reviewed replay evidence `78e4ba8`.
The bounded admission runner is prepared; no actual launch is authorized, and
held-out splits remain unopened. Stage C/full-batch execution remains a proposal.
Engine, application schema, sensors and controller production code are unchanged.
The shared handoff audit now joins physical subjects rather than lexical fact IDs
(`009c950`), with original and permuted-order fixtures; canonical cases are unchanged.

The completed manual, fixed FLYNN and replay data remain immutable. This proposes
the smallest admission check and limited comparison before deciding whether a
48-cell development batch is feasible. It does not assert statistical power or
choose geometry to produce a memory benefit.

## Existing factors and concrete cells

Use existing `make_world_case(seed, regime, 'development-test', kind=kind,
acquisition=True, change_tick=300)` with seeds **24–31**, regimes **local_cue /
paired_cue**, kinds **change / null / no-event**. Exactly 8 × 2 × 3 = 48 cells.
All eight bit combinations are represented: bit 0 swaps relation-to-physical-side,
bit 1 swaps fact lexical order, bit 2 swaps subject lexical order. Subject order
is an additional ID nuisance factor, not a second goal-route factor.

| Decimal seed | Existing case ID suffix | Lower relation | Lower fact suffix | Lower subject suffix |
| --- | --- | --- | --- | --- |
| 24 | `00000018` | local_cue | a | a |
| 25 | `00000019` | paired_cue | a | a |
| 26 | `0000001a` | local_cue | z | a |
| 27 | `0000001b` | paired_cue | z | a |
| 28 | `0000001c` | local_cue | a | z |
| 29 | `0000001d` | paired_cue | a | z |
| 30 | `0000001e` | local_cue | z | z |
| 31 | `0000001f` | paired_cue | z | z |

Existing public case ID is `live-development-test-<suffix>`. A cell key must also
include regime and kind, for example `s24/local_cue/change`. The current generator
intentionally shares bank/entity IDs between the six cells at one seed; there are
**eight namespaces, not 48 independent instance namespaces**. Each cell gets a
fresh recording UUID, event/prefix/native lineage and a fully hash-bound case.
Within-seed reuse permits matched regime/schedule comparisons; it must not be
mistaken for independent samples. These namespaces are disjoint from original
history IDs and earlier development seeds 8, 9 and 16. No current-case entity,
regime, geometry, gold or test bank enters `fit(E)`.

`change` closes the passage associated with the selected regime and flips the
cue at 300. `null` flips the cue with unchanged occupancy. `no-event` leaves both
cue and occupancy unchanged. Live M always starts unknown; both known before
expectations must come from actual recorded packets, with full retained evidence.
Historical local/paired E bundles and exact E-only refits remain those pinned by
the completed FLYNN protocol. Own uses the matching historical artifact, swapped
the other artifact, hand-authored stays explicitly local_cue, and the other seven
conditions keep their current definitions. Only retrieval gets runtime historical
E; only oracle gets independent evaluator gold. Target budget remains one.

## Geometry and observability remain conditional

Keep the existing west acquisition lane, source ticks 200–299 at v=0/yaw 9°,
source-only privileged pose supervision, paused public goal move to [-0.5, -2.7],
source before/after/native proof and declared-cue-only fixed FLYNN continuation.
All nine conditions share the same source, world and policy/RNG anchor within a
cell. No private bearing, motor rescue, larger sensor or post-outcome tuning is
introduced. U and selector configuration/resources may differ; all nine are not
U-only conditions.

This geometry is asymmetric: at boundary 300 the source is near the upper
inspection landmark, while the common goal and later route are lower. An upper
closure can be observed and committed at the event boundary before a selected
inspection affects motors. The existing lower closure was incidentally observed
and committed at 358 in every condition. Balance of labels does not remove this
observation-opportunity or goal-route confound. Report which changed subjects
were already locally observable at the event; do not pool their correction times
as though all selections had the same opportunity to cause a revisit.

A read-only sensor check on all 129 retained own FLYNN poses found the existing
lower goal visible at all 129 frames and at correction/handoff 358. A hypothetical
upper goal [-0.5, 2.7] was visible at only 16 frames, first invisible at 316 and
invisible at 358. This is geometry evaluated on a retained lower-goal trajectory,
not an executed upper-goal prediction; changed goal graphics/cues could change
that trajectory. Simply doubling goal sides is not an admitted balanced profile.
No upper goal is adopted here. A later route-balanced protocol would need its own
prospective admissibility and sensor/navigation contract, without selecting a
pose or fallback after observed failures. This proposal qualifies only the fixed
lower-goal profile, not route-independent memory benefit.

## Three separately reviewed stages

**A. Pure coverage, no owner.** Enumerate all 48 parameter cells, validate generator
metadata/geometry/schedule/types, all eight factor combinations, ID relationships,
historical/test separation and condition-specific information access. Verify
change has exactly one occupancy difference, null/no-event have none, no-event
has no trigger, and gold uses genuinely observed stale expectations only. A
synthetic selector check may diagnose expected targeting, but remains synthetic;
it supplies no live known M, E or acquired evidence. Freeze raw and semantic case
pins against the actual authoring source before later GO. No old-version hash is
presented as a new-source pin.

A bounded pure enumeration already validates all 48 unknown-M runtime cases on
this planning base; its ignored index is
`runs/m5-counterbalance-preparation-78e4ba8/cases.json`, SHA
`6297af880eb153684d9e1f106c57eaea96b6f3108a6cf3073324a5c7bf6f2b29`.
This is preparation coverage, not execution of stages B/C or a held-out freeze.

**B. Eight short admission cells, 24 owners.** Predeclare exactly this diagnostic
subset, independent of outcomes:

| Cell key | Schedule | Actual closure for change |
| --- | --- | --- |
| `s24/local_cue/change` | change | lower |
| `s25/local_cue/change` | change | upper |
| `s26/paired_cue/null` | null | none |
| `s27/paired_cue/no-event` | no-event | none |
| `s28/paired_cue/change` | change | upper |
| `s29/paired_cue/change` | change | lower |
| `s30/local_cue/null` | null | none |
| `s31/local_cue/no-event` | no-event | none |

For each cell: fresh manual source 300 ticks; atomic empty-U CPU FLYNN anchor
zero ticks; a no-U neural probe with exactly one actual policy tick at 300,
pausing at 301. There is no own-U anchor or nine-condition claim in this stage.
Require actual packet 299, relocated-world probe and packet 300 visibility,
evidence-backed M, exact controller-replacement preservation, correct gate/cue
outcome and correct actual observation eligibility. Never fabricate packet 300
or convert an observed-but-uncommitted atomic failure into a revision. Preserve
each existing 300-boundary source and empty-U anchor for exact later reuse.

This subset covers every seed bit combination, both closure sides under each
regime, and all three schedules under each regime. It is not the full factorial:
its schedules are deliberately incomplete across lexical combinations. It checks
physical/sensor admission before expensive comparisons, not performance or power.
Unexpected source/invariant/infrastructure failure stops with unattempted cells;
no replacement or retry. A recorded task failure remains failure and may make the
source unsuitable for later comparison; it is never passed as successful coverage.

**C. Four complete diagnostic comparisons, 40 added owners.** Only after B is
reviewed, reuse its exact source/empty-U anchor for:
`s24/local_cue/change`, `s29/paired_cue/change`, `s30/local_cue/null`,
`s27/paired_cue/no-event`. Each adds one zero-tick own-U anchor and the existing
nine FLYNN continuations, at most 300 ticks each. This avoids reacquisition and
retains identical within-cell initial model/hidden/RNG/non-U state. Both change
cells target the physical lower passage with fact suffix a; they test learned
relation transfer in matched geometry, not lexical/side generalization. Null and
no-event test false targeting and absence of selector invocation. This four-cell
subset is a resource/admission pilot, not an unbiased estimate of the 48-cell
matrix or a completed counterbalance. No automatic full batch follows.

## Readouts, nulls and implementation boundary

Reuse existing selector dispatch, native guards/readers, policy-call/row binding,
world geometry gold and evaluator accounting. The original verifier is deliberately
hard-coded to seed 16/change and its trigger/evaluator assumes one event/closed
gate; it cannot execute this proposal unchanged. The new fixed eight-cell
`scripts/verify_memory_counterbalance.py` composes its source/native guards and
the neural runner's actual policy-call binding, quota and owner supervision.
Null/no-event validation stays local to the new admission runner; actual behavior
is still unverified until a frozen runtime gate. Keep old frozen runners/results unchanged. No Engine, schema,
controller, sensor or generic experiment framework expansion is proposed.

Gold comes from actual before/post clearance plus pre-source observed expectations
and consecutive visible cue evidence; never from selected IDs, U or regime labels.
Null gold is empty despite a real cue change: false targets/costs are valid results
and abstention is correct. No-event requires **zero actual selector invocations**,
zero targets/inspection requests and zero selector behavior bytes; represent that
absence in the report without inventing a memory_selection event. Current learned
rules may select a relation on null because the cue alone cannot prove occupancy
changed. Report this tradeoff instead of changing fit after seeing outcomes.

For every case/condition retain targets, exact-set correctness, false/missed counts,
precision/recall with undefined values as null, correct abstention, payload/envelope/
history/validation-versus-behavior bytes, actual observation and committed revision
separately, uncertainty/censoring, requests/starts/resolutions/timeouts/unresolved
facts, first input/neural/motor divergence, contact/path/reward, goal/terminal reason,
and independently evaluated task outcome versus worker placeholder. On null,
post-event fresh observations are confirmations, not corrections of stale values.
Missing correction or goal is null/censored with reason; do not impute 600 as an
observed completion time. Keep per-cell paired own/swapped/sham/no-U differences;
frames and the nine branches are not independent samples. Own/sham parity remains
a mechanism check. No arbitrary effect threshold, power, significance or guarantee
of benefit is introduced. Preserve exact task failures; infrastructure/invariant
failure stops the gate with unattempted entries.

No-U here retains the declared memory sensor/bridge and passive evidence updates.
It is not relabelled as unmodified upstream FLYNN or a separate raw sensor-only
architecture. PRD §15.4 controller-baseline distinctions and any route-balanced /
held-out qualification remain separate reviewed work.

## Resource ceilings and full-matrix decision

Retained actual twelve-stage evidence used 323,246,836 recording bytes and
336,870,129 indexed recording/SNP bytes, with 482.156 s outer wall. Source recording
was 61,768,821 bytes/300 ticks; a 129-tick neural recording was 29,054,194 bytes.
The existing numeric shape derivation remains 216,094 bytes/tick, before events/
NPZ/metadata. These are measured references, not promises for new cells.

| Prospective stage | Owners / maximum control ticks | Finite output / free floor | External wall |
| --- | --- | --- | --- |
| B | 24 / 2,408 | 6 GiB / 2 GiB | 3,900 s |
| C | 40 / 10,800 added | 10 GiB / 2 GiB | 6,460 s |

Each child keeps 160 s external / 150 s internal, 192 MiB recording, one 16 MiB
initial SNP, and 1 MiB per stream. Use the existing pre-publication snapshot guard
for these verifier owners, a 64 MiB bounded control/monitor headroom and sampled
start-verified cleanup; no parallel owners, retry or tuning. Require full declared
allowance plus free floor/headroom before each stage. Include new stage output
and controls in aggregate accounting, keep B's retained inputs immutable during C,
and check global free space. The 24 × 208 MiB and 40 × 208 MiB worst-case recording/
SNP sums are below their respective quotas with log/control margin. Stage B's
setup-only wall reference is approximately 730 s from eight observed source +
two-zero-step-owner setups; probe inference/controls add cost. Stage C remains a
separately admitted ten-owner-per-cell gate, not covered by B's runtime GO.

A full fresh 48-cell matrix has 576 owners and at most 144,000 control ticks. Simple
scaling of the observed case gives about 16.17 GB indexed bytes and 6.43 h wall,
but different trajectories, failures and 300-tick neural continuations may increase
both. The unchanged per-owner recording/SNP ceilings alone sum to **125.63 GB**,
and child wall ceilings total 92,160 s before cleanup. That worst-case retained
allowance is not available on this local workspace. After B/C, review actual
length/storage distribution and choose a finite separately frozen full-batch
allowance or an explicitly retained external-storage/wave policy. Do not launch
576 owners, silently discard earlier raw data, assume the observed 129-tick length,
or present the current disk as sufficient. Source-case and output/launcher IDs,
resource preflight and first-failure/unattempted accounting must be frozen before
any full-batch GO.

Root review is needed for the concrete staged scope, the fixed-route interpretation,
and the later storage/full-matrix decision. Held-out case IDs, splits and artifacts
are not generated or opened by this proposal.

## Stage B prepared review boundary

Pure preparation only: no worker has started. The ignored prepared plan is
`runs/m5-counterbalance-stage-b-preparation-009c950/prepared-plan.json`
(586,017 bytes), SHA `ecaedc5c9341063eaa619635da69bda2149dd66e46ed1d01a7ffe13834515131`.
Protocol SHA `85f6ec028aefa4d02a4c61701452f2a5275f57744786adf8670ec238960ee214`;
runner SHA `ffb7fa9d3b84441c6fa05945b893d4c4028481502d80355f8e951e5238d30927`.
The source inventory actually verified 122 pinned upstream files and 10 declared
assets. An independent frozen outer source/test/lock/upstream/asset inventory and
PID/PPID/PGID/start monitor are still required before any runtime GO. The full
plan binds every raw and semantic case pin to this source; historical planning
case hashes are not substituted. Output must be fresh:
`runs/m5-counterbalance-stage-b-20261003`.

One parent holds the existing storage lease throughout the batch; each child
shares that allowance and is the sole serialized payload writer. No concurrent
owner, retry, replacement cell or goal/target tuning is admitted. A failure before
the next owner preserves the preceding owner's passed status, names the current
unattempted owner and stops. Any attempted task/runtime/admission failure stops;
it is not accepted as successful coverage. Normal close is required on every
owned Engine. The prospective outer bound is 3,900 s plus explicit cleanup grace;
start-verified surviving-owner cleanup and any forced signal must be reported and
fail the operational gate. Nested process groups must be surveyed independently.

Worst-case recording/SNP payload is **5,234,491,392 bytes** (24 × 208 MiB).
A conservative retained estimate adds 48 MiB child streams, 72 MiB for 24
supervisor/worker/job envelopes (1 MiB each), 2 MiB plan/report, and 64 MiB
outer/control/monitor allowance: **5,429,526,528 bytes** (5.06 GiB). This estimate
is below the enforced 6 GiB aggregate ceiling; envelope size is bounded by the
existing writers/validators, and outer controls must share aggregate accounting.
Require 6 GiB + 2 GiB floor + 64 MiB headroom before admission. This is a bound,
not a measured Stage B recording size. Maximum numeric ticks remain 2,408.

| Cell | Source UUID | Empty-U policy-anchor UUID | One-tick no-U probe UUID |
| --- | --- | --- | --- |
| s24/local_cue/change | `b3cbd532336d4b86a5d2c6545dff91b8` | `ba309a22cb374001a180ba7d20f8bb1b` | `0c98e6ff6280435795b3dacd4a578f13` |
| s25/local_cue/change | `fff91d6a5a40470c963469b5a02960ca` | `d8028dc1dd2a45658cd299a087ec48fe` | `22afca39e626414085caa639b260a83b` |
| s26/paired_cue/null | `2b29549c42e647518102f8e0511b087d` | `1f29205a25664bb78dff5d46a89b4652` | `a1b15dc6b2914f8e88d2b7d2297d726e` |
| s27/paired_cue/no-event | `19d59574a0e242f08060753c37694b4e` | `881e9078ad38428c9e0e172873302b30` | `b78286d80c56445da2eb3272c8deb432` |
| s28/paired_cue/change | `dbc07665346a4fdb89b6040387612bf8` | `eef0d4869a9940a88204e2de727eac20` | `f96b989d9b8b44a2857ce2716c53cbce` |
| s29/paired_cue/change | `5c2d61f814e24b1590dd0ae3b71a1f52` | `80b95e4d84e84d0a91c36197c11165aa` | `aed1cc64bb1b4ea49209198279e8436b` |
| s30/local_cue/null | `e41be252316046a88f81dc593c4a51d8` | `bda16c15d1d349c19a154cd453e25442` | `357f6d9af3414230b94f186a2ea693b9` |
| s31/local_cue/no-event | `44cfe6e3628a4958bfe8b4fc146d7349` | `88ee6eb04dde4e1d9d294fa0541b8840` | `baef9736aab0487992367243188e0123` |

The native detector299 and actual packet300 must reconstruct exactly the recorded
trigger/selection; reconstructed values are audit-only and never injected into
Engine or history. No-event requires zero trigger/selection events and zero
selector behavior bytes. Null requires the recorded cue flip, unchanged actual
clearance, empty gold and separately recorded observed confirmations/revisions.
Gold uses actual before/post clearance and retained observed pre-event M, with
unknown facts excluded. Passive upper-passage correction observed at tick 300 is
reported as an actual event; the one-tick stage does not score completed tasks or
aggregate correction/goal times. Controller access stays real CPU `policy.act`
with step-only commands and exact row/input/output bindings. Across cells the
case seed also changes controller/RNG initialization; only within-cell native
anchors are matched. Stage B is diagnostic admission coverage, not an effect estimate.

Pure command:

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest tests.test_memory_counterbalance tests.test_memory_transfer tests.test_flynn_memory_transfer tests.test_memory_experiment -q
```

No actual invocation is authorized by this document. Review/freeze the new source,
prepared plan, bounded outer launcher and cleanup/resource inventory before GO.

## Retained Stage B outcome

The separately authorized frozen gate at `8506407` completed all 24 owners and
2,408 numeric ticks with no retries, failures or unattempted cells. Native/source
identity and cleanup checks passed. Upper changes were passively observed and
committed at 300; lower changes remained stale at the one-tick stop. Null gold
was empty; no-event cases had zero trigger/selector invocation and zero selector
behavior bytes. Task completion and benefit remain unscored. Exact results,
immutable hashes and the two retained audits are in
[the Stage B evidence report](../reports/m5-counterbalance-stage-b.md). At that
historical boundary, Stage C, full-matrix and held-out execution still required
separate reviewed runtime GO. Later C3/C4 evidence supersedes that status only.


## Approved remaining development scope, 3 October 2026

Complete the existing 48-cell design: seeds 24–31 × local_cue/paired_cue ×
change/null/no-event. Exclude the eight completed C3/C4 cells below; do not repeat
or relabel them. Forty cells / **360 condition readouts** remain. Every cell keeps
all nine conditions: own, swapped, sham, no-U, hand-authored,
history-independent, traversal, retrieval and oracle; target budget stays one.
Only retrieval receives historical E and only oracle receives evaluator gold.

The fixed chunks enumerate seed, relation, then schedule, omitting completed
cells. `local` and `paired` below mean local_cue and paired_cue. Each table entry
is a separate cell, including within-seed reuse; there remain eight namespaces,
not 48 independent instances.

| Chunk | Exact four remaining cells |
| --- | --- |
| 1 | s24/local/null; s24/local/no-event; s24/paired/change; s24/paired/null |
| 2 | s24/paired/no-event; s25/local/null; s25/local/no-event; s25/paired/change |
| 3 | s25/paired/null; s25/paired/no-event; s26/local/change; s26/local/null |
| 4 | s26/local/no-event; s26/paired/change; s26/paired/no-event; s27/local/change |
| 5 | s27/local/null; s27/local/no-event; s27/paired/change; s27/paired/null |
| 6 | s28/local/change; s28/local/null; s28/local/no-event; s28/paired/null |
| 7 | s28/paired/no-event; s29/local/change; s29/local/null; s29/local/no-event |
| 8 | s29/paired/null; s29/paired/no-event; s30/local/change; s30/local/no-event |
| 9 | s30/paired/change; s30/paired/null; s30/paired/no-event; s31/local/change |
| 10 | s31/local/null; s31/paired/change; s31/paired/null; s31/paired/no-event |

Completed, excluded cells are s24/local/change, s25/local/change,
s26/paired/null, s27/paired/no-event, s28/paired/change, s29/paired/change,
s30/local/null and s31/local/no-event. Earlier partial C1/C2 failures stay separate
and do not count as completed cells.

### Prerequisites and finite execution boundary

The current admission validator accepts only historical B's eight cells;
comparison accepts only C3/C4 and their original B pins. A narrowly versioned
fixed-cell extension must reuse the existing source, owner supervision, readers,
selector dispatch, native guards, evaluator and strict C4 core forks. Preserve
historical profile defaults, protocol hashes, path contracts and records. No
Engine/schema/sensor/controller change or experiment framework is needed.

Each chunk first requires four fresh unknown-M sources, four empty-U CPU FLYNN
anchors and four one-tick admission probes: **12 owners**. Actual packets must
establish both before expectations, visibility and schedule/geometry outcomes.
Then reuse those exact acquired anchors for four own-U anchors and 36
continuations: **40 owners**. Total remaining scope is **520 owners**, at most
120,040 numeric ticks. Freeze source/case/history/native/control identities and
all fresh UUIDs before each separately reviewed runtime GO. Preserve one parent
lease, serial owners, 160-second external / 150-second internal bounds, 192 MiB
recordings, 16 MiB SNPs, 1 MiB streams, target limit one and no retries. Admission
and comparison remain separate finite gates, retaining the existing 6 GiB and
10 GiB allowances, 2 GiB free floor and 64 MiB headroom; new exact parent deadlines
require source review before controls preparation.

New own/swapped/sham/no-U core forks inherit one shared selector and retain full
non-U invariants. Other five conditions retain explicit resource/configuration
differences. Historical C3 remains broader; C4 and the new core remain strict.
Do not pool them as an entirely strict U-only physical matrix. A strict-core
claim over every development cell would additionally need a separately named
four-anchor/16-continuation C3 preparation, not reinterpretation or repetition of
all nine historical conditions. It is not included in these 40 remaining cells.

Gold stays actual clearance plus acquired expectations; null confirmations are
not stale corrections; no-event requires zero invocation/behavior bytes.
Natural failures/censoring and null benefit remain outcomes. Infrastructure,
invariant, quota or source drift stops the gate with exact unattempted IDs.

### Measured cost, storage refusal and interpretation

Retained B admission took 729.3387 seconds / eight cells and used 524,242,270
output bytes. C3/C4 comparisons took 1881.2165 / 1836.5973 seconds and used
1,098,312,862 / 1,104,708,610 output bytes, respectively, for four cells each.
These scopes include output artifacts, unlike the reports' separately indexed
reference totals. Scaling observed lengths gives approximately **6.2 hours and
13.6 GB** additional output: about 37 minutes / 1.36 GB per chunk, plus small new
controls/audits. Longer trajectories or failure retention can increase both;
this is not a power calculation or guaranteed fit.

The read-only planning check measured 32,104,431,616 free bytes. The unchanged
recording/SNP caps alone permit 113.4 GB across 520 owners; the worst case cannot
fit locally. Recheck global free space and full finite allowance/floor/headroom
before every gate. Refuse the next gate if retention no longer fits; obtain
explicit retained external storage rather than discard old evidence, shrink
conditions or relax limits. No automatic ten-chunk launch is authorized.

This completes the **fixed lower-goal-route estimand** if all remaining cells are
retained and analysed; it does not establish original broader route-independent
qualification. Preserve acquisition, goal relocation and sensing geometry,
including upper passive corrections and incidental lower observations. Do not
change routes to force benefit. Route-independent claims need a separately
validated profile/protocol; the fixed-route experiment can finish with a null
result. Existing reference/replay qualifications need no automatic repetition
for every new cell.

Full48 development alone does not complete M5/R2. The approved implementation
gate still requires separately frozen held-out splits, budgets, tolerances,
outcomes, all-condition targeting/closed-loop bundles and paired analysis.
Reserved held-out IDs 64–71 remain unopened and unfrozen. The PRD's proposed
30-layout/300-layout counts are planning targets, not an already frozen memory
suite or power claim. This plan authorizes no held-out generation/access,
acquisition, source edits, controls preparation or runtime execution.
