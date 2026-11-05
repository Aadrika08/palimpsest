# Task 2 fix round 1 independent scoped review

Reviewed target: `24ccccf2f1f70e45b8a857f01ae487d1175c1b19..54d41e478df2a0b968123586880551836fc4d30a`.

Scope: the original P2 marker-witness finding and material breakage introduced by this fix only. The target changes exactly the public source seal helper and its tests (67 additions, 3 removals). Unchanged code and Task 3 obligations were not reopened.

## Verdict

**Approved for this scoped fix.** Original P2: **addressed**. No supported new P1/P2 or material breakage found in the changed lines. Together with the original review, there are no remaining supported findings in the reviewed Task 2 slice. This is software review acceptance, not source qualification or an actual execution grant.

## Finding disposition

The new `_prepared_marker` at `scripts/memory_family_source_seal_v2.py:184` opens `.commit.tmp` immediately after the exclusive write and registers descriptor closure on the existing lifetime stack before validation. It verifies regular-file type, single link, bounded exact size, expected bytes, and device/inode/mode/size/mtime/link-count. Its descriptor and mutation check remain active through real rename and teardown.

The writer establishes this witness at `:445`, then explicitly checks that `commit.json` still resolves to the same prepared descriptor and pre-rename bytes/mtime at `:463`. Ctime is excluded from the pre-rename comparison because rename can legitimately change it. The existing final tree then supplies the post-rename full-metadata/name witness. The callback order keeps the output directory open until the marker checks and closure have completed, and errors remain inside the existing quarantine/`SealIndeterminate` handling.

The new authored regression at `tests/test_memory_family_source_seal_v2.py:717` reproduces the original real-rename, append-and-restore sequence, asserts same inode and changed mtime, and requires writer refusal. Both durable quarantine and unavailable-quarantine paths are covered; raw bytes and the restored marker remain retained. The durable-quarantine case also refuses a public reread. This addresses the reproduced finding without changing protocol, APIs, qualification scope, accounting reserves or legacy code.

## Verification and limits

- Inspected `fix1-red-marker.log`: genuine **2 failed / 105 deselected** before the fix, both failing new marker regressions.
- Inspected `fix1-focused.log`: **8 passed / 99 deselected** after the fix.
- Inspected `fix1-final.log`: **236 passed** (107 public source + 129 numeric codec), pytest 173.94 seconds, measured wall 174.23 seconds, exit 0. This is the implementer's final frozen run; this reviewer did not rerun that suite or claim whole-repository coverage.
- Independently ran `sha256sum -c runs/memory-numeric-v2-task2/fix1-final-snapshot.sha256`: source, tests and unchanged protocol all matched.
- Independently ran `git diff --check 24ccccf2 54d41e478df2a0b968123586880551836fc4d30a`: passed. HEAD matched the target commit and the working tree was clean before this ignored report was added.

No additional probe was necessary: the new regressions directly reproduce the original independent authored observation, and the changed mechanism is explicit. No source/test/protocol edits, actual data/native/research execution, deletion, commit or push were performed by this reviewer. Enclosing parent census, stage/lifetime acceptance and actual qualification remain outside this scoped review.
