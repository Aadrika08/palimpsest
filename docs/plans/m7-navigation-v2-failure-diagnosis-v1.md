# M7 navigation-v2 failure diagnosis v1

8 October 2026. This is the prospective contract for one read-only diagnosis
of the completed navigation-v2 development batch. It asks why the augmented
training arm reached 0/4 goals for every seed while the old-corpus arm reached
2/4, 1/4 and 1/4 on matched scenes. It does not rerun or reclassify that failed
gate. The earlier seed-11 diagnosis covers different scenes and models and does
not answer this comparison.

The canonical [JSON protocol](m7-navigation-v2-failure-diagnosis-v1.json)
enumerates all 24 case IDs, run IDs, outcomes and tick counts from the already
published compact index. Its input is exactly producer `e3f9a47`, index SHA-256
`850c6337e1fa4e2916751a8f02c20dae4a9ba347eb88eb3f17d17cedb065dc71`,
10,822 numeric ticks and the 542-file / 2,382,058,832-byte retained raw ledger.
Scenes 3120–3127 are forbidden. The diagnosis opens no unreported result.

## Fixed analysis

For each run, the analyzer reads only `action`, `control`, `pose`, `next_pose`,
`sensors` and `simulation_time` from the published numeric chunks. It validates
the complete chunk files and their metadata without loading camera members. It
reads the initial goal only from the existing episode-start event. It computes:

- initial, minimum and final goal distance; best/net progress and regression
  from the closest point;
- path length, contact count and terminal contact suffix;
- the terminal suffix satisfying the native stall operands: step movement below
  0.002 m and absolute velocity command above 0.05;
- reverse/stopped command counts, velocity/heading sign changes and mean absolute
  commands; and
- for each matched scene/seed, old-versus-augmented action divergence over the
  common executed prefix using the fixed 1e-6 absolute threshold.

The mutually exclusive terminal classes are mechanical descriptions only:
`goal`, `terminal-contact-stall`, `terminal-clear-stall`,
`terminal-contact-time-limit`, and `terminal-clear-time-limit`. “Contact” here
means the final recorded collision sensor is true. Suffix lengths preserve how
persistent it was. The report aggregates by arm, seed, outcome and terminal
class. It performs no significance test and makes no causal, capability,
topology, biological, hardware or R3 claim.

## Trust and resource boundary

The analyzer rejects duplicate/nonfinite JSON, symlinks, unsafe paths, any case
or ledger drift, missing/extra runs, changed hashes, malformed numeric fields,
noncontiguous ticks, unexpected outcomes, and input changes between its complete
before/after hash passes. The output directory must be new and disjoint from the
input. A failure is retained as a failed diagnostic, never a partial result.

One actual invocation has a 300-second deadline, a 3 GiB input ceiling, a
16 MiB output ceiling and a 1 GiB free-space floor. It imports NumPy and the
standard library only. Torch, MuJoCo, model loading, inference, fitting, physics,
camera decoding and snapshot decoding are forbidden. Tests use authored tiny
recordings and do not consume the retained batch. The actual invocation occurs
at most once, after focused tests and source review pass.

## Implementation sequence

1. Commit this plan and protocol before any retained trajectory is decoded.
2. Add failing tests for exact protocol/case admission, selective numeric reads,
   measures, pairing, terminal classes, provenance drift, resource limits and
   forbidden imports/held-out paths.
3. Implement the smallest standalone analyzer using the recording format and
   SHA helpers already present in Palimpsest.
4. Run focused synthetic tests and review the source. Only then run the one
   bounded retained-data invocation in an exclusive output directory.
5. Independently recheck the output, publish a byte-identical compact JSON report
   plus a Markdown interpretation, and retain limits and uncertainty.

Any later navigation-v3 study is separate. Before execution it must freeze one
training change, matched budgets and controls, fresh disjoint development and
held-out reserves, capability and topology estimands, stopping rules and the
existing per-seed 3/4 development then 6/8 held-out release gates.
