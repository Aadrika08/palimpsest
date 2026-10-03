# M6 puck mechanics v3 — recovery still cycles

The one approved v3 mechanics run at
`3b078cb0fc51ae5ea79bcbc7b3de0e1556474f8b` **failed**. Its positive analytical
teacher completed the unchanged 600-tick episode with `time_limit`, without
qualifying goal dwell. No controller, threshold or horizon changed after this
run. No retry, continuation/replay qualification, teacher collection or training
followed. The [v1](m6-puck-mechanics-v1.md) and [v2](m6-puck-mechanics-v2.md)
failures remain unchanged.

| Planned owner | Actual ticks | Result |
| --- | ---: | --- |
| zero, seed 5990 | 120 | Passed; zero puck XY displacement, no rover-puck contact |
| push-positive, seed 5991 | 120 | Passed; +.6572949964 m X displacement with contact |
| push-negative, seed 5992 | 120 | Passed; −.6571574766 m X displacement with contact |
| teacher-positive, seed 5993 | 600 | Failed; `time_limit`, .4438123838 m final goal distance |
| teacher-negative, seed 5994 | 0 | Not started |
| continue-tick1 | 0 | Not started |
| continue-contact | 0 | Not started |
| continue-dwell | 0 | Not started |
| replay-actions | 0 | Not started |
| replay-policy | 0 | Not started |

The teacher reached .7583860024 m maximum XY displacement, had 109 intended
contact intervals, and retained initial, completed-tick-1 and first-contact
snapshots. First contact was completed tick 112; no qualifying dwell or dwell
snapshot occurred. Final mode was `approach`. The recording completed normally;
the owner then exited 1 because strict mechanics acceptance failed.

Outer supervision exited 1 after **20.228797507 s**; inner elapsed time was
**19.970457462 s**. All callbacks and retired/current renderers closed. No forced
signals, sampler errors, survivors or finalization errors were reported. Six
observed PID/start identities and all four owner groups were independently
absent. All 81 source hashes and each owner's full model hash remained unchanged.
The native slot was explicitly released before read-only audits.

The [JSON index](m6-puck-mechanics-v3.json) binds all ten statuses, source/protocol
pins, controls, raw records, native receipts and audits. Raw output is
`runs/m6-puck-mechanics-v3-20261003/`; controls/audits are under
`runs/m6-puck-mechanics-v3-prepared/`.

- Inner report: `069b9c99529b9ef11f744ecc56e86670eca5ab3bc32573e3511a6d9070c1140e`.
- Outer report: `4cd23a2c7395840a91de4d8f53ad10ec60f4fd8043a6453b50552a32fa335ea0`.

The independent NumPy-only audit passed in **2.625 s**, checking **960 rows**, six
snapshots and **73 indexed files / 119,785,385 bytes**. It reconstructed all 600
stateful teacher decisions, before/after modes, events, task digests, contacts
and snapshot mode fields. Root's separate audit passed in **2.473 s**. Neither
audit imported MuJoCo/Torch or decoded/restored native state. Integrity checks
preserve the mechanics failure and do not qualify continuation.

The first local audit attempt failed on an incorrect nested
`manifest['summary']['teacher_mode']` lookup: `RunWriter.finish` merges summary
fields at the manifest root. Its script and failure receipt remain retained.
The separate `audit-v2.py` changes only that lookup to
`manifest['teacher_mode']`; its successful report is separately pinned. No raw
artifact or runtime source was modified. Root's audit did not have this error.

The teacher issued **167 moving** and **433 turn-only** commands: 267 decisions
ended in approach, 333 in push. These are zero-based action-index ranges:

| Action ticks | Mode / command phase |
| --- | --- |
| 0–25 | Approach / turn |
| 26–71 | Approach / move |
| 72–89 | Push / turn |
| 90–160 | Push / move |
| 161–213 | Approach / turn |
| 214–266 | Push / turn |
| 267–311 | Approach / turn |
| 312–362 | Push / turn |
| 363–412 | Push / move |
| 413–468 | Approach / turn |
| 469–511 | Push / turn |
| 512–550 | Approach / turn |
| 551–597 | Push / turn |
| 598–599 | Approach / turn |

Every recovery approach interval commands zero translational velocity. Native
positions nevertheless move during turning/contact; arrival can therefore
become true before the body points toward the goal. At action 214, behind-point
distance is .079915565 m, satisfying the .08 m arrival test, but goal heading
error is +1.613979 rad. The teacher enters push and commands `[0,+.4]`. At 267,
lateral error .060488105 m loses readiness before heading alignment completes,
and approach commands `[0,−.4]`. The same mechanism recurs at 469/512 and 551/598.
This is a slower mode cycle, not evidence that extending the horizon alone would
complete recovery.

The last moving command is action **412**, `[.2,+.002910416]`, reducing goal
distance by .006971295 m. Later turn/contact motion gives smaller progress; the
last strictly positive recorded reward is action **591**, .0000420600844 m.
Actions 592–599 have zero reward. At 599 the teacher remains in approach with
behind distance .120410039 m, lateral error .061341740 m and heading error
−2.242625 rad; it is not at an arrival boundary. Contact is not being rejected:
maximum intended penetration remains .000435239 m, within the .02 m bound.

Read-only source review confirms signed velocity is already supported by
`body_profile.effective_control`, the pinned upstream converter/step and motor
control range. At action 161 the behind target is approximately
`[-.103225,−.061950]` m in the body frame. Facing it for forward approach needs
−2.601063 rad, whereas facing away for reverse approach needs +.540529 rad.
This is a geometric comparison at a retained state, not a counterfactual rollout
or proof of reverse-contact behavior.

A minimal candidate for review is to change only approach travel-direction
selection: use the forward or reverse target heading with smaller absolute
wrapped error, breaking an exact tie toward forward; keep the .12 rad alignment
gate and .4 rad cap, and apply the existing .25 velocity magnitude with the
selected sign after alignment. Push stays positive .2 and the two-mode
transitions, physics, success limits and horizon remain unchanged. This could
reduce large recovery rotations, but arrival/alignment cycling may remain.
It is **not implemented or executed**. Any next version needs separate design,
source/protocol and runtime approval. Training remains closed because the
mode-dependent teacher still requires a reviewed learner contract.
