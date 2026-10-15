# Numerical import characterization and remaining runtime compatibility

The full simulation release goal remains active; all seven release gates are open.
This unit implements an ordinary-import development observation of the exact
installed NumPy/Torch/MuJoCo stack. It is not held-runtime qualification, original
model qualification, a collection owner, a physics run, fitting or a study attempt.
No memory amendment, catalog access or navigation decision is supplied by it.

## Source path and verification

`scripts/characterize_puck_runtime_imports.py` validates a canonical externally
hashed 64 KiB request before importing any numerical package. It requires a fresh
`-I -B -S` process, an exact environment and one explicit canonical site root.
It records raw package versions, cache names versus canonical specs, finite direct
producer attributes/object aliases and persistent mapped-file observations.
Module dictionaries are inspected directly; framework `__getattr__` is never
used to discover metadata or exports. No inference or simulator entry point is
called. Libraries can execute native initialization as part of ordinary imports;
this is trusted development code, not an import sandbox.

Bounds: cache 8192 entries, 262144 module attribute edges, mapped observation
4 MiB / 65536 lines, terminal report 1 MiB. Import/environment/budget failure is
retained as failure and never advances to the next package. An oversized full
report yields a compact failure instead of truncated successful evidence.
Results always deny runtime qualification and collection authority.

The frozen [parent capsule](puck-v3-runtime-interop/characterization-parent.py)
reuses `bounded_qualification.supervised` and its hard guard. Its complete local
source declaration includes `evaluate.py` (the supervisor's lazy log dependency)
and package initialization. A fresh exclusive output directory prevents a second
invocation, including after a failed child. The exact source hashes, interpreter
hash, request and fixed allocation are in the
[freeze](puck-v3-runtime-interop/characterization-01-freeze.json).
The capsule observes source identities before execution; it does not implement
held import custody or establish atomic source/dependency/native closure.

Observed source checks, before the actual installed-stack invocation:

- Five missing-script REDs: 0.04s; then five passing fixtures: 0.11s.
- Thirteen characterization checks: 0.30s; those plus the existing supervisor
  checks: 47 passed, 2.61s.
- New parent-capsule RED: missing capsule, 0.05s. Its authored execution then
  exposed missing `palimpsest.evaluate` in the prospective source closure; it
  was corrected before any installed-stack invocation.
- Explicit aged-atime unchanged-file RED: 0.05s. Read identity now excludes
  access time while retaining device/inode/mode/link count/size and nanosecond
  modification/change times. No runtime, source or content hash was relaxed.
- Final authored child/one-attempt, metadata/resource/failure and supervisor
  checks: **49 passed, 2.85s**. These use authored numerical package fixtures,
  not the actual installed numerical stack.

The full repository `pytest -q` command was also run in the unchanged R0
interpreter: **ten collection errors, 1.78s**. Missing FastAPI affects
`test_lab.py`, `test_male_lab.py`; missing httpx affects
`test_male_recovery_collection.py`, `test_male_recovery_data.py`,
`test_train_male_recovery.py`, `test_verify_body_adaptation.py`,
`test_verify_body_runtime.py`, `test_verify_body_turns.py`,
`test_verify_task_phases.py`, `test_verify_task_starts.py`.
No full-suite pass is claimed and no packages were installed or upgraded.
The new scripts do not modify the existing collection/runtime implementations;
the focused affected scope is the characterizer, parent and reused supervisor.
Raw source-check logs are retained under
`runs/source-validation/puck-v3-runtime-interop/` (ignored).

## Frozen installed-stack observation, not qualification

Use the unchanged R0 CPython 3.11.15 interpreter and the exact lab-hardening
Python 3.11 site root specified in the freeze. Interpreter SHA remains
`572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a`.

The fixed allocation is 60s normal / 70s hard, sampled parent-plus-child RSS
stop threshold 1 GiB, output cap 64 MiB, free-space floor 1 GiB, one child.
RSS sampling, clocks and process-group cleanup are operational controls, not
hard memory/WCET/escaped-descendant qualification. The capsule uses only two
output subdirectories and the supervisor's existing bounded log drains.

The exact prospective environment predeclares NumPy's two OpenBLAS/GotoBLAS
flags, caps numerical thread counts, disables CUDA visibility and Torch device
backend autoload, and selects EGL/Agg. This avoids guessing how environment or
third-party backend entry points should be admitted by the later held worker.
These values describe this development observation only. A successful ordinary
import cannot qualify the held finder, package-path resource/plugin resolution,
origin-relative ELF dependencies, or transient/anonymous/JIT native closure.

Execution status at source freeze: **not invoked**. Source/freeze review and a
fresh free-space check precede the one installed-stack invocation. Preserve any
failure and do not automatically retry. No model, scene, catalog or retained
study payload is an input to this observation.

## Rulings and next work

Ruling: use one ordinary-import characterization to learn the actual finite
virtual/alias export set before defining the held dependency profile. Do not
add wildcard cache authority or an ambient import fallback. If observations are
incomplete, the held profile stays unqualified rather than guessing.

Ruling: the parent capsule is an evidence artifact for this fixed development
allocation, not a replacement study supervisor or a new native execution grant.
The authored parent test exposed its transitive log dependency before the actual
run; all five local source files are now declared. Remaining host/stdlib trust
and source-check/import windows are explicit.

The earlier read-only installed-source audit exceeded its 1 MiB read budget
(reported 2,538,435 unique bytes including repository reads). This was a source
read-budget deviation, not a numerical/model/study invocation; the original
budget must not be reported as met. No installed payload hashing or numerical
qualification follows from that audit.

After the observation, use explicit source-bound finite virtual exports and
an authored native origin-relative fixture to settle the supported runtime
route. Preserve the old exact-file-descriptor route; any directory-descriptor
alternative needs its distinct before/after-edge and mapped-inode guarantees
stated and reviewed before adoption. Then separately freeze and qualify the
held numerical configuration and complete inventory/reservation/scene/model,
worker dispatch, parent identity/progress/drain, lease/storage/clock integration.
The six artworks remain simulation-first; CI and physical rover remain excluded.

Frozen invocation (prospective until the retained result below is added):

```bash
/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
  -I -B -S docs/reports/puck-v3-runtime-interop/characterization-parent.py \
  docs/reports/puck-v3-runtime-interop/characterization-01-freeze.json \
  d5b3cfa43f5269cae187bfd73e53361039331cc5410f412c5930e2dac8d432bc
```

The request SHA is
`7c6331c64226b8ea4f36292a3fc3fedab60c54760d7e82e415400ed7e6cc0f89`.
Do not rerun this command to refresh an observation; its exclusive attempt marker
is retained after success or failure.
