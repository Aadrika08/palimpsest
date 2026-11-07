# Independent historical-pin policy code review

**Spec: PASS. Code quality: APPROVED. No required changes.**

Reviewed exact base `65b6789cff2f08f1e2b33875a41432145b05c1e2` to commit `e620b345233bdb873d0ca48d4a2639fde1206e32` in `.worktrees/authority-paper-rewrite`. The commit changes exactly the five authorized files. Root's unstaged `docs/plans/memory-terminal-vnext-implementation.md` is excluded. No severity-ranked defect, reproduction or fix request remains.

This reviewer read the plan, authoritative reviewed-v2 registry, original classification and correction/closure-split reviews, final amended implementation report, source diff, retained command/environment/exit records, raw logs and collection/reuse metadata. `.codegraph/` is absent. Independent Python AST/JSON/source comparisons and `git diff --check` were performed; **no pytest, collection, helper import, production invocation, whole-suite rerun or behavioral probe was executed by this reviewer**. Only this report was written. No protected raw/SNP/model/native payload, service, dependency, CI, cleanup, HEAD movement or sub-agent action occurred. Billing quota is unknown. No working-set tools were available in this review context.

## Specification and mechanism

- `tests/frozen_pins.py:70-87` loads the actual case-publication base `behavior_sources` and condition/publication `source_pins`. The merge accepts equal duplicates and raises on conflicts; it contains no copied digests and does not use the older retained-condition loader. Existing loaders are unchanged.
- `tests/frozen_pins.py:125-229` matches the authoritative reviewed-v2 registry exactly: **100 unique strings, 81 function entries and 19 exact parameter entries**. Independent AST comparison with the base confirms all 129 old entries, owners and loader assignments unchanged. Comparing retained old and new collection registries confirms the previous 99 entries plus only the original mixed profile node. The five earlier overskip corrections remain preserved.
- `tests/frozen_pins.py:410-430` rejects duplicate ownership and same-function base/exact ambiguity, including within one group. Exact lookup precedes function fallback. `tests/conftest.py:7-12` marks only a resolved owner with real drift. There is no blanket skip, xfail, caught-refusal skip or production-guard patch.
- `tests/test_memory_case_publication_profile_v1.py:78-103` remains byte-for-byte within the original module prefix. The counterpart at lines 138-165 has no decorators or historical owner. Independent AST comparison proves that, excluding its explanatory docstring, it preserves the original body after removing only the generator import and live-closure assertion. It keeps all three canonical reads, the exact 12-member required literal, exact five-member excluded set, and six independent assertion sites, including iteration over all three source lists. It does not traverse the current closure or fabricate trust.
- The helper/conftest and appended profile-test file are historical byte pins. Their drift is expected; no pin was refreshed. Independent readback of the named profile, guard, trust, Engine and memory_decision bytes matches the base and retained baseline. The five-file commit excludes generator, production, frozen JSON, trust and admission changes. The retained source-guard script uses the real unpatched reader and records `Behavior source differs: engine`.
- `tests/test_frozen_pins.py:59-172` exercises the real collection hook with authored bytes: matching source has no skip; missing/changed source produces the explicit reason only on the owned node; cache state is cleared between states; equal/conflicting union, exact/fallback/unrelated lookup, sibling exclusion and duplicate/base-exact rejection are covered. Existing history checks remain, with a direct fixed-main-ancestor check added. The retained genuine RED logs precede GREEN; this is meaningful behavioral coverage, not solely assertions mirroring registry constants.

The ADR explicitly distinguishes registry strings, collected nodes, lost historical coverage and active metadata coverage. It discloses the initializer's lost later assertions and does not promote a skip or historical provenance proof to current qualification.

## Evidence reconciliation

Fresh evidence root: `legacy-pin-policy-evidence/20261106T045532915674Z-amendment/`. Prior root: `legacy-pin-policy-evidence/20261106T044123346083Z/`. Paths are relative to this SDD directory.

| Evidence | Verified retained result | Interpretation |
| --- | --- | --- |
| `amendment-mechanics-history-green` | 31 passed, 0 skipped, 0 failed/errors; 1.83 s; exit 0 | Mechanics and history execution by implementer |
| `amendment-collection` | 1,233 collected; 1.47 s; exit 0 | Collection only; no fixture execution |
| `amendment-early-profile` | 54 passed, 4 skipped, 0 failed/errors; 20.20 s; exit 0 | Active counterpart and early checks pass; four profile nodes historical |
| `amendment-source-guard-readback` | unchanged named bytes and real active-profile source refusal; exit 0 | Current source remains unqualified |
| Prior `task4-original-four` | 236 passed, 126 skipped, 0 failed/errors; 93.90 s; exit 0 | Explicitly reused prior execution, not a post-amendment rerun |

Independently compared every raw collection node line with `collection-audit.json`: all 1,233 identities match in order and are unique. All 100 registry strings resolve; each exact parameter resolves once; every function has descendants. Recomputed 307 new-group nodes and 716 related-module nodes without that group. New markers occur precisely on new-group owners. All 20 prior explicit exclusions are identical, present once, and have no skip/xfail. The counterpart appears once without owner/skip/xfail; the original mixed node has its intended historical marker. The retained execution selectors resolve to exactly 58 collected nodes: 54 active, four historical, no xfails. Combined with the zero-failure raw execution log this supports the counterpart PASS; the original live-closure assertion did not pass.

The command records use the approved `.venv/bin/python -B`, replaced sanitized environment, and distinct retained basetemps. Read the collection audit and source-readback harnesses: collection uses `--collect-only`, rejects accidental test setup, validates real item markers and refuses failed collection. The source readback does not patch the reader.

## Four-file reuse judgment

**Reuse is adequate for the approved bounded amendment.** Independently hashed all four current modules and compared them with the recorded pre-amendment bytes and base revision. Independently compared all 362 prior/fresh exact node IDs, owners, skip polarity and xfail polarity; they are unchanged. Full prior/fresh reason records match their corresponding collection records. Reason text is correctly different because the appended profile-test file now drifts; neither the report nor this review claims literal reason equality.

| Original file | Passed | Historical skips |
| --- | ---: | ---: |
| `test_memory_family_terminal_numeric_vnext.py` | 68 | 0 |
| `test_memory_family_numeric_preservation_v2.py` | 5 | 124 |
| `test_memory_family_compact_v4.py` | 40 | 2 |
| `test_memory_family_terminal_audit_vnext.py` | 123 | 0 |
| Total | 236 | 126 |

The amendment's helper patch is explicitly labelled as a reconstruction of the prior helper by removing the single added registry string; it is not an independent historical source snapshot. This does not invalidate the bounded reuse: that addition belongs to a different module, current helper behavior is independently reviewed, the four selected source modules and marker identities match, named production dependencies are unchanged, and changed helper/history behavior was freshly verified. No material doubt calls for expanding execution.

The 124 new and two prior historical skips are lost execution coverage. The codec's 68 tests and auditor's 123 tests remain active; their counts are not augmented by skipped legacy checks. The prior failed early wave is retained as **1 failed / 53 passed in 21.23 s**, with the exact new current dependency at the original closure assertion. Its later output-cycle/sorted-pin/empty-trust assertions were not reached in that invocation. The final report now states this correctly. The new counterpart supplies only its stated metadata/trust coverage.

## Disposition and limits

The five-file implementation satisfies the reviewed specification and is approved as authored test-policy work. No current source qualification, historical live-closure success, runtime/research acceptance, admission, GO or deletion authority follows. Root retains Task 4 overall acceptance and explicit final pass/skip accounting. No further implementation fix or test execution is requested by this review.

Memory was consulted only for the general requirement to recheck current evidence and preserve custody/qualification boundaries (`MEMORY.md:416-418`); all implementation judgments above come from current source and retained evidence.
