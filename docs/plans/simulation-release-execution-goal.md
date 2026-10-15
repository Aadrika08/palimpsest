# Goal: deliver Palimpsest in simulation

**Deliver one reproducible local Palimpsest simulation release that a new operator
can install, run, inspect, replay, export and recover, with supported controllers
and all six artworks. Prove and accept that simulation before starting the physical
rover.**

This is the active execution goal. It continues the
[original completion scope](simulation-completion-next-goal.md). The
[previous execution/evidence history](simulation-release-execution-goal-history-2026-10-15.md)
is preserved unchanged; its commands and consumed allocations are historical,
not instructions to rerun. Implementation history must not obscure what remains.

## Next milestone: one real simulator episode

**Run one bounded episode on the exact qualified local CPU runtime, then record,
replay and export it with an independently audited result.**

The deliverable is a portable bundle containing the exact source/runtime and
model/scene identities, seed and declared limits; complete episode records and
snapshots; the replay comparison; exported-file hashes; and the terminal outcome
with normal process cleanup. Complete the three steps below in order. This
milestone passes only when runtime qualification and the complete episode route
both pass their declared checks.

This is an engineering demonstration toward the complete release. A natural
task failure can still establish the recording/replay/export route; it cannot
pass a controller capability gate. Tiny fixtures, package metadata and source
test counts cannot satisfy either actual-runtime exit below.

1. **Prepare the installed runtime.** The pinned package payloads and wheel RECORD
   entries now have actual audited evidence in PR #141. Build and hash the missing
   python-louvain wheel under its own
   bounded configuration; measure the installed namespace and retain licence
   contents. Specify the exact interpreter, native/EGL paths, staging and custody.
   Finish the CPU preparation/qualification parent using the reviewed four-import
   entry. This produces a reviewable executable configuration, not a passing run.
2. **Qualify that exact runtime.** After prospective review and any required
   decision, run the separately numbered qualification once. Require actual
   NumPy, Torch, torchvision and MuJoCo versions, the unchanged identity/custody
   checks, normal process cleanup and an independent terminal-outcome audit.
   Freeze the source, invocation and finite wall-clock, output, storage, RAM,
   file-descriptor and process limits before invocation. An import pass alone
   does not qualify operators, rendering, physics, inference or collection.
3. **Prove the complete episode route.** Finish input/scene admission and the
   durable parent/worker collection path. Prospectively specify the exact model,
   scene, seed and finite episode allocation, including required operator and
   renderer checks. Retain the actual episode, snapshots, contiguous records,
   replay comparisons, exported bundle identities and normal cleanup, with an
   independent audit. Required catalog-access decisions precede protected reads.
   This is an engineering demonstration, separate from development and held-out
   studies; it grants no new navigation or memory study attempt.

Stop an actual allocation on its declared failure boundary and preserve the
outcome. A failed allocation remains failed. Before adding another prerequisite,
identify which of these three exits it blocks and the smallest check that resolves
it. Do not turn this milestone into a general package-security framework or
another sequence of source-only milestones.

## What counts as finished

All seven gates must close on **one integrated candidate**. All seven are open.

| Gate | Required evidence |
| --- | --- |
| Memory / R2 | Complete valid nine-condition development and held-out studies, independently audited family analysis and controls. A valid positive or null result is acceptable; missing or invalid cells are not a null result. |
| Learned puck | Every required relabeled model reaches at least 3/4 development and 6/8 held-out goals; mechanism replay and lab integration pass. |
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

| Order | Deliverable | Finite exit |
| --- | --- | --- |
| 1 | Establish the exact local CPU runtime. | Complete preparation and obtain a passing actual qualification under exits 1–2 above, with fresh resource admission and independent outcome audit. A failed allocation stops the lane with retained evidence; a proposal or test count is not the exit. |
| 2 | Record, replay and export one actual simulator episode. | Complete exit 3 above through the durable public collection route, retaining exact inputs, records, replay/export checks and cleanup. This does not qualify a learned controller. |
| 3 | Complete memory family admission and case closure. | Finish the reviewed historical-seed-to-case binding and single-condition admission, qualify the exact admitted configuration, and resolve the frozen oracle/own ordering conflict before all-nine/case closure. Preserve raw evidence and publication/quarantine checks. |
| 4 | Complete studies and controller capability. | Valid development and separately admitted held-out results meet the unchanged memory/scientific and puck/MaleCNS capability boundaries above. Preserve failures and resolve the next study prospectively. |
| 5 | Integrate and experience the product. | One candidate supports the lab and all six artworks; actual browser, mapping, replay, export, interruption and endurance checks pass. |
| 6 | Accept and deliver that candidate. | Artistic/operator sessions, final verification and all seven gate records are complete; the installation and evidence package are reproducible. |

**Current next action:** produce the missing verified python-louvain wheel.
Authenticate the proposed exact setuptools backend, finish the authored
source/write-routing and isolation preflights, and review the exact bounded
configuration before building. Then finish the installed namespace, licences,
native paths and executable CPU qualification configuration. The next actual
runtime result must satisfy steps 1–2 above before episode collection begins.
Review the family qualification binding in parallel without opening a new
scientific allocation. The directory-enumeration source fix is complete within
its tested scope; the first actual family admission remains open.

Independent source work can proceed while actual qualification or a decision is
pending. Stages interleave when their dependencies permit. Every new prerequisite
must name the blocked deliverable and its finite exit; do not grow an unbounded
source-hardening programme or count test totals as release progress.

## Current starting point and decisions

At **2026-10-15 06:30:08 UTC**, the project filesystem has **98,974,609,408 bytes
(92.18 GiB) available**. The same metadata-only check reports **4,768,952,320 bytes
(4.44 GiB) MemAvailable**. Disk clearance removes the reported disk blocker;
available RAM is transient and this snapshot does not admit the complete CPU/EGL
closure. Keep archives and build scratch on the project disk; stage only the exact
required runtime inputs on tmpfs under its reviewed native-identity policy.
Recheck retained inputs, actual installed sizes, writable/executable staging,
custody and all resource limits immediately before each admitted stage. The older
RAM shortfall in PR #138 remains a historical observation, not a new measurement.

- [PR #137](https://github.com/Aadrika08/palimpsest/pull/137) supplies the reviewed
  tmpfs-only native dependency identity policy; [PR #136](https://github.com/Aadrika08/palimpsest/pull/136)
  supplies finite expected-missing-import handling.
- [PR #138](https://github.com/Aadrika08/palimpsest/pull/138) supplies independently
  audited CPU package metadata and a reviewed four-import worker source route.
  The complete executable configuration and actual installed-stack qualification
  remain unfinished. Metadata sizes are estimates, not installed-payload proof.
- [Draft PR #141](https://github.com/Aadrika08/palimpsest/pull/141) supplies actual
  full-payload evidence:71 archives/385,328,518B,70 wheels with complete RECORD
  checks, and an independent terminal audit of all26,913 regular wheel members.
  The single acquisition exited0 in55.276s; no owned worker-group members remained.
  The [report](https://github.com/Aadrika08/palimpsest/blob/research/puck-cpu-payload-verification-v1/docs/reports/puck-cpu-payload-verification-v1.md)
  retains raw outcomes, exact source/configuration, full checksum index and the
  independent audit program. The
  [source-wheel proposal](https://github.com/Aadrika08/palimpsest/blob/research/puck-cpu-payload-verification-v1/docs/plans/puck-python-louvain-build-v1-proposal.md)
  selects an exact backend candidate; acquisition/build/installation of that
  backend remains prospective. No numerical runtime or release gate is qualified.
- [Draft PR #140](https://github.com/Aadrika08/palimpsest/pull/140) resolves the
  directory-enumeration gap: all33 authored condition checks pass on Btrfs and
  tmpfs, with369 affected legacy checks and88 census/admission/profile checks.
  Its [source report](https://github.com/Aadrika08/palimpsest/blob/research/memory-directory-census-v1/docs/reports/memory-directory-census-v1-source.md)
  preserves the corrected/confounded diagnostics and original failures. The new
  prospective profiles preserve all scientific fields and original frozen files.
  Actual family admission, a reviewed seed400-to-case proof binding and case close
  remain unfinished; amendment02 alone does not establish family-use admission.
- The [memory ordering audit](../reports/memory-condition-case-close-gap-audit.md)
  finds oracle before own in 42/48 families (126/144 cases), conflicting with
  existing prior-own and condition-close requirements. No resolution is selected.

**Pending prospective decisions:** memory qualification amendment 02 in
[PR #119](https://github.com/Aadrika08/palimpsest/pull/119); mixed-catalog access
versus independent identity projections in
[PR #123](https://github.com/Aadrika08/palimpsest/pull/123); the next navigation
study; and a concrete resolution of the memory ordering conflict. Continuation
and disk clearance do not approve those decisions.

Preparation 01, qualification 01, runtime observations 01/02 and navigation
attempts 1/2 remain consumed. Memory amendment 02 remains uninvoked. No silent
retry, reordered study, altered threshold or invented passing receipt is permitted.
A failed actual stage stops its lane with preserved evidence and a concrete
prospective next decision; independent implementation work may continue.

## Ownership and scope

The agent owns implementation, bounded verification, evidence, incremental
repo-local commits and authorized draft PR updates. The user owns artistic
acceptance and required prospective study decisions. An independent operator
owns the installation/encounter session. Do not merge without authorization.

Physical rover work, physical fabrication, purchases, paid cloud and CI are
outside this goal. Simulation evidence makes no physical actuation claim.
At each milestone report working behavior, actual result, remaining gap and the
next concrete action. Completion means all seven gates above pass on the same
candidate. Starting the rover is a separate subsequent user decision.
