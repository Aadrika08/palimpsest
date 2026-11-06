# Source failure-preservation prerequisite

Implemented the independently adopted preservation compatibility extension only, based on HEAD `b7a967026d1261b20450024e271f7cfc790dfd17`. HEAD was unchanged after verification. No commits.

## Changed APIs and mechanism

- `snapshots.save_snapshot(..., preserve_failed=False)` rejects anything whose exact type is not `bool`, before NumPy import, serialization, path output or budget calls. True retains exclusively created target bytes on write/flush/fsync failure. Existing `xb` creation still refuses an existing target, without unlinking or truncating it. The original container encoder and return value are unchanged.
- `RunWriter(..., preserve_failed=False)` performs the same early exact-bool validation. Its flag reaches `_atomic_manifest`, `_publish_chunk`, `_BackgroundWrites` and the existing synchronous `_flush` finally block. True skips failed-pending unlink; successful replace consumes the pending name normally. No publication block, serializer or writer was copied. Default cleanup and ordinary running-manifest replacement stay as before.
- `Engine.open` conditionally passes `preserve_failed=True` only in canonical-prepared-vnext-v1 mode. The default branch omits the keyword; a real default Engine invocation through a legacy-signature writer boundary verifies this.
- Source docstrings state that retained failed bytes remain chargeable and separate atomic-space reservation belongs to source admission, which this change does not implement.

Exclusive pending creation prevents reusing/truncating an existing pending leaf. Failure leaves the writer broken, and existing close/background error handling still drains/stops the thread and refuses continuation. Existing recorder quotas and StorageBudget checks are unchanged; retained physical leaves remain visible to recount. There is no cap bypass, retry, failed-byte normalization, raw/chunk/SNP deletion in preservation mode, export or repair path.

## Test evidence

Every test invocation used this environment and named interpreter, from the worktree root:

```
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest <named files> --basetemp=<fresh retained path> -q
```

| Run | Exact named files | Result | Retained log / basetemp |
| --- | --- | --- | --- |
| Initial RED | `tests/test_source_failure_preservation_vnext.py` | 43 failed, 20 passed, 0.68s | `source-preservation-red-initial.log`; `/var/tmp/palimpsest-source-preservation-red-jxQwjc9T/pytest` |
| Corrected RED, before source edits | same | 42 failed, 21 passed, 0.70s | `source-preservation-red.log`; `/var/tmp/palimpsest-source-preservation-red-LD8wwox3/pytest` |
| GREEN | same | 63 passed, 0.65s | `source-preservation-green.log`; `/var/tmp/palimpsest-source-preservation-green-sqx13vIz/pytest` |
| Covering, once after GREEN | `tests/test_memory_source_bootstrap_vnext.py tests/test_records.py tests/test_records_background.py` | 119 passed, 3.37s | `source-preservation-covering.log`; `/var/tmp/palimpsest-source-preservation-covering-iD808NnF/pytest` |

Logs are in this report's SDD directory. The initial RED included one incorrectly located test monkeypatch: Engine imports RunWriter inside `open`, so the legacy-boundary test must patch `records.RunWriter`, not an absent Engine module attribute. Corrected that test before source edits; both RED logs and fixture roots remain retained. Corrected RED failures were missing new keyword acceptance/validation and canonical Engine's old pending deletion. Default-path assertions passed.

Dedicated coverage includes exact-bool refusal before serialization/output, exact successful default/True SNP bytes with controlled ZIP timestamps, real container decoding, real default/True recorder bytes, sync/background drain, snapshot partial write/flush/fsync failures, manifest/chunk partial write/flush/fsync/replace failures across sync/background modes, existing target/pending refusal, initial manifest failure, closed/broken no-retry behavior, absence of terminal success after failure, unchanged quota refusal, and real storage recount charging retained snapshot bytes. Canonical Engine uses the existing imported `route` bootstrap fixture, real held provenance/resolver/world guards/constructor/RunWriter and only that fixture's controlled native/ML boundaries. No bootstrap fixture or guarded success behavior was duplicated or patched.

Inspected both safe recorder test modules before running. Their subprocess test imports only authored NumPy/recorder work and kills that authored writer; the snapshot-registration case uses authored `SmallEnv` and patched capture/saver, with no native/model allocation. Inspected the imported SmallEnv definition. This authorized covering evidence is ordinary software-unit runtime, not experiment cost or CPU-provider qualification. The two existing recorder unittest modules retain their existing TemporaryDirectory lifecycle; new dedicated pytest fixtures and logs were not cleaned up.

## Source diff check and self-review

`git diff --check` passed, with result retained in `source-preservation-diff-check.log`. Source diff is 31 insertions and 13 deletions across exactly the three owned source files; the only new test is the brief's `tests/test_source_failure_preservation_vnext.py`. Documentation/logs are the requested evidence in this SDD directory. No other code edits, native/ML execution, protected payload/namespace reads or hashes, actual research/probe/service launch, network, dependency/CI change, cleanup or agent delegation was performed.

Reviewed all four original cleanup paths and their call sites. The private helpers receive the public writer's already validated bool; exact-bool validation is at the two requested public APIs. Existing `xb` creation protects preexisting pending bytes in preservation mode, no retry path was introduced, and normal replacement still consumes its pending name. Errors retain their real disk exception/cause and no terminal-completed manifest appears after failure. Tests preserve actual authored disk bytes and drive real background error/drain/close behavior.

A call-site name search also found an unrelated `_atomic_manifest` in `puck_on_policy.py` and callers in `puck_collection_close.py`; they are outside this source-prerequisite ownership, were not inspected/modified/run, and are not claimed covered or available for source use. No additional pending/export helper is used by the changed snapshot/recorder path. No wider compatibility edit was needed.

## Limitations and remaining ownership

This is a failure-retention primitive, not admission, capacity reservation, source production, numerical qualification, accepted Q/L/F/R, or a complete source vertical slice. Atomic-space admission and the source owner that will call `save_snapshot(..., preserve_failed=True)` remain unimplemented. The current change does not enable background writes for source callers; future source ownership must remain synchronous and reject enabling background writes. Existing defaults intentionally retain their legacy cleanup behavior. Failure injection and authored fixtures do not establish real filesystem durability, native/runtime/full-model/physical results, actual CPU accounting, or actual experiment readiness. Independent source review remains with root; no reviewer or broader suite was launched here.

## Round 1 test-only correction

Root accepted the review's P2 finding that the original active default compatibility test unnecessarily patched asset verification/preparation to success. The historical report body, logs and fixtures above are preserved. The active test now raises a dedicated sentinel at an exact legacy-signature writer entry, with all fixture acquisition denials intact. An accidental new keyword would raise TypeError instead of that sentinel. Its active result proves default writer handoff/keyword omission and pre-acquisition refusal only; it no longer exercises full legacy startup, writer completion or environment closure. The historical full-path run did not prove real asset verification/preparation, admission or qualification. See `source-preservation-fix1-report.md` for the correction, fresh verification and retained evidence. Production source was unchanged.
