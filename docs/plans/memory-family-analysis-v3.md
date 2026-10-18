# Memory family v3: prospective analysis contract

8 October 2026. Software-only implementation plan, stacked on the verified
family producer contract at `392bfe1`. This plan freezes analysis choices before
any development owner, selected held-out block, or scientific outcome is opened. It
does not allocate storage, launch a model, qualify family independence, or make
an R2 claim.

## Decision

Keep the existing complete-family readout descriptive. Add one separate pure
analysis module and one canonical protocol file, then bind both through the
existing producer registration. The analysis consumes only a complete readout
and hash-bound upstream check receipts. It never reads recordings, snapshots,
models, or owner state.

The target is the narrow registered `memory-family-v3` generator/catalog under
the frozen CPU FLYNN controller and equal 1/3 change/null/no-event mixture. The
analysis is model-based: it treats distinct generated families as independent
within the three fixed route-cost strata, conditional on the registered
generator and balanced assignment. Within-stratum Student coverage additionally
uses a stated approximate-normal sampling model for the bounded family contrasts.
The result must carry those assumptions; IDs and hashes do not prove statistical
independence, normality, or generalization beyond this catalog.

Use one complete 48-family development block and, only after its technical and
precision gate passes, one independently selected 48-family held-out block.
Development block zero is fixed. After the development gate closes, held-out
selection makes exactly one `os.getrandom(3)` call, masks the high bit of the
big-endian integer to obtain a uniform 23-bit block index, and permits no redraw.
Its canonical receipt retains the six raw hex digits, selected index, draw count
one, redraw count zero, source/runtime hashes, and exclusive-publication proof
before any selected case construction. Publication failure stops the design.
The selected index, collection, and outcomes may not
be opened earlier. Generic candidate IDs remain publicly enumerable from the
deterministic generator and are not represented as secret. The draw prevents
selective block choice; it does not create the 48-family independence assumption.
Development and held-out results are never pooled.

## Frozen estimands and inference

For reference `r` in `no-U, swapped`, family `f`, and kind `k` in
`change, null, no-event`, retain the existing paired score difference
`D[f,k,r] = capped_ticks(own) - capped_ticks(r)`. A natural continuation failure
is 900; acquisition, owner, audit, or other infrastructure failure is unscored.
The primary family value is the equal mean of its three `D` values. Families are
then weighted equally. Negative cost favors own.

Use a blocked paired Student interval. For stratum `h`, calculate mean `m[h]`,
unbiased variance `s2[h]`, and `v[h] = (1/3)^2 * s2[h] / 16`. The overall mean is
`sum(m[h])/3`, standard error is `sqrt(sum(v[h]))`, and Satterthwaite degrees of
freedom are `sum(v[h])^2 / sum(v[h]^2/15)`. Use `scipy.stats.t.ppf` from the pinned
simulation dependency for critical values. If the total standard error is zero,
or any formula is nonfinite, fail inference closed; identical observed values do
not prove zero generator variance. For the two primary contrasts use two-sided
97.5% nominal intervals, preserving the already chosen 5% familywise Bonferroni
rule. This is approximate model-based coverage, not an exact or distribution-free
guarantee.

Freeze the following prospective utility choices, not values learned from the
correlated pilot:

- meaningful benefit: 90 ticks (10% of the cap, 1.8 simulated seconds);
- acceptable cost harm: 45 ticks (5% of the cap, 0.9 simulated seconds);
- acceptable null own-only failure probability: 1/16 = 0.0625, an
  operational tolerance of one additional failure per 16-family cost stratum in
  expectation rather than a conversion from ticks.

The primary benefit claim is an intersection: both primary upper bounds must be
strictly below -90. An adequately precise null requires both complete primary
intervals to lie strictly inside `(-90, 45)`. A primary harm result requires at
least one Bonferroni interval lower bound strictly above 45. Equality never
passes a margin. Any zero-variance or nonfinite primary or null-cost interval is
`variance-unresolved` before classification. Otherwise compute
`primary_disposition` before guardrails. Final benefit or supported-null requires
that primary disposition and every guard pass; primary harm overrides guards;
an observed own-only failure is `observed-guardrail-harm`; a benefit or
supported-null primary with another failed guard is `guardrail-not-established`;
all remaining configurations are `inconclusive`. This is one global all-pass
intersection claim. No component-level population claim is permitted.

An overall result cannot hide null harm. For each reference in the null case kind,
require a one-sided 95% blocked-t upper cost bound strictly below 45 and zero
observed events where own fails and the reference reaches the goal. With 48
independent families, the conservative zero-event upper bound `-log(0.05)/48` is
below 1/16; any observed own-only failure fails that guard. No-event is a
structural control rather than an estimated harm endpoint: every family must have
exact all-nine-condition trace, goal, duration, path, capped score, and terminal
outcome equality, backed by the upstream zero-selector/zero-behavior receipt. A no-event
mismatch is an invariant failure, not sampling variation.
These components form one all-pass intersection gate. Report component values,
but do not advertise separate population claims for them.

The development phase makes no benefit/null/harm claim. It may open held-out
registration only when the full matrix and all upstream checks pass, every
primary and null cost interval has nonzero finite estimated variance,
all four cost-interval half-widths are at most 45 ticks, and the no-event exact
invariant passes. This plug-in check is
a prespecified feasibility screen, not a guarantee of held-out precision. The
mean effect and development guard outcomes cannot stop, resize, or alter the
held-out study. Failure of the precision screen ends this design as infeasible;
it does not authorize extra families or weaker margins.

## Order, stopping, and evidence boundary

Run declared prerequisites first in registration order. Then interleave the three
16-row cost strata: for within-stratum index `i = 0..15`, visit all three strata
in the cyclic order starting at `i mod 3`. This spreads south/north/tie families
across the full execution epoch instead of confounding stratum with elapsed time.
Within family row `r`, rotate change/null/no-event left by `r mod 3`; every kind
therefore occupies every within-family position 16 times.
Each case runs its source acquisition before any fork, followed by the frozen
nine-condition cyclic schedule for family row `r`: rotate the canonical condition
list left by `r mod 9`. Across 48 rows, every condition occupies every position
five or six times, the minimum possible imbalance. The future launcher must bind
and verify this complete 1,440 study-owner order after prerequisites; the analysis
accepts only its authenticated receipt. Order is a drift control, not an
independent sample.

There are zero within-phase interim analyses or outcome-based efficacy/futility
stops, automatic retries, replacement families, fallback profiles, threshold
changes, or post-result extensions. The fixed development precision screen is the
only between-phase feasibility stop. Dispositions are exact:

- audited natural continuation task failure: score 900 and continue;
- source acquisition failure: score nothing and stop the phase before any more
  study owners; the incomplete matrix cannot support inference;
- owner, raw-audit, provenance, invariant, resource, deadline, or cleanup
  failure: score nothing, stop the phase, and retain the partial evidence;
- any missing/unscored cell or failed prerequisite: descriptive partial readout
  only, with no interval or scientific disposition.

Every analysis envelope contains the canonical protocol, descriptive readout,
producer-derived analysis design, and verification object. The analysis design
regenerates all 48 family IDs, rows and cost strata from split/block and binds the
protocol and family-design hashes. The verification object exactly binds the
registration, protocol, plan, readout and six passed receipts for family
sampling, provenance, assignment balance, complete owner order, and access
sequencing, plus the no-event zero-selector/behavior invariant. Held-out verification also carries the raw selection receipt and
recomputes its masked index. Inputs are bounded canonical JSON; the CLI emits one JSON result.
A bare Boolean or caller-supplied family-to-stratum map is insufficient.

A held-out analysis additionally requires the frozen development-gate receipt.
The pure analyzer checks bindings and arithmetic; it cannot establish that the
receipt producer told the truth. Independent scientific close remains separate,
and every output keeps `r2_complete=false` and empty qualification claims.

## Implementation tasks

### Task 1: Pin the contract and the existing acquisition boundary

**Files:**
- Create: `docs/plans/memory-family-analysis-v3-protocol.json`
- Create: `tests/test_memory_family_analysis_v3.py`
- Modify: `tests/test_memory_confirmatory_v3.py`
- Modify: `docs/plans/memory-confirmatory-v3-design.md`

- [x] Write the exact canonical protocol and assert strict rejection of missing,
  unknown, nonfinite, Boolean-substituted, or altered fields.
- [x] Pin the cyclic order, 16/16/16 strata, exact 48-family phase count, margins,
  confidence levels, no-interim rule, and split sequencing.
- [x] Amend the older design explicitly: thresholds and the full estimator are
  now frozen before development; development may test only the fixed precision
  screen and technical prerequisites before held-out access.
- [x] Add a regression proving acquisition-phase failures are unscored and never
  converted to the 900-point natural continuation outcome.
- [x] Add synthetic 48-family checks for interval arithmetic, strict boundaries,
  development precision, held-out benefit/null/harm/inconclusive dispositions,
  null cost/success guards, exact no-event guards, immutable inputs, and
  refusal on incomplete or unverified evidence.
- [x] Run the focused tests and record the expected failures before implementation.

### Task 2: Implement the smallest pure analyzer

**Files:**
- Create: `scripts/memory_family_analysis_v3.py`
- Modify: `scripts/memory_confirmatory_v3.py`

- [x] Implement exact protocol validation, regenerated analysis design, complete
  deterministic owner ordering, and one bounded strict-JSON CLI envelope.
- [x] Recompute the retained family/kind contrasts from readout cells, rejecting
  mismatches with the descriptive vectors and any unexpected family count/order.
- [x] Implement blocked Satterthwaite intervals with zero-variance refusal, the
  zero-event upper bound,
  development precision gate, held-out decision table, strict margin comparisons,
  and fail-closed evidence bindings.
- [x] Keep the analyzer pure, bounded, deterministic, JSON-safe, and explicit
  about its model assumption and inability to prove upstream attestations.
- [x] Remove acquisition-phase causes from natural continuation failures; retain
  them as a named unscored infrastructure disposition.

### Task 3: Bind semantics through the producer

**Files:**
- Modify: `scripts/memory_family_producer_v3.py`
- Modify: `tests/test_memory_family_producer_v3.py`

- [x] Validate the protocol semantically in both producer registration paths,
  rather than accepting any canonical JSON object.
- [x] Embed the exact regenerated analysis design and cross-check protocol split,
  development block zero, family order/strata, and condition/owner order.
- [x] Add the analysis module to the producer dependency inventory and preserve
  the existing protocol digest in job/admission envelopes.
- [x] Reject a canonical but scientifically altered protocol without writing or
  launching anything. Preserve every zero-allocation sentinel.

### Task 4: Verify, review, and publish the boundary

**Files:**
- Create: `docs/reports/memory-family-analysis-v3.md`
- Create: `docs/reports/memory-family-analysis-v3-evidence/verification.json`

- [x] Run focused analysis/readout/producer tests, then the affected family,
  oracle, admission, snapshot, artifact, and replay slice. Compile changed Python
  files and run `git diff --check`.
- [x] Independently review estimands, interval arithmetic, multiplicity, exact
  boundaries, incomplete-matrix refusal, acquisition disposition, protocol
  binding, and all evidence claims. Fix material findings once and rerun the
  affected checks.
- [x] Record exact commands, results, hashes, assumptions, and remaining blockers.
  Commit as Aadrika Maurya, push through Aadrika08, and open a draft PR stacked on
  PR #100. Do not merge or allocate a native study.

Storage, the complete historical namespace inventory, a hash-bound launcher,
actual upstream check receipts, native family qualification, and the entire
development/held-out collection remain outside this unit. The current roughly
559 GB known storage shortfall continues to make native allocation inadmissible.
