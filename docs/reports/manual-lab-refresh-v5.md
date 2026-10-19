# Manual lab refresh v5: passed

**Verdict: passed.** The single registered session passed every gate.

## Run details

- **Commit and registration:** `0b8ab81`, registration sha256 `a33414f7…aeff98`.
- **Launch:** root started it detached as the systemd user unit `palimpsest-lab-v5` at 2026-10-19 05:03:40Z, using the registered command.
- **Duration:** 3,620.8 s in total, worker 3,619.2 s. The deadline was 5,880 s.
- **Final state:** the heartbeat ended at phase `published`, status `passed`, with 30 of 30 endurance cycles.
- **Evidence:** [`manual-lab-refresh-v5-evidence/`](manual-lab-refresh-v5-evidence/) holds the runner's own `publication.json` receipt, covering 39 published files.
  - git ignores `.superpowers/` and `test-results/`, so 38 of those files are packed into `retained-records.zip` (2,019,988 bytes, sha256 `5fc03aff…4c87859a`).
  - Each packed file matches its hash in the receipt and its canonical source. The one exception is the heartbeat file, which moved on to `published` after it was copied; this is recorded in `publication-index.json`.
- **Local data:** the canonical phase folder `.superpowers/sdd/manual-lab-refresh-v5/` (2.9 GB, including runs) stays local and ignored by git.

## Gates and measured values

| Gate | Measured |
| --- | --- |
| Preflight | Passed. `/tmp` 4.73 GB free, `/dev/shm` 7.76 GB, project disk 13.24 GB. Chromium 152.0.7977.82 (binary sha `27c398e1…`), Playwright 1.63.0, Node v24.21.0. `npm run test:browser-shm` passed. |
| Selection and build | Passed: exactly 8 acceptance tests and 1 endurance test |
| Acceptance browser suite | **8 of 8 passed**; 0 skipped, flaky or unexpected (64.9 s) |
| Measured cadence (8 s window) | **Passed.** 30.04 Hz delivered (241 display updates), p50 gap 33.1 ms, p99 gap 45.4 ms, acknowledgement p95 20.6 ms (12 commands) |
| Endurance cadence (30 windows pooled) | **Passed.** 29.64 Hz (3,706 updates), p50 gap 32.8 ms, p99 gap 64.6 ms, acknowledgement p95 34 ms (240 commands) |
| Endurance cycles | **30 of 30** (3,544.8 s). 15 action and 15 policy replays all passed. 6 reloads recovered the stream. Every preview request returned HTTP 200. |
| Network failures and page errors | **0** and **0** |
| Listener growth (gate) | **Passed.** Early and late medians both 257, growth 0, allowance 64. Idle counts were 257, or 211 right after each reload. Counts while streaming without GC were 245–1,225 and were reclaimed. |
| DOM-node growth (gate) | **Passed.** Early median 2,042, late median 2,059, growth +17, allowance 256. Each 5-cycle block repeats the same values: 1,862 to 2,068 at first, then 2,025, 2,059, 2,093, 2,109, and 1,109 after each reload. In v4 the count grew by about 70 nodes per cycle. |
| JS heap (recorded only) | Growth +53 KB against an 8 MiB allowance |
| Run window | At most 11 options in every cycle. Every later cycle's search reached cycle 0's source run. |
| Exports and run closes | 1 SVG and 1 checksum-verified bundle. 7 of 7 runs `closed`. |
| Storage | Acceptance runs 256 MB, endurance runs 2.6 GB (90 runs, about 87 MB per cycle). Control storage 3.01 GB of the 7 GiB cap. Floors held throughout: project disk at least 12.9 GB free, `/tmp` 4.73 GB, `/dev/shm` 7.73 GB. |
| Recording writers | 105 owners: 72 live owners recorded in the background and 33 replay jobs synchronously. 1,997 items written, queue peak 8 of 16, **0 backpressure events**, no errors. |
| Chromium (5 s probe, 709 samples) | `/dev/shm` regions 63–142 MB, RSS 716–1,175 MB (it fell from 1,102 MB to 716 MB over the run), file descriptors 356–376 |
| Shutdown and cleanup | Both servers logged "Application shutdown complete" with no errors (exit -15 is the expected SIGTERM). 152 processes were observed, 0 survivors needed killing, the process group is gone and the storage lease is free. The supervisor completed with exit 0. |

## Abnormal or worth watching

**Late-session cadence drift.** The gates are pooled, and they pass. Individually, 5 of the 30 four-second endurance windows would fail the per-window rule, all because their p99 gap exceeded 70 ms:

| Cycle | Rate | p99 gap |
| --- | --- | --- |
| 18 | 29.74 Hz | 74.9 ms |
| 25 | 29.22 Hz | 73.7 ms |
| 26 | 28.73 Hz | 76.0 ms |
| 27 | 28.53 Hz | 76.7 ms |
| 29 | 29.08 Hz | 79.1 ms |

Four of the five come from the last five cycles, and the pooled p99 of 64.6 ms is within 6 ms of the limit. The recording writer showed no backpressure at all, so the cause is not the writer queue. Candidates I have not tested:
- the storage-budget recount, which walks every file in the runs folder (about 1,400 files by the end) before each write;
- disk latency as the endurance runs folder grows toward 2.6 GB.

A longer session could fail the pooled rule. Profiling this before any longer session is recommended.

## Scope

This is software and browser acceptance of the local lab, using the manual CPU controller and real MuJoCo physics. It makes no claim about FLYNN, male or body-profile browser workflows (their specs did not run in this session), GPU or full-model real-time behaviour, PNG export through the browser (the button is only checked for its disabled state), a fresh documented setup on the integrated candidate, human usability, artistic acceptance or hardware. No qualification claims are made.
