# Consolidated final-review fix wave

Worktree: /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite
Branch: research/source-cpu-compat-v1
Base: 80a9258b58c4a89e717ad683dbb1bda5737d08cb
Commit: a75a4c2cbc7f21e8ccf53479b7eae65eba434c54 (verified post-commit readback).

## Adopted review findings and narrow implementation

Read final-review.md in full first, including Minor findings1 and2 verbatim. Used code-review reception/TDD and the existing efficient-frontier/ponytail bounded implementation guidance. No nested agents or working-set binding. Both findings were verified against the named owner/holder/test sources before changing production.

Finding1: owner identity previously called one explicit full recheck plus the real descriptor accessor for every immutable pin. The unchanged accessor performs before/after full rechecks, creating1+2*(3+N) full rechecks per lifecycle callback. Moved the same complete descriptor equality loop immediately after successful handle entry. All three scalar semantic pins and every required source remain compared, including redundant semantic pins. The same error and early-before-loader refusal remain. Each original identity call site still performs bounded deadline checks, its independent live-layout check and one full holder recheck; teardown and final post-release deadline handling remain unchanged. Task1 holder descriptor/accessor/poison/custody semantics were not modified.

The bounded regression executes the actual RuntimeHandle.descriptor method on the existing authored holder proxy with an in-memory descriptor map, active-state assertion and fail-on-unexpected-poison test seam. It does not construct a real runtime holder, census/hash a real namespace or open an engine. Tests cover6 and64 source descriptors, prove the accessor still performs2 rechecks per lookup, compare every semantic pin once before loader, and exercise7 repeated callbacks with(1 full recheck,0 lookups,1 layout) each. Entry/lifecycle/release ordering remains observed. This establishes callback-count reduction, not measured CPU/time/RSS/I/O savings or real-runtime fit.

Finding2: changed only the parent test harness to target close faults by party, identifying the first-created context as parent and the independently created second context as child. The harness records whether a provisional marker exists at the injected fault. Kept the existing child-close test, made the target explicit, and asserted owner-only/no-marker failure there. Added a separate parent-only late-close regression: owner and independent authored raw audit finish with completed accounting before fault; commit exists at parent close; production returns stopped with the precise teardown error; commit, quarantine, authored raw report and SNP remain; both contexts release; qualification/execution flags stay false. No production parent change was needed and no new production bug was found.

## Exact test commands, results and retained evidence

All commands ran in the worktree above via the existing venv alias, -B and a clean environment. Only the two changed owner/parent modules were executed. No CPU/helper/codec module rerun, fullsuite, CI, research, native owner, model or protected payload test was invoked. Existing module integration reads only its authored fixture raw/SNP/controls.

### red.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_runtime_v2.py tests/test_memory_family_source_qualification_v2.py -k 'immutable_pins_checked_once or parent_only_late_close' --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/final-fix-logs/tmp-red > .superpowers/sdd/runtime-reference-v1-implementation/final-fix-logs/red.log 2>&1
```

3 failed, 205 deselected in 1.65s, exit1. The owner test detected pin lookups after loader; the parent test saw only owner, proving the injected close still hit child before audit.

### red-counts.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_runtime_v2.py -k 'immutable_pins_checked_once' --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/final-fix-logs/tmp-red-counts > .superpowers/sdd/runtime-reference-v1-implementation/final-fix-logs/red-counts.log 2>&1
```

2 failed, 102 deselected in 0.21s, exit1. Test instrumentation was strengthened before production changes to collect the complete repeated-callback count rather than stop on the first after-loader lookup. Logs reveal (19 full rechecks,9 lookups,1 layout) and (135,67,1) at6/64 source pins versus expected(1,0,1). This remains a genuine pre-fix red.

### green-focused.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_runtime_v2.py tests/test_memory_family_source_qualification_v2.py -k 'immutable_pins_checked_once or parent_only_late_close or handle_teardown_failure_cannot_return_preserved' --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/final-fix-logs/tmp-green-focused > .superpowers/sdd/runtime-reference-v1-implementation/final-fix-logs/green-focused.log 2>&1
```

4 passed, 204 deselected in 4.33s, exit0. Real accessor counts remain2 per lookup; all seven repeated callbacks use exactly1 full recheck,0 descriptor lookups and1 layout check at6 and64 sources. Both child and parent close boundaries pass.

### final-two.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_runtime_v2.py tests/test_memory_family_source_qualification_v2.py --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/final-fix-logs/tmp-final-two > .superpowers/sdd/runtime-reference-v1-implementation/final-fix-logs/final-two.log 2>&1
```

208 passed in 135.90s (0:02:15), exit0. All production and test edits were final before this run; no later source/test edit occurred.

All basetemp paths are separately named for this wave and retained, including both red runs and their partial authored fixtures. No default pytest temp-root invocation or cleanup/deletion command occurred in this wave. Raw logs are preserved unchanged.

## Self-review and limitations

- Production diff is only the equality-loop placement in the private V3 owner seam. No public gate, schema, profile, cap, protocol, trust pin, resource budget, CPU convention or default factory changes.
- Descriptor comparisons remain inside a successfully entered handle and before loader; every original lifecycle identity callback retains its deadline/layout/full-current-byte checks. Existing mismatch, missing-layout, deadline, post-report drift, close failure and first-written failure preservation tests are included in the final owner-module run.
- The authentic descriptor method is exercised without replacing its implementation with a one-recheck fake. No source-text assertions, runtime discovery or real installation hashing is used.
- The parent-only test witnesses a marker at the actual injected parent close, after normal owner/audit completion. Quarantine and retained evidence assertions check the existing production finalizer; the child case remains separate.
- Reviewed the complete three-file diff and checked named-file whitespace. No helper/parent/codec production expansion was necessary.
- B precompletion, collector authenticity/prior completeness, preparation publication/freeze tail, full asset/native coverage, pre-import/load isolation, empirical FD/time/RSS fit, lifetime reconciliation and exact-stage GO remain explicit external gates. All prior declined review judgments remain unqualified. No actual runtime/source/scientific authority is created.
- No new load-bearing issue was found. Root owns scoped independent rereview, integrated whole-canonical verification and exact-head hosted checks; this wave does not substitute for those gates.

## Exact three-file commit and final readback

Executed the following commands after the passing final run:

```sh
git diff --check -- scripts/memory_family_source_runtime_v2.py tests/test_memory_family_source_runtime_v2.py tests/test_memory_family_source_qualification_v2.py
git diff --cached --name-only
git add -- scripts/memory_family_source_runtime_v2.py tests/test_memory_family_source_runtime_v2.py tests/test_memory_family_source_qualification_v2.py
git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
git commit -m "fix(memory): bound owner rechecks and cover late parent close"
git rev-parse HEAD
git show --format=fuller --stat --oneline HEAD
git status --short
git diff --exit-code HEAD -- scripts/memory_family_source_runtime_v2.py tests/test_memory_family_source_runtime_v2.py tests/test_memory_family_source_qualification_v2.py
```

Named-file and staged whitespace checks passed. The index was initially empty; staged names were exactly the three owned files. Commit a75a4c2cbc7f21e8ccf53479b7eae65eba434c54 contains exactly3 files,96 insertions,7 deletions. Post-commit status is clean and the three owned-file diff is empty. The ignored report/logs/fixture workspaces remain retained and are not part of the source commit. No merge/push/CI/research action was taken.

