# M6 puck mechanics v1 — failed at the positive teacher

The one approved ten-owner gate at source
`056088634e58d8c40876d17eee87e0af430bce3d` **failed** on the fourth owner.
The zero-control and opposite constant-push checks passed. The positive analytical
teacher completed 600 ticks with `time_limit`, without reaching the unchanged
puck goal. The remaining six owners were not started. No retry, threshold change,
controller edit, teacher-data collection or training followed this execution.

| Planned owner | Actual ticks | Result |
| --- | ---: | --- |
| zero, seed 5990 | 120 | Passed; maximum puck XY displacement 0 m; no rover-puck contact |
| push-positive, seed 5991 | 120 | Passed; final X displacement +0.6572949964 m; 63 contact intervals |
| push-negative, seed 5992 | 120 | Passed; final X displacement −0.6571574766 m; 61 contact intervals |
| teacher-positive, seed 5993 | 600 | Failed; `time_limit`, final goal distance 1.1762439580 m, maximum displacement 0.0261412006 m |
| teacher-negative, seed 5994 | 0 | Not started |
| continue-tick1 | 0 | Not started |
| continue-contact | 0 | Not started |
| continue-dwell | 0 | Not started |
| replay-actions | 0 | Not started |
| replay-policy | 0 | Not started |

The positive teacher's four intended-contact intervals ended at completed ticks
113, 118, 121 and 127. It never acquired a qualifying dwell tick. Its initial,
tick-1 and first-contact native snapshots are retained; no dwell snapshot exists.
The first-contact boundary is exactly completed tick 113. None of the subsequent
native continuation or replay owners ran, so this execution supplies no such
qualification. Constant pushes are mechanics checks, not learned capability or
physical-robot evidence.

Outer supervision ended with exit 1 after **19.415051557 s**; the inner verifier
recorded **19.202254718 s**. The three short owners exited 0; the teacher exited 1
because strict natural-task acceptance failed. Its 600-tick numeric recording
finished normally. There was no startup/progress timeout, forced signal, sampler
error, surviving observed process, callback leak or renderer leak. Both parent
finalization-error lists were empty. All four model identities and 80 source
hashes remained unchanged. Six independently sampled PID/start identities and
all four owner process groups were absent at terminal audit. The exclusive native
slot was explicitly released before the read-only audits.

The primary directory is
`runs/m6-puck-mechanics-v1-20261003/`. The retained launcher and plan are under
`runs/m6-puck-mechanics-v1-prepared/`; the original unlaunched wrapper is retained
there too. The [JSON index](m6-puck-mechanics-v1.json) binds their exact hashes,
all ten statuses, four recordings, six snapshots, containment receipts, source
identity and both independent audit artifacts. Primary report hashes are:

- Inner: `f5e2ade8a2997f3ce657cd70a3848ded253bbd55575db968e3e2a360930bf4ad`.
- Outer: `0f6cf23adb8c600a05d86471de98f41f3ea21a5f794f4e0cf0ca6431f761a636`.

A separate retained NumPy-only audit checked **960 raw rows**, 80 sources and 73
indexed files totaling **119,691,075 bytes** in 2.620 s. It independently rebuilt
all eight inputs, every fixed/teacher action, controls, current-qpos world,
raw-contact interpretations, rewards and task transitions. All matched exactly.
It checked camera dtypes/shapes, finite arrays, zero applied external forces,
source snapshot hashes and first-boundary selection without importing MuJoCo or
Torch or deserializing native state. The original frozen task/model source was
not changed by the audit.

Root's separate audit also passed its retained-evidence checks in 2.487 s, with
the mechanics result still **failed**. Its first audit completed the checks but
failed JSON serialization of NumPy integer counters; the original script and
partial report remain retained. The correction changed only count serialization
and serialize-before-open. This was an audit-output correction, not a native
rerun or change to the primary failure. All four root audit artifact hashes are
in the index.

The retained trace identifies the teacher's target-selection problem. All tick
numbers below are **zero-based action indices**, not completed snapshot ticks.
The frozen teacher selects the goal direction only when within .08 m of a point
.55 m behind the puck. Otherwise it aims at that approach point; the wider
`.35–.63 m` axial / `≤.06 m` lateral push corridor affects velocity selection only
after the heading test.

| Action tick | Behind-point distance | Axial / lateral distance | Chosen action |
| --- | ---: | ---: | --- |
| 105 | 0.058478 m | 0.493579 / 0.015375 m | `[.2, −.018748]` |
| 109 | 0.084294 m | 0.467421 / 0.016919 m | `[0, −.4]` |
| 110 | 0.090491 m | 0.461176 / 0.017290 m | `[0, −.4]` |

At tick 109 the rover remains inside the declared push corridor, and its heading
error relative to the goal direction is only −0.033319 rad, inside the .12 rad
alignment bound. Crossing the approach-point radius nevertheless changes the
selected heading error to −2.972831 rad and commands a turn away. First contact
occurs later, at the end of action tick 112, while residual motion remains.

The teacher issued **65 moving commands and 535 turn-only commands**. Forward
velocity is zero for every action from tick 109 through 599. Later the selected
target alternates across the .08 m approach boundary while yaw remains near
−1.5 rad. In 269 recorded states it selects the behind point despite being inside
the declared push corridor. The frozen stall rule also behaves as specified:
turn-only commands have zero forward velocity and therefore do not accumulate
the forward-command stall counter. The run terminates at the unchanged time
limit. This establishes a concrete target-selection defect in this trace; it does
not establish that any proposed correction will complete the task.
