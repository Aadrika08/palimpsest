# Puck collection custody and model staging: source evidence

The source unit at `72013da5b2a210c978982bfec95753700a1c9756` adds working descriptor
custody and unchanged-model staging on top of PR #116. Independent source review
approved that exact source; **220 affected tests passed independently in 19.36 seconds**.
There are no remaining actionable source-unit blockers. This report
records software evidence; original-bundle positive qualification, collection
allocation and all seven simulation release gates remain open.

## Working behavior

`HeldCollectionExecution` authenticates an externally reviewed canonical custody
manifest before opening seven fixed descriptor roles. It holds current sources,
freeze/envelope, collection projection, immutable original index, selected
bundle, historical producer sources and the exact registered runtime file.
Every root/ancestor/file edge remains held through staging and final close.
Source discovery covers the exact Python/XML roster under package, scripts and
upstream, rejects stale bytecode/links, and checks discovered edges after inventory.
The public context binds imported package paths to the admitted current root.
Role paths and actual held inode identities cannot alias across roles.

The selected bundle passes the existing fixed original-byte facade. Its admitted
arrays feed the unchanged `puck_model.make_model` with strict loading and evaluation
mode. Before and after staging, the context compares CPU float32 parameter bytes,
module topology and forward/call dispatch, rejects compiled dispatch and local or
global forward hooks, and rechecks inputs. The existing interval API stages one
teacher query followed by the bound student's prediction. A changed scene goal,
terminal state or custody/model drift refuses before returning a staged result.

Failed, expired or closed contexts are unusable. Exceptional close rechecks inputs
and releases all descriptors. Metadata is copied defensively. Legacy loaders,
protocol pins, native owner denial and study limits are unchanged. The context
neither steps physics nor publishes an interval; staged results are not native or
durable publication proof. It creates no reservation or execution grant.

## Verification and corrections

The affected six-file test slice passed **220 tests in 19.51 seconds**:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
  -m pytest -q tests/test_puck_execution.py tests/test_puck_execution_files.py \
  tests/test_puck_collection_admission.py tests/test_puck_bundle_provenance.py \
  tests/test_puck_on_policy_interval.py tests/test_puck_on_policy_native_interval.py
```

There are 114 new checks (59 holder / 55 context), plus 106 inherited affected
checks. Holder positives use authored temporary files, including an exact
21,662,864-byte sparse runtime fixture and a 4 MiB copied read. Model tests run the
actual unchanged Torch MLP in isolated subprocesses on authored numeric arrays
through the private generic lineage core. These do not manufacture a positive
public original-model admission or establish task capability.

Observed RED tests preceded implementation and each review fix. Independent
review reproduced three finding families: matching parameter bytes permitted an
activation change (and compiled dispatch); namespace drift could return before
final edge checking; and double-leading-root spelling bypassed cross-role alias
checks. The fixes bind full module dispatch, check inputs again after discovery,
reject ambiguous root spelling and compare actual held objects across roles.
Regression tests show changed predictions before rejecting altered computation.
The inventory race test asserts rejection after cleanup, so close-only rejection
cannot hide an incorrect success return. Additional checks cover file changes
after actual inference, wrong goals, terminal states, misuse, aliases, deadlines,
missing/extra entries, type aliases, defensive metadata and descriptor cleanup.

## Broad-suite limitations

The first default `pytest -q` attempt with the R0 environment stopped at collection
with ten errors: `test_lab` and `test_male_lab` lacked FastAPI; `test_male_recovery_collection`,
`test_male_recovery_data`, `test_train_male_recovery`, `test_verify_body_adaptation`,
`test_verify_body_runtime`, `test_verify_body_turns`, `test_verify_task_phases` and
`test_verify_task_starts` lacked httpx. Its terminal exit was 2. No tests ran.

The existing lab environment has those dependencies. Its default broad run showed
failures/errors, then stalled without a terminal summary. The recorded process
was verified by exact pytest argv and worktree, first interrupted with SIGINT and
then terminated with SIGTERM when it did not complete. Tool handle 99033 is
terminal with exit **143**. This is an interrupted, non-passing broad attempt;
no total pass/failure count or root cause for every failure is inferred.

A bounded 30-second, `--maxfail=1 --tb=short` comparison on unchanged base PR #116
reproduced the first failure in 2.89 seconds: **43 passed, 1 failed**, 15 deprecation
warnings. `tests/test_assets.py::AssetsTests::test_registry_pins_identity_and_mapping_hashes`
lacks `upstream/fly-gym/connectomes/drosophila adult connectome/visual_column_L1_L2_L3_rear_view_left.csv`.
This verifies that first failure exists on the base. It does not explain every
broad-suite failure or prove an integrated release. The focused source slice is
passing; the full repository/browser/native gates are not established here.

## Remaining execution admission

Independently qualify supplied original bundles under a bounded freeze, then bind
fresh-worker source imports, loaded runtime/dependencies, invocation and input
custody to durable attempt/owner reservations. Complete lease/process/deadline,
RSS/free-space/storage supervision and durable owner/collection close before
native collection. Measure the full context's cost inside existing limits.
Only four collection scenes (6110–6113) resolve; development scenes remain outside
this path. Preserve twelve owners times 600 intervals, 149 MiB recording/160 MiB
owner, 3 GiB stage, 1 GiB RSS/free floor, 16 GiB retention and 2210/2260/2270-second
stage limits. No actual puck collection, fitting or held-out phase ran for this
unit. CI and physical rover work remain excluded.
