# Task3a independent spec and quality review

**Spec: FAIL. Quality: CHANGES REQUIRED. Actual acceptance: false.**

Reviewed exact implementation `be2fbf4424a4c8eb5d4386ad8c2d9514c9ab2dfd` → `e42a5f8d56ebdfc1af86bd2c70005689a93fcb1c`: only the two new 468-line auditor/test files. The later root documentation commit does not change either file. Reference contract: current reviewed plan Task3a and its frozen semantic projection, review brief, contract-fix review, and implementation report. Existing Task1/2a acceptance and deferred Task3b/6 authority remain outside this review.

## Required changes

### P1 — Apply the source event byte ceiling to the complete supplied event list

Location: `scripts/memory_family_terminal_audit_vnext.py:146–155`.

The implementation bounds only `application.event_prefix.size_bytes` and serializes only `events[:event_count]`. `_events` bounds the complete list's count, but no check bounds its complete deterministic byte representation. Events after the acquired prefix are still accepted and examined by the proof. The unchanged source-event ceiling is 7 MiB, not merely a ceiling on the acquired prefix.

Reproduced using the existing zero-condition authored fixture, appending one correctly enveloped source `diagnostic` event at boundary tick with a `message` containing `7*1024**2+1` ASCII characters. The original source prefix and all commitments remain unchanged and valid. Complete source event bytes: **7,394,102**, above **7,340,032**; prefix bytes: **53,919**. `prove` returns `row_count=0, capped_ticks=900` instead of an unscored resource refusal. Raw output is retained at `task-3a-review-probes/source-event-cap.log`.

Fix within the new auditor: enforce the 7 MiB ceiling on all supplied source-event deterministic writer bytes, preferably incrementally before source replay, while separately verifying the exact acquired-prefix commitment. Keep physical-original-byte and inventory certification deferred to3b. Add an authored regression with valid prefix plus a byte-over suffix; do not reduce the source input to a prefix silently or waive the cap.

### P2 — Require exact normal terminal event payload equality, not Python numeric equivalence

Location: `scripts/memory_family_terminal_audit_vnext.py:367–383`; inherited comparison in `scripts/memory_family_raw_audit_v4.py:570`.

The new auditor takes the actual `episode_finished` event but delegates its payload comparison to the legacy helper. That helper checks `event['outcome'] != outcome` and `event['metrics'] != metrics`, which accept booleans as integers and integer/float substitutions. It validates exact types in the manifest payload, but not in the independent event payload. This violates the frozen requirement that the manifest equal the sole verified terminal outcome with exact nested schema/types.

Reproduced from `fixture(count=4, normal=True)`: detach the terminal event's `outcome` and `metrics` dictionaries, leave the manifest intact, then set event outcome `episode=False`, `steps=float(original_steps)`, `final_distance=10`; event metrics `reward=0`, `contact_ticks=False`, `path_length=0`. Rebind only deterministic raw descriptors. Both the baseline and the malformed event are accepted with `row_count=4, capped_ticks=900`. Raw output: `task-3a-review-probes/exact-types.log`.

Fix within the new auditor: require canonical exact equality of the actual normal terminal event's outcome and metrics with the already independently validated manifest values (or explicitly validate every nested event field). Preserve the inherited full normal checks. Add detached event-only mutations so manifest aliasing cannot hide this boundary. No modification to an accepted predecessor helper is necessary.

### P2 — Validate exact source application eye booleans

Location: `scripts/memory_family_terminal_audit_vnext.py:123–129`.

The narrow inherited `_source_application` validator uses ordinary dictionary equality for `eyes`; consequently `{left:1,right:1}` passes its comparison with `{left:true,right:true}`. The new auditor strengthens several inherited fields but omits the explicit frozen `A.eyes` check. Checking restored event eyes later does not validate the supplied application's eye types.

Reproduced by wrapping the authored fixture's `_application` builder to use integer eye flags before Context/source hashes and witnesses are constructed, constructing the zero-condition fixture normally, then setting only the actual `application_restored.eyes` back to true booleans and rebinding raw descriptors. The malformed source application is correctly hash-bound, yet the proof accepts `row_count=0, capped_ticks=900`. Raw output: `task-3a-review-probes/exact-types.log`.

Fix within the new auditor: explicitly require exact canonical equality of `application['eyes']` to `{left:True,right:True}` before replay; add integer and float substitutions with valid source commitments and correct restored eyes.

## Verified strengths and scope limits

- Replay reconstructs symbolic packets from supplied case/pose/edit evidence, invokes Task1 once per sensed packet, derives complete Witness/Commit bodies and references independently, and compares ordinary decision/inspection/cue order. It does not use producer reached flags as authority. The eight non-oracle arms receive no `OracleBinding`.
- Returned state assignment is separate from raised local evidence. The two recognized natural branches are replayed CueUnavailable and an independently returned supervisor-failure state with its exact existing ValueError message. Unknown/unproved causes refuse. The normal branch retains the legacy full terminal guard; the required additional event exactness check above is local to this wrapper.
- Zero rows require no condition chunks, no policy calls, empty sequence digests, and nonempty supplied source/source-SNP identity. Positive rows retain inherited exact array shape/dtype/camera/digest checks. The safe exact NumPy scalar allowances match real RunWriter→iter_ticks outputs, while opaque array hooks and array subclasses are refused before coercion.
- At 900 motor rows, the early semantic preflight forbids another sensed tail before writer encoding. This neither bypasses the event ceiling nor establishes a fitting positive 900-row trace.
- The API honestly binds deterministic representations, not physical originals. It opens no caller-referenced file and exposes no public admission adapter, fabricated receipt, or qualification flag. Actual source/SNP/native placement, job-body correspondence, source closure/admission, original container bytes/inventory, held custody, and publication remain explicit premises/deferred work. Missing Task3b is intentional, not this review's defect.

## Evidence inspected and probes performed

Inspected the retained final raw log: **303 passed, 9 skipped, 175.17s** for the five approved files. The nine skips follow existing `tests/conftest.py` / frozen-pin collection policy and are not passed qualification checks. Inspected the initial missing-API RED and genuine decision-reach, scalar-readback, empty-snapshot/opaque-loader, and corrected-environment writer-spy RED logs. No whole-suite rerun was performed.

Inspected the final authored normal900 descriptor directly: **4,838 events, 7,012,715 bytes**, SHA256 `92d2a3f9421e25eec4b4581e7deeaf2a2336d86460235569e6bc682f71b5035f`, versus the **5,242,880-byte** condition-event cap. Its expected result is resource refusal/unscored. The separate invalid900-plus-tail trace is not normal900 evidence. Neither this sample nor this review establishes a fitting900 positive, an actual corpus measurement, or universal900 impossibility.

The two review probes used only existing small authored fixtures, safe local test imports and NumPy arrays. Both used the report's exact sanitized interpreter environment (`env -i`, PATH `/usr/bin:/bin`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=src:scripts:tests`, `LC_ALL=C.UTF-8`, all four thread limits1, `MUJOCO_GL=egl`, empty `CUDA_VISIBLE_DEVICES`, repository `.venv/bin/python -B`). Both exited0 after printing accepted/refused outcomes; an exit0 is probe execution success, not proof correctness. Logs are retained in the fresh `task-3a-review-probes/` directory. No source changes, HEAD moves, real native/model/raw/SNP/protected reads, services, dependencies, CI, cleanup, or further agents were used. Account quota telemetry was unavailable and remains unknown.

Task3a acceptance should wait for these three local fixes and focused negative verification. Full-project actual qualification/adoption/GO remain false independently of this review outcome.
