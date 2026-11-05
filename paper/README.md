# Authority-aware replay manuscript

The venue-neutral paper is `main.tex`. It replaces the historical feature and
capability inventory with one semantic-contract argument and RQ1–RQ4. The target
is 7–9 pages including figures and references; final pagination must be checked
with the real generated tables and plot.

The execution study is `studies/authority_replay_v1/`. Its predeclared protocol
was committed and then frozen before the result-producing campaign. This is not
an independent public preregistration. Fixed seeds are engineering repeatability
units, and seed 0 was used in disclosed harness-development smoke checks; they
are not held out.

## Build and evidence binding

Use `make -C paper paper` after the evidence-generation owner has installed the
focused build interface and bound the retained campaign summary. Use
`make -C paper verify` for the integrated verification flow. Consult the Makefile
and study README for the exact current command and source options; this document
does not authorize launching or repeating a campaign.

The manuscript consumes only these focused generated inputs:

- `generated/authority-claims.tex`
- `generated/fault-matrix.tex`
- `generated/replay-table.tex`
- `generated/overhead-table.tex`
- `generated/operation-table.tex`
- `generated/overhead-plot.tex`
- `generated/snapshot-ablation.tex`

Missing inputs display explicit PENDING text. The paper never substitutes the
historical `claims.tex`, old capability outcomes, smoke measurements, or expected
fault responses for new results. Generated files must come from verified compact
campaign evidence. Real result interpretation, final PDF rendering and every-page
visual inspection remain necessary before claiming the rewrite is complete.

The two static figures are vector TikZ/table sources. Authority ticks are
symbolic, and the replay matrix describes this system's execution/validation
semantics. Neither is a measured performance plot or a competitor comparison.
