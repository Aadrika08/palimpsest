# Task 3 independent review

## Spec compliance

- **PASS for the bounded Task 3 source-only contract.** Reviewed supplied base `f00dc47` to head `7bd0a860869a980ae30840f8e6d0818e74610e6b`; all four specified files have corresponding changes, with no owner/helper/CPU/numeric-policy changes in the package. `scripts/qualify_memory_family_source_v2.py:163` selects only V3-freeze/V2-job or V4-freeze/V3-job, and `:196` validates the exact B reference, frozen requirements equality, and prior consistency without external payload reads. The two plan changes describe the same prospective boundary (`docs/plans/memory-source-preservation-v2.md:79`, `docs/plans/memory-numeric-preservation-v2-implementation.md:25`).
- **Cannot verify from this diff:** Task 1's complete manifest custody, physical inventory and ledger implementation, and Task 2's full independent owner-layout/deadline enforcement. The parent consumes those interfaces at `scripts/qualify_memory_family_source_v2.py:555` and `:940`; the authored parent/child test at `tests/test_memory_family_source_qualification_v2.py:1008` checks interface integration, not real process or installation qualification. Whole-migration review must assess these earlier tasks together.
- **Cannot qualify actual adoption:** pre-freeze completion, global prior completeness, publication/freeze tails, complete model/graph/asset dependency coverage, pre-import/native isolation, resource fit, external lifetime acceptance and GO remain explicitly unresolved (`scripts/qualify_memory_family_source_v2.py:313`, `:806`). Five runtime prefixes plus an assets-directory existence check at `:521` do not establish complete asset coverage. The existing old path also depended on external qualification; this is not a newly discovered Task 3 gate bypass.

## Strengths

- Real V4 execute refuses unconditionally before external runtime binding or output creation, including when verification is substituted with successful-looking JSON (`scripts/qualify_memory_family_source_v2.py:632`, `:695`, `:765`; regression `tests/test_memory_family_source_qualification_v2.py:974`). Pure verification retains explicit false authority flags and unresolved blockers (`:311`).
- Parent custody uses independently frozen roots/pins, its own layout and alias checks, and one full holder recheck per identity callback rather than repeated per-descriptor full-tree checks (`scripts/qualify_memory_family_source_v2.py:521`, `:543`). Parent and child receive the original absolute runtime deadline, with the tighter source deadline retained (`:938`; test `tests/test_memory_family_source_qualification_v2.py:1008`).
- Accounting uses held exact integer totals and rejects authority claims (`scripts/qualify_memory_family_source_v2.py:221`). The fixed allocation is checked by the shared integer `_prior` implementation, not by reconstructing nanoseconds from floats; old floating fixed-allocation admission is skipped only for V4 (`:932`). Authored ledger coverage includes exact lane boundary and inconsistent values (`tests/test_memory_family_source_qualification_v2.py:1027`).
- Complete emitted controls feed the unchanged numeric sealer; the parent additionally charges the original pinned external freeze bytes (`scripts/qualify_memory_family_source_v2.py:904`, `:1058`, `:1066`). The final strengthened test independently sums actual authored physical bytes and strictly positive reserves at exactly 1 MiB and one byte over (`tests/test_memory_family_source_qualification_v2.py:1061`). Equal-content copies remain separate physical costs (`:1116`).
- Known-overhead precheck, complete post-seal/read checks, and existing finalization compose correctly: an overflow or checked teardown failure cannot return a preserved report and quarantines an already published marker (`scripts/qualify_memory_family_source_v2.py:1066`, `:1116`, `:1120`). Late overflow retention is directly exercised at `tests/test_memory_family_source_qualification_v2.py:1132`.

## Findings

### Critical

- None found in the reviewed Task 3 scope.

### Important

- None found in the reviewed Task 3 scope.

### Minor

- **Parent-only late handle-close coverage is missing.** `tests/test_memory_family_source_qualification_v2.py:99` raises whenever `close_error` is true and two contexts have been created. Consequently `test_v4_handle_teardown_failure_cannot_return_preserved` at `:1225` fails the child context first, before audit/sealing; it does not reach a parent-only close failure after provisional preservation. Add a party-specific fault (for example, only the first-created context raises on exit) and assert stopped status, retained commit plus quarantine, and retained raw/SNP. This is a coverage gap rather than a demonstrated code failure: the parent finalizer at `scripts/qualify_memory_family_source_v2.py:1122` explicitly changes status and quarantines on teardown exceptions.

## Checks and evidence

- Read the complete task brief, binding global constraints, approved requirements amendment, implementer report and supplied diff. Initial tool output cut off the middle of the diff; recovered only the omitted parent/test hunk ranges. No second whole-diff pass or Git-state commands were run.
- Named integration risk: older floating validation might reject or bypass V4 integer lane admission. Checked the omitted `verify_freeze` and core context (`scripts/qualify_memory_family_source_v2.py:242`, `:832`) and the shared `_charge`/`_prior` source (`scripts/memory_source_runtime_closure_v1.py:380`). Canonical upward floats plus integer fixed-allocation admission are preserved; live float monitors remain conservative containment.
- Named integration risk: splitting external original-freeze accounting from the sealer might omit controls/reserves or permit late preservation. Checked the omitted control registration/census and finalizer (`scripts/qualify_memory_family_source_v2.py:824`, `:865`, `:1010`, `:1080`) and unchanged sealer `_external`/`_account` plus reserve constants (`scripts/memory_family_source_seal_v2.py:27`, `:217`). Emitted descriptors deduplicate by path with matching pins, positive reserves remain included, and original freeze bytes are separately added. The original freeze is not passed as an unsupported absolute-path sealer control.
- Named compatibility risk: namespace helper extraction might drop old-path holds/callbacks. Checked the omitted old `_bind_inputs` context (`scripts/qualify_memory_family_source_v2.py:450`); descriptor holds, runtime checks and namespace callback behavior remain intact.
- Named test risk: the new teardown fixture might exercise the wrong party. Traced the supplied harness diff and obtained exact definition/fault line numbers with a bounded symbol search; this produced the minor finding above.
- Inspected retained log summaries: `task-3-logs/final-five.log` reports **387 passed in 329.15s**. This is the production-final snapshot run, not a claim that the later strengthened boundary test was part of that run. `task-3-logs/boundary-real-bytes.log` separately reports **1 passed, 102 deselected in 3.99s** for the final actual-byte boundary test. No warnings appear in the inspected summary output. Reported red runs were read as historical implementer evidence, not independently rerun.
- **Reviewer executed no tests.** No runtime/native/model/raw/SNP/checkpoint/protected payloads, interpreter/site-package payloads, hashes or censuses were accessed. No service/API calls, broad tracked hashes, index/HEAD changes or implementation edits were made. Only this requested review artifact was written.

## Quality verdict

- **APPROVED with one minor coverage follow-up.** The changes preserve old-format behavior and finite interfaces while separating metadata checks from private custody and actual admission. No blocking correctness, scope or maintainability defect was identified. Whole-migration review should triage the parent-only close test gap together with the already deferred Task 2 recheck multiplier; Task 3 does not introduce that multiplier.
