# Actual held-runtime import qualification01 implementation plan

> Execute inline with executing-plans and TDD; independent bounded registration
> builder lane and one fresh whole-branch/source+freeze review before actual input.

Goal: one separately admitted held-import invocation through the authenticated
worker, with exact dependencies/source/runtime/environment and durable outcome.
Spec: active simulation-release-execution-goal.md, next qualification unit afterPR134.
A scoped pass or preserved terminal failure completes this allocation, never the
whole project. Observations01/02 remain consumed. No supplied models, scenes,
catalog/retained-study input, task physics, fitting, held-out or navigation retry.

Architecture: v3 bootstrap selects only fixed palimpsest.puck_runtime_qualification
entry; v1/v2 behavior remains strict/preflight-only. Child imports exactly NumPy,
Torch, MuJoCo in order, checks expected versions and held guards, returns false
execution/qualification authority. A fixed __mp_main__ -> captured __main__ alias
accommodates stdlib multiprocessing without allowing arbitrary cache identities.
Retained observation02 supplies physical module/image selection and non-executable
52-row candidate. A bounded descriptor-based builder hashes the full known package
namespace plus selected /usr/lib images; its hashes are staging, not lifetime custody.
The child independently admits/leases/rehashes those files before any numerical import.

Files: puck_runtime_registration.py owns finite namespace census/hash/map assembly;
puck_runtime_qualification.py owns fixed three-import entry; puck_worker_bootstrap.py
owns v3 registration/dispatch/alias identity. scripts/qualify_puck_held_runtime.py
owns exact freeze, exclusive allocation, source capsule, source/dependency registration,
existing bounded supervisor, bounded terminal outcome and failure preservation.
Tests: test_puck_runtime_registration.py, test_puck_held_runtime_entry.py,
test_puck_held_runtime_parent.py plus existing worker/dependency/bounded suites.

Interfaces: build_registration(site_root,observation,profile,*,deadline)->strict
v2 dependency registration dict. qualify(admission)->bounded three-import result,
no authority. Parent reads a canonical externally SHA-pinned freeze and uses
fixed source closure; qualification entry and package roots are never arbitrary
argv-selected code. Agent owns only builder/tests; root owns all integration.

Prospective allocation01 (must be reviewed before actual invocation): registration
at most180s; child at most180s normal/190s hard; total normal360s/hard390s; child
supervision samples parent+child at2GiB, output transport64MiB, total artifacts96MiB,
free floor1GiB, at mostone child; dependency16GiB logical/file2GiB/32768files/
60000entries/registration16MiB/metadata64MiB; original pinned3.11.15 interpreter.
Staging uses chunk/deadline/count bounds and post-stage parent high-water RSS check;
this is operational control, not hard RSS/WCET/escaped-descendant proof. No budget
borrowing. All actual stages serial; no unrelated /tmp or watched-ancestor mutation.

Review focus: no ordinary loader fallback; exact source before compile; special
stdlib main alias exact identity; all known nonstdlib cache rows classified; missing/
ambiguous map or unexpected file image refusal; duplicate/hardlink/symlink identity;
registration staging drift; marker/output no-clobber; fail before runtime import;
trusted parent/source native windows; complete failure/outcome cleanup records.

- [ ] Task1: RED fixed v3 entry/alias/strict descriptor cases; implement; GREEN
  existing v1/v2 and149 profile/custody/bootstrap regressions.
- [ ] Task2: builder RED/GREEN authored snapshots/deadlines/path/identity/maps;
  integrate exact source capsule and parent freeze, allocation and durable close.
- [ ] Task3: authored parent positive/negative/no-retry proof, full-suite attempt,
  one fresh whole-branch and exact actual-freeze review. Fix important findings
  once with explicit RED/GREEN; any change of actual freeze requires exact review.
- [ ] Task4: after source+freeze admission, execute allocation01 once, preserve
  every terminal/failure record, independent outcome audit without rerun, publish
  incremental commits/draftPR and update goal/matrix with unchanged release gates.

Initial state: PR134 ce4b55f clean; productiona57cb0d had149 affected checks61.66s;
all seven release gates open. Actual runtime qualification01 has not been invoked.
Three prospective study decisions remain pending; no new approval inferred.
