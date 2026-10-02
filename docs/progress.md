# Palimpsest recovery brief

Objective: implement the approved [full plan](implementation-plan.md), R0–R5 and all listed task/art profiles.

Working-set binding: `98d42920e321b42d22c6336f938d2c3ba9fd770d8ba24a2a`. Its MCP tools are not exposed in this session; this file is the recovery fallback, not a claim that the binding was updated.

## Current state

- Implemented: M0/R0 reproduction and M1 execution/recovery. Manual/teacher/FLYNN lifecycle, bounded commands, lossless recording, validated world edits and full snapshots are implemented. Original PRD remains unchanged.
- Partial: M1 branch `feat/execution-recovery` is pushed; evidence/documentation and its stacked draft PR are being finalized. M2 interactive lab contracts have been reviewed; implementation is next. R0 is draft PR #1; neither branch is automatically merged.
- Mechanism: unchanged pinned upstream environment/neural model, allowlisted student inputs, raw-output guards, one owner for mutable runtime state, native MuJoCo snapshot caches plus wrapper/controller/RNG/command state. Branch identity binds the durable source event prefix and teacher reset baseline.
- Missing: M2–M10: interactive lab and replay/export workflow, release hardening, memory experiments, additional tasks, MaleCNS, rover qualification, artwork modes and handoff.
- Known limitation: CUDA CSR inference varies on identical input tensors on this host, even with deterministic algorithms enabled. The strict CUDA continuation case failed; tolerances were not relaxed. Full-model CPU continuation passed. Snapshot compatibility metadata is not a universal repeatability guarantee.
- Unknown: original checkpoint training lineage, full-model Pi performance, viable MaleCNS circuit and physical stopping limits.
- Blocked tasks: physical procurement/qualification requires selected hardware, reviewed cost, components and an operator. No rover components are available. Simulation work can continue.
- Next action: finish M1 evidence/CI and draft PR, then create the stacked M2 branch. Implement validated scenarios/masks, worker/API supervision, UI, three replay modes, sequential branch comparison and exports; test one interruption/two traces end to end.

## Verification

M1: 98 tests passed with actual EGL checks enabled and no skips. Fresh-process manual and teacher continuation passed for 12 ticks; full FLYNN CPU passed for 100 ticks, all compared values identical. CUDA failed first at right-camera values on tick 10 under exact image comparison. A frozen-input CUDA probe isolated varying CSR multiplication while index addition matched across all 30 repetitions. See [M1 evidence](reports/m1-execution.md).

M0: 63 tests passed; CI passed for `0e60603`. Teacher 30/30 goals; FLYNN 28/30 goals, two time limits. All 30 initial states/inputs matched. Reference parity passed on 375 ticks. See [R0 evidence](reports/r0-reproduction.md). These are simulation development results only.

## Git and environment

Repository-local author/committer: Aadrika Maurya <aadrikamaurya@gmail.com>. Fetch URL remains HTTPS; local push URL uses `github.com-shraddha`, whose existing SSH key was verified as Aadrika08. This resolves the OAuth token's missing workflow scope without changing global Git/gh identity. GitHub CI uses CPU fixtures only; real GPU runs are local and separately indexed.

Raw run bundles are ignored by Git under each milestone worktree's `runs/`. Shared model assets remain in `.worktrees/r0-reproduction/data/assets/flynn/`; M1 uses that path explicitly. Python 3.11 environment is in `.venv`; use `uv run --no-sync` or explicitly include `--locked --extra simulation` when syncing. One full model/job at a time.
