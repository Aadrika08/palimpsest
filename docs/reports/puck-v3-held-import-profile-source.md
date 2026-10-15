# Finite held-import profile: source and authored-fixture report

## Boundary and configuration

Base: `8cca8ba42c2eb600bb3f401f380de34655bcbb41` (draft PR133).
Implementation commits: `c615f28`, `60b9438`, `be53322`, `a57cb0d`; authored RED contracts
were retained in `2bf5da5`. Worktree: `/home/utkarsh/.codex/worktrees/0071/brain`,
branch `research/puck-v3-held-import-profile`. Git identity is repository-local
Aadrika Maurya <aadrikamaurya@gmail.com>; publication account Aadrika08.

This unit changes source and tests. It runs authored fresh Python workers and tiny
C libraries, not the installed NumPy/Torch/MuJoCo stack, supplied models, scenes,
catalogs, retained study data, native task physics, collection, fitting or a study.
No consumed observation or scientific attempt was retried. All seven release gates
remain open. The production preflight entry stays preflight-only.

## Working behavior

- Dependency registration v1 remains exact and defaults to the exact leaf-FD
  native route. V2 adds a strict, externally hashed `import_profile` with at most
  1,024 combined export, module-change and native-origin rows. Unknown fields,
  wildcard names, duplicate/overlapping names, unattached/stdlib producers, wrong
  phases, unsupported class paths and native policies for Python modules refuse.
- Export names confer no ambient cache permission. `native_create` or `module_exec`
  resolves a bounded raw attribute path on the exact registered producer object.
  Only that prepared object can later occupy its exact cache key; cache removal,
  substitution, producer-edge drift and undeclared entries refuse. Nested attribute
  paths can differ from cache-name spelling. Producers survive cache replacement.
- Module replacement and in-place reclassification are declared separately. Direct
  class identity is resolved from original producer dictionaries. Generated classes
  bind each captured identity to declared factory code/base/local name; factory and
  method CodeTypes must be the actual compiled held objects, not equal copies.
  This trusts held initialization: it does not instrument factory calls or prove
  arbitrary class construction provenance against malicious in-process code.
- Class/MRO namespace slot and method-code identities and raw module/spec/loader/
  file/package/search metadata are rechecked without framework metadata hooks.
  Replacement originals retain independent metadata seals. Direct module/class/
  function delegate edges captured at phase close keep exact reference identities
  (at most4,096 per virtual seal); new data attributes remain possible. Helper
  receiver/class identity and instance shadows are checked before callbacks.
  Mutable package data and arbitrary global/default/closure state are not a hostile
  in-process isolation boundary. Local support function/class dispatch is checked
  before reconciliation runs and before the complete cache census admits names.
- Explicit `held-directory-observed-v1` uses a held parent FD plus leaf name, with
  target/ancestor guards before loading, full guards around trusted initialization,
  persistent-image registration checks and a mapped held-target inode postcheck.
  Authored glibc2.44 probes pass sibling `$ORIGIN` and `$ORIGIN/../lib` helpers.
  The old leaf-FD sibling-helper failure remains unchanged. Both policies reject
  unregistered persistent helper images.

**Native limitation:** directory-edge replacement during dlopen could execute
changed native code before later refusal. The alternate route observes/detects
persistent mismatches; it does not prevent that race. Baseline/stdlib image trust,
transient/anonymous/JIT code and escaped-process qualification remain outside this
source result. No hostile-root or hard memory/time bound is claimed.

## Finite compatibility candidate

`docs/plans/puck-v3-observed-import-profile-candidate.json` covers every one of the
52 numerical exceptional observation02 rows: 42 exports (40 native children and
two Python-created namespace objects), ten physical module transitions, all twelve
observed module subclasses, and eleven observed numerical extension origin rows.
The source-only test binds the candidate to the retained 304,584-byte report SHA
`a1b70f800a329d1f7c01ca90f836cc37c45a29478707d04ce331444805207045`.

The candidate has no roots/file hashes or execution authority. Native-create
availability is a prospective hypothesis, not measured by the ordinary import
snapshot. Source/runtime/dependency/image/environment registration, a separate
held-runtime qualification and exact launcher/input admission are still required.
The candidate's qualification/execution fields are false and claims empty.

Bounded read-only installed Torch source mapping examined 131,072 unique bytes:
13 explicit producer/helper files plus 4,988 bytes of torch/__init__.py. It mapped
all twelve subclass source declarations. Backends replaces its cache object before
nested child imports; generated ConfigModuleInstance is per factory invocation;
ops/classes are constructed in their producer modules and can be published later.
The cap did not locate their exact torch/__init__.py cache-publication lines; no
runtime timing is inferred. No installed package import occurred in this mapping.

## Verification performed

Interpreter: existing `.worktrees/r0-reproduction/.venv/bin/python` (3.11.15),
with `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=src:.:tests`, no installs and pytest
`-q -p no:cacheprovider`.

| Check | Actual result |
| --- | --- |
| Unchanged dependency custody/worker/bootstrap baseline | 94 passed, 16.31s |
| Native helper RED | 13 failures: helper absent, 0.40s |
| Native helper authored C/API GREEN | 13 passed, 0.26s independently |
| Initial profile RED | 5 missing-v2 positive failures, 19 negatives passed, 21.68s |
| First integration regression | 131 passed, 42.77s |
| Factory/method code-identity and physical-spec RED | 3 failed, 3.45s; equal copies admitted and explicit spec guard absent |
| Expanded profile boundary GREEN | 33 passed, 36.70s |
| Candidate and expanded regression | 141 passed, 53.50s |
| Exact module/spec-loader identity RED | 2 failed, 2.32s; equal-comparing loaders admitted |
| Pre-review root dependency/profile/native/bootstrap regression | 143 passed, 55.66s |
| Independent sequential profile/native slice on601ee9e | 49 passed, 38.09s |
| Independent review regression RED | Six failed, 6.85s |
| Single review fix-pass GREEN | Six passed, 6.65s |
| Final review-fixed root affected regression on a57cb0d | 149 passed, 61.66s |
| Final default repository suite on a57cb0d | Ten collection errors, 1.83s; not a full-suite pass |
| Default repository suite | Ten collection errors, 1.87s; not a full-suite pass |

The exact final focused command is:

```sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
-m pytest -q -p no:cacheprovider \
tests/test_puck_dependency_profile.py tests/test_puck_dependency_files.py \
tests/test_puck_worker_dependencies.py tests/test_puck_worker_bootstrap.py \
tests/test_puck_native_origins.py
```

Default collection errors: test_lab.py and test_male_lab.py lack FastAPI;
test_male_recovery_collection.py, test_male_recovery_data.py,
test_train_male_recovery.py, test_verify_body_adaptation.py,
test_verify_body_runtime.py, test_verify_body_turns.py, test_verify_task_phases.py
and test_verify_task_starts.py lack httpx. These are the same documented environment
limits as PR133; dependencies were not changed. No broad pass is claimed.

Fresh whole-branch review of `601ee9e` found three Important defects: retained
original metadata, proxy delegate identity and instance helper shadowing. No
Critical or Minor findings were reported. Root reproduced all three plus the
other new helper receiver paths in six failing tests, then fixed them in one pass
and ran149 affected checks. The fixed source is `a57cb0d`; it has not had a second
independent review. The initial review verdict remains changes requested, with
its reported findings addressed by explicit RED/GREEN proof rather than a claimed
independent final GO. See [review and rulings](puck-v3-held-import-profile-review.md).

The reviewer's initial concurrent run recorded48 passes/one held-ancestor refusal
in37.62s while separate temporary-directory probes ran. The reviewer attributed
the refusal to concurrent /tmp creation. That contaminated result is retained;
the sequential49-pass38.09s run is the independent test evidence. Neither run is
an installed-stack observation or scientific-attempt retry. Account quota telemetry
is unavailable, so no remaining quota percentage is asserted.

## Next action and outstanding project work

After independent source review/fixes, freeze a separate exact held configuration
and qualification allocation. Review its dependency roots, complete persistent
images (including system GPU/EGL libraries), phase declarations and native trust
window before any actual invocation. Then complete puck inventory/reservation/
scene seals and parent/worker dispatch, independent process identity/progress/
escaped descendants, one-owner lease, storage/clock accounting and durable stage
close. The preflight result and this source result grant none of those stages.
Memory condition/case close remains available as independent source work; actual
memory amendment02, catalog-access and next navigation-study decisions remain
pending. No attempt3 or physical rover work follows from this change.

## Source references

- [CPython3.11 importlib loader/spec contract](https://docs.python.org/3.11/library/importlib.html)
- [CPython3.11 ModuleType metadata](https://docs.python.org/3.11/library/types.html)

These API references inform implementation; authored fresh-worker/C observations
above, rather than documentation alone, establish the reported host behavior.

## Publication and continuing goal

[Draft PR134](https://github.com/Aadrika08/palimpsest/pull/134) is stacked on133.
The authoritative execution goal was advanced in07be15a and synchronized to the
matrix in2befb2b. Three requirements-evidence checks pass0.03s; both goal copies
are byte-identical, links valid, all33 requirement/gate statuses unchanged.
Main remains ee6bf61. The source unit is complete; the full simulation goal stays
active with all seven release gates open and actual held qualification next.
