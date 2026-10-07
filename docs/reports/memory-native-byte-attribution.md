# All 72 retained native differences are timer durations

7 October 2026. One registered offline readout completed in **4.552369 s**.
All 72 differing bytes in the two retained 458,761-byte native payloads map to
14 timer duration fields. Replacing only those durations on a decoded copy
reproduces the right original payload **byte for byte**, including its SHA256.
There are **zero unexplained differing bytes** for this retained pair.

Both decoded models use Newton (`solver=2`) with `noslip_iterations=0`, so dual
solver arena fields are ineligible. The two previously suspect AR arrays are
NumPy-owned, have no base and are not captured native storage. This separately
registered readout resolves the two uncertainties left by PR #72; it preserves
the old results and does not amend the full-state gate or qualify a restore.

[Contract](../plans/memory-native-byte-attribution.md),
[prospective registration](memory-native-byte-attribution-evidence/registration.json),
[exclusive invocation](memory-native-byte-attribution-evidence/offline-launched.json),
[original execution receipt](memory-native-byte-attribution-evidence/execution.json),
[full analysis and offset list](memory-native-byte-attribution-evidence/analysis.json),
[invocation log](memory-native-byte-attribution-evidence/readout.log).

## What changed and how the attribution was proved

Parent `29b01b5`, draft PR #72; branch `research/memory-native-byte-attribution`.
Contract `f8f2e10`, implementation `65f482c`, and registration `895e56f` were
committed before the invocation. The existing offline auditor and its admission,
raw/post-state integrity, historical owner linkage, deadline, artifact indexing
and failed-close guards were reused. The only new scientific operation is an
optional registered timer byte-attribution probe on decoded local copies.

Both retained five-control restores passed raw and post-state audits again.
Their trace digest remains
`794593e481fe2cca88fa49f59a491e33597f0bf2f9713b3496a68ad3d99f3249`.
Full normalized state still differs only in `native_data` and `native_sha256`;
the other ten component hashes match. This remains two restore attempts with
one frozen source/profile/seed, not ten independent experimental samples.

Each native payload round-tripped through deserialize/serialize **exactly**.
For each of the 15 timers on both sides, a finite float64 probe changed all eight
representation bytes. Every probe changed exactly one unique contiguous
eight-byte interval and nothing else. Restoring each original duration restored
the complete original payload exactly. No serialized-layout offsets were guessed.

Every original differing offset falls in the same timer-index interval on both
sides. Finally, copying only the right durations into the decoded left object
produced the exact right payload SHA256:
`c6a2fa9f6c67023ce27ed21df46cce37352556981c91c75c7792292f585faca8`.
The modified copy was never saved as a snapshot or used for qualification.

| Timer index | Serialized interval, end exclusive | Original differing bytes |
|---:|---|---:|
| 0 | [279971, 279979) | 6 |
| 1 | [279987, 279995) | 6 |
| 2 | [280003, 280011) | 0 |
| 3 | [280019, 280027) | 5 |
| 4 | [280035, 280043) | 5 |
| 5 | [280051, 280059) | 5 |
| 6 | [280067, 280075) | 5 |
| 7 | [280083, 280091) | 4 |
| 8 | [280099, 280107) | 5 |
| 9 | [280115, 280123) | 5 |
| 10 | [280131, 280139) | 5 |
| 11 | [280147, 280155) | 6 |
| 12 | [280163, 280171) | 4 |
| 13 | [280179, 280187) | 5 |
| 14 | [280195, 280203) | 6 |
| **Total** | **30 successful probes across both sides** | **72** |

The repaired named-field decoder reports 173 fields and 34 omissions per side:
32 zero-sized arrays and the two nonempty unbacked AR views. Its sole differing
named field is `timer.duration` (14 of 15 elements; maximum absolute difference
0.000491245999988621). The complete byte attribution above establishes the
payload difference independently of this reduced named-field inventory.

## Actual arena eligibility and source interpretation

Both decoded sides record `nA=0`, `nefc=284`, Newton solver and zero noslip
iterations. Both `efc_AR_rowadr` and `efc_AR_rownnz` have shape [284], dtype int32,
`numpy_owns_data=true` and `has_base=false`. Their contents were not copied by the
attribution probe. The earlier unfiltered AR observations therefore came from
unbacked binding arrays; they are not differences in serialized solver state.

MuJoCo 3.3.6 defines dual eligibility as PGS or positive noslip iterations, and
conditionally serializes those arena fields. Its bindings construct the exposed
array using the field pointer and shape. These reviewed source rules, combined
with the actual recorded model settings and ownership metadata, support this
model-specific interpretation.
[Dual predicate](https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.6/src/engine/engine_core_constraint.c),
[serialization](https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.6/python/mujoco/structs_wrappers.cc),
[arena binding](https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.6/python/mujoco/structs.cc).
The timer duration is a cumulative diagnostic statistic, distinct from the call
count; this readout mapped duration fields only.
[Timer definition](https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.6/include/mujoco/mjdata.h),
[prospective source review](memory-native-byte-attribution-evidence/source-review.json).

## Validation, preservation and limits

One parameterized synthetic regression verifies timer-only attribution and
refusal to hide an unrelated `qpos` difference. The reused real-child launcher
check verifies clean admission and an exclusive marker for both studies. The new
checks failed before implementation, then the focused suite passed **38** in
1.45 s. The full local suite passed **953**, with **24 skipped** and 39 warnings,
in 98.66 s. The new attribution and launcher checks take no physics steps. The
full software suite includes isolated MuJoCo step/forward exercises on synthetic
fixtures, including `PhysicsSnapshots` in `tests/test_snapshots.py`. Those are
software validation, not retained-study replay or qualification. The registered
readout's zero-physics count applies to that invocation alone.
[RED](memory-native-byte-attribution-evidence/red.log),
[GREEN](memory-native-byte-attribution-evidence/green.log),
[full suite](memory-native-byte-attribution-evidence/full-suite.log).

Python 3.11.15, NumPy 2.2.5 and MuJoCo 3.3.6 were pinned. Admission had
19,639,709,696 free bytes. The single 300 s study used a fresh output and marker;
the external wrapper retained its 290 s timeout and 5 s kill grace. No retry,
current PID probe, native worker, neural inference, reset, forward or physics step
occurred. Qualification claims remain empty; the previous failed scientific
close and six-of-eight prerequisite disposition remain unchanged.

[Publication integrity](memory-native-byte-attribution-evidence/publication-integrity.json)
rechecks all **473** preserved files across seven prior evidence/output sets and
all **18** bound inputs, including old consumed markers. Exact executed code is
archived as the [offline driver](memory-native-byte-attribution-evidence/executed-offline-driver.py),
[diagnostic helper](memory-native-byte-attribution-evidence/executed-diagnostic-driver.py)
and [pilot helper](memory-native-byte-attribution-evidence/executed-pilot-driver.py).
Raw SNP/NPZ stay local at registered paths; Git metadata are not a replay bundle.

[One independent final review](memory-native-byte-attribution-evidence/final-review.md)
found no blocking code issue and passed 14 synthetic checks in 0.96 s. It caught
the original report's overbroad no-physics claim about the full software suite;
that editorial error is corrected above. The reviewer verified registration and
analysis hashes and all three archived drivers, without independently decoding
retained states or repeating the full suite. Its scope limits and executor
rulings are preserved in the review record; no deferred minor findings remain.

The attribution is exact for this pair and version. It does not show restored
behavior across more seeds, longer trajectories, other models or hardware, nor
does it automatically establish a new scientific state definition.

## Next boundary

No same-contract state repair is needed to explain these bytes: they are recorded
profiling durations, while the current exact full-state rule still includes them.
The next decision is a prospective contract proposal separating profiling
statistics from restore reproducibility. A candidate should retain lossless full
native bytes and their integrity hashes while explicitly declaring any narrower
comparison; it must not silently strip bytes or promote historical results.
Timer call counts should stay in scope unless separately justified.

Only an approved prospective contract and fresh qualification could unlock the
memory pilot. No contract amendment, qualification, pilot, held-out or physical
work was performed here. Navigation R3 and puck/operator gates remain open.
Repo-local Aadrika Maurya <aadrikamaurya@gmail.com>, publication as Aadrika08;
draft PR stacked on #72. Main unchanged; CI excluded. Quota telemetry unavailable.
