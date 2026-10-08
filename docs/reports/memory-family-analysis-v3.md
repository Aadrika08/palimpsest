# Memory family v3 prospective analysis verification

**Date:** 8 October 2026  
**Implementation head:** `6b956181d4d80860835128b8b587f31d3e0b4a20`  
**Base:** `392bfe161ac2a07612b2602694728752d7bf1fc7`
(`research/memory-family-native-registration-v3`)  
**Handoff:** draft [PR #101](https://github.com/Aadrika08/palimpsest/pull/101),
stacked on draft PR #100; goal tracker `fd6b2f8`  
**Status:** verified software analysis contract; no study allocation or scientific
result

## Result

This unit freezes the analysis before any development outcome or selected
held-out block is opened. The canonical protocol hash is
`02e252fb5bdf41c48b2b384378e8a70eee98480829e25e1f0dcf269faebdce9b`.
Its regenerated development design hash is
`c70ba02adf06c7035145a5372437ae26545d004eee31c38bdef6927d8c25eb04`;
the 1,440-owner logical-order hash is
`9e0430eff26d606e2df081ae55294025d302b2aaf3de53ea2497a990a94e92b4`.

The analyzer accepts one bounded canonical envelope containing the protocol,
producer-derived design, complete descriptive readout and verification receipts.
It regenerates all 48 family identities and their 16/16/16 south, north and tie
strata; validates the complete 1,296-cell matrix; rejects duplicate run IDs,
per-case invariant drift, own/sham mismatch, altered descriptive contrasts and
no-event mismatch; and binds the result to the protocol, design, readout,
verification and producer registration hashes.

For each of `no-U` and `swapped`, the primary value is the equal mean of the
change, null and no-event paired cost differences within a family. The analyzer
then applies the registered blocked Satterthwaite interval with equal stratum
weights. The two primary intervals are 97.5% two-sided; the null-cost guards are
95% one-sided. Zero or nonfinite estimated variance fails inference closed.
Strict benefit, supported-null, harm, observed guardrail harm and inconclusive
outcomes follow the frozen decision table. Development emits no scientific
disposition and can only pass or fail the fixed four-endpoint precision screen.

No-event is checked as an exact nine-condition structural invariant. The null
success guard permits no observed own-only failures and uses the conservative
upper bound `-log(0.05)/48 = 0.062411...` against the registered `1/16 =
0.0625` margin. The margin exceeds that bound by only about `0.0000889`; every
future result must disclose this knife-edge relationship.

Acquisition timeout, incomplete acquisition and blocked acquisition now remain
unscored `acquisition-before-fork` failures. They cannot become the 900-tick
natural continuation outcome. The producer now rejects any semantically changed
protocol, embeds the regenerated design, and includes the analyzer in its source
dependency inventory. Existing pre-change v3 registration files are therefore
intentionally incompatible with this branch and must not be reused.

## Verification

The final analysis and readout command passed **53 tests in 10.92 seconds**:

```text
PYTHONPATH=src /home/utkarsh/Work/shraddha/brain/.worktrees/execution-recovery/.venv/bin/python -m pytest -q \
  tests/test_memory_family_analysis_v3.py \
  tests/test_memory_confirmatory_v3.py
```

The final producer command passed **35 tests in 70.59 seconds**:

```text
PYTHONPATH=src /home/utkarsh/Work/shraddha/brain/.worktrees/execution-recovery/.venv/bin/python -m pytest -q \
  tests/test_memory_family_producer_v3.py
```

The affected family, oracle, snapshot, artifact and replay slice passed **221
tests, with 7 skipped and 4 deselected, in 166.93 seconds**:

```text
PYTHONPATH=src /home/utkarsh/Work/shraddha/brain/.worktrees/execution-recovery/.venv/bin/python -m pytest -q \
  tests/test_artifacts.py \
  tests/test_memory_confirmatory_v3.py \
  tests/test_memory_decision_world.py \
  tests/test_memory_experiment.py \
  tests/test_memory_family_analysis_v3.py \
  tests/test_memory_family_oracle_admission_v3.py \
  tests/test_memory_family_oracle_v3.py \
  tests/test_memory_family_producer_v3.py \
  tests/test_memory_family_runtime.py \
  tests/test_memory_family_slots.py \
  tests/test_memory_family_world.py \
  tests/test_memory_task.py \
  tests/test_replay.py \
  tests/test_snapshots.py \
  -k 'not FlynnContinuation'
```

The four deselected `FlynnContinuation` cases require the absent upstream
`core` and `agents` modules from the uninitialized `upstream/fly-gym` fixture in
this worktree. An earlier undeselected run reached 215 passing and 7 skipped
tests before those four setup errors. The other snapshot cases passed: 10
passed, 3 skipped and 4 deselected. The affected run emitted 15 non-failing
Torch and Matplotlib warnings.

Compilation passed for all three changed scripts, and `git diff --check` passed:

```text
python -m py_compile \
  scripts/memory_family_analysis_v3.py \
  scripts/memory_confirmatory_v3.py \
  scripts/memory_family_producer_v3.py
git diff --check
```

The initial test-first run failed because the analysis module did not exist and
because acquisition timeout was still scored. Review regressions then reproduced
mutable-protocol acceptance, impossible readout acceptance, missing verification
lineage, Boolean block substitution and an own/sham numeric-compatibility edge.
All now pass.

Three independent read-only implementation reviews covered statistical
arithmetic and claims, analyzer trust boundaries and producer binding. The
statistical review found one incomplete model-assumption disclosure. The code
review found four trust-boundary defects plus one compatibility defect. The
producer review found no material issue. All six findings were fixed; the final
code reviewer reran all 32 analyzer tests, compilation and whitespace checks and
reported no remaining scoped finding.

CI was excluded by instruction.

## Evidence boundary

The intervals are approximate and model-conditional. They assume approximate
normality of bounded family contrasts and independence across the 48 generated
families within the fixed strata, conditional on the registered generator and
balanced assignment. Deterministic IDs, random-looking hashes and a uniformly
selected block do not establish those assumptions or generalization beyond the
registered catalog. Each stratum contributes only 16 families.

Verification receipt bindings are checked, but the analyzer does not independently
observe whether a receipt producer told the truth. A future independent close
must verify the retained source data, run order, selection publication and every
upstream check. The output therefore always retains
`receipt_truth_verified:false`, `study_complete:false`, `r2_complete:false` and
empty qualification claims.

No development family was collected. No held-out block was selected. No model
inference, native study owner, new physics study, scientific observation or
physical rover was used. The MuJoCo steps in the affected snapshot suite are
test mechanics, not study collection.

## Resource decision and remaining work

The producer's known storage subtotal remains 627,836,977,152 bytes. The final
free-space check found 68,743,004,160 bytes, leaving a **559,093,972,992-byte
known shortfall** before report, audit, prerequisite and close headroom. Native
allocation remains inadmissible.

This completes the software analysis boundary. R2 remains open. Before a
development phase can be registered, the project still needs sufficient storage,
a complete independently checked historical namespace inventory, a hash-bound
launcher that enforces the registered interleaved order, real upstream receipts,
and native source/profile/snapshot/sensing qualification. Only a passing complete
development matrix may authorize the single-draw held-out registration; it would
still make no physical-rover claim.
