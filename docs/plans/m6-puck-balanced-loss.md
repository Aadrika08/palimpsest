# Puck balanced-loss pilot — frozen source contract

This proposal follows evidence commit `0f5de8b`. Existing models 21–23 each
failed development with 0/4 goals. The frozen residual audit found poor fit on
original turn-only teacher inputs, not just previously unseen contact states.
The hypothesis is that balancing training mass across existing action regimes
may improve that fit. It cannot supply missing recovery examples or guarantee
task success. Source implementation is approved. Fitting, a new rollout and held-out use require separate review and authorization.

## Immutable data and experiment boundaries

Reuse only the admitted collection report SHA256
`3cf5044ac12fa80ebfed9aa044d0e983a94fcddb4e177da779a4684b944b518b`:
6000–6015 train (5710 rows) and 6016–6019 recorded-dev (1314 rows). Re-run the
unchanged strict teacher admission, independent BEFORE-mode reconstruction,
float32[9] feature and float64[2] target checks. Preserve all source/feature/target
hashes; reject any mismatch. No new labels, resampling, augmentation, row dropping,
teacher collection, student-development rows, or held-out data enter fitting.
The original teacher/task/supervisor protocols and source remain unchanged.

## Exactly one changed objective

Partition training rows by actual target labels and BEFORE phase, with exact
comparisons and stop priority. Both target components zero define `stop`.
Otherwise cross BEFORE `approach`/`push` with target velocity zero, positive,
or negative. The zero-velocity non-stop stratum is `turn_only`.

| Nonempty training stratum | Fixed count n | Weight (exact formula, float64) |
| --- | ---: | --- |
| Stop | 381 | 5710 / (6 × 381) |
| Approach turn-only | 578 | 5710 / (6 × 578) |
| Approach positive velocity | 944 | 5710 / (6 × 944) |
| Approach negative velocity | 170 | 5710 / (6 × 170) |
| Push turn-only | 478 | 5710 / (6 × 478) |
| Push positive velocity | 3159 | 5710 / (6 × 3159) |

The empty push-negative stratum remains empty. Require the fixed counts and
exhaustive disjoint partition; an unexpected count rejects the pilot rather than
recomputing a different design. For row i in stratum s, `w_i = N/(K*n_s)` with
N=5710, K=6. Weights are derived from train labels only, fixed for all epochs and
seeds, and have dataset mean 1. Define `ell_i = mean_components(((a_i-y_i)/0.4)^2)`.
The full objective is `mean_rows(w_i * ell_i)`, equivalent to the mean of the six
stratum mean losses. Each ordinary shuffled minibatch uses the mean of its
weighted row losses; do not renormalize weights within a minibatch, oversample,
rebalance from dev residuals, or introduce an auxiliary loss.

All model arithmetic stays fixed: 9→32→32→2 tanh MLP, float32 parameters/logits/
tanh, promote normalized output to float64 before ×0.4; retain float64 targets
and weighted loss. The model still supplies both continuous actions, with no
analytic fallback, action clipping, extra features, phase threshold change or
learned phase switch.

## Training, selection and reporting

Fresh deterministic initialization for each of seeds 21,22,23; do not warm-start
old checkpoints. Keep 30 epochs, batch 64, existing seeded training-only shuffle,
Adam lr 0.001 / weight decay 0, gradient norm cap 1, CPU one thread and pinned
runtime. No hyperparameter/candidate search or winning-seed choice.

Selection is unchanged: evaluate ordinary **unweighted** recorded-dev mean
normalized MSE every epoch, save its earliest strict minimum independently for
each seed. The same 1314 dev rows and all phases participate. Weighted training
loss must be explicitly named in histories; never label it comparable to the
historical unweighted training loss. Preserve all 30 epochs, selected epoch and
all three statuses/checkpoints. Report the same frozen residual strata for all
three final checkpoints as diagnostics, never use those metrics for selection.
There is no new residual threshold that substitutes for task success.

## Identity, bounds and stopping

Use a distinct balanced-training protocol/report identity that pins this exact
objective, counts, weight arithmetic, base learning/task identities, current
trainer/model source and data hashes. Existing unweighted reports/checkpoints
remain immutable. Do not relabel the base learning protocol's loss as weighted.
Reuse numeric model/checkpoint validation; any prospective reader extension must
admit the new identity explicitly while preserving historical/default validation.
Do not replace the production model manifest or existing student bundle pins.

Retain per seed: 120 s internal, TERM 180 s +15 s grace, 200 s supervisor,
16 MiB; all three: 660 s stage/TERM +15, 680 s enclosing including publication
and return, 64 MiB controls+outputs, 1 GiB free floor. Existing 1 MiB checkpoint,
2 MiB expanded NPZ, 4 MiB JSON and 1 MiB per-stream logs stay fixed. One owner at
a time, all three planned rows retained; stop on first failure, no retry,
replacement, budget extension or partial-model promotion. Rehash original data,
models and sources before/after; retain drained logs and exact owned cleanup.

Fitting is a separate stage. Source review and an explicit serialized runtime GO
must precede it. Only a later reviewed native mechanism/development stage may
evaluate these new identities; fitting or better residuals do not authorize it.
Scenes 6100–6103 are already seen development evidence, with the unchanged
requirement of ≥3/4 goals for EACH of all three models and no seed selection.
Held-out 6200–6207 stays locked. Any later independent generalization claim needs
the original untouched held-out boundary and separate authorization.
