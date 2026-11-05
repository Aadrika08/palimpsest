# Final whole-branch code and architecture review

**Verdict: APPROVED for the scoped software implementation. No supported Critical, Important or Minor code finding remains.** This is not actual preservation, runtime/lifetime qualification, scientific acceptance, or execution authorization. The exact-head full canonical suite is still pending in the root's concurrent verification at the time of this report; landing must consume that result separately.

## Identity, scope and method

- Base: `530ffe6d3e43b33e425dfa41a9e491e1df09afc9`.
- Head, verified at start and completion: `53ab035f6e0082dd3430490067cb6b0ac4c8dc5a`.
- Retained review package: `.superpowers/sdd/memory-numeric-preservation-v2-implementation/review-530ffe6..53ab035.diff`; SHA256 `15a7f2330bdbcbe6694d348b763041d642b100f6276be4b133637a43c070bf6b`.
- Reviewed all four new production modules, the four authored test modules' coverage and relevant implementations, the numeric implementation and source-preservation requirements, source runtime plan, prospective case/cell and oracle/order designs, progress integration, and prior task/fix review dispositions. Read unchanged codec/producer, storage/engine and pilot interfaces where necessary to assess integration. Large retained logs and historical research evidence were not treated as current feature test results or new scientific evidence.
- Review was independent and read-only except for this requested ignored report. No source/test/protocol/index/HEAD mutation, subagents, native owner, model/protected/retained raw/SNP reads, research execution, pruning, deletion, commit or push. No old tests were rerun; root owns the fresh complete suite on the frozen head. No `.codegraph/` directory was present in this worktree. No working-set MCP binding was exposed to this reviewer.

## Strengths

1. **The composite codec preserves the immutable base contract and closes the missing numeric channel gap explicitly.** `scripts/memory_family_numeric_preservation_v2.py:119` first reads the unchanged base; `:225` requires the V2 envelope and exact companion/file bijection; `:269` ties each companion to the original partition descriptor; and `:300` runs the unchanged producer proof before comparing every additional scalar/matrix by dtype, shape and bytes at its actual tick. Signed zero is retained. Strict finite little-endian float64 and `(3,4)` population eligibility are enforced at `:86` without coercion. Bounded NPY dimensions and canonical NPZ reserialization at `:159` reject malformed/unbounded companion representations before accepting them. There is no V1 fallback after V2 refusal.

2. **Public source conversion uses the same retained raw and sole SNP without an extra owner or public V1 seal.** `scripts/memory_family_source_seal_v2.py:349` holds the existing closed V4 registration and original control/raw/SNP descriptors, rejects nondevelopment metadata before case construction, independently revalidates the public raw-audit receipt, and decodes the held nonempty source. `:412` creates only the derived fresh numeric candidate. `:312` additionally binds the candidate snapshot reference and event prefix to the held original SNP. The reader at `:505` repeats raw-backed proof and exact records/namespace checks, so rehashed timing/population corruption does not become trusted merely by updating candidate descriptors.

3. **Accounting is explicit about both coverage and limits.** The codec's ledger at `memory_family_numeric_preservation_v2.py:209` computes actual serialized bundle overhead. `memory_family_source_seal_v2.py:217` deduplicates identical physical paths, not equal hashes; `:236` includes registered/additional support controls and fixed positive conversion/marker/quarantine/terminal/atomic reserves in the same 1 MiB envelope. Raw 512 MiB and the one SNP 16 MiB stay separate. `qualify_memory_family_source_v2.py:686` supplies the complete parent control prefix, retaining creation-time pins for already validated authority and using ancillary files only for accounting. `:858` checks the preconversion output roster; `:873` checks the complete final roster and bounded tail against 640 MiB including 64 MiB headroom. Both public and parent results retain `stage_peak_accounted:false`; a closed census is not called an observed lifetime peak.

4. **Publication and parent finalization compose defensively.** The public writer holds candidate descriptors across marker rename and rereads disk bytes before and after publication. The repaired pre-rename marker witness at `memory_family_source_seal_v2.py:184`, invoked at `:445` and `:463`, retains identity, bytes, size, mtime and link-count through the deliberate rename. Late errors quarantine retained bytes or raise `SealIndeterminate` if durable outcome recording is unavailable. Parent `qualify_memory_family_source_v2.py:867` never follows a failed writer with a reader; `:905` and `:909` stop/quarantine on later failures and teardown; `:931` enforces terminal bounds and actual postwrite output census; `:592` catches writer-lease exit failure. Duplicate-output refusal cannot quarantine a previous attempt because the outer handler requires this attempt to have created the output.

5. **Owner admission and result authority remain bounded.** `memory_family_source_runtime_v2.py:98` admits only the fixed development tuple, canonical UUID, exact paths/limits and immutable roster. The adapter uses the fixed `Engine.open`, CPU FLYNN, acquired paused boundary, one separately stored SNP and existing instrumentation (`:290`). Failed close/final checks prevent a successful owner outcome even if a late worker report remains (`:356`). The parent requires successful closed/drained accounting before audit, then independently invokes the existing auditor (`qualify_memory_family_source_v2.py:244`, `:749`, `:795`, `:827`). V3 freeze/preparation/result schemas avoid reinterpreting earlier V2 preparation semantics, while owner V2 and export V4 remain unchanged. Actual metadata/profile bytes are checked and held (`:137`, `:592`). Real execution remains closed (`:221`, `:466`, `:529`), and all provisional results deny actual source, lifetime and scientific qualification.

6. **Authored tests exercise the public contract and the risky cross-task seams.** Numeric tests cover rehashed numeric tampering, signed zero, row/column permutation, partial and maximum partitions, malformed NPZ, exact/one-byte-over accounting and allocation-safe NPY rejection. Public tests use unchanged raw audit, actual writer/rereader and disk corruption, with change-and-restore, aliases, occupied paths, partial writes, deadlines, teardown, marker/quarantine and added-control cases. Parent tests explicitly observe both real public calls and full numeric values, control census, one SNP/no old public marker, terminal caps, postwrite drift, indeterminate writer nonresumption, lease teardown and actual controlled-HOME bootstrap (`tests/test_memory_family_source_qualification_v2.py:565`). These are meaningful authored software checks, with explicit assertions against qualification claims.

## Issues

### Critical (must fix)

None supported by the reviewed branch.

### Important (should fix)

None supported by the reviewed branch.

### Minor (nice to have)

None filed. The retained hosted raw log contains trailing whitespace, but changing those evidence bytes for formatting would be inappropriate; this is recorded below rather than proposed as cleanup.

## Verification and evidence limits

- Verified unchanged `src/`, V1 codec, V4 producer/raw auditor and original compact protocol against the stated base using `git diff --quiet`; exit 0. The branch adds the new feature modules without altering those legacy acceptance paths or trust pins.
- `git diff --check BASE HEAD -- scripts tests docs/plans docs/progress.md` passes. Whole-range `git diff --check` reports trailing whitespace in the retained `docs/reports/main-foundation-delivery-2026-11-06/hosted-success-42087513935.log`; it is not an all-files whitespace pass.
- Reviewed task reports and prior independent reviews, which record final Task 2 coverage of 236 passed and final Task 3 coverage of 116 passed, with earlier unchanged-component coverage of 453 passed / 58 skipped. These are retained prior results, not tests run by this reviewer and not a fresh whole-branch pass.
- Root's complete canonical suite on `53ab035` is pending in this review snapshot. The previous hosted/main evidence concerns a different tree and cannot satisfy this new branch's complete test gate. No current CI, current hosted branch publication, real preservation feasibility or research success is inferred.
- No code changes were needed during this review, and tracked state remained clean. The report is the only reviewer-authored file.

## Behaviors considered and declined to judge

- Actual model/native/runtime package completeness, pre-import/exec isolation, namespace-only export authority and independent complete-parent lifetime acceptance: outside this software scope and explicitly unimplemented/blocked; fixtures and metadata do not establish them.
- Actual numerical/source preservation on collected data and real 32 MiB serialized feasibility: no actual data read or acquisition authorized for this review; the public path retains oversize refusal and scoped claims.
- Zero/early terminal conditions, public condition sealing, case-bound neural qualification, trusted pins, final retained-case readers and whole-study completeness: prospective follow-on interfaces; the implemented public source domain is explicitly nonempty and does not claim those capabilities.
- Adoption or scientific validity of the oracle-resource and owner-order proposals: design documents explicitly remain unadopted; current prior-own/analysis contracts are unchanged. No empirical result or all-nine completeness follows from those proposals.
- Historical single-archive “19 members” design wording: the later numeric implementation plan explicitly and prospectively supersedes that physical layout with unchanged 16 plus mandatory 3 companions; no hidden deviation or missing semantic field found.
- Reader recovery after all writer failure-recording writes are unavailable: reviewed as an intentionally limited current-byte proof, not a successful writer outcome. `publication_outcome_verified:false` and `independent_finalization_required:true` stay explicit, and the parent never resumes an indeterminate writer via a reader.
- Exact resource/CPU/lease-release/process-return tail acceptance: explicitly delegated to a required external lifetime mechanism and denied in current result flags. No claim of hard aggregate lifetime accounting is made by sampled containment or observed phase CPU.
- A stronger adversarial filesystem model that restores payload plus mutable timestamps, or modifies bytes after final held-descriptor teardown: not treated as a proven immutable runtime. Current APIs supply scoped custody/current-byte proof; immutable namespace and whole-lifetime external acceptance remain required actual-execution gates.
- Generic architectural refactoring of shared private V1 helpers: reuse is narrowly mechanical and tested; a registry/loader abstraction would add scope without fixing a supported bug.
- Reformatting retained hosted logs or replaying their historical runtime probes: evidence preservation takes priority, and neither operation is needed to review current source integration.

## Recommendations and merge assessment

**Ready to merge? Yes, from code/architecture review, after the separately running exact-head canonical checks pass.** No implementation fixes are requested. Attach the final exact-SHA verification result to the root's delivery record and keep the actual-execution blockers and provisional scope intact.

The branch composes the owner, independent raw audit, strict numeric codec, public raw-backed source writer/reader and parent accounting/finalization without bypassing unchanged contracts or promoting software evidence into actual qualification. This approval completes this whole-branch review unit only; it does not close the larger project, authorize research execution, or approve pruning.
