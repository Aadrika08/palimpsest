# M3 / R1 hardening evidence — incomplete

**R1 is not qualified.** The current 193-test suite and natural-completion manual/teacher benchmark pass within the scopes below. Four current browser workflow assertions, command acknowledgement and clean service shutdown pass. Display cadence is **27.98 Hz**, below the labelled 30 Hz target. Fresh-cached offline setup and short full-FLYNN CPU functionality also pass. A 240-second CPU FLYNN mixed-operation smoke also passes within the small sample limits below. Current-runtime natural throughput, final CLI checks and the 193-test suite pass. The 60-minute mixed-operation gate remains open.

This draft records evidence through final validation source `a24c2379716bf21f1d497896e25a1227f8de5c49` on 2026-10-02, including supervisor cleanup committed as `a0828f5fb4dd1a8a60535e81b47b1a3a4cba0d7b`. Natural performance and browser v1 used `dc911f32c68b7507e3b0c917309f5e31fb00f903`, whose runtime matched implementation `f0638861b4c5cc830a613fe1a8aaf55d19621368`. Later browser instrumentation, storage traversal and shutdown changes are identified separately; their performance is not inferred from earlier runs. [The JSON index](m3-release-hardening.json) records measured runtime hashes, small raw-report hashes, source identities, requirement limits and pending checks.

## Retained checks

The [final validation index](../../runs/m3-validation-20261002/report.json) records **193 tests passed, no skips, in 59.444 seconds**, with `PALIMPSEST_SIMULATION_TESTS=1`, EGL and two OpenMP threads. All 69 tracked source/test/script/UI/configuration hashes and HEAD `a24c237` match before and after validation. The teacher CLI separately completed its bounded 30-tick evaluation, and the Node 24.21.0 build and seven full-window measurement checks passed. No matching owner/server/verifier processes, listener changes or resource-tracker warnings remained. FLYNN unit coverage uses a small real upstream recurrent fixture; separate full-model offline/smoke evidence is retained below.

The earlier results retain their original narrower scopes:

An earlier retained full suite reports **191 tests passed, no skips, in 55.739 seconds** in `/tmp/palimpsest-m3-post-resource-full-suite.log`, including actual EGL tests, the storage traversal change and uncommitted supervisor resource cleanup. Parent orchestration confirms that scope. The subsequently added guard against joining a never-started process and its new test are **not** covered by that result. A retained focused run of the failed-spawn, semaphore-release and unread-feeder checks passes **3 tests in 1.701 seconds** in `/tmp/palimpsest-m3-final-shutdown-focused.log`, before their commit as `a0828f5`. That earlier result does not cover the later guard; the final 193-test result above does.

The earlier full suite reported **188 tests passed, no skips, in 56.889 seconds** in `/tmp/palimpsest-m3-post-queue-full-suite.log` on runtime `f063886`. Both logs retain individual test names and results but no embedded source manifest; source attribution comes from orchestration. Current `lab.py` is not hashed as though unchanged from the 191-test run. These local temporary logs are hashed in the index, not bundled into this commit. An additional reported five-test metadata check has no retained log and is not counted here.

Coverage includes lifecycle and invalid-output guards, student input allowlists, all six registered scenarios, actual owner snapshot/branch/disconnect, actual manual executable replay with masks/edits/reset and inherited commands, comparison/export integrity, and actual MuJoCo continuation across contact/recovery and terminal boundaries. FLYNN coverage within this suite uses a small real upstream recurrent fixture. The separate offline gate below provides current full-graph CPU functional evidence.

Storage and recovery checks cover aggregate quota and free-space preflight, initial-snapshot/count limits, temporary-file overlap, exclusive publication, overlapping writer scopes, bounded native/Python logs, and preservation of a published 32-tick prefix after abrupt or failed publication. The Engine recorder disk-failure test uses fixture physics; separate actual MuJoCo and snapshot-publication tests cover their stated boundaries. These scopes are not interchangeable.

Three shutdown/IPC regressions pass in this suite: final native-log fsync failure cannot become successful completion; a final large display frame is drained after authoritative completion; and an abruptly truncated multiprocessing frame becomes an explicit owner failure rather than hanging the monitor. The later suite also verifies release of all 20 named semaphores for a cached owner before interpreter exit and bounded exit of a feeder with unread commands. The current browser v2 gate also verifies whole-service PID-only SIGTERM shutdown without semaphore warnings or escalation.

## Manual and teacher performance

The [current-runtime natural-completion gate](../../runs/m3-performance-final-20261002/report.json) passed on unchanged `a24c237`: manual **600 ticks / 1.00010826× active RTF**, teacher **653 ticks / 1.00030542×**. Outer rates including request/poll/reset time are **0.99557347× / 0.98877306×**, respectively. Both recordings close cleanly with contiguous 20 ms ticks; the verifier took 38.8159 seconds. These are narrow margins on this host, not general real-time guarantees. The separate historical result below remains unchanged.

[`m3-performance-natural-20261002b/report.json`](../../runs/m3-performance-natural-20261002b/report.json) passes the declared worker-active real-time threshold on its recorded runtime and host. It uses actual spawned owners, CPU manual/teacher controllers, the sparse-navigation/checker profile and EGL. After at least 600 ticks, each controller runs until a natural episode ending; it is not the earlier operator-pause protocol.

| Controller | Recorded ticks | Worker-active RTF | Outer RTF | Outcome |
|---|---:|---:|---:|---|
| Manual | 600 | 1.0008689635 | 0.9982323007 | Time-limit truncation; default zero action |
| Privileged teacher | 653 | 1.0005898722 | 0.9884186194 | Three goal terminations: 266, 191 and 196 ticks |

Worker-active time excludes loading and pauses. Outer time includes the run request, inter-episode resets and polling, and remains below 1× for both controllers. The narrow active margin does not establish universal real-time performance. Kernel-only RTF (4.6462 manual, 2.5057 teacher) excludes IPC, recording and display and is not the release metric. Loading took 4.8614 and 4.4187 seconds respectively; the whole verifier took 37.5861 seconds.

Manual zero-action execution measures the workload, not navigation success. The teacher has privileged geometry and is not an equal-information student baseline. The 341/371 observed transport samples are not browser frames. Raw `pre_close_observations` are explicitly unqualified copied telemetry; accepted metrics are the `controllers` results after close and integrity validation. Both recordings have completed manifests, distinct ending phases, and closed supervisor reports.

The measured software includes Python 3.11.15, MuJoCo 3.3.6, NumPy 2.2.5 and PyTorch 2.9.0 on Linux. Diagnostics detected an RTX 4050 Laptop GPU, but these controllers ran on CPU. Default full-model assets were absent in this worktree, so its recorded `doctor.ready` was false. This benchmark does not qualify full-FLYNN assets, inference or offline use.

All earlier performance artifacts are retained, including failures and the incomplete attempt:

| Raw report directory under `runs/` | Recorded result | Interpretation |
|---|---|---|
| `m3-performance-600ticks-20261002` | `running` | Incomplete artifact; no terminal result, source commit or controller measurements retained |
| `m3-performance-startup-failure-20261002` | Failed | `ModuleNotFoundError: palimpsest.storage`; constructor/startup failure, no performance result |
| `m3-performance-600-20261002` | Failed | Legacy operator-pause protocol; active RTF 0.962678533 manual / 0.946869781 teacher |
| `m3-performance-600-20261002b` | Failed | Same legacy protocol; manual 1.000032464 passes, teacher 0.998744993 fails |
| `m3-performance-natural-20261002` | Failed | Manual reached 600 ticks, then `CloseTimeout`; no qualified controller result and no teacher measurement |
| `m3-performance-natural-20261002b` | Passed | Natural completion, recorded pre-storage/cleanup runtime; limits and outer timing above apply |

The failed natural attempt's copied telemetry is not promoted to a performance result. Its shutdown failure motivated the queue fixes and regression tests. Source commits and verifier hashes are preserved in the index; no failed report was rewritten after a fix. The natural and operator-pause protocols answer different timing questions and are not interchangeable repetitions.

## Browser and offline status

The latest [browser v2 index](../../runs/m3-ui-evidence/20261002T080624Z/final-verification.json) records all four workflow assertions passing on unchanged source `ec1d2e6`, after the storage and shutdown fixes. Action and policy replay each match 256 ticks; a separate action replay cancels after 67 ticks. Every workflow asserts its final owner close response is HTTP 200 with status `closed`.

Across the complete **8,041.2 ms** window, 225 sample arrivals and DOM commits measure **27.9809 Hz**, below the 30 Hz target. The 220 after-commit animation callbacks measure 27.3591 Hz; 472 general callback opportunities measure 58.6977 Hz and are neither fresh-data updates nor physical scanout. Raw timestamps are retained: the arrival channel has 4.3 ms leading and 9.5 ms trailing gaps, with a largest internal gap of 202.8 ms. The M3 contract requires the target to be measured and an unmet result labelled; this report does not call 27.98 Hz a 30 Hz pass.

The **12 command acknowledgements pass**, with nearest-rank **p95 43.4 ms** against below 150 ms. Observed application p95 is separately **53.8 ms**. Worker-active RTF is **0.98749** (8.9 simulated seconds / 9.0128 active seconds) in this browser run with pause cycles. It is not the natural-completion throughput protocol, whose current-runtime result is reported separately above.

PID-only SIGTERM exits the server in **0.2005 seconds**, with shell status 143, no escalation, zero stderr bytes, no semaphore warning, no matching Python processes and no port listener. This supports clean shutdown in this measured workflow. It does not substitute for full-model performance or endurance gates.

The earlier v1 failure and profiling run remain separate evidence:

The retained [browser v1 index](../../runs/m3-ui-evidence/20261002T074408Z/final-verification.json) records four passed assertions on unchanged source `dc911f3`: manual lifecycle/intervention/branch/export, executable replay/disconnect/reload/export, trajectory input isolation with keyboard/error recovery, and instrumentation. Action and policy replay each matched 257 ticks; a separate action replay cancelled explicitly after 32 ticks. Instrumentation assertions passing does not mean the performance targets passed.

The declared 8,035.7 ms window contains **148 arrivals, or 18.4178 Hz over the full window**. The raw meter's **26.6401 Hz** uses only the 5,518 ms span between its first and last arrivals. Raw arrival timestamps were not persisted in v1, so the remaining 2,517.7 ms cannot be assigned to the start, end or internal coverage gaps. There were 148 DOM commits and 144 after-commit animation callbacks; these callbacks are not physical scanout. Both cadence measures miss the 30 FPS target.

Across 12 commands, nearest-rank command-receipt **p95 is 927.6 ms**, failing the below-150 ms target; observed application **p95 is 1,020.4 ms**. Receipt timing includes browser fetch and response-body parsing, excludes loading, and remains distinct from authoritative application delivery. Recorded worker-active RTF in this browser run is 0.6465; the passing headless benchmark does not override it. PID-only SIGTERM exited 143 without KILL escalation and left no matching server/spawn processes, but warned of **160 tracked semaphores**. The test awaited the final close request without asserting its status, so this is not clean shutdown qualification.

The later [instrumented diagnostic](../../runs/m3-ui-profile-20261002/diagnosis.json) is **not qualification**. It measured 27.4863 arrivals/s over its full window, receipt p95 63.1 ms and application p95 87.5 ms; the original long acknowledgement did not reproduce. Repeated 88–138 ms display gaps overlapped synchronous durable publication, whose 14 calls above 20 ms totalled 1.2305 seconds, including 0.6923 seconds in quota checks. Instrumentation and approximate clock alignment limit causal interpretation; this does not retrospectively establish the cause of the original delay.

A [stdlib inventory microbenchmark](../../runs/m3-inventory-microbenchmark-20261002/report.json) motivated storage change `7778c4e`. With warm filesystem metadata and alternating old/new order, fresh recount medians on the 140-file UI roots fell from 9.1355 to 3.2370 ms (30 repetitions); a separate 400-file synthetic tree fell from 116.7300 to 35.8063 ms (20 repetitions). It exercised no renderer, simulation, lease or browser. No end-to-end speedup or target pass follows. Browser v2 retains raw timestamps and separates full-window from interarrival rates. Its actual result is reported above; a component-only microbenchmark cannot establish how much of that change it caused.

The current [full offline index](../../runs/m3-offline-full-20261002/offline-index.json) passes in **213.9938 seconds** on unchanged source `ec1d2e6`. A fresh local shared checkout and pinned upstream `8d9645` are prepared from caches, then locked offline Python simulation/lab dependencies, pinned Node 24.21.0, offline npm install and the UI build complete. Every recorded phase command returns zero.

Inside a mapped user-owned network namespace, only loopback is available; external IPv4 and IPv6 probes return `ENETUNREACH`. All **40 observed descendants** retain isolation and host namespace identities remain unchanged. Sub-100 ms processes may evade periodic observation, so the report also retains exact phase commands. Existing cached Git/Python/Node/package objects and the shared verified asset root remain prerequisites; this is offline operation with cached resources.

The actual **full-FLYNN CPU functional verifier passes in 149.1145 seconds**: a four-tick prefix and four-tick continuation, zero maximum continuation error, action and policy replays each matching **8 ticks and 22 events**, and SVG/PNG/bundle exports. Five recorded runs cover the source, exact continuation branch, exploratory live-intervention branch and two replays. The interval includes sequential model loading and is not an inference-latency or real-time measurement. No prescribed direction or size of behavioral effect is claimed for the intervention.

The fresh-checkout CLI HTTP/WebSocket manual/teacher smoke separately passes **55.0001 seconds and three mixed-operation cycles**. It is explicitly a short smoke, with no late-window growth result. Cleanup requires no survivor killing; 38 retained logs contain no `resource_tracker` warning. The API server exits with SIGTERM status −15. No CUDA, browser-30-Hz, hour-long endurance or physical qualification follows.

The earlier [`m3-cached-setup-20261002a/report.json`](../../runs/m3-cached-setup-20261002a/report.json) remains a separate **setup-only** pass in 7.8532 seconds on source `6c54e11b9b9fee50d87ea83cbfe1e2efe7ca0907`. Its configured `duration: 55` was not a live 55-second session. The newer gate supplies actual offline runtime evidence without rewriting that earlier result. See [the runbook](lab-hardening-runbook.md) for isolation, retention and reproduction commands.

## 240-second CPU FLYNN mixed smoke

The [smoke report](../../runs/m3-flynn-smoke-20261002/report.json) passes **240.0001 wall-clock seconds and two mixed-operation cycles** on unchanged source `19787f7`, through the actual loopback HTTP/authenticated WebSocket service. This is not 240 seconds of continuous inference: eight paused-completed recordings contain only **56 ticks / 1.12 simulated seconds**, including 18 action-replay ticks that bypass inference. The other 38 ticks comprise 18 source, two branch and 18 policy-replay ticks. All four executable replay reports pass nine ticks each; paused completion does not mean navigation success.

[Controller metrics](../../runs/m3-flynn-smoke-20261002/controller-metrics.json) separate the execution modes. These kernel rates exclude loading, API/IPC and recording:

| Category | Ticks | Mean policy time | Policy p95 | Kernel RTF |
|---|---:|---:|---:|---:|
| Source FLYNN | 18 | 13.1666 ms | 15.3844 ms | 1.1859 |
| Branch FLYNN | 2 | 16.6978 ms | 16.8845 ms | 0.3231 |
| Policy replay | 18 | 12.9156 ms | 16.0347 ms | 1.3502 |
| Action replay | 18 | Inference bypassed | Inference bypassed | 11.6023 |

The raw report's pooled kernel RTF of 1.5447 includes those inference-bypassing action ticks and is **not FLYNN throughput**. Two small run-request-to-observed-pause bursts, including IPC/polling, measure **0.7177× and 0.7066×**. Full-model real-time performance is not qualified. Receipt p95 is 21.713 ms over 16 requests; observed application p95 is separately 107.181 ms.

Across 48 periodic resource samples, observed peaks are 1,525,854,208 summed RSS bytes, 92 file descriptors, 16 threads and 22,745,509 output-root bytes; at most one owner is observed. These meet this smoke's configured bounds. The short-smoke late-growth gate is `null`, not passed, despite retaining finite server-growth measurements. Server SIGTERM exits with status −15 and no owned survivors require killing. This supports bounded mixed functionality and a small CPU inference sample, not hour-long endurance or a continuous workload guarantee.

## Requirements-to-evidence matrix

“Test-backed” records the scoped checks available now; it does not mean the entire release is qualified. Current browser evidence and final release gates remain separate from historical M2 results.

| Requirement | Current assessment | Evidence and limit |
|---|---|---|
| LAB-001: local/offline launch | Test-backed | Current fresh-cached setup, full-CPU-FLYNN verification and manual/teacher CLI API smoke pass inside isolated networking |
| LAB-002: validated manifests | Test-backed | Actual six-scenario and explicit controller-replacement tests; registered profiles only |
| LAB-003: run/pause/reset/stop/step | Test-backed | Exact tick boundaries, stale/idempotent commands, bounded queues and actual owner checks |
| LAB-004: distinct endings | Test-backed | Actual goal/time-limit results; stop, runtime failure and late diagnostic failure remain distinct |
| LAB-005: intervention application | Test-backed | Schema/revision/queue checks, actual world edits and retained browser workflow |
| LAB-006: aligned world/input panels | Test-backed | Aligned browser workflows and acknowledgement pass; 27.98 Hz display remains below the labelled 30 Hz target |
| LAB-007: three controller paths | Test-backed | Current offline paths and 240-second CPU FLYNN mixed smoke pass; 38 inference ticks and small burst/kernel timing limits remain explicit |
| LAB-008: privileged-state isolation | Test-backed | Input allowlist, invalid schema and masks; teacher privilege explicitly retained |
| LAB-009: authoritative recording | Test-backed | Lossless fields, events/configuration, integrity, quotas and published-prefix recovery |
| LAB-010: full snapshots | Test-backed | Actual contact/recovery/endings tests and current full-FLYNN CPU four-tick exact branch continuation |
| LAB-011: distinct replay modes | Test-backed | Current browser manual replays plus offline full-FLYNN actions/policy replay of 8 ticks/22 events each |
| LAB-012: sequential comparisons | Test-backed | Provenance before trace interpretation; no causal claim from exploratory branches |
| LAB-013: route/bundle export | Test-backed | Recorded world-coordinate projection, snapshot registration hashes, exclusive and bounded publication |
| LAB-014: disconnect/failure recovery | Test-backed | Disconnect/watchdogs, partial IPC, semaphore/feeder checks and current clean PID-only service shutdown pass |
| LAB-015: invalid-output diagnostics | Test-backed | NaN/infinity/shape guards, timeouts, recorder faults and final-log-fsync failure |
| LAB-016: headless evaluation/doctor | Test-backed | CLI bounds/diagnostic tests, fresh offline CLI launch/API smoke and headless full-FLYNN verification; current teacher CLI 30-tick evaluation also passes |
| ART-001: actual trace/input isolation | Test-backed | Recorded projection tests and retained actual browser overlay/input-isolation workflow on source `ec1d2e6` |

## Qualification boundaries and next gates

The original PRD is unchanged: SHA-256 `4ce71144b2ce3b72b5f7318e0d357ee0f13efb20302befe9482650318d2352db`. Upstream remains pinned to `8d964599119b420de67ee259434d273651a1a76d`. This draft hashes small reports and runtime files; it does not rescan large model assets or recordings. Model files retain their original licences and provenance limits.

[M2's retained report](m2-interactive-lab.md) contains actual browser workflows, full-FLYNN CPU action/policy replay, exports and exact 30-tick masked fresh-process continuation on its recorded sources. Those results remain historical; current M3 full-model functionality is supported separately by the new offline gate. The comparison boundary is `atol=rtol=1e-6` for floating values and exact cameras/integers, with fixed 20 ms control ticks. CUDA repeatability remains unqualified following the [M1 sparse-CSR variation and strict-continuation failure](m1-execution.md).

The remaining release work is concrete:

- Complete the frozen-runtime 60-minute mixed-operation gate with declared RSS/FD/thread/storage bounds, retained diagnostics and clean process shutdown.
- Finish the release-status review after the hour gate. Keep the measured 27.98 Hz display limitation and earlier failures/scoped checks visible.

No memory learning, new navigation competence, topology result, original checkpoint training lineage or physical capability follows from these checks. Hardware remains blocked and unqualified; it is not a prerequisite for R1. The [M3 contract](../plans/m3-release-hardening.md) remains open until its final gates have retained evidence.
