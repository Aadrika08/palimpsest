# Memory-v2 integrated software verification

Implementation `253f7f6`; pinned Python 3.11.15/Torch 2.9.0/NumPy 2.2.5 environment.
The complete default checkout suite passed: **878 passed, 24 skipped** in 116.79 s.
No targeted test partition or exclusions were used. Asset-backed opt-in skips do
not qualify the new native scene. [Raw output](regression.log).

```sh
timeout --signal=TERM --kill-after=5 300s env \
  PYTHONPATH=.:src:scripts OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  /home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python \
  docs/reports/research-capability-execution/validation-invocation.py \
  -q -o faulthandler_timeout=45
```

The published validation helper uses a private temporary `Path.home` fixture for
software cache tests; HOME and production validation are unchanged. Scientific
execution uses the actual user writer lease, without this fixture.

Independent static integration review and nine pure checks found no important
remaining issue after correcting snapshot preallocation admission, pilot profile
metadata, commitment bindings, destination receipt IDs and pre-event failures.
Runtime-focused verification also passed 177 tests with 6 opt-in skips. A broader
agent checkout run failed 18 tests and raised 14 errors because its upstream files
were absent; the populated integrated checkout above resolves those failures.

One retained real CPU FLYNN SNP was read-only checked for structural compatibility
with explicitly synthetic application/profile substitutions. Its SHA256 remained
`55196322961a10669fabefad77975d6a269d53ccbab3040ad237b9bd1dd03b1d`.
The hybrid was never executed or published as a native snapshot. This is a schema
compatibility check only. Actual native restore remains a separate prerequisite.

The historical TestClient timeout was not reproduced in the
[bounded ordering investigation](../memory-v2-testclient-order-audit.md) or the
complete integrated suite. No causal production fix is claimed.
