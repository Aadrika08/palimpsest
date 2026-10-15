# Versioned four-import runtime entry: source evidence

Source commit `2a1b3aa` adds qualification descriptor-v3 inside the unchanged
bootstrap-v3 envelope. Its exact expected_versions keys are numpy, torch,
torchvision and mujoco. The fixed import order is NumPy → Torch → torchvision →
MuJoCo. It accepts no arbitrary entry or import list. Before numerical initializers,
the active dependency provider's public custody snapshot must attest dependency-v3
`tmpfs-raw-dev-inode-v1`; all finite missing-import proof, local-name overlap and
receipt protections from descriptor-v2 also apply. Expected versions are captured
before initializer effects so rewriting registration expectations cannot disguise
a wrong package version.

New entry receipts use `puck-held-runtime-import-qualification-result-v2`, version2,
with qualification_version3. All runtime/native/collection/execution claims remain
false. Descriptor-v1/v2 keep their three-import order and result-v1. This route
can support a future CPU configuration; it does not force or qualify CPU binaries,
native operators, codecs, rendering, inference or a scientific study.

## Verification

Only tiny authored package forests and the real isolated worker were used.

| Check | Actual result |
| --- | --- |
| Initial new-file RED | 6 failed /18 passed in4.39s |
| New source GREEN | 25 passed in17.47s |
| New + legacy entry + expected-missing slice | 61 passed /1 failed in34.12s |
| Independent focused source verification | 38 passed /1 failed in22.94s |
| Root isolated legacy alias refusal on owned storage | 1 passed in1.30s |

The initial RED includes five intended unsupported-descriptor failures and one
narrow error-message assertion corrected for existing canonical-JSON refusal.
The broader implementation failure was the existing shadowed-provider callback
control encountering ancestor drift during email.quoprimime import before
provider admission. That callback control passed during independent verification;
that run instead refused an ancestor change while loading the qualification entry
for the legacy bad-alias control. The latter passed separately under a fresh owned
Btrfs basetemp. No guard was relaxed, no test skipped and no full-suite pass claimed.
All25 new cases passed in both complete source-verification runs.

Independent whole-source review against19b640e found no concrete Critical,
Important or Minor defect after inspecting the connected parser, custody,
import/absence, dispatch and receipt contracts. Exact independent command:

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python -B \
-m pytest -q -p no:cacheprovider \
tests/test_puck_cpu_runtime_entry.py \
tests/test_puck_held_runtime_entry.py \
tests/test_puck_expected_missing_imports.py::test_absence_exemption_cannot_use_a_shadowed_provider_callback
```

Root's isolated check used the same interpreter/environment and pytest options,
`--basetemp runs/cpu-legacy-alias-check-01`, and
`tests/test_puck_held_runtime_entry.py::test_fixed_entry_retains_no_success_when_import_or_identity_gate_fails[bad-alias-alias]`.
That is an authored regression, not a numerical allocation retry.

## Remaining actual route

The [CPU candidate](../plans/puck-cpu-runtime-candidate-v1.json) and
[metadata assessment](puck-cpu-runtime-footprint.md) remain explicitly unadmitted.
The actual allocation01 parent still constructs the old three-import descriptor;
it is not a CPU preparation/qualification parent. A complete separately numbered
parent/configuration, source wheel build, payload verification, installed namespace,
renderer/stdlib/external-image configuration, RAM/storage/custody/process/clock
admission and independent exact/outcome audits remain required. No consumed command
was rerun. No installed numerical package, model, scene, catalog, renderer context,
physics, collection, training or browser/human session ran. All seven simulation
release gates remain open.
