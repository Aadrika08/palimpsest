# M6 puck mechanics v2 — failed at the lateral-corridor transition

The one approved v2 mechanics run at
`d65d5fea4a0a881bb0eb6ebc1de7a496c675d1d0` **failed**. The positive analytical
teacher reached the unchanged 600-tick limit without reaching the puck goal.
No thresholds, controller code or limits changed after this execution, and no
retry or downstream stage ran. The [v1 failure](m6-puck-mechanics-v1.md) and all
its raw artifacts remain unchanged.

| Planned owner | Actual ticks | Result |
| --- | ---: | --- |
| zero, seed 5990 | 120 | Passed; zero puck XY displacement and no rover-puck contact |
| push-positive, seed 5991 | 120 | Passed; +0.6572949964 m final X displacement with actual contact |
| push-negative, seed 5992 | 120 | Passed; −0.6571574766 m final X displacement with actual contact |
| teacher-positive, seed 5993 | 600 | Failed; `time_limit`, 0.8086486549 m final goal distance, 0.3940011924 m maximum displacement |
| teacher-negative, seed 5994 | 0 | Not started |
| continue-tick1 | 0 | Not started |
| continue-contact | 0 | Not started |
| continue-dwell | 0 | Not started |
| replay-actions | 0 | Not started |
| replay-policy | 0 | Not started |

The positive teacher had 59 intended-contact intervals, first at completed tick
112. It retained initial, completed-tick-1 and first-contact native snapshots;
there was no qualifying dwell tick or dwell snapshot. Its final goal distance
remained above .2 m, and its maximum displacement remained below .5 m. The
recording completed normally with the actual `time_limit` task reason. The owner
then exited 1 because strict task acceptance failed, not because of a runtime or
watchdog exception. The six later owners and every teacher-data/training stage
remained closed.

Outer supervision ended with exit 1 after **18.210479692 s**, and the inner
verifier recorded **17.962151818 s**. All callbacks and retired/current renderers
closed. Source and full model hashes remained unchanged. No forced signal,
sampler error, survivor or finalization error was reported. All six observed
PID/start identities and four owner groups were independently absent. The native
slot was explicitly released at terminal before read-only audits.

The [JSON index](m6-puck-mechanics-v2.json) binds the source/protocol/control hashes,
all ten statuses, raw recordings, snapshots and independent audit artifacts. Raw
output is `runs/m6-puck-mechanics-v2-20261003/`; preparation/audit files are under
`runs/m6-puck-mechanics-v2-prepared/`. Primary report hashes are:

- Inner: `ac14f445d161e876a4b0d065ca516755ac153df6f219f0daa10b8e910062f69b`.
- Outer: `a57c89c9c54f8a3a18c222ad54454bc93289d6bf5eda63be4ca5ded1e99e8a80`.

A separate NumPy-only audit verified **960 raw rows**, **81 source hashes**, six
snapshots and **73 indexed files / 119,701,251 bytes** in 2.483 s. It independently
reconstructed all inputs, commands, controls, contact meanings, rewards and task
transitions exactly, without MuJoCo/Torch imports or native-state deserialization.
Root's independent audit passed the same retained-evidence checks in 2.470 s.
Both audit results preserve **mechanics failed**; they are integrity checks, not
successful task qualification.

The v1 correction behaved as specified: action tick 109 now keeps the goal
heading while inside the push corridor. V2 produced 117 moving commands and
483 turn-only commands. Its next discontinuity occurs when lateral error crosses
the unchanged .06 m corridor boundary. The following ticks are **zero-based
action indices**, distinct from completed snapshot ticks:

| Action tick | Axial / lateral position | Goal heading error | Selected target/error | Command |
| --- | ---: | ---: | --- | --- |
| 160 | .446066 / .059479 m | +.013887 rad | goal, +.013887 rad | `[.2, +.013887]` |
| 161 | .445896 / .060461 m | +.014362 rad | behind point, −2.601063 rad | `[0, −.4]` |
| 187 | .446138 / .060303 m | +.664676 rad | behind point, −1.950876 rad | `[0, −.4]` |
| 188 | .446497 / .058616 m | +.698028 rad | goal, +.698028 rad | `[0, +.4]` |

At tick 161, the goal heading is still inside the .12 rad alignment tolerance,
but a sub-millimetre crossing of the lateral boundary replaces a nearly-forward
target with a point behind the rover. By tick 188 the rover has re-entered the
corridor, but its yaw is −.650630 rad; choosing the goal target reverses the turn
command. Target selection then alternates around the same boundary. The trace
has 66 contiguous target/motion ranges, and **every action from 161 through 599
has zero forward velocity**. The unchanged forward-command stall rule therefore
does not accumulate a stall, and the time limit ends the episode.

This is an observed discontinuity in geometric target selection and recovery,
not a contact rejection: no other-robot or puck-wall contact was recorded, and
maximum intended-contact penetration was .000435239 m, within the .02 m bound.
The analysis does not establish that a proposed recovery controller will solve
the task. Any further controller version requires a separately reviewed design,
source freeze and finite gate; there is no continuation/replay, learned-control,
held-out or physical qualification from this failed run.
