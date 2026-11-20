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
new protocol decision for the owner, with new stage names and budget accounting. The navigation lane has 13,149 CPU-s of its
14,400 cap unspent, but the protocol's one-attempt-per-stage rule and "no relaxing the 3/4 and 6/8 thresholds" stay.

## Independent AI audit (not human acceptance)

A fresh reviewer agent re-derived the result read-only from the recorded files: SHA256SUMS, the GO fields, the receipt and
ledger charge (413.050 CPU-s; lane total 1,250.835) and every count above reproduce, and all 24 per-owner `result.json`
files agree with `report.json`. The six checkpoint shas in the report equal the files and the binding's constants, and each
worker builds the binding for its own `(seed, arm)`; the per-owner results record no checkpoint hash of their own, so that
link rests on the code path plus the report-level identities. `goal_reached` comes from the engine's natural-goal boundary,
not from a threshold. Raw payload and policy-input hashes are all distinct and the old-corpus arm on the same initials
behaves normally, so the harness is not the cause.

**Observation to read the failure with:** from the recorded per-tick actions, the augmented checkpoints emit an almost
constant action independent of the observation (seed 10 about forward 0.49, turn near 0; seed 11 about 0.54, -0.27; seed 12
about 0.53, -0.20; standard deviation over ticks at most 0.02 for seeds 11 and 12, and small for seed 10), so each drives a
fixed arc and stalls early in 9 of 12 owners. The old-corpus arm shows ordinary action variance. This points to collapsed or
saturated augmented policies (a training or checkpoint question), not a navigation failure that varies by scene. Nothing
authorised so far establishes the cause, and this document does not claim one.
