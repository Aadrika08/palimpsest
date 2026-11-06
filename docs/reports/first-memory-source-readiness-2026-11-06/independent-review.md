# Independent read-only asset resolver review

SPEC: PASS

QUALITY: APPROVED

Reviewed baseline `0e21d0b5584abae9a1adf9dafb72ca605dc64c64` to source HEAD `482589b590f04bb18ac55aa0c90b6283e7280ba3`, the complete supplied 447-line/two-file package, current resolver and existing helper source, implementation report, review brief, and the binding contract including its safe-relative-root clarification. Live HEAD matched the supplied SHA; neither owned file had uncommitted changes. The parent-owned contract clarification was the only tracked working-tree modification observed. This review file is ignored.

No actionable severity findings within the assigned scope.

## Contract and implementation checks

- `src/palimpsest/assets.py:231-251`: root spelling rejects lexical `..`; ancestor inspection proceeds from filesystem root downward with `lstat`, refusing symlinks and nondirectories before canonical resolution. Safe relative roots become absolute without changing CWD. Named inputs use the existing relative-path validator and inspect intermediate directories and regular leaves, refusing symlinks, directories at leaf roles, and special files. This is the clarified generic-helper rule, not a relaxation of future job admission.
- `src/palimpsest/assets.py:264-283`: the real project manifest parser is retained; archive/checkpoint identities use unchanged size/hash verification. Only the exact hash-named prepared directory and its metadata are selected. Metadata size is checked before opening and read at most 1 MiB plus one byte, with over-limit rejection before JSON parsing.
- `src/palimpsest/assets.py:253-262,284-294`: duplicate object keys are rejected at all nesting levels; explicit nonfinite tokens and overflowed floats refuse. Sorted JSON comparison enforces the exact six metadata fields and their complete nested values, distinguishing booleans, integers, and floats. Metadata cannot select an alternate edge path.
- `src/palimpsest/assets.py:295-302`: only the manifest's exact safe archive member is resolved; edge identity is verified. All seven source and prepared mapping leaves are type-checked before unchanged `_check_mappings(..., copy_missing=False)` verifies their pinned identities and CRLF-to-LF relation (`assets.py:148-163`). Returned keys are exactly `archive`, `checkpoint`, and `edge`, with absolute Paths under the supplied asset root.
- The appended function contains no acquisition, extraction, repair, output creation, copy, rename, deletion, graph search, fallback, model/native import, Engine integration, new qualification flag, or schema/pin change. The local standard-library `stat` import supports type checks only.

## Evidence reviewed

Read the full new test-file diff. Fixtures author tiny bytes, clone only the named static project manifest metadata, write a synthetic manifest, and invoke real `load_manifest`; they do not patch that validator. Per-call guards deny mutation/acquisition and compare retained tree bytes, names, inode/device, modes, size, mtime/ctime, symlink targets, and CWD. Positive cases cover canonical paths, relative roots, all seven CRLF pairs, and the exact metadata size boundary. Negative cases cover each input role, identity mismatch, complete metadata values/types, malformed JSON, unsafe paths/types, no alternate-edge search, over-limit pre-open refusal, and separately rebound archived mapping hashes that still fail CRLF normalization.

Read retained RED, iteration, and final logs. RED records the expected missing-resolver `AttributeError` (1 failure, 0.10 s). Iteration records 222 passed in 1.01 s. Final `/var/tmp/palimpsest-readonly-final-5cuEE3jh/pytest.log` records **222 passed in 1.00 s**; adjacent `time.txt` records wall 1.22 s, user 0.86 s, system 0.34 s, max RSS 50428 KiB. These are retained implementer results, not reviewer executions.

Read `readonly-assets-evidence/ast-preservation.txt`, which records all 21 existing top-level AST nodes unchanged. Independently inspected the baseline-to-HEAD resolver diff: the only production delta is the appended 83 lines after the original function's end; existing source is untouched. Owned-file statistics match 83 production plus 364 test insertions, zero deletions. No reviewer test or import was run; no independent AST program was executed.

## Limits

Approval covers the narrow read-only bootstrap helper and authored-fixture evidence. The checks do not preserve continuous file-descriptor custody or prevent concurrent hostile replacement, and do not establish admission, provenance, actual asset readiness, source/backend/wrapper qualification, namespace/accounting enforcement, runtime/model/native behavior, scientific results, rights/human acceptance, or deletion authority. No actual graph/checkpoint/mapping/native/runtime/catalog/raw/SNP/model/protected payload was read or hashed in this review. No tests, network, probes, research runs, CI, dependency changes, cleanup, or agents were launched. Only this ignored review artifact was written.

The full goal remains open, raw deletion remains disabled, and CPU-provider choice, independent exports, and GO remain outstanding as stated in the supplied task. This approval does not advance those gates.
