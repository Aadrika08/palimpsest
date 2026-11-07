# Source owner and independent qualification: readiness

2026-11-06. Source-only audit at root-supplied clean `b7a967026d1261b20450024e271f7cfc790dfd17`;
HEAD/cleanliness were not independently rechecked. Only source/docs/named static metadata were read.
No imports, tests, probes, runtime/asset/raw/SNP/catalog/protected payload reads or hashes, execution,
network, dependency/CI work, cleanup or extra agents. Only this report is written.

## Verdict

**The complete actual producer plus independent qualification contract is not implementation-ready.**
The canonical bootstrap is implemented and reviewed; it fixes one necessary creation boundary.
The remaining gap is an exact provider-neutral native-parent/input and successor qualification contract,
not another wrapper, zero replay, boolean acceptance field or authored holder. Retained source does not
specify enough to freeze its exact API/keysets/roles/trust roots without making new authority choices.

**Accounting adoption is not a prerequisite to designing or unit-testing a provider-neutral workload.**
Nor do missing actual descriptor values alone prevent specifying software that consumes them later.
Those facts must not be used to defer the engineering clauses below to the user. Conversely, a private
owner core with injectable success callbacks would not deliver the missing actual backend.

The fixed future owner remains `scripts/memory_family_source_runtime_vnext.py`. Do not implement a
launcher/accounting mode, fabricate Q/L/R/admission, or count an always-refusing actual API as completion.

## Already fixed, and reusable without new authority

1. Creation must call the **real shared** `Engine.open` with `source_bootstrap_mode='canonical-prepared-vnext-v1'`,
   genuine exact `HeldProvenance`, original canonical absolute repo/asset roots, generated/validated family-v3
   case, matching seed, CPU FLYNN/checker/memory-decision-v2, fresh options and canonical hyphen UUID.
   Preserve that UUID in job/path/owner/writer/events/application/SNP/report from creation; never normalize
   legacy bytes. Open returns ordinary memory **state3**, paused at tick0, not acquired/accepted/state4.
   Evidence: bootstrap contract `:19–75`; implementation review `:14–19,39`.
2. Reuse the old algorithm, not its authority/envelopes: audit actual policy inputs, issue ordinary queued
   policy `step` commands, require paused full-eye CPU FLYNN each step, stop only at genuine unarmed acquired
   boundary within **1..1200** steps, episode0, total_tick=episode_step and memory/world cursor=boundary−1.
   Never configure a condition or selector, restore, replace, retry or delete. `policy_step` and `audit_policy`
   are real existing mechanisms (`memory_decision_pilot.py:522–544`); acquired semantics are validated by
   `memory_decision.py:279–287`, not a worker-supplied acquired flag.
3. Capture exactly one original SNP via real snapshots.capture/save_snapshot and actual application state.
   Preserve its real pre-registration event prefix `{sha256,size_bytes,event_count}`; register its actual digest
   afterward, then close the real writer/environment before independent reading. SNP boundary, report,
   terminal manifest, rows, events and raw prefix must agree; no second/synthetic/normalized SNP.
   Existing sequence: `memory_family_source_runtime_v2.py:317–348,393–444`;
   prefix/boundary checks: `memory_family_raw_audit_v4.py:387–401,405–494`.
4. Keep every prefix on failure, including broken-recorder running manifests and cleanup/report failures.
   An owner report is not sufficient success evidence; independent reading rejects incomplete/failed outcomes.
   Bootstrap broken-writer clarification is binding. No repair around caps, condition, retry or deletion.

## Minimum unresolved engineering clauses — one concrete contract, not more helper milestones

| Clause | Exact missing choice to freeze | Why existing source cannot supply it |
| --- | --- | --- |
| **Parent → workload entry** | One named fixed entrypoint and owner/qualifier signatures; exact serialized job versus live held-input arguments; schema/keysets/types/caps; who authenticates source plan, immutable runtime/model/input roster, namespace and enclosing job/deadline/allocation; which facts must hold **before native/model import**; exact refusal and lease-release behavior. The parent assertion must explicitly distinguish external execution GO from workload metadata. | Old job validation checks a live enclosing assertion, not its authority (`source_runtime_v2.py:1–8,214–240`); V3 public entry refuses (`:530–534`). `HeldProvenance` constructs diagnostics from supplied authenticated pins; it authenticates no registration (`held_provenance.py:1–7,97–125`). A new dict/token/duck holder cannot fill this boundary. |
| **Successor raw/codec epoch** | Direct successor job/owner/outcome/report/raw-audit/E/V/C validators; exact keysets and cross-record equalities, canonical ID checks, source-only source3 application/row/SNP contract, descriptor roles and physical path formulas. Name the source files that own these validators and the independent raw auditor. | Old job requires hex (`source_runtime_v2.py:143–148`); old raw auditor requires hex and old manifest admission (`raw_audit_v4.py:61–68,725–767`); producer requires old development registration (`producer_v4.py:43–102`). New canonical records cannot be passed through these validators by renaming schemas or stripping hyphens. Preflight `:38–40` fixes some outer names, not this nested contract. |
| **Genesis Q and guarded replay loader** | Separate execution-time admission of the first independent qualifier from later acceptance of its output Q. Freeze exact trusted input/loader receipt and external pin ownership, genuine full model/runtime closure, independent reader/acceptor, Q schema/scope/keysets and source bindings. No Q prerequisite that requires the very Q being created. | `_replay_rows` provides computation but no path/receipt/model admission (`cell_replay_v4.py:1–6,51–129`). Existing public replay binds old envelopes (`:157–210`). Old loader gates on a **previous independently accepted** historical receipt before reads/imports (`replay_admission_v1.py:52–57,240–269`), and its trust root is empty (`qualification_pins_v1.py:1–10`). It cannot bootstrap successor Q by self-attestation. |
| **Physical slots, call order and close scope** | For every J/job/owner/raw/SNP/control/audit/E/V/C/Q and failure/atomic output: sole role/path, cap, empty status, defining record, creation stage, retained count and writer/reader; precreated directory/ancestor mutation map; exact source/qualifier recheck frequency and lease release. Define bounded source-production L scope separately from subsequent F/R/admission/holder work and assign every later phase to a finite accounted roster. | Preflight `:35–46` gives an acyclic DAG but not a complete slot ledger. Strong held ancestors detect sibling creation (`source-custody-contract-review.md:39–49`). A pre-F/R L cannot establish whole-operation closure including F/R/readers (`:9–13,59`). Generic 1MiB decode limits do not create metadata storage capacity. |

These are root engineering decisions for independent review. No source evidence authorizes this audit to
invent an actual admission authority, complete native-parent provider, accepted Q/L/R or actual typed holder.
The parent contract can be provider-neutral; changing the resource/accounting boundary cannot.

### Concrete decisions root can take now

- Separate **workload invocation** from admission: the parent must authenticate the frozen job/plan/source
  closure, runtime/native/model load environment and input namespace before entering the owner. Do not put
  `parent_admission: {admitted:true,...}` into the successor job as an independent acceptance mechanism.
  Validate job structure/canonical digest/deadline in the worker, but call these consistency checks only.
  Root must name the real fixed parent-entry gate and how its authenticated state reaches this worker;
  no such accepted interface currently exists. This is the specific missing external interface to request.
- Choose one fresh source-only callable owner, no CLI/launch/condition/history/retry surface, and a separate
  source-only raw auditor + numerical qualifier. Reuse proposed J/E outer keysets verbatim (preflight `:38–39`),
  freeze a **new** job and direct canonical owner/report/audit/V/C envelopes alongside them; do not add source
  acceptance fields to the Engine. Root can own these schema choices without choosing an accounting provider.
- Retain the source layout candidate: `.pending/<case_id>/.raw/<canonical_run_id>/recording/`, sibling raw
  `worker-report.json`, `.pending/<case_id>/source/owner.json`, sole `source/snapshots/initial.snp`, and external
  `controls/<canonical_run_id>/` for job/supervisor/stdout/stderr/cleanup/audit. E remains outside source/raw/numeric.
  This is a candidate until every input holder's ancestors and precreated output branches are reconciled.
- Preserve source-stage component maxima512MiB raw +16MiB SNP +32MiB candidate +8MiB controls +8MiB atomic
  +64MiB headroom =640MiB; logs≤256KiB each inside controls, not extra capacity. Preserve900wall/1800CPU/8GiB,
  worker360s and cleanup10s as proposed limits, not measured cost (`qualify_source_v2.py:35–40`). Assign all
  successor metadata/failures to those slots before claiming fit; do not silently allocate another receipt tree.
- Keep producer output **recorded/unqualified**. Run independent raw audit and guarded positive source replay
  after real close, then independent Q acceptance, then bounded L, F and R in the acyclic DAG. Split L's source
  scope from later F/R/holder/accounting readers; none becomes exempt. Freeze genesis loader admission before
  coding it; later acceptance pins belong outside their own source/receipt hash closure. This prevents both
  producer-self-qualification and a Q-needs-Q bootstrap cycle without weakening the actual acceptance gate.

## Independent Q must contain real work

Reuse **`memory_family_cell_replay_v4._replay_rows`**, through a new directly validated successor wrapper:
real exact FlynnPolicy/full pinned cell, CPU float32/eval/one thread, model/controller identities and genuine
held inputs; operation='source', first_tick=0, input_width=4813, rows count equal SNP episode_step in1..1200.
It resets source hidden to zeros; compares **every row's** raw output and mapped action bitwise; compares
final hidden to the original SNP source endpoint; checks tensors/runtime and input immutability; restores
caller policy/state/cache/diagnostics on exit (`cell_replay_v4.py:51–129`). None of that is a producer flag.

The successor wrapper must independently establish rows/raw/codec/SNP identity, real held FD decode,
runtime/model provenance and source tensors before calling the core, and recheck through teardown.
Old `qualified_replay` demonstrates hold-before-load and active-session checks (`:159–225,240–285`),
but its fixed seed400/historical scope/runtime roster and old source pins are not successor authority.
Current `hold_runtime_manifest` supplies current-byte custody, explicitly **not** qualified execution
(`memory_source_runtime_closure_v1.py:641–701`). Reusing it needs an independently admitted loader/input
contract, not promotion of `runtime_qualified=False` to true. Q is encoded-cell/source-endpoint evidence,
not proof of full native physical replay or full project feasibility.

## Meaningful unit acceptance after the contract is frozen

Use actual shared Engine.open/constructor, genuine held-provenance factory, readonly resolver, real writer,
case/profile/world/memory validation, ordinary submit/advance/acquisition logic, original SNP container and
real closed-output readers. Controlled native/RNG/model allocation boundaries are ordinary unit evidence.
Require a positive source3 acquisition and independently decoded positive-row replay path; do not patch
admission/trust/state guards or merely assert that mocks were called. Exercise first and1200th-step acquisition,
no acquisition/termination, wrong eyes/controller/device, cursor/state divergence, duplicate output/SNP,
canonical-ID disagreement, prefix/raw/tensor/row/endpoint mismatch, deadline/cap/write/close/recheck/teardown
failures and retained incomplete prefixes; prove refusals precede forbidden allocation/import/output.

A small real FlynnPolicy/cell unit can test `_replay_rows`; it cannot qualify the full model. No new tests
were run here. Exact owned implementation/test files beyond the fixed owner **are not frozen** because
validator/qualifier/loader ownership is one of the missing clauses; naming only the owner and its tests
would conceal the absent independently useful backend. Do not start that partial slice as the deliverable.

## What only the user or independent inputs can resolve

- **User policy choice:** retain all-project-process final CPU accounting, or prospectively adopt the explicit
  provider exclusion/interval-charge proposal. The latter is UNADOPTED; its own `:103–108` requires user choice
  before implementing its launcher. No GNU Time provider/topology is selected here. Under the current boundary,
  administrator/watchdog/bespoke-reader final tails remain unknown and justified whole-operation upper=null
  (`memory-source-accounting-contract-next.md:25–29,37–64`). This blocks actual admission, not source contract drafting.
- **Independently supplied facts:** both authorized namespace-only exports (`pre-heldout-development-history`,
  `training-namespace`), exact allowed roots/identities and independently admitted runtime/native/model/load
  environment/lifetime/capacity/provenance, plus prior-cost reconciliation. Engineering cannot derive these
  facts from filenames or inspect protected catalogs as a substitute. Old qualifier lists missing interfaces
  (`qualify_memory_family_source_v2.py:259–317,630–640`). A CPU choice alone supplies none of them.
- **Separate exact actual GO:** only after a reviewable bounded packet and independent inputs/accounting exist.
  No actual GO exists here; software tests are excluded ordinary units, not source execution authorization.

**Next action:** root freezes the four engineering clauses together in ONE exact provider-neutral owner +
independent qualifier contract, with independent authority review; resolve the explicit CPU boundary choice
separately before any launcher implementation. If the fixed native-parent/admission interface cannot yet be
named, stop there and request that specific external interface; do not implement a fake accepted producer.

Full goal unchanged:96 families (48 development +48 held-out) ×3 kinds ×9 conditions;24 aggregate CPUh lanes
1 audit/12 memory/5 puck/4 navigation/2 final, no borrowing. Source-stage proposal1800 CPU s/900 wall s/8GiB/
640MiB is not measured feasibility. Actual6a.2/Q/L/F/R/backend/GO remain absent. Raw deletion stays disabled.
