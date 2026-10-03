# Balanced puck fitting: fixed residual comparison

The bounded NumPy-only audit completed once on 2026-10-03, but **the balanced
objective did not resolve the recorded-development turn-only problem**. All
three aggregate and approach-turn-only joint losses worsened. No new fitting,
selection, rollout, held-out read or task qualification followed this diagnostic.

The comparison uses all three [balanced fits](m6-puck-balanced-training-v1.md)
and the [original residual evidence](m6-puck-student-diagnosis.md), with exactly
the same 5710 training and 1314 recorded-development rows. The original seven-way
exclusive phase/action partition, overlapping diagnostic strata, metrics and
thresholds were reused verbatim. Float32 NumPy dense/tanh arithmetic and float64
action scaling were unchanged. All three checkpoints were reported; none was
selected using this comparison.

| Seed | Dev aggregate MSE, original → balanced | Dev approach-turn MSE, original → balanced | Dev approach-turn mean \|v\|, original → balanced | Dev turn rows \|v\| > .05, original → balanced |
| --- | ---: | ---: | ---: | ---: |
| 21 | .05303843 → .06030484 | .41481256 → .42899499 | .216520 → .197731 | 106 → 105 / 106 |
| 22 | .05333466 → .06008516 | .40143745 → .42274133 | .204667 → .197179 | 106 → 104 / 106 |
| 23 | .05388684 → .06074273 | .40621950 → .42393682 | .205239 → .188661 | 106 → 105 / 106 |

Development approach-turn heading MAE increased from .285646/.287061/.289356
to .304350/.301709/.307602. On the 578 training approach-turn rows, joint MSE
improved, while velocity leakage worsened: counts above .05 increased from
411/421/418 to 481/478/481. The training reverse-motion stratum improved, and
stop-label MSE improved on both splits. Positive-motion losses worsened; the
development push-turn joint loss improved while its training counterpart
worsened. These mixed changes do not establish a useful closed-loop policy.
The fixed contact/recovery coverage gaps remain unchanged.

The [comparison index](m6-puck-balanced-residual-v1.json) retains every stratum's
count, original/balanced MSE, component MAE and the original velocity-leakage
metrics. Full RMSE, bias and maxima remain in the pinned raw residual reports.
There is no new diagnostic threshold or acceptance rule.

The audit ran at clean evidence commit
`b952f01881b8f42e896755e097fa64fbedaf4381`, with numerical producer source unchanged
from `ec7a113`. It passed in **11.169660 s** internally and **11.461205 s** under
the 60 s supervisor; the enclosing command exited 0. It rehashed all **372 inputs
and controls before/after**, used no writer lease, and imported neither Torch
nor MuJoCo. NumPy reconstructed the selected unweighted development losses with
absolute differences **5.325495e-10, 2.918154e-10 and 3.799721e-10**, all within
the original 1e-6 numerical tolerance. This tolerance verifies arithmetic; it
does not admit task performance.

The independent root review passed its first invocation. It rehashed the
retained inputs and ledgers, verified exact original/new feature and target
hashes and every stratum count, and independently recomposed all six aggregate
MSEs from the disjoint primary strata. It did not repeat dense predictions.
Its receipt, the original controls and both residual outputs are pinned in the
index; complete file inventories remain in those raw receipts.

The historical result remains 0/4 development goals for each original model.
Balanced-model runtime binding, native/replay checks and fixed development
6100–6103 × all three models require separate review and authorization. The
unchanged gate is **at least 3/4 goals for each model**, and held-out 6200–6207
remains locked. These diagnostics authorize neither another loss search nor an
automatic rollout promotion.
