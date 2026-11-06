# Task4a independent spec and quality review

**Spec: FAIL. Quality: CHANGES REQUESTED. Combined-suite verification: BLOCKED separately.**

Reviewed candidate `4fd9cb8379dfc46934783eab7388287d6b8b29bb` against base
`5148b3c8062f6911ec6a4417dd8eed4f902bca2d`, the current root-owned uncommitted
Task4a frozen wire/per-API/accounting contract, and `task-4-contract-fix-review.md`.
The commit adds exactly the three authorized files. HEAD remained the candidate;
the root plan remained the only tracked uncommitted modification.

## Required change

### P2 — Reader accepts copied policy events outside the motor interval

Location: `scripts/memory_family_terminal_numeric_vnext.py:321`, reached from
the reader through line474. The common `_recording` validation checks only
`len(legacy._policy_calls(events)) == n`. That helper validates policy-event
fields but does not compare their ticks against the proof's motor interval.
The generic `audit._events` check only establishes integer bounds and
`episode_step == tick`. Consequently, the reader accepts internally contradictory
event placement despite having the complete copied events and exact motor
interval available.

This violates the frozen per-API requirement at plan lines332–335 that copied
recording metadata/events, partitions and proof agree on counts and interval.
It is distinct from the explicitly allowed inability to authenticate retained
array values or timings from opaque row digests. Convert/prove already call
`audit._policy` through `_raw`, which checks the policy ticks; the reader does not.

Reproduction: start with the candidate's genuine authored `sample(1)` and its
converted bundle. Its sole motor row is tick20. Change just the copied
`neural_policy_call` event's `tick` and `episode_step` to2099, then update the
recorded-event descriptor, supplied/copied proof and affected bundle descriptors
using the candidate's existing `_rebind_recorded_events` test helper. The reader
returns successfully, with motor interval `(20,20)` and policy tick2099.
The retained proof in this mutation is deliberately no longer an independently
replayed Task3a proof; this demonstrates the required structural coherence gap,
not a bypass of an unchanged authenticated proof or an actual authority grant.
The reader's `raw_comparison_performed` and `actual_acceptance` flags correctly
remain false.

Minimal fix: in the common `_recording` path, require the ordered policy-event
ticks to equal `list(range(b, b+n))`, including the empty case. Add a rebound
reader-negative test so rejection reaches this interval check rather than an
earlier descriptor mismatch. This needs no source replay, raw pixels, new proof
field, pin change or authority claim.

## Review coverage and retained evidence

No other material issue was found in the inspected three-file candidate. The
review checked distinct PURE schemas/null authority fields and refusal of
nonnull values; exact9+2*k member census and zero typed arrays; inherited16+3
layout and exact supplied-byte comparisons; canonical proof/Context and
descriptor bindings; safe decoded NumPy types; fixed stored ZIP/NPY header
checks before array loading and exact reserialization; selected-frame checks;
profile identity without a self hash; unchanged role caps and external metadata
floor arithmetic; and explicit false actual/physical claims. The bounded probe
also exercised conversion of its genuine one-row fixture before mutation.

Read retained `task-4-report.md`, focused/raw combined logs and failure inventory.
Verified retained log SHA256 values:

- `focused-all-second.log`: `ed3c7e482e5f1c854f85ccd6a18d32915fcd37236e85c83720f83197b0eb2bd2`;67 passed in31.00s.
- `final-green.log`: `015bd2e7c187a7ffbb712492f58a6628cfe2b433a80399c7ab8182b8352e13eb`;111 failed,235 passed,2 skipped,13 errors in101.68s. Its filename is not a GREEN result.

The final failure inventory records124 exceptions with
`ValueError: Behavior source differs: engine`. The independent legacy-only
reproduction and prior Task1/2a source drift classification are root-reported
evidence, not reruns by this reviewer. No combined-suite rerun was performed.
The separate test-policy boundary remains unresolved; this review neither
waives nor repins the guard. Fixing the code finding alone cannot establish
Task4a acceptance or combined GREEN.

The private900 test covers numeric partition primitives only. The authored
normal900 fixture remains a7,035,422-byte event-resource refusal; it is neither
a positive900 conversion nor evidence about actual corpus fit. The retained
sixteen-frame refusal is consistent with the unchanged1.5MiB cap plus headers.

## Reviewer probe provenance and scope

Probe source and both attempts are retained in `task-4a-review-probes/`.
`policy_interval.log` records a first invocation failure before fixture execution:
direct script invocation lacked the repository root on `sys.path`, causing
`ModuleNotFoundError: No module named 'scripts'`. It is not semantic evidence.
The second invocation used `python -B -c` with `runpy.run_path(...)`, restoring
the standard current-directory import behavior without changing environment or
code. `policy_interval-second.log` records successful reproduction, exit0,
SHA256 `0d543d8d3332165bb3d2477e681caa5878cb5fa7a18d1f55cd12f1a049a6ecec`.

Both used the exact sanitized environment:

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B
```

Successful suffix:

```sh
-c "import runpy; runpy.run_path('.superpowers/sdd/memory-terminal-vnext-implementation/task-4a-review-probes/policy_interval.py')" > .superpowers/sdd/memory-terminal-vnext-implementation/task-4a-review-probes/policy_interval-second.log 2>&1
```

Only this report and the explicitly permitted authored probe/log directory were
written. No production/test/profile/pin/legacy/HEAD change, actual native/model/
raw/SNP/catalog/protected-data access, service, dependency, CI, cleanup or agent
spawn occurred. No physical accounting or public acceptance was claimed. Root
must resolve both the required review change and the separate verification
boundary before Task4a acceptance. Reviewer stops here.
