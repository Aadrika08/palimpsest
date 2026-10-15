# Finite held-import profile implementation plan

> Execute inline with executing-plans and TDD; one fresh whole-branch review.

Goal: complete the worker integration for finite producer exports, module
replacement/reclassification and native origin policy identified by PR #133.
Spec: simulation-release-execution-goal.md on research/simulation-completion-next;
the independently audited observation02 supplies compatibility data only.

Architecture: dependency registration v1 remains exact. Version2 adds one finite
import_profile with exports, module_changes and native_origins. Producers are
registered physical Python/native modules; exported cache names never gain access
without the exact object resolved from raw producer attributes at their declared
phase. Direct class anchors use original producer dictionaries; generated classes
use held compiled factory code, declared local class/base identities and per-call
captured class identity. No framework metadata hooks run during capture/recheck.

Files: puck_dependency_bindings.py owns profile validation and object/class seals;
puck_dependency_files.py owns held registration access; puck_dependency_imports.py
owns phases and loader integration; puck_worker_bootstrap.py checks support code
before invoking reconciliation, then applies the existing complete cache census.
puck_native_origins.py owns the explicit native path and mapped-target contract.
Tests: test_puck_dependency_profile.py, existing dependency/bootstrap suites and
separate authored C origin fixtures in test_puck_native_origins.py.

Constraints: no installed stack rerun, model/scene/catalog/retained input, physics,
collection, fitting or scientific/held qualification. Observations01/02 consumed;
no new navigation attempt. Public claims remain false. No dependency installs.
V1 leaf-FD route remains unchanged. Directory-FD origin is detection after a trusted
native initialization window, not prevention of a concurrent namespace swap.

Review focus: native exports during create before cache insertion; replacement
before child imports; exported instances published later; fresh generated classes
per factory invocation; raw metadata hooks; post-import object/class/code/edge
mutation; unknown/declared-but-unprepared names; helper dispatch tampering.

- [ ] Task1: authored fresh-worker RED fixtures for declarations and transitions;
  strict finite schema and phase integration; green existing v1 regressions.
- [ ] Task2: authored C RED/GREEN origin proof preserving v1, explicit v2 loader
  integration and unknown persistent-image rejection; record host limitations.
- [ ] Task3: complete native-create export fixture and generated-factory mutation
  negatives, exact candidate profile covering 52 observed exceptional rows, source
  closure/dispatch regression; focused regression, full-suite attempt, one fresh
  whole-branch review and one RED/GREEN important-finding pass if required.
- [ ] Task4: retain source report, commit/push draft PR stacked on133; synchronize
  authoritative goal/evidence without changing any of the seven gate statuses.

Verification command: existing R0 Python with PYTHONDONTWRITEBYTECODE=1 and
PYTHONPATH=src:.:tests; pytest -q -p no:cacheprovider tests/test_puck_dependency_profile.py
 tests/test_puck_dependency_files.py tests/test_puck_worker_dependencies.py
 tests/test_puck_worker_bootstrap.py tests/test_puck_native_origins.py.
Baseline94 passed16.31s before edits. No whole-suite pass is assumed.

Preflight shared interfaces: provider.import_profile() returns a detached validated
profile (v1 empty); DependencyImports owns begin/complete/capture phase callbacks;
ExportBindings.recheck() returns exact activated cache names only; bootstrap invokes
it after authenticated local support function/class checks, before global cache
census. Native helper APIs frozen in the independent authored-fixture task.
Ruling: implement inline, with independent bounded native-helper task permitted by
efficient-frontier; single fresh integration review at end. Preserve scope and
all source/runtime qualification distinctions. No new prospective study decision.
