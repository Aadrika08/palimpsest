# Puck learning v2: align teacher stop with the existing task radius

This is a source-only candidate. The teacher and independent sensor-only supervisor
stop at distance **≤0.2 m**, returning the carried mode before any transition or
unit-vector division. The task already uses this radius. Nothing else in the
teacher transitions, signed approach, action caps, physics, success/contact rules,
record admission or execution budgets changes.

The immutable [v1 collection evidence](../reports/m6-puck-teacher-collection-v1.md)
retains all 20 natural goals and the failed data admission. Seed 6004 terminated at
0.19417256244312925 m with ten qualifying task intervals but zero terminal zero-action
labels: the old teacher stopped only at 0.18 m. Its final command remained
`[-0.25, 0.09437987642473056]`. The native task result was valid; the fixed training
batch remains rejected.

Source evaluation on all 7070 retained worlds found that the proposed 0.2 m stop
would yield 16 terminal zero commands on seed 6004's **unchanged recorded path**,
with independent teacher/sensor mode agreement on all evaluated rows. This supports
testing the candidate; it predicts no rollout. Different actions change the native
trajectory, and a nonzero goal-entering interval can start task dwell before the
first zero command. Every future training owner must still supply at least ten
actually executed terminal zero labels. There is no guarantee of admission.

The source-only review is retained beside the rejected batch as
`runs/m6-puck-teacher-collection-v1-prepared/stop-boundary-review.py` and `.json`
in the `puck-learning` worktree, with SHA256
`f2408cd20e068acda4e15ba9929492e574d2ae180a763705d1dcd69b18bf5afe` and
`abe04cf227258849515546d7e6b2749e2ebcd882bd5afb9c17bcfdb58bd66431`.
These local derivative files are not a new dataset or native run.

## Exact version boundary

- [Task protocol v5](m6-puck-pushing-protocol-v5.json) changes the teacher to
  `analytic-puck-behind-align-push-v5`. The complete numerical task, XML, layouts,
  learning hyperparameters, thresholds and limits remain equal to task v4.
- [Learning protocol v2](m6-puck-learning-v2.json) pins task v5 and the new teacher
  source. Its own supervisor is `sensor-only-puck-phase-v2`, with feature identity
  `virtual-puck-eight-plus-own-before-mode-v2`. Nine-input, float32-to-float64
  reconstruction, action/loss arithmetic and atomic completed-interval mode commit
  are unchanged. Stop is checked before division, including coincident goals.
- [Mechanics protocol v5](m6-puck-mechanics-v5.json) pins the changed source for the
  existing ten-owner verifier. Owner order, intervals, continuation boundaries,
  replay checks and bounds are identical. A changed teacher trajectory must be
  measured anew; historical 361-tick trajectories and parity do not transfer.
- Record/application field schemas remain unchanged. Exact protocol, teacher,
  supervisor source and feature hashes reject old records, cursors and snapshots.
  All earlier protocol files and failed data remain immutable. The rejected batch
  cannot be relabeled, readmitted, padded, extended after termination or repaired
  by replacing only seed 6004.

Strict arithmetic remains visible at the boundary: `float32(.2/14) * float64(14)`
is `0.2000000011175871`, while the next lower float32 value reconstructs to
`0.19999998807907104`. No tolerance, clipping or rounding is added. If privileged
teacher and independently reconstructed own modes disagree, the existing guard
preserves the original float64 label and raw sensors, records no executed interval
and rejects the batch. A dedicated fixture exercises this actual discrepancy.

## Next stages require separate review and GO

1. Freeze and review these source/protocol hashes and focused pure checks. Reuse the
   existing ten-owner mechanics verifier with fresh retained controls: 600 s inner,
   TERM 660 s +15 s grace, 680 s supervisor, 1 GiB. Compare continuation/replay
   against its own new source records, preserving any failure and unstarted rows.
2. Only after acceptance, freeze a fresh full 20-owner teacher attempt using the
   existing collector: 6000–6015 train, 6016–6019 recorded dev; one natural episode
   of at most 600 ticks each. Keep 1500/1560/+15/1580 s and 4 GiB stage limits,
   160 MiB per owner, 1 GiB free floor and 16 GiB aggregate retention. All 20 goals,
   per-train ≥32 ticks, ≥10 contacts and ≥10 executed terminal zero labels remain
   mandatory. No retry, replacement, reset, padding or threshold relaxation.
3. A separate combined source review will bind the existing parallel trainer/model
   implementation to this new protocol. Keep all three seeds 21/22/23, 30 epochs,
   optimizer and selection rules. The historical tiny CPU mechanism evidence stays
   bound to its original source, not this revision. No training is authorized here.
4. Closed-loop dev 6100–6103 and held-out 6200–6207 remain unopened under the
   unchanged all-model thresholds and matched-start requirements. No teacher result
   establishes learned capability or physical qualification.

Production Engine, UI, worker and model files are untouched. No native collection,
Torch, training, browser or build job was run for this source slice.
