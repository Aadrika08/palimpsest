# Memory v4 source finalization: synthetic software evidence

This branch adds the approved source-only post-close converter and staging seal.
It retains every raw byte and the one original source snapshot. It never launches
an owner, opens a model/native/retained/held-out asset, authorizes allocation, prunes
a run, closes a condition/case/campaign, or changes an analysis/release threshold.
All protocol claims remain false; qualification claims remain empty.

The separate raw-auditor process publishes the pre-prune receipt into the existing
independent owner-audit slot. The converter consumes that immutable descriptor,
post-close terminal-export contract, original owner record, controls and external
shared snapshot. Raw-to-compact proof independently compares retained numeric
bits, camera digests, legacy row digests, ASCII-hex aggregate trace, selected
frames, exact legacy metadata bytes and source oracle projection. Disk payloads,
support files, raw inventory and input descriptor/namespace identities stay bound
through all preparation checks. The reader retains consumed input/output file
identities, bytes and complete source/case/raw namespaces through return.

Every preparation file and directory is fsynced before final publication. The
prepared `.commit.tmp` uses the existing compact publication temporary allowance;
all input/output context exits finish before Linux no-replace final marker rename.
There is no overwriting fallback or post-rename validation/fsync. Namespace
persistence across power loss remains explicitly unqualified, and final case
publication is a separate prerequisite. Read-only descriptor-close failures after
publication are returned as teardown warnings; pre-publication close failures
stop preparation. This avoids reclassifying an already published source as an
unknown publication while requiring future native callers to stop on a warning.

Accounting is unchanged. The temporary duplicate raw worker report consumes the
one existing converter-scratch entry and at most 1 MiB of its 32 MiB allowance;
the encoder writes no numeric disk scratch. The final worker report is charged
once to owner support, and the sole source owner record is retained in place.
External raw audit uses its separate existing 1 MiB audit allowance; its retained
recording copy and conversion receipt consume compact overhead. No extra source
snapshot, `.pending/cases` directory, permanent admission anchor or control/export
file was introduced.

## Verification

- Faithful RED reproduced missing source-finalization behavior, rebound legacy
  whitespace acceptance, context-exit quarantine omission, numeric descriptor
  aliases, late source/case/raw namespace drift, late raw/output mutation,
  marker-data fsync plus quarantine failure admitting the old marker, and
  postcommit descriptor-close failure reclassifying publication.
- Final source suite: **50 passed in 40.33 seconds**, using
  `/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python`
  and `PYTHONPATH=src:.`.
- The last complete affected invocation had **233 passed / 1 failed**. The sole
  failure was initial unsealed-source rejection using a drift exception class;
  that initial validation classification was fixed and covered by the final
  source suite. Its **193 unchanged raw-audit/pair/compact tests passed**.
  Subsequent bounded source regressions/refinements are covered by the final 50.
  This is split coverage, not a final single-invocation 243-test pass claim.
- Exact behavior-source pins, canonical protocol, pure import, all-false claims,
  Python compile checks and `git diff --check` passed after the final code change.
- Final protocol SHA-256:
  `40c2f243559dd177d1387ccfa4efe6419181be5ed9cd0aa330f388f2a9ce4eb9`.

Independent review must rerun the four affected files at the committed head:

```sh
PYTHONPATH=src:. /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python -m pytest -q tests/test_memory_family_producer_v4.py tests/test_memory_family_raw_audit_v4.py tests/test_memory_family_oracle_admission_v4.py tests/test_memory_family_compact_v4.py
```

## Remaining boundaries

The source sealer/reader operates only on `.pending/<case>` with its retained raw
source. Existing pure pair admission retains its original read-only final-root
descriptor semantics; the next condition-close slice must wire staged receipt/case
handles and the nine registered conditions. Native owner job/cleanup/writer
integration, model/cell replay, complete condition/case/final closes, pruning,
namespace coverage and allocation admission remain open. Pruning always refuses
without mutation. CI and physical rover work remain outside this scope. No third
navigation attempt was created or run.
