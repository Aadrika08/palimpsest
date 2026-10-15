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

## Clear execution target after disk clearance

**The next demonstrable outcome is one actual local CPU simulator episode that
we can record, replay and export.** Package preparation and runtime qualification
are dependencies of this outcome. The complete project goal remains the release
above, with all seven gates below closed on one integrated candidate.

| Checkpoint | Concrete deliverable | Pass condition |
| --- | --- | --- |
| A — working simulation route | An exact local runtime and one portable real-episode bundle. | Retained installation admission, four-import qualification, declared operator/renderer checks, recording, replay comparison, export validation and normal cleanup pass with independent audits. |
| B — supported results | Complete memory studies and capable puck/MaleCNS controllers. | Valid nine-condition memory development and held-out analysis; every required puck model and MaleCNS seed meets 3/4 development and 6/8 held-out goals under its unchanged protocol. |
| C — usable product | One integrated lab with all six artwork encounters. | Asset-backed browser, sustained visual/audio, keyboard/viewport, faithful mapping, provenance, replay/export, interruption/recovery and endurance checks pass. |
| D — accepted delivery | A reproducible release and evidence package that another person can use. | User artistic acceptance, independent installation/all-six-mode session, final review, licences, runbook and every release-gate record are complete. |

Work through A first. Continue independent memory-contract work when it does not
open a scientific allocation. B depends on valid runtime/collection prerequisites
and the pending study decisions; C and D retain their own browser and human
evidence requirements. Disk clearance removes the disk blocker only. It does not
resolve failed controller scores, the memory ordering conflict or human acceptance.

**The next work unit is checkpoint A, ending with the episode bundle.** Its
ordered checklist is:

- [x] Accept the exact installed CPU package tree and retain its independent audit.
- [x] Accept the bounded CPU four-import observation with exact versions,
  intact pins, normal cleanup and an independent outcome audit. Distinct02
  passes; failed01 remains preserved. This supplies CPU profile data only.
- [x] Integrate the CPU profile and tmpfs copier into the dedicated bounded
  preparation/four-import parent, emitting dependency-v3/descriptor-v3. PR148
  supplies source checks and authored end-to-end fixtures only.
- [x] Freeze and independently review the production PREPARE configuration,
  binding all 24 sources and 16 input roles to accepted package receipts,
  observation02 and the declared interpreter/native/profile inputs under PR149.
- [x] Prepare and independently review the standard-library terminal/byte auditor
  and external observer. These are source controls, without an actual outcome.
- [ ] Admit fresh full-stage RAM, tmpfs/project storage, descriptors and process
  bounds. Actual RAM floors are 4 GiB for preparation and 2 GiB for qualification.
- [ ] Run the separately numbered actual tmpfs preparation once and independently
  audit its terminal outcome, complete staged bytes, custody and cleanup.
- [ ] Freeze and independently review the qualification configuration using the
  real preparation result and its passing independent audit. It is not frozen;
  no placeholder preparation hash is permitted.
- [ ] After fresh qualification admission, run the separately numbered actual
  held four-import qualification once and retain normal custody and cleanup.
- [ ] Independently audit the actual held-qualification terminal, source/input
  identities, staged bytes and cleanup. No actual installed stack has reached
  these stages.
- [ ] Specify the engineering episode's exact model, scene, seed, limits and
  required operator/renderer probes; complete the durable collection route.
  Resolve catalog access before any protected read.
- [ ] Run that episode, record its complete state/events, replay against the
  declared comparison criterion, export the portable bundle and verify cleanup.
- [ ] Independently audit the bundle and report checkpoint A's actual outcome,
  the first remaining gap and the next concrete action.

The accepted ordinary observation02 supplies actual NumPy, Torch, torchvision
and MuJoCo import/version and bounded module/native-map data. It does not establish
held-runtime, native-closure, renderer, operator, model or episode qualification.
The CPU profile, tmpfs copier and dedicated CPU parent are implemented in the
source checkpoints below. PR149 adds reviewed PREPARE controls and the independent
terminal auditor. Fresh resource admission is the next boundary; qualification
configuration follows a real preparation result and its passing independent
audit. An unchanged accepted tree does not need another installation or
retained-data admission.

Every added prerequisite must identify the checkpoint and smallest blocked check;
source-only hardening is not a substitute for reaching the episode deliverable.
A failed actual stage retains its outcome and consumed allocation. No study or
numerical invocation follows from a source fixture alone.

## Current CPU checkpoint: preparation controls reviewed, admission refused

[Draft PR #149](https://github.com/Aadrika08/palimpsest/pull/149) retains the
[source report](https://github.com/Aadrika08/palimpsest/blob/acd14e2861f8e0ec0209085dbd6b2ec302b26b64/docs/reports/puck-cpu-held-allocation-v1.md).
The production PREPARE configuration is reviewed: 7,903 B, SHA256
`38134e016eff974e06806f1ac74492dc51e0a5721d8cd13d1123a1fd950fe8a6`,
with 24 sources, 16 input roles and the prospectively selected CPU missing-import
roster `numpy._distributor_init_local`, `org`. The standard-library auditor is
independently reviewed: 58,090 B, SHA256
`19723b4ec19c6cd8fd29d38b5cbabab60f89c136ee37564f6e94175439b4eed9`.
The external observer is also frozen and reviewed. The control freeze is
committed at `7d368ebb91ee7e1d917190ae936e4cca12835618`. Qualification configuration
is not frozen: it requires the real preparation result and a passing independent
audit, with no zero-hash placeholder.

Preflight metadata found six accepted SITE leaves above the old 16 MiB inherited
file limit, with a largest leaf of 432,273,704 B. Before any actual allocation,
PR149 corrects preparation's file limit and the observer's inherited hard limit
to 1 GiB. Qualification's 16 MiB file limit, the observer's 16 MiB stream acceptance bound and
the 64 MiB output cap stay unchanged. The original uninvoked configuration is
preserved in commit `026ec3c`; this is a prospective correction, not a retry.
The real 17 MiB regression first refuses with EFBIG, then exposes the outer hard
limit; all 55 affected checks pass in 7.91 s after both corrections. Authored phase
pairs and CLI/tamper/alarm checks use stand-ins, not the installed CPU stack.

The auditor's byte-only plan matches the parent's metadata: 27,255 files /
1,318,494,346 B, 71 distributions and directory counts 2,074/2/0/0 across the four
roots. The two source-profile cache-creator bindings still need actual held
qualification. These checks do not establish custody of the actual installed
stack or operator, renderer, model, collection or scientific qualification.

Independent review permits one actual PREPARE after fresh resource admission
and rechecking the frozen control/source/input pins and absent paths. The preflight at **2026-10-15 13:08:01.377406 UTC** is **NOT_ADMITTED**:
MemAvailable was 2,852,470,784 B against the 4,294,967,296 B preparation floor.
Project and `/tmp` free bytes are 99,317,600,256 and 4,988,243,968 respectively;
all 40 source/input pins match and all actual allocation paths are absent.
No production parent or namespace was started, and the actual preparation
allocation remains unused.
This snapshot is transient: refresh admission before invocation. The next route
is preparation once plus independent audit, real-pin qualification freeze/review,
qualification plus audit, then the separately specified episode bundle.

## Earlier source checkpoint: dedicated CPU parent and authored fixtures

[Draft PR #148](https://github.com/Aadrika08/palimpsest/pull/148) implements the
dedicated bounded CPU preparation/four-import parent. Its
[source report](https://github.com/Aadrika08/palimpsest/blob/8df9faded4910e5aa1849abd23ca50971f648fac/docs/reports/puck-cpu-held-parent-v1.md)
retains the source and authored-fixture evidence.

The source route retains four registration roots, the exact 24-source roster
and 16 input roles. Its metadata byte plan is 27,255 files / 1,318,494,346 B;
this is a planned copy, not an observed staged tree or full-stage RAM admission.
Actual configurations must bind the accepted package and ordinary observation02
records, complete source rosters, candidate/profile, aliases and original trusted
interpreter/stdlib/native baseline. At that checkpoint no exact actual-stack
configuration or independent terminal auditor was prepared; PR149 above now
supplies the reviewed preparation controls.

All 326 affected source checks pass in 35.40 s. A separate test-only transport
check passes in 3.74 s. Authored end-to-end fixtures use 18 files and four stand-in
modules, with test-only 128 MiB resource floors. They prove the bounded parent
route within that fixture; actual RAM floors remain 4 GiB for preparation and
2 GiB for qualification. Qualification uses explicit descendant supervision and
a trusted `setsid`/`exec` launcher: the authored worker has PID/PPID/PGID/SID
2/1/2/2, while its escaped host process group remains covered by descendant
custody. The fixed bootstrap and worker contracts remain intact. Supervision
provides sampled operational tracking and cleanup only; hostile fork containment
and hard timing guarantees remain outside its scope.

The installed CPU stack has not been staged or held-qualified. This source
checkpoint grants no runtime/native, operator/renderer, collection, scientific,
model or episode qualification. PR149 above supplies the preparation configuration
and auditor; fresh admission, actual preparation/audit and a real-pin qualification
freeze remain open. Checkpoint A still ends with the actual episode bundle; all
seven release gates remain open.

## Earlier source checkpoint: prospective CPU held preparation

[Draft PR #147](https://github.com/Aadrika08/palimpsest/pull/147) retains the
[source report](https://github.com/Aadrika08/palimpsest/blob/7213ea1d6a9f9315708d0689648e631aece5275c/docs/reports/puck-cpu-held-preparation-v1.md).
Profile-v2 cache bindings are implemented only under dependency-v3, with terminal
completeness checks and a streaming tmpfs copier. The prospective CPU candidate
has 1,783 modules, 38 exports, 13 changes, 11 native origins and 2 cache bindings;
its root indices are SITE (0), `/usr` (1), `/etc` (2) and the generated helper (3).
The candidate is 340,908 B, SHA256
`d20076cd2e1961d1514bb135746b1701a14567136b80ee073fecedb389f929df`.
The 2,355 B generated helper is prospective source, without a historical-byte claim.

Source verification passes 62 focused checks; 66 legacy tmpfs checks pass in
59.59 s. The 342-case persistent slice has 336 passes and 6 failures: 5 reproduce
on the old base and 1 is an ancestor-change refusal. All failures remain retained; no green
full-suite result is claimed. The Cython representation gap is resolved in
source, while the predicted native-creation bindings remain unqualified on the
actual held stack. No installed-tree staging or actual CPU held qualification
ran in that source checkpoint. PR148 above now supplies the dedicated source
parent, and PR149 adds reviewed preparation controls. Fresh admission, actual
preparation and the subsequent qualification freeze/run/audits remain required.
All seven release gates stay open.

## Latest checkpoint A result: ordinary CPU observation02 accepted

[Draft PR #146](https://github.com/Aadrika08/palimpsest/pull/146) retains the
[actual02 report](https://github.com/Aadrika08/palimpsest/blob/b329093685ee2854c2bbd517accfc3cbdd9f1170/docs/reports/puck-cpu-characterization-02.md).
The separately frozen parent exits0 in17.546290720s. NumPy2.2.5, Torch2.9.0+cpu,
torchvision0.24.0+cpu and MuJoCo3.3.6 are observed in the fixed order. The private
namespace probe and worker complete normally; closure reports zero children/
threads and5→5 descriptors. Sampled parent peak RSS is82,993,152B and sampled
parent+worker peak is412,393,472B.

The independent outcome audit exits0 in4.098550721s. The publication retains82
indexed files/8,224,498B, exact source/configuration, raw receipts and terminal
outcomes;234 affected source checks pass. Evidence-index SHA256 is
`c827dc11dd3bcfe60a3020dccc008c385c779f19f60ad2bf6f930d69fcd654da`.
These results accept ordinary import observation only; all runtime/native/
collection/study/executable authority remains false and all seven gates stay open.

[Characterization01](https://github.com/Aadrika08/palimpsest/blob/05c3193d2626d670bdc9bac1ecb861b80c8ad5a8/docs/reports/puck-cpu-characterization-01.md)
remains failed and consumed, with its original source, configuration, generic
NumPy error, missing receipts and independent preservation audit unchanged.
The host-zlib correction and bounded diagnostics belong to the distinct02 profile;
the passing observation does not recover01's unrecorded underlying exception.
PR149 above now supplies reviewed preparation controls and the independent
auditor. Next admit fresh resources, prepare and audit the actual tree, then
freeze/review and qualify that exact held runtime before any episode allocation.

## Completed dependency within checkpoint A: accepted package data

**The exact retained71-wheel tree now has passing preparation acceptance.**
[Draft PR #144](https://github.com/Aadrika08/palimpsest/pull/144) retains the
[actual admission02 report](https://github.com/Aadrika08/palimpsest/blob/research/puck-cpu-retained-admission-v1/docs/reports/puck-cpu-retained-admission-02.md),
source freeze `41e128c025ac2d9c52f434ca674bdf4d1f31dadf`, exact configuration
SHA256 `32605ca0d48537a6eabf98a54d605ad23bf525456760d83726381aeaf38e3e96`,
and independently verified current bytes/receipts. The actual parent returns0
in15.475359s, admitting27,225 regular files/1,304,701,872B and2,074 directories.
The independent audit03 returns0 in4.676837s and verifies96 licence identities,
all124 source/input pins and132 receipt fingerprints. Peak sampled parent RSS
is75,276,288B; closure records zero children/threads and5→5 descriptors.

Installation01 and retained admission01 remain FAIL. The latter failed a held
ancestor/directory check after87.950787s without naming the path; subsequent
outside-ancestor activity does not establish that historical failed path.
Admission02 uses a separately reviewed private profile with full selected-tree
metadata/contents/hashes and stable outside-ancestor pathname identities.
Public collection/dependency profiles are unchanged. The sole authenticated NumPy
`.pyc` remains inert data. All124 focused source checks pass.

Checker02's configuration-serialization assumption failed before its package
census. Its source and FAIL remain preserved. The separate reviewed checker03
validates the original input hash and exact compact receipt bytes required by
the frozen writer; the actual admission was not rerun. The report retains33
byte-identical indexed files, both checker outcomes and normal terminal evidence.

- [x] Accept the exact current package tree under a distinct reviewed receipt.
- [x] Retain complete census/hashes, wheel/distribution/relocation identities,
  measured installed size and licence contents with original failed evidence.
- [x] Independently audit the result and publish the installed location,
  preparation provenance, actual limits and source/configuration evidence.

**Scope:** package preparation only. The numerical stack, native/render/operator
behavior and real episode remain unqualified; all seven release gates stay open.
Use this measured accepted tree for the next tmpfs/four-import configuration.

## Next milestone: one real simulator episode

**Run one bounded episode on the exact local CPU runtime after its held-import
qualification passes, then record, replay and export it with an independently
audited result.**

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
   entries have actual audited evidence in PR #141. PR #142 adds the built and
   independently verified python-louvain wheel: all 71 candidate wheel artifacts
   are now available, and admission02 above accepts the retained installed tree.
   PR149 supplies the reviewed PREPARE configuration and independent auditor:
   24 sources, 16 input roles and four roots, with declared interpreter,
   native/EGL, staging and custody bindings. Fresh resource admission precedes
   one actual preparation and its independent audit. Source fixtures produce no
   passing installed-runtime receipt.
2. **Qualify that exact runtime.** Freeze and independently review qualification
   only after the actual preparation result and its passing audit exist. After
   fresh qualification admission, run that separately numbered stage once. Require actual
   NumPy, Torch, torchvision and MuJoCo versions, the unchanged identity/custody
   checks, normal process cleanup and an independent terminal-outcome audit.
   Freeze the source, invocation and finite wall-clock, output, storage, RAM,
   file-descriptor and process limits before invocation. An import pass alone
   does not qualify operators, rendering, physics, inference or collection.
3. **Prove the complete episode route.** Finish input/scene admission and the
   durable parent/worker collection path. Prospectively specify the exact model,
   scene, seed and finite episode allocation, including required operator and
   renderer checks, replay comparison criterion, export validation and cleanup
   conditions. Retain the actual episode, snapshots, contiguous records,
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

| Order | Deliverable | Finite exit |
| --- | --- | --- |
| 1 | Establish the exact local CPU runtime. | Complete preparation and obtain a passing actual qualification under exits 1–2 above, with fresh resource admission and independent outcome audit. A failed allocation stops the lane with retained evidence; a proposal or test count is not the exit. |
| 2 | Record, replay and export one actual simulator episode. | Complete exit 3 above through the durable public collection route, retaining exact inputs, records, replay/export checks and cleanup. This does not qualify a learned controller. |
| 3 | Complete memory family admission and case closure. | Finish the reviewed historical-seed-to-case binding and single-condition admission, qualify the exact admitted configuration, and resolve the frozen oracle/own ordering conflict before all-nine/case closure. Preserve raw evidence and publication/quarantine checks. |
| 4 | Complete studies and controller capability. | Valid development and separately admitted held-out results meet the unchanged memory/scientific and puck/MaleCNS capability boundaries above. Preserve failures and resolve the next study prospectively. |
| 5 | Integrate and experience the product. | One candidate supports the lab and all six artworks; actual browser, mapping, replay, export, interruption and endurance checks pass. |
| 6 | Accept and deliver that candidate. | Artistic/operator sessions, final verification and all seven gate records are complete; the installation and evidence package are reproducible. |

**Current next action:** carry checkpoint A through these five finite steps:

1. Refresh resource admission for the reviewed PREPARE controls. The dated
   preflight above is NOT_ADMITTED because RAM is below the 4 GiB floor. Check
   full-stage tmpfs/project storage, descriptors and process bounds as well;
   fixture floors and content-byte plans do not admit the installed stack.
2. Once admitted, run the actual preparation once and independently audit its
   terminal outcome, all staged bytes, custody and cleanup. Preserve any failure
   without an implicit retry.
3. Freeze and independently review the qualification configuration with the real
   preparation result and its passing audit. No configuration with a placeholder
   preparation hash is accepted.
4. After fresh qualification admission, including its 2 GiB RAM floor and explicit
   descendant supervision, run the actual held four-import stage once and obtain
   its independent terminal/byte audit. The source Cython representation gap is
   resolved; predicted native-creation bindings still need actual held checks
   without skipped modules or guessed producers.
5. Resolve the engineering episode and catalog contract before protected reads,
   then run the actual recorded/replayed/exported episode with its declared
   operator/renderer checks and independent bundle audit.

Required cache, version, custody or cleanup failures stop the stage and retain
its outcome and consumed allocation; there is no implicit retry. A source
candidate or ordinary import pass does not satisfy actual held qualification.
Preserve failed characterization01 and every earlier consumed allocation.

Review the family qualification binding in parallel without opening a new
scientific allocation. The directory-enumeration source fix is complete within
its tested scope; the first actual family admission remains open.

Independent source work can proceed while actual qualification or a decision is
pending. Stages interleave when their dependencies permit. Every new prerequisite
must name the blocked deliverable and its finite exit; do not grow an unbounded
source-hardening programme or count test totals as release progress.

## Current starting point and decisions

Disk clearance permits fresh admission checks; it does not admit the installed
CPU/EGL stack. The dated PR149 preflight above refused preparation admission on
RAM before any parent or namespace started; the allocation remains unused.
Resource snapshots are transient and must be refreshed immediately
before each admitted stage. The planned 1,318,494,346-byte copy is content only,
not full-stage RAM admission. Keep archives and build scratch on the project
disk; stage only the exact required inputs on tmpfs under the reviewed identity
policy. Recheck retained inputs, writable/executable staging, custody and every
resource bound. Actual RAM floors remain 4 GiB for preparation and 2 GiB for
qualification. The older RAM shortfall in PR #138 remains historical evidence.

- [Draft PR #144](https://github.com/Aadrika08/palimpsest/pull/144) supplies
  accepted retained package preparation as detailed above. It does not accept the
  historical installer teardown, qualify the numerical runtime or close any
  release gate. Observation02 above now supplies ordinary CPU import data;
  PR148 supplies the dedicated source parent and PR149 the reviewed PREPARE
  controls and auditor. Fresh resource admission, actual preparation/audit,
  real-pin qualification freeze and held qualification/audit remain open. No real simulator
  episode or scientific allocation ran in this unit.
- [Draft PR #143](https://github.com/Aadrika08/palimpsest/pull/143) supplies the
  actual offline installation and independently verified retained namespace:
  all71 distributions,27,225 regular files/1,304,701,872B,2,074 directories and
  96 licence files/1,576,818B. UV returned0, but allocation01 exited1 in29.519s
  on `native log drain/final sync timed out`; both groups are empty. The prepared
  acceptance audit fails on one source-authentic NumPy `.pyc`. The separate failure
  audit exits0 in8.914s and verifies payloads, RECORDs,18 launchers, licence bytes
  and original receipts while keeping acceptance false. The
  [full evidence](https://github.com/Aadrika08/palimpsest/blob/research/puck-cpu-install-v1/docs/reports/puck-cpu-install-01.md)
  retains both programs and136 byte-identical indexed artifacts. All124 focused
  source checks pass, including the real authored namespace fixture. The current
  host/tool baseline matches; the missing original post-baseline receipt stays
  missing. Admission02 above now supplies a distinct preparation acceptance;
  no numerical runtime, controller or release gate is qualified.
- [PR #137](https://github.com/Aadrika08/palimpsest/pull/137) supplies the reviewed
  tmpfs-only native dependency identity policy; [PR #136](https://github.com/Aadrika08/palimpsest/pull/136)
  supplies finite expected-missing-import handling.
- [PR #138](https://github.com/Aadrika08/palimpsest/pull/138) supplies independently
  audited CPU package metadata and a reviewed four-import worker source route.
  The complete executable configuration and actual installed-stack qualification
  remain unfinished. Metadata sizes are estimates, not installed-payload proof.
- [Draft PR #142](https://github.com/Aadrika08/palimpsest/pull/142) closes the
  missing wheel artifact gap. Source-wheel invocation 02 exited 0 in 3.218s;
  namespace, authored backend fixture and target build all completed with empty
  worker groups. The portable wheel is 9,458B, with nine fully verified members.
  All nine independent terminal-audit checks pass, findings empty; 236 affected
  source checks pass. The [actual report and wheel](https://github.com/Aadrika08/palimpsest/blob/research/puck-python-louvain-build-v1/docs/reports/puck-python-louvain-build-02.md)
  retain exact source/configuration, complete raw evidence and the audit program.
  Invocation 01 remains a preserved namespace-launch failure; its independent
  failure-audit stdout bookkeeping error is recorded. Packages were uninstalled
  at that stage; PR143 retained installation data and PR144 above now accepts that
  data under a distinct preparation receipt. No numerical
  runtime, study, controller or release gate is qualified.
- [Draft PR #141](https://github.com/Aadrika08/palimpsest/pull/141) supplies actual
  full-payload evidence:71 archives/385,328,518B,70 wheels with complete RECORD
  checks, and an independent terminal audit of all26,913 regular wheel members.
  The single acquisition exited0 in55.276s; no owned worker-group members remained.
  The [report](https://github.com/Aadrika08/palimpsest/blob/research/puck-cpu-payload-verification-v1/docs/reports/puck-cpu-payload-verification-v1.md)
  retains raw outcomes, exact source/configuration, full checksum index and the
  independent audit program. The
  [source-wheel proposal](https://github.com/Aadrika08/palimpsest/blob/research/puck-cpu-payload-verification-v1/docs/plans/puck-python-louvain-build-v1-proposal.md)
  recorded the backend candidate; PR #142 above adds actual backend verification
  and the accepted target wheel. No numerical runtime or release gate is qualified.
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

CPU installation01 and retained admission01 remain failed and consumed; their
read-only evidence does not grant historical acceptance. Distinct admission02
accepts only current package preparation. CPU characterization01 also remains
failed and consumed; distinct02 accepts ordinary imports only. The earlier
preparation01,
qualification01, runtime observations01/02 and navigation attempts1/2 remain
consumed. Memory amendment 02 remains uninvoked. No silent
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
