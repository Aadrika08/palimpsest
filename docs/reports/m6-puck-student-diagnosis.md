# Puck development diagnosis: approach control is poorly fitted

The [negative development result](m6-puck-student-development.md) remains **0/4
goals for every model**, with held-out layouts 6200–6207 locked. Retained-data
checks found no concrete sensor, cursor, action-scaling or runtime-mapping defect.
They did find large action errors on the original teacher inputs, as well as
limited teacher coverage of the contact states visited by the student. Neither
finding alone proves the causal explanation for the failed rollouts.

The own supervisor correctly stayed in `approach`: none of 7200 student intervals
reached the existing ≤0.08 m behind-point arrival condition. Per-run closest
arrivals were 0.097004–0.158146 m. Scenes 6100/6102 missed the ≤0.06 m lateral
corridor; 6101/6103 sometimes entered that corridor but remained too close to
the puck along its goal axis to reach the behind point. No transition threshold
or task condition was changed.

The source and retained-record checks bind float32 sensor projection,
float64 geometry reconstruction, BEFORE-mode input nine, one MLP action,
float32 tanh promoted to float64 before scaling by 0.4, and the existing wheel
mapping. The earlier independent audit reproduced the recorded MLP actions
within 9.54e-8. This is evidence against a demonstrated mapping defect, not proof
that every implementation defect has been excluded.

Two descriptive coverage comparisons use the same frozen geometric predicates:

| BEFORE-approach condition | Teacher train | Teacher recorded-dev | Student development |
| --- | ---: | ---: | ---: |
| All approach rows | 1709 | 336 | 7200 |
| Contact sensor true | 53 | 0 | 4634 |
| Ready corridor, arrival still >0.08 m | 16 | 2 | 2039 |
| Contact and ready corridor, arrival still >0.08 m | 0 | 0 | 1575 |

These are BEFORE-observation counts, not the later contact-interval counts in
the development report. Component-wise input-range overlap does not establish
coverage of these joint states. Of 6511 misaligned student approach rows,
4657 executed |velocity command| >0.01. At scene 6100/model 21/tick 103, for
example, the actual action was approximately `[0.063237, -0.021125]`; the authored
controller evaluated at that same retained state would return `[0, 0.4]`.
That comparison is a counterfactual source calculation, not an executed recovery
or prediction of a different rollout.

One separately frozen residual audit used **only** the original 5710 train rows
(6000–6015), 1314 recorded-dev rows (6016–6019), and all three unchanged
checkpoints. Before execution, the plan declared an exclusive partition: exact
zero-action stop labels, then BEFORE approach/push crossed with turn-only,
positive-velocity and negative-velocity target labels. Overlapping diagnostic
slices used the existing alignment, contact and arrival predicates. Empty
strata remain explicitly empty. Metrics and leakage cutoffs were fixed before
viewing residuals; no fitting, model selection or hyperparameter search occurred.

On approach turn-only rows, the target velocity is exactly zero:

| Split | Model | Rows | Mean absolute predicted velocity | Heading MAE | Rows with abs(v) >0.05 | Normalized MSE |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Train | 21 | 578 | 0.113962 | 0.308686 | 411 | 0.379085 |
| Train | 22 | 578 | 0.110564 | 0.309491 | 421 | 0.375417 |
| Train | 23 | 578 | 0.110392 | 0.312252 | 418 | 0.380834 |
| Recorded-dev | 21 | 106 | 0.216520 | 0.285646 | 106 | 0.414813 |
| Recorded-dev | 22 | 106 | 0.204667 | 0.287061 | 106 | 0.401437 |
| Recorded-dev | 23 | 106 | 0.205239 | 0.289356 | 106 | 0.406220 |

Normalized MSE is the mean of `((prediction - target) / 0.4)^2` over rows and
both action components. Values describe controller commands. For comparison,
the 811 recorded-dev positive-push rows have MSE 0.005306/0.005461/0.004922 for
models 21/22/23. Whole recorded-dev MSE is only 0.053038/0.053335/0.053887.
The aggregate therefore obscures much larger errors on turn-only approach rows.
All models exceed |velocity| 0.05 on all 106 of those original recorded-dev
rows. Poor fit is also present on training rows; missing recovery-state coverage
cannot be the sole explanation.

The audit reused full teacher admission and the strict bounded NPZ reader.
NumPy applied three float32 matrix/bias/tanh stages and the identical float64
0.4 action scaling against original float64 targets. Selected recorded-dev
losses agree with the historical reports within 1.73e-9. This arithmetic audit
does not establish bitwise NumPy/Torch equivalence. It imported neither Torch
nor MuJoCo, acquired no writer lease, ran no simulator, and opened no held-out
data. The single invocation passed in 7.298419 s, with exit 0 after 7.494519 s
under the existing 60 s supervisor. All 374 source/control/input entries were
rehash-verified unchanged before and after. No retry or correction was needed.
Root's separate first-pass review took 1.189689 s, rehashed the same 374 entries,
read the frozen arithmetic/strata implementation, and independently recomposed
all six train/dev aggregate MSEs from the exhaustive disjoint strata. That review
made no new predictions and confirmed the turn-only leakage and loss agreement.

The [compact index](m6-puck-student-diagnosis.json) pins the diagnostic scripts,
predeclared residual plan, primary receipts and the authoritative input ledger.
It does not duplicate all raw record ledgers. Historical development and fitting
reports retain their original labels and producer identities.

Uniform-loss imbalance or smoothing, optimization limits, and sparse recovery
support remain hypotheses. A minimal **unapproved prospective** pilot would
change only training-row weights: equal total mass for each nonempty primary
action/phase stratum, weights `N / (K * n_stratum)` derived from train data only.
It would retain the same MLP, nine inputs, seeds 21–23, 30 epochs, optimizer,
resource limits and earliest minimum of the unchanged recorded-dev mean loss.
All three models would be reported; both continuous actions would still be
learned, with no analytic fallback. Weighting cannot create missing recovery
states and is not a success guarantee. Any such pilot needs a separate frozen
protocol and authorization. Scenes 6100–6103 are now seen development evidence;
the ≥3/4-goals-per-model gate and locked held-out set remain unchanged. No pilot
implementation, training, new rollout or UI promotion is authorized by this report.
