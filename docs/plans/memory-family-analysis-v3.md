# Memory family v3: prospective analysis contract

8 October 2026. Software-only implementation plan, stacked on the verified
family producer contract at `392bfe1`. This plan freezes analysis choices before
any development owner, held-out family ID, or scientific outcome is opened. It
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
generator and balanced assignment. The result must carry that assumption; IDs
and hashes do not prove statistical independence or generalization beyond this
catalog.

Use one complete 48-family development block and, only after its technical and
precision gate passes, one independently selected 48-family held-out block.
Development block zero is fixed. The held-out block is selected uniformly from
the registered block range with an independently retained CSPRNG receipt after
the development gate closes; no held-out IDs may be materialized earlier.
Development and held-out results are never pooled.

## Frozen estimands and inference

For reference `r` in `no-U, swapped`, family `f`, and kind `k` in
`change, null, no-event`, retain the existing paired score difference
`D[f,k,r] = capped_ticks(own) - capped_ticks(r)`. A natural continuation failure
is 900; acquisition, owner, audit, or other infrastructure failure is unscored.
The primary family value is the equal mean of its three `D` values. Families are
then weighted equally. Negative cost favors own.

Use a blocked paired Student interval: calculate a mean and unbiased variance
inside each 16-family cost stratum, weight the three stratum means by 1/3, and
use the Satterthwaite standard error/degrees of freedom. A zero estimated
variance produces a point interval and is reported. For the two primary
contrasts use two-sided 97.5% intervals, preserving the already chosen 5%
familywise Bonferroni rule. This is a model-based interval, not distribution-free
coverage.

Freeze the following practical margins as stakeholder choices based only on the
900-tick task scale, not on the correlated pilot:

- meaningful benefit: 90 ticks (10% of the cap, 1.8 simulated seconds);
- acceptable cost harm: 45 ticks (5% of the cap, 0.9 simulated seconds);
- acceptable null/no-event own-only failure probability: 1/16 = 0.0625.

The primary benefit claim is an intersection: both primary upper bounds must be
strictly below -90. An adequately precise null requires both complete primary
intervals to lie strictly inside `(-90, 45)`. A primary harm result requires at
least one Bonferroni interval lower bound strictly above 45. Equality never
passes a margin. Other configurations are inconclusive or mixed.

An overall result cannot hide null/no-event harm. For each reference and each of
those two kinds, require a one-sided 95% blocked-t upper cost bound strictly below
45. Also require zero observed events where own fails and the reference reaches
the goal. With 48 independent families, the conservative zero-event upper bound
`-log(0.05)/48` is below 1/16; any observed own-only failure fails the guard.
These components form one all-pass intersection gate. Report component values,
but do not advertise separate population claims for them.

The development phase makes no benefit/null/harm claim. It may open held-out
registration only when the full matrix and all upstream checks pass and both
primary interval half-widths are at most 45 ticks. The mean effect and development
guard outcomes cannot stop, resize, or alter the held-out study. Failure of the
precision gate ends this design as infeasible; it does not authorize extra
families or weaker margins.

## Order, stopping, and evidence boundary

Assign condition order by the frozen nine-condition cyclic Latin schedule for
family row `r`: rotate the canonical condition list left by `r mod 9`. Across 48
rows, every condition occupies every position five or six times, the minimum
possible imbalance. Each condition still forks the same source snapshot in an
independent owner. The future launcher must bind and verify the scheduled order;
the analysis accepts only its authenticated receipt.

There are zero interim analyses, efficacy/futility stops, automatic retries,
replacement families, fallback profiles, threshold changes, or post-result
extensions. Dispositions are exact:

- audited natural continuation task failure: score 900 and continue;
- source acquisition failure: score nothing and stop that family before forks;
- owner, raw-audit, provenance, invariant, resource, deadline, or cleanup
  failure: score nothing, stop the phase, and retain the partial evidence;
- any missing/unscored cell or failed prerequisite: descriptive partial readout
  only, with no interval or scientific disposition.

Every analysis requires passed, hash-bound receipts for family sampling,
provenance, assignment balance, condition order, and held-out access sequencing.
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

- [ ] Write the exact canonical protocol and assert strict rejection of missing,
  unknown, nonfinite, Boolean-substituted, or altered fields.
- [ ] Pin the cyclic order, 16/16/16 strata, exact 48-family phase count, margins,
  confidence levels, no-interim rule, and split sequencing.
- [ ] Add a regression proving acquisition-phase failures are unscored and never
  converted to the 900-point natural continuation outcome.
- [ ] Add synthetic 48-family checks for interval arithmetic, strict boundaries,
  development precision, held-out benefit/null/harm/inconclusive dispositions,
  null/no-event cost guards, zero-event success guards, immutable inputs, and
  refusal on incomplete or unverified evidence.
- [ ] Run the focused tests and record the expected failures before implementation.

### Task 2: Implement the smallest pure analyzer

**Files:**
- Create: `scripts/memory_family_analysis_v3.py`
- Modify: `scripts/memory_confirmatory_v3.py`

- [ ] Implement exact protocol validation and deterministic condition ordering.
- [ ] Recompute the retained family/kind contrasts from readout cells, rejecting
  mismatches with the descriptive vectors and any unexpected family count/order.
- [ ] Implement blocked Satterthwaite intervals, the zero-event upper bound,
  development precision gate, held-out decision table, strict margin comparisons,
  and fail-closed evidence bindings.
- [ ] Keep the analyzer pure, bounded, deterministic, JSON-safe, and explicit
  about its model assumption and inability to prove upstream attestations.
- [ ] Remove acquisition-phase causes from natural continuation failures; retain
  them as a named unscored infrastructure disposition.

### Task 3: Bind semantics through the producer

**Files:**
- Modify: `scripts/memory_family_producer_v3.py`
- Modify: `tests/test_memory_family_producer_v3.py`

- [ ] Validate the protocol semantically in both producer registration paths,
  rather than accepting any canonical JSON object.
- [ ] Add the analysis module to the producer dependency inventory and preserve
  the existing protocol digest in job/admission envelopes.
- [ ] Reject a canonical but scientifically altered protocol without writing or
  launching anything. Preserve every zero-allocation sentinel.

### Task 4: Verify, review, and publish the boundary

**Files:**
- Create: `docs/reports/memory-family-analysis-v3.md`
- Create: `docs/reports/memory-family-analysis-v3-evidence/verification.json`

- [ ] Run focused analysis/readout/producer tests, then the affected family,
  oracle, admission, snapshot, artifact, and replay slice. Compile changed Python
  files and run `git diff --check`.
- [ ] Independently review estimands, interval arithmetic, multiplicity, exact
  boundaries, incomplete-matrix refusal, acquisition disposition, protocol
  binding, and all evidence claims. Fix material findings once and rerun the
  affected checks.
- [ ] Record exact commands, results, hashes, assumptions, and remaining blockers.
  Commit as Aadrika Maurya, push through Aadrika08, and open a draft PR stacked on
  PR #100. Do not merge or allocate a native study.

Storage, the complete historical namespace inventory, a hash-bound launcher,
actual upstream check receipts, native family qualification, and the entire
development/held-out collection remain outside this unit. The current roughly
559 GB known storage shortfall continues to make native allocation inadmissible.
