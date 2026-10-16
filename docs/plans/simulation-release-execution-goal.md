# Goal: deliver Palimpsest in simulation

**Deliver one reproducible local Palimpsest simulation release that a new operator
can install, run, inspect, replay, export and recover, with supported controllers
and all six artworks. Prove and accept that simulation before starting the physical
rover.**

This is the active goal. It continues the [original completion scope](simulation-completion-next-goal.md).
Implementation history is preserved in the unchanged [earlier history](simulation-release-execution-goal-history-2026-10-15.md)
and the [byte-identical prior goal snapshot](simulation-release-execution-goal-history-2026-10-16.md).
Those dated records are evidence, not instructions to repeat consumed attempts.

## Active work unit: qualify the exact local CPU runtime

**Obtain one normal, independently audited completion of qualification 10 on the
exact installed CPU runtime. Keep the existing 180s normal limit and 2GiB resource
floor. This qualifies the import route only; it is the first prerequisite to the
real recorded, replayed and exported episode below.**

The source prerequisite is complete in [PR175](https://github.com/Aadrika08/palimpsest/pull/175):
the parent, observer and independent auditor explicitly bind q4 only to allocation
10. [Retained source evidence](https://github.com/Aadrika08/palimpsest/blob/e723db037ed1f790c2618798d59f56913054754f/docs/reports/puck-cpu-q4-qualification-epoch10.md)
records 732 passing affected cases, including 51 new cases, and independent review
with no material findings. Old allocations 1–9 still select q3. These are authored
source checks, not an installed-runtime pass.

1. Freeze a distinct qualification-10 control packet against source `cbe48b3`.
   Bind current source/input bytes, candidate D, nineteen negative imports,
   original preparation anchors, exact environment and limits. Preserve every
   consumed attempt 01–09, old receipt and historical absence. Independently
   review the exact controls before execution.
2. Perform fresh full byte/custody/resource admission and review its outcome.
   Disk clearance alone is not admission. Only after passing those checks and the
   final pre-invocation guard, invoke qualification 10 once under its observer.
3. Independently audit the outcome, four ordered imports, exact source and
   dependency identities, final byte checks, normal process/descriptor closure
   and complete receipts. This unit passes only if all required checks pass.
   Preserve any failure as a consumed attempt; never silently rerun it.

**Current status (2026-10-16): source ready; real controls, admission and runtime
invocation 10 have not been performed. All seven release gates remain open.**
About 45GiB of project-disk space is available at this check; each execution must
refresh its own resource checks. After import qualification, separately qualify
the finite operator/renderer route and finish the real public episode bundle.
Scientific study decisions and artistic or independent-operator acceptance
remain with their named owners.

## Next checkpoint: prove one complete simulation episode

**Run one public manual CPU episode, record it with snapshots, replay every
recorded tick under the declared comparison, and export a portable evidence
bundle. This checkpoint finishes only when independent checks verify the inputs,
recording, replay, exports and normal cleanup.** Finish these steps in order:

1. Pass the exact local runtime's separately reviewed qualification and independent audit.
2. Admit and run one bounded episode with declared model/controller, scene, seed,
   limits, operator/renderer checks, input identities, records and snapshots.
3. Meet the replay comparison criterion declared before execution; validate the
   portable export and independently audit the outcome, bytes and normal cleanup.

The bundle must retain the source/runtime/input identities, controls and limits,
complete recording and snapshots, replay comparison, source and replay exports,
member hashes and terminal/cleanup evidence. A natural task failure may prove
this engineering route; it cannot pass a controller capability gate.

| Checkpoint | Concrete deliverable | Pass condition |
| --- | --- | --- |
| A — working simulation route | Exact local runtime and one portable real-episode bundle. | Runtime qualification, declared operator/renderer checks, recording, replay comparison, export validation and normal cleanup pass with independent audits. |
| B — supported results | Complete memory studies and capable puck/MaleCNS controllers. | Valid nine-condition memory development and held-out analysis; every required puck model and MaleCNS seed meets 3/4 development and 6/8 held-out goals under its unchanged protocol. |
| C — usable product | One integrated lab with all six artwork encounters. | Asset-backed browser, sustained visual/audio, keyboard/viewport, faithful mapping, provenance, replay/export, interruption/recovery and endurance checks pass. |
| D — accepted delivery | Reproducible release and evidence package another person can use. | User artistic acceptance, independent installation/all-six-mode session, final review, licences, runbook and every release-gate record are complete. |

## Current result and first unfinished action

**The next product result is the real recorded, replayed and exported episode
bundle. Runtime qualification is its current prerequisite.** Preparation 01 and
ordinary observations 02/03 have scoped passing audits; they do not establish an
installed-runtime pass.

- [PR162](https://github.com/Aadrika08/palimpsest/pull/162) preserves failed 06:
  data admission passed, but Torchvision/PIL could not resolve its packaged TIFF
  library. Qualifications 01–06 are consumed; their failures and missing receipts
  remain preserved.
- [PR164](https://github.com/Aadrika08/palimpsest/pull/164) corrects exactly the
  two Pillow native-origin declarations in candidate D. All 678 affected authored
  cases pass. The separate post-06 data-only check 03 passed once in 26.972s with
  complete byte/forest rechecks and normal closure. Its receipt review found no
  findings; that dated result covers 06/C, not source 07/D or runtime acceptance.
- [PR165](https://github.com/Aadrika08/palimpsest/pull/165) freezes distinct 07 at
  pushed commit `1a1ffa0`. Its fresh data-only admission passed once in 42.608s,
  with independent receipt review. **Its one runtime invocation failed at the
  180s normal-return deadline.** The external observer returned 1 normally in
  180.400s; supervision stopped the worker with SIGTERM and sampled no matching
  survivors. Both worker logs are empty, and final outcome/baseline-after receipts
  are absent. The independent auditor correctly refused the nonzero transport.
  Attempt 07 is consumed. No completed four-import or parent-closure claim follows,
  and the retained evidence does not identify which worker phase exhausted time.

The bounded diagnostic source is now implemented and reviewed at
[`5ccde54`](https://github.com/Aadrika08/palimpsest/blob/5ccde54d8f41d1f83ec858b2cdb8eb12755c795e/docs/plans/puck-cpu-runtime-phase-trace-v1.md).
Its final 217 disjoint authored checks pass: 214 worker/consumer cases in 119.86s
and three persistent historical-publication integrations in 46.53s. It adds 18
nominal stderr checkpoints with a best-effort cap of 24 attempts/16KiB; terminal
stdout follows close. The reviewed nested-latch and old-bootstrap compatibility
fixes preserve q1/q2 and owners without the optional hook. Failed green01/consumer01
source validations remain retained without a new root-cause claim for their
storage-metadata/native persistent failures. These authored checks do not explain
the installed 07 timeout or establish installed-runtime acceptance.

[PR167](https://github.com/Aadrika08/palimpsest/pull/167) implements the closed
diagnostic 08 source support and is independently reviewed with no material
findings. All 630 disjoint authored cases pass: 622 private cases in
26.42s and eight persistent integrations in 119.48s. The initial three REDs and
mixed-layout source-validation result (two failures/622 passes) remain retained.

[PR168](https://github.com/Aadrika08/palimpsest/pull/168) preserves actual 08.
Its controls were reviewed and pushed at `2f74653` before execution. A
pre-execution raw-stream-cache fix passed five control checks, including the
original four; its uninvoked revision remains retained. Fresh 08/D data-only
admission passed once (33.702s externally; 33.522s in the source receipt), with full
SITE/staged/native/current-control byte checks, nineteen absences, six old PID
identity samples and 4→4 descriptors/no children or threads. Independent receipt
review was GO; this was data admission, not runtime acceptance.

**The sole 08 runtime invocation failed at the 180s normal-return deadline.** The
external observer returned 1 normally in 180.464s without external timeout;
supervision stopped the worker with SIGTERM(-15) and sampled no matching survivors.
Eleven worker-relative markers include NumPy return at 38.084s, Torch return at
79.741s and last-seen Torchvision entry at 81.564s. No later marker, result,
baseline-after, completed four-import receipt or parent-closure evidence exists.
The last marker does not identify where the remaining time was spent. The audit
CLI correctly refused the nonzero transport; it did not perform a full post-run
payload check. Attempt 08 is consumed; the cause remains unknown.

[PR169](https://github.com/Aadrika08/palimpsest/pull/169), pushed at
[`3975f8a`](https://github.com/Aadrika08/palimpsest/commit/3975f8a158c0899e9c640b323488de9a0f0a40df),
completes the authored guard-cost measurement. The original passes nine cases in
13.43s; its 2048-entry cache median is 93.742ms/check. The direct variant measures
1.517ms/check but has two failures/seven passes on overridden container membership.
The hoisted variant measures 1.068ms/check but has one failure/eight passes on callback removal.
Both faster probes change current behavior; production remains unchanged.
Independent outcome review found no material findings. All 32 artifacts/291,335B,
including three empty files, verify against originals, source Git and the committed
archive. These synthetic cases do not establish the cause of 08's timeout,
installed qualification or independent FD proof.

Bounded guard accounting in [PR170](https://github.com/Aadrika08/palimpsest/pull/170) at
[`d76b9f3`](https://github.com/Aadrika08/palimpsest/commit/d76b9f332c034a994bc2e867604a551df8c66a1f) retains the original union: restricting cache
values to exact built-in types cannot prevent asynchronous mutation. This unit
changes only bootstrap production source; the qualifier is unchanged. Its q3
cost channel is separately bounded to 32 attempts/32KiB and 1024B per row, with a
cooperative 10s cadence; the phase channel remains 24 attempts/16KiB. The final 304
disjoint authored cases pass: 302 private cases in 242.70s and two persistent
integrations in 24.43s. Independent source and final evidence review
found no material findings. All 136 artifacts/1,560,197B (13 empty files) verify
against originals, source Git and the committed archive. These source checks neither identify 08's installed timeout cause
nor establish installed qualification. At that source-only checkpoint, no actual
09 controls, admission or runtime invocation existed; attempts 01–08 remained consumed.

Closed 09 source support in [PR171](https://github.com/Aadrika08/palimpsest/pull/171) at
[`96ace37`](https://github.com/Aadrika08/palimpsest/commit/96ace37062fd14e20ae1ebd2371b90fa88f8d7ab) changes only the parent, independent auditor and
observer production scripts; bootstrap and qualifier are unchanged. The authored
API coverage includes normal acceptance when optional cost rows are absent.
Final validation passes 673 disjoint authored cases: 664 private cases in 24.71s
and nine persistent integrations in 110.19s. Independent source and final evidence
reviews found no material findings. All 145 artifacts/2,138,968B (eight empty files)
verify against originals, source Git and committed archive bytes. At that
source-only checkpoint, no actual 09 controls, admission or runtime invocation existed.

As of 2026-10-16, actual 09 controls are prepared and independently reviewed at
[`60e5756`](https://github.com/Aadrika08/palimpsest/commit/60e5756d8c670e898320b26b3a2cee267577e53c)
([PR172](https://github.com/Aadrika08/palimpsest/pull/172)), binding source `96ace37`. Nine small history-control
checks pass. The metadata-only self-check covers 1,259 pins / 81,114,419B; exact
control and proof-roster reviews found no material findings. These checks retain
the genuine failed 08 evidence and the unchanged byte/custody, absence and limit
contracts. These were pre-execution source/control checks, not runtime acceptance.

[PR172](https://github.com/Aadrika08/palimpsest/pull/172), with outcome at
[`31d980b`](https://github.com/Aadrika08/palimpsest/commit/31d980be15921b206eb77d2455931cc44c06270e), preserves consumed actual 09.
Fresh data-only admission passed once in 29.175485s externally, with full current
byte/custody checks and normal FD4→4 closure; independent receipt review passed.
**The sole runtime invocation failed at the unchanged 180s deadline** (external
normal exit 1 in 180.517676s, no external timeout). Supervision stopped the worker
with SIGTERM(-15); its sampled matching-survivor list was empty. Final result and
baseline-after remain absent; no parent-closure or completed four-import receipt
exists. The one audit correctly refused the nonzero transport, without a complete
post-run payload audit.

The retained stream has eleven phase and nineteen optional cost rows. NumPy and
Torch returned; the last phase is Torchvision entry at 87.536113s. The final cost
row at 175.091295s reports cumulative cache 59.248136s, bindings 31.626744s and
custody 30.099583s. These incomplete, unauthenticated source counters may include
nested work and instrumentation; they are not exclusive timing or proof of the
full timeout cause. Independent outcome/publication reviews found no material
findings. All 144 artifacts / 13,668,698B / seven empty files match the retained
originals and source/control Git origins. Attempts 01–09 remain consumed; no
actual 10 controls, admission or invocation exist.

The completed authored equivalence experiment is preserved in
[PR173](https://github.com/Aadrika08/palimpsest/pull/173) at [`69af058`](https://github.com/Aadrika08/palimpsest/commit/69af058e9e59815e6731affe7cc7fc3f03111a2f).
Its plan and new case were committed first at `fb20e74`. Unchanged production
passes seven semantic cases in 10.01s; the sole in-place candidate passes six and
fails one in 9.73s. Both deselect the three timing cases. The original propagates
the reflected-union sentinel, closes owned holders and stays poisoned; the
candidate skips that exception. It is rejected without a performance run.
Independent source/outcome/publication reviews found no material findings. All
63 artifacts / 680,759B / two empty files verify against retained originals and
test-first source Git. This rejects one rewrite, not every possible optimization.
No installed-runtime or performance acceptance follows.

The explicit q4 boundary-snapshot guard is implemented in source commit
[`1fa9421`](https://github.com/Aadrika08/palimpsest/commit/1fa94213f583a30e6c5533a45bef5575b45e9095);
[source evidence](https://github.com/Aadrika08/palimpsest/blob/89f51ab1ec08b2a210152b5fe4b675a281aa24c5/docs/reports/puck-cpu-guard-contract-v4.md)
records 41 distinct q4 guard/entry, 397 legacy and three cost cases with passing
evidence: 441 across split batches, not one all-green invocation. Four retained
legacy import-path failures passed a targeted environment-only correction.
Historical median batch/3 costs were 0.705/5.833/93.742ms at 128/512/2048 names;
q4 measured 0.721/1.517/4.729ms. This unpaired authored comparison uses different
contracts/context/diagnostics; q4 is slightly slower at 128 and shows bounded
reduction at larger sizes, without installed-speed or actual 09-cause proof.
Q4 deliberately changes sampling semantics, preserves q1–q3 and remains
non-atomic with ABA/post-observation limits. At that source-only checkpoint,
existing outer epochs remained unchanged and old-parent admission refused q4.
No installed runtime or actual 10 was qualified or invoked by that source unit.
Scientific protocols, model thresholds and human acceptance gates remain unchanged; all seven release gates remain open.

[PR175](https://github.com/Aadrika08/palimpsest/pull/175) closes the distinct CPU
qualification-10 source epoch at `cbe48b3`. Its complete authored parent→q4 worker→
independent API/CLI route passes. The affected regression passes 732 cases in
122.64s, including all 51 new cases; these counts overlap. Independent review
found no material findings. The [report](https://github.com/Aadrika08/palimpsest/blob/e723db037ed1f790c2618798d59f56913054754f/docs/reports/puck-cpu-q4-qualification-epoch10.md)
preserves the initial fixture mistakes and intended REDs, exact source pins,
normal authored closure, optional-cost-row acceptance and specific mixed-tag
refusals. Authored fixtures use 18 missing names and 128MiB floors; production
still requires nineteen names and 180s/2GiB. No installed qualification follows.

**First unfinished action:** freeze and independently review the distinct actual
10 controls against that fixed source, then complete fresh full byte/custody/
resource admission. Once admission and its review pass, invoke actual 10 exactly
once and independently audit the outcome. Preserve attempts 01–09 and every
historical missing receipt. This is the finite exit from the current runtime
prerequisite; it does not admit operator/renderer, physics, inference or studies.
After the separate operator/renderer route qualifies, finish the real recorded,
replayed and exported public episode bundle. The full release remains the goal.

[PR163](https://github.com/Aadrika08/palimpsest/pull/163) already implements the
manual constructor seam with exact arguments and seed/reset order preserved;
its 19 authored cases pass. It has not run a real episode or renderer. Integrate
that source work into the product route.

Reuse `Engine` → UUID `RunWriter` → initial snapshot → replay → bundle export.
The numeric `PuckIntervalWriter` format cannot simply be passed to those readers.
The proposed public route uses the checker scene at upstream `8d964599`;
protected inputs remain closed. Complete the finite CPU worker/import/operator/renderer bindings
and the same admitted reopening route for replay. Declare the exact inputs,
seed, limits and comparison criterion before execution, then package the source
and replay exports with controls and comparison evidence without widening the
export whitelist.

Every prerequisite must name the blocked milestone and its smallest finite exit.
Source fixtures, PRs and test totals do not replace the episode. Do not grow a
general package-security framework. Independent episode and memory-contract
implementation may proceed without opening an allocation.

## What counts as finished

All seven gates must close on **one integrated candidate**. All seven are open.

| Gate | Required evidence |
| --- | --- |
| Memory / R2 | Complete valid nine-condition development and held-out studies, independently audited family analysis and controls. A valid positive or null result is acceptable; missing or invalid cells are not a null result. |
| Learned puck and supported tasks | Every required relabeled puck model reaches at least 3/4 development and 6/8 held-out goals; mechanism replay and lab integration pass. Supported exploration, homing and adaptation retain their scoped evidence. |
| MaleCNS | Every required seed reaches at least 3/4 development and 6/8 held-out goals under matched budgets. A topology benefit is not required. |
| Lab | Asset-backed installation and actual browser inspection, replay, exports, interruption/recovery and required endurance pass. |
| Six artworks | Sufficient portable inputs and declared-duration visual, audio, keyboard, viewport, faithful mapping, control and provenance checks pass for every encounter. |
| Human acceptance | Recorded user artistic acceptance and an independent operator's installation and all-six-mode session. |
| Integrated delivery | Reviewed integration, final verification, reproducible installation, licences, limitations, runbook and complete requirements-to-evidence matrix. |

The encounters are **Afterimage; One map, many possible lives; Counterfactual
choir; Borrowed body; Atlas of what disappears; The space between two flies.**
The [release matrix](../requirements-evidence.md) tracks individual requirements.
Source tests and additional PRs close implementation tasks only. They do not
substitute for numerical results, capability, actual browser use or human acceptance.

## What we do next

| Order | Product milestone | Done when |
| --- | --- | --- |
| 1 | One working episode bundle. | The exact runtime and public engineering route qualify; one nonzero episode has complete records and registered snapshots, all ticks pass the declared replay comparison, exports validate, and independent outcome/byte/cleanup audits pass. A task failure can prove this route, not controller capability. |
| 2 | Valid memory results. | Frozen ordering, seed-to-case and admission issues are resolved prospectively; all nine conditions have valid development and separately admitted held-out results with independently audited family/control analysis. A valid positive or null result counts; missing or invalid cells do not. |
| 3 | Supported controllers. | Every required relabeled puck model and MaleCNS seed meets unchanged 3/4 development and 6/8 held-out goals; mechanism replay and lab integration pass, with scoped exploration, homing and adaptation evidence retained. |
| 4 | A usable six-artwork lab. | One asset-backed candidate passes actual browser, declared-duration visual/audio, keyboard/viewport, faithful mapping, control/provenance, replay/export, interruption/recovery and required endurance checks for all six encounters. |
| 5 | Human acceptance. | The user records artistic acceptance, and an independent operator completes installation and an all-six-mode session. |
| 6 | Reproducible delivery. | All seven gates close on that same integrated candidate; final review/verification, reproducible installation, licences, limitations, runbook and the complete requirements-to-evidence matrix are ready. |

## Decisions and evidence boundaries

- Memory qualification amendment 02 in [PR119](https://github.com/Aadrika08/palimpsest/pull/119)
  remains uninvoked. Oracle precedes own in 42/48 families (126/144 cases),
  conflicting with prior-own/condition-close requirements. No resolution is selected;
  do not reorder the frozen protocol. The reviewed seed 400-to-case binding,
  exact single-condition/family admission and remaining cells still need closure.
- Protected mixed-catalog access versus independent identity projections in
  [PR123](https://github.com/Aadrika08/palimpsest/pull/123) remains a user decision.
  Use declared public engineering inputs while it is unresolved; continuation or
  disk clearance does not authorize protected reads.
- Navigation attempts 1/2 are consumed; no attempt 3 is authorized. R3 and the new
  navigation study/held-out decision remain open. Existing failed controller scores
  do not pass the capability thresholds above.
- Installation 01, retained admission 01, characterization 01 and every earlier
  consumed allocation remain historical failures. Distinct later scoped passes
  do not rewrite them. Never fabricate a missing receipt or silently retry.
- Runtime-import qualification cannot admit operators, rendering, physics,
  inference, collection or a scientific study. Freeze each actual route separately
  with exact source/input/custody/versions, finite limits, fresh resources and
  independent outcome checks. Keep build/evidence scratch on project disk and
  stage only required inputs on executable/writable tmpfs under the existing
  identity policy. Existing preparation/qualification RAM floors remain 4/2GiB;
  every future admission refreshes its own exact limits and bytes.

## Ownership and scope

The agent owns implementation, bounded verification, evidence, incremental
repo-local commits as Aadrika Maurya, and authorized draft PR updates/pushes as
Aadrika08. The user owns artistic acceptance and prospective study decisions.
An independent operator owns the installation/all-six-encounter session.
No automatic merge follows.

Physical rover work, fabrication, purchases, paid cloud and CI are outside this
goal. Simulation evidence makes no physical-actuation claim. Complete and accept
all seven gates on one candidate before a separate user decision starts the rover.
At each milestone report working behavior, observed result, first remaining gap
and next concrete action.
