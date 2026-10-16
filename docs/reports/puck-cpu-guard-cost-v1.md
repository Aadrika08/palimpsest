# Guard cost measured; two shortcuts rejected

The authored workload demonstrates repeated whitelist construction and a large
local saving from avoiding it. Both tested shortcuts change existing behavior,
so **production code is retained unchanged**. This is a source diagnosis toward
the first recorded/replayed/exported episode, not runtime qualification or an
explanation of consumed attempt 08's timeout.

## Measurement

The [workload and refusal cases](../../tests/test_puck_guard_cost.py) use the
existing real isolated worker and held dependency fixture. Each workload inserts
128, 512 or 2048 plain synthetic module-cache entries with corresponding temporary
dependency in-flight allowances. It does not initialize those modules through
the loader or fabricate loaded-module seals. All entries and allowances are
removed before normal terminal verification.

Each row reports the median of three sequential samples, with three real
`_check(full=False)` calls per sample. Timing excludes fixture startup and terminal
checks. One separate profiled check counts built-in `keys()` calls on the real
dependency loaded dictionary; profiling is outside the timed samples and the
previous hook is restored. Light checks still run their existing reconciliation,
source/runtime metadata, process, environment and clock checks.

| Synthetic cache entries | Original, ms/check | Direct dependency membership, ms/check | Hoisted whitelist, ms/check |
| --- | ---: | ---: | ---: |
| 128 | 0.705 | 0.411 | 0.348 |
| 512 | 5.833 | 0.607 | 0.465 |
| 2048 | 93.742 | 1.517 | 1.068 |

The original requests dependency keys **138 / 522 / 2058 times per check**;
direct membership requests them zero times and hoisting once. The ten additional
original requests come from the fixture's other nonstdlib cache entries. Raw
nanosecond samples, counts, commands, source copies and terminal results are
retained in the [packet](puck-cpu-guard-cost-v1/evidence-index.json).

The baseline suite passed **9 cases in 13.43s** (outer normal exit 0 in 14.191s).
The two experimental source copies are used only by the fixture driver;
`scripts/puck_worker_bootstrap.py` remains byte-identical to source commit
`2159cdf1d515513abdd36bdd5999019ea27ff39c`, SHA256
`71263511b6f8b1828a59f2a82f74473f9151f1ec7b28dfe8bfa8c637ccac9c0e`.

## Why the faster copies are rejected

- **Direct dependency membership:** 7 passed / 2 failed in 13.41s, outer normal
  exit 1 in 15.750s. A set subclass returning false from `__contains__` makes
  the shortcut reject an existing in-flight allowance. A subclass returning true
  makes it accept an unregistered cache entry. The original union uses actual
  set contents and passes both cases.
- **Hoisted whitelist:** 8 passed / 1 failed in 15.86s, outer normal exit 1 in
  16.130s. A string-subclass cache key removes its allowance in `split()` without
  resizing `sys.modules`. The original builds its whitelist after that callback
  and refuses; the earlier snapshot still accepts it.

These expected experimental failures remain preserved; they are not fixed by
weakening the tests. The original refusal cases also verify first-failure
identity, an emptied owned-holder list and continued poisoning after cache cleanup.
Exact builtin container types alone would not establish equivalence: their keys
may still have custom hashing/equality, and later callbacks may mutate contents.
No bounded compatible fast path has been demonstrated by this work.

## Independent review and retained bytes

Independent review found no material evidence findings. It recomputed all nine
medians, checked the variant diffs and driver, confirmed the three exact failure
cases and verified unchanged production bytes. It did not rerun the experiments
or establish installed-runtime cleanup or equivalence of any other rewrite.

The packet retains **32 artifacts / 291,335 B / 3 empty stderr files**, including
the eleven source/fixture files bound to commit `2a9db8d`, both rejected source
copies, all three commands/log pairs/terminal records, the comparison, tool
terminals, independent review and reused byte verifier. Its index SHA256 is
`7d036968be423a661730f4086d868db89bd87d8bea3ca561757fa56f5f6ddb25`.
Archive/original/source-Git verification passes. Verify the committed packet with:

```sh
python docs/reports/puck-cpu-guard-cost-v1/verify_evidence.py --originals --git-revision <evidence-commit>
```

The immutable direct/hoisted failure logs retain their original whitespace and
are the only paths excluded from whitespace checking.

## Decision, limits and next action

Retain the original loop. The measured saving warrants further work, but neither
candidate can be used in the qualified runtime as it stands. The next finite
task is to review a mutation/dispatch contract and a compatible fast-path design
against these counterexamples before implementing any production optimization.
If that cannot preserve the existing acceptance/refusal boundary without a
general framework, instead use bounded guard-time accounting to locate actual
runtime cost. Any changed contract must be stated prospectively; it cannot be
described as an equivalent optimization.

These are three sequential local samples per size, without randomized order,
system-load control, initialized dependency seals or installed vendor imports.
They show cost for this synthetic in-flight workload, not application throughput,
a guaranteed speedup, hard timing or the cause of attempt 08. The timed light
checks exclude full forest/native-image work; normal fixture startup and terminal
verification still perform their existing checks outside the timed interval.
The retained pytest logs are aggregate fixture evidence; individual private-tmpfs
worker trees and every child stream are not a portable episode or an independent
installed-runtime cleanup audit.

No installed runtime, renderer, model, scientific study or protected input ran.
No 09 controls, admission or invocation were created. Attempts 01–08, the
180s deadline, 2GiB qualification RAM floor, prior predicates and all seven open
release gates remain unchanged. Full-repository tests, CI and physical checks
were not run for this test/evidence-only change.
