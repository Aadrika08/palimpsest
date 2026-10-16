# Goal: deliver Palimpsest in simulation

**Deliver one reproducible local Palimpsest simulation release that a new operator
can install, run, inspect, replay, export and recover, with supported controllers
and all six artworks. Prove and accept that simulation before starting the physical
rover.**

This is the active goal. It continues the [original completion scope](simulation-completion-next-goal.md).
Implementation history is preserved in the unchanged [earlier history](simulation-release-execution-goal-history-2026-10-15.md)
and the [byte-identical prior goal snapshot](simulation-release-execution-goal-history-2026-10-16.md).
Those dated records are evidence, not instructions to repeat consumed attempts.

## Active work unit: review a compatible guard fastpath

**Review the current mutation and dispatch contract, then decide whether a
small fastpath can preserve it.** This is the immediate task toward checkpoint A;
the complete simulation release above remains the goal.

1. Use the retained measurements and authored cases to describe the guard's
   existing cache callbacks, container overrides and mutation visibility,
   including legitimate acceptance and required refusals.
2. Review the smallest compatible fastpath design against that contract. Preserve
   current callback/container behavior and custody checks; a stronger restriction
   is a contract change, not an equivalent optimization.
3. Independently review the design. If no small compatible design is supported,
   retain the original guard and define bounded guard-time accounting before
   further installed qualification. This unit ends with a reviewed design or a
   retain-and-account decision; it does not create a general framework.

Authored measurements cannot prove the installed timeout's cause or qualify the
runtime. Any later installed qualification needs distinct reviewed controls and
fresh resource admission. Attempts 01–08 stay consumed; this work unit creates
no 09 controls and invokes no installed qualification. Preserve the 180s deadline,
2GiB qualification RAM floor and all custody and refusal checks.

Disk clearance permits preparation; each actual execution still needs its own
fresh resource checks. After runtime and separate operator/renderer qualification,
finish the real episode bundle below. Scientific study decisions and artistic or
independent-operator acceptance remain with their named owners.

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

**First unfinished action:** review the narrow mutation/dispatch contract and a
small compatible fastpath design preserving current cache callback/container
acceptance, refusal and custody. If no such design is supported, retain the
original guard and define bounded guard-time accounting before further installed
qualification. Require independent source review before separately reviewed future
controls. Preserve the old 05–07 predicates, failed/consumed 01–08 outcomes and the
unchanged 2GiB RAM floor/180s normal-return deadline. No 09 controls, admission or
invocation exist, and there is no silent 08 retry.
After runtime qualification and separate operator/renderer admission, the product
exit remains one real recorded, replayed and exported public manual CPU episode.
Detailed raw results remain in the linked PR/report packets, dated histories and
Git history.

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
