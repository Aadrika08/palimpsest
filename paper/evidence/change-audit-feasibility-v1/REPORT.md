# Change-audit feasibility: bounded investigation

Date: 5 November 2026. Parent worktree baseline: `c9e8e66c35d730a1f62f37557a952b55db8406a0`.
Upstream: `862dcb02c0dffeefd6955293345770f726d8ef95`.
Status: **numerical reconstruction passed; conditional research opportunity; no Palimpsest improvement certificate**.

## Decision

The papers suggest a useful downstream question for authority-aware replay:
can a recorded change support a statistically valid claim of improved task performance?
Palimpsest can supply the identity and execution evidence; it cannot supply the
sampling assumptions or a beneficial controller by replaying an old trajectory.

Proceed with a separately frozen small plumbing pilot after the adapter/sampling
contract below is implemented and checked. Do not launch a large certification study
or change the submitted scientific argument on this evidence. Existing engineering
repetitions are ineligible for a new population-improvement claim.

This investigation used the supplied abstract screenshots and the public artifact.
OpenReview forum/API access returned a verification challenge; the complete PDFs
were not obtained or reviewed. The source audit is not a full theorem/proof audit.

## What executed

The unchanged upstream `scripts/reproduce_headline.py` ran under the existing
Python 3.11.15 / NumPy 2.2.5 environment, exit 0 in 0.3314 seconds. See
[stdout](upstream-reproduction/stdout.log),
[execution metadata](upstream-reproduction/reproduction.json), and
[hash inventory](upstream-reproduction/download-inventory.json).

- 200 paired sample means reconstructed exactly: 100 remote-sensing and 100 Walsh.
- 100 stored remote-sensing radii checked. **No Walsh radius assertions ran**,
  because its records lack the field used by that conditional branch.
- Every released round used 32,768 observations. This does not demonstrate
  an early-stopping benefit or establish that our simulator meets the assumptions.
- Printed held-out percentages were parsed from released TSV summaries;
  held-out model inference was not rerun. They are not independent reproduced
  experimental evaluations.
- Nineteen upstream files were pinned, including README, Apache-2.0 LICENSE,
  numerical inputs and six audited Lean files. No packages were installed.
- No training, new simulator episodes, Lean compilation, theorem certification,
  or changes to the manuscript or historical measured results occurred.

Initial sandbox mount initialization and a subsequent `/tmp` clone/write probe
failed with quota errors. Failed partial paths remain retained. The authorized
project worktree accepted the small evidence download and kept more than 6 GiB
free. First-party account quota telemetry was unavailable; quota remains unknown.
The bounded work used two independent agent lanes, one numerical and one
mathematical, integrated by the parent.

## Assumption audit

All links refer to the pinned upstream revision; copies are retained under
`upstream-reproduction/upstream/lean/`.

| Requirement | Evidence and implication for Palimpsest |
| --- | --- |
| Valid statistical process | [AnytimePACBayes lines 97–113 and 385–392](https://github.com/noumenal-ai/anytime-anywhere-pac-bayes/blob/862dcb02c0dffeefd6955293345770f726d8ef95/lean/E_star_export/lean/CertifiedPolicyTheory/Core/AnytimePACBayes.lean#L97) require a supermartingale witness. Identity hashes and replay agreement do not establish it. |
| Fresh sampling | [FreshBoundedPairedIncrements, lines 456–470](https://github.com/noumenal-ai/anytime-anywhere-pac-bayes/blob/862dcb02c0dffeefd6955293345770f726d8ef95/lean/E_star_export/lean/CertifiedPolicyTheory/Core/AnytimePACBayes.lean#L456) requires independence from the past, boundedness, zero mean and adaptation. Whole-scenario fresh draws are a plausible construction; correlated ticks are not extra independent episodes. |
| Fixed target and reference | The core uses a fixed population-risk function, prior and comparator. Audit-adaptive posterior selection does not permit arbitrary post-hoc changes to the environment distribution, candidate family or prior. |
| Strictly positive finite laws | [PositiveFiniteLaw lines 21–25](https://github.com/noumenal-ai/anytime-anywhere-pac-bayes/blob/862dcb02c0dffeefd6955293345770f726d8ef95/lean/E_star_export/lean/CertifiedPolicyTheory/Core/PositiveFiniteLaw.lean#L21) excludes literal point masses on a multi-element family. Our deterministic-controller specialization is **not an instantiated Lean theorem**. A support extension or genuinely positive-mixture estimand is needed for that label. |
| Conditional-moment constants | Raw paired loss differences lie in [-1,1] for individual losses in [0,1]. Centered differences may lie in [-2,2]. The exported common-centered-interval constructor therefore gives a different compensator from a sharper pair-specific Hoeffding construction. Never interchange them. |
| Tail/selection accounting | [ConfidenceBridge lines 210–294](https://github.com/noumenal-ai/anytime-anywhere-pac-bayes/blob/862dcb02c0dffeefd6955293345770f726d8ef95/lean/E_star_export/lean/CertifiedPolicyThesis/ConfidenceBridge.lean#L210) allocates both tails. This feasibility calculation instead uses a **one-sided** familywise improvement gate; two-sided reporting must split its error budget. |
| Formal reproducibility | The [upstream README](https://github.com/noumenal-ai/anytime-anywhere-pac-bayes/blob/862dcb02c0dffeefd6955293345770f726d8ef95/README.md) says the Lean checkout lacks the toolchain and some imported overlays and cannot compile standalone. We read statements and code; we did not rebuild proofs. |

A Lean proof establishes its encoded proposition under its premises. It does not
automatically validate the simulator adapter, loss computation, audit independence,
asset provenance or data-selection practice.

## Independently derived comparison baseline

For K fixed candidate policies against one fixed baseline, define one observation
as a whole independent scenario, with losses in [0,1]. Let
`D_i = loss(candidate, scenario_i) - loss(baseline, scenario_i)`, so
`D_i in [-1,1]`. Negative mean means improvement.

For a single predeclared horizon n, Hoeffding plus a union over K candidates gives

`upper_n = mean(D_1..D_n) + sqrt(2 log(K/alpha) / n)`.

For a fixed, positive, pre-audit lambda, the conditional Hoeffding bound gives
an exponential supermartingale with compensator `lambda^2 / 2` per scenario.
Ville plus the finite candidate union gives an anytime upper endpoint

`upper_n = mean(D_1..D_n) + log(K/alpha)/(lambda n) + lambda/2`.

This second derivation handles deterministic fixed candidates independently of
the upstream strictly-positive-law API. It is **not Lean-certified**. Changing
lambda after observing outcomes requires a valid mixture/grid and its selection
penalty. Both formulas require the target/sampling assumptions; the fixed-horizon
formula is invalid for unaccounted arbitrary early stopping.

With K=3, alpha=.05, and lambda fixed using the design horizon 128:

| Independent scenarios | Fixed-horizon radius | Fixed-lambda anytime radius |
| ---: | ---: | ---: |
| 10 | 0.904914 | 1.745224 |
| 32 | 0.505862 | 0.632328 |
| 64 | 0.357699 | 0.379397 |
| 128 | 0.252931 | 0.252931 |
| 512 | 0.126466 | 0.158082 |

A fixed-horizon radius at most .20, .10 or .05 needs **205, 819 or 3,276**
independent scenarios, respectively. These are conservative radius requirements,
not power calculations or sample counts guaranteed to certify an improvement.
The fixed lambda chosen for horizon 128 has a limiting radius of .126466, so
more observations alone cannot reduce that particular anytime radius below .10.

[feasibility.json](feasibility.json) binds these calculations to the actual
compact campaign summary. It checks 111 descriptors, including 110 completed
and one incomplete, and ten matched execution-cost sets. Those checks validate
compact metadata consistency only. They do not independently revalidate the
raw traces or turn ten selected engineering seeds into population samples.

## Concrete next pilot, separate from certification

The [prospective pilot specification](../../studies/change_audit_feasibility_v1/pilot-proposal.json)
defines four fresh developmental scenarios and four separately executed policy
conditions, capped at 64 ticks per condition. It is deliberately a plumbing pilot,
not an improvement test. The proposed changes scale outgoing FLYNN forward
velocity by .5, .75 or 1.25, leaving heading and policy input unchanged; the
baseline uses gain 1. All conditions must execute the policy. Action replay
and playback cannot stand in for a modified policy rollout.

Candidate selection is a parent implementation choice, not an evidence-backed
claim that any gain is useful. The target research audit would use a separately
frozen full-episode task and outcome definition. Debug-pilot results must not be
pooled into that audit or used to tune candidates while retaining its original
selection penalty.

Before pilot launch: pin the adapter code, checkpoint/asset/renderer profile,
scenario factory and fresh draw mechanism; prove no protected held-out bank is
opened; restore identical full initial state before each branch; record all policy
calls and adapter gain in snapshots, manifests and loss provenance. Verify
resource admission before each condition. Keep failures rather than dropping
incomplete pairs. A timeout, quota breach, or unverifiable identity stops the
pilot and yields no certificate.

Pilot limits: CPU only, sequential, four whole scenarios, four conditions,
64 ticks each, 30 minutes overall, 120 seconds per condition, 512 MiB total new
runtime output, and 6 GiB disk reserve. No training, purchases, paid compute,
protected held-out access, relaxed qualification thresholds or cleanup.

The adapter is not implemented and this proposal is not launch-ready. A true
128-scenario/full-horizon audit needs a new runtime/output estimate and explicit
finite allocation; this investigation does not authorize exceeding the pilot cap.

## Verification and scope

Run the stdlib-only analysis/checks from the worktree root:

```sh
python3 -B -m unittest discover -s paper/studies/change_audit_feasibility_v1 -p 'test_*.py' -v
python3 -B paper/studies/change_audit_feasibility_v1/assess.py --summary paper/evidence/authority-replay-v1/summary.json --output NEW_PATH.json
```

Output creation is exclusive; retain the prior result. Tests exercise the
analytical boundary cases and rejection of inconsistent compact metadata. They
are software checks, not evidence that a controller improved.

The initial test run had one failed, mistyped decimal reference
(.2529342512 instead of .2529310850502965); the formula and retained planning output
were unchanged. The corrected test uses a known analytic value and also checks
the minimal integer count on both sides of the .10-radius boundary.
