# Manual lab refresh v4: retained interrupted session

**Verdict: failed, because the session was interrupted.** It was not a lab failure and it is not a pass. The single registered allocation was consumed, so per protocol there was no relaunch and no retry.

- **Launch:** `9073ec1`, registration sha256 `be292c56…e9c861`. Started 2026-10-19 03:06:07Z with the registered command, from a clean tree, on an idle host (load 0.28).
- **Interruption:** at 03:41:40Z, 2132 s in, a SIGTERM reached the launch process tree. The agent session that started the session in the background hit its usage limit, and its shell was terminated.
  - The supervisor recorded the worker as `interrupted`, and the worker failed with `KeyboardInterrupt` (from the SIGTERM handler).
  - The endurance browser was stopped at cycle 18 of 30.
  - Every phase before the interruption had passed.
- **Evidence** is in [`manual-lab-refresh-v4-evidence/`](manual-lab-refresh-v4-evidence/), byte copies made by the runner's publish step: 51 files, 28 MB, including the endurance Playwright trace. The run was interrupted before `publication.json` was written; the partial publication is retained as-is.
- The canonical phase folder `.superpowers/sdd/manual-lab-refresh-v4/` is kept locally, ignored by git, 2.2 GB including runs. Its `result.json` says `failed`.

## Criteria with measured values

| Criterion | Result |
| --- | --- |
| Preflight | Passed. `/tmp` 4.77 GB free, `/dev/shm` 7.78 GB, project disk 14.26 GB. Chromium 152.0.7977.82 (binary sha `27c398e1…`), Playwright 1.63.0, Node v24.21.0. `test:browser-shm` exited 0. |
| Selection | Passed. Exactly 9 tests: 8 acceptance and 1 endurance. |
| Acceptance suite | **Passed, 8 of 8**, with 0 skipped, flaky or unexpected (66 s). Covered inspection, snapshot, branches including the goal edit, comparison, action and policy replay, SVG and bundle export, WebSocket disconnect and reload recovery, the memory inspector and recorded snapshots. |
| Measured cadence (8 s window) | **Passed.** 29.91 Hz, p50 gap 33.0 ms, p99 gap 45.3 ms, acknowledgement p95 26.5 ms (12 commands). |
| Exports | Passed: 1 SVG and 1 bundle. |
| Owner closes | Passed: 7 of 7 `closed`, HTTP 200. |
| Endurance cycles | **Failed: 17 of 30**, because of the interruption. All 17 completed cycles passed their replays (action and policy). 3 reloads recovered the stream. Every preview request returned HTTP 200. |
| Endurance cadence (17 windows, pooled) | Passed. 29.79 Hz from 2,111 updates, p50 gap 32.8 ms, p99 gap 57.9 ms, acknowledgement p95 32 ms (136 commands). Per cycle: 29.50–30.24 Hz, p99 gap 44.4–67.3 ms. |
| Endurance network and page errors | Passed: 0 network failures and 0 page errors. |
| Endurance test result | **Failed.** Playwright reported "Channel closed" when the session was interrupted. |
| Listener growth (gate) | **Passed.** Idle post-GC counts: 256, 256, 256, 256, 210, 256, 256, 256, 256, 210, 256, 256, 256, 256, 210, 257, 256. Unreclaimed growth 0, allowance 64. Raw counts while streaming were 284–1144 and were reclaimed by GC. |
| DOM nodes (recorded only) | Exceeded the recorded rule. Idle post-GC nodes went from 1,816 to 2,953. They dropped back after each reload, but each post-reload baseline was higher (1,200, then 1,545, then 1,890). The likely cause is the page rendering every recorded run into its selects; the run count grows by about 3 per cycle. This is not a gate, but it is worth fixing or bounding. |
| JS heap (recorded only) | Within the rule. |
| Chromium resources (5 s probe, 411 samples) | `/dev/shm` regions 85–128 MB, RSS about 1.08–1.12 GB, file descriptors 362–366. Stable throughout. |
| Recording writers | 69 owners: 48 live owners in background mode and 21 synchronous replay jobs. 1,319 items written, queue peak 10 of 16, 0 backpressure events, no errors. |
| Storage | Acceptance runs 252 MB. Endurance runs 1.6 GB for 17 cycles, about 94 MB per cycle, so about 2.8 GB projected for 30 (cap 4 GiB). Floors held throughout. |
| Shutdown and cleanup | The acceptance server exited on SIGTERM (-15) with "Application shutdown complete". The endurance server also logged "Application shutdown complete". 115 processes were observed, 0 survivors needed killing, the process group is gone and the storage lease is free. |

## Assessment

Everything that ran passed, except the endurance phase, which was cut off by the interruption. That includes cadence under the agreed tolerance on the project disk, now that the background writer is in place.

The only abnormal observation is the DOM node growth above. It tracks how many recorded runs the page lists, not a leak in its event listeners.

A full 60-minute endurance result still needs a new, separately approved allocation. The consumed allocation cannot be rerun. Run it from a process that cannot be terminated by the agent session's own limits.
