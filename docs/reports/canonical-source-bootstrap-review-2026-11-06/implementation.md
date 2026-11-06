# Canonical prepared Engine creation: implementation and source-unit report

Worktree: `/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite`.
Baseline: `a591076`; binding: `docs/reports/canonical-source-bootstrap-contract-2026-11-06/contract.md`.
Owned files: `src/palimpsest/engine.py` and new `tests/test_memory_source_bootstrap_vnext.py` only.
Commit: `1b3f0f9` (`feat(engine): add canonical prepared source bootstrap mode`), local only. Post-commit status has no owned modifications; the root-owned untracked `docs/reports/canonical-source-bootstrap-contract-2026-11-06/broken-writer-clarification.md` is preserved. Commit contains exactly the two owned files.

## Delivered behavior

`Engine.open` gains one keyword-only argument, `source_bootstrap_mode=None`. None/omitted mode preserves existing defaults and ordinary paths. The sole exact-string alternative is `canonical-prepared-vnext-v1`. It requires the exact held-provenance type, private memory-decision-v2/checker/CPU FLYNN profile, actual dict/exact version3 generated family case, fresh noncontinuation options, matching validated seed, exact lowercase hyphenated UUID and lexical canonical absolute original roots. Existing profile, case, geometry and constructor guards run unchanged.

The canonical path obtains and validates the real held report before any readonly resolver/payload access, passes original root arguments to the real resolver once before caller Path.resolve, preserves the ID and adds only manifest configuration `source_bootstrap_epoch`. FLYNN receives resolver edge/checkpoint directly; canonical mode never calls verify_assets/prepare_graph or imports doctor. Both modes use the same environment defaults, synchronous RunWriter, event/report predicate, RNG/Torch thread/seed sequence, upstream environment interface, configure_world, policy load/provenance, real Engine.__init__, reset/world/memory initialization, events and cleanup.

No public source factory, owner, authorization flag, admission token, qualification pin/backend, accepted-source flag, strict4 promotion or memory_terminal_vnext manifest/Engine fields were added.

## Verification and evidence limits

The settled final command exited 0: **101 passed in 1.19s, 0 skipped**. Only the new file ran. The previous final also passed 101/101; root then explicitly requested retained observed exception/status/closed-file evidence, so the test observation helper was extended and the final new-file command rerun once with a fresh basetemp. Both logs and both fixture roots remain intact. Root clarification that no second full run was needed arrived after this rerun completed; no further test run was launched.

The positive traverses real Engine.open and __init__, held_provenance factory/type/report, validate_decision, generated development family case (development/block0/row0/change only), _memory_restore/_decision_restore, case generator comparison, geometry_check, readonly resolver pinned-byte checks, synchronous RunWriter, twenty-obstacle configure_world branch, memory_world._validate_env, decision-world configure and initialize, reset, world, event order and close. It asserts paused tick0/episode0, memory version3, world/registered profile version3, ordinary diagnostics/policy/environment provenance, exact canonical UUID in writer/Engine/events/final manifest, constructor/seed/thread/reset ordering and original authored fixture bytes unchanged.

Controlled boundaries only: Python/NumPy RNG seed methods, an inert Torch module (manual_seed/set_num_threads), upstream import/environment construction interface, policy loading/reset interface, synthetic array/joint environment and inert mj_forward. Real native model/physics, ML/Torch allocations/imports, runtime closures and policy feasibility were not exercised. These are source units, never native/backend/source qualification or an actual experiment.

Refusals cover unknown and nonexact mode types; incompatible scenario/texture/controller/device/fresh options; invalid/mismatched seed; malformed/version2/tampered/unknown-profile/version-only/subclass cases; noncanonical/missing/nonexact UUIDs; relative/dot/traversal/repeated/trailing/bytes roots; original symlink and ancestor-symlink roots; missing/duck/dict/foreign/subclass diagnostics; genuine held reports with failed Python/upstream/dependency checks; corrupted/missing/symlink prepared inputs. Preflight refusals assert zero resolver calls/output/allocation. Resolver refusals assert one genuine resolver entry, no fallback/output/allocation. No unrelated setup refusal was accepted as a semantic negative.

Legacy evidence covers omitted/None mode, genuine held and controlled doctor interface, FLYNN verify/prepare/load order, manual/teacher ordinary constructors, generated and supplied hex IDs, two-thread setting, and post-writer failed-held diagnostic recording. The controlled legacy doctor is an inert module; no ambient host doctor ran. Legacy preparation is an explicit controlled boundary; no acquisition/extraction occurred.

## Failure evidence and preserved recorder limitation

Normal allocation, real cylinder guard, policy-load, missing authored uv.lock provenance, real __init__ control-interval guard and actual episode JSON-serialization failures all enter the shared try/except, persist failed manifests and close the real writer and allocated environment/renderer. A nonbreaking diagnostics storage callback TypeError also persists a failed manifest and closes the writer before allocation. Renderer close failures retain existing env/writer closure even when the cleanup exception replaces the body exception.

Nine actual observed failure records are retained in `canonical-bootstrap-evidence/failure-observations.json`, with original per-case files under the final basetemp. They are extracted from the actual unwound Engine.open frame, without replacing RunWriter or its methods. Each records raw exception/context type/message, retained manifest status, writer._broken, actual events stream.closed and fileno() refusal (`I/O operation on closed file`), plus env.closed if allocated.

The broken-budget case is explicitly a failed call, not terminal completion: observed ValueError `run writer is closed or finished`, context RuntimeError `authored storage quota refusal`, retained manifest status `running`, writer_broken true, events_stream_closed true, fileno refusal above, environment null (not allocated). Exact retained path:
`/var/tmp/palimpsest-bootstrap-final-20261106-4ae275f6/a7adda3162b541dbb85f7c0fd97d590f/failure-observation.json`.
Existing _check_budget marks the writer broken; finish cannot publish a failed manifest, while close still closes its event stream. This incomplete prefix is never treated as success; later actual-source admission must reject it. No production recorder cleanup, recovery, repair, acceptance or error-masking policy changed.

The close-masking case observed BoundaryFailure `renderer close boundary`, context BoundaryFailure `policy boundary`, manifest failed, writer closed and env closed; retained at:
`/var/tmp/palimpsest-bootstrap-final-20261106-4ae275f6/9251dc2ccd7a434681b3fdb52b3552a8/failure-observation.json`.

## TDD failures retained and corrected

Initial 8 failures were the expected missing source_bootstrap_mode API keyword. Expanded red2 also exposed an authored fixture mismatch: cylinder radius .35 rather than the existing required .4, causing two legacy omitted-mode positives to fail. Corrected the fixture (no guard change), then red3 showed 87 expected unsupported-keyword failures and 2 legacy omitted-mode positives passing before production implementation.

First focused implementation run had one fixture failure: injected NaN velocity was in a joint slot that the real configure implementation zeroes. It therefore did not reach the intended episode-event error. Moved the authored invalid velocity outside the forty configured joint slots; the real JSON serializer then refused at episode_started after env reset, mj_forward and policy reset. No source/world validation patch was introduced. All original failures and fixture trees remain retained. No quota/ancestor setup refusal occurred and no root was reused.

## Self-review and source custody

`git diff --check` passed. AST review against named baseline engine.py (only that source read from git) found 40 existing function/method definitions; only Engine.open changed. The sole added definition is private _runtime_diagnostics_ok, sharing the unchanged required-status predicate. All existing Engine.open positional/keyword parameters and defaults are AST-identical; only trailing keyword source_bootstrap_mode=None was added. The report is `canonical-bootstrap-evidence/ast-review.json`. The new test file parses and the final run imports it successfully. No tracked source/fixture/profile/pin/plan/ledger outside the two owned files was edited. Root owns the fresh independent spec/quality review.

Readonly roots/assets are current path-and-byte validation, not FD lifetime custody, immutable retention or runtime/import closure. Output uses ordinary RunWriter layout and is not an admitted output location. New authored fixtures clone only static named manifest metadata, with tiny authored archive/checkpoint/graph/mapping/source/lock bytes. No actual checkpoint, graph, mappings, runtime/catalog/SNP, held-out/protected payloads were read or hashed. No all-tracked hash scan, real model/native/physics/source-owner run, research launch, probe/service/dependency/network/CI/push/deletion/cleanup or additional agent occurred. Production atomic recorder temporary-file operations remain ordinary writer behavior.

Account quota UNKNOWN: no first-party quota tool available. Serial ordinary source-unit pytest time is reported below; it is excluded from research CPU accounting. Actual first-experiment cost remains unmeasured. CPU provider choice, two namespace exports, actual GO/input admission/Q/L/F/R/source owner/parent/closure/6a.2 and strict4 integration remain pending. Raw deletion stays disabled. Full goal and 24 CPUh 1/12/5/4/2 accounting plus 96 families x3 x9 are unchanged. These passing units do not complete 6a.2 or the first experiment.

## Exact pytest commands and retained results

All commands ran serially from the worktree above; every basetemp was fresh and retained. No pytest skip reason applies (zero skips throughout). Environment intentionally excludes ambient user environment and hides CUDA. Earlier red/focus shell wrappers printed log tails after pytest; their outer shell exit code therefore does not encode pytest status. The exact raw pytest summaries below are authoritative. Both final pytest commands themselves exited 0, and guarded their fresh basetemp with `test ! -e <basetemp> &&` before execution.

### red-1.log: 8 failed in 0.30s

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest tests/test_memory_source_bootstrap_vnext.py -q --basetemp=/var/tmp/palimpsest-bootstrap-red-20261106-1 > .superpowers/sdd/memory-terminal-vnext-implementation/canonical-bootstrap-evidence/red-1.log 2>&1
```

### red-2.log: 89 failed in 1.72s

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest tests/test_memory_source_bootstrap_vnext.py -q --basetemp=/var/tmp/palimpsest-bootstrap-red-20261106-2 > .superpowers/sdd/memory-terminal-vnext-implementation/canonical-bootstrap-evidence/red-2.log 2>&1
```

### red-3.log: 87 failed, 2 passed in 1.50s

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest tests/test_memory_source_bootstrap_vnext.py -q --basetemp=/var/tmp/palimpsest-bootstrap-red-20261106-3 > .superpowers/sdd/memory-terminal-vnext-implementation/canonical-bootstrap-evidence/red-3.log 2>&1
```

### focus-1.log: 1 failed, 88 passed in 1.01s

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest tests/test_memory_source_bootstrap_vnext.py -q --basetemp=/var/tmp/palimpsest-bootstrap-focus-20261106-1 > .superpowers/sdd/memory-terminal-vnext-implementation/canonical-bootstrap-evidence/focus-1.log 2>&1
```

### focus-2.log: 90 passed in 0.99s

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest tests/test_memory_source_bootstrap_vnext.py -q --basetemp=/var/tmp/palimpsest-bootstrap-focus-20261106-2 > .superpowers/sdd/memory-terminal-vnext-implementation/canonical-bootstrap-evidence/focus-2.log 2>&1
```

### focus-3.log: 96 passed in 1.16s

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest tests/test_memory_source_bootstrap_vnext.py -q --basetemp=/var/tmp/palimpsest-bootstrap-focus-20261106-3 > .superpowers/sdd/memory-terminal-vnext-implementation/canonical-bootstrap-evidence/focus-3.log 2>&1
```

### final.log: 101 passed in 1.18s

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest tests/test_memory_source_bootstrap_vnext.py -q -ra --durations=10 --basetemp=/var/tmp/palimpsest-bootstrap-final-20261106-6d62b19b > .superpowers/sdd/memory-terminal-vnext-implementation/canonical-bootstrap-evidence/final.log 2>&1
```

### final-with-failure-observations.log: 101 passed in 1.19s

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest tests/test_memory_source_bootstrap_vnext.py -q -ra --durations=10 --basetemp=/var/tmp/palimpsest-bootstrap-final-20261106-4ae275f6 > .superpowers/sdd/memory-terminal-vnext-implementation/canonical-bootstrap-evidence/final-with-failure-observations.log 2>&1
```

