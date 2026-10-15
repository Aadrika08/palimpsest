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
The exact org denial has no ambient fallback and does not poison the worker:
original CPython3.11.15 pickle.py101–105 probes Jython and handles ImportError.
All other unexpected import failures poison; their original cause is retained.
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

Two separately reviewed allocation01 freezes are required. Preparation01 creates
exact dependency hashes and source capsule before qualification configuration
review; it imports no installed numerical packages. Qualification01 then consumes
an externally SHA-pinned preparation receipt and independently rehashes/leases
actual inputs through the child. No input pins are invented inside qualification.

Prospective preparation allocation: normal180s/hard190s; streaming registration
within180s;2GiB post-stage parent high-water stop check,96MiB artifacts,1GiB free
floor, FDsoftfloor40000. Prospective qualification allocation: normal180s total,
childhard190s/parenthard200s; existing supervisor samples parent+child at2GiB,
transport64MiB/artifacts96MiB/free1GiB/onechild/FDfloor40000. Combined active normal
allocation360s/hard390s, no borrowing; independent review between stages is outside
these active invocation clocks. Child bootstrap remains180s. Dependency logical
16GiB/file2GiB/32768files/60000entries/registration16MiB/retainedmetadata64MiB;
original pinned3.11.15 interpreter. These are operational controls, not hard RSS,
WCET, sandbox or escaped-descendant proof. Actual stages remain serial.

Review focus: no ordinary loader fallback; exact source before compile; special
stdlib main alias exact identity; all known nonstdlib cache rows classified; missing/
ambiguous map or unexpected file image refusal; duplicate/hardlink/symlink identity;
registration staging drift; marker/output no-clobber; fail before runtime import;
trusted parent/source native windows; complete failure/outcome cleanup records.

- [x] Task1: RED fixed v3 entry/alias/strict descriptor cases; implement; GREEN
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

Progress: builder39 RED→GREEN0.07s; fixed-entry/strict alias/denial/first-cause plus
inherited regressions201pass69.47s. Authored two-stage parent13pass5.28s. Source
implementation8dee733 plus current parent. Actual preparation/qualification remain
uninvoked. Exact freezes and independent prospective review are still required.
Ruling: separate preparation from imports so actual dependency/source hashes exist
before exact qualification review. Cost if skipped: qualification would authorize
its own newly discovered inputs. Ordinary observations stay consumed/unmodified.
