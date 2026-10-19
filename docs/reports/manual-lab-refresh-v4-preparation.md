# Manual lab refresh v4: preparation and rehearsal

The v4 session is prepared and registered, and has not been run. The registration is `docs/plans/manual-lab-refresh-v4-registration.json`, 244 pinned sources, with no `launched.json` marker. The protocol is in [manual-lab-refresh-v4.md](../plans/manual-lab-refresh-v4.md). Evidence is in [`manual-lab-refresh-v4-preparation/`](manual-lab-refresh-v4-preparation/).

**Status: the session is ready to run.** The first two rehearsals failed only the cadence criterion, because recording writes were made synchronously to the nearly full project disk. You chose to fix this in code. Live lab owners now record through a bounded background writer (see "Background recording writer" below). The third rehearsal, run after that fix, **passed every check**, including cadence, with the runs folder still on the project disk.

## Rehearsals

Both rehearsals ran the complete worker and its judging, but with a 300 s endurance window made of 60 s cycles: `--rehearse 300 60`. Rehearsal 2 took 374 s from start to finish.

| Check | Rehearsal 1 | Rehearsal 2 |
| --- | --- | --- |
| Preflight (versions, free space, `test:browser-shm`) | Passed | Passed |
| 8 acceptance tests | 7 passed; the measured cadence test failed | 7 passed; the measured cadence test failed |
| Measured cadence (8 s window) | 28.79 Hz, p99 75.2 ms, ack p95 59.9 ms: **failed** | 29.16 Hz, p99 76.5 ms, ack p95 32.6 ms: **failed** |
| Endurance | Not run: this rehearsal stopped after the acceptance failure, which led to the fix in `5088b12` | 5 of 5 cycles; action and policy replays all passed; 1 reload recovered; 0 network failures; 0 page errors |
| Endurance cadence (pooled) | — | 25.37 Hz, p99 137.5 ms, ack p95 172.8 ms: **failed** |
| Listener growth | — | Passed. Idle counts after forced GC: 256, 256, 257, 254, 210. Counts while streaming, without GC: 284 to 1104. |
| SVG and bundle exports; owner closes | Passed | Passed (7 closes, all `closed`) |
| Cleanup | 0 survivors | 0 survivors (83 processes observed) |

The functional workflow passed in both rehearsals: inspection, snapshot, branches including the goal edit, comparison, action and policy replay, SVG and bundle export, WebSocket disconnect and reload recovery, and the memory inspector. Only cadence failed.

## Listener growth: not a leak

The growth reported earlier (from about 4,400 to 7,700 listeners) was garbage that had not yet been collected.

I streamed one run to 600 ticks and sampled the page with and without a forced GC (`HeapProfiler.collectGarbage`).
- **Without GC**, the count rose to 1,520 and then fell back as garbage collection ran.
- **After a forced GC**, it went only from 213 to 240 over the run. That growth tracks the live DOM, which went from 259 to 394 elements as rows were added. It stayed at 240 when the run was idle.

The endurance rehearsal agrees: the idle post-GC count stayed flat across cycles (256, 256, 257, 254, 210; the 210 follows a page reload). The v4 rule fails only growth that is not reclaimed, so it guards against a future leak without flagging this.

## Cadence: diagnosis (before the fix)

**Symptom.** The delivered display stream has periodic stalls.

**Spacing.** In rehearsal 1, the gaps over 50 ms were spaced 640, 636, 2570, 625, 678, 1260 and 637 ms apart. These are multiples of about 640 ms, which is 32 ticks at 50 Hz: the recorder's `CHUNK_TICKS`.

**What happens every 32 ticks.** The worker writes about 6.3 MB of camera arrays (`.npz`) and calls fsync, inside the same loop that emits display samples. Every recorded event is also fsynced.

**Write cost.** I timed writing one 6.3 MB `.npz` and fsyncing it, 20 times:

| Location | p50 | p90 | max |
| --- | --- | --- | --- |
| Project disk (btrfs, about 97% used) | 27 ms | 291 ms | 309 ms |
| `/dev/shm` | 5.3 ms | 6.4 ms | 6.9 ms |

**Same test, different storage** (`cadence-by-runs-storage.json`). I ran the measured cadence test 6 times with the lab's runs folder on each storage. Nothing else changed.

| Runs folder on | Mean rate | p99 gap | ack p95 | Passed |
| --- | --- | --- | --- | --- |
| Project disk | 26.04–29.66 Hz | 63.8–66.3 ms | 31–82 ms | 5 of 6 |
| `/dev/shm` | 29.91–30.04 Hz | 45.1–53.7 ms | 18–33 ms | 6 of 6 |

The project-disk p99 sits just under the 70 ms limit. In the full rehearsals the measured test ran fifth in the suite, and it crossed the limit both times (75–76 ms). During endurance, the project disk also accumulates more data each cycle.

**Options presented** (the chosen option was 1):
1. **Code:** move the recorder's chunk and event writes off the worker's step and display loop, using a bounded background writer that keeps the same durability and storage checks. Write it test-first, then re-register.
2. **Environment:** free a substantial amount of project-disk space or use faster storage, then rehearse again. Putting the session's runs folder on tmpfs would also need a decision, because evidence would then live in RAM.
3. **Run as is** and accept that the cadence criterion will probably fail.

Any change to the pinned sources makes the current registration invalid. To re-register: delete `docs/plans/manual-lab-refresh-v4-registration.json`, run `--register` again, and commit.

## Background recording writer (the chosen fix)

| Commit | What it is |
| --- | --- |
| `8a683a2` | Failing tests, written first |
| `579fc44` | The implementation |

The new method is `RunWriter.start_background()` in `src/palimpsest/records.py`.

**What moved to the background, and what did not.** The caller still validates every record, assigns its sequence number, stages the `.npz` chunk, hashes it and checks quotas. One first-in-first-out thread only writes the chunk files and event lines and fsyncs them. Because of that split, the published bytes are identical to the synchronous path.

**Durability.** The data is fully on disk before a run counts as closed:
- `flush` (which snapshots use), `finish` and `close` all wait for the queue to empty.
- The terminal manifest is written only after every chunk and event is durable.

**Kill behaviour.** A killed process keeps a valid published prefix of the recording. That prefix can be shorter than before by at most the items still queued: up to 16, and 0 to 8 were observed.

**Quotas.** Bytes that are queued but not yet written count against both the writer quota and the storage budget.

**Backpressure.** When the queue (16 items) is full, the caller blocks instead of using more memory. These events are counted, with the time spent blocked.

**Errors.** The first write error stops all later writes and fails the next writer call. The engine then fails the run, and the published prefix stays valid.

**Who uses it.** Only the live lab owner turns it on (`worker.py`, right after `Engine.open`). Replay jobs, campaign and held-episode workers, evaluation, and every other `RunWriter` user stay synchronous and unchanged. Those paths have frozen registrations or no display cadence to protect, and their per-event durability timing is part of what they have already reviewed and recorded.

**Statistics.** Each owner's writer statistics (`recording_writer`: mode, items written, high-water mark, backpressure count and seconds, error) reach its run view and its `supervisor.json`.

**Bug found while testing.** The caller's temporary-file cleanup could delete a chunk file that the writer thread was still publishing. A deterministic test reproduced it (`FileNotFoundError` on rename), and it is fixed.

**Proof of identical bytes.** `tests/test_records_background.py::test_recording_is_byte_identical_to_the_synchronous_path` runs the same fixed schedule through both paths: events, 70 ticks in episode 0, an explicit flush, 5 ticks in episode 1, then finish. Every file comes out byte-identical (manifest, `events.jsonl` and every chunk).

A full-engine comparison is not possible on either path. The recordings contain wall-clock latency fields (`latency`, `step_latency`), so even two synchronous runs differ. The writer is the only component that changed how bytes are produced.

### Tests

- **`tests/test_records_background.py`:** 8 tests. Before the implementation, 7 failed (`background-writer-red.log`); the race test was added later and failed until the cleanup fix.
  - identical bytes;
  - the caller does not wait on fsync, and flush drains;
  - the race above;
  - the bounded queue and its backpressure count;
  - errors fail the run and keep the prefix;
  - quotas and the storage budget count queued bytes;
  - a process killed with SIGKILL leaves a valid published prefix that is a whole number of chunks;
  - the synchronous default is unchanged.
- **`tests/test_lab.py`:** an opt-in test runs a real live owner through 33 steps and a snapshot. It checks background mode, no error, an empty queue at close, the persisted `supervisor.json` and 33 published ticks. Before the change it failed with `KeyError recording_writer` (`live-owner-red.log`). With `PALIMPSEST_SIMULATION_TESTS=1`, all 20 `test_lab` tests pass.
- **`tests/test_recovery.py`:** a background write failure fails the engine run, keeps a 32-tick prefix and leaves no temporary files.

**Full canonical suite** (`scripts/run_tests.sh`, `full-suite-summary.log`):
- Pass 1: 5,975 passed, 304 skipped and 18 failed.
- The isolated, process and tmpfs passes: 7 + 5 + 31 all passed.

All 18 failures are puck bootstrap tests that raise "Collection root or ancestor changed while held", or tests near them. That guard holds every ancestor directory from `/` downward and fails if any of their timestamps change. In this worktree that includes the shared `.worktrees` directory, which other sessions keep changing, so the failing set changes from run to run: 45 failures on the first run, which also hit stray bytecode I had created myself and since removed; 18 on the second; and 64 when I re-ran just those files.

Run from a quiet location (`puck-flake-comparison.log`), the same 9 files gave the same result at this branch's head as at `main` `5456b33`: 1 failed and 232 passed, and the one failure is the same test (`test_authored03_completes_after_real_failed01_02_without_changing_their_bytes`). So these failures come from the environment, not from this branch.

The 304 skips are opt-in tests (including the new live-owner test) plus historical frozen-pin cases. Archived evidence is unaffected. Historical registrations that pin `src/palimpsest/*.py` (now including the changed `records.py`, `worker.py` and `lab.py`) report as historical under the existing frozen-pin policy. No test failed because of a pin mismatch.

### Cadence on the project disk after the fix

**Measured 8 s test, 6 runs** (`cadence-after-background-writer.json`): all 6 passed, at 29.77–30.28 Hz. The p99 gap was 45.0–47.0 ms and acknowledgement p95 was 20–27 ms. Before the fix the same disk gave 26.0–29.7 Hz with a p99 gap of 63.8–66.3 ms.

**Rehearsal 3** (`--rehearse 300 60`, 371 s, `rehearsal-3-background-writer-worker.json`) **passed every check:**

| Check | Result |
| --- | --- |
| Acceptance tests | 8 of 8 passed, including the enforced cadence test |
| Measured cadence | 29.92 Hz, p99 gap 45.1 ms, acknowledgement p95 24.6 ms |
| Endurance cadence (pooled) | 29.58 Hz, p99 gap 56.0 ms, acknowledgement p95 20.9 ms |
| Endurance cycles | 5 of 5 |
| Listener growth | Passed; idle post-GC counts 256, 256, 256, 256, 210 |
| Failures | 0 network failures, 0 page errors |
| Exports and run closes | Passed |

Across the 22 live owners in this rehearsal, every one used the background writer. Together they wrote 581 items, with a queue high-water mark of 8 of 16, 0 backpressure events and no errors. The 8 replay jobs stayed synchronous.

## Expected duration and resources for the real session

**Duration:** about 63–65 minutes.

| Part | Time |
| --- | --- |
| Preflight, selection and build | about 10 s |
| Acceptance suite | about 75–85 s |
| Endurance (30 cycles of 120 s) | 3600 s plus about 15 s |
| Publication | under 1 min |

The hard limit is the outer TERM at 5970 s.

**Storage:**

| Item | Size |
| --- | --- |
| Acceptance runs | about 250 MB |
| Endurance runs | about 82 MB per cycle, so about 2.5 GB in total (managed cap 4 GiB) |
| Control total | about 2.8 GB (cap 7 GiB) |
| Published evidence | a few MB; runs and exports are not copied |

**Free space and memory:**
- The project disk has 14.7 GiB free now. The session needs at least 10 GiB at launch and refuses to continue below 4 GiB.
- `/tmp` has 4.8 GB free (floor 2 GiB). The session does not write to it.
- `/dev/shm` has 7.4 GiB free (floor 1 GiB). Chromium uses about 80–120 MB there.
- Chromium uses about 1.1–1.2 GB RSS and about 360 file descriptors. The resource probe samples every 5 s, capped at 4 MiB.

## Exact command for the real run (not executed)

Run this from `/home/utkarsh/Work/shraddha/brain/.worktrees/manual-lab-refresh-v4` with a clean tree, no `ui/dist` and no `ui/test-results`. Serialize it against other simulation and native jobs.

```sh
PYTHONPATH=src:scripts flock /tmp/palimpsest-software-tests.lock \
  timeout --signal=TERM --kill-after=10s 5970s \
  /home/utkarsh/Work/shraddha/brain/.venv/bin/python -B scripts/manual_lab_refresh_v4.py --launch
```

The command consumes the allocation once, and there is no retry. Qualification claims remain empty.
