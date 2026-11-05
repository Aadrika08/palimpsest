# Standalone finite-candidate change audit

This package implements the approved Palimpsest audit, rather than rebuilding
upstream PAC-Bayes or importing its unavailable model overlay. It pins installed
Lean 4.31.0 and mathlib `fabf563a7c95a166b8d7b6efca11c8b4dc9d911f`.

**Locally verified, 5 November 2026:** all nine modules pass one coherent
serial Lean build (`evidence/build-full-verification-02.json`), with unchanged
source/configuration hashes and no warnings. Serial Lake module builds and the
final default `lake --no-cache build` pass (`serial-lake-verification-01.json`).
All 17 exported axiom reports contain only `propext`, `Classical.choice` and
`Quot.sound`. `evidence/verification-summary.json` binds these checks and their
resource records. The parent independently repeated the default Lake build and Audit kernel
check, verified all 17 axiom reports, and checked unchanged source/configuration
hashes; its receipt is `evidence/parent-independent-verification.json`. No
research simulation, training or empirical improvement certificate was executed.
The memory sampler, population target and conditional-MGF assumptions remain
empirical/modeling obligations, not consequences of these proof builds.

## Statistical boundary

Each observation is a whole scenario/family; correlated kinds are averaged
within that family first. An observed contrast is candidate loss minus baseline
loss, in [-1,1] when each loss is in [0,1]. Negative expected contrast is better.
The candidate family, baseline, sampling/evaluation law, loss, alpha and betting
scale are fixed before audit observations. Candidate comparisons may share a
scenario and be correlated; no independence across candidates is required.

`FreshBounded` records actual mathematical measurability, fresh-increment
independence, mean-zero centering and width-two bounds. Its center may differ
at every position. `freshOfContrasts` constructs it from explicit deterministic
per-position means. The separate `ConditionalMGF` interface allows more general
predictable conditional means, provided the conditional exponential-moment
bound, adaptedness and integrability are established. It does not assume a tail
probability conclusion.

The target is the prefix average of the stated expected contrasts. With a
blocked or stratified schedule it is not automatically one fixed iid population
risk. Deterministic catalog balance and valid replay hashes cannot prove a
sampling law, and a conditional-mean guarantee does not establish generalization
to an unspecified future family population.

## Modules

- `Contrast`: bounded losses give width-two contrasts; centered sub-Gaussian
  one-position fact. This alone does not establish fresh sampling.
- `Exponential`: the conditional-MGF premises construct a nonnegative
  exponential supermartingale.
- `FreshBounded`: width-two fresh increments discharge those premises, including
  adaptedness and integrability.
- `Ville`: attributed adaptation of the upstream standalone Ville proof.
- `Anytime`: fixed positive betting scale, all positive prefix lengths, then a
  finite union over deterministic candidates. No Gibbs posterior is required.
- `FixedHorizon`: a predeclared horizon-specific optimal scale gives the usual
  square-root bound. Recomputing this scale after audit-driven stopping is not
  justified by that theorem.
- `Numerical`: exact finite Taylor lower sums certify an upper logarithm budget;
  conservative rational endpoints imply the real-valued mathematical gate.
- `Targets`: explicit target-minus-observation prefix identity, deterministic
  fresh-contrast constructor, non-strict and strict false-acceptance theorems.
- `Audit`: exact arithmetic fixtures and `#print axioms` for exported results.
  Fixtures are not scientific task outcomes.

For K candidates and fresh contrasts in [-1,1], the one-sided bounds are
`sqrt(2 log(K/alpha)/n)` at a fixed horizon and
`log(K/alpha)/(lambda*n) + lambda/2` at all prefixes for a fixed positive lambda.
The latter's nonvanishing floor must not be confused with a vanishing fixed-
horizon radius. Multiple directions, rounds or betting scales need their own
explicit failure-budget allocation.

## Evidence and numerical bridge

Run `python evidence/build_proofs.py UNIQUE-LABEL` to compile only this package's
sources serially with `lean -j1 -M4096` with a 5.5 GiB MemAvailable preflight (measured-RSS amendment retained). The script never fetches or automatically
builds dependencies. It retains each command, exit status, source hash, log and
post-build source-identity check. It refuses replacement of prior build evidence.
`Audit` prints the theorem axiom dependencies. No sorry/admit/custom axioms or
native computation shortcut are permitted.

The runtime rational checker is `paper/studies/change_audit_v1/check.py` at the
repository root. Its arithmetic/completeness tests are separate from these
proofs. The Lean bridge proves the mathematics of rational enclosures; it does
not formally verify the Python parser, infer sampling assumptions from a
manifest, certify proof-receipt authenticity, or assert a simulator outcome.
Strict acceptance uses an upper endpoint strictly below the negative margin;
its false-positive event includes equality of the true contrast to that margin.

## Dependencies, provenance and resource failures

`.lake` and compiled cache are excluded from source control. The pinned mathlib `lakefile.lean:143–147` has a `post_update` hook that
automatically fetches the full cache unless `MATHLIB_NO_CACHE_ON_UPDATE=1`.
Future dependency bootstrapping must use that flag and a separately bounded
target-only acquisition; do not run plain `lake update`. The original
automatic `lake update` started a full mathlib cache fetch and breached its
4 GiB dependency cap. `evidence/dependency-cap-breach.json` preserves this real
failure; it is not retrospectively declared compliant. Partial files were not
deleted. Subsequent corrective work uses a separately admitted cumulative
4 GiB increment over its recorded `.lake` plus archive-cache baseline and a
6 GiB free-space floor, serial target-only archive processing and retained logs.
The wrong extraction base for early non-mathlib archives is also retained in
wave-01 records; wave-02 fixed the base and stopped on sandbox DNS failure.
The first manifest exporter omitted its first requested root because the cache
CLI parser consumes a command argument. Its five-root subset was still needed;
the corrected exporter adds a command sentinel and asserts the complete root
count. The additional 19-module closure is retained separately, without
replacing earlier manifests or resetting the cumulative corrective allocation.

`third_party/provenance.json` pins the reused Ville helper to its exact upstream
revision, Git blob and SHA-256. Original bytes, copyright header and complete
Apache-2.0 license are retained. The adapted helper removes an unrelated Metis
narrative; this reuse is not a new-theorem novelty claim. Other project-owned
source licensing follows the repository's separate contributor-authority review.
