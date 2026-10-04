# Bounded TestClient ordering investigation

4 October 2026, before runtime changes, base `e77d128`. This investigates the
combined-process startup timeout retained in the previous phase. No cause or
production fix is established; no source was patched.

All targeted checks used the pinned Python 3.11 environment, the existing private
`Path.home` fixture, unchanged `HOME`, one CPU thread and an external 55-second
bound. Every targeted process exited zero:

| Selection | Result | Pytest seconds |
|---|---|---:|
| Artwork handoff plus standalone host/origin/session guard |8 passed|1.07|
| All 19 alphabetical pre-lab modules plus host guard |176 passed, 1 skipped|33.27|
| Full 836-test collection, host guard alone |1 passed, 835 deselected|1.29|
| Pre-lab execution plus all 8 API guards |183 passed, 1 skipped|34.81|
| Full collection, retaining pre-lab execution and all API guards |183 passed, 1 skipped, 652 deselected|34.77|

The final selection preserves collection of all later modules and runs every
alphabetical predecessor plus all guards, including the first active-owner test.
The historical hang did not recur. Static inspection of global import mocks and
`sys.modules` patches found no demonstrated leak. This is bounded negative
reproduction evidence; it does not erase the earlier timeout or prove absence of
cross-module shared-state failures. No dependency upgrade or speculative fix follows.

Exact final command, from the integration checkout:

```bash
timeout 55 env PYTHONPATH=/tmp:.:src:scripts:tests PYTEST_PLUGINS=order_select_prefix OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 /home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python docs/reports/research-capability-execution/validation-invocation.py -vv -o faulthandler_timeout=15
```

`/tmp` only supplies the scoped selection plugin. The plugin and all five raw
successful logs are [retained here](memory-v2-testclient-order-evidence/).
Whole-branch regression after integration remains a separate check.
