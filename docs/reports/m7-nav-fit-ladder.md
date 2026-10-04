# Navigation fitting probes: no candidate meets the joint rule

**EXPLORATORY — not gate evidence.** Executed 4 October 2026 under the
[capability-first plan](../plans/research-capability-phase.md). All six
historical original-graph fits reproduce exactly. All twelve reached probes
finish, but none is eligible. Conditional output-node injection is unattempted
because no graph-free baseline passes. No candidate is selected or promoted;
reserved scenes 3120–3127 remain unopened, and R3 remains open.

## Reproduction and retained preflight failure

The first preflight refuses the producer HEAD before corpus admission or any
fit: it expected training revision `6feade9770dc40efa567633412baec4347ee33cb`,
whereas the retained checkout is at its evidence-publication commit
`041434dd2b6fab5f19329b003f98407887e49286`. All protocol-pinned reader sources,
added sources and lockfile still match. The runner correction pins that exact
publication HEAD and retains the training revision separately; it does not
relax source or artifact checks. The 0.072-second refusal and its logs are
preserved. No scientific fit is retried.

The corrected first scientific reproduction passes for seeds 10/11/12, both
old-corpus and augmented recipes, using the historical physical producer root
and actual pinned upstream cell. Every epoch train/dev loss and all 1,228
selected-checkpoint recorded-dev responses match with maximum absolute
difference **0**. Selected epochs are 20/16/17 for old-corpus and 1/1/7 for
augmented. Supervised reproduction takes 328.72 seconds, inside the remaining
shared reproduction allocation. The pinned cell is the upstream source with
SHA256 `707cba79e7bf92923618ccc596e3d7a2d779edc02a970b0949f6dd3c0d28ae80`.

## Grouped panels and metric definitions

Old teacher training remains the common foundation. All three learner owners
10/11/12 from advice scenes 3100/3101 enter train; all owners from 3102/3103
enter advice-dev. New train has 5,094 rows in 16 episodes, teacher-dev1,228 in 4,
and advice-dev2,103 in 6. These are retained, already-seen development scenes,
not a fresh test sample. Train-only statistics leave contact binary unchanged.

For each panel, recompute the raw-input .7/bearing rule, using wind sine/cosine
features 387/386 rather than collision angle 385. Fit the constant velocity and
circular heading only on training. Teacher-dev rule loss is .0074433033;
advice-dev rule loss .2028839727. The training-fitted constant scores .0671977103
on teacher-dev and .3448926806 on advice-dev, making the advice threshold
.2759141445. These panel-specific values replace historical hardcoded baselines.

Advice labels are validated queried teacher actions at the pre-action learner
state. Every one of the 5,080 advice labels differs from its executed learner
action. Contact onset and before/start recovery phases are checked separately;
retained learner trajectories cannot test counterfactual teacher recovery
success. Advice-dev has 44 negative-target contact-onset rows and 1,536
nonnegative-target rows outside recovery. Old teacher phase metadata is unknown;
its recovery rates are reported unknown, not silently assigned zero.

Each seed must simultaneously satisfy teacher-dev loss≤its rule, advice-dev
loss≤.8×its training-fitted constant, onset reverse recall≥80%, and false
reverse rate≤5% on nonnegative targets outside recovery. Empty or unknown
required advice denominators would make a candidate ineligible.

## Results at each fit's earliest combined-dev minimum

| Candidate | Arm | Seed | Teacher loss | Advice loss | Onset reverse recall | False reverse | Pass |
|---|---|---:|---:|---:|---:|---:|---|
| Conditioned endpoint |Original|10|.046196|.332748|0%|0%|No|
| Conditioned endpoint |Rewired|10|.059168|.330669|0%|0%|No|
| Conditioned endpoint |Original|11|.054820|.317261|0%|0%|No|
| Conditioned endpoint |Rewired|11|.048414|.296940|0%|0%|No|
| Conditioned endpoint |Original|12|.052975|.279156|0%|0%|No|
| Conditioned endpoint |Rewired|12|.048144|.301258|0%|0%|No|
| Frame MLP |Graph-free|10|.056888|.293460|0%|0%|No|
| Frame MLP |Graph-free|11|.054292|.277030|0%|0%|No|
| Frame MLP |Graph-free|12|.051484|.299753|0%|.13%|No|
| GRU64 |Graph-free|10|.061551|.290076|100%|38.35%|No|
| GRU64 |Graph-free|11|.064052|.307173|38.64%|14.00%|No|
| GRU64 |Graph-free|12|.068195|.264823|68.18%|25.13%|No|

All candidates fail the teacher-dev criterion. The graph/MLP candidates predict
no required onset reversals. GRU onset counts are 44/44, 17/44 and 30/44, with
589/1,536, 215/1,536 and 386/1,536 false reversals respectively. GRU seed 12
passes the advice-loss criterion alone. Neither that seed nor seed 10's perfect
recall constitutes a passing model: inappropriate reversals remain substantial.

Every reached fit receives exactly 2,000 Adam updates, .001 cosine to .00001,
clip 1, CPU float32, one thread, episode shuffling by seed, consecutive 32-tick
windows, detached hidden carry and episode-start reset. Graph arms have 61,872
trainable parameters each; MLP 29,186; GRU 87,298. Schedule hashes match across
all candidates for a seed and across graph arms. The actual upstream cell is
used at batch 1; there is no custom batched cell or GPU implementation.

The graph endpoints have nonzero state variation at sampled window ends;
this is not an audit of every artificial readout ReLU. Removing frozen W changes
recorded-input responses: advice velocity mean-absolute change .00980–.05612
and heading .08084–.51589 radians. Thus these fits show some W sensitivity,
without establishing useful control or a topology advantage. Degree rewiring
preserves degree and the weight multiset, but not weighted incoming strength.
Do not infer a memory horizon or teacher-redesign necessity from these failures.

## Evidence and stopping decision

Navigation exploration takes 312.38 supervised seconds, including admission.
Both scientific stages verify source/input identities unchanged. Six injection
fits are explicitly unattempted under the prospective conditional rule, rather
than marked failed or omitted. There is no budget exhaustion, reserve access,
new native rollout, new collection, or model promotion.

[The JSON report](m7-nav-fit-ladder.json) retains the original refused preflight,
both full runner receipts, actual commands, source/data/model pins, grouped
assignments, train statistics, histories, parameter counts, schedule hashes,
per-scene metrics, recovery audit, response variation and W-removal diagnostics.
[Compact probe evidence](m7-nav-fit-evidence/) contains 12 exploratory Torch
state dictionaries and 12 NPZ response panels totaling 3,626,880 bytes. They are
not legacy evaluator bundles. No source camera copies are published. The exact
reproduction references the six already-retained historical checkpoints and
preserves their identities and response parity in the receipt.

The declared decision is **stop fitting with no passing reached candidate**.
Capability remains unresolved. Any next intervention needs a new explicit
development decision; fresh confirmation and held-out access are separate work.
