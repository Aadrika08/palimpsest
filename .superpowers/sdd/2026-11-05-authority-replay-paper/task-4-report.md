# Task 4: matched semantic overhead study

Status: implementation and fixture/static verification complete; full CPU FLYNN execution is deliberately pending the orchestrator's serialized dry run. No scientific campaign or overhead result was produced.

## Scope and behavior

Created only `paper/studies/authority_replay_v1/overhead.py`, `null_writer.py`, and `tests/test_overhead.py`. Production engine, records, replay and other study drivers were not modified by this task.

The execution driver expands frozen seeds 0--9 in cyclic condition order. Every condition starts a fresh child process; the actual production Engine still computes policy, sensors, cameras, physics, statistics and actions. Its RunWriter constructor is replaced only inside the benchmark process to select null, synchronous, background, or background plus actual StorageBudget accounting. The null sink creates only an empty events file for the production application's outside-timing snapshot boundary and never provides replay data.

Twenty warm-up ticks and a writer drain precede 200 measured ticks and their final writer drain. Open time is separate. Each timed tick submits the same deterministic command ID, then calls actual Engine.advance. Timing rows initially remain ineligible. Only four completed conditions with the same action digest, 220 tick count and scientific final-state digest become eligible; all four rows are preserved on mismatch. The digest excludes recorder source ID/event prefix and process-global RNG; it retains native state, integration state, environment, policy/recurrent state, observation and remaining authoritative application state. Finite JSON metrics are enforced.

Policy and physics timings use existing Engine.last_transition values. Camera timing wraps the instance's actual `_render_camera` call, delegates it unchanged and remains nested in physics; these components must not be added as independent costs. Resource samples are collected after warm-up and every 20 measured ticks; wall time includes this uniform instrumentation. Bytes/tick is the measured recording-byte delta divided by 200, rather than total startup bytes. Storage recount seconds/count include both unit and aggregate campaign budgets. Existing background backpressure counters are differenced across the measured window.

Operation cost accepts only an explicit completed Task 3 replay row with same seed/current campaign identity, background_storage provenance, background writer, actual storage accounting, prefix8/source100. It uses the exact prefix snapshot and source owner path. It records restore/first-tick, capture, save, read, validated tick-stream playback, action replay and policy replay separately. Playback here means parsing/validating all stored ticks without policy/physics/rendering; the raw operation scope is explicit. Production replay requires a fresh UUID owner directory and a passed replay report. Owners run sequentially. The source owner tree and source row hash are retained and the owner tree must remain unchanged.

## Resource and CLI contracts

The planned execution CLI is supported, including `--kind execution --protocol ... --assets ... --output ...`. Operation costs use `--kind operation --sources REPLAY_ROOT`, whose inputs are `seed-{seed}/row.json`. `--self-check` verifies the frozen protocol without loading a model.

Both drivers accept `--campaign-root` and `--campaign-deadline-epoch`. Aggregate bytes count the shared raw campaign root. `campaign-clock.json` persists identity/started_unix/deadline_unix; an explicit deadline can shorten, never extend, the stored deadline. Each child timeout is min(900 seconds, remaining global deadline). The four-hour deadline persists across invocations. All unit outcomes remain accounted for; hard caps/timeout/admission failures stop subsequent execution, retaining incomplete descriptors. CLI success requires completed eligible rows.

Background-storage and operation-cost paths use actual unit512MiB/campaign8GiB budgets with6GiB reserve, 250ms conservative recount intervals, and16MiB concurrent metadata/log headroom. Synchronous/background execution writer limits are480MiB. Each native stdout/stderr is capped at1MiB in the parent, with overflow terminating/refusing the unit. Parent100ms output monitoring is a stop check, not a strict pre-write bound. Fixed protocol scope is not reduced to fit resources. No page-cache flushing occurs. Original assets are read-only inputs.

## Verification evidence

- Initial RED: `task-4-red.log`: collection fails because overhead implementation does not exist. Tests already specified the four-condition action/tick/final digest gate, cyclic order, writer dispatch, finite values, exact220 ticks, null lifecycle and operation source separation.
- Focused final fixture verification:18 passed in `task-4-fixture-green.log`. Includes all four actual production writer implementations on a fake deterministic runtime with220 ticks each, exact windows, matched outputs, source provenance, failed-condition whole-seed exclusion, persisted deadline non-extension and refusal before process launch for expired deadlines.
- Production recording/replay regression slice:40 passed,4 skipped in `task-4-regressions.log`; skipped tests require actual full model runtime and remain unverified here. Command: `PYTHONPATH=src /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -m pytest -q tests/test_records.py tests/test_records_background.py tests/test_replay.py paper/studies/authority_replay_v1/tests/test_overhead.py --basetemp=runs/task4-final-regressions-c`.
- CLI static check passed: `task-4-selfcheck.log`; no model executed.
- Initialized upstream gitlink verified as `8d964599119b420de67ee259434d273651a1a76d`.
- Temporary final verification files are under ignored `runs/task4-*`.

## Footprint preflight and limitations

The actual sparse-navigation profile uses128x128 RGB. Engine records four cameras (raw and effective, two eyes), and RunWriter uses uncompressed NPZ. The camera-only payload is196,608 bytes/tick. Execution's30 full-writer conditions x220 ticks imply1,297,612,800 bytes =1.2085GiB before other arrays/events; ten null conditions write no camera payload. Continuation's10x(108 source+100 restored)=2080 ticks add0.3809GiB. Replay uses5x(100 source+92 branch+100 action+100 policy)=1960 ticks, adding0.3589GiB. Operation costs add5x(1 capture-owner+100 actions+100 policy)=1005 ticks, adding0.1840GiB. Combined camera-only floor is about2.132GiB.

This is not a full campaign total: snapshots, array metadata, events, retained native logs, fault trajectories, the approximately413MiB shared fault runtime base and D2 copied assets, and offline reproduction remain additional. Offline has its fixed2GiB cap. The floor exposes no execution-only infeasibility; actual aggregate storage and free-space admission remain mandatory. No camera data, tick counts or conditions were omitted to fit the cap.

Main limitations: full FLYNN dry validation and scientific matching/performance are pending. Native state digest stability across actual processes, actual camera wrapper availability, full operation source/replay compatibility and actual storage cost are not established by fixture evidence. Root must serialize the actual runtime dry run after Task2. Fixture success is implementation evidence, not repeatability or performance evidence.

## Review fix round 1

The review found two important correctness gaps and one timing-reporting omission. The earlier description of RNG exclusion is superseded: `_final_digest` now retains the entire captured seeded RNG state, including environment, spaces, Python, NumPy and Torch. Only recorder source-run/event-prefix identity is normalized. Five regression variants change a single RNG field without changing actions/ticks/other state; each now excludes the entire seed.

Successful child exit is no longer sufficient for resource acceptance. After exit, native-log drain/close and result parsing, the parent rechecks unit bytes, aggregate campaign bytes, free-space reserve, elapsed unit timeout and absolute campaign deadline. This covers a child that exits between monitor polls. Byte/reserve failures retain a `resource_limit` code (`unit_bytes`, `campaign_bytes`, `free_space`); the campaign stops later execution while preserving all remaining incomplete descriptors. An additional campaign-level fixture verifies that the first cap failure launches only one of the40 declared units and retains all40 rows. The raw worker-result file remains retained when final acceptance fails.

`close_seconds` now records Engine.close separately; the20+200 tick steady-state wall definition is unchanged and excludes open and close.

Observed RED: `task-4-review-red.log` has11 failures/17 passes: missing close metric, five RNG variants incorrectly matching, and five fast-child resource/deadline boundaries incorrectly completing. After the changes, focused verification passed28 tests (`task-4-review-green.log`); one additional full-campaign stop-accounting fixture was then included. Final focused verification passed29 tests (`task-4-review-final-focused.log`). Final production recording/replay regression slice passed51 tests with4 existing full-model skips (`task-4-review-regressions.log`), using `--basetemp=runs/task4-review-regressions`. No full model or scientific campaign ran in this round.
