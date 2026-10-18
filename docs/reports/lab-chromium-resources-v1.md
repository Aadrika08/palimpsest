# Lab Chromium resources v1: the v3 `ERR_INSUFFICIENT_RESOURCES` failure

This was a diagnostic and fix run on branch `fix/lab-chromium-resources-v1`, off `0473641`. It is not the formal manual acceptance session.
Evidence is in [`lab-chromium-resources-v1/`](lab-chromium-resources-v1/). Every attempt is listed in `attempts.json`, and `attempt.sh` holds the exact command.

## Result

Manual lab refresh v3 failed because Chromium's shared memory lived in `/tmp`, and `/tmp` was nearly full of other workloads' data. Neither the lab UI nor the server leaks resources.

- **How shared memory reached `/tmp`.** Playwright launches Chromium with `--disable-dev-shm-usage` by default. That flag moves all of Chromium's shared memory from `/dev/shm` into `TMPDIR`, which is `/tmp` here. This includes the data pipe behind every fetch response body.
- **Why that matters.** On this host `/tmp` is the 7.5 GiB tmpfs that campaigns and test suites write to. `/dev/shm` is a separate tmpfs that nothing else uses (28 MiB used).
- **What fails.** When `/tmp` has only a few MiB free, Chromium cannot allocate a data pipe. The fetch then fails with `net::ERR_INSUFFICIENT_RESOURCES`, which the page sees as `TypeError: Failed to fetch`, and no HTTP response arrives. The page itself survives.

The fix is in `ui/playwright.config.ts`: `launchOptions.ignoreDefaultArgs: ['--disable-dev-shm-usage']`. Chromium then keeps its shared memory on `/dev/shm`. This raises no limit and adds no retry.

## Evidence

### What the v3 trace rules out

The v3 page made 73 requests in total. The largest response was about 17 KB. The WebSocket carried 905 KB over 8.7 s. The failing POST (`1-trace.network:69`) failed after 9 ms. A `close` POST from the same page succeeded 0.4 s later.

So this was not request-count, socket or body-size exhaustion. It was a short-lived allocation failure.

### Same binary as v3

`/usr/lib/chromium/chromium` has sha256 `27c398e1…a95e97c5d243ff`, the same value v3 pinned. Its version is Chromium 152.0.7977.82 (Arch Linux). Playwright is 1.63.0. The built UI is `index-DP8Vou6b.js`, identical to v3's build.

### Normal runs: no leak in our code

Before the fix, the v3 workflow passed 3 of 3 times (`base1`–`base3`).

| Resource | Peak, roughly flat |
| --- | --- |
| Chromium shared memory mapped in `/tmp` | 101–123 MB across 300–400 regions |
| File descriptors | about 365 |
| Sockets | about 108 |
| In-flight requests | at most 3 |

A full 600-tick streaming run (`diag90`) sent a preview pair every 5 s. Shared memory stayed flat at a peak of 81 MB, and no request failed.

I also held 20 unread preview response bodies (`pins-chromium-resources.json`). `TMPDIR` free space changed by 0 bytes. Leaving bodies unread is therefore not a factor.

### Reproduced exactly by exhausting `TMPDIR`

These runs used a private tmpfs as `TMPDIR` (`unshare` plus `mount`), so the host `/tmp` was never filled.

| Free space in `TMPDIR` | Result |
| --- | --- |
| 1.28 MB | The first fetch failed with `net::ERR_INSUFFICIENT_RESOURCES` / `Failed to fetch`. The page survived. After the filler file was deleted, the next round returned `[200, 200]`. |
| 3.1 MB | `[200, "TypeError: Failed to fetch"]`: the first preview succeeded and the second failed, the same shape as v3. |
| 4.4 MB and 17 MB | No failure. |

When the whole `TMPDIR` was only 64–96 MiB, the renderer crashed during the workflow. With 104 or 128 MiB, the workflow passed.

### `/tmp` was under pressure when v3 ran

The original session log records `/tmp` at 79% used, with 1,696,083,968 bytes available, at 16:29:40Z. That was 2 min 35 s before the failure at 16:32:23.707Z. A pytest run that started at 16:38 then failed the 2 GiB tmpfs free-space floor (`full-suite-tmpfs-floor-failure.log`). Concurrent agents were running memory and artwork work at the same time.

The exact free space at 16:32:23 was not retained, and the host rebooted on 2026-10-16. This is the one link that is inferred rather than observed.

## Fix and tests

| Commit | Change | Check |
| --- | --- | --- |
| `3a748b6` | RED: `ui/tests/browser-shm.check.ts` (`npm run test:browser-shm`), the probe `scripts/lab_chromium_resource_probe.py`, and the opt-in diagnostic `ui/tests/chromium-resources.spec.ts` | Failed: 26 regions under `/tmp/.org.chromium.Chromium.*` (`browser-shm-check-red.log`; the RED commit message says 50+, which counted the duplicated assertion output) |
| `caad85b` | `ui/playwright.config.ts` adds `ignoreDefaultArgs: ['--disable-dev-shm-usage']` | Passed: 26 regions, all on `/dev/shm` |

Other checks after the fix:

- **Full Playwright suite** against a fresh lab server: 7 passed and 5 skipped (all opt-in). See `browser-suite-postfix.log`.
- **UI checks:** `npm run typecheck`, `npm run build`, `npm run test:measurement`, `npm run test:memory` and `npm run test:browser-shm` all pass.
- **Python tests:** `scripts/run_tests.sh -- tests/test_lab.py tests/test_manual_lab_refresh_v2.py tests/test_manual_lab_refresh_v3.py tests/test_requirements_evidence.py tests/test_cli.py` gives 39 passed and 2 skipped.

## Real-browser verification after the fix

| Attempt | Condition | Result |
| --- | --- | --- |
| `fill1m-fixed` | `TMPDIR` left with 1.8 MB free | Previews `[200, 200]`; no network failures |
| `verify-normal` | v3 workflow, normal `/tmp` | Passed in 11.5 s |
| `verify-tmp48m` | v3 workflow, whole `TMPDIR` only 48 MiB | Passed in 12.4 s; before the fix, 64–96 MiB crashed the renderer |
| `verify-long` | 549 ticks with preview pairs every 5 s, including one round with `TMPDIR` left 1.8 MB free | Then captured a paused snapshot, ran two branches (the second with a goal edit), compared them, played back the recording and exported an SVG. 0 network failures; passed in 21.6 s |

## Browser preflight facts (2026-10-19)

**Browsers present:**
- `/usr/bin/chromium`: Chromium 152.0.7977.82, Arch Linux. The wrapper adds Omarchy flags from `~/.config/chromium-flags.conf`.
- `/usr/bin/brave`: Brave 155.1.97.57.
- Playwright Chrome for Testing builds: `chromium-1228` (149.0.7827.55), `chromium-1234` (151.0.7922.34) and `chromium-1243` (153.0.8010.12), each with a matching headless shell.
- No Firefox.
- The "0 browsers" result from the 15 October preflight came from the agent tool's own inventory, not from this host.

**Physical display:** `eDP-1`, 1920×1080 at 144.003 Hz.

**Measured cadence** (`perf1-ui-performance.json`, Chromium headless, 8.03 s window):

| Measure | Value |
| --- | --- |
| Samples arriving at the page | 238 (29.65 Hz) |
| DOM updates | 238 (29.65 Hz) |
| Animation-frame opportunities | 60.05 Hz |
| Gap between arriving samples | p50 32.9 ms, p95 44.5 ms, p99 64.5 ms |
| Command acknowledgement | p95 27.9 ms |

**The 30 Hz shortfall.** Both v3's 27.98 Hz and today's 29.65 Hz measure how often samples arrive from our pipeline, not the display refresh rate. The worker schedules display samples at exactly 1/30 s (`worker.py`, `next_display + 1/30`). Both the worker's display queue and the WebSocket stream keep only the newest sample, so any delivery jitter drops one. That is why the p99 gap is 64.5 ms. The browser offered frames at about 60 Hz and the screen runs at 144 Hz.

So the shortfall is in our design, not an environment limit. Fixing it needs a decision: either emit above 30 Hz or define the target with a tolerance. It was not changed here.

## Remaining for formal manual lab refresh v4

- **Use the fixed config.** Run with `ui/playwright.config.ts` from `caad85b` and run `npm run test:browser-shm` as a preflight. Also record `/tmp` and `/dev/shm` free space in the preflight.
- **Full workflow under approved, serialized resources.** That means inspection, snapshot, branches, comparison, action/policy replay, export, interruption/disconnect recovery and endurance. Endurance should include the 60-minute mixed operation with forced-GC readings.
- **Check one possible UI leak.** The page's `JSEventListeners` count grows while a run streams: about 4,400 to 7,700 between ticks 290 and 550, falling to 560 after the run stops. It is not related to this failure.
- **Decide the 30 Hz cadence target**, as described above.
- **Manual-run scripts.** `manual_lab_refresh_v2.py`/`v3.py` still budget only project-disk storage. v4 should add the browser's shared-memory filesystem to its preflight.
