# Fixed-development paired readout: 44 accepted cells

The unchanged [analyzer](../../scripts/analyze_memory_matrix.py) completes the
11-report readout on `fabfedc` in **0.683 seconds supervised**, first invocation
with exit 0. Inputs are audited C3, C4 and remaining-01–06, 08–10 comparison
reports. The [index](m5-development-readout-44.json) pins inputs, exact command,
limits and output. This summarizes existing reports without new model, simulation,
writer lease, held-out data or raw-record audit. The earlier
[24-cell snapshot](m5-development-readout-24.md) remains unchanged.

Coverage is **44/48 cells**, 396 condition readouts and 352 own-versus-reference
pairs. Seeds 24–27 and 30–31 each retain six cells; seed 28 has five and seed 29
has three. Four historical C3 cells retain broader core differences; forty later
cells retain strict core forks. The failed remaining-07 batch remains excluded:
`s28/paired_cue/no-event`, and `s29/local_cue/{change,null,no-event}` are missing.
Its proposed repeat requires the separate pending amendment.

| Paired metric (`own - reference`) | Observed result |
| --- | --- |
| Evaluator task pass | 352 ties |
| Goal boundary | 340 ties; own one tick later in 12 pairs |
| Stale-value correction | 120 ties in 15 change cells; not applicable in 232 null/no-event pairs |

There is **no observed own-U task, correction or goal-timing advantage**. All
15 null cells retain false targeting; all 14 no-event cells have zero selector
invocations and behavior bytes. Exact per-condition targeting, observations,
confirmations and censoring remain in the full output.

The analysis preserves paired seed, regime, schedule, closure-side and fork
strata. Null confirmations are not stale corrections, and missing events are not
assigned timeout boundaries. Shared namespaces and fixed lower-goal geometry
preclude independent-frame, significance, causal-benefit or route-independent
claims. Full-matrix evaluation, held-out work and R2 remain open.

The readout uses a prospective 30-second limit and 4 MiB per analysis log stream;
this does not change any experimental owner limit. Output is 905,760 bytes,
SHA-256 `987996212a4af69a05d80b68788df51cf1d9897d7c27a006d3cc363fc21b0959`.
Analyzer SHA remains
`7759d7fe70479489ab2c90f3f16de8a097099f3c750325c33548e708d4b2b3f0`.
Its existing checks remain covered by the recorded combined regression; no new
suite is claimed for this input-only readout.
