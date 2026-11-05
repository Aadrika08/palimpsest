# Task 2 review

## Spec Compliance

- **Spec compliant for the Task 2 slice reviewed.** Base `eebd51a`, head `f00dc47`; the supplied package contains precisely the two owner files plus the approved pure-helper wrapper/test amendment. No blocking missing, extra or misunderstood Task 2 requirement found.
- **Cannot verify from this diff:** Task 3 V4 freeze/job root equality, independently held parent custody and parent/child agreement, original parent deadline provenance, combined 1 MiB accounting of all copies, and final parent handling of a propagated teardown failure. These are cross-task requirements; Task 3 is not implemented yet. This verdict does not establish them.
- **Cannot verify from this diff:** actual runtime/preparation/lifetime/accounting qualification or resource fit. Public execution remains refused and no actual profile adoption, authority backend or GO is established (`scripts/memory_family_source_runtime_v2.py:529–534`).

## Strengths

- V2 validation stays on its original inline-closure branch, retains positive-size descriptors and the admission-excluded 256 KiB hash rule; V3 adds separate exact immutable requirements and a complete admitted-size check (`scripts/memory_family_source_runtime_v2.py:70–77`, `:101–178`). The ordinary source case, identity, assets/output disjointness and limits remain enforced (`:180–202`). Existing V2 tests/fixtures are not rewritten by the diff.
- Independent metadata is parsed once through a shared owner parser: sorted nonoverlapping roots, five pure validated pins, lexical config location, contradictory-repeat rejection and independent returned collections (`scripts/memory_family_source_runtime_v2.py:101–123`). The helper addition is only the specified pure wrapper (`scripts/memory_source_runtime_closure_v1.py:257–259`).
- V3 template validation takes the metadata-only branch and public execution refuses before layout, holder, storage, loader or output operations (`scripts/memory_family_source_runtime_v2.py:126–164`, `:206–211`, `:529–534`). Added fail-on-call tests cover payload open, holder construction and loader paths.
- Admission binds manifest/profile digests, finite non-bool deadlines, source <= runtime, 360-second source and 900-second enclosing bounds; the child passes the original absolute runtime deadline to its own handle and checks the tighter source deadline throughout custody and teardown (`scripts/memory_family_source_runtime_v2.py:214–246`, `:487–526`).
- Live layout checks require all five full-prefix obligations and all six named source helpers, plus the executing alias and ELF. No fresh source hash becomes an expected pin. The active handle is used through reports/final checks, and the zero-argument loader factory is called only after successful layout/custody/descriptor checks (`scripts/memory_family_source_runtime_v2.py:465–525`).
- Outcome/failure versions are chosen before core work and before the first exclusive failure write; the V2 field structure remains unchanged. Close failures propagate out of the context instead of returning a recorded outcome, and existing failure artifacts are not rewritten (`scripts/memory_family_source_runtime_v2.py:351–360`, `:450–462`, `:522–527`). Added authored tests check both versions, canonical failure bytes, held callbacks, loader arguments, source/helper omissions, deadline exhaustion and close/drift failures.

## Issues

### Critical

- None found.

### Important

- None found.

### Minor

- **Repeated complete-runtime rechecks for immutable pin lookups.** `scripts/memory_family_source_runtime_v2.py:509–518` performs one explicit `held.recheck()` and then `held.descriptor()` for each of three scalar descriptors plus every required source. The real accessor performs two further complete rechecks per lookup (`scripts/memory_source_runtime_closure_v1.py:668–687`). Thus each identity callback performs `1 + 2*(3 + N)` full holder rechecks: 19 for the six required sources, up to 135 for 64 sources, including redundant owner pins. The new authored fake performs only one recheck per accessor, so its event assertions do not expose this exact multiplier. This is a static cost/maintainability concern, not measured resource failure or an authority defect. Consider checking immutable descriptor equality once after entry, relying on subsequent full handle rechecks to preserve that already-established equality, while retaining every required lifecycle check. Do not weaken holder semantics or change Task 1 custody policy to address it.

## Exact checks and evidence

- Read the Task 2 brief, binding amendment, implementation report and supplied `review-eebd51a..f00dc47.diff`. Read the 910-line diff once in consecutive ranges; no Git commands were rerun.
- Read `.superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/final.log`: progress output followed by **149 passed in 38.72s**, with no warnings shown. This is retained implementer evidence, not a reviewer rerun or CI assertion.
- Named cutoff/compatibility check: the diff omits the middle of metadata validation and core execution. Read owner lines 50–100, 180–215, 260–345 and 350–465 to establish that hash semantics, output disjointness, exclusive writes, existing-output refusal, engine close, final identity checks and failure emission remain intact. The extra context resolved these risks without expanding into other features.
- Named accessor-contract check: new repeated `descriptor()` calls could multiply full-runtime work or outlive custody. Located and read only helper entry/recheck/descriptor/exit at lines 641–699 and 724–742. The methods enforce active custody and final release, but confirm the minor multiplier above. Entry independently validates the expected pins before acquiring runtime records.
- Confirmed this worktree has no `.codegraph/` directory; CodeGraph was therefore not used. No working-set MCP binding was exposed in the available tool list.
- No tests, imports, authored probes, native/model/raw/SNP reads, installed-runtime census/hashing, broad tracked hashing, branch/index changes or source edits were performed. Only this requested ignored review report was written.

## Assessment

**Task quality: Approved, with the minor cost observation above.**

The bounded source change preserves the public refusal and V2 behavior while making the private V3 custody/deadline/schema path explicit and well tested with authored fixtures. This is a Task 2 software review only; the outstanding parent integration and actual execution qualification remain separate and unverified.
