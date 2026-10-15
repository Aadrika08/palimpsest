# CPU primary import failure: preserve the first denial as the explicit cause

**The narrow source fix is implemented and its focused regression passes. Both
affected three-file batches retain one failure; no fully green batch is claimed.**
This is source-only evidence. The first cause of actual Torch qualification 01
remains unknown, and this unit authorizes no actual retry or allocation 02.

Source and test commit: `6d52855fa27d579d6a60049bdb32cbc50dae7aea`, based on
`4036a382b87ab99640bed96f6b2f8aeaa7873b2c`. The final
[bootstrap snapshot](puck-cpu-primary-import-failure-v1/final-source/scripts/puck_worker_bootstrap.py)
is 38,375 B, SHA256 `436b1ffe34b96fca166f6fb38022ad7392daef3517e58157092db2d9fd84c69f`.
The [test snapshot](puck-cpu-primary-import-failure-v1/final-source/tests/test_puck_worker_dependencies.py)
is 10,502 B, SHA256 `fb311232bcea45c52d9ba45a78361ab586c9025800a8bb72fd354870c75b5f09`.
The [bounded diff](puck-cpu-primary-import-failure-v1/source-diff.patch) changes
only `invoke` exception handling and adds one 18-line authored native regression.
After `_fail(error)` stores the first failure and closes custody, a distinct
secondary terminal exception is raised explicitly from that stored failure. The
same primary exception is re-raised unchanged. Denial, poisoned-state behavior,
custody, authority, profiles and frozen actual controls are unchanged. A separate
read-only review of this narrow diff found no material issue; it ran no tests.

The two [authored native diagnostics](puck-cpu-primary-import-failure-v1/diagnostic-01/results.json)
on unchanged source head `102a4a9` pass: package-from-list import in 1.419123732 s
and direct submodule import in 1.336922409 s (root terminal `c0520c`). The
[caught-optional diagnostic](puck-cpu-primary-import-failure-v1/diagnostic-02/results.json)
first attempts `fixture_missing_optional`, catches `ImportError`, then attempts a
registered authored native submodule. It exits 1 in 1.345769534 s (root terminal
`60f477`), with [stderr](puck-cpu-primary-import-failure-v1/diagnostic-02/caught_optional.stderr)
ending in `ModuleNotFoundError: No module named 'fixture_dep._native'`. This
reproduces primary-error masking using tiny authored Python/C-extension fixtures.
It neither reruns actual Torch nor identifies its historical first failure.

| Retained source verification | Pytest outcome |
| --- | --- |
| [Meaningful RED](puck-cpu-primary-import-failure-v1/validation/puck-cpu-primary-import-failure-v1-01/red.log) | 1 failed in 1.66 s: caught primary denial missing from the final traceback. |
| [Affected 01, shared tmp](puck-cpu-primary-import-failure-v1/validation/puck-cpu-primary-import-failure-v1-01/green.log) | 63 passed, 1 failed in 41.06 s: existing unregistered-import fallback case refused an ancestor change; new regression passed. |
| [Isolated existing case](puck-cpu-primary-import-failure-v1/validation/puck-cpu-primary-import-failure-v1-01/isolated-existing.log) | 1 passed in 1.55 s. |
| [Affected 02, private persistent tmp](puck-cpu-primary-import-failure-v1/validation/puck-cpu-primary-import-failure-v1-02/pytest.log) | 63 passed, 1 failed in 42.63 s: existing authored native positive refused an unregistered native file image; new regression passed. |
| [Root baseline setup attempt](puck-cpu-primary-import-failure-v1/root-checks/unchanged_base_persistent_positive.log) | 1 setup error in 0.07 s: explicit basetemp parent absent; not runtime evidence. |
| [Root corrected unchanged base](puck-cpu-primary-import-failure-v1/root-checks/unchanged_base_persistent_positive_02.log) | 1 failed in 1.40 s on unchanged `4036a382`: the same persistent native-image refusal. |
| [Root final-source tmpfs checks](puck-cpu-primary-import-failure-v1/root-checks/new_source_tmpfs_positive_and_regression.log) | Native positive plus new primary-denial regression: 2 passed in 2.79 s. |

All observations remain. Raw filenames containing “green” are historical labels,
not assertions that their batches passed. The root checks independently reproduce
the persistent native-positive failure on unchanged source and demonstrate the
final-source positive/regression pair on tmpfs. They do not establish a physical
filesystem root cause or general runtime qualification. Pytest durations above
are distinct from external wall times in the retained command/result JSON.
Root's corrected baseline terminal is `4c449e` (session 52806, exit 1); the targeted
tmpfs terminal is `ef5510` (session 57849, exit 0).

The [verification ledger](puck-cpu-primary-import-failure-v1/verification-ledger.json)
and [machine report](puck-cpu-primary-import-failure-v1.json) distinguish every
failure, setup error and pass. The exact [builder validation index](puck-cpu-primary-import-failure-v1/validation/puck-cpu-primary-import-failure-v1-01/validation-index.json)
is 4,739 B, SHA256 `23cb9ccf62e7d6cb22378d06fc05bf62dc9adc19304f8220c5f3bd51cb9fccb0`,
binding all 16 copied builder raw files. All seven root-check files are retained;
`summary.json` predates corrected baseline 02, whose separate JSON/log are included.
The original eight diagnostic files, final source/test bytes and exact diff are
also retained. No missing console or runtime result is reconstructed.

The [evidence index](puck-cpu-primary-import-failure-v1/evidence-index.json)
records 37 entries / 106,027 B and excludes itself. The capsule has
38 files / 117,861 B, including 34 byte-identical copied originals and zero-byte
streams. Index SHA256 is `64afa9d9dd93348a817b956e50fda2d6b601417706435e8d68462ba7163bb2bd`.
Text conversion is disabled. Only unified-diff blank context lines and literal
traceback padding in three exact raw pytest logs are exempt from trailing-blank
diagnostics; the original bytes remain unchanged. No target payload, authored compiled extension,
cache artifact or protected data is copied.

The accepted [preparation](puck-cpu-held-preparation-01.md) and consumed
[qualification failure](puck-cpu-held-qualification-01.md) remain unchanged.
This source fix preserves future diagnostic causality; it does not repair or
reinterpret the failed allocation. No actual runtime, native, operator/renderer,
model, collection, study or release authority follows. Any future actual run needs
a distinct reviewed allocation and fresh resource admission; no attempt 02
configuration or retry is created here. All seven release gates remain open.
