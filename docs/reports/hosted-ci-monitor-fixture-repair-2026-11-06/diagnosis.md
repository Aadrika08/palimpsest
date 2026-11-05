# 8cbeff2 hosted failure diagnosis

Initial scope was read-only tracked source/log investigation; the orchestrator subsequently authorized the diagnostic-only authored helper change and one genuine authored low-capacity preparation probe recorded below. No production/archive edits, hosted retries, full-suite runs, model/research execution, protected dataset opens, or cleanup. Source head verified: `8cbeff2`. Raw hosted log: `runs/ci-8cbeff2-failure-42079043646.log`.

## Confirmed boundary of failure

All five failures stop at `tests/test_puck_cpu_held_amendment.py:187`: the **prepare parent CLI** returns 1 (`raw log:229-235,287-293,340-346,390-396,445-451`). Historical independent audit invocation is later, at test source lines 194-208, and is not reached. The visible JSON prefix contains `allocation_id`, `closure`, and `status: FAIL`, matching a parent outcome; it does not show `auditor_source_sha256` or an independent-audit result.

The tuple assertion renders long stdout bytes with an ellipsis. Therefore the parent result's exact `error` and `error_type` are **unknown from this log**. Do not characterize this run as a historical-auditor rejection or a measured disk failure. The diagnostic added for the old `CPU held-runtime resource admission failed` exception does not trigger for a serialized FAIL outcome (`test_puck_cpu_held_parent_integration.py:286-292`).

Hosted pass summaries are 6516 passed / 318 skipped in the first pass, 7 passed in the isolated pass, 5 failed in the persistent `runs/` pass, and 57 passed in the tmpfs pass (`raw log:163,175,468,480`). Passing the selected preflight does not establish that the later filesystem/resource state is the same.

## Independent monitor floor remains real

The current authored clone changes exactly the four free-capacity expressions **inside resource_admission** to synthetic 8 GiB values (`test_puck_cpu_held_parent_integration.py:68-82`). It preserves the original configured 4 GiB disk threshold and all resource-monitor semantics; its exact LIMITS assertion scales RAM only (`:85-89`). The bound synthetic admission values are fixture data, not host measurements.

Preparation subsequently calls the real `bounded_qualification.supervised`, passing unchanged `limits['min_free_bytes']` (`scripts/qualify_puck_cpu_held_runtime.py:1022-1027`). That supervisor independently reads `shutil.disk_usage(output_root).free` and records `failure: free-space floor` below the threshold (`src/palimpsest/bounded_qualification.py:441-450`). It observes before `Popen`, during monitoring, and after cleanup (`:458-468,496`). Admission success therefore does not guarantee monitored execution.

If supervision fails, the parent writes `supervision.json`, raises `CPU prepare worker failed; retained logs are authoritative`, catches the exception into the FAIL result's `error_type`/`error`, writes `result.json`, and prints that result with return code 1 (`qualify_puck_cpu_held_runtime.py:1028-1029,1049-1055,1080-1082`). This mechanism fits the visible hosted shape but is not proven to be the hosted error. Other caught preparation exceptions can produce the same shape.

## Retained tiny causal probe

Executed the unchanged production supervisor with a bounded Python `print("authored-monitor")` command, original 4 GiB disk floor, and synthetic low/high disk samples. No authored package project, model, simulator, native qualification, or research job was started.

| Synthetic free sample | Status | Failure | Child |
| --- | --- | --- | --- |
| 3 GiB | failed | free-space floor | no launch: pid/returncode null |
| 8 GiB | completed | none | return code 0 |

Probe exit code: 0. Summary, complete observations, and streams: `runs/ci-8cbeff2-monitor-capacity-probe/`. This proves the independent monitor path can cause a prelaunch failure despite a separate successful admission receipt. It does not recover the missing hosted error or measure hosted free bytes.

## Minimal next diagnostic, before a behavior change

In the authored-only `run_cli` helper, when a CLI returns nonzero, print a small decoded diagnostic instead of relying on a tuple of long raw stdout bytes. Include:

- phase and return code;
- parsed parent `kind`, `status`, `error_type`, `error`, and elapsed seconds;
- from the fresh clone's known output path only: `supervision.json` fields `status`, `failure`, `returncode`, `pid`, `matching_survivors`, and `sampled_peak_rss_bytes`, or an explicit absent indication;
- the configured relevant limits and retained admission values, labeled **synthetic authored capacity** for this clone;
- an optional compact **post-failure** host sample of project-root free bytes, `/tmp` free bytes, MemAvailable, and NOFILE. These are later samples, not measurements of the failure instant.

Read only the bounded, known result/supervision leaves below this newly created `authored-project`. Handle missing/non-JSON stdout without replacing the original failure. Do not print complete inputs, source capsules, environment, or megabytes of output. Printing these selected decoded fields makes pytest's captured stdout expose the error without repr truncation. Alternatively, a short explicit `AssertionError` string containing the selected fields can replace the tuple. Apply the same pattern to the later audit CLI assertion if that boundary is reached in a future failure, keeping parent and auditor errors distinct.

The script removes its test basetemps after all four passes (`scripts/run_tests.sh:51-56`), so these retained JSON files are not recoverable from the present Actions console excerpt. Future failure artifacts should be preserved before that cleanup if more than the compact printed fields is needed. No cleanup behavior was changed here.

## Cheap local discrimination before another hosted run

1. First expose the selected parent/supervision diagnostics locally. Keep original thresholds and archived auditor bytes intact.
2. For an end-to-end authored-clone reproduction, place only the new authored project's output filesystem on a private tmpfs with total capacity below 4 GiB, while keeping its `/tmp` staging writable/executable and independently sized. Run one existing authored prepare case, preserving diagnostic/raw outputs outside that private mount before teardown. Its synthetic 8 GiB admission should still pass, while the real output monitor should report `free-space floor`. This is a deterministic capacity experiment; avoid filling the user's disk or rerunning thousands of tests.
3. Compare with the same one-case invocation on a filesystem with sufficient real free capacity. Both experiments should use the shared interpreter alias and bounded authored modules. A matched FAIL result/error plus supervision reason would support the resource mechanism locally; it would still not prove the unobserved hosted cause.
4. If the later hosted diagnostic instead shows a different error, investigate that exact error. Ordinary and isolated passes run in separate fresh pytest processes; in-process monkeypatch state from those passes cannot itself persist into the third process. Shared filesystem/OS resources can persist. The full third-pass collection imports all non-integration modules before marker selection, unlike the small selected preflight, so collection-time state is another possibility until the error is known (`scripts/run_tests.sh:36-41,50-54`). Do not assume it without evidence.

If the resource hypothesis is confirmed, a possible next **test-only** design is an explicitly AUTHORED, source-bound cloned-parent capacity provider scoped to all parent disk samples, including supervision, instead of admission-only expressions. That is a future behavior decision, not implemented or validated here. Preserve original configuration floors and archived auditor bytes; keep real FD/tmpfs/output/ownership constraints; label synthetic capacity receipts as fixture data; make no claim that such a test validates the production free-space guard.

The archive auditor still validates exact authored configuration floors (`docs/reports/puck-cpu-held-preparation-01/controls/scripts/audit_puck_cpu_held_runtime.py:187-188,191-194`) and retained admission receipt fields against those floors (`:483-484`). It does not independently sample disk or MemAvailable. None of these predicates caused the currently visible failure because execution stopped before that auditor was invoked.

## Authorized diagnostic implementation and genuine parent probe

Pending tracked change is confined to `tests/test_puck_cpu_held_parent_integration.py::run_cli`: on nonzero return, print selected decoded parent and supervision fields, reading at most 64 KiB plus a sentinel from the known supervision leaf, with an optional 2 KiB stderr tail. Missing/invalid records are reported without replacing the original CLI outcome. Exact stdout/stderr and transport receipts retain their existing bytes and paths. No all-capacity shim or resource-threshold behavior change was added to the fixture helper.

The first generated low-capacity probe had an inline-comment syntax error and never reached monitored preparation. Its stderr, source clone, configuration, and diagnostic remain at `runs/ci-8cbeff2-authored-parent-low-disk-probe/`. This was a software harness failure, not evidence about resource behavior. The orchestrator authorized a fresh corrected probe with pre-compilation of generated source; nothing from the first attempt was overwritten or deleted.

The corrected genuine authored preparation probe is retained at `runs/ci-8cbeff2-authored-parent-low-disk-causal-probe/`. It ran under bwrap with a private 4 GiB `/tmp`, preserved the shared interpreter alias, kept the parent admission's authored 8 GiB samples, and retained the original configured 4 GiB disk floor. Only its freshly created bound source clone replaced the supervisor's one disk-capacity expression with a synthetic 3 GiB value. Full source rows were rehashed into the fresh authored configuration before CLI execution. The generated source was compiled before launch.

Observed causal chain, verified by assertions; probe exit code 0:

- admission receipt: disk and tmpfs capacity both 8589934592 synthetic bytes;
- actual parent CLI: return code 1, status FAIL, error_type ValueError, error `CPU prepare worker failed; retained logs are authoritative`;
- retained supervision: status failed, failure `free-space floor`, pid and returncode null, matching survivors empty;
- staged worker was not launched; the stage directory was empty;
- original production parent, production supervisor source, and archived independent auditor SHA-256 values were unchanged before/after the probe, with those hashes retained in `summary.json`;
- `diagnostic.log` exposes the complete selected parent error and supervision failure without the old bytes-tuple ellipsis.

This establishes the hypothesized mechanism through the real parent and its real supervision call under controlled authored inputs. **It still does not reveal the exact error in run 42079043646 or prove that hosted disk capacity crossed 4 GiB.** The authored monitor sample is synthetic. The new diagnostic must expose the hosted result before that causal attribution can be confirmed.

## Subsequently authorized bounded authored monitor simulation

The orchestrator authorized a test-only capacity simulation for the authored parent clone, retaining the original 4 GiB floor. The pending tracked patch remains confined to `tests/test_puck_cpu_held_parent_integration.py`:

- The exact reversible clone-source transformation adds `_authored_supervised`, guarded by `ROOT.name == 'authored-project'`, and changes the one cloned-parent supervision call to use it.
- That wrapper temporarily supplies synthetic 8 GiB free bytes to the unchanged `bounds.supervised`, restoring the exact original sampler in `finally`. Admission's existing four synthetic samples and exact RAM-only limit adjustment remain unchanged. The wrapper does not permanently patch the shared shutil module.
- A new regression runs the unchanged real supervisor directly with a synthetic 3 GiB sample and confirms `free-space floor` rejection before launch. Calling it through the authored wrapper then completes under the original 4 GiB threshold. The test verifies sampler identity restoration after success, an actual supervisor exception, and the foreign-root guard rejection. It also verifies that the supervisor function itself is unchanged.
- Production scripts, production supervisor source, protocol, archived auditor bytes, configured guard limits, RSS/FD/tmpfs checks, output accounting, and ownership behavior were not edited. Fresh authored source bindings include the transformed parent.

One focused pytest invocation under bwrap/private 4 GiB `/tmp` passed **8 tests in 55.39 seconds**: all five previously failing amendment cases, the existing authored prepare/four-fake-import helper case, the admission/source-binding guard, and the new monitor/restoration regression. Complete pytest output and fresh raw fixtures: `runs/ci-8cbeff2-monitor-wrapper-focused.log` and `runs/ci-8cbeff2-monitor-wrapper-focused-raw/`. No failing attempts were overwritten or removed. `git diff --check` and protected-source/archive/protocol diff checks passed.

This validates authored fixture behavior only, not production resource-guard qualification or the exact hosted root cause. No full suite, hosted retry, push, or commit was performed after the wrapper change; the patch is awaiting the orchestrator's fresh review. Because the new regression lives in an integration-named test file, explicitly include its node in hosted preflight if it must run before the canonical full suite.
