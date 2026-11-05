# Task 1 independent spec and quality review

What this change does: Adds a strict three-array numeric companion to every unchanged 16-member V1 partition. It checks the complete composite format, retains the existing producer proof, and compares the added values against supplied raw rows without granting publication or qualification authority.

Verdict: Approve Task 1. No supported P1 or P2 findings.

## Reviewed identity and scope

- Review target: `2652e367353983c8898e997c0d616f85cbc5149e..383b4c29cc16aa03bb2708349b5dbb6314c3b751` and retained `task-1-review.diff`.
- Inspected all 320 codec source lines, the complete protocol, all 592 test lines, Task 1 implementation plan/report, connected V1 reader/NPZ/limit helpers, and unchanged producer `_prove`.
- Target diff changes exactly the three owned new codec/protocol/test files. Current HEAD was `8ba2c052419a8cd999f299e4e37c96ac7d8268b3`, a later unrelated documentation commit; a direct diff against the target confirmed the three reviewed files are identical. The unrelated oracle proposal is excluded.
- Confirmed the report destination is ignored. No source edits, commit, push, research/model/native execution, protected data read, or actual raw/SNP/asset/catalog read was performed. Authored fixture references were reviewed as source code only.

## Contract and quality assessment

- The base dictionary is explicitly extracted and passed to unchanged V1 validation. Envelope file descriptors bind every original payload, and each companion entry binds the complete original chunk descriptor, including sequence/path/SHA, episode/start/count, and compact SHA. Exact expected paths and ordered index correspondence reject missing, reordered, or orphan companions and V1-only input; no fallback exists.
- Mandatory `<f8` scalar timing values and `(3,4)` population values are checked without Python scalar/list inference or dtype casts. Reader validation enforces finite values and field shapes. The proof checks every added field at every supplied tick using dtype, shape, and bytes, preserving signed-zero distinctions, after calling unchanged producer `_prove` for all old obligations.
- Companion preflight bounds payload size, member count/name/compression/flags/comments, NPY member lengths, version, header position, primitive dtype, dimensions and C order before the mechanical legacy decoder allocates arrays. Re-serialization through the actual existing `np.savez` helper rejects alternate ZIP/NPY encodings and trailing content.
- Receipt binding preserves its canonical byte cap, frozen source declaration and base identity, with exact integer row/chunk/event counts. Population order and listed source identities remain declared provenance; neither decoding nor comparison authenticates their labels or source lifetime.
- Tests exercise an authored full `(3,4)` source fixture accepted by unchanged public raw auditing, then run the complete producer-plus-numeric proof. Rehashed timing/population bit mutations at early nonsampled/final ticks, row/column permutations and signed-zero changes reach raw comparison rather than merely failing stale hashes. Existing retained-field corruption still fails the old proof.
- The ledger sums actual bundle byte lengths and explicitly supplied combined external overhead, subtracting the validated dense, selected pixel and event payloads to obtain overhead. Original 32/25 MiB caps and one combined MiB are retained. Tests independently sum serialized NPZ arrays, check actual ZIP/NPY overhead for all partition counts 1–32, exact/one-byte-over bounds, operation maxima and V1-valid metadata that cannot fit V2. External overhead defaults explicitly to zero; the codec marks snapshot and stage-peak accounting false. This is not complete public caller accounting.
- Claims and returned scope keep actual source/condition/model/physics/full-pixel/lifetime/allocation authority false. Conversion creates an in-memory candidate and does not publish, prune or qualify it. The public source writer/rereader, custody, complete unique-path ledger and parent integration remain Tasks 2/3.

## Verification evidence and limits

Read retained `runs/memory-numeric-v2-task1/final-reviewed.log`: **235 passed, 58 skipped**, exit status 0, 26.98 seconds pytest time / 27.39 seconds wall time. This is retained implementation evidence, not a fresh reviewer run; the 58 historical skips remain skips. No specific uncovered defect justified rerunning the suite within this bounded review.

Read `serialized-ledgers.log`: authored source maximum uses 24,596,866 bundle bytes with 297,833 overhead; authored condition maximum uses 18,826,125 bundle bytes with 232,714 overhead. Both explicitly use zero external overhead and false snapshot/stage-peak accounting. These numbers demonstrate those serialized fixtures, not actual acquisition feasibility or full-stage fit.

Reviewer read-only Git checks confirmed the target has only the three owned additions, unchanged legacy codec/producer/raw-auditor target diffs, identical reviewed working-tree files, and a clean target `git diff --check`.

Approval covers Task 1 software only. Actual preservation, Task 2 public source completion, source lifetime acceptance, qualification, pin issuance and permission to execute remain unproven and ungranted.
