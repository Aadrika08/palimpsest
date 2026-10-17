# Source review 04: preparation03 and extended-clock epoch 14

**Range:** `8f3a138..f05bd69` (PR #177). **Reviewer:** separate read-only review
agent. **Verdict: APPROVE**, with no Critical findings.

The user chose to raise the qualification time limit after runtime11 hit its 180s
deadline during `import mujoco`, with guard logic unchanged.

## Confirmed

- **Worker deadline.** It may only be set through `deadline_seconds`, on a v3
  registration with policy v5, and only to exactly the integer 360. Any other
  value, type or registration version is refused.
  - The dependency namespace accepts only 180 or 360. Every caller other than the
    worker keeps 180.
  - The parent adds the field only for v14, and the auditor requires it to be
    exactly 360 for v14 and absent otherwise.
  - Guard checks are unchanged.
- **Clock ordering for epoch 14:**
  - Worker: about 370s (parent start + 10 + 360).
  - Parent: child-hard 375, hard 390.
  - Observer: normal 400, hard 415.
  - Outer wrapper: at least 440 (set by the procedure).

  All other epochs keep 180/190/200 and 210/225. No old epoch gains time.
- **Preparation binding is exact:**
  - Preparation03 (v13) and epoch 14 bind each other only: a v13 prior, auditor
    `6292b550…` and identical sources.
  - Epochs 10/11 refuse preparation03, and epoch 14 refuses preparation01/02.
  - Preparation02 audits stay pinned to the retained auditor `04192a3b…`; the
    test copy is byte-identical.
- **Timing estimate.** Mujoco should take about 20–25s guarded, putting the end of
  the four imports at about 180s and the full allocation at about 200–215s
  against 360s. This is an extrapolation: the post-import steps have never run
  under the guard.

## Required procedure deltas (Important)

1. **Preparation03 tools.** Retarget the preparation02 tools to 03 (paths, stage,
   output). `check_audit` must expect audit v13, allocation 13 and auditor
   `6292b550…`. The configuration is preparation01's with kind/version/id 13, the
   `-03` stage and the 24 sources at `f05bd69`. **The synthetic acceptance proof
   must build epoch 14** (`QUALIFY14_LIMITS`, the 32-name roster, candidate D).
2. **Epoch-14 run controls.**
   - Configuration: v14 limits, preparation03 acceptance, and the `-03` stage
     with boot and identity guards.
   - Observer wrapper of at least 440s.
   - Assertions: parent elapsed < 360, transport < 400, registration
     `deadline_seconds: 360`, per-import seconds < 360. The audit wrapper stays 130s.
3. **Keep preparation02's stage.** Projected after preparation03: about 5.0 GB
   tmpfs and about 6.1 GB RAM free, above both floors.

**Reviewer runs:** 1,090 unit cases passed (3 flakes or basetemp cases passed on
rerun) and 6 integration cases passed.
