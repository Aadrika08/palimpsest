# Manual lab refresh v5: protocol

This protocol prepares a single registered real-browser session. It is run once: there is no corrective attempt and no retry. Preparation does not consume the allocation. The real 60-minute session starts only when a separate instruction is given.

The v3 failure has a cause and a fix (see the [diagnosis](../reports/lab-chromium-resources-v1.md)). Playwright's default `--disable-dev-shm-usage` put Chromium's shared memory in `/tmp`, the tmpfs that campaigns fill. The fix keeps it on `/dev/shm`. All consumed v1, v2 and v3 phases stay unchanged.

v5 follows v4. [v4](../reports/manual-lab-refresh-v4.md) passed everything that ran, but an interruption stopped it at endurance cycle 18 of 30. It also showed the page's idle DOM growing by about 70 nodes per cycle. That growth came from every recorded run being rendered into the run and snapshot selects. v5 makes three changes:

1. **Bounded run lists.** The UI shows a window of 10 runs and 10 snapshots (`ui/src/run-window.ts`). Selected runs and this tab's recent runs always appear in it. A **Find run** search over run id, controller and scenario reaches any run, so every run stays selectable. Checked by `npm run test:run-window`; the endurance spec also searches for cycle 0's source run on every later cycle.
2. **A DOM-node gate.** Idle post-GC DOM nodes are gated under the same rule as listeners. The thresholds are set from rehearsal data.
3. **A detached launcher.** Root starts the session as a transient systemd user unit (`detached_command()` in the runner; the exact command is in the preparation report). It needs no TTY and no parent process. The runner refreshes an atomic heartbeat file at `.superpowers/sdd/manual-lab-refresh-v5/progress.json` at least every 5 s, recording the phase, status, elapsed time, endurance cycles completed out of expected, free space and pid.

## Session

The runner is `scripts/manual_lab_refresh_v5.py`. Its software fixtures are in `tests/test_manual_lab_refresh_v5.py`.

| Mode | Purpose |
| --- | --- |
| `--register` | Writes `manual-lab-refresh-v5-registration.json`. This pins the sources, installed UI dependencies, runtime, Chromium, commands, caps, floors, deadlines and acceptance criteria. |
| `--launch` | Consumes the allocation: it creates the exclusive `launched.json` marker, runs the worker under a bounded supervisor, and publishes once to `docs/reports/manual-lab-refresh-v5-evidence/`. |
| `--rehearse SECONDS CYCLE` | Runs the same worker and judging on a separate rehearsal phase. It is never published and never consumes the allocation. |

The worker runs these phases in order:

1. **Browser preflight.** Records the UTC time and free space on `/tmp`, `/dev/shm` and the project disk. Records the Chromium version and binary hash, and the Playwright and Node versions. Runs `npm run test:browser-shm`, which checks that Chromium's shared memory is on `/dev/shm`.
2. **Selection.** A single Playwright `--list`. It must name exactly the 8 acceptance tests and the endurance test.
3. **Build.** `npm run build`.
4. **Acceptance browser suite**, on a fresh lab server (port 8776) with `PALIMPSEST_MEASURE_UI=1` and `PALIMPSEST_REQUIRE_UI_TARGETS=1`. It runs every test in `ui/tests/lab.spec.ts` and `ui/tests/recorded-snapshots.spec.ts`:
   - manual workflow: inspection, paused snapshot, two sequential branches (the second with a goal edit), comparison, recorded playback and SVG export;
   - action and policy replay, transport pause, real WebSocket disconnect, status-only reload recovery, stop, and an authenticated bundle export with checksum-verified members;
   - trajectory overlay isolation and keyboard error recovery;
   - memory inspector and U-only branch;
   - declared-task inspection for two scenarios;
   - measured cadence;
   - recorded-snapshot recovery.
5. **Mixed browser endurance**, on a second fresh server (port 8777). It runs `ui/tests/lab-endurance.spec.ts` for 3600 s as 30 cycles of 120 s. Chromium is wrapped in `scripts/lab_chromium_resource_probe.py`, which samples every 5 s, capped at 4 MiB. Every cycle goes through the actual UI:
   - create a manual run;
   - stream for 4 s with manual drive and the preview-request pattern (cadence meter on);
   - pause, step, snapshot and close;
   - branch from that snapshot (odd cycles carry a validated goal edit), step twice, close;
   - action replay on even cycles and policy replay on odd cycles, each requiring a passed report;
   - recorded playback;
   - a page reload every fifth cycle, which must recover the local stream;
   - stay idle until the cycle ends, then take a forced-GC renderer sample (`HeapProfiler.collectGarbage` twice).

Live lab owners record through a bounded background writer (`RunWriter.start_background`, commit `579fc44`). It keeps the chunk and event fsyncs out of the step and display loop. Every recording is still byte-identical to the synchronous path and fully durable before the run closes. Each owner's writer statistics are kept in its `supervisor.json`, including backpressure events, the queue high-water mark and any error. Replay jobs and all other recording paths stay synchronous. The queue holds at most 16 items. Each chunk carries about 6.3 MB of camera arrays, so the queue can hold at most about 100 MB per owner before the owner blocks. `evaluate()` records every owner's writer statistics in the session evidence (`evaluation.recorded.recording_writers`); a writer error already fails that owner's close.

## Acceptance criteria (all required)

**Cadence (decided tolerance).** Emission stays at 30 Hz. The delivered DOM display rate must average at least 29 Hz over the full window. The 99th-percentile gap between samples must be at most 70 ms. Command acknowledgement p95 must be under 150 ms. The p50 and p99 gaps are recorded.
- The rule is applied to the 8 s measured test, which the browser enforces and the runner recomputes from raw timestamps.
- It is also applied to the pooled 4 s endurance windows. Pooled means total updates divided by total window time; gaps between windows are not counted.

**DOM-node growth (new in v5).** The rule has the same shape as the listener rule, with an allowance of max(256, 10% of the early median), over at least 3 cycles. JS heap is recorded only, not gated.

**Listener growth.**
- The forced-GC idle event-listener counts are compared between the early third and the late third of cycles, by median.
- If the late median exceeds the early median by more than max(64, 10% of the early median), the session fails: that is unreclaimed, monotonic growth.
- Growth while streaming that a forced GC reclaims is allowed, and is recorded as streaming raw minus idle post-GC.
- DOM nodes are gated under the rule above. JS heap is recorded under the same rule but does not gate the session.

**Workflow and endurance.**
- Exactly 8 acceptance tests pass, with none skipped, flaky or unexpected.
- Every owner-close response is HTTP 200 with status `closed`.
- At least one SVG and one bundle are exported.
- All 30 endurance cycles complete, and every replay passes.
- There are zero network loading failures (requests cancelled by a reload are excluded) and zero page errors.

**Resources and cleanup.**
- Starting floors: `/tmp` at least 2 GiB free, `/dev/shm` at least 1 GiB, project disk at least 10 GiB.
- Continuing floors, checked every second while a child runs: `/tmp` 2 GiB, `/dev/shm` 1 GiB, project 4 GiB.
- Control storage is at most 7 GiB.
- Acceptance server: 2 GiB managed storage, 32 runs, 4 snapshots per run, 4 exports.
- Endurance server: 4 GiB managed storage, 128 runs, 2 snapshots per run, 1 export.
- Both servers must shut down gracefully, and their logs must contain no errors.
- Cleanup allows one natural-exit window of 2 s for exact descendant identities. A survivor is killed and fails the session.
- Deadlines: worker 5730 s, supervisor 5790 s, publication 5880 s, outer TERM at 5970 s and KILL 10 s after that.

A failed browser phase is recorded and the session continues, so the single consumed allocation always produces both acceptance and endurance evidence; the evaluation then fails it. Infrastructure failures stop the session: a floor, a deadline, server readiness or shutdown, or a selection mismatch.

Qualification claims remain empty. This session is software and browser acceptance of the lab only. It makes no human-usability, artistic, scientific or hardware claim.
