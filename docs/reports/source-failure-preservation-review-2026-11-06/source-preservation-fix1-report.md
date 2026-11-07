# Preservation round 1 correction

Addressed the sole P2 test/spec finding from `source-preservation-review.md`. Only `tests/test_source_failure_preservation_vnext.py` changed in this round; production source is unchanged and no commit was made. HEAD remains `b7a967026d1261b20450024e271f7cfc790dfd17`.

The default Engine test now supplies an exact old-signature writer callable that immediately raises a local dedicated `LegacyWriterEntry` sentinel. It requires that exception from the real default `Engine.open` route. A regression passing `preserve_failed` would raise TypeError before entering the callable, failing the test. The fixture's existing denied asset verification/preparation/acquisition functions remain intact. The test also requires no allocation trace, no constructed environments and no recording output. Removed the now-unused `assets` import.

The active test proves writer handoff, default keyword omission and pre-acquisition refusal. It does not claim full legacy startup/completion/close. The canonical preservation test continues to use the real readonly resolver, held/world guards, constructor and recorder unchanged. Historical full-path test results remain retained controlled-boundary evidence, never proof of real asset verification/preparation, source admission or qualification.

Both commands ran from the worktree root with:

```
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest <node-or-file> --basetemp=<fresh retained root>/pytest -q
```

| Scope | Result | Retained log | Retained basetemp |
| --- | --- | --- | --- |
| `tests/test_source_failure_preservation_vnext.py::test_default_engine_omits_new_keyword_for_legacy_writer_boundary` | 1 passed in 0.19s | `source-preservation-fix1-node.log` | `/var/tmp/palimpsest-source-preservation-fix1-node-3knITuHG/pytest` |
| `tests/test_source_failure_preservation_vnext.py` once after the changed node | 63 passed in 0.64s | `source-preservation-fix1-file.log` | `/var/tmp/palimpsest-source-preservation-fix1-file-Tl7YQQKv/pytest` |

Logs are in this SDD directory. `git diff --check` passed and is recorded in `source-preservation-fix1-diff-check.log`. The approved three-source-file diff remains 31 insertions/13 deletions. No historical report body, log or fixture was overwritten; the original implementation report received only an appended correction. No unchanged 119-test covering rerun, broader suite, protected payload/namespace access, runtime/native/model allocation, actual research/probe, agent, network, dependency/CI change, cleanup or source edit was performed. Independent scoped review remains with root. Full source vertical implementation, admission/reservation and actual qualification remain absent.
