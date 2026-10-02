# Palimpsest recovery brief

Objective: implement the approved [full plan](implementation-plan.md), R0–R5 and all listed task/art profiles.

Working-set binding: `98d42920e321b42d22c6336f938d2c3ba9fd770d8ba24a2a`. Its MCP tools are not exposed in this session; this file is the recovery fallback, not a claim that the binding was updated.

## Current state

- Implemented: M0/R0 reproduction, M1 execution/recovery and M2 interactive lab. Actual input inspection, all six scenarios, live edits, snapshots, sequential branches, three replay modes, comparison and exports passed their implementation gates. Original PRD remains unchanged.
- Partial: M0 and M1 are stacked draft PRs #1 and #2 with CI green; M2 implementation/evidence is committed and pushed as `78e8228` in [draft PR #3](https://github.com/Aadrika08/palimpsest/pull/3); both backend and frontend CI are green at `be25154`. M3/R1 release hardening is active in `.worktrees/lab-hardening` on `feat/lab-hardening`, tracked in [draft PR #4](https://github.com/Aadrika08/palimpsest/pull/4). Pacing, actual-time telemetry, storage budgets, bounded logs, exports, CLI integration and queue/resource cleanup are implemented. No automatic merges.
- Mechanism: unchanged pinned upstream environment/neural model, allowlisted student inputs, raw-output guards, one owner for mutable runtime state, native MuJoCo snapshot caches plus wrapper/controller/RNG/command state. Branch identity binds the durable source event prefix and teacher reset baseline.
- Missing: M3 release qualification; M4–M10 memory experiments, additional tasks, MaleCNS, rover qualification, artwork modes and handoff.
- Known limitation: CUDA CSR inference varies on identical input tensors on this host, even with deterministic algorithms enabled. The strict CUDA continuation case failed; tolerances were not relaxed. Full-model CPU continuation passed. Snapshot compatibility metadata is not a universal repeatability guarantee.
- Unknown: original checkpoint training lineage, full-model Pi performance, viable MaleCNS circuit and physical stopping limits.
- Blocked tasks: physical procurement/qualification requires selected hardware, reviewed cost, components and an operator. No rover components are available. Simulation work can continue.
- Next action: run the frozen-runtime 60-minute mixed manual/teacher/FLYNN endurance gate. Current natural throughput, CLI evaluation, the full actual suite, cached full-model offline setup and the 240-second FLYNN smoke have passed. R1 remains incomplete until those gates are evidenced; the measured 27.98 Hz display rate remains below its labelled 30 Hz target.

## Verification

M2: 145 Python tests passed with actual EGL enabled and no skips. UI build/typecheck and both actual browser workflows passed (24.5 s and 33.8 s). Manual/teacher/full FLYNN CPU owner gates passed; final FLYNN gate covers four identical continuation ticks, a live obstacle edit, both exact executable replays and all three export formats. Separate 30-tick masked full-model continuation passed across fresh processes. All final FLYNN runtime hashes match the final Python files; earlier run identities remain recorded. See [M2 evidence](reports/m2-interactive-lab.md). These checks do not establish release endurance or performance.

M3 final integration at `a24c237`: 193 tests passed with actual EGL enabled and no skips (59.444 s), covering storage/recovery, delayed and truncated IPC, semaphore/feeder cleanup, failed-spawn close and complete-cycle controller coverage. Teacher CLI evaluation completed 30 ticks; UI build and seven measurement checks passed. The durable validation index retains 69 unchanged source/test/configuration hashes and confirms no remaining owned jobs or listener changes. The original PRD hash and pinned upstream are unchanged. See the scoped [M3 evidence draft](reports/m3-release-hardening.md).

M3 qualification remains partial. Current natural throughput passes at `a24c237`: manual 600 ticks at 1.00010826× active RTF and teacher 653 at 1.00030542×; outer rates remain 0.99557347× and 0.98877306×. Earlier natural-completion throughput passed on `dc911f3`: manual 600 ticks at 1.000869x active RTF and teacher 653 at 1.000590x, with clean exits. Earlier failed and incomplete performance reports remain retained; the operator-pause protocol is distinct. Current `ec1d2e6` browser evidence passes four workflows (including overlay isolation and keyboard recovery), all four close responses and clean PID-only SIGTERM without semaphore warnings. Acknowledgement p95 is 43.4 ms; application p95 is 53.8 ms. Full-window display updates are 27.9809 Hz, below the 30 Hz target. Profiling tied recurring gaps to synchronous publication; inventory traversal was improved without caching or weakening durability. The original 927.6 ms browser acknowledgement outlier did not recur and its precise cause remains unproven.

The complete offline gate passed at `ec1d2e6` in 213.994 s: fresh cached Python/Node setup, five recorded full-FLYNN CPU runs with exact continuation and both executable replays, and three CLI/API/WebSocket smoke cycles. It ran inside an isolated network namespace without changing host networking; no owned survivors or semaphore warnings remained. The 240-second CPU FLYNN smoke at `19787f7` completed two full cycles and four successful replays, with 1.421 GiB sampled peak RSS, one sampled owner and clean shutdown. Its short-burst RTF was 0.707–0.718; no full-model real-time claim is made. Only the 60-minute mixed gate and final release-status review remain pending for M3. No complete R1 claim is made.

M1: 98 tests passed with actual EGL checks enabled and no skips. Fresh-process manual and teacher continuation passed for 12 ticks; full FLYNN CPU passed for 100 ticks, all compared values identical. CUDA failed first at right-camera values on tick 10 under exact image comparison. A frozen-input CUDA probe isolated varying CSR multiplication while index addition matched across all 30 repetitions. See [M1 evidence](reports/m1-execution.md).

M0: 63 tests passed; CI passed for `0e60603`. Teacher 30/30 goals; FLYNN 28/30 goals, two time limits. All 30 initial states/inputs matched. Reference parity passed on 375 ticks. See [R0 evidence](reports/r0-reproduction.md). These are simulation development results only.

## Git and environment

Repository-local author/committer: Aadrika Maurya <aadrikamaurya@gmail.com>. Fetch URL remains HTTPS; local push URL uses `github.com-shraddha`, whose existing SSH key was verified as Aadrika08. This resolves the OAuth token's missing workflow scope without changing global Git/gh identity. GitHub CI uses CPU fixtures only; real GPU runs are local and separately indexed.

Raw run bundles are ignored by Git under each milestone worktree's `runs/`. Shared model assets remain in `.worktrees/r0-reproduction/data/assets/flynn/`; M1 uses that path explicitly. Python 3.11 environment is in `.venv`; use `uv run --no-sync` or explicitly include `--locked --extra simulation` when syncing. One full model/job at a time.
