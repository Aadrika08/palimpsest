# Runtime-reference source software verification

Frozen source candidate `afacfbfc3d2ffbfa1af0dca3a70fb5e0940be207` passes the
canonical four-pass non-integration runner: **7,104 passed, 318 skipped, zero
failures**. Passes: ordinary 7,035/318 (1956.10s), isolated 7 (10.40s),
persistent 5 (59.19s), tmpfs 57 (53.26s). The ordinary pass reports105 warnings;
subsequent passes report two each. Original warning-bearing output is retained.
The final source and scoped fix reviews passed before this run.

All21 explicitly named source/config files in snapshot_sources.py match before
and after; tracked files are clean. This is a finite continuity check, not a
complete input inventory or installed-runtime/model/data hash. The earlier
57-artifact broad-hash scope error belongs to the numeric-source verification
record and is not repeated here.

The canonical runner and its clean pytest environment/test selection are
unchanged. A parent-shell-only rm wrapper suppresses the runner's final cleanup;
pytest does not inherit that wrapper. A private4GiB /tmp tmpfs is copied with
sparse tar before namespace exit. All three exit records are0. Remaining
private-tmp software fixtures are retained locally in
runs/runtime-reference-v1-canonical-20261106/tmpfs-authored-fixtures.tar:
10,588,160bytes, SHA256
249833b458cc5dbd063bda600e61eb9d0243ec22d87a6682a7b0a23a797f8941.
The archive is not included in this source report or publicly shared; no rights
or access claim follows from its checksum. Failed logs and earlier authored
workspaces remain retained locally. Test-internal disposable operations are not
a claim of retaining every transient test file.

Research opt-ins were unset. This run is ordinary software verification,
excluded from the research ledger; approved research prior remains
1,222.455497 CPU seconds in the audit lane. No actual research/source owner,
preservation comparison, runtime preparation or protected cohort was launched.
The proposed runtime profile is unadopted, public V3-job/V4-freeze execution
remains closed, actual source/preservation/scientific qualification is false,
and raw deletion stays disabled. Exact-head hosted validation is tracked
separately; older numeric-source main CI does not cover this later candidate.
