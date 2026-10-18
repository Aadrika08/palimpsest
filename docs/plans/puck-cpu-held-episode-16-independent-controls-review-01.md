# Allocation-16 independent controls review 01: GO WITH FIXES (fix applied)

**Range:** `4b22f2b..5ad1178`. **Reviewer:** separate read-only agent. It
reconstructed the admission main body up to the forest walk against real files,
and reran `canonical-preflight` (PASS).

## Critical (fixed before CONTROL)

Commit `c816f5e` made admission16 import `tempfile` before taking its baseline.
On this CPython 3.11.15 build, that import keeps `/dev/urandom` open, so the
published receipt records file descriptors 5→5.

`tools/make-observer-guard.py:26` still expected 4→4. As frozen, admission16
would have been consumed, and the maker would then have refused to build the
pre-observer guard. **Fix:** line 26 now expects 5→5. The tool is not
freeze-pinned; it is bound by Git at CONTROL. Root re-measured the
`tempfile` import in a clean isolated interpreter: 4 descriptors became 5.

## Confirmed

1. **Configuration.** All parent and auditor validators pass. It has 98 sources,
   preparation04 binding, 42+4 rosters, and fresh run ids.
2. **Merge.** `75df4db` changes documents only. COUNT is computed from it.
3. **Stage and boot guard.** It checks preparation04 roots 317249–317252 before
   every one-shot step.
4. **Clocks.** These are in order:

   | Layer | Seconds |
   | --- | --- |
   | Worker | 600 |
   | Parent | 1200 / 1215 / 1230 |
   | Observer | 1260 / 1275 |
   | Wrapper | 1300 |
   | GNU timeout | 1310 |
   | Python | 1330 |

5. **Admission fixes.** `8a01ea0` and `c816f5e` are correct in themselves.
6. **History binding.** Binding consumed history through evidence indexes is sound
   and justified by the 2 GiB held-byte margin. Re-measured peak: 37,982 entries
   and 2,044,405,373 bytes. Index-bound packet files rely on Git integrity rather
   than admission-time re-hashing.
7. **Outcome criteria.** The collect-outcome PASS criteria cover the plan's
   acceptance section.

## Minor

- The renderer version is pinned to Mesa 26.2.2. Do not update system packages
  before the run.
- Free space: disk 13 GB, RAM 5.9 GB, `/tmp` 4.0 GB.
