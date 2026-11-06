# Preservation round 1 re-review

Spec: **PASS** for the bounded preservation prerequisite.
Quality: **APPROVED**. The sole P2 finding is resolved; no residual findings.

Scope: accepted P2 correction and direct regression review only. Read the fix
report and three fix logs, inspected the current dedicated test and source diff,
and compared them with the source/test content inspected in the original review.
HEAD remains `b7a967026d1261b20450024e271f7cfc790dfd17`.

`tests/test_source_failure_preservation_vnext.py:262-273` now uses an exact legacy
writer signature that immediately raises the local `LegacyWriterEntry` sentinel.
The test requires that specific exception from real default `Engine.open`.
Passing the new keyword would instead fail Python argument binding with TypeError,
so the assertion meaningfully proves keyword omission. No broad RuntimeError
catch can confuse an unrelated acquisition refusal with the sentinel.

The test no longer patches asset verification or preparation to success. Its only
patch is the writer entry callable; the imported fixture's acquisition denials
remain intact. Empty trace/environments and absent recording output additionally
assert that the sentinel stops before allocation and recording output. This
establishes the required handoff without claiming complete legacy startup.

The only other dedicated-test change is removal of its unused `assets` import.
No collateral test changes were observed. The canonical preservation test and
its real authored resolver/held/world guards remain unchanged. The three-source
diff is unchanged from the originally approved preservation implementation.

Inspected retained evidence, without rerunning tests:

- `source-preservation-fix1-node.log`: **1 passed in 0.19s**.
- `source-preservation-fix1-file.log`: **63 passed in 0.64s**.
- `source-preservation-fix1-diff-check.log`: `git diff --check exit=0`.

The previous 119-test covering result remains historical evidence for unchanged
production code; it was not rerun. Original review/logs remain separate, and the
implementation report appends the correction and narrows the legacy-test claim.
No source admission, actual source execution, filesystem crash durability,
experiment readiness, CPU-provider qualification or scientific result is claimed.

This review performed no tests/imports/runtime work, protected payload access,
git mutation or delegation. This new report is the only review write.
