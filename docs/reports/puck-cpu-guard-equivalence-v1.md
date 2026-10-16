# Guard accumulator rejected by real-worker dispatch evidence

**The sole in-place accumulator candidate changes existing guard behavior and
is rejected. Production remains unchanged.** This completes the bounded authored
equivalence check toward the first recorded/replayed/exported public episode.
It does not qualify the installed runtime or explain the full actual 09 timeout.

The plan and new real-worker case were committed first at
`fb20e74362cd3cf19331a291d0a95753b19a81da`. Unchanged production passes all seven
selected semantic cases in 10.01s (outer normal 0 in 10.286119s). The experimental
copy passes six and fails one in 9.73s (outer normal 1 in 9.983805s). Both batches
deselect all three timing cases; their wall times are not guard-speed evidence.

The new case installs a source loading-set subclass with a reflected union hook.
The original binary union calls that hook, observes its exact sentinel exception,
preserves first-failure identity, empties owned holders and remains poisoned after
cleanup. The candidate skips the hook and reaches
`SOURCE_UNION_REFLECTED_FAILURE_SKIPPED`. Its generic nonzero child exit does not
satisfy the expected failure/poison assertions. Retained logs include this new
case's complete captured child stdout/stderr.

The six previous allowance/refusal cases pass in both batches, including lying
membership and split removal. That green subset does not prove equivalence.
All thirteen shared source pins match; the candidate adds only the captured
experimental bootstrap and fixture driver. Production remains 45,915B, SHA256
`f137429398dc30270e67ef198c508231f9e2cf02d3aeedb98663630cafa51451`.
The experimental copy is 46,230B, SHA256
`df8a2b6cb688e36de2a3ba7dac6c6d309b98f069c5e7085172873e542abb3d86`.

Independent source and outcome review found no material findings in this negative
experiment. All 28 pre-execution snapshots verify; the shared thirteen match the
test-first Git commit. The rejected source and failure remain retained; no test
was weakened and no performance workload followed rejection.

The packet contains **63 artifacts / 680,759B / two empty stderr files**. Index
SHA256: `2a175b9f7caa5faf3cc641c203741ad3c9228496fc55eda9429cde1d85f6d8cf`.
Archive/original/source-Git verification passes. Verify the committed packet with:

```sh
python docs/reports/puck-cpu-guard-equivalence-v1/verify_evidence.py --originals --git-revision <evidence-commit>
```

This rejects one unconditional rewrite; it does not prove that every compatible
optimization is impossible. The next source unit selects the explicit
[prospective q4 contract](../plans/puck-cpu-guard-v4-prospective.md): canonical
names/containers, one allowance snapshot and a late fail-closed stability check.
It changes acceptance semantics and must not be called an equivalent optimization.
Q1–q3 remain unchanged. Q4 is not implemented or validated by this report.

No installed vendors, actual 10, study, protected input, renderer or physical
hardware ran. Private fixture trees and every prior case's child streams are not
an independent installed FD/process/payload custody audit. Actual 01–09 remain
consumed; main and all seven open release gates remain unchanged. Full-repository
tests and CI were outside this test/evidence-only unit.
