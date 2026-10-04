# Software verification and its limits

Verification ran on the integration checkout on 4 October 2026 with pinned
Python 3.11.15, the existing locked environment, and one CPU thread. The
[machine receipt](validation.json) records actual commands, setup, results and
earlier failures. These are software checks, not task or hardware qualification.

| Check | Passed | Skipped | Observed pytest time |
|---|---:|---:|---:|
| Focused puck/model/balanced checks, explicit CPU Torch |33|0|17.30s|
| Focused navigation checks, explicit CPU Torch |14|0|2.42s|
| Default suite excluding the three API modules |786|21|84.95s|
| `test_lab.py`, fresh process |17|2|28.52s|
| `test_male_lab.py`, fresh process |7|0|.98s|
| `test_memory_branch.py`, fresh process |2|1|.83s|

The four default-regression partitions account for all **836 collected tests**:
**812 passed, 24 skipped**. Their exit statuses are zero. Focused checks cover
the changed Torch paths that are opt-in in the default suite; they are separate
checks, not extra distinct tests to add to the default count. Optional renderer,
native and other opt-in paths are not universally verified.

The whole suite **did not pass in one process**. It stalled in
`tests/test_lab.py::ApiGuards.setUp`, entering `TestClient`. The last bounded
combined attempt timed out at 180 seconds. Its diagnostic showed the main thread
waiting for a concurrent future, the portal event loop in `selector.select`, and
the lab monitor waiting. This paragraph summarizes the observed tool output;
it is not a preserved raw combined-process traceback.

The same host/origin/session guard passed standalone on both the unchanged main
checkout (.84s) and research checkout (.72s), and all three API modules then
passed in fresh processes. No lab application or existing lab-test source was
changed. The observations establish a difference with test ordering/process
state, but do not establish the cause or rule out shared-state bugs. The
combined-process startup hang remains a separate debugging follow-up; partitioning
is an explicit verification limit, not a production fix.

Two earlier environment failures are also retained in the receipt: the isolated
checkout initially lacked its pinned upstream mapping CSV, and the real user's
cache lock was read-only. The exact upstream revision was populated from an
existing local checkout. [The validation harness](validation-invocation.py)
patches only `Path.home` to an owned temporary cache fixture. It leaves `HOME`,
production sources and validation predicates unchanged and has a main guard for
multiprocessing spawn. Existing unit/physics fixtures run under their own test
contracts; no new scientific task rollout or data collection is claimed.

For reproduction from the integration checkout, use the locked interpreter and
the published harness instead of the temporary harness path in the historical
commands. Ensure the unchanged pinned upstream checkout is populated. Run the
non-API partition and each API module in separate interpreter invocations:

```bash
PYTHONPATH=.:src:scripts:tests OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python docs/reports/research-capability-execution/validation-invocation.py -q --ignore=tests/test_lab.py --ignore=tests/test_male_lab.py --ignore=tests/test_memory_branch.py
PYTHONPATH=.:src:scripts:tests OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python docs/reports/research-capability-execution/validation-invocation.py -q tests/test_lab.py
PYTHONPATH=.:src:scripts:tests OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python docs/reports/research-capability-execution/validation-invocation.py -q tests/test_male_lab.py
PYTHONPATH=.:src:scripts:tests OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python docs/reports/research-capability-execution/validation-invocation.py -q tests/test_memory_branch.py
```

Raw successful output is retained in [non-API](regression-non-api.log),
[lab](regression-lab.log), [MaleCNS lab](regression-male-lab.log), and
[memory branch](regression-memory-branch.log) logs. Standalone baseline/research
logs and the serial module invocation are adjacent. Receipt hashes are listed in
[the phase inventory](../research-capability-phase.json).
