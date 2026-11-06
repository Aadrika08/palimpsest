# Hosted fixture free-space repair

Run [42136045205](https://github.com/Aadrika08/palimpsest/actions/runs/42136045205)
at `1743647922e739efd819bc3d67ffc1856b9a9d9f` failed the isolated wheel-child
fixture. Its added diagnostic reports `failure: free-space floor`, `pid: null`:
the supervisor correctly refused to launch under its2GiB free-space floor.
The earlier4a59e7a run's exact refusal remains unknown; this later observation
does not retrospectively prove it.

The hosted ordinary pass completed7,035 checks with318 skips in2688.60s;
isolated had6 passes and1 failure in14.31s; persistent passed5 in77.91s;
tmpfs passed57 in72.87s. Total7,103 passed,318 skipped,1 failed. Frontend
passed. Original API response and warning-bearing log are retained here.

The runner retains ordinary temporary files until all passes finish. The repair
runs the isolated group first, before that accumulation. It retains the same
four selectors, separate clean processes, basetemp names, selected/integration
modes, status propagation and final cleanup. Production guards, limits and test
expectations are unchanged. Initial workspace `df` output did not independently
establish headroom for the failed home-directory mount; the order repair is not
a guarantee that every hosted filesystem has enough space.

Local verification: the7 existing isolated cases passed in0.52s with138
deselections against the unchanged source/test tree; the12 existing runner
contract cases passed in0.60s against the modified runner in the sparse repair
worktree. The latter checks all four default invocations plus selected and
integration modes, explicit opt-ins and clean environment. Shell syntax and
scoped whitespace checks passed. No new tests or guard mocking were added.
The selected fixtures are not a fresh complete canonical or hosted pass.

Remaining authored workspaces are retained outside the repository; exact
isolated command and logs are included. Existing test-internal transient-file
operations are unchanged; this is not a claim that every transient file survives.
The repair worktree checked out only named source/docs/test files, not retained
model/data artifacts. No research opt-ins, actual research owner, source03
service, protected read or raw deletion occurred. Actual qualification remains
false; PR187 remains held until exact-head hosted checks pass.
