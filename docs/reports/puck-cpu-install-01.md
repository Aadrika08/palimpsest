# CPU installation 01: retained files, failed preparation acceptance

The pinned offline installer wrote all71 candidate distributions and exited0.
The enclosing allocation exited1 after29.518958525s because the supervisor rejected
log teardown: `native log drain/final sync timed out`. **Allocation01 remains
FAIL and consumed; installation acceptance and numerical qualification are false.**
No installer rerun, numerical import, model, scene, catalog, physics or study ran.

The [summary](puck-cpu-install-01.json), [original result](puck-cpu-install-01/raw/result.json),
[full evidence index](puck-cpu-install-01/evidence-index.json) and
[frozen configuration](puck-cpu-install-01/raw/configuration.json) retain the
exact outcome. Source was committed before invocation as
161eb2839182168da5ff78e52ebeae25f2f52c04. Configuration SHA256 is
edc9f98bb546212f9f8e07722f04ca4be0a3cbf63d68a38033b50ae3d44709b4.
All14 source pins and the trusted host baseline are copied under `source/`.

## What actually ran

A source-pinned CPython parent reverified all71 archives and wheel payloads, then
ran an authored poison-package/hook fixture and the target UV0.9.25 installation
in separate bubblewrap namespaces. Each had private network/user/PID/mount state,
read-only tool/interpreter/wheel inputs, a clean environment and only fresh SITE
and scratch writes. The trusted interpreter's observed setuptools shim was
explicitly disabled; UV's ordinary interpreter probe still runs trusted helpers.
There is no claim that no Python code anywhere ran.

Fixture group2370311 returned0 and completed with no survivors. Target group2370341
returned0 but its supervisor failed. Target combined sampled peak RSS was
232,443,904B; sampled SITE+scratch peak2,444,216,286B. Both groups were independently
rechecked empty after the parent ended. Sampling thresholds are operational stops,
not hard aggregate quotas or a hostile-tool guarantee. All original finalizer
outputs that were absent remain absent; derivative evidence is stored separately.

The two-second thread join in `evaluate.bounded_logs` establishes only that a log
thread remained alive. It does not identify stream or whether it was reading,
writing, flushing or syncing. The logs contain UV's full71-package completion
summary. No specific Btrfs/fsync root cause is established, and the timeout was
not increased or bypassed.

## Independent retained-namespace evidence

The prepared [acceptance audit](puck-cpu-install-01/acceptance-audit.json) exited1
in3.697s. Its first refusal is the pinned NumPy wheel's existing
`numpy/distutils/__pycache__/conv_template.cpython-311.pyc`. The original census
rejects all bytecode. This member already exists in the authenticated source wheel;
its presence does not prove installer compilation or execution. Do not delete it
or silently relax the policy to obtain a pass.

The separate [preserved-failure audit](puck-cpu-install-01/failure-audit/report.json)
exited0 in8.914s with `PRESERVED_FAILURE_VERIFIED`, while explicitly keeping
`accepted_installation:false` and every runtime/study/collection authority false.
It independently verifies exact archive identities, all immutable payloads,
installed RECORD paths/hashes/sizes, all18 UV launchers, the community shebang,
local-wheel metadata and both raw namespace/process receipts. It measures:

| Retained evidence | Actual value |
| --- | --- |
| Distributions | 71 |
| Installed regular files | 27,225 |
| Installed directories, excluding SITE root | 2,074 |
| Installed regular-file bytes | 1,304,701,872 |
| Retained licence files / bytes | 96 / 1,576,818 |
| Source-authentic `.pyc` / target `.pth` files | 1 / 0 |

These are regular-file bytes, not filesystem block allocation or runtime RAM.
The complete [file census](puck-cpu-install-01/failure-audit/inventory.json) and
[licence manifest](puck-cpu-install-01/failure-audit/licences.json) identify every
retained byte. The licence contents are copied under that audit directory.
The [auditor](puck-cpu-install-01/failure-audit.py) imports only the reviewed
[helper](puck-cpu-install-01/acceptance-audit.py), never a target package. Its
report SHA256 is8761fee111396ae46c071a60b25da932f75b7ee6d8ce34924ec3284296000b12.

A separate [current host check](puck-cpu-install-01/post-failure-host-check.json)
rehashes the full4,233-file/1,048-symlink interpreter prefix, nine external libraries,
bubblewrap and UV. They still match their pins. This does not fill the missing
original `baseline-after.json` or establish the original log drain completed.

The installed tree remains local at
`runs/puck-cpu-install-01/site` in the CPU worktree; it is not committed to Git.
The archived source, acquisition/build pins and census identify it reproducibly.
To rerun the read-only historical auditors, restore their checksum-matching helper,
layout and acceptance receipt to the exact `/tmp` paths declared in their source,
use the selected interpreter with `-I -S -B`, and preserve fresh output paths.
The consumed installer command must not be rerun as an audit.

## Source checks and next exit

All124 focused checks pass in3.68s, including an explicitly enabled real authored
namespace installation. Initial red tests and the review-caught reservation/cache
issues preceded source freeze. An initial combined test run had118 passes and four
child import failures from the wrong editable checkout; explicit CPU PYTHONPATH
corrected them. No full-suite pass is claimed; historical FastAPI/httpx collection
limits were not rerun or reclassified.

Next: review the [retained-tree admission proposal](../plans/puck-cpu-retained-installation-admission-v1.md).
It defines a new ordinary read-only preparation stage, retaining allocation01's
FAIL and the strict original policy. It must explicitly admit only authenticated
inert bytecode, establish complete current custody and durable new receipts, and
produce a distinct acceptance record before numerical qualification. Do not rerun
installation to collect missing receipts. All seven simulation release gates,
all original scientific thresholds and pending decisions remain unchanged.
