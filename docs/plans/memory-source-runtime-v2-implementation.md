# Memory source runtime V2 implementation plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans task by task. Preserve the execution ledger and all failed evidence.

**Goal:** Connect one prospectively frozen real world-case-V3 acquisition to the existing independent raw auditor and non-destructive public source sealer.

**Architecture:** Add a narrowly scoped source-owner adapter and an enclosing qualification parent. Reuse Engine, snapshot serialization, policy-call instrumentation, the existing accounted process supervisor, raw auditor and public source seal/read. Preserve their existing schemas and guards. This source qualification is an engineering prerequisite; it neither substitutes for the full study nor enables condition/final-case publication.

**Tech stack:** Existing pinned Python 3.11 environment, CPU FLYNN, Linux descriptor/process custody, existing project recording/snapshot modules.

**Spec:** [Full completion plan](project-completion-2026-11-05.md), [preservation criteria](../reports/memory-compact-preservation-2026-11-05/README.md), and existing V4 raw/source contracts. The registered early-natural-failure rule in `memory-confirmatory-v3-design.md:137–140` remains authoritative for later condition work.

## Global constraints

- No actual model, graph, checkpoint, SNP or protected-catalog read and no native owner launch during source implementation or authored verification.
- Actual execution requires a reviewed exact source/runtime/input/resource freeze and the already-required exact-stage operator GO. A fixture or successful source test supplies neither.
- Research budget: 24 aggregate CPU hours; audit1h, memory12h, puck5h, navigation4h, final2h; no borrowing. All preparation, runtime, audits, failures, supervisors and accounting tail for this new source qualification charge memory. Ordinary authored software checks are excluded.
- No paid compute, automatic research retry, alternate case, evidence deletion, pruning or old-attempt reuse. Preserve consumed historical attempts01/02 and old source/profile bytes.
- The fixed candidate engineering tuple is `('development', 0, 0, 'change')`, chosen before acquisition. Its generated case/seed must be frozen before actual execution. It is not automatically reusable as a registered study observation or a broader-case qualification.
- Retain one acquired source SNP at `.pending/<case>/source/snapshots/initial.snp`; raw at `.pending/<case>/.raw/<run>/`; owner record at `.pending/<case>/source/owner.json`; external controls outside `.pending/` and `cases/`.
- Source raw remains nonempty. Natural early/zero-row conditions retain score900 but need a separately versioned evidence-admission design before any actual condition stage. No invented donor proof or missing-cell inference.
- Source sealing remains non-destructive. `prune_raw_source` and retained/final raw-residue guards remain unchanged. No historical projection packet grants production qualification.

## Review focus

Admission failure must precede model import and writes; acquired state must be captured at the real paused boundary; snapshot registration must refer to the separately stored sole SNP; close/drain failure must prevent accepted export; source/runtime/custody changes must retain failure and stop without retry. Each task below covers its owned part of these five failure classes.

## Task 1: Explicit source job and owner adapter

**Files:** Create `scripts/memory_family_source_runtime_v2.py` and `tests/test_memory_family_source_runtime_v2.py`. Do not change the historical pilot worker, producer-v3 non-executable contract, existing raw auditor or sealer.

**Interfaces:** `validate_source_job(value: dict) -> dict` validates a bounded frozen source-only job without model imports or output allocation. `run_source(job: dict) -> dict` is the internal owner used only by the enclosing parent after admission; real CLI loading is hardwired, with no fake-engine/policy option. Tests may exercise narrow private helpers with authored objects. Source job binds its exact case, canonical run UUID, source identity, immutable runtime/assets, output paths, parent allocation and limits. It cannot accept a held-out case or another operation/condition.

- [ ] Write red tests `test_admission_precedes_model_import_and_output`, `test_rejects_heldout_or_changed_generator_case`, `test_rejects_history_or_asset_alias`, `test_rejects_wrong_snapshot_raw_or_control_path`, `test_no_condition_or_retry_entrypoint`. Assert refusals occur before engine loader and before any writer invocation.
- [ ] Run only this file under the canonical source environment and retain the failing output. No actual assets may be opened.
- [ ] Implement exact job validation. Keep JSON finite, bounded and canonical; require exact fields/types, disjoint immutable/output paths, fixed source operation and externally pinned source/resource descriptors. Reject a missing enclosing admission rather than creating an allocation.
- [ ] Write red authored owner tests `test_acquired_source_emits_exact_v4_manifest_and_report`, `test_snapshot_is_captured_once_at_acquired_boundary`, `test_source_limit_without_acquisition_is_unscored_failure`, `test_close_or_identity_failure_prevents_export` and `test_no_policy_calls_after_acquired_boundary`.
- [ ] Implement acquisition using the sequencing demonstrated by `memory_decision_pilot.worker`, with the current family case accepted by Engine. Preserve CPU FLYNN, checker texture, full unmasked eyes, one policy call per motor interval and the 1,200-step source bound. Do not carry over `frozen-v1-historical-acquisition` metadata or call historical `validate_job` on a generated family case.
- [ ] Emit `memory_family_oracle_admission_v3` exactly as its existing `_manifest` requires, with current compact protocol SHA and owner-source SHA. Emit the exact twelve-field `memory-family-owner-report-v3` only for the correctly closed source. Failures have separately retained control/error evidence and cannot be made accepted by removing diagnostic fields.
- [ ] Capture/save the sole SNP using existing `snapshots.capture/save_snapshot` at the actual paused acquired boundary. Register exactly one `snapshot_registered` event with `initial=True`, filename `initial.snp` and its real SHA; do not create a raw-local snapshot/index or copy the SNP into raw. Preserve the actual event prefix before registration. Reuse existing storage checks and durability operations.
- [ ] Run covering authored checks. Require the emitted successful authored raw/support layout to pass unchanged existing raw/source schema checks; no monkeypatch of their production acceptance gates. Test error paths, signed/scalar typing where relevant, and final close/identity failure.
- [ ] Independent task review for specification and code quality; commit only reviewed source/tests and its evidence.

## Task 2: Accounted parent, terminal export and preservation invocation

**Files:** Create `scripts/qualify_memory_family_source_v2.py`, `tests/test_memory_family_source_qualification_v2.py`, and `docs/plans/memory-source-preservation-v2.md`. Modify Task1's module/tests only to expose the pure template-validation interface below. Reuse `paper/studies/change_audit_v1/process.py::run_accounted` without weakening it.

**Interfaces:** The parent has a preparation/verification mode that cannot open actual protected/model payloads, and an explicit execution entry consuming `--freeze PATH --expected-freeze-sha256 SHA`. The actual worker command, environment, source/runtime roster, unique output and limits are frozen; no arbitrary command/loader callback is available from the real CLI. `run_source` from Task1 supplies the closed owner outcome; the parent supplies real launch/reap/drain and CPU/control records.

Add `validate_source_template(value: dict) -> dict`: it accepts the same exact job metadata only with `parent_admission=None`, performs common metadata validation, and cannot authorize `run_source`. Keep `validate_source_job` strict and its existing return shape unchanged. Actual admission is attached only after execution admission, with the existing non-circular job hash. Preparation must not invent or publish an `admitted=True` placeholder to reuse the live validator.

- [ ] Write red tests `test_verify_mode_cannot_launch`, `test_closed_or_changed_freeze_refuses_before_owner`, `test_unknown_cpu_or_non_drained_owner_prevents_raw_audit`, `test_duplicate_output_is_not_a_new_attempt`, `test_deadline_covers_cleanup_and_final_receipt`, and `test_raw_and_snapshot_remain_after_pass_or_failure`.
- [ ] Freeze the complete selected input/resource contract and validate real namespace-only coverage for the two existing logical sources before native admission. Missing independently authorized projections remain a concrete input blocker; do not inspect a mixed held-out catalog to manufacture them. Clean installation/source-prefix and exact dependency closure must be prepared without deleting old bytecode or evidence.
- [ ] Implement bounded parent admission and owned process supervision. Preserve executable venv alias plus separately hashed ELF. Use real held input paths and no-replace writes. Unknown accounting stops admission; charge supervisor/parent once, never sum nested worker and subtree CPU twice.
- [ ] Use the existing native source work limit360s plus10s cleanup. Proposed enclosing qualification ceiling is900s wall,1,800 aggregate research CPU seconds,8GiB enforced runtime memory,640MiB new retained/peak output and6GiB filesystem reserve. These are a proposed maximum allocation, not execution authority or measured feasibility; before actual freeze, prove all raw/SNP/candidate/control/atomic peaks fit and reconcile all memory-lane charges. A tighter binding existing contract takes precedence; no limit is silently raised.
- [ ] After a genuinely closed/drained source only, run the unchanged independent `memory_family_raw_audit_v4.audit_raw_run` through its public CLI/API with the sole separately bound SNP. Write the real terminal export `memory-family-source-finalization-registration-v4` with job/supervisor/stdout/stderr/cleanup/audit descriptors; every descriptor must bind actual bytes from this one attempt, not synthesized successful receipts.
- [ ] Invoke public `seal_compact_source` and `read_sealed_source` on that same closed raw tree; retain and compare immutable raw inventory before/after. Do not call a synthetic converter, private preparer, retained-only reader or final publisher as an admission shortcut. Report actual stored-field preservation, original-row commitment comparison and omissions separately; a source pass is not complete paper-evidence adequacy or condition qualification.
- [ ] Author positive integration using the real source-schema checks and controlled software-only owner. Negative tests independently corrupt raw hash, snapshot prefix, report, event mapping, terminal export control identity, closure and final recheck. Verify no successful export/seal on failure, and no deletion or retry. Run only covering source tests; no actual runtime.
- [ ] Independent task and whole-feature review, including exact limits and complete accounting tail; retain source-level results. Prepare the concrete actual execution freeze and approval request only after all implementation, input and resource checks are reviewable. Do not launch it merely because CI passed.

## Task 3: Prepare the following case-bound condition stage

**Files:** Create `docs/plans/memory-case-cell-qualification-v2-design.md`; implementation belongs to its own reviewed follow-on plan.

- [ ] Specify exact case/seed/SNP/model/runtime identity in a new receipt/admission version, preserving existing historical seed400/three-trace contracts unchanged.
- [ ] Specify numeric-channel retention and zero/early natural-failure representation against the unchanged900 scoring rule before any actual own continuation. Reached-boundary obligations remain explicit; missing oracle donor evidence stays incomplete.
- [ ] Freeze one own continuation and qualification of its same closed raw, with no extra restore/repeat owner, replacement or broad seed grant. Existing numerical consumer and guarded immutable model loader should be reused. Include predeclared discriminating negative controls and independent outcome acceptance before any trusted pin.
- [ ] Keep the full48-development/48-held-out nine-condition study, order/observer qualification, complete-family analysis, CPU feasibility and separate held-out GO as remaining project requirements. No claim that this source implementation completes them.

## Plan review and execution record

The user has already requested implementation and continued goal pursuit; execute reversible source work without asking again for an execution method. The existing explicit actual-runtime GO boundary remains. Use a per-plan ledger; record source commits, exact covering checks, independent review and remaining gates. Preserve the ledger/workspace under the user's no-deletion rule.
