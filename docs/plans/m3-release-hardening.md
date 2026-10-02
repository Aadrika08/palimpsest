# M3 / R1 hardening contract

Base: M2 draft PR #3, `be25154`. Scope: approved PRD LAB-001–016, ART-001 and operational metrics, resource/security/licensing and release requirements in §§16–18 and §21. No model-learning or physical qualification claim.

## Work and ownership

- Parent: worker pacing/active execution telemetry, storage admission and integration in lab/worker/replay/artifacts/CLI, bounded native/Python logs, final integration and evidence.
- Storage owner: one shared storage budget/limits implementation, existing recorder and snapshot integration, focused exhaustion/locking tests.
- Recovery owner: actual abrupt-owner and recorder-publication failure checks, offline runner, sustained execution benchmark, mixed-operation endurance runner and operational runbook.
- UI owner: frontend-only trajectory overlay and input-isolation check, explicit measured RTF, keyboard/accessibility checks, actual browser command/display measurements.

Use one active mutation job (run, branch, replay or export), reject conflicting operations, and retain partial evidence on failure. Count existing outputs, snapshots, logs and interrupted temporary files before admission; assets must live outside managed output roots. Check quota and free-space bounds before publication, including temporary-file overlap. Never silently delete old runs. Bound log bytes at the writer boundary, including native file descriptors. Preserve the original immutable source recording during replay.

Pacing uses fixed 20 ms simulation ticks and deadlines including computation, without skipping updates. Slow inference remains allowed and labelled. Report active execution RTF separately from time paused/loading, and report browser paint cadence separately from actual telemetry arrival. The 30 FPS display target must be measured rather than inferred from a configured interval.

## Release checks

Evidence: [requirements matrix](../requirements-evidence.md), [M3 report/index](../reports/m3-release-hardening.md), and [operating runbook](../reports/lab-hardening-runbook.md). The fresh mixed gate passed on unchanged `c43f5df` in 3600.000099 seconds under `runs/m3-endurance-hour-20261002b`. Checked items below describe scoped operational evidence; final R1 review is complete under PRD §21.3, retaining documented limitations.

- [x] All lifecycle, allowlist, interruption, full-state recovery, replay and export checks pass with actual EGL enabled.
- [x] Aggregate storage/free-space/count bounds and native/Python log caps stop explicitly before exceeding their configured budget; recovery preserves the published prefix.
- [x] Abrupt owner exit, watchdog stalls, recorder failures, browser disconnect and configured headless continuation have runnable fault/recovery checks with retained diagnostics; fixture and actual MuJoCo/full-model evidence are distinguished in the matrix.
- [x] Cached setup, full-model CPU verification and CLI/API launch passed inside an isolated network namespace on recorded source `ec1d2e6`, without changing host networking. This historical scoped pass is not a rerun on `c43f5df`.
- [x] Natural completion on unchanged `c43f5df` passes supplied simple-profile manual/teacher worker-active RTF ≥1 on this host; outer RTF remains below 1. Full CPU-FLYNN inference/action-replay timings retain their separate earlier smoke scope, without a full-model real-time claim.
- [x] Recorded-source `ec1d2e6` browser receipt p95 is 43.4 ms (<150 ms), application p95 separately 53.8 ms. Full-window display updates measure 27.9809 Hz; the 30 Hz target is explicitly unmet, not checked as a pass.
- [x] Overlay changes cannot mutate policy inputs; controls remain accessible by keyboard and usable at narrow widths.
- [x] Frozen-runtime 60-minute mixed gate passes all eight declared gates:29 complete cycles (manual 10/teacher 10/Flynn 9),58 passed executable replays,116 closed/completed supervisor/job dispositions, one sampled owner, resource/growth bounds and orderly server SIGTERM. Finite sampling and per-owner exit-code recording limits remain explicit; original failed hour/close reports are retained.
- [x] Requirements-to-evidence matrix, linked setup/recovery/retention instructions and licence/provenance limits are prepared and cross-checked; release status retains the documented limits.
- [x] Publish the reviewed documentation and terminal release-status assessment with this change. Draft PR #4 already exists as the stack above PR #3; push as Aadrika08, do not merge automatically.

M3 has retained short full-model CPU smoke, cached offline and browser observations on their recorded sources, plus current natural throughput and two normal full-model close passes. The fresh 60-minute mixed gate has now passed; it does not represent continuous inference or qualify browser 30 Hz/full-FLYNN real-time behavior. No hardware, memory-learning or original-training-lineage qualification follows. Keep raw results and measured source identities; do not rewrite prior evidence after source changes.
