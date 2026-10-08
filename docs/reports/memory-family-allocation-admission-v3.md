# Memory family v3 allocation-admission execution report

**Date:** 8 October 2026  
**Attempt ID:** `memory-family-allocation-v3-probe-g01m8ejp`  
**Attempted commit:** `3c2a1975a2943e488ab958073c0b3b18291c294c`  
**Execution status:** `EXECUTION_ERROR`  
**Scientific status:** `INCONCLUSIVE`

## Outcome

The bounded execution did not measure storage capacity, upstream state,
namespace coverage, or asset/model identity. It published no
`allocation-admission.json` and provides no allocation authorization or
qualification claim.

Two invocation errors occurred. The first stopped during direct-file import.
The second entered `admit` but stopped while constructing `StorageLimits`,
before capacity could be measured and before upstream, namespace, or asset/model
checks. Exact exit codes were not retained in the durable attempt files. Both
standard-output streams are empty, both nonzero exits were observed, and the
complete standard-error streams are preserved byte-for-byte.

No third invocation is permitted under this attempt ID. Any future execution
requires a separately frozen amendment, a new attempt ID, and pre-run
independent review.

## Frozen capacity requirement

The contract arithmetic remains valid even though host capacity was not
measured:

| Component | Bytes |
|---|---:|
| Producer subtotal | 627,836,977,152 |
| Prerequisite allowance | 8,589,934,592 |
| Non-recording allowance | 6,710,886,400 |
| Allocation quota | 643,137,798,144 |
| Continuing free-space floor | 2,147,483,648 |
| **Minimum empty-filesystem capacity** | **645,285,281,792 (600.96875 GiB)** |

Available bytes and the resulting shortfall are unmeasured, so this report does
not say whether the host passes or fails the capacity gate.

## Attempt chronology

The software-only registration was created under
`/tmp/memory-family-allocation-v3-probe-g01m8ejp`. Its publication directory
contained only `registration.json` before and after both invocations.

1. At approximately `2026-10-08T18:21:46.062810147+05:30`, the direct-file
   command was invoked:

   ```text
   /home/utkarsh/Work/shraddha/brain/.worktrees/memory-family-oracle-raw-adapter/.venv/bin/python scripts/memory_family_allocation_v3.py --registration /tmp/memory-family-allocation-v3-probe-g01m8ejp/publication/registration.json --search-manifest /tmp/memory-family-allocation-v3-probe-g01m8ejp/coverage-paths.json --repo /home/utkarsh/Work/shraddha/brain/.worktrees/memory-family-allocation-admission-v3 --assets /tmp/memory-family-allocation-v3-probe-g01m8ejp/must-not-open-assets
   ```

   It failed before `main` with `ModuleNotFoundError: No module named
   'scripts'`.

2. At approximately `2026-10-08T18:22:22.640237793+05:30`, module mode was
   invoked:

   ```text
   /home/utkarsh/Work/shraddha/brain/.worktrees/memory-family-oracle-raw-adapter/.venv/bin/python -m scripts.memory_family_allocation_v3 --registration /tmp/memory-family-allocation-v3-probe-g01m8ejp/publication/registration.json --search-manifest /tmp/memory-family-allocation-v3-probe-g01m8ejp/coverage-paths.json --repo /home/utkarsh/Work/shraddha/brain/.worktrees/memory-family-allocation-admission-v3 --assets /tmp/memory-family-allocation-v3-probe-g01m8ejp/must-not-open-assets
   ```

   It entered `admit` and failed on the first storage operation with
   `TypeError: StorageLimits.__init__() got an unexpected keyword argument
   'max_entries'`. Resolution of an older installed `palimpsest.storage` is the
   supported explanation, but it remains an inference because the imported
   module path was not captured during the attempt.

The second traceback ends inside `_capacity` before the loop can continue to
the upstream and namespace checks. The namespace sentinel roots and asset path
did not exist; no namespace-root scan, held-out read, upstream identity read,
asset/model check, publication link, Engine, model load, owner, or admission
success occurred. This is control-flow evidence, not a system-call trace.

## Prospective bootstrap correction

After the attempt was closed, the admission module was changed to prepend its
own repository root and `src` directory before importing any project module.
Isolated import-only tests use Python `-I`, trace sentinels for `main`, `admit`,
and `build_namespace_inventory`, and an `os.scandir` sentinel. Direct-file and
module imports now resolve exactly:

- `src/palimpsest/artifacts.py`;
- `src/palimpsest/storage.py`;
- `scripts/memory_family_producer_v3.py`.

Those tests also require `StorageLimits.max_entries` to default to `100000` and
accept the explicit `131072` keyword. They do not invoke the CLI or admission,
and this prospective correction does not convert the failed attempt into a
capacity or namespace result.

## Preserved evidence

| File | Bytes | SHA-256 |
|---|---:|---|
| `attempt-01-direct.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `attempt-01-direct.stderr` | 297 | `6ce89a78ac5e4bf12524d2e71a18e72678e099e769f841d5b6c136e8b958daa1` |
| `attempt-02-module.stdout` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `attempt-02-module.stderr` | 1,677 | `288929b731923cee56e58be58479aee637379e6fc10d7d638cf2f5e2730b68fe` |

`docs/reports/memory-family-allocation-admission-v3-evidence/verification.json`
is the canonical machine-readable index. The retained streams are byte-identical
to the four files preserved in the attempt directory.

## Verification

- Focused allocation/storage tests: `57 passed`.
- Import-only bootstrap regression: `2 passed` within the focused result.
- Affected family/oracle/producer/analysis/storage/artifact/replay slice:
  `264 passed, 7 skipped, 4 deselected, 15 warnings` in 233.59 seconds.
- No `FlynnContinuation` test was used to initialize or read upstream state.

The result remains `allocation_authorized: false`,
`storage_allocation_admitted: false`, `namespace_coverage_complete: false`,
`native_owner_launch_authorized: false`, `native_allocation: false`, and has no
qualification claims.
