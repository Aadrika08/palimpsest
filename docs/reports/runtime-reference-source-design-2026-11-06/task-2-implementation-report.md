# Task 2 implementation handoff

Task 2 is implemented and ready for independent review. Commit:
`f00dc47420b2f7651fa661dbd946b1786ca8cc94` (`feat(memory): add private V3 source-owner runtime custody`).
Base: `eebd51a3c6f40e025b6dbddef14bf62b84cb78e3`; branch `research/source-cpu-compat-v1`.
Only these four tracked files are in the commit:

- `scripts/memory_family_source_runtime_v2.py`: 155 additions / 20 deletions.
- `tests/test_memory_family_source_runtime_v2.py`: 462 additions, preserving the original V2 tests/fixtures.
- `scripts/memory_source_runtime_closure_v1.py`: 5 additions, exclusively the pure `_pins` export wrapper.
- `tests/test_memory_source_runtime_closure_v1.py`: 25 additions, exclusively the focused export test.

## Delivered contracts

- `_runtime_requirements` (owner line 101) validates exact independent roots/config/source metadata, uses Task 1's path grammar and exported five-pin validator, checks the lexical config location, allows identical redundant semantic pins, rejects contradictions, and returns independent collections.
- V3 metadata (line 126) accepts exactly the five immutable fields from the amendment; V2 retains its original inline closure, descriptor size policy, serialized hash, and validation restrictions. Mixed/unknown versions refuse without payload IO. The V3 complete admitted serialization gets its own 256 KiB check in addition to the unchanged admission-excluded hash cap. V3 source paths also use Task 1's POSIX path/component/UTF-8 bounds.
- V3 admission (line 214) binds manifest/profile digests and two finite non-bool absolute deadlines. Source remains within 360 seconds, source <= runtime, runtime remains future and <=900 seconds away. Neither value is reset by the private owner.
- Public `run_source` (line 529) validates V3 metadata/admission then immediately refuses `retained-unqualified`, before any holder, live-layout lookup, loader, storage allocation, payload open or output write. No public flag or loader injection was added.
- `_run_reference_admitted` (line 487) is exclusively a private authored seam. It validates the job, checks its own live layout, enters a fresh process-local handle with the independently supplied roots/five pins and unchanged runtime deadline, checks held descriptors, invokes the zero-argument loader factory only after successful custody/layout checks, and passes the returned opener to the existing core. Identity callbacks repeatedly use the active handle; no V2 closure list or parent handle is used.
- `_check_reference_layout` (line 465) checks all five executing prefix obligations, covering nested requirements with an outer required root; it requires all six named source helpers at actual checkout paths. Executable alias/ELF checks use the existing post-gate symlink mechanisms and `/proc/self/exe`, never a newly computed expected source digest.
- `_run_admitted` (line 351) selects the finite outcome/failure schema pair before any failure construction/write; V2 canonical failure bytes and all existing V4 owner/V3 worker report fields remain unchanged. A V3 custody/close/deadline failure propagates and cannot return recorded. Existing core failure artifacts remain unchanged, with no second overwriting writer.
- `validate_runtime_pin_requirements` (helper line 257) is exactly a pure wrapper around existing `_pins`; no Task 1 internals, profile, limits, namespace custody, accounting or fixes changed.

## Verification and retained logs

Working directory for every command:
`/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite`.

All commands used the explicit venv alias, `-B`, clean opt-in environment and disabled pytest plugin autoload. Each invocation had a unique basetemp; outputs and failed logs remain retained. No full suite or CI was run.

Final exact command (exit 0; **149 passed in 38.72s**):

```bash
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_source_runtime_closure_v1.py tests/test_memory_family_source_runtime_v2.py --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/final-tmp > .superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/final.log 2>&1
```

Earlier exact invocations and results, in order:

```bash
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_runtime_v2.py tests/test_memory_source_runtime_closure_v1.py::test_pin_requirements_validator_is_pure_copied_and_zero_byte_eligible --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/red-metadata-tmp > .superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/red-metadata.log 2>&1

env -i HOME=/home/utkarsh PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_runtime_v2.py tests/test_memory_source_runtime_closure_v1.py::test_pin_requirements_validator_is_pure_copied_and_zero_byte_eligible --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/red-metadata-2-tmp > .superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/red-metadata-2.log 2>&1

env -i HOME=/home/utkarsh PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_runtime_v2.py tests/test_memory_source_runtime_closure_v1.py::test_pin_requirements_validator_is_pure_copied_and_zero_byte_eligible --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/green-metadata-tmp > .superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/green-metadata.log 2>&1

env -i HOME=/home/utkarsh PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_runtime_v2.py tests/test_memory_source_runtime_closure_v1.py::test_pin_requirements_validator_is_pure_copied_and_zero_byte_eligible --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/green-metadata-2-tmp > .superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/green-metadata-2.log 2>&1

env -i HOME=/home/utkarsh PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_runtime_v2.py -k 'private_v3 or owner_uses_parent_runtime or owner_final_checks or owner_custody_failure or owner_outcome_and_failure or unknown_core' --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/red-private-tmp > .superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/red-private.log 2>&1

env -i HOME=/home/utkarsh PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_source_runtime_closure_v1.py tests/test_memory_family_source_runtime_v2.py --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/green-private-tmp > .superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/green-private.log 2>&1

env -i HOME=/home/utkarsh PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_family_source_runtime_v2.py -k 'asset_paths_obey or requires_each_named or requires_every_live or deadline_includes_handle' --basetemp=.superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/red-boundaries-tmp > .superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/red-boundaries.log 2>&1
```

| Log basename | Exit | Result | Interpretation |
|---|---:|---|---|
| red-metadata.log | 1 | 7 failed, 60 passed, 8.60s | Missing V3/export behavior plus an initially oversized test fixture. |
| red-metadata-2.log | 1 | 7 failed, 60 passed, 9.51s | Fixed the fixture sizing; missing V3/export behavior remains red. |
| green-metadata.log | 1 | 6 failed, 61 passed, 8.60s | New fixture incorrectly used an outer root overlapping its own temp venv/output; corrected to the independent required source prefixes. |
| green-metadata-2.log | 0 | 67 passed, 8.51s | Metadata/export behavior green after fixture correction. |
| red-private.log | 1 | 17 failed, 2 passed, 66 deselected, 2.24s | Missing private seam and unknown-schema early rejection; old V2 cases remain passing. |
| green-private.log | 0 | 132 passed, 34.05s | Task 1 + owner checks green. |
| red-boundaries.log | 1 | 5 failed, 12 passed, 85 deselected, 0.99s | Additional asset path grammar cases fail; every required source/prefix and teardown deadline already pass. |
| final.log | 0 | 149 passed, 38.72s | Two focused modules green after V3-only path-bound fix. |

All log/basetemp paths are under `.superpowers/sdd/runtime-reference-v1-implementation/task-2-logs/`; no cleanup was performed.

Additional exact checks (passed with no whitespace errors / no diff for CPU compatibility files):

```bash
git diff --check -- scripts/memory_family_source_runtime_v2.py scripts/memory_source_runtime_closure_v1.py tests/test_memory_family_source_runtime_v2.py tests/test_memory_source_runtime_closure_v1.py
git diff --exit-code eebd51a -- scripts/qualify_memory_family_source_v2.py tests/test_memory_source_cpu_limits.py
git diff --cached --check
git diff --cached --name-only
git commit -m 'feat(memory): add private V3 source-owner runtime custody'
git show --stat --oneline --summary HEAD
git status --short
git rev-parse HEAD
```

## Self-review, scope and limitations

Reviewed the source diff against the Task 2 brief/amendment for V2 compatibility, public refusal ordering, independent requirements, exact source membership, nested prefix coverage, original absolute deadlines, zeroarg loader sequencing, first-write schema selection and custody failure propagation. Existing tests are untouched before their appended additions. No additional production framework/validator was introduced.

Private tests use the existing authored engine fixture, recording fake process-local handles and explicitly substituted alias/ELF lookups. They exercise the actual owner core's recording/snapshot/report/failure paths with tiny generated test data; they do not establish installed runtime custody, model behavior, preparation completeness, pre-import identity, accounting authenticity, scientific/resource fit or execution authority. Task 1's own named authored custody tests passed as part of the two-module run. No actual installed interpreter/site-packages census, hashing, collection, preparation, real model/raw/SNP input access or broad tracked-file hashing was performed. Existing named-owner identity tests read only their explicitly named source and authored tiny inputs.

A tentative recorded raw report remains retained if handle close subsequently fails; the exception propagates, no recorded outcome returns, and no second owner failure writer is added. The parent may record teardown failure in its own controls. If core failure evidence already exists it remains byte-identical.

Task 3 parent integration and independent review remain outstanding. Real V3 execution remains closed; backend/collector/lifetime qualification remains unresolved. No protocol, actual resource ceiling, old Puck cap, per-holder policy, CPU compatibility helper or GO changed. No full suite/CI or production/native/model execution was requested or run.

Unrelated root-owned changes to `docs/plans/project-completion-2026-11-05.md` and untracked `docs/reports/compact-paper-adequacy-2026-11-06/` were observed, reported and preserved; they are excluded from this commit. This ignored handoff report and all evidence logs are retained but not added to the four-file commit.

No blocking ambiguity remains for this Task 2 slice. Review readiness: ready for root's independent review; no actual-execution readiness claim.
