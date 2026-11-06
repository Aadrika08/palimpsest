# Historical-pin proposal correction rereview

**PASS — the five requested proposal corrections and bounded verification plan are ready for implementation.**

This is a source/metadata-only rereview of the five findings in `legacy-pin-policy-review.md`, not a second classification of all 101 original entries. Inputs read: the retained original registry, `legacy-pin-diagnosis/proposed-node-registry-reviewed-v1.json`, and `legacy-pin-policy-plan.md`. No test or collection execution, repository imports, runtime/model/native work, protected data reads, HEAD operation, policy/source edit or sub-agent activity occurred. Only this report was written. Root supplied current HEAD `65b6789`; it was not independently queried here.

## Corrections verified

A structural JSON comparison returned exactly 101 original entries, 99 revised entries and 99 unique revised entries. The entire set difference consists of the five removals and three additions below; unchanged entries were not reclassified.

| Required correction | Observed revised proposal | Result |
| --- | --- | --- |
| Keep qualification `test_duplicate_output_is_not_a_new_attempt` active | Removed | PASS |
| Keep qualification `test_closure_final_recheck_prevents_export` active | Removed | PASS |
| Keep qualification `test_parent_keeps_venv_alias_and_independent_audit_command` active | Removed | PASS |
| Keep qualification `test_parent_records_and_passes_inherited_cpu_clamp` active | Removed | PASS |
| Refine raw `test_rejects_size_caps_before_hashing_oversized_file` | Function entry removed; exact `[recording]`, `[events]`, `[report]` added; `[snapshot]` absent | PASS |

No other node was added or removed. Ninety-nine registry strings are not ninety-nine collected tests. The original 101-entry proposal remains a separate retained input.

## Verification plan judgment

The companion plan addresses the previous review's required boundaries:

- Four-file ownership: `tests/frozen_pins.py`, `tests/conftest.py`, `tests/test_frozen_pins.py`, and the accepted ADR only; original test assertions and production/frozen JSON/qualification sources remain unchanged.
- Distinct case-publication pin union from actual protocol documents, equal-duplicate handling, conflict rejection, preserved old registry ownership and expected self-pin drift without repinning to green.
- Exact node lookup before function fallback; duplicate and base/exact ambiguity rejection; real drift required for a historical marker; cache isolation in helper mechanics.
- Real source-history verification and focused collection, with exact-ID existence/uniqueness, base descendants and retained marker audit for all exclusion siblings, four removed qualification functions, raw snapshot/run_id/symlink and authored current semantics.
- Execution of the explicitly still-active early cases and unpatched source refusal, then the originally approved four-file Task 4 suite, each with fresh retained evidence/basetemp and separate pass/skip/error accounting. Later source-seal/runtime/qualification candidates remain collection-only/historical in this plan.
- No expansion into a whole suite, actual research/runtime/model/native services, protected evidence, dependencies, cleanup or CI. Unknown dynamic dependencies must be reported before scope expansion. A fresh implementation review remains required.

The three launch/accounting tests among the four removed qualification functions can invoke an authored independent audit that refuses historical source drift; this is part of their preserved authored-test behavior, not actual runtime qualification. Keep their exact assertions intact. The closure-final-recheck case remains an early refusal before audit launch.

## Disposition

No remaining blocker from these five proposal findings prevents the fresh builder from implementing this specific four-file plan using the revised 99-entry registry. This PASS is proposal readiness only. It is not a claim that helper tests, collected IDs, active early cases or the combined suite have passed. Implementation, recorded verification and independent code review remain outstanding; Task 4 acceptance and every actual qualification/admission/research gate remain open or closed exactly as the root's plan specifies. No source assertion or actual-source refusal is waived.
