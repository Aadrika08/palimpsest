# Task 1 fix round 1 independent rereview

**Spec: PASS for the two reviewed corrections. Code: APPROVED for this fix diff.** Both original Important findings are **ADDRESSED**. No new Critical, Important, or Minor defect was identified in the narrow fix diff.

Reviewed HEAD: `00e9ae33b10db8ca603abeeb758b20a2d9ac5e2c`. Fix base: `a2b8c4451d3aced2e6f980ebe55d4f098a876d77`. Read the supplied `review-a2b8c44..00e9ae3.diff`, the appended fix-round report, and the actual Git diff; the production delta is exactly one deleted call and two added guard lines. The two owned files match HEAD. This is a scoped rereview of the prior findings and possible breakage introduced by their fixes, not a fresh broad review.

## Finding dispositions

1. **Wrong RuntimeReference serialized ceiling — ADDRESSED.** The call applying the cumulative-charge 8192-byte encoding ceiling is removed from `validate_runtime_reference` (current lines 215–226). Exact reference fields, fixed profile/schema values, bounded descriptor integers/digests, canonical bounded paths, structural bounds and metadata-disjointness checks remain. Those constraints give the reference a finite size without inventing a new serialization ceiling. Neither PROFILE nor `_charge` changed; cumulative-charge references retain their specified 8192-byte ceiling. Added tests at `tests/test_memory_source_runtime_closure_v1.py:437` cover three exact 4096-byte paths, ordinary and quote-rich forms, canonical JSON above 8192 and 16384 bytes respectively, 4097-byte refusal, and normalized-copy independence. This resolves the original valid-input false refusal without weakening the declared path/schema bounds.

2. **Handle accounting absent-prior bypass — ADDRESSED.** `RuntimeHandle.accounting` now requires exact dictionary arguments inside its existing poisoning `try` at `scripts/memory_source_runtime_closure_v1.py:707–708`. `(None, None)`, either missing binding, and non-dictionary inputs therefore refuse and enter the normal poison/release path. Valid dictionary arguments still pass through the existing prior identity/float/allocation checks and before/after rechecks. The pure ledger validator's documented child-side both-absent behavior is untouched. Added tests at test-file line 462 exercise refusal, unusable subsequent summary/recheck, refusal of successful context exit, and return to the prior FD count. The separate child-mode regression at line 475 preserves that intended API distinction.

## Evidence inspected

- Retained red log `runs/runtime-reference-task1/fix1-red-qsLU7V/pytest.log`: **3 failed, 43 passed in 17.02s**. Its final summary names both long-path regressions and the handle `(None, None)` regression.
- Retained green log `runs/runtime-reference-task1/fix1-green-hN8UWw/pytest.log`: **46 passed in 18.37s**.
- Read-only `git diff a2b8c44..00e9ae3 --` for the two owned source/test files agrees with the supplied package. `git diff --exit-code HEAD --` for those files succeeded.

These are inspected implementation-run logs, not tests independently rerun during this review. No new probe or old/full-suite run was necessary for the three-line production change. The earlier report remains the record of the broader review; this report resolves its two requested changes.

## Scope and limits

The original unqualified accounting/execution/source/runtime flags and all stated feasibility, artifact chronology, actual B-adoption, external accounting/lifetime, loader and scientific limits remain. Approval concerns the authored current-byte prototype and its contract corrections only. It grants no actual execution or adoption authority.

No source/index/HEAD/remote mutation, subagent, native/service/network action, runtime/model/raw/SNP/checkpoint/catalog payload read/hash/import, broad hashing, cleanup, or operational probe occurred. Root-owned untracked lifetime documentation was untouched. Only this ignored review report was written.
