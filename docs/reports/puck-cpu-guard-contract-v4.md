# Q4 held-worker cache guard: source unit

The explicit q4 contract is implemented in production commit
`1fa94213f583a30e6c5533a45bef5575b45e9095`. It uses exact builtin containers and
string names, bounded strong-reference snapshots, one whitelist per guard and a
late stability check after diagnostics/completion. Observed changes fail closed.
The fixed entry imports four authored CPU modules and emits result-v2 with explicit
`qualification_version: 4`. Q1–q3 retain their original union loop and result semantics;
existing parent/auditor/observer epochs remain unchanged; the old parent refuses q4 admission.

This is source and authored evidence. No installed runtime, actual 10 controls,
actual 10 allocation, protected data or rover hardware was invoked. All seven
simulation-release gates remain open.

## Validation

| Scope | Distinct passing cases | Evidence |
| --- | ---: | --- |
| Q4 guard and entry |41| `guard-entry03`:31 guard + 9 entry = 40 passed in 57.01s; stable `entry-final01`:10 entry passed in 6.34s, with 9 overlapping cases. |
| Legacy contracts |397| `legacy01`:393 passed,4 failed,3 timing cases deselected in 243.68s. Four child imports lacked current-src PYTHONPATH; only those four reran and passed in 0.38s, with 29 deselected. No production change. |
| Authored q4 cost |3| Three size cases passed in 5.30s after semantic/source review. |

Total 441 distinct cases have passing evidence across these batches; this was not
one all-green 441-case invocation. The extra legacy-parent case was added after
`guard-entry03` pinned and collected its older 9-case entry file; its latest 10-case file
was checked separately. [Validation notes](../plans/puck-cpu-guard-contract-v4/validation-notes.json)
retain this boundary. The batch source copy checks verified 204 pinned copies.

Test-first descriptor refusal, the first fixture template SyntaxErrors, a zero-test
selector invocation, late policy downgrade, coordinated stdlib replacement and
selector-exception cleanup failures are all retained. Corrections were followed
by the final passing cases. Independent source review is
[GO, source only](../plans/puck-cpu-guard-contract-v4/source-review-final.json).

## Bounded descriptive measurements

| Added names | Historical median batch/3, ms | Q4 median batch/3, ms | Original dependency dict keys calls: historical / q4 |
| ---: | ---: | ---: | ---: |
|128|0.705|0.721|138 /0|
|512|5.833|1.517|522 /0|
|2048|93.742|4.729|2058 /0|

Each size has three raw samples of three sequential complete light checks, then a
separately profiled check. Setup and cleanup are outside timing. All samples and
source hashes are in the [comparison](../plans/puck-cpu-guard-contract-v4/cost-comparison.json).
The historical run and q4 use different contracts, source, initializer context and
diagnostics; the comparison is unpaired. At 128 names q4 is slightly slower.
Useful bounded reduction at larger sizes supports continuing engineering work;
it does not establish equivalent semantics, installed speedup or actual 09's cause.
Zero keys calls counts only the original dependency loaded dictionary; it does not
mean zero key processing, copies or allocation. Batch/3 is descriptive, not a
latency distribution, WCET or hard bound.

## Remaining

Q4 is a trusted-source boundary-sampling contract. ABA and changes after the final
observation can escape; no atomicity or hostile-code isolation is claimed. The
fixture uses two authored missing-import names; the frozen actual 19-name policy
still needs separate admission.

Next: close a distinct source epoch that explicitly selects q4 in its worker,
parent, observer and independent auditor; prepare and review fresh controls and
resource admission before any new actual run. Keep attempts 01–09 consumed. Then
qualify the operator/renderer route separately and prove one public nonzero
episode through recording, initial snapshot, replay and exports. Controller
capability, valid memory studies, six artworks, human acceptance and integrated
reproducible delivery remain required for the full goal.

## Independent evidence review and archive

[Outcome review](../plans/puck-cpu-guard-contract-v4/outcome-review.json) found no
material findings and independently verified the 204 source copies, raw timing
rows and split-batch case counts. The sealed [evidence index](../plans/puck-cpu-guard-contract-v4/evidence-index.json)
covers 290 artifacts, 4,235,424 bytes and 13 empty files, with 21 committed source
paths. Original/source-Git verification passes. This is an authored evidence
archive; it grants no runtime or release authority.

Verify without running an allocation:

```sh
python3 -B docs/plans/puck-cpu-guard-contract-v4/verify_evidence.py --originals
```
