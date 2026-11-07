Spec compliance: **FAIL**. Task quality: **CHANGES REQUIRED**.

Scope: Task 1 only, BASE `0de8cc1e7e47bb29c86a859080433fb371cf929f` to HEAD `7f3c783868f8c878426e9ee02b44c86a125353c6`, four-file supplied diff. Current root-owned plan clarifications are binding. No whole-branch or actual-source/GO verdict.

### Strengths

- `src/palimpsest/memory_decision.py:383` retains the original worker ordering behind strict public state3 admission. The fixed terminal builder is the only added worker mode; no public callback, alternate loader or state4-to-state3 admission was added. The missing explicit state3 assertion inside the private terminal=None worker is **not a blocking defect**: its documented validated-input precondition and strict public entry provide the relevant boundary.
- `src/palimpsest/memory_transition_vnext.py:321`, `:437` separate source-M geometry/gold resolution from the single ordinary live-M selector call, use the exact four stage commitments, and retain pending versus resolved-empty semantics. `tests/test_memory_transition_vnext.py:147` checks complete stage preimages rather than only stage names.
- `src/palimpsest/memory_transition_vnext.py:376`, `:392` separately deep-copy result projections and retain the same exception object plus independent immutable projection bytes. Aligned exception/Witness mutation cannot rewrite the captured projection.
- `tests/test_memory_transition_vnext.py:293`, `:524` exercise complete actual RunWriter bytes and the exact Engine envelope. The final retained log reports Witness 12,244 / Context 4,782 / Commit 793 bytes, with 95 passed in 17.15s and no warnings. I read that log; I did not rerun the 95-test suite.
- `docs/plans/memory-terminal-vnext-v1-protocol.json:1` remains explicitly proposed/unqualified, carries inherited metadata rather than new self-pins, and distinguishes syntax from later source custody and actual event authentication.

### Critical

- None found in the task scope.

### Important

1. **Idempotent admission bypasses lifecycle/chain coherence.** `src/palimpsest/memory_transition_vnext.py:503` returns before the expected-count check at `:512`. After a real authored first oracle selection, repeating the consumed packet with the selected proposed state but `chain=(0, sha(context))` returns `idempotent`; the same contradictory chain on the next packet correctly returns `rejected`. The plan requires the supplied state/Lifecycle and chain to agree, including selected implying count1. Move invariant chain/Lifecycle checks before the early return while retaining the no-second-call/no-new-witness behavior. Add both valid and contradictory same-packet chain cases. Evidence: `task-1-evidence/review-lifecycle-wire-probe-01.log:1-2`.

2. **Standalone Witness encoding accepts unconditional contradictions that transition admission rejects.** `src/palimpsest/memory_transition_vnext.py:554` enforces index1 implies selected, but not selected implies index1. An actual later selected-input Witness can be rewritten to index0/previous=Context and still encode successfully. The nested Reach checks at `:561` also omit the gate/intervention pair and gate-requires-cue invariants already enforced by `validate_reach_vnext` at `:300`; removing gate_event while retaining intervention_event still produces accepted complete event bytes. These are locally decidable schema/chain contradictions, not the deferred question of authenticating event bodies. Enforce the symmetric count/Lifecycle relation and reuse the context-independent Reach invariants in both validators; retain contextual kind/body checks for their proper later owner. Evidence: `task-1-evidence/review-lifecycle-wire-probe-01.log:3-5` (2,576-byte invalid-chain event, 3,797-byte unpaired-Ref event; the same Reach is refused by its public validator).

3. **A post-validation output cap failure is classified as a raised transition and receives a Witness.** `src/palimpsest/memory_transition_vnext.py:530` treats every ordinary-core exception other than `_Rejected`/partial-oracle execution as `raised`. A strict4-valid authored no-U/no-event state with `last_decisions=['x'*65520]` has a 65,524-byte decision list; the real next bridge append crosses the unchanged 65,536-byte legacy decision cap. The function returns `raised` with Witness.result=`raised` and `ValueError('Memory JSON exceeds byte limit')`, although the binding result contract explicitly requires cap/serialization refusal to be infrastructure `rejected` without a Witness. Preserve the legacy public exception semantics, but give the fixed terminal path an explicit validation/cap refusal category rather than relying on general Exception classification or message matching. Test this valid-input/output-over-cap boundary. This counterexample establishes syntactic refusal behavior only; it does not claim the authored decision history is authentic acquired source. Evidence: `task-1-evidence/review-cap-probe-01.log:1-5`.

### Minor

- No additional polish findings; the issues above are the required changes.

### Checks and limits

- Read the Task 1 brief, current plan wire/state/result/Task 1 requirements, implementer report, full supplied diff/new files, and raw `green-final-03.log`. Supplied diff output was segmented to avoid truncation; no git commands or broad checkout crawl were run.
- Named focused unchanged-code checks: `memory.py:29`, `:60`, `:90`, `:310` and `memory_task.py:36`, `:162` establish plain canonical input, size-error behavior, exact selection semantics, fixed hashed sensor IDs and selector limit1. These resolved suspected generated-ID/selector-bound risks; neither is a finding.
- Ran only two fresh inline authored-fixture probes with the approved isolated Python/environment (env -i, empty CUDA visibility, research opt-ins absent, numerical threads1, no bytecode). Each exited0 and retained its newly named log under the ignored Task 1 evidence directory. No pytest basetemp was needed because these were direct bounded Python probes, not pytest executions. No source/native/model/recording payloads, services, CI, publication, cleanup or code changes.
- Unverified cross-task dependencies remain intentionally outside Task 1: authentic source holder and geometry placement proof; complete actual Ref/event authentication and natural-cause eligibility; Engine fsync/assignment/commit/stop integration; terminal numeric replay; physical census and all actual adoption/qualification/GO gates. Their absence is not a Task 1 defect.

Assessment: **CHANGES REQUIRED** for the three reproducible admission/result-contract gaps above. The core one-execution transition, detachment and proposed bounds otherwise align with the reviewed task.

🟡 Review complete; fix lifecycle/wire consistency and output-cap classification before Task 1 approval.
