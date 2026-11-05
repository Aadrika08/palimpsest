# Task 2 independent spec and quality review

Reviewed target: `8ba2c052419a8cd999f299e4e37c96ac7d8268b3..9e65300b7e0f75425e001f8c623af5c987b392c2`.

Scope: new `scripts/memory_family_source_seal_v2.py`, its authored tests, and the new V2 protocol source-publication additions. Requirements include the root's `additional_controls=()` plan amendment and the SDD ledger rulings. Task 1 was already reviewed; reused helper contracts were inspected only where necessary to assess this wrapper. No implementation, test, protocol, legacy, pin or plan files were edited by this reviewer. The plan amendment was outside the reviewed implementation commit; it subsequently became root commit `24ccccf2` while this review was active.

## Verdict

Spec compliance: **changes requested**. Quality: **changes requested**. One supported P2 custody defect remains in the marker publication boundary. No supported P1 finding.

### P2: retain a mutation witness for the prepared marker across rename

Location: `scripts/memory_family_source_seal_v2.py:159-161`, `:423`, `:434-441` (primary finding range `:423-436`).

`_tree(..., preparing=True)` intentionally opens `.commit.tmp` without retaining the file witness. The writer then records only `_edge()` (`st_dev`, `st_ino`, `st_mode`) and compares that tuple after the rename. Consequently an in-place marker change followed by restoration during `_rename_noreplace` preserves that tuple, and the later `_tree` takes its first retained marker witness only after the intervening mutation. Current-byte equality does not detect the lost custody interval.

An independent small authored probe performed the real marker rename, appended bytes to `commit.json`, then restored its exact original bytes before returning from the hook. The marker's mtime and ctime both changed, with the same inode. `seal_numeric_source_v2` returned `preserved-awaiting-lifetime-reconciliation` and no quarantine was written. This contradicts the Task 2 change-and-restore requirement and the report's claim that complete candidate file witnesses span publication. It is distinct from the explicitly authorized later-reader proof of current bytes after `SealIndeterminate`: this is the writer returning without detecting its own custody failure.

Retained authored observation: `runs/memory-numeric-v2-task2/review-marker-witness-r64135ya/review-observation.txt`. The preceding relative-path probe directory `review-marker-witness-bkm0tztn` is retained but has no observation and is not evidence for the finding.

Fix at this boundary: keep an open prepared-marker descriptor through rename and verify its identity, bytes and rename-safe mutation metadata against its pre-rename witness (including mtime; legitimate rename can change ctime). Ensure the post-rename name still resolves to that descriptor, preserve teardown failure handling, and add a regression that changes and restores the marker during the real rename. The regression must refuse the writer result and quarantine retained output, or raise `SealIndeterminate` if quarantine cannot be made durable.

## Reviewed strengths and limits

- Bounded canonical development/V3 registration and protected control descriptors are checked before legacy case construction or their payload opens. The public path consumes the closed V4 export and current independent raw audit without requiring a prior qualified/V1 seal.
- Raw, source owner, SNP, controls, registration and supplied extras remain bound; original SNP reference and event prefix are compared to the held SNP. Actual disk bundle bytes undergo all-row unchanged-base plus three-field numeric proof.
- Fresh `numeric-v2/<case>/<run>` output, exact recursive membership, exclusive durable writes, candidate companion witnesses across rename, late teardown refusal and quarantine/indeterminate handling are explicit. The marker witness exception above is the remaining supported gap.
- Accounting deduplicates physical paths rather than content hashes. Worker support is conservatively charged in overhead while counted once physically in raw; SNP stays at its sole original path. Conversion/commit/quarantine/future-terminal/atomic reserves are positive and bounded. Registered extras are sorted, exact, held, conversion-bound and required on reread. Combined overhead and recording limits include known metadata and reserves.
- `stage_peak_accounted=false`, provisional source status, `actual_source_qualified=false`, `publication_outcome_verified=false` and `independent_finalization_required=true` preserve the intended authority limits. Task 3 still owns complete parent census, the future terminal cap, enclosing 640 MiB proof, lifetime reconciliation and actual qualification. No public condition/zero/retained fallback or pruning grant was added.

## Evidence and verification

Inspected the final exact-snapshot log: **234 passed** (105 public source + 129 codec), exit 0, 177.69 seconds pytest / 178.00 seconds measured wall. This was the implementer's run; this reviewer did not rerun that suite. The separate 235 passed / 58 skipped legacy run is historical coverage, not a final whole-suite result.

Independently reran `sha256sum -c runs/memory-numeric-v2-task2/final-reviewed-snapshot.sha256`: all three owned files matched. `git diff --check 8ba2c05 9e65300b7e0f75425e001f8c623af5c987b392c2` passed. Exact target changes contain only the three owned paths; Task 1 and the inspected unchanged V1 codec/producer/raw-audit files have no target diff.

The only new execution was the bounded authored marker probe above; it ran successfully and reproduced the finding. No actual model/raw/SNP/protected data, native owner, research invocation, destructive operation, trust pin, commit or push was performed by this reviewer.
