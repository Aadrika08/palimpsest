# Bounded closure-assertion split review

**PASS — the proposed five-file amendment is ready for root's bounded implementation ruling, with the concrete shape and verification below.**

This review addresses only the newly measured mixed-test counterexample and the proposed preservation of its independent assertions. It does not reopen the 101-entry classification, review the uncommitted policy implementation, or approve Task 4 acceptance. Only this report was written; no tests, collection, imports, runtime/native/model operations, protected data reads, HEAD changes or sub-agents were used.

## Evidence and diagnosis

Read the actual retained log and exit record at `legacy-pin-policy-evidence/20261106T044123346083Z/early-active-cases/`: **1 failed, 53 passed in 21.23 s**, exit 1 (wrapper elapsed 21.60555666399887 s). The failure is precisely `tests/test_memory_case_publication_profile_v1.py:97`:

```python
assert generator.local_python_closure(ROOT,required)<=set(paths)
```

The log identifies one extra current dependency, `src/palimpsest/memory_transition_vnext.py`. Present `memory_decision.py` source imports that module at lines 387 and 420. This supports the current-code-versus-historical-roster diagnosis; no production refusal or historical pin defect is demonstrated. The generator describes and implements a static local-source closure, not runtime qualification.

The existing mixed function at lines 78-103 first reads three canonical profile documents, checks unique declared paths and required-root membership, then performs the live closure comparison. Its later output-cycle, sorted publication-pin and empty execution/qualification trust assertions were **not reached in this failed invocation**. The implementation report's statement that these assertions “stay active” can describe collection status only; it must not be interpreted as observed execution of the later assertions in this node. Other separate passing trust checks do not repair that distinction.

The reported 31 helper passes, 1,232 collected nodes and 236 passed/126 skipped original-four-file result are supplied implementation evidence, not executions performed by this reviewer.

## Required implementation shape

Use root's preferred unchanged-original-plus-active-counterpart approach. It preserves evidence custody and every original assertion with a small explicit duplication; moving the assertion or factoring the existing function is unnecessary for this bounded correction.

1. Preserve the entire existing `test_complete_declared_closure_excludes_output_cycles_and_real_trust` body and decorators unchanged, including the generator import and live closure assertion. Add only its exact existing function node to the case-publication historical group. The reviewed 99 strings become **100 strings**, with all previous ownership and exclusions unchanged. The same real-drift condition applies; no unconditional skip.
2. Append one clearly named active counterpart, for example `test_declared_profile_metadata_and_empty_real_trust_remain_active`. It must use the same `read(BASE)`, `read(CONDITION)`, `read(PUBLICATION)` calls, the same `paths` construction, the exact 12-member literal `required` set, the same five-member `excluded` set and the same assertion expressions listed below. No generator import or live closure assertion is needed in this new function.
3. Do not list that new counterpart in any historical group or add marks/fixtures that skip it, replace source identity, refresh pins or fabricate trust. It should run against the real unchanged profile JSON and live trust constants through the module's existing imports. A short docstring should state that this verifies declared metadata and empty trust despite current source drift; it does not establish completeness of the current import closure.
4. Extend ownership only to `tests/test_memory_case_publication_profile_v1.py`, in addition to the four already approved helper/conftest/helper-test/ADR files. Update count-dependent policy checks, the reviewed registry artifact and ADR/implementation explanation to 100 with a one-node amendment. Preserve the earlier 99-entry evidence rather than overwriting it.

The new active counterpart must retain all six independent assertion sites, including the loop over all three source lists:

```python
assert len(paths)==len(set(paths))
assert required<=set(paths)
for rows in (base['behavior_sources'],condition['source_pins'],pub['source_pins']):
    assert not excluded & {row['path'] for row in rows}
assert [r['path'] for r in pub['source_pins']]==sorted(set(r['path'] for r in pub['source_pins']))
assert execution.ACCEPTED_EXECUTION_AUDIT_SHA256==frozenset()
assert admission.TRUSTED_QUALIFICATION_PINS==()
```

Retain the original literal required paths rather than deriving them from the current generator or subtracting new dependencies. Retain `publication.EXECUTION_POLICY_PATH` and `publication.QUALIFICATION_POLICY_PATH` in `excluded`. The shared `read` helper's canonical-byte assertion also remains exercised for all three documents. Do not silently reduce the counterpart to only empty-trust assertions.

This fifth file is itself already in the frozen closure; appending the counterpart creates expected historical byte drift. No source or protocol pin may be updated to match it. The original historical function can execute again only when its selected group's real pins match; the new counterpart supplies present metadata/trust coverage, not a replacement claim of live closure completeness.

## Required verification after root authorizes the amendment

- Source/diff review must show the old mixed body is unchanged, exactly one historical registry string was added, and the new active body preserves the six assertion sites and canonical profile reads above. Production readers, generator, frozen JSON, trust roots and existing exclusions must remain unchanged. Do not broaden the new active function into current code traversal.
- Rerun the changed helper/history checks with the 100-entry expectation. The historical source proof must still use the real frozen bytes at an ancestor; the new test-file drift is expected, not grounds to repin.
- Repeat the focused real collection/marker audit in fresh evidence: **100 unique registry strings**, every exact ID exactly once, every base entry with descendants, original mixed node owned by the case-publication group and historically marked under current drift, new counterpart collected exactly once with **no skip/xfail or historical owner**, and all prior early/current-semantic exclusions retained. Explicitly verify the previous 99 strings and old group ownership unchanged. Update collection totals from observation, not arithmetic assumptions.
- Rerun the active early/profile wave with the new counterpart explicitly selected. The original mixed node may now report one historical skip when included; the new counterpart must execute and pass. Preserve the original 1F/53P evidence and report fresh pass/skip/error totals separately. Do not claim the historical live-closure assertion passed.
- The prior original-four-file **236 passed / 126 skipped** result may be retained as prior evidence if source/diff and refreshed collection audit establish that those four modules' code and selected-node ownership/markers remain unchanged. The added node belongs to a different module. Label the result as reused prior execution, not a post-amendment rerun. Any relevant implementation change or altered markers require reconsidering the affected check.
- Fresh independent code review remains necessary for the full uncommitted implementation, including this amendment. This source-only proposal review is not that review.

## Disposition

The new counterexample justifies a narrow amendment to the earlier expectation that this whole mixed function could remain active. Keeping all independent checks in a distinct active counterpart avoids the coverage loss that a bare whole-function historical skip would cause. No further mapping expansion is justified here. Root may authorize this exact five-file shape and bounded verification; actual source qualification, research/admission/GO authority, production acceptance and Task 4 acceptance are not granted by this PASS.
