# Isolated-first CI repair verification

Repair worktree: `/home/utkarsh/Work/shraddha/palimpsest/.worktrees/ci-isolated-first-20261106`
Base: `1743647922e739efd819bc3d67ffc1856b9a9d9f`, branch `research/source-cpu-compat-v1`.
Only tracked edits: `scripts/run_tests.sh` and `docs/testing.md`.

The default four-pass path now runs process-isolated fixtures before ordinary
fixtures. The remaining passes, marker selectors, separate clean Python
processes, basetemp names, selected/integration modes, failure continuation and
final cleanup are unchanged. Documentation states the order and why the fixed
2 GiB production free-space floor must run before ordinary temporary files
accumulate; all temporary fixtures still remain until normal final cleanup.

Root supplied the diagnostic hosted run 42136045205 at 1743647: its failed child
fixture reported `failure='free-space floor'`, `pid=None`. The earlier 4a59e7a
hosted failure's exact reason remains unknown. No guard, child return-code
expectation, test assertion, workflow or capacity limit was changed.

Fresh local checks:

- `bash -n scripts/run_tests.sh`: exit 0 (`bash-n.log`, `bash-n.exit-code`).
- `git diff --check`: exit 0 (`diff-check.log`, `diff-check.exit-code`).
- Full worktree src/scripts/tests compared against 1743647 with
  `git diff --exit-code`: exit 0 (`full-source-compatibility.log`, companion
  exit-code file). Full worktree commit was caf919b18817c44304a0bc4fe19ffefd3284e7e1.
- Existing authored isolated fixtures only: **7 passed, 138 deselected in
  0.52 seconds**, exit 0. Exact clean environment, five file arguments, Python
  path and outside-repository basetemp are in `isolated-command.sh`; complete
  output is `isolated.log`, status in `isolated.exit-code`. No research opt-ins
  were passed.

All fixture temporary files remain under
`/home/utkarsh/.cache/palimpsest-pytest/source-ci-isolated-first-20261106-01/isolated`.
The wheel-child fixture's supervision recorded returncode 7, failure null,
no survivors, and sampled peak RSS 65101824 bytes.

This proves shell syntax, the narrow source diff and successful local execution
of all seven existing isolated cases with unchanged source/test dependencies.
It does not reproduce hosted disk pressure, execute the modified full runner,
or establish that the next complete hosted run passes. Root will review before
committing/pushing and decide the hosted qualification. No commit, push, CI run,
full canonical repeat, model/runtime work or protected payload reads performed.
