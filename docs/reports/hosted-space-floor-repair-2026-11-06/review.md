# Independent isolated-first CI repair review

**Verdict: APPROVED.** The two-file change is a bounded scheduling repair consistent with the observed hosted failure. No corrective source change is required by this review. Approval is for this patch, not a claim that the next full hosted run passes.

I inspected the actual diff of `scripts/run_tests.sh` and `docs/testing.md`, the full runner, existing runner-test references, the retained focused test logs, and the relevant retained hosted failure excerpt. I ran no tests, CI, services, probes, OS queries, or actual model/research payload reads; changed no source/docs; and did not commit/push. This review is the sole authored artifact.

The only runtime-script behavior change moves the existing `process_isolated` invocation ahead of the ordinary invocation (`scripts/run_tests.sh:50–54`). All four marker selectors, explicit file list, separate clean Python executions, basetemp paths, selected/integration branches, continuation after failed passes, nonzero aggregate status and final cleanup remain present and unchanged. The change does not alter production free-space guards, child exit-code expectations, assertions, workflows, or capacity limits. Documentation now accurately reflects the four pass order and separate isolated basetemp.

The diagnostic hosted log at `runs/hosted-supervision-diagnostic-20261106/hosted-1743647-42136045205.log` in the full worktree explicitly reports `failure='free-space floor'`, `pid=None`, and `returncode=None` where the fixture expected 7 (`:1519` and surrounding lines). This supports a pre-child disk-admission failure, not the intended child-failure path. Running isolated fixtures before retained ordinary-pass temporary output accumulates addresses that ordering pressure without bypassing the floor. It does not establish that initial or later disk capacity is sufficient on every runner.

Retained verification inspected, not rerun by this reviewer:

- `isolated.log`: **7 passed, 138 deselected in 0.52s**.
- `runner.log`: **12 passed in 0.60s** with the modified runner.
- The implementation report records `bash -n` and diff whitespace checks returning 0. These are reported checks, not independently rerun here.

The old 4a59e7a failure's exact cause remains unknown. Full-suite/hosted success remains unverified after this patch. Existing final cleanup is unchanged, and no extra cleanup, skip, fake disk result, lowered guard or broader accounting/scientific authority is introduced. A fresh complete hosted result is the remaining integration evidence after the root's normal commit/push decision.
