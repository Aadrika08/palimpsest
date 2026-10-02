# M3 / R1 hardening contract

Base: M2 draft PR #3, `be25154`. Scope: approved PRD LAB-001–016, ART-001 and operational requirements in §16. No model-learning or physical qualification claim.

## Work and ownership

- Parent: worker pacing/active execution telemetry, storage admission and integration in lab/worker/replay/artifacts/CLI, bounded native/Python logs, final integration and evidence.
- Storage owner: one shared storage budget/limits implementation, existing recorder and snapshot integration, focused exhaustion/locking tests.
- Recovery owner: actual abrupt-owner and recorder-publication failure checks, offline runner, sustained execution benchmark, mixed-operation endurance runner and operational runbook.
- UI owner: frontend-only trajectory overlay and input-isolation check, explicit measured RTF, keyboard/accessibility checks, actual browser command/display measurements.

Use one active mutation job (run, branch, replay or export), reject conflicting operations, and retain partial evidence on failure. Count existing outputs, snapshots, logs and interrupted temporary files before admission; assets must live outside managed output roots. Check quota and free-space bounds before publication, including temporary-file overlap. Never silently delete old runs. Bound log bytes at the writer boundary, including native file descriptors. Preserve the original immutable source recording during replay.

Pacing uses fixed 20 ms simulation ticks and deadlines including computation, without skipping updates. Slow inference remains allowed and labelled. Report active execution RTF separately from time paused/loading, and report browser paint cadence separately from actual telemetry arrival. The 30 FPS display target must be measured rather than inferred from a configured interval.

## Release checks

- [x] All lifecycle, allowlist, interruption, full-state recovery, replay and export checks pass with actual EGL enabled.
- [x] Aggregate storage/free-space/count bounds and native/Python log caps stop explicitly before exceeding their configured budget; recovery preserves the published prefix.
- [x] Abrupt owner exit, renderer stalls, recorder failures, browser disconnect and explicit headless continuation have runnable checks and retained diagnostics.
- [x] Cached setup and one-command launch run inside an isolated network namespace without changing host networking; include the cached full-model profile where feasible.
- [x] Manual and teacher supplied simple profiles meet real-time execution on this host; full FLYNN latency/RTF is measured with its actual device/profile.
- [x] Actual browser command receipt p95 is below 150 ms outside loading; report application latency separately. Measure 30 FPS display target and label any unmet target.
- [x] Overlay changes cannot mutate policy inputs; controls remain accessible by keyboard and usable at narrow widths.
- [ ] Frozen-runtime 60-minute mixed-operation run passes declared resource/growth budgets with clean child shutdown and a complete report.
- [ ] Requirements-to-evidence matrix, setup/recovery/retention instructions, licence/provenance limits and release status are committed. Push as Aadrika08 and open a stacked draft PR; do not merge automatically.

Short smoke runs and cached-network feasibility have already passed on M2. They are preparation, not substitutes for the final hardening checks or 60-minute gate. Keep raw results and measured source identities; do not rewrite prior evidence after source changes.
