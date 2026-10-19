# Manual lab refresh v4: preparation and rehearsal

The v4 session is prepared and registered, and has not been run. The registration is `docs/plans/manual-lab-refresh-v4-registration.json`, 244 pinned sources, with no `launched.json` marker. The protocol is in [manual-lab-refresh-v4.md](../plans/manual-lab-refresh-v4.md). Evidence is in [`manual-lab-refresh-v4-preparation/`](manual-lab-refresh-v4-preparation/).

**Main finding: the real session will probably fail the cadence criterion on this host.** The cause is synchronous recording writes to the nearly full project disk (see "Cadence: decision needed" below). Every functional part of the session passed in both rehearsals.

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

## Cadence: decision needed before the real run

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

**Options (a decision is needed):**
1. **Code:** move the recorder's chunk and event writes off the worker's step and display loop, using a bounded background writer that keeps the same durability and storage checks. Write it test-first, then re-register.
2. **Environment:** free a substantial amount of project-disk space or use faster storage, then rehearse again. Putting the session's runs folder on tmpfs would also need a decision, because evidence would then live in RAM.
3. **Run as is** and accept that the cadence criterion will probably fail.

Any change to the pinned sources makes the current registration invalid. To re-register: delete `docs/plans/manual-lab-refresh-v4-registration.json`, run `--register` again, and commit.

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
