# Memory family v3 raw oracle admission verification

8 October 2026. Implementation commit `a469dc0`, stacked on the pure oracle at
`e100275`. This report covers software-only admission of one explicitly named
source/`own` recording pair. It does not report a native run or a scientific
result.

## Result

`scripts/memory_family_oracle_admission_v3.py` now admits one exact pair only.
It verifies the independent case and hash inputs, strict terminal manifests and
reports, complete event/chunk recordings, registered snapshots and durable event
prefixes, restore lineage, full neural policy-call bindings, and the existing
recorded-history bundle. It derives every oracle binding from the admitted bytes,
then invokes and revalidates `memory_family_oracle_v3` and exposes its result only
through the oracle selector resource.

The implementation never scans for a donor and never reads an outcome to choose
one. It accepts no owner, attempt or cleanup assertion because version-3 producer
registration and receipt schemas do not exist yet. The admission envelope frozen
in the plan is the minimum contract that the later producer must emit.

The shared snapshot reader now uses the repository's strict JSON decoder for
`metadata.json`, so duplicate keys and nonfinite constants are rejected before
typed snapshot decoding.

## Review corrections

Independent plan review first found that the proposed owner proof would have
been self-consistent rather than independently registered. The plan was narrowed
to byte admission, strict snapshot metadata was added, and hostile concurrent
pathname replacement was left behind an explicit future immutable-close gate.
The revised plan had no remaining critical or important finding.

Independent code review then reproduced a mixed-generation admission: an event
file could change after decoding but before the old baseline fingerprint. The
oracle would evaluate stale decoded events while recording hashes came from the
new bytes. Fingerprints now precede every metadata/report/snapshot read and are
checked after decoding and again before return. Mutation tests cover the event,
report and snapshot gaps.

The same review found two identity gaps. Terminal manifest world state is now
validated and must equal the worker report, and every non-chunk event must carry
the admitted run ID. Recorder chunk events may omit it, but any supplied chunk
run ID must also match. Final targeted rereview found no remaining critical or
important issue.

## Verification

- Focused adapter plus strict snapshot decoder: 16 passed in 3.54 seconds.
- Independent adapter plus pure-oracle review run: 20 passed in 68.09 seconds.
- Affected memory, snapshot, artifact and replay slice: 139 passed, 7 skipped,
  4 deselected in 89.62 seconds.
- Python compilation and `git diff --check` passed.

The first broad invocation did not deselect `FlynnContinuation`: 134 tests passed
and 7 skipped, while its four setup cases errored before execution because the
optional upstream `core` fixture is absent in this worktree. The clean affected
run excluded only that class. This is an environment/input absence, not a claim
that those four cases passed.

## Evidence boundary

All raw pairs in tests are synthetic temporary `RunWriter` recordings. No Engine,
FLYNN model, native owner, development block, held-out block or physical rover
ran. The adapter detects ordinary read-time drift with stat fingerprints; it
does not defeat a hostile same-user process that can replace or mutate paths
between every reopen. Study evidence therefore still requires a version-3
producer with registered slots, owner/cleanup receipts and an immutable close.

Historical namespace inventory, finite storage/time allocation, matrix
completeness, frozen margins/estimator/stop rules and development inference also
remain open. CI was excluded by instruction. `main` was not changed.

Machine-readable hashes and commands are retained in
[`memory-family-oracle-admission-v3-evidence/verification.json`](memory-family-oracle-admission-v3-evidence/verification.json).
