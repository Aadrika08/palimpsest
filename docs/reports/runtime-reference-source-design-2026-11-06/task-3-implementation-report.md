# Task 3 source-only implementation report

Worktree: /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite
Branch: research/source-cpu-compat-v1
Starting HEAD: f00dc47420b2f7651fa661dbd946b1786ca8cc94
Commit: 7bd0a860869a980ae30840f8e6d0818e74610e6b (post-commit readback).

## Scope and resulting contract

Read task-3-brief.md first, including its binding global schemas and approved requirements amendment. No nested agents. Changes are restricted to the parent, parent tests, source-preservation plan and the numeric plan's prospective boundary. Root-owned project-completion and delivery/report edits stay excluded.

Exact dispatch is V3 freeze/V2 inline job and V4 freeze/V3 reference job, without mixtures/fallback. V4 adds only runtime_accounting and prior_charge_reference; preparation/parent result use V4. Existing V3 labels, bytecode refusal, inline limits, _worker_cpu_budget, inclusive CPU convention, old protocols/pins and helper/owner APIs remain unchanged.

_verify_reference_metadata uses pure owner/template/requirements and runtime-reference/charge validation, canonical upward binary64 prior consistency and integer lane admission. Metadata verification reads only the pinned freeze and existing public numeric/coverage metadata. It does not instantiate a holder or open the referenced recipe/manifest/ledger/accounting evidence. Actual V4 execute, default private execution and real admission are unconditionally closed before external payload/output/GO/loader effects, even when a substituted verification result asserts authorization.

_bind_reference_inputs is private/post-gate only. Parent independently checks its own live source/paper/venv/base layout and six required sources, retains alias-chain identity, uses exact frozen requirements/pins and one current-byte handle. Child enters its own independent handle via the reviewed owner seam and receives the identical original runtime absolute deadline plus the tighter source deadline. Parent repeats one full holder recheck per identity callback rather than per-descriptor full-tree rechecks. The shared namespace helper preserves old coverage/collision/recheck semantics and all namespace/lifetime descriptor holds. Acquisitions, parse/hash/census work, repeated checks and teardown remain in the existing parent/child resource intervals; no new ceiling is adopted.

_validate_reference_accounting uses only handle.accounting, exact derived integer totals and complete described external bytes; it does not expose manifest/ledger/FD rosters. Authority always stays false. Report/reference/provenance/summary/accounting controls are bounded and included in the complete census.

Combined metadata uses the unchanged numeric sealer for every emitted descriptor plus candidate metadata and positive conversion/commit/terminal/atomic/failure reserves, then separately charges actual pinned original freeze bytes. Identical paths deduplicate only identical pins; separate copies count separately regardless of digest. Known metadata gets a pre-conversion bound. Full post-seal and reread bounds can reject a tentatively published marker: existing retained-failure/quarantine handling prevents a preserved return. Controls8 MiB/headroom64 MiB grant no extra metadata. Creation-time control pins and checked input teardown stay authoritative for the software result.

The exact-boundary test independently sums actual original freeze, complete registered external files and candidate bytes less dense/event/pixel domains plus every positive reserve. Its final version creates real canonical metadata padding bytes, reconstructs only explicitly described authored bundle members and calls the real pure numeric accountant for exact1MiB/one-byte-over. The separate late-overflow integration test forces the completed parent sum over and verifies retained marker plus quarantine/raw/SNP.

## Exact verification commands and retained results

All commands below ran in the worktree above, through the existing venv alias with -B and a clean environment. No fullsuite/CI/research/native/model command ran. Only the five named modules and selections within the parent module were executed. Exit status is reflected in the actual logs; red/fixture failures are preserved, not relabeled successes.

### red-metadata.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_qualification_v2.py > .superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/red-metadata.log 2>&1
```

7 failed, 65 passed in 89.28s; expected new-format dispatch/metadata failures.

### green-metadata.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_qualification_v2.py -k 'version_pair or v4_verify or v4_has or actual_v4 or v3_still or frozen_roots' > .superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/green-metadata.log 2>&1
```

9 passed, 63 deselected in 0.68s.

### red-private.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_qualification_v2.py -k 'v4_parent_and_child or v4_ledger or v4_full or v4_new_copy or v4_one_byte or v4_consistent or v4_added' > .superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/red-private.log 2>&1
```

10 failed, 1 passed, 72 deselected in 1.23s; missing V4 admission/binding/result integration, plus fixture context-suppression bug.

### green-private-1.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_qualification_v2.py -k 'v4_parent_and_child or v4_ledger or v4_full or v4_new_copy or v4_one_byte or v4_consistent or v4_added' --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/tmp-green-private-1 > .superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/green-private-1.log 2>&1
```

8 failed, 3 passed, 72 deselected in 1.26s; authored external-control fixture had nonexistent not-opened descriptors.

### green-private-2.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_qualification_v2.py -k 'v4_parent_and_child or v4_ledger or v4_full or v4_new_copy or v4_one_byte or v4_consistent or v4_added' --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/tmp-green-private-2 > .superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/green-private-2.log 2>&1
```

11 passed, 72 deselected in 22.62s, after creating the explicitly named authored control and correcting poison/raises nesting.

### red-canonical.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_qualification_v2.py -k 'v4_metadata_is_canonical' --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/tmp-red-canonical > .superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/red-canonical.log 2>&1
```

1 failed, 7 passed, 95 deselected in 0.71s; genuine missing rejection of noncanonical actual V4 freeze bytes.

### green-new-all.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_qualification_v2.py -k 'v4 or version_pair or v3_still' --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/tmp-green-new-all > .superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/green-new-all.log 2>&1
```

40 passed, 63 deselected in 23.27s.

### final-five.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_source_runtime_closure_v1.py tests/test_memory_family_source_runtime_v2.py tests/test_memory_family_source_qualification_v2.py tests/test_memory_source_cpu_limits.py tests/test_memory_family_source_seal_v2.py --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/tmp-final-five > .superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/final-five.log 2>&1
```

387 passed in 329.15s (0:05:29), exit 0. Production code was final before this run; the exact-boundary test was strengthened while it ran and its final version passed separately below. Later changes were documentation-only.

### boundary-real-bytes.log

```sh
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin LANG=C.UTF-8 PYTHONPATH=src:. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_qualification_v2.py -k 'v4_full_combined_metadata_sum_includes_freeze_job_logs_tail' --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/tmp-boundary-real-bytes > .superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/boundary-real-bytes.log 2>&1
```

1 passed, 102 deselected in 3.99s. Final test-only strengthening after final-five began; no production change after final-five start.

## Preserved authored workspaces and process limitations

The first three runs used pytest's default /var/tmp/pytest-of-utkarsh/pytest-48, pytest-49, pytest-50. These were copied with the exact command below before any further default-temp run. All later runs use fresh explicit basetemp names retained alongside logs. Earlier pytest default-retention evictions are unknown; no broad temp scan or no-deletion claim was made. No cleanup/delete command was issued.

```sh
cp -a /var/tmp/pytest-of-utkarsh/pytest-48 /var/tmp/pytest-of-utkarsh/pytest-49 /var/tmp/pytest-of-utkarsh/pytest-50 .superpowers/sdd/runtime-reference-v1-implementation/task-3-logs/
```

The preservation copy contains authored fixtures/raw/SNP/controls and failed partials from these tests. No real runtime/site-packages/base-interpreter namespace was traversed/hashed to create fixtures. No installation/model/checkpoint/protected catalog was prepared or examined. Actual selected source paths are metadata-only fake pins in reference-layout tests; real custody accounting tests hold explicitly authored recipe/manifest/ledger/evidence/runtime files in temporary roots. Existing named public numeric profile/source tests retain their established software-only reads.

## Self-review

- Re-read parent dispatch, pure metadata checks, private handle placement/lifetime, owner admission/outcome versioning, metadata census, original/copy accounting, late-overflow quarantine and final teardown paths.
- V4 serialized metadata rejects duplicate/noncanonical JSON, unknown authority fields, wrong classification, inexact/integer/bool/negative-zero prior values. All supplied charge/reference values remain untrusted.
- Authored parent/child contexts prove independent handle entry, identical original deadline and exact frozen roots/five pins. Each process checks its own layout; parent tests cover every mandatory prefix and source, while the unchanged owner module tests cover child obligations.
- Real held authored ledgers prove baseline+operation integer totals, exact memory-lane fixed-allocation boundary, one-nanosecond-over/inconsistent/bool/float refusals and complete external byte totals including the final ledger descriptor. Accounting authority remains false.
- Actual V4 fail-on-call instrumentation guards holder construction, loader, output creation and core execution. A caller's successful-looking JSON cannot remove the explicit retained-unqualified blocker.
- Existing owner/helper/Puck/numeric/CPU implementations are outside Task3 ownership and have no Task3 diff. Root-owned dirty delivery/planning files remain untouched/excluded.
- No test manufactures qualification from its completed label, fake handle or authored engine. The initial poison/raises fixture bug and nonexistent authored-control fixture were corrected transparently after preserving their failures.

## Remaining limitations and review handoff

B is an asserted precompleted immutable-input class, not authenticated creation-time or complete accounting evidence. Neither mtime nor JSON completed/true fields establish it. Complete external physical/copy inventory, failed preparation CPU, ledger publisher/accounting/publication/freeze tails and nonoverlapping attempt cut require an external backend. This migration implements no collector authority.

Actual namespace authorization, pre-import/load/exec isolation, native closure, complete model/graph/asset descriptor coverage, FD/RSS/time/resource fit, whole-parent lifetime reconciliation and exact-stage GO remain unqualified. The five required runtime prefixes and an existing assets directory do not establish complete model/asset coverage. The manifest can represent explicit selected asset roots/standalones, but no qualified complete package is created. All actual_source_qualified/runtime_qualified/execution_authorized flags remain false.

The reviewed owner has a deferred repeated descriptor-lookup recheck multiplier. Task3 deliberately did not modify it or duplicate the multiplier in parent. Repeated work is charged and empirical fit remains unknown. Whole-migration review must triage that issue and asset completeness.

Independent focused Task3 review and whole-migration review are root-owned next steps after this commit; this report is self-review, not independent acceptance. No merge/push/preparation/research execution is authorized by this handoff.

## Final git verification / exact owned commit

Commands executed:

```sh
git diff --check -- scripts/qualify_memory_family_source_v2.py tests/test_memory_family_source_qualification_v2.py docs/plans/memory-source-preservation-v2.md docs/plans/memory-numeric-preservation-v2-implementation.md
git diff --cached --name-only
git add -- scripts/qualify_memory_family_source_v2.py tests/test_memory_family_source_qualification_v2.py docs/plans/memory-source-preservation-v2.md docs/plans/memory-numeric-preservation-v2-implementation.md
git diff --cached --name-only
git diff --cached --stat
git diff --cached --check
git commit -m "feat(memory): add closed V4 source parent reference path"
git rev-parse HEAD
git show --format=fuller --stat --oneline HEAD
git status --short
git diff --name-only HEAD -- scripts/qualify_memory_family_source_v2.py tests/test_memory_family_source_qualification_v2.py docs/plans/memory-source-preservation-v2.md docs/plans/memory-numeric-preservation-v2-implementation.md
```

Diff checks passed. Cached names were exactly the four owned files, no other staged files existed. Commit succeeded with exactly four files, 762 insertions, 18 deletions. Post-commit readback confirms the four owned files are clean. Root-owned project-completion/delivery/report edits and new report artifacts remain dirty/untracked and excluded.

