# Runtime development observation 02: diagnostics and explicit EGL contract

Continue the full seven-gate simulation goal from PR #132, preserving its consumed
observation01. This is a prospective **development** amendment requiring independent source/
freeze review, distinct from memory qualification amendment02. It grants no memory,
catalog, navigation, original-model, native-owner, physics, fitting or study run.
No held-runtime or release qualification follows from ordinary package imports.

## Mechanism and preserved boundaries

The characterizer now publishes result schema v2. Its request schema remains v1;
exact-environment admission and fixed NumPy/Torch/MuJoCo import order remain.
After a failed import/admission it attempts independent cache and persistent-map
snapshots, labels their scope `post_failure` and retains secondary diagnostic
failures without erasing the primary cause. A failure of cache inspection does
not erase a usable map snapshot. A report over one MiB becomes compact failure,
retaining the primary cause, bounded environment diagnostics and overflow size.

Environment changes are sampled after the import phase and after observations;
any observed drift fails the result. Added/removed/changed values are retained as
filesystem-encoded byte counts and SHA-256, not plaintext. Limits are 256 names,
128 changed entries, 256 characters per key and 4096 encoded bytes per value.
Exceeded limits produce an explicitly incomplete diagnostic, never a successful
admission. This is point-in-time diagnostics, not a history of transient changes
or atomic environment custody. Bounded primary exception text remains plaintext;
the frozen environment contains only declared nonsecret configuration values.

Import `SystemExit(0)` is now retained as failure with a nonzero exit, rather than
allowing a successful empty process with no observation terminal. Metadata still
uses raw module dictionaries, not framework `__getattr__`. All cache identities
are retained; direct producer edges remain restricted to explicitly exceptional
identities (aliases, absent/nonstandard specs, absent files or module subclasses).
Cache8192/attribute-edges262144/maps4MiB/65536lines/report1MiB remain unchanged.
Runtime/collection/executable authority stays false and qualification claims empty.

The new [fixed parent](puck-v3-runtime-amendment-02/characterization-parent.py)
binds the unchanged prior failed report SHA, five executable local source files,
the original interpreter and one exclusive observation02 output directory. It
reuses the existing supervisor and hard guard, with unchanged 60s normal/70s hard,
sampled parent-plus-child RSS1GiB, output64MiB, free floor1GiB and maxonechild.
The prior parent/freeze/all evidence files are unchanged, and the original
source worktree remains intact at `8b6d798`. Source-check/import windows, trusted
host/stdlib, sampled resources and process-group-only cleanup remain unqualified;
the capsule is not a held importer, sandbox or complete collection supervisor.

## Source evidence before the actual observation

- Clean parent baseline: 50 focused checks passed, 2.73s.
- Initial eleven amendment REDs: 0.26s, missing environment/partial diagnostics
  and the numbered parent.
- Authored package `SystemExit(0)` RED: 0.08s; old child returned0 with no terminal.
- First diagnostics/parent implementation: 12 checks passed, 0.62s.
- Deterministic late-environment mutation RED: 0.06s; metadata observation could
  previously return observed despite the drift. Added pre/post-observation guards.
- Final focused characterizer/amendment/supervisor slice: **63 passed, 3.48s**.
  New large-report and cache-edge fixtures preserve the primary environment error;
  all new numerical inputs are authored Python package fixtures. No actual
  installed-stack invocation is counted by these source checks.
- Default repository `pytest -q`: **ten collection errors, 1.78s**, missing FastAPI
  in `test_lab.py`, `test_male_lab.py`; missing httpx in
  `test_male_recovery_collection.py`, `test_male_recovery_data.py`,
  `test_train_male_recovery.py`, `test_verify_body_adaptation.py`,
  `test_verify_body_runtime.py`, `test_verify_body_turns.py`,
  `test_verify_task_phases.py`, `test_verify_task_starts.py`. No full-suite pass,
  dependency installation or upgrade is claimed. Ignored raw logs are retained
  in `runs/source-validation/puck-v3-runtime-amendment-02/`.

## Exact prospective freeze and source-derived hypothesis

The [freeze](puck-v3-runtime-amendment-02/characterization-02-freeze.json) SHA is
`aa3dcb432f600d2b84a3b705d19552edb0e390b3bb96ae47a356cf95b1d6e06a`;
its worker request SHA is
`eed779fe3ada56378d1bbc36015bc753a70e0dbf9c18d21bfd1e05f13781322d`.
Original CPython3.11.15 SHA remains
`572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a`.

The actual lab-hardening site root, original environment values and every resource
limit are unchanged. The only new environment key is `PYOPENGL_PLATFORM=egl`.
All three previously inspected MuJoCo source files were rehashed unchanged
(13,849 bytes reread); their EGL source assigns that key when absent and selects
EGL for the frozen Linux/EGL configuration. This source-derived hypothesis is
consistent with observation01; its missing runtime delta prevents proving the
assignment was the only previous mutation. This amendment preserves that limit.

The new isolated source root and exclusive output/argv paths are explicit in the
freeze. The parent requires observation_id2, the exact prior failure SHA and the
explicit EGL key before creating an attempt directory or launching a child.
A fresh whole-branch source and exact-freeze review precedes the one actual run.
At this source checkpoint observation02 is **not invoked**. A failure consumes its
allocation and stops actual installed-stack runs; no automatic observation03.

Frozen command (executed once as recorded below; do not rerun):

```bash
/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
  -I -B -S docs/reports/puck-v3-runtime-amendment-02/characterization-parent.py \
  docs/reports/puck-v3-runtime-amendment-02/characterization-02-freeze.json \
  aa3dcb432f600d2b84a3b705d19552edb0e390b3bb96ae47a356cf95b1d6e06a
```

## Rulings and following project work

Ruling: the amendment changes diagnostics and declares the source-required EGL
key; it does not relax exact environment checks, add import fallbacks, enlarge
resource/census limits or repeat observation01. Unknown values stay hashed;
partial data remain explicitly post-failure. If the hypothesis is incomplete,
preserve the actual failure and its diagnostics before another prospective decision.

Ruling: catch package SystemExit and check environment around metadata collection
because a zero process exit or a partially inspected report cannot be successful
ordinary-import evidence when a detected invariant failed. Native initialization
can execute inside ordinary imports, but no model or simulator API is called.

Manual Git worktree creation finished in the discovery batch that first exposed
a native managed-worktree tool. Preserve the already created isolated worktree;
do not create a duplicate or claim native creation was used. No unrelated user
branch/source or dependency environment was altered.

A valid observed result can inform the finite held dependency profile, explicit
virtual/alias exports and authored origin-relative native fixture. It cannot
establish held bytes, package-path/plugin access, transient/anonymous/JIT closure,
actual owner execution or task capability. Finish that runtime/parent collection
route and memory case-close, then execute only separately admitted studies,
integrate lab/six artworks and obtain user/operator acceptance. All seven gates
and the three prospective memory/catalog/navigation decisions remain open.

## Fresh source/exact-freeze review and actual observation02

Fresh review of clean `380fa2c` (executable source `51d33a7`) found no Critical
or Important defect and passed the exact freeze for **one development observation02
only**. All five source hashes, interpreter hash and prior failure SHA were
independently checked. The fourteen tracked observation01 artifact-tree files
remain byte-identical to the parent. Site/limits match; the only environment
addition is `PYOPENGL_PLATFORM=egl`. The thirteen amendment fixtures independently
passed in **0.63s**; no actual installed package import accompanied review.

The reviewed invocation then ran once on source
`380fa2cb18e44cca3d06680ccc8e8f7e80c97183` at **2026-10-15 01:37:44 UTC**.
Prelaunch checked all source/prior hashes, an absent exclusive directory and
**99,738,644,480 bytes free**. No allocation or source changed after launch.
Observation02 is now consumed; do not rerun its command to refresh evidence.

**Result: observed / supervisor completed, child exit0.** There were no detected
environment changes or diagnostic errors, no supervisor operational failure and
no matching process-group survivors. This is successful ordinary-import evidence,
not a passed held-runtime, model, owner, native-closure or release gate.

| Measured item | Retained result |
| --- | --- |
| Supervisor duration | 1.569026201s |
| Worker observed duration, including diagnostic snapshots | 1.148922862s |
| Sampled parent-plus-child peak RSS | 637,472,768 bytes, about 607.9 MiB |
| NumPy | 2.2.5; import 0.044382101s; cache180 |
| Torch | 2.9.0+cu128; import 1.013691987s; cache1060 |
| MuJoCo | 3.3.6; import 0.078123365s; cache1131 |
| Worker terminal | 304,584 bytes; SHA `a1b70f800a329d1f7c01ca90f836cc37c45a29478707d04ce331444805207045` |
| Cache | 1131 entries /1125 distinct module objects /49462 inspected attribute edges |
| Persistent mapped-file observations | 105 total /12 baseline /93 new; 44 new in selected site,49 outside |

The [lossless manifest](puck-v3-runtime-amendment-02/observation-02/manifest.json)
and ten records retain all **309,449 data bytes** of the exact freeze, request,
invocation, child report/logs, supervision, prelaunch and outer logs. Original
outputs remain under `runs/puck-runtime-import-characterization-02/`; committed
copies are byte-identical. The [derived compatibility observations](puck-v3-runtime-amendment-02/compatibility-observations.json)
retain their source report SHA and deny all runtime/collection/executable authority.
The successful frozen configuration supports the EGL hypothesis; it does not
retroactively prove the unrecorded full mutation set of observation01.

## Actual finite profile gaps, not an admitted runtime profile

There are **95** cache rows with exceptional producer bindings or aliases; **52**
belong to the three numerical top-level namespaces (in this observation these
are Torch entries). File-backed native-produced modules can have no spec, so
`__file__` alone cannot make an ordinary extension-loader registration. The three
explicit alias rows are stdlib aliases; two nonmodule cache entries are stdlib
`typing.io`/`typing.re`. Full raw identities and finite producer edges are retained;
this is no wildcard permission for `torch._C.*` or another namespace.

The twelve numerical module subclasses include VFModule, GenericModule, backend
wrappers, ops/classes, two generated ConfigModuleInstance types and Deterministic.
The current held loader assumes the original ordinary module survives import.
Its future profile needs explicit finite exported-object, replacement/reclassification
and class identity contracts, including the spec-less file-backed `_C` children.
Names/types alone are observations, not source-bound runtime grants. Observe and
bind initialization phase boundaries before admitting cache entries.

New persistent images include packaged CUDA libraries, system GPU/EGL drivers,
MuJoCo plugins and ordinary system libraries even with CUDA visibility empty.
This does not establish GPU computation, CPU model inference or renderer/physics
qualification: no model, render or simulator API was called by the characterizer.
Image membership does not establish held-byte consumption, transient-image or
anonymous/JIT closure. Source/path/plugin/origin-relative handling and root-owned
system-image declarations still need explicit review and actual held qualification.

Next implement a reviewed finite dependency/import profile using these exact
observations and authored fixtures, including distinct module-class/replacement
bindings. Prove the chosen origin-relative native route with authored libraries,
retain the existing exact-file-FD contract, then separately freeze/qualify the
supported held numerical configuration. Connect the complete parent/worker
inventory/reservation/scene/model route, identity/progress/drain/lease/storage/clock
contracts and terminal acceptance before real collection. No study, held-out,
original inference, fitting, browser workflow or consumed science retry ran here.

A parallel bounded source-only memory inspection revalidated `2514c47`: existing
cell replay/custody/compact/source seals can support a condition seal that invokes
replay internally and persists its receipt. All nine ordered condition seals and
then whole-case close remain missing. Those API suggestions are proposed, not
implemented; the trusted successful qualification descriptor remains dependent
on pending memory amendment02 approval, execution and independent close. No
retained payload/model/SNP read, numerical import, edit or test accompanied that
inspection. All seven project gates and three prospective decisions remain open.

An independent retained-outcome audit found no Critical or Important mismatch.
All ten records /309,449 data bytes match the original outputs, and the exact
freeze/request/five source hashes/prior failure binding/expected interpreter SHA,
invocation, receipt, child PID and supervision reconcile. All retained summary
row/image lists and counts were independently recomputed. The 49,462 attribute
edge figure agrees with the worker's counter but is not independently recoverable
from the retained row census. All fourteen observation01 artifacts remain unchanged.
Audit reads stayed within 2 MiB and added no invocation, numerical import, edit
or test. Exactly-once history relies on the exclusive directory and retained
records; no universal process-history or escaped-descendant proof is implied.
The audit validates ordinary-import evidence only, not held-runtime/native-closure,
GPU/model/physics capability or release authority.
