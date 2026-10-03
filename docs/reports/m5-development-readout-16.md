# Partial fixed-development paired readout

The [analysis tool](../../scripts/analyze_memory_matrix.py) completed its first
retained-data invocation on `4229820` in 0.273 s supervised, reading the four
explicitly pinned successful C3, C4, remaining-01 and remaining-02 reports.
The [evidence index](m5-development-readout-16.json) binds the exact inputs,
command, output and checks. No model, simulation, writer lease or held-out data
was used. This summarizes already audited reports; it is not a fresh raw audit.

Coverage is **16 of 48 cells**, 144 condition readouts and 128 paired comparisons
of own against each of the other eight conditions. All eight seed namespaces are
represented, but only seed 24 has all six cells at this stage. Thirty-two cells
remain. Four historical C3 cells retain broader core differences; twelve C4/new
cells retain strict core forks. They are separate analysis strata.

| Paired metric (`own - reference`) | Observed result |
| --- | --- |
| Evaluator task pass | 128 ties |
| Goal boundary | 123 ties; own is one tick later in five pairs |
| Stale-value correction | 48 ties in six change cells; not applicable in 80 null/no-event pairs |

No own-U task or correction/goal-timing advantage appears in these completed
cells. All five null cells still have false targeting, and the five no-event
cells have no actual selector invocation. Exact targeting, precision/recall,
actual invocation/behavior bytes, per-fact observations, confirmations and
uncertainty intervals remain visible in the JSON output. This is a partial,
fixed-route result, not a route-independent memory conclusion.

The analysis preserves per-cell pairing and eight shared namespace blocks. It
reports timing means only within explicit regime/schedule/closure-side/fork
strata, with the paired denominator and missing counts. It never substitutes a
timeout boundary for an unobserved event or treats a null confirmation as a
stale correction. No significance test or independent-frame inference is made.

One synthetic check covers full/partial matrix membership, historical versus
strict strata, timing direction and censoring, missing/duplicate/foreign reports,
wrong gold-side attribution, contradictory targeting metrics and changed input
hashes. The latest check passed in 0.156 s. Review tightened gold-subject and
targeting consistency before the first actual readout; no actual-data retry was
needed. The original experiment reports and failures remain unchanged.

The complete stdout JSON SHA is
`6d474ad8ab69069da723dc92527cc6977ac3ca4d8ce714e986e4457f0c6c40d9`.
The analyzer SHA is
`7759d7fe70479489ab2c90f3f16de8a097099f3c750325c33548e708d4b2b3f0`.
R2 and held-out qualification remain incomplete, even when a later input set
fills all 48 development cells.
