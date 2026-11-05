# Anytime, Anywhere PAC-Bayes — code, records and formalization

Companion repository for the paper. Repository URL: `https://github.com/noumenal-ai/anytime-anywhere-pac-bayes`

This holds the released measurement records, the Lean sources behind the machine-checked
claims, reproduction scripts that assert against the published values, and the full figure set:
every figure the manuscript includes, the earlier versions they replaced, and the measured figures
the paper does not carry.

## Reproducing the headline numbers

```
python3 scripts/reproduce_headline.py
```

Output:

```
w_sr_battery_20260824: 100/100 rounds reproduce the released values exactly
w2_spi_battery_20260824: 100/100 rounds reproduce the released values exactly
remote sensing:    1.4744% -> 1.3587% -> 0.4141%
Walsh acquisition: 0.1819% -> 0.2880% -> 0.4605%
```

Every check is an assertion, so a regression fails rather than printing a wrong number.
Four reconstruction details are documented in the script header and are worth reading
before modifying it: the loss table is code-major; the Eq-(6) radius carries a Hoeffding
variance factor of 4; the paired mean needs exact summation (`math.fsum`) because numpy's
pairwise `mean()` differs by about 1 ulp; and the two substrates have different atom
geometries and different record schemas.

## Recovery at the minimum contrast budget

```
python3 scripts/tree_budget_experiment.py
```

Appendix B.3. Result 4 says `K-1` contrasts forming a spanning tree determine every directed
difference in the noiseless case; this measures what that is worth under noise. It refits the field
on 20,000 uniform spanning trees drawn from the measured graph (Wilson's algorithm, 34 contrasts
each against the 94 edges actually measured) and scores every fit on the same 1,094 held-out pairs
as the headline number, then repeats with 5,000 random 34-edge subsets drawn without requiring that
they span, and sweeps the edge count between the two at 2,000 spanning draws per budget. Runtime is
a few minutes.

What the script asserts, and what it declines to. Medians and quartiles converge, so they are
reported at a declared draw count and asserted against the published population values with a
tolerance; any seed reproduces them up to Monte Carlo error. Extremes do not converge: a sample
maximum grows with the draw count, and the number of unrestricted subsets that happen to span is a
rare event whose count scales with the draws. Those are printed for information and are not
asserted, and no claim in the appendix rests on them. The two error distributions do overlap --
some unrestricted subsets beat some trees, so the comparison is between medians, which differ by
a factor of 31 at the same contrast budget.

As in `reproduce_headline.py`, the full-graph fit is asserted against the released `D_100` before
anything derived is reported; it currently agrees to 5.1e-14 relative. Three reconstruction details
are in the script header and are worth reading first: the fit is inverse-variance weighted by the
certified radius (`w = 1/r^2`; unweighted least squares misses `D_100` by about 1% relative, which
looks like a rounding difference and is not one); the incidence block is rank `K-1 = 34` on any
spanning tree, while the system actually solved is that block plus a sum-to-zero anchor row and so
is rank 35, which is what makes the solution unique; and the 100 records sit on 94 edges, five of
which carry two records each.

## Claim-to-artifact map

| paper claim | value | read from |
|---|---|---|
| paired mean and Eq-(6) radius, all rounds | 100/100 exact | `data/*/results/records.json` with `loss_table.f64`, `draw_streams.bin` |
| remote-sensing held-out error, budget 5/10/100 | 1.4744% / 1.3587% / 0.4141% | `data/w_sr_battery_20260824/results/primary.tsv` |
| Walsh held-out error, budget 5/10/100 | 0.1819% / 0.2880% / 0.4605% | `data/w2_spi_battery_20260824/results/primary.tsv` |
| directed transitions measured | 8.0672% and 4.2517% | `primary.tsv`, confirmed against the incidence tables |
| pre-registered thresholds | in `certificate.json` per battery | `data/*/results/certificate.json` |
| spanning-tree budget, appendix B.3 | median 1.268%, IQR [1.017%, 1.605%] over 20,000 trees | `scripts/tree_budget_experiment.py` over `records.json` and `incidence_T100.tsv` |

Held-out error is normalized over the held-out set, and that set grows with the measurement
budget. The two substrates therefore run in opposite directions and their series are not a
like-for-like trend.

## Lean sources

`lean/` holds 101 canonical Lean files with `lean/MANIFEST.md` recording the source path,
size and sha256 of each. Duplicates were resolved to one copy per distinct content, preferring
the battery and export directories the paper's numbers are read from.

**No toolchain is shipped, and the tree does not compile standalone.** Several modules import
a vendored overlay (`NN.Spec.Models.Vit`, `NN.MLTheory.SelfSupervised.JEPA`) whose sources are
not part of this repository. The Lean files are included so the statements and proofs can be
read and audited, not so they can be rebuilt from this checkout alone.

## Figures

Thirty-one figures, with the emitting scripts alongside. PDF in `figures/`, PNG in `figures/png/`.
Every figure the manuscript includes is here.

### Ships in the paper's main text

#### `Fig0_closed_loop`

![Fig0_closed_loop](figures/png/Fig0_closed_loop.png)

The measurement loop: a change is proposed, priced, and the price is checked against what happened.

#### `Fig2_adaptive_validity`

![Fig2_adaptive_validity](figures/png/Fig2_adaptive_validity.png)

All 100 rounds standardized by their certified radius, with the dotted line at the worst
standardized deviation under the tightest admissible radius. The emitting script recomputes every
displayed number and asserts it against source before drawing, and checks that nothing overflows
the canvas before saving, naming the offending artist if anything does.

#### `Fig1_one_quantity`

![Fig1_one_quantity](figures/png/Fig1_one_quantity.png)

One signed quantity prices heterogeneous changes on a common scale.

#### `Fig1_recovery_ladder`

![Fig1_recovery_ladder](figures/png/Fig1_recovery_ladder.png)

Held-out recovery against measurement budget, both substrates.

#### `Fig3_nonvacuity_at_scale`

![Fig3_nonvacuity_at_scale](figures/png/Fig3_nonvacuity_at_scale.png)

The certified radius stays informative as the model scales.

#### `Fig4_parameter_bound`

![Fig4_parameter_bound](figures/png/Fig4_parameter_bound.png)

Identification by connected contrasts, and what the anchor fixes.

#### `Fig5_dyadic_bridge`

![Fig5_dyadic_bridge](figures/png/Fig5_dyadic_bridge.png)

Executed binary32 values entering the kernel exactly through the dyadic subring.

#### `FigA_appendix_plate`

![FigA_appendix_plate](figures/png/FigA_appendix_plate.png)

One signed performance difference orders nine heterogeneous rewrites, each with a certified interval.

#### `fig_walsh_plate`

![fig_walsh_plate](figures/png/fig_walsh_plate.png)

Walsh acquisition substrate, per-configuration detail.

`render_fig2_adaptive_validity.py` and `render_fig0_closed_loop.py` need Python 3.10 or newer:
they use an assignment expression inside a subscript, which does not parse on 3.9.

### Earlier versions, retained figures, and material the paper does not draw


### `Fig1_Q1_one_quantity`

![Fig1_Q1_one_quantity](figures/png/Fig1_Q1_one_quantity.png)

Earlier version of the one-quantity figure, before the base-style rebuild.

### `Fig2_Q2_adaptive_validity`

![Fig2_Q2_adaptive_validity](figures/png/Fig2_Q2_adaptive_validity.png)

Earlier version of the adaptive-validity figure, before the base-style rebuild.

### `Fig3_Q3_nonvacuity_at_scale`

![Fig3_Q3_nonvacuity_at_scale](figures/png/Fig3_Q3_nonvacuity_at_scale.png)

Earlier version of the nonvacuity figure, before the base-style rebuild.

### `Fig4_Q4_identification`

![Fig4_Q4_identification](figures/png/Fig4_Q4_identification.png)

Earlier version of the parameter-bound figure, before the base-style rebuild.

### `fig1_instrument`

![fig1_instrument](figures/png/fig1_instrument.png)

The confidence sequence drawn directly from measured data, with the standardized envelope and the region geometry. Superseded in the paper by the four question-aligned figures.

### `fig2_field_recovery`

![fig2_field_recovery](figures/png/fig2_field_recovery.png)

Recovered against sealed reference field, three measurement budgets. Retained as an appendix figure.

### `fig3_heldout_scatter`

![fig3_heldout_scatter](figures/png/fig3_heldout_scatter.png)

Held-out directed differences, recovered against reference. Retained as an appendix figure.

### `fig4_policy_path`

![fig4_policy_path](figures/png/fig4_policy_path.png)

Twelve-step policy path with the reference drawn as a band, since recovered and reference coincide
exactly. Refreshed to the version the paper carries.

### `franka_audit_cp`

![franka_audit_cp](figures/png/franka_audit_cp.png)

Robotic decomposition, telescoping signed differences summing to the reported total.

### `franka_paired_intervals`

![franka_paired_intervals](figures/png/franka_paired_intervals.png)

Paired intervals for the robotic sequence. Compressed to one clause in the paper.

### `panel_w2`

![panel_w2](figures/png/panel_w2.png)

Walsh acquisition summary panel. Dropped for the same reason.

### `panel_wsr`

![panel_wsr](figures/png/panel_wsr.png)

Remote-sensing summary panel. Accurate but not a good use of the space; dropped.

### `pilot_anytime_interval_evidence`

![pilot_anytime_interval_evidence](figures/png/pilot_anytime_interval_evidence.png)

Pilot rounds with pre-registered actions, before the adaptive phase begins.

### `rewrite_W1_classical_improvements`

![rewrite_W1_classical_improvements](figures/png/rewrite_W1_classical_improvements.png)

Classical substrate improvements across the rewrite battery.

### `rewrite_W2_gain_forecast`

![rewrite_W2_gain_forecast](figures/png/rewrite_W2_gain_forecast.png)

Forecast against realised gain. The forecast series is overdrawn.

### `rewrite_W2_risk_trajectory`

![rewrite_W2_risk_trajectory](figures/png/rewrite_W2_risk_trajectory.png)

Risk descent over the measured trajectory.

### `rewrite_W3_loss_functionals`

![rewrite_W3_loss_functionals](figures/png/rewrite_W3_loss_functionals.png)

Signed differences under bounded log loss, Brier and hard error.

### `rewrite_W4_shift_transport`

![rewrite_W4_shift_transport](figures/png/rewrite_W4_shift_transport.png)

Deployment and surrogate differences under distribution shift.

### `rewrite_W5_utility_leakage`

![rewrite_W5_utility_leakage](figures/png/rewrite_W5_utility_leakage.png)

Consistent-objective collapse and leakage against channel width. Encoded as a flat ratio line; the collapse 125 to 33 to 4 to 1 is the informative content.

### `rewrite_W6_executable_rewrites`

![rewrite_W6_executable_rewrites](figures/png/rewrite_W6_executable_rewrites.png)

Two executable rewrites with certified audit intervals. Two points on a chart; the candidate grid carries more.

### `w2_witness_detail`

![w2_witness_detail](figures/png/w2_witness_detail.png)

Per-configuration detail for the Walsh substrate.

### `wsr_ladder`

![wsr_ladder](figures/png/wsr_ladder.png)

Single-substrate recovery ladder. Superseded by the two-substrate ladder, which shows the substrates run in opposite directions.

## License

Apache License 2.0; see `LICENSE`. This covers the Lean sources, the reproduction and
figure scripts, the released measurement records and certificates, and the figures.

The Lean file headers carry the Mathlib convention — `Copyright (c) 2026 Dhruv Gupta.
All rights reserved. Released under Apache 2.0 license as described in the file LICENSE`
— and `LICENSE` is that file. Modules vendored from Mathlib and from the vendored overlay
retain their own upstream licenses and copyright.

## Layout

```
lean/      135 Lean sources + MANIFEST.md
           T3Witness/ — executed neural witness (13 modules, checkpoint, emitter, URS)
data/      measurement records, certificates, replay binaries
scripts/   reproduction scripts
figures/   main-text, superseded and unshipped figures, with emitting scripts
```

Total size: 20.8 MB.
