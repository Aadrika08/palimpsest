# Manual lab refresh v5: preparation and rehearsal

The v5 session is prepared, registered and has not been launched. The branch `verify/manual-lab-refresh-v5` is based on v4 at `c3107ec`, which stays unchanged. The protocol is [manual-lab-refresh-v5.md](../plans/manual-lab-refresh-v5.md). Evidence is in [`manual-lab-refresh-v5-preparation/`](manual-lab-refresh-v5-preparation/).

## DOM growth: cause and fix

**Cause.** I counted DOM nodes after each action with garbage collection forced. Every recorded run added about 45 nodes (Chromium's `Nodes` counter), as one option in each of three selects (Recorded run, Left run, Right run). Every captured snapshot added one option to the Snapshot select. In the v4 session, each endurance cycle added 3 runs and 3 snapshots, which explains the steady growth of about 70 nodes per cycle (1,816 to 2,953).

**Fix** (`ui/src/run-window.ts`, commits `11d171f`, `600f471`, `3ca9e1f`):
- The run and snapshot selects show at most 10 entries each.
- The runs that are currently selected always appear. After them come this tab's recent runs, newest first; these are kept in `sessionStorage` so they survive a reload, and if storage fails the page still works without them.
- A **Find run** search over run id, controller and scenario reaches any run. It also filters the snapshot list and both comparison selects. A short note shows how many runs are hidden.
- No capability is removed: every run stays selectable through search.

**Why 10.** A window of 20 kept growing for about 7 cycles, which the early-third versus late-third gate could read as growth. A window of 10 fills up within about 3 cycles.

**Checks.**
- `npm run test:run-window` covers the bound, the selected runs, the recent ordering, unknown ids, and search reaching each of 90 runs and the snapshots. It failed first with the module absent (`run-window-red.log`).
- The endurance spec checks every cycle that the Recorded run select has at most 11 options (10 plus the placeholder). From the second cycle on, it searches for cycle 0's source run and requires it to be listed.

## A UI race found and fixed during rehearsal

Rehearsal 2 failed one acceptance test: the replay-job test got HTTP 409 (`rehearsal-2-busy-race-worker.json`).

**What happened.** The page has one shared "busy" flag that disables its buttons. Close run was still in flight when the test chose a Recorded run. That fast selection finished first and cleared the flag. Action replay was then clicked while the run was still closing, and the server refused it.

**Fix** (`ui/src/busy.ts`; commits `1a527ca` with the failing test, `337b230` with the fix). The page now counts operations in flight and clears the busy flag only when all of them have finished. `npm run test:busy` failed first (`busy-red.log`). The race was already in the code; this run was the first time it showed up. The v4 runs passed this test five times.

## v5 runner (`scripts/manual_lab_refresh_v5.py`, commit `d8f5e3f`)

The runner is a copy of v4's, which is left untouched. It adds three things.

**1. A DOM-node gate.** Idle DOM nodes after forced garbage collection are gated with the same rule shape as listeners. The median of the last third of cycles may exceed the median of the first third by at most max(256, 10% of the first-third median), over at least 3 cycles. Reasons for 256:
- After the fix, the rehearsal's idle counts were 1862, 1965, 2068, 2108, 1109, 2025, 2059, 2093, 2109 and 1109 (each reload resets to about 1,109). The counts level off at about 2,100. Even this short 10-cycle rehearsal, which includes the ramp-up, shows only +128.
- Over 30 cycles each third contains the same pattern of a reload every 5 cycles, so the expected difference is close to 0.
- v4's growth of about 70 nodes per cycle would show as about +790 at 17 cycles and about +1,400 at 30 cycles, far above 256.
- 256 is roughly what 6 more listed runs would add, so a return of unbounded lists is caught quickly.

**2. A heartbeat file.** The runner atomically writes `.superpowers/sdd/manual-lab-refresh-v5/progress.json` at each phase change and at least every 5 s while a child process runs. It records phase, status, update time (UTC), elapsed seconds, endurance cycles completed and expected, free space on `/tmp`, `/dev/shm` and the project disk, and the process id. The launcher writes `starting`, then `published` with the final status. The heartbeat never blocks or gates the session.

**3. A detached launcher.** `detached_command()` builds a transient systemd user unit:
- no terminal and stdin set to null;
- an explicit `PATH` (Node 24.21.0, `/usr/bin`, `/bin`), plus `PYTHONPATH`, `TMPDIR` and `PYTHONDONTWRITEBYTECODE`;
- `flock -w 300` on the shared lock, then the registered outer `timeout`.

The registration records this exact command. Software tests: 22 pass (`tests/test_manual_lab_refresh_v5.py`); the 5 new ones failed first (`runner-red.log`).

## Rehearsal 3: run detached through systemd, passed every gate

It ran through `systemd-run --user`, using the same argument shape with `--rehearse 300 30`, so 10 cycles of 30 s. It took 358 s and the heartbeat ended `passed` (`rehearsal-3-detached-worker.json`, `rehearsal-3-progress.json`).

| Gate | Result |
| --- | --- |
| Acceptance tests | 8 of 8 passed, none skipped or flaky |
| Measured cadence (8 s) | 29.93 Hz, p50 gap 33.1 ms, p99 gap 45.4 ms, acknowledgement p95 24.9 ms |
| Endurance cadence (10 windows pooled) | 29.85 Hz, p50 gap 32.8 ms, p99 gap 53.9 ms, acknowledgement p95 24.3 ms |
| Endurance cycles | 10 of 10; replays passed; 2 reloads recovered |
| Network failures and page errors | 0 and 0 |
| Listener growth | Passed, +0 (idle counts 257, with 211 after each reload) |
| DOM-node growth (new) | Passed, +128 against an allowance of 256 |
| Run window | At most 11 options; search reached cycle 0's source run in every later cycle |
| Exports and run closes | Passed |

Recording writers: 32 owners recorded in the background and 13 replay owners recorded synchronously; 865 items; queue peak 16 of 16. There were 5 backpressure events totalling 0.23 s and no errors. This is the first backpressure seen, from brief disk stalls; cadence was unaffected.

## Real session (not launched)

Root starts it from the worktree with a clean tree, no `ui/dist`, no `ui/test-results`, and no other heavy jobs running:

```sh
systemd-run --user --unit=palimpsest-lab-v5 --collect --working-directory=/home/utkarsh/Work/shraddha/brain/.worktrees/manual-lab-refresh-v5 --property=StandardInput=null --setenv=PATH=/home/utkarsh/.local/share/mise/installs/node/24.21.0/bin:/usr/bin:/bin --setenv=PYTHONPATH=src:scripts --setenv=TMPDIR=/tmp --setenv=PYTHONDONTWRITEBYTECODE=1 /usr/bin/flock -w 300 /tmp/palimpsest-software-tests.lock timeout --signal=TERM --kill-after=10s 5970s /home/utkarsh/Work/shraddha/brain/.venv/bin/python -B /home/utkarsh/Work/shraddha/brain/.worktrees/manual-lab-refresh-v5/scripts/manual_lab_refresh_v5.py --launch
```

To follow it:
- `cat /home/utkarsh/Work/shraddha/brain/.worktrees/manual-lab-refresh-v5/.superpowers/sdd/manual-lab-refresh-v5/progress.json`
- `systemctl --user status palimpsest-lab-v5`
- `journalctl --user -u palimpsest-lab-v5 -f`

Expected duration is about 63–65 minutes; the hard limit is the outer TERM at 5970 s. Expected storage is about 2.8–3.0 GB. Launch requires at least 10 GiB free on the project disk; it currently has about 13.1 GiB. `/tmp` must stay at least 2 GiB free and `/dev/shm` at least 1 GiB.

## v4's local phase folder

v4's `.superpowers/sdd/manual-lab-refresh-v4` is 2.1 GB and ignored by git. It is almost all recording chunks of uncompressed camera arrays. A sample 6.3 MB chunk compressed with `zstd -3` to 0.40 MB, about 16 times smaller, so a `tar --zstd` archive would be roughly 150 MB. I did not compress, move or delete it.
