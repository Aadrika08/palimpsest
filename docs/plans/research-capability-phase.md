# Capability-first research implementation plan

Approved 4 October 2026 in conversation. Base: `ee6bf61`. The supplied Claude
plan is background; this document records the corrected, approved execution
contract. The deliverable is exploratory evidence and a memory-v2 design, not
R2/R3/M6 qualification or access to reserved scenes.

## Decisions and bounds

- Capability first: establish useful control with simple baselines before a
  confirmatory topology comparison. Graph interventions apply identically to
  original and existing degree-rewired controls. Keep that control's documented
  weighted-strength limitation visible.
- Retire memory v1 as non-decision-bearing for passability-based route choice,
  with an observed development null. Do not claim held-out equality is forced.
  Preserve 44/48 accepted cells and the failed batch. R2 completes through v2.
- Reopen puck fitting for bounded conditioning/capacity probes. The historical
  stop-fitting decision and failed models remain unchanged as historical evidence.
- Exploratory runs use only retained train/already-seen recorded-development
  data. Label all reports `EXPLORATORY — not gate evidence`; no model promotion,
  reserve access, new native rollout, or new data collection.
- Compute caps, including per-stage admission: reproduction/admission 1200 s,
  puck exploration 2400 s, navigation exploration 3000 s, final readout 600 s;
  maximum 7200 s total. Implementation and synthetic verification are excluded.
  Sequential model execution, pinned CPU float32, one thread. Do not automatically
  redistribute time, retry fits, or extend a cap. Report incomplete candidates.
- New outputs <=2 GiB total, with 2 GiB disk free floor; source data immutable.
  Preserve evidence and publish compact arrays/checkpoints, not camera copies.
- Historical reproduction: all 3 original puck fits and all 6 actual original-
  graph old/augmented navigation fits. Every epoch loss and selected-checkpoint
  response must agree within absolute 1e-6. A disagreement stops that track.
- Exploratory decision rules live in runner docstrings before execution. Reports
  retain source/input hashes, actual CLI, split/seed/recipe, train-only statistics,
  exact attempted/unattempted outcomes, metrics, caps and qualification_claims=[].

## Task 1: decisions and memory-v1 retirement

Update current implementation plan, publish the honest structural-null retirement
report, and prepare a memory-v2 design (Task 4). Do not rewrite old evidence.

## Task 2: puck fitting ladder

Create `scripts/puck_fit_ladder.py`, `tests/test_puck_fit_ladder.py`, then publish
`docs/reports/m6-puck-fit-ladder.md` and `.json` after actual execution.

Reuse train_puck.prepare/loss, original model/actions and existing stratum IDs.
Keep the admitted 5710 train / 1314 recorded-dev rows. Independently evaluate
label reconstruction, duplicates, final-checkpoint versus online train loss,
feature scale, leakage and heading sign before fitting. Never infer under-fit
from unlike losses alone.

Rungs (every reached neural rung uses seeds21/22/23):
1. Conditioned32: standardize first six continuous inputs using train mu/sigma;
   binary flags/mode unchanged, constant sigma=1; historical30 epochs.
2. Longer32: same,300 epochs, Adam .001 cosine to .00001, batch64, clip1.
3. Capacity256: 9->256->256->2 tanh, same preprocessing/objective/schedule.
4. Training-only1NN diagnostic using standardized features, dev predictions;
   self-neighbor train scores are not evidence. No trees/new dependencies.

Preserve CPU input guards by putting normalization inside the exploratory model.
For width32, fold into first layer W_export=W/sigma and
b_export=b-W@(mu/sigma); validate exported float32 parity <=1e-6 and original
six-array checkpoint shape. Wider arrays use exploratory outputs, never legacy
bundle admission. Every seed uses earliest recorded-dev minimum; no winning seed.

Eligibility, each seed: dev normalized MSE<=.01; approach turn-only |v|>.05
leak<=5%; heading-sign agreement>=95% excluding exactly zero target headings.
Choose first passing neural rung. Report missing/empty strata as ineligible.
1NN-only success identifies a question, not a new runtime. No passing rung/budget
exhaustion stops fitting; no automatic collection/relabeling/native experiment.

## Task 3: navigation fitting probes

Create `scripts/nav_fit_ladder.py`, `tests/test_nav_fit_ladder.py`, then actual
`docs/reports/m7-nav-fit-ladder.md` and `.json`.

Reproduce historical CPU fits before changing splits. Reuse admitted v2 data and
actual upstream cell. New advice-train scenes3100/3101 include all three owners
each; advice-dev3102/3103 include all owners each. Old training sources remain
the common foundation, old recorded-dev a separate panel. These are seen scenes.
Fit preprocessing/constants only on training. Recompute .7/relative-bearing rule
and training-fitted constant on each evaluation panel; do not hardcode .0074.

Audit pre-action contact onset/sustained contact/recovery labels; distinguish
queried advice from executed learner actions. Retained trajectories cannot test
counterfactual teacher recovery success. Reverse after contact can be legitimate.

Ordered candidates, seeds10/11/12, <=2000 optimizer updates per fit:
1. Conditioned actual endpoint-readout model.
2. Per-frame388->64->64->2 tanh MLP.
3. GRU hidden64,32-tick truncated windows.
4. If graph model substantially trails passing graph-free baselines: encoder
   injection also at output nodes, equally in original/rewired arms.

Use CPU Adam .001 cosine to .00001, clip1, historical bounds/loss. Keep batch1
upstream cell; shuffle episodes but retain consecutive windows, detached hidden
carry and reset only at episode starts. MLP/GRU use same episode/window schedule.
Compare graph arms with identical seeds/order/update budgets and report parameter
counts. No custom batched cell or GPU implementation is required.

Report panels separately: imitation loss, wrapped heading MAE, negative-target
contact-onset reverse recall, false reversals with nonnegative targets outside
recovery, output variation, readout activity, per-scene/seed metrics and empties.
W-removal sensitivity is diagnostic, not topology qualification.

Eligibility each seed: teacher-dev loss<=recomputed rule loss; advice-dev loss
<=.8 times training-fitted constant loss; onset reverse recall>=80%; correctly
defined false reverse<=5%. Empty required strata are ineligible. Choose first
passing candidate in order. GRU success does not prove horizon causality; all
failures do not prove teacher redesign is required.

## Task 4: memory-v2 design only

Publish `docs/plans/m5-v2-decision-scene.md`, no runtime implementation. Question:
does history-fitted invalidation improve goal cost when passability affects route
commitment? Require separating barrier/two apertures, public waypoint graph,
same finite-state routing/inspection supervisor in all nine conditions. Obtain
initial beliefs by real samples; commitment outside both .75m sampling radii.
Blocked routes excluded; observed-open preferred to uncertain; then shortest
public route, deterministic counterbalanced ties. Preserve4m/90degree visibility
and declared bearings, no hidden-pose/true-goal fallback. Snapshot routing state.
Counterbalance relation, lexical IDs, preferred side/closure; null/no-event worlds.
Primary: paired capped time-to-goal including failures. Also success, wrong
commitment, path/inspection cost, case-family units. A separately approved pilot
must show route-choice dependence, no passive correction before commitment,
measurable wrong-route cost, valid visibility and CPU-FLYNN execution of both
routes before any confirmatory protocol. Spec approval is outside this phase.

## Verification and finish

Test reproduction refusal, train-only normalization, zero-variance inputs,
folded export parity, grouped split exclusion, recurrence carry/reset, correct
recovery metric alignment, matched graph budgets, finite values, held-out/output
guards and deadline handling. Test-first meaningful checks, focused tests then
appropriate whole-branch regression and independent code review.

Separate commits and draft PRs per reviewable lane, repository-local Aadrika
identity/Aadrika08 authentication. No automatic merge. Confirmatory steps require
new versioned admission and frozen protocol: puck existing3/4 per model dev then
6/8 held-out, navigation fresh dev first then reserved3120-3127 by separate review.
Do not edit legacy readers/protocols to accept probes. Hardware, exhibition,
README cleanup and archival migration are outside this phase.
