# Task3a conditional pure terminal proof

Implemented only `prove_terminal_vnext` in the two assigned new files. Full Task3 is incomplete: public audit/validate adapters are deliberately absent until Task3b after the authentic Task6 holder. There is no always-raising public stub or receipt-shaped qualification shortcut. Baseline was `be2fbf4424a4c8eb5d4386ad8c2d9514c9ab2dfd`; root-owned plan/contract reports remain outside this commit.

Scoped implementation commit: `e42a5f8` (`feat: add conditional pure terminal evidence proof`), exactly the assigned two new files. Postcommit index is empty; unrelated root-owned changes remain unstaged. Retained evidence paths are listed in `task-3-evidence/inventory.txt`.

The fixed pure raw input is exactly `{manifest,events,rows,worker_report,job,descriptors}`. Job is a matching descriptor premise, not an invented partial owner job. Deterministic manifest/events bytes use the actual spaced RunWriter encoder/newline; Context/report use canonical bytes. The required frozen manifest/report projection, three recording counters, exact row fields/dtypes, exhaustive policy digests, geometry, edit events, complete event references, once-per-sensed-packet Task1 replay, Witness/Commit chain and ordinary event order are checked. Raised local state is never treated as assigned state. Known CueUnavailable and the exact replayed returned-supervisor failure are distinguished; unknown/infrastructure/malformed normal evidence refuses without a scientific score. Zero conditions retain a nonempty supplied source and nonempty source-SNP descriptor identity. No-event pending remains distinct from null selected-empty.

Self-review retained the original source/normal obligations, event/metadata/row/chunk ceilings and exact terminal stop. An early bounded semantic check rejects a sensor tail after the900th motor row before writer encoding. Exact safe NumPy scalars from real `RunWriter -> iter_ticks` readback are accepted alongside plain arrays, without normalization or digest changes; opaque `__array__` loaders and subclasses are refused before invocation. The readback test covers both authored source and condition rows.

## Verification

Final approved five-file run: **303 passed, 9 skipped, exit0,175.17s**. The nine skips are the existing frozen-pin collection policy; they are not passed qualification checks. No whole canonical/native suite was run.

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest tests/test_memory_family_terminal_audit_vnext.py tests/test_memory_family_raw_audit_v4.py tests/test_memory_family_oracle_v3.py tests/test_memory_transition_vnext.py tests/test_memory_engine_transition_vnext.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-implementation/task-3-evidence/final-green-tmp > .superpowers/sdd/memory-terminal-vnext-implementation/task-3-evidence/final-green.log 2>&1
```

Every earlier pytest invocation used that same environment/interpreter with the new test file only, a distinct retained basetemp and corresponding log, except the explicitly non-authoritative `cap-red-3` environment typo below. Targeted `-k` runs are identified here. All files/partials/logs are retained.

| Log stem | Result and interpretation |
| --- | --- |
| red | exit1;63 failed0.23s: intended missing Task3a API RED before production code. |
| attempt-1 | exit1;1 failure: an overrestrictive generic seed bound, fixed within the frozen projection. |
| attempt-2 | exit1;1 failure: authored zero-sum integer instead of required finite float, fixture corrected to original metric type. |
| attempt-3 | exit0;63 passed17.02s. |
| decision-red (`-k local_decision_cut`) | exit1;1 failed0.61s: genuine missing local decision reach on raised terminal; fixed without assignment claim. |
| attempt-4 | exit0;108 passed33.98s. |
| cap-red (`-k extra_sensor_tail`) | exit1;chunk-count inconsistency, **not** intended semantic RED. |
| cap-red-2 (`-k extra_sensor_tail`) | exit1;invalid900-tail descriptor size refusal before semantic check, **not** valid900 normal evidence. |
| cap-red-3 (`-k extra_sensor_tail`) | exit1;writer spy failed; **non-authoritative environment deviation**: OPENBLAS_THREADS was mistakenly supplied instead of OPENBLAS_NUM_THREADS. Retained and rerun correctly before code fix. |
| cap-red-4 (`-k extra_sensor_tail`) | exit1;1 failed11.80s: genuine missing early semantic guard, demonstrated writer encoding invoked before required postterminal refusal. Exact approved environment. |
| input-red (`-k 'nonempty_source_snapshot or opaque_array_loader'`) | exit1;2 failed0.67s: genuine empty source-SNP descriptor admission and opaque array hook invocation; both fixed. |
| attempt-5 | exit0;112 passed55.99s. |
| decoder-red (`-k actual_authored_runwriter`) | exit1;1 failed0.48s: genuine rejection of exact scalar types returned by real authored RunWriter/iter_ticks. |
| decoder-green (`-k 'actual_authored_runwriter or opaque_array_loader'`) | exit0;2 passed0.68s. |
| final-green | exit0;303 passed,9 skipped175.17s; exact five-file command above, after source/condition scalar readback coverage. |

The ordinary attempt commands used `-q -x` for bounded first-failure feedback; RED/targeted/final commands used `-q`. No occupied basetemp was reused, no logs/partials were deleted, and no source pin/protocol was rebound.

## Capacity finding and limits

The final run retained `task-3-evidence/final-green-tmp/test_oversized_nine_hundred_ro0/authored-normal-900-descriptor.json`: authored no-U/no-event900-motor-row **row-backed normal time_limit** input,4838 events, **7,012,715 bytes**, SHA256 `92d2a3f9421e25eec4b4581e7deeaf2a2336d86460235569e6bc682f71b5035f`. Existing condition event cap is **5,242,880 bytes**. The pure proof correctly resource-refuses this sample, unscored. This is authored software data, not an actual source/corpus/qualification measurement. A fitting900-row positive trace is **not established**; this one sample does not prove all900-row traces impossible. The valid four-row normal-terminal branch is tested across all nine conditions. No cap, producer format, IDs, or required per-row inspection/event obligations were changed.

Separately, `cap-red-2.log` shows **7,021,002 bytes**, SHA256 `882a9795979c42df1825c40b316d8ccc1c9d85fb45d975dd47f1a3dbe1788c95`, for an **invalid900-row-plus-postcap-sensor-tail** input. That trace was initially refused by the descriptor cap and is not evidence of a validated normal900-row trace. The later exact-environment semantic RED and guard address its forbidden extra advance directly.

The proof is conditional on supplied application/events/nonempty rows and their checked hashes/prefix/replay. It does not authenticate held SNP origin, native placement, actual job-body/Context binding, successor source closure/admission, original NPZ bytes/inventory, physical raw-byte census, held-path lifetime or exclusive publication. Known decoded array bytes are only a necessary lower-bound refusal, not container accounting. Canonical-hyphen versus predecessor UUID-hex compatibility remains a Task3b/6 design gate; no bytes are silently relabeled. Task3b must independently check held actual bytes and source/job authority. Full Task3, actual qualification, namespace/adoption, resource admission and GO remain closed. Source03/provider-exemption decisions are unchanged.

No actual native/model/source/SNP/catalog/protected payload, owner/research/service, held-out draw, dependency installation, CI, push, cleanup or pruning occurred. Account quota telemetry was unavailable in this child and is unknown; no safety percentage was invented. Explicit edits outside the two owned source files were ignored authored test evidence and this report; pytest may maintain its ordinary local cache. Root owns the plan and contract-review report changes.

## Round1 review fixes

Read `task-3a-review.md` and both retained `task-3a-review-probes/` logs first. The prior303-pass result did not establish the three missed boundaries. Review found a whole supplied source-event stream accepted above7MiB, normal terminal event-only numeric aliases accepted by inherited Python equality, and correctly hash-bound integer source-eye flags accepted by inherited Python equality. All fixes remain in the same two owned files, without editing accepted predecessor helpers, schemas, caps, pins or public adapters.

- **F1:** Incrementally encode and count the complete supplied source event list under **7,340,032 bytes**, before source row/replay work. Separately compute/verify the acquired prefix bytes/digest, and pass the entire unchanged event list to source replay. This checks deterministic supplied representations only, not physical originals or custody. The regression passes the exact ceiling and rejects a valid prefix plus exact one-byte-over suffix before replay.
- **F2:** Retain all inherited normal terminal checks, then require canonical exact equality of the independent actual `episode_finished` outcome and metrics to the validated manifest. Six detached event-only integer/float/boolean aliases now refuse while the manifest remains valid and unchanged.
- **F3:** Require canonical exact source application eyes `{left:true,right:true}` before source replay. Integer and float eye substitutions constructed before all source/Context hashes and witnesses, with correct restored boolean eyes, now refuse.

Round1 baseline was root-held `b5f667b8e3bf03e2d82d9e7d8f085fb74549ff55`. Scoped fix commit is `6cc0e8e` (`fix: enforce exact terminal proof source bounds and types`): exactly the two owned files,75 insertions/5 deletions. Independent F1–F3 rereview remains root's next gate; no actual acceptance is asserted.

| Fresh retained round1 log | Result |
| --- | --- |
| `task-3-evidence/round1/red.log` | exit1; **9 failed,1 passed,113 deselected,3.18s**. Genuine intended REDs: over-ceiling stream reached forbidden source replay; all six detached terminal aliases and both hash-bound nonboolean source-eye variants were accepted. Exact-ceiling source stream passed. |
| `task-3-evidence/round1/focused-green.log` | exit0; **10 passed,113 deselected,2.81s**. |
| `task-3-evidence/round1/final-green.log` | exit0; **313 passed,9 skipped,169.56s**. The9 unchanged frozen-pin skips remain explicit and are not qualification passes. SHA256 `9d4b1e4c65c4c6fa330db3007e457ef5177d659bea0de9509f30377fd88310d8`. |

The exact final command, run once after settling the fixes and focused green:

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest tests/test_memory_family_terminal_audit_vnext.py tests/test_memory_family_raw_audit_v4.py tests/test_memory_family_oracle_v3.py tests/test_memory_transition_vnext.py tests/test_memory_engine_transition_vnext.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-implementation/task-3-evidence/round1/final-green-tmp > .superpowers/sdd/memory-terminal-vnext-implementation/task-3-evidence/round1/final-green.log 2>&1
```

RED/focused commands use the identical sanitized environment/interpreter and only the Task3 test file with `-q -k round1`, distinct `round1/red-tmp` / `round1/focused-green-tmp`, and corresponding retained logs. Every basetemp was fresh. `round1/inventory.txt` lists retained paths. Self-review and scoped `git diff --check` passed; no additional tests or scopes were launched.

The round1 final normal900 authored artifact is unchanged: **4,838 events,7,012,715 bytes**, SHA256 `92d2a3f9421e25eec4b4581e7deeaf2a2336d86460235569e6bc682f71b5035f`, versus5,242,880-byte cap; expected resource refusal/unscored. It is at `round1/final-green-tmp/test_oversized_nine_hundred_ro0/authored-normal-900-descriptor.json`. Fitting900-row positive evidence remains **not established**. This is no actual corpus/qualification measurement, and the separate invalid900-plus-tail result remains classified separately. Task3b, authentic source/job/SNP/physical custody/publication, whole-project adoption and GO remain closed; there was no format/cap expansion or actual owner/research/native/model/service/protected-payload activity.
