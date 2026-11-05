# Numeric-complete source preservation V2 implementation

> **For agentic workers:** Use superpowers:subagent-driven-development task by task. Preserve the workspace, failed checks and all evidence.

**Goal:** Retain every admitted timing/population value through a real, non-destructive public source conversion and raw-backed reread.

**Architecture:** Wrap the unchanged V1 base bundle in an exact V2 envelope with one mandatory three-array numeric companion per original chunk. Add a public V2 source writer/reader using existing held-input, raw-audit and publication mechanisms; then wire the provisional source parent to it. This supplies software for the preservation check, not actual source qualification.

**Tech stack:** Existing Python3.11.15, NumPy2.2.5, canonical JSON, ZIP_STORED NPZ, descriptor custody and no-replace publication.

**Spec:** [Reviewed case/cell design](memory-case-cell-qualification-v2-design.md), [preservation contract](../reports/memory-compact-preservation-2026-11-05/compact-preservation-contract.md), [full goal](project-completion-2026-11-05.md).

## Global constraints and implementation decisions

- Existing V1 codec, producer, raw auditor, protocol/profile bytes and trust pins stay unchanged. No global swapping, alternate loader, generic converter registry or schema fallback.
- Explicit prospective physical-layout adjustment: the proposed 19-member single chunk becomes the unchanged 16-member base plus a three-member companion. All 19 semantic fields remain mandatory. Additional archive/index/envelope bytes count toward bounds. This is a reversible implementation choice, not an assertion that the earlier single-archive layout was implemented.
- The added arrays are exactly little-endian float64 scalar latency and step_latency and float64 population_stats with actual row shape(3,4), preserving ordering and signed-zero bits. No casts, padding, compression, alternate shapes or loss. Other population shapes fail eligibility before candidate publication.
- Nonempty source domain only at public integration. Pure codec may also cover existing eligible nonempty condition fixtures. Zero/early terminal, condition qualification/sealing, final case publication and retained-only readers remain separate future work; never use V1 as a fallback after a V2 failure.
- Raw remains fully retained. Source SNP stays at its original sole path and counts once in its separately reserved16MiB domain. Candidate output is derived as `<evidence_root>/numeric-v2/<case_id>/<run_id>/`, outside the old staged source namespace. The enclosing output roster/640MiB peak reservation includes it before execution.
- Source recording ceiling32MiB, condition codec ceiling25MiB; one combined1MiB envelope includes all non-event/non-dense/non-pixel container metadata, receipts, non-SNP support/control/markers and atomic metadata. Deduplicate identical physical paths, never duplicate real copies. Do not reuse the old producer's additional support/control MiB. Count raw, SNP, candidates and atomic peaks separately in the enclosing640MiB stage accounting.
- Existing source maximum1200rows/32rows per chunk and condition900rows stay fixed. Source worst-case dense+pixels+events+1MiB remains33,536,672bytes, only17,760 below32MiB. This conditional formula is not measured serialized feasibility; actual canonical complete sizes must fit before publication.
- No actual model/raw/SNP/protected namespace reads, native owner, research invocation, trust-pin issuance, deletion or pruning during implementation/tests. Authored fixtures only. Source parent remains closed on its unresolved whole-lifetime/pre-import/namespace/runtime/resource/GO gates. Research lanes stay audit1h/memory12h/puck5h/navigation4h/final2h,24h total; ordinary software tests excluded.
- Real source sealing consumes the already closed owner and independently validated raw-audit registration. It does **not** require a completed preservation result as a prerequisite to creating that result. Source qualification/independent lifetime acceptance follows later; no circular requirement for a previously qualified compact source or an extra owner/V1 seal.

## Review focus

1. Candidate with rehashed descriptors but changed timing/population bits must fail comparison against raw at the exact field/tick.
2. Missing/reordered/orphan companions, wrong schema/shape/endian or V1-only payload must never pass as V2.
3. Unique physical byte accounting must include all metadata/control/atomic costs and the separately referenced SNP without hidden allowances.
4. Raw/input/candidate replacement, late teardown or publication failure must retain evidence and prevent accepted output, including after intermediate proof success.
5. Parent integration must execute the public V2 path while keeping actual qualification and all existing real-execution blockers false/closed.

## Task 1: Strict composite codec and exhaustive comparison

**Files:** Create `scripts/memory_family_numeric_preservation_v2.py`, `docs/plans/memory-family-numeric-compact-v2-protocol.json`, `tests/test_memory_family_numeric_preservation_v2.py`.

**Interfaces:** `convert_candidate(base_bundle:dict, raw_rows:list, *, raw_audit_receipt:dict)->dict`; `read_numeric_compact(bundle:dict, *, raw_audit_receipt:dict)->dict`; `prove_numeric_preservation(raw_data:dict, bundle:dict, receipt:dict)->dict`. Direct conversion accepts decoded fixture/admitted rows and supplies no authority. Return merged rows and explicit preservation/qualification scope. Public source Task2 is its production caller.

- [ ] Write red authored tests for 1/31/32/33rows, full3x4 values, signed zeros and final partial chunks. Use valid unchanged V1 base/receipt fixtures, not patched acceptance gates. Preserve old fixture source bytes.
- [ ] Implement exact V2 envelope/companion index schemas and the new protocol. Bind unchanged base protocol/manifest/all file descriptors, original chunk sequence/path/SHA, compact chunk SHA, episode/start/count and one companion per partition. Exact keys/types, canonical bytes and finite bounds; no caller-supplied schema/profile.
- [ ] Reuse unchanged V1 read on the explicit base dictionary; read the three-field companions with the existing mechanical strict NPZ reader. Merge only after exact correspondence. Require `<f8` and(count,3,4), no coercion.
- [ ] Prove old obligations through unchanged producer `_prove` on the base, then compare all three additional arrays at every raw tick by dtype/shape/bytes. Timing-only tampering may leave the old trace unchanged and must still fail this proof. Population changes must fail preservation and original commitments as applicable.
- [ ] Add rehashed-corruption tests for each timing field, population bits/row/column order, early nonsampled and final ticks; wrong shape/dtype/endian/nonfinite, unknown/duplicate/missing member, orphan/reordered companion, malformed ZIP and old/new schema confusion. Test exact aggregate/recording bounds and one byte over using independently summed actual serialized bytes.
- [ ] Run focused codec tests and legacy codec coverage; preserve genuine red/green logs. Independently review the task and commit only owned files. No actual preservation claim.

## Task 2: Public raw-backed V2 source write/read

**Files:** Create `scripts/memory_family_source_seal_v2.py`, `tests/test_memory_family_source_seal_v2.py`. Task1 protocol may gain its final exact source-result/commit/conversion fields before any real freeze; do not change V1.

**Interfaces:** `seal_numeric_source_v2(evidence_root, registration, *, case_id, deadline, additional_controls=())->dict`; `read_numeric_source_v2(evidence_root, registration, *, case_id, deadline, additional_controls=())->dict`; `prune_raw_source(*args, **kwargs)` always refuses. Registration is the existing exact closed-owner V4 source export; V2 commit additionally binds the V2 protocol and derived candidate path. Additional controls are sorted, bounded exact descriptors for the enclosing parent's other metadata; conversion binds their list, holds their actual bytes and includes their unique-path charges. They supply no authority and cannot be omitted/changed on reread. Neither function creates an owner or grants lifetime/source qualification.

- [ ] Write genuine red integration tests from authored complete raw/source/SNP/control fixtures accepted by unchanged public raw audit. Use full3x4 population rows; no real model/native data. First show the public functions are absent, not fake a successful registration.
- [ ] Reuse old `_inputs`, `_raw_request`, `validate_raw_receipt`, exhaustive decode and held raw inventory for their unchanged input semantics. Keep owner/source/SNP/control bytes held; no old public seal or accepted V1 marker is published as a first phase.
- [ ] Derive the sole fresh `numeric-v2/<case>/<run>` namespace. Hold ancestor/output edges, forbid aliases/preexisting output/commit/quarantine, enforce exact recursive membership and exclusive durable writes. Original staged source remains unchanged. Mechanical helpers may be reused only where they carry no incompatible V1 semantics.
- [ ] Generate Task1 candidate inside admitted raw custody. Include registration, actual raw receipt, owner/worker/control descriptors and the original SNP reference in exact conversion/commit records. Freeze expected descriptors at validated creation; no rehash-to-trust altered controls. Write/reread every candidate file and run the full base-plus-numeric proof on actual disk bytes.
- [ ] Implement a unique-path ledger for recording, events, dense arrays, selected pixels, combined overhead/support/control/markers/atomic metadata, raw and sole SNP. Hold additional control descriptors outside raw/cases/candidate namespaces; deduplicate shared paths only with identical descriptors. Scope covers the closed export plus provided extra controls, not an asserted complete enclosing process/output inventory. Require exact sizes before marker publication. Metadata-heavy valid raw or extra controls that cannot fit must remain a retained failure; do not truncate or increase caps.
- [ ] Perform final raw/input/namespace/candidate checks and descriptor teardown before publishing the V2 marker last. On any failure preserve partials/raw/SNP; no accepted marker/result, or durable quarantine if a late marker/teardown failure is indeterminate. Public raw-backed reread repeats all proof and custody checks.
- [ ] Return `preserved-awaiting-lifetime-reconciliation`, actual_source_qualified=false and no numerical/model/physics/full-camera qualification. Distinguish raw-compared stored-field equality from digest commitments and omitted pixels.
- [ ] Cover raw/control/SNP change-and-restore, path replacement/symlink/hardlink, partial writes, occupied outputs, deadline, disk corruption, final reread/teardown and marker failure; require raw inventory unchanged and no deletion. Run focused new/public-source covering tests and independent review; commit.

## Task 3: Wire the enclosing source parent

**Files:** Modify `scripts/qualify_memory_family_source_v2.py`, its test file, and `docs/plans/memory-source-preservation-v2.md`.

**Interfaces:** Parent uses only `seal_numeric_source_v2` / `read_numeric_source_v2` for its new numeric preservation result. Retain hardwired owner, raw auditor and actual execution gates. Freeze verification must bind the new protocol/source closure before actual inputs; derive the candidate path from the existing immutable output identity.

- [ ] Write red authored integration showing the real parent reaches the public V2 writer/rereader and retains all three numeric fields while producing only the provisional terminal. Test missing/mutated new profile before any owner/import/write.
- [ ] Include the derived candidate in the prospective output/peak roster; do not create an unaccounted second32MiB V1 artifact or duplicate SNP. Census all parent control files after owner/auditor closure and pass every other metadata descriptor through `additional_controls`: retain creation-time pins for already validated controls, and hold ancillary cache metadata for accounting without treating it as authority. Reserve and enforce the64KiB future parent-terminal bound. Reconcile the complete output census/640MiB peak; Task2's supplied-descriptor ledger alone is not that proof. Update terminal marker/quarantine descriptor handling to V2, including teardown failure after intermediate success.
- [ ] Preserve original creation-time control pins, executable alias/runtime census checks and real monitor; unknown/non-drained/failed owner still blocks raw audit/conversion. The outer lifetime/pre-import/namespace/runtime/package/GO blockers remain explicit.
- [ ] Run meaningful new+parent+owner+legacy coverage, verify V1 code/protocol/pin bytes unchanged, retain failure/pass logs, independent task review and whole numeric-feature review. Commit locally; no push or research execution implied.

## Execution record

Existing isolated `research/memory-runtime-v2` worktree is reused; Tasks1/2/3 are sequential with separate reviews. The user has repeatedly authorized implementation and continuation, so no new execution-method confirmation is needed for this reversible source work. Actual exact-stage GO remains separate. Keep a dedicated ignored SDD ledger; never delete this or earlier workspaces/evidence. Task1/2 does not finish the project or general condition preservation.
