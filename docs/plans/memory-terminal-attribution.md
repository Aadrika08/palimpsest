# Memory terminal attribution implementation plan

> Execute inline with `superpowers:executing-plans`; use one independent source
> review before the single registered diagnostic. The user requested the goal
> and its pursuit; this implements its first bounded, read-only work unit.

**Goal:** Explain the recorded selected exit's absence at the failed local-null
boundary, without rerunning or re-scoring the pilot.

**Architecture:** One evaluator-only script reads the checksum-validated existing
recording, retains the last 64 control poses and corresponding events, and reports
the frozen range/FOV/occlusion predicates and target handoff timing. It never calls
the supervisor, model, Engine or snapshot decoder. Existing scientific source is
read and pinned, never edited. Registration fixes all consumed file hashes first.

**Tech stack:** Python 3.11, stdlib, existing NumPy record reader and storage guard.
**Spec:** [First bounded work unit](simulation-completion-next-goal.md#first-bounded-work-unit).

## Global constraints

- One invocation, 300 seconds including input checks, diagnostic and publication;
  invoke under external `timeout --signal=KILL 300s`. An internal monotonic deadline
  checks progress, with no deadline reset. Zero retries/corrective invocations.
- New publication root: `docs/reports/memory-terminal-attribution-evidence`;
  new runtime/output root: `runs/memory-terminal-attribution-v1`. Aggregate128MiB,
  continuing2GiB free floor and64MiB headroom, inclusive of registration and copies.
- Fixed source pilot registration SHA
  `61b295030e692c580331d5ab282ab380da87e7b7d3718f4e31809238835543a1`;
  close SHA `ca92aaf06a964ec26daf651ff9203fa313039179a3840b66e107a2977699102d`.
- Fixed job `local-null/own`, run `c2ed14671d124705a93616c09cd8985e`, terminal880,
  source audit SHA `49fb72963fc607da5a427cc04dfd5fd4e044b6b72e086853f30a18f5a84d8082`.
- Existing reader may stream all153 rows to validate chunk counts/checksums; retain
  and analyze only the final64 controls (816–879) plus the sensor-only boundary880.
  The extra boundary uses the last recorded `next_pose`, never a predicted pose.
- Matching events are bounded by the recording's32MiB envelope. Exact event
  sequence and packet/pose alignment are validated; no earlier event is analyzed.
- Exact case/profile and event schedule come from the indexed original job and
  independent close. Pin raw recording manifest/events/chunks and job, close,
  source registration, independent audit, and all project Python dependencies.
- Zero native owners, physics steps, fits, SNP decoding, policy replay, held-out
  access or historical score changes. Existing source/output/control roots are
  immutable; hash consumed inputs before and after. Keep bytecode writes disabled.

## Review focus

1. Terminal packets lack a motor row; use `next_pose` at880, not `pose` at879.
2. Exact90-degree FOV and4m range are inclusive; coincident marker bearing is zero.
3. A visible predecessor does not prove successor visibility; report both without
   inserting a private bearing into the controller.
4. First observed selection inside a truncated window may not be first selection
   overall; explicitly label left-censoring and unresolved handoff timing.
5. Bad paths/hashes, duplicate/missing events, exceeded bounds and a consumed output
   refuse success. Report infrastructure failure rather than guessing an attribution.

## Task 1: diagnostic and synthetic validation

Files: create `scripts/memory_terminal_attribution.py` and
`tests/test_memory_terminal_attribution.py`. Preserve all existing runtime files.

- [x] Test `visibility(pose, xy, circles)` with hand-derived inclusive range/FOV,
  behind-camera, occlusion, coincident and nonfinite cases. It returns distance,
  bearing degrees, range/FOV booleans, blocking-circle indices and visible boolean.
- [x] Test `attribute(case, rows, events, target, terminal_tick, event_tick)` on a
  tiny real-format sensor-only terminal fixture with a visible predecessor and
  missing successor. Assert the terminal uses `next_pose`; a wrong packet fails;
  a >64-row window fails; duplicate packet ticks fail.
- [x] Test `verify_files(rows, deadline)` with real temporary files: unsafe paths,
  symlinks and changed bytes fail; valid immutable bytes pass. Test consumed output
  refusal before decoding. These checks must fail before implementation exists.
- [x] Implement the pure visibility decomposition using the existing segment
  distance helper. Cross-check the terminal target's visibility against the actual
  reconstructed sensor packet. Read bridge/arrival events for timing; do not
  reproduce supervisor state or invent a missing first selection.
- [x] Implement one fail-closed registered invocation: exclusive consumed marker,
  existing real-user read-only writer lease, source/input admission, streaming
  reader/deque, before/after hashes, bounded JSON report, failure receipt. Cap all
  control documents at1MiB. No new framework or dependency.
- [x] Run focused tests and the required existing software suite with checkout
  PYTHONPATH, CPU/EGL environment and no native-study opt-ins. Retain actual results.
- [x] Review the full change once; fix material findings with regression checks,
  then commit verified software before diagnostic registration.

## Task 2: one registered offline diagnostic and handoff

- [ ] Build/commit a fresh machine registration with fixed source and consumed
  input hashes, dependency hashes, interpreter/NumPy identity, paths and bounds.
  Metadata/byte checks only before registration; no terminal-record analysis.
- [ ] Invoke once under the exact300s ancestor cap. Retain stdout/stderr, consumed
  marker and result, including failures. No output deletion or retry.
- [ ] Accept result as `attributed`, `multiple-predicates`, or `unresolved`, only
  with complete input integrity and packet alignment. This qualifies a diagnostic
  explanation at the recorded pose, not a controller repair or new scientific pass.
- [ ] Perform independent byte/readout verification without a second diagnostic;
  publish an evidence-linked report, the future nine-condition design proposal,
  and an updated completion checklist. Commit/push through the existing account.

The old pilot retains both900 scores and its false path predicate/composite result.
Any route/profile/controller change or new native study needs a distinct frozen
protocol and allocation. The future design is not an executed study.
