# M7 navigation development v2 — completed, negative gate

All 24 fixed fresh runs completed at producer `e3f9a471aacf359943eebb72f6a1e37aebe0ca2c`, retaining 10,822 numeric rows, 24 initial snapshots and 22,159 events. **Every augmented seed achieved 0/4 goals**, below the unchanged requirement of at least 3/4 **per seed**. Old-corpus seeds 10/11/12 achieved 2/4, 1/4 and 1/4. Operational completion is separate from this failed development gate. R3 remains open; held-out scenes 3120–3127 remain locked. There was no second development run, refit or threshold change.

The [evidence index](m7-navigation-development-v2.json) binds the [six frozen models](../../data/manifests/male-navigation-research-development-v2.json), [development handoff](../plans/m7-navigation-development-v2.md), controls, actual startup/drain receipts, and independent checks. Both arms retain `male-original` / ORIGINAL graph: the comparison is old-corpus versus augmented training data, **not topology**. Arm and training seed are research provenance; inference scene seed is separate. The [training report](m7-navigation-training-v2.md) retains the unequal optimizer-update budget and privileged-teacher label limitations. These results do not establish their causal contribution.

## All fixed outcomes

Entries show natural outcome / executed ticks. All owners used the same task, contact profile, CPU model interface and maximum 600 ticks; no teacher supplied actions. The four scientific initial states matched across all six models before first prediction/action, with declared model-specific fields excluded. Parent-data disjointness and original-graph admission were retained.

| Scene | Training seed | Old-corpus | Augmented |
| --- | --- | --- | --- |
| 3110 | 10 | goal / 348 | stalled / 256 |
| 3110 | 11 | stalled / 147 | time_limit / 600 |
| 3110 | 12 | stalled / 475 | stalled / 369 |
| 3111 | 10 | goal / 415 | stalled / 198 |
| 3111 | 11 | stalled / 271 | time_limit / 600 |
| 3111 | 12 | goal / 543 | stalled / 419 |
| 3112 | 10 | stalled / 268 | time_limit / 600 |
| 3112 | 11 | goal / 533 | time_limit / 600 |
| 3112 | 12 | stalled / 294 | stalled / 344 |
| 3113 | 10 | stalled / 594 | time_limit / 600 |
| 3113 | 11 | time_limit / 600 | time_limit / 600 |
| 3113 | 12 | time_limit / 600 | stalled / 548 |

Totals: four goals, twelve stalled episodes and eight time limits. All 24 records completed normally; there was no stopped infrastructure prefix or replacement. Each interval retained raw contact telemetry before the frozen all-11-stage / 125-pair profile admission. The final gate reports `operational_status: completed` and `status: failed-development-gate`; no pooling or winning-seed selection is permitted.

## Execution and evidence scopes

Actual exec session **15391** fully drained with exit **0**. The retained host receipt binds the exact command and terminal tool chunk `0df48a`, independently of the nested JSON reports. Runner supervised duration was 861.498307463 s; launcher supervised duration was 944.931785805 s. Enclosing **prepublication** elapsed was 946.311591649 s. The conservative host-observed interval was 988.523879344 s, including invocation/observation scheduling delay; it is not the exact process duration.

Bounds stayed 180 s per owner, 1,800 s runner, 1,850 s normal through return, TERM target 1,857 s / KILL target 1,860 s / fallback 1,863 s. Failure-only explicit waits form a nominal 1,883 s envelope, excluding publication and uninterruptible I/O; this is not a universal wall-time guarantee. The 4 GiB stage includes 4,074 MiB existing allowances, up to 10 MiB diagnostic extras and the full 8 MiB reserved headroom (4,092 MiB total), with a 1 GiB floor. Startup observed 25,083,748,352 bytes free against a whole-study-plus-floor requirement of 18,857,590,784 bytes. Storage admission/per-writer caps and sampling are not an atomic filesystem quota.

Both finite samplers stopped without errors, PID reuse, forced signals or survivors. Their 29-identity union plus enclosing PID `1079039` / start `15346855` were absent after host drain. The existing owned regular HOME lock was probed and released through its file descriptor; no startup managed-root lock was created. All current source, upstream, asset, selected runtime, six-model/input and control inventories remained unchanged. Finite sampling is not proof that every transient process was observed. Current runtime identity is e3f9a47; historical training remains 6feade9 with the separately pinned publication head 041434dd.

Producer checks: 18 focused source fixtures passed in 1.366 s; 11 control fixtures passed without skips in .185 s (.879357581 s supervised). The successful metadata preflight recorded 6.111501325 s before publication; its actual exit/drain is retained separately. Root independently repeated the 11 control fixtures and admitted all metadata/capacity. No actual model or native owner was created by those checks.

Root's retained raw audit passed first, with session **31073** fully drained exit 0: 110.116982690 s child / 110.443016658 s supervised. Receipt SHA `5dfe731fa3b22659869cf0927970c9ed845e36d866f02efa345fe7190ffb37b9` binds all 542 raw files / 2,382,058,832 bytes, rows/events/snapshots, four matched scenes, contacts, fixed outcomes and process cleanup. Its scope combines the existing source/one-call/initial/contact validators with independent raw contact-incidence, finite-array, count/hash and cleanup checks; it did **not** reconstruct policy inference or simulate physics. Root's separate host cross-check passed first, SHA `e8274aedde2ee8a48949d8ecb70b610176b55c4377e3f7000dec54aa81e29694`, reconciling the actual tool return, 30 absent identities and small receipt references.

## Preserved preparation and monitoring failures

The first focused source invocation failed import on a missing closing parenthesis. Its original source/log is retained; the one-parenthesis correction preceded the 18 passing checks. The first metadata-only readmission refused the uninitialized pinned upstream checkout before candidate admission or any model/native work. Bounded local setup checked out the exact clean `8d964599` gitlink; a separately authorized output-path-only v2 readmission then passed all six bundles. Both failed and corrected receipts remain indexed. Initial unexecuted control drafts are also retained; review corrected loss of obtainable drift evidence and an internal-only `after` CLI mismatch before any control invocation.

During the successful experiment, one separate monitor command attempted the nonexistent `/home/utkarsh/Work/shraddha/brain/.venv/bin/python -V` and returned shell **127 before Python started**. Tool chunk `03e2f5`, exact error and scope are retained in `host-end-session.json`. It neither changed the active experimental command nor caused an experimental retry. The actual experiment, producer control checks and independent root raw audit each completed on their first invocation.

Publication hashes only 83 small direct/control/prerequisite references (2,274,255 bytes). The exact 542-entry raw ledger is copied from the hash-pinned root audit without repeating its bulk read. Deduplicated across both ledgers: 624 references / 2,383,934,489 bytes. Retained local artifacts require these sibling worktrees; the tracked index preserves their identities. This report supplies no useful-navigation, topology, biological or physical qualification claim.
