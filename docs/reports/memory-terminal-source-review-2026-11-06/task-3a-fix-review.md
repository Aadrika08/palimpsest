# Task3a round1 fix rereview

**Scoped spec: PASS. Quality: APPROVED. Actual acceptance: false.**

Reviewed `b5f667b8e3bf03e2d82d9e7d8f085fb74549ff55` → `6cc0e8ef8ae2b9afc932b8e408d194f9ed67ea7e`, with current HEAD verified at the latter. This is the F1–F3 rereview requested after `task-3a-review.md`, limited to the two owned auditor/test files and material regressions introduced by their fix diff. No unrelated predecessor paths were reopened. All three original findings are resolved; no new material issue was found in the changed code.

## Findings resolved

- **F1, complete supplied source event ceiling:** `_source` now encodes each supplied source event using the unchanged deterministic writer, adds its byte length to the complete-stream total, and refuses above **7,340,032 bytes**. It separately hashes and counts only the declared acquired prefix and verifies that commitment. The complete event list still reaches the source evidence replay unchanged; no suffix is silently removed. The byte refusal precedes `_audit_rows` and `_source_evidence` (the earlier cheap decoded-row type/count/lower-bound checks remain). The new tests accept an exact-ceiling stream and reject a valid acquired prefix plus a suffix making the stream exactly one byte over. The RED log shows the over-cap input reached the source-replay spy before the fix, establishing the intended failure boundary.
- **F2, exact terminal event payloads:** after the unchanged full legacy normal-terminal guard, the auditor obtains the sole `episode_finished` event and requires canonical exact equality of its outcome and metrics with the validated manifest. This closes Python's boolean/integer/float equivalence hole without weakening normal outcome, cap, phase, ordering, or metric checks. Six tests independently detach and mutate the actual event payload while leaving the manifest unchanged; all six demonstrate incorrect acceptance in RED and refusal in green.
- **F3, exact source eye booleans:** `_source` now immediately requires canonical equality of `application['eyes']` with `{left:true,right:true}`, before the inherited source validator and replay. Both integer and float substitutions are tested after being correctly bound into source/Context hashes, while restored event eyes remain genuine booleans. Both were accepted in RED and now refuse.

The fixes are local and maintainable: they reuse the existing canonical comparison and writer, preserve accepted predecessor helpers, and add focused adversarial tests for the exact gaps. The source-prefix hash algorithm remains equivalent for valid inputs; it is now incremental rather than a joined prefix allocation. No schema, cap, identity, producer format, public-adapter, authority, or scoring permission changes appear in the diff.

## Evidence inspected

Read the actual retained round1 logs, not only the appended report:

| Retained log | Observed result |
| --- | --- |
| `task-3-evidence/round1/red.log` | 9 failed, 1 passed, 113 deselected, 3.18s; the intended F1–F3 failures, with exact-cap positive passing. |
| `task-3-evidence/round1/focused-green.log` | 10 passed, 113 deselected, 2.81s. |
| `task-3-evidence/round1/final-green.log` | 313 passed, 9 skipped, 169.56s for the approved five-file command documented in the implementation report. |

Recomputed final log SHA256: `9d4b1e4c65c4c6fa330db3007e457ef5177d659bea0de9509f30377fd88310d8`, matching the report. The nine unchanged frozen-pin collection skips are not qualification passes. Scoped `git diff --check` passed and the working tree was clean before writing this review. No test rerun or additional probe was necessary for this narrow diff.

Read the retained round1 normal900 authored descriptor: **4,838 events, 7,012,715 bytes**, hash `92d2a3f9421e25eec4b4581e7deeaf2a2336d86460235569e6bc682f71b5035f`, against the unchanged **5,242,880-byte** condition-event limit. That authored normal time_limit sample remains an expected resource refusal and unscored. A fitting900 positive remains unestablished. The separate invalid900-plus-sensor-tail input is not normal900 evidence; neither sample is an actual corpus measurement or proof of universal900 impossibility.

## Acceptance boundary

This approval resolves the three Task3a implementation findings and supports the scoped conditional pure-proof deliverable. It does not authenticate actual source/SNP/native placement, actual job-body correspondence, original container bytes/inventory, held custody, publication, or source admission. Public Task3b remains intentionally absent pending authentic Task6 custody. Full-project qualification, adoption, resource admission and GO remain closed; actual acceptance remains false.

Only this review file was written. No code or HEAD changes, tests, native/model/raw/SNP/protected reads, services, dependencies, CI, cleanup, or further agents were run. Account quota telemetry remains unavailable/unknown.
