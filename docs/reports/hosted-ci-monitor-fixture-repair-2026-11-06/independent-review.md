# Authored monitor fixture repair review

What this change does: The test-generated AUTHORED parent supplies synthetic 8 GiB disk samples during its real supervisor call, extending the fixture's existing synthetic admission capacity to monitored execution. It also prints bounded decoded diagnostics for failed parent CLIs and includes the new monitor regression in hosted preflight.

## Verdict

**Ship this bounded fixture patch. No supported P1/P2 findings.** This is a review verdict for the two-file uncommitted change, not a claim that hosted CI is green or that run 42079043646's exact cause has been recovered.

Reviewed head: `8cbeff20db5b759b264107adc87f9cfb18860740`. Reviewed files: `tests/test_puck_cpu_held_parent_integration.py` and `.github/workflows/checks.yml`, against `runs/ci-monitor-fixture-repair-review.diff`. The current tracked diff contains only those two files, with 56 insertions and 2 deletions.

## Scope and correctness checks

- The additional function and call replacement exist only in the ephemeral source clone built by `project()` (`tests/test_puck_cpu_held_parent_integration.py:68-93`). Exact replacement counts and reverse transformation back to the original bytes remain enforced. Source rows are calculated from the transformed clone, preserving its actual source binding.
- The wrapper calls the unchanged `bounds.supervised` with unchanged arguments. It changes only the free-byte value supplied by the disk sampler; total/used fields still come from the original sampler. The synthetic value is explicitly labeled fixture data, and a foreign `ROOT` name is rejected before sampler mutation. The wrapper restores the exact captured sampler in `finally`, including exceptions.
- The production parent has one `bounds.supervised(command,...)` call (`scripts/qualify_puck_cpu_held_runtime.py:1022`). The transformation targets that exact one occurrence. The original 4 GiB configuration floor and RAM-only LIMITS adjustment remain enforced by the existing equality checks. No production parent, supervisor, archived auditor, protocol, or resource threshold is edited by the reviewed diff.
- The real supervisor still owns process launch, RSS, output accounting, clock, process scope, survivor checks, and cleanup (`src/palimpsest/bounded_qualification.py:393-520`). The wrapper's temporary shared `shutil` mutation is bounded to the synchronous supervisor call in the authored parent process. Current callers do not run concurrent wrapper invocations.
- The new regression (`tests/test_puck_cpu_held_parent_integration.py:347-370`) first exercises the unchanged supervisor with synthetic 3 GiB against a 4 GiB floor and asserts prelaunch rejection. It then exercises the wrapper with the same floor and verifies completion, unchanged supervisor identity, and exact sampler restoration. It also checks restoration after an actual supervisor validation exception and after the foreign-root guard rejects the call. This validates simulation/restoration behavior, not host capacity or production guard qualification.
- Failure diagnostics bound stdout decoding to 64 KiB, supervision reads to 64 KiB plus a sentinel, and stderr to a 2 KiB tail (`tests/test_puck_cpu_held_parent_integration.py:295-313`). They emit selected parent/supervision fields and handle absent or malformed leaves without replacing the original returned CLI result. The raw stdout/stderr and transport receipt writes remain unchanged. The output path derives from the current authored API/configuration, not arbitrary log discovery.
- Hosted preflight selects the new exact test node (`.github/workflows/checks.yml:90-91`). This matters because canonical `scripts/run_tests.sh` excludes integration-named files from its default four passes. The change does not alter canonical selection or bypass existing negative tests.

## Evidence inspected

- `runs/ci-8cbeff2-diagnosis.md`, including the explicit distinction between a plausible capacity mechanism and the unobserved hosted error.
- `runs/ci-8cbeff2-authored-parent-low-disk-causal-probe/summary.json` and `diagnostic.log`: the actual authored prepare parent returned FAIL with `CPU prepare worker failed; retained logs are authoritative`; supervision reported `free-space floor`, null pid/returncode, and no survivors under a synthetic 3 GiB monitor sample. Admission retained synthetic 8 GiB capacity and the configured floor remained 4 GiB. This is controlled fixture evidence.
- `runs/ci-8cbeff2-monitor-wrapper-focused.log`: retained result is **8 passed in 55.39s**. The diagnosis identifies these as the five previously failing amendment cases, the authored prepare/qualify case, admission binding guard, and new monitor restoration regression. I inspected this retained result and did not rerun the tests.
- Connected source in the authored fixture generator, its `run_cli` callers, the production parent admission/supervision path, the real supervisor, the canonical test runner, and the hosted preflight.
- Independently ran `git diff --check`: passed. Independently read current HEAD and tracked status. No source edits or additional execution probes were performed for this review.

## Limits

The exact parent error in hosted run 42079043646 remains unknown because the retained console tuple truncates it. The causal probe establishes a possible failure mechanism through the genuine parent under synthetic monitor inputs; it does not establish hosted free bytes at failure. A later hosted failure needs its decoded diagnostic assessed on its own evidence.

The new wrapper intentionally makes AUTHORED monitor capacity synthetic. Its passing result cannot support a claim that a real filesystem has 8 GiB available or that production free-space qualification passed. Physical tmpfs staging, real FD/RSS/process/output behavior, and authored fixture labels remain distinct constraints. This review assumes the existing sequential pytest/parent CLI execution model; it does not establish thread-safe concurrent use of a shared sampler override.

No full suite, hosted retry, model/native qualification, research job, protected dataset read, commit, push, or external action was performed by this reviewer. Syntax/YAML/bash checks reported by the orchestrator were not independently rerun here.
