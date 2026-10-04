# Puck fitting ladder: conditioning helps, capability rule still fails

**EXPLORATORY — not gate evidence.** Executed 4 October 2026 under the
[capability-first plan](../plans/research-capability-phase.md). All three
historical fits reproduce exactly. All nine new neural fits finish; none passes
the declared recorded-dev rule. No model is selected, promoted, or evaluated
in a native rollout. Held-out layouts remain unopened.

## Inputs, reproduction, and scoped mapping audit

The frozen collection has 5,710 train rows from layouts 6000–6015 and 1,314
already-seen recorded-dev rows from 6016–6019. Collection SHA256 is
`3cf5044ac12fa80ebfed9aa044d0e983a94fcddb4e177da779a4684b944b518b`.
Original seeds 21/22/23 reproduce every epoch loss and selected-checkpoint
response on both panels with maximum absolute difference **0**. Selected
epochs are 30/27/26; dev normalized MSE is .0530384/.0533347/.0538868.
Selected-checkpoint train MSE is .0794580/.0805384/.0802588.

Reconstructing the existing teacher on valid canonical worlds from the nine
float32 inputs and BEFORE mode covers all 7,024 rows. Maximum action residual
is 3.8768e-7; no row exceeds 1e-6. There are 480 exact-feature duplicate groups
(1,828 rows), zero conflicting-target groups at 1e-6, and zero cross-split
duplicate groups. This supports a consistent finite-corpus mapping. It does
not prove observability outside these rows or guarantee generalization.

Train-only scales for the first six inputs are .0137214, .0108957, .0410024,
.0312088, .0839097, .00686387. Binary flags and mode remain untouched. Dev
contains 106 approach turn-only rows and 1,215 nonzero target-heading rows.
Approach-negative and push-negative dev strata are empty; push-negative is also
absent from train and remains untested. These empty regimes are reported, not
invented. Eligibility requires the two declared gate denominators to be nonempty.

## Results at each seed's earliest dev minimum

All seeds must have normalized dev MSE≤.01, approach turn-only |v|>.05 leak≤5%,
and heading-sign agreement ≥95%, excluding exactly zero target headings.

| Probe | Seed | Selected epoch | Dev MSE | Turn-only leak | Heading sign | Pass |
|---|---:|---:|---:|---:|---:|---|
| Conditioned 32, 30 epochs |21|22|.020870|75.47%|54.49%|No|
| Conditioned 32, 30 epochs |22|24|.020904|76.42%|65.51%|No|
| Conditioned 32, 30 epochs |23|29|.020066|83.02%|68.07%|No|
| Longer 32, 300 epochs |21|22|.020896|75.47%|54.32%|No|
| Longer 32, 300 epochs |22|43|.020890|57.55%|72.18%|No|
| Longer 32, 300 epochs |23|32|.019526|76.42%|67.65%|No|
| Capacity 256, 300 epochs |21|11|.020333|70.75%|66.75%|No|
| Capacity 256, 300 epochs |22|10|.023163|75.47%|62.96%|No|
| Capacity 256, 300 epochs |23|13|.021828|77.36%|63.05%|No|
| Training-only 1NN diagnostic |—|—|.045000|22.64%|60.49%|No|

Conditioning improves overall recorded-dev MSE substantially. Additional epochs
and width do not meet the joint rule. The 300-epoch probes select early dev
minima; later dev MSE rises to .0255–.0270 for width 32 and .0310–.0352 for
width 256 while final online train loss falls to .0054–.0061 and .00325–.00329.
Those online losses differ from selected-checkpoint losses and are not directly
comparable estimates. The trajectories are consistent with worsening
generalization later in training; they do not establish one unique cause.

1NN uses only train references in standardized feature space, with earliest-row
ties and bounded distance chunks. It supplies no train self-neighbor score as
evidence. Its failure does not establish that a different teacher or new data
collection is necessary. No further automatic fitting is authorized by this run.

## Arithmetic, execution, and retained evidence

Width 32 preprocessing is internal to the model, preserving the raw-input guard.
Folding mu/sigma into its first affine layer preserves the original six-array
shape. All six folded exports pass action parity across both panels; maximum
error is 4.4108e-7, below 1e-6. Width 256 NPZs contain six wider parameter arrays
plus `mean` and `scale`, without an embedded format/version marker. Shape
compatibility does not admit a new recipe through the legacy
bundle reader; these artifacts are not qualified production bundles.

Pinned CPU Torch 2.9.0/NumPy 2.2.5, float32 model arithmetic, original float64
targets/actions, one thread, seeds 21–23, batch 64, Adam .001, clip 1. Longer and
wider probes use cosine decay to .00001. Earliest strict dev minimum wins,
with no winning-seed selection. Reproduction takes 24.44 supervised seconds;
exploration takes 321.05 supervised seconds, including admission. No candidate
is incomplete or unattempted. Source/input identities verify unchanged after
each stage. Shared phase caps and the initial navigation preflight are retained
in the phase execution receipts; there is no scientific-fit retry here.

[The JSON report](m6-puck-fit-ladder.json) retains both complete runner receipts,
actual CLI, source/data/bundle hashes, train statistics, all epoch histories,
per-stratum metrics, decisions, storage limits, and artifact hashes.
[Compact checkpoint evidence](m6-puck-fit-evidence/) contains the three exact
reproductions and nine probes: 12 NPZ files totaling 897,942 bytes. Retained
source recordings remain external immutable inputs; no camera copies are made.
The underlying invocation is under
`runs/research-capability-20261004T070529Z` in the research checkout.

The declared decision is **stop fitting with no passing neural rung**. M6 learned
puck capability remains open. A future study must explain and freeze its next
intervention before using fresh development or held-out data.
