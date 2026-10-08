# Nine-condition family accounting: software complete

8 October 2026. [Plan](../plans/memory-confirmatory-v3-readout.md) committed at
`a661951` before implementation, on `research/memory-confirmatory-v3-readout`
above PR #94. This is a tested descriptive component for the prospective study,
not its native driver or a new experimental result.

`scripts/memory_confirmatory_v3.py` admits only the complete registered
case × nine-condition matrix, with exactly three matched kinds per family.
It rejects duplicate/unregistered slots, reused owner identities, inconsistent
pair invariants and own/sham differences, including differences on failed arms.
Missing cells, failed owner infrastructure or missing raw audit assertions remain
unscored. Unmet declared prerequisites prevent aggregate results. No complete-case
subset is silently analyzed as the full matrix.

An audited natural failure receives 900 while retaining actual duration, path
and terminal cause. Goals retain actual continuation ticks. Costs and success
contrasts average the three kinds equally within each registered family and
then weight families equally. Each family contrast remains visible for the later
prospectively selected inference method. Family IDs do not establish independent
sampling, and audit assertions do not prove provenance; both limitations are
explicit in every output, with `r2_complete=false` and empty qualification claims.

The pure function is `summarize(plan, rows, prerequisites)`. The CLI accepts one
bounded JSON envelope with those three keys:

```sh
PYTHONPATH=src:. python -m scripts.memory_confirmatory_v3 synthetic-input.json
```

Its inputs must come from a future registered slot producer and independently
verified audits before use on scientific data. No native launch, raw recording
reader, model, snapshot decoder, fit or held-out access is implemented here.
The runnable synthetic envelope in `tests/test_memory_confirmatory_v3.py`
demonstrates the schema without treating the pilot as confirmatory data.

## Verification

- Initial check: 20 failures because the module did not exist. Duplicate JSON
  keys were separately reproduced as accepted, then rejected by the parser.
- Final focused checks: **56 passed in 3.34 seconds**.
- Required full software suite: **1,188 passed, 24 skipped, 39 warnings in
  354.82 seconds** (357.302 seconds outer).
- One independent source review: no Critical, Important or Minor finding;
  independent execution of the 20 new checks passed in 0.35 seconds.
- An initial broader focused invocation passed 55 tests but hit an existing
  worker test's free-space guard on `/tmp` (2.543 GB available). The final run
  used workspace temporary storage; the guard was not changed.

Exact final outputs and source hashes are retained in
[software evidence](memory-confirmatory-v3-readout-evidence/verification.json).
No new third-party dependency or historical protocol was changed.

## Ruling and remaining work

Source review clarified the previous next-step wording: the existing raw audit
already observes visibility loss at each required control boundary and the
terminal `next_pose`. It does not prove visibility between those boundaries.
Adding an all-visible or all-success gate to scored memory arms would change
the study. Existing prerequisite success criteria remain scoped to their named
open-route, retreat, acquisition and restore cells; natural failures in scored
arms stay outcomes. The prospective design now makes that distinction explicit.

Review deliberately did not establish audit assertion truth, independence,
generator validity, resource/oracle isolation, opportunity gates, sample count,
uncertainty, effect/null-harm margins or scientific qualification. Those remain
required parts of the full study. The 64-family software envelope is a size
ceiling, not an experimental sample decision or new compute allocation.

Next implementation: independent family generation and slot production, with
oracle provenance and existing raw audits wired into a separately frozen
nine-condition development phase. Historical 900 scores, 22/24 pilot goals and
`mechanism_observed=False` remain unchanged. R2 and the simulation release are open.
