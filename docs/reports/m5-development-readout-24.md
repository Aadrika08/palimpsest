# Partial fixed-development paired readout: 24 cells

The unchanged [analyzer](../../scripts/analyze_memory_matrix.py) completes the
six-report readout on `c6485af` in 0.617 s supervised, first invocation. Inputs are
the audited C3, C4 and remaining-01 through remaining-04 comparison reports.
The [index](m5-development-readout-24.json) pins inputs, command and full output.
No model, simulation, writer lease or held-out data was used. This summarizes
audited reports; it is not another raw-record audit. The earlier
[sixteen-cell snapshot](m5-development-readout-16.md) remains unchanged.

Coverage is **24/48 cells**, 216 condition readouts and 192 own-versus-reference
pairs. The eight shared seed namespaces are preserved: 24, 25 and 26 each have
six cells, 27 has two, and 28–31 have one each. Four historical C3 cells retain
broader core differences; twenty C4/later cells retain strict core forks.

| Paired metric (`own - reference`) | Observed result |
| --- | --- |
| Evaluator task pass | 192 ties |
| Goal boundary | 187 ties; own one tick later in five pairs |
| Stale-value correction | 72 ties in nine change cells; not applicable in 120 null/no-event pairs |

There is no observed own-U task, correction or goal-timing advantage. All seven
null cells retain false targeting; all eight no-event cells have zero selector
invocations and behavior bytes. Exact per-condition targeting, observations,
confirmations and censoring remain in the full JSON output.

Pairing and regime/schedule/closure-side/fork strata are unchanged. Missing
events are not assigned timeout boundaries; null confirmations are not stale
corrections. The analysis makes no independent-frame, significance, causal-benefit
or route-independent claim. The analyzer's existing seven combined checks remain
the previously recorded validation; this input-only run does not claim a new suite.

Full output SHA:
`a952b4a5ba0a50b72ed46f1db3258c52b2f3600a217831598b89f4e5f6cc2734`.
Analyzer SHA:
`7759d7fe70479489ab2c90f3f16de8a097099f3c750325c33548e708d4b2b3f0`.
Twenty-four development cells, separate held-out evaluation and R2 remain open.
