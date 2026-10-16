# Q4 guard implementation unit

Continue the active simulation-release goal. Implement the explicit prospective
q4 boundary-snapshot contract in `puck-cpu-guard-v4-prospective.md`; do not treat
it as equivalent to q1–q3 live callback semantics. No actual10 or installed
runtime invocation belongs to this unit. All seven release gates remain open.

Reach: bootstrap parser/startup/cache guard/diagnostics, fixed qualification
entry, new authored tests and existing worker/CPU/dependency regression tests.
Keep dependency schema and parent/auditor/observer admission strict and unchanged.

1. Preserve observed RED before source edits: entry-red01 (2 failed,7 passed,
   descriptor refusal) and guard-red01 (25 failed, descriptor refusal). The first
   custody assertion matched a temporary-path substring; tighten it to the exact
   custody error before accepting GREEN. Capture qualifier version before imports.
2. Implement only the q4 branch. Validate exact types/strings before lookups;
   bound allocation; retain strong object references and compare values with is.
   Capture one whitelist after first reconciliation; compare late state after
   diagnostics/completion and keep a final deadline. Preserve old branch semantics.
3. Run authored guard/entry tests, then scoped legacy regression. Independently
   review source and test reach, including late mutation and failure/closure.
4. After semantics pass, measure three real-worker samples at128/512/2048
   authored names, three light checks each, plus separate profiles. Setup/cleanup
   are outside timing. Compare to retained original evidence with changed-contract
   limits; no installed throughput or runtime qualification inference.
5. Publish source, raw bounded evidence and review in a draft PR; update the
   execution goal with the next concrete source/admission unit. Do not retry09.

Exact-type sampling cannot prove atomicity, concurrency safety or hostile-code
isolation; ABA and post-final-observation mutations remain outside the contract.
