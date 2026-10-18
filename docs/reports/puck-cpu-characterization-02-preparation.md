# CPU characterization02 source preparation

This preparation precedes the distinct actual02 engineering allocation defined
by the [execution contract](../plans/puck-cpu-characterization-v2.md). It does not
report successful vendor imports or any held-runtime/operator/render qualification.
The actual01 failure, its consumed allocation and its64-file capsule are unchanged.

The fixed-purpose parent now selects output02 and exact metadata-v5. It authenticates
prior01's configuration and derives exactly42 input pins:12 roles,16 historical
accepted-admission sources and14 historical01 sources. Prior01's failed result,
configuration and preservation audit have fixed original hashes; validation runs
before and after observation under held inputs. Missing, changed or extra input
rows cannot reach execution. Limits, environment, versions and envelope schemas
are unchanged; the consumed01 configuration is refused by the new parent.

The new parent regressions first produced23 failures/16 passes; the explicit
required-worker-failure-field case then failed separately (1 failed/40 passed).
The final focused parent suite passed41 checks in0.39s. The root's integrated
source suite passed234 checks in6.74s (session77196, terminalc817aa, exit0):

```sh
PYTHONPATH=/home/utkarsh/.codex/worktrees/0071/brain/src \
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONDONTWRITEBYTECODE=1 \
/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
-m pytest -q tests/test_puck_cpu_characterization_parent.py \
tests/test_puck_runtime_characterization.py tests/test_puck_runtime_amendment_02.py \
tests/test_bounded_qualification.py tests/test_puck_retained_installation.py \
tests/test_puck_execution_files.py --basetemp=runs/cpu-characterization02-source-GREEN-01
```

The CLI error-boundary fixtures also require the mocked executor's JSON output,
so an earlier missing-input error cannot masquerade as proof of late-failure refusal.
A real private-namespace fixture uses four tiny authored Python packages, not the
actual numerical stack. Source checks do not establish runtime success.

The exact [configuration](../plans/puck-cpu-runtime-characterization-02.json) is
13,940B, SHA256 `4b98ff368e97351b2079ff44c75cb910d08559e5e037a6afc4887c28cd38fea8`.
Its copied canonical receipt is11,701B. The [source verification record](puck-cpu-characterization-02-preparation/source-verification.json)
and [prospective auditor](puck-cpu-characterization-02-preparation/audit-v2.py)
retain the exact checks and source. The auditor is distinct from the uninvoked01
acceptance auditor; it requires an externally observed parent exit code and
separates successful imports from verified preservation of a failure. All runtime/
native/collection/study authority stays false in either case.

Final exact-source/configuration review, freeze commit and fresh resource admission
precede actual02. After its single normal terminal result, invoke the reviewed
independent auditor with that actual outcome; retain any failure without retry.
Only accepted observation can feed the subsequent tmpfs/held qualification work.
All seven release gates remain open after source preparation alone.
