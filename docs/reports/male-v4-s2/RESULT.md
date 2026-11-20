# MaleCNS v4 stage S2: result (DEVELOPMENT GATE NOT MET)

S2 ran once on 2026-11-20 under owner GO (`go-S2.json`, tree head `bf979b0148338567b91d901e93cc455904688893`,
manifest sha256 `833109d005ceb53825d7f722351b1344601b8ef97796683b09b6f20a0d562263`). `scientific_attempt: true`.
The protocol gate was applied unchanged: each augmented seed needs at least 3 of 4 development scenes by native goal.

**Result: `admission.status: failed-gate`. Every augmented seed reached the goal in 0 of 4 scenes. The
held-out stage S3 is not run and no qualification claim is made.**

| Training seed | old-corpus arm (reported, not gated) | augmented arm (gated, need >= 3) |
| --- | --- | --- |
| 10 | 1 of 4 | **0 of 4** |
| 11 | 2 of 4 | **0 of 4** |
| 12 | 1 of 4 | **0 of 4** |

Per owner (12 per arm, scenes 3160 to 3163): old-corpus 4 goal, 6 stalled, 2 time-limit (median final distance
1.79 m, min 0.78, max 7.50); augmented **0 goal**, 9 stalled, 3 time-limit (median final distance 10.03 m, min 4.45,
max 12.35). In this development evaluation the augmented arm did not outperform, and on these figures did worse than,
the old-corpus arm. This is a descriptive count over four scenes, not a statistical comparison, and S2 was designed
as a gate, not an effect-size estimate.

## Gate items

| Item | Observed |
| --- | --- |
| Unit | receipt `complete`, `drained`, returncode 0, no survivors; ledger `charged` S2 row |
| Cost | **413.050 CPU-s** measured (wall 541.7 s) against the 4,435 reservation; navigation lane now **1,250.835** CPU-s of 14,400 |
| Report | `route: development`, `status: completed`, no `failure.json`, `finalization_errors: []` |
| Owners | all 24 `completed-recording` and normal (`all_owners_normal: true`), teacher queries 0, scene initials matched across the six owners of each scene |
| Scenes | 3160 to 3163 only; held-out 3170 to 3177 never reachable on this route |
| Held-out | `held_out_status: locked-permanently` (protocol label: development gate not met) |

The infrastructure behaved as designed: no owner failed, nothing timed out (the stage used 542 s of the 1,800 s
deadline) and nothing was retried or replaced. The negative result is therefore a result about the trained
checkpoints under this protocol, not an operational failure. Raw owner recordings stay in
`palimpsest-authored-test-evidence/male-v4-s2/eval` (about 24 recordings, not committed).

## What this does and does not show

It shows that the six S1 checkpoints, trained with the matched budget of the v4 protocol and evaluated once on four
fixed development scenes, do not meet the gate; the augmented policies mostly stalled far from the goal. It does not
establish why (no diagnostic stage was authorised), does not say anything about held-out scenes (never read), and
does not license a different training or evaluation budget: any follow-up (another training design, a diagnostic) is a
new protocol decision for the owner, with new stage names and budget accounting. Remaining navigation budget is
12,749 CPU-s, but the protocol's one-attempt-per-stage rule and "no relaxing the 3/4 and 6/8 thresholds" stay.
An independent compact AI audit of this report (not human acceptance) is recorded separately.
