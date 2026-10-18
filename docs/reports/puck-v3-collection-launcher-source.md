# Puck collection launcher: held native route and fixed clocks

The collection path now connects the held model's staging and integrity checks
to the existing native interval and real durable row writer. A separate fixed
clock ledger prevents child time from being borrowed for parent work. These are
implemented launcher components; the complete collection launcher and all seven
simulation release gates remain incomplete.

Source commit: `b3d84a62fb4956923b2efdd17e09c860e956f8e1`, based on PR #121
`9485df1`. The [implementation sequence](../plans/puck-v3-collection-launcher.md)
records the full path and the remaining prerequisite/runtime/owner integration.

## Behavior and failure boundaries

- `HeldCollectionExecution.native_interval(...)` uses the unchanged interval
  pipeline with the held context as its staging provider. A simultaneous loose
  model is rejected. The historical `owner(config)` v3 denial remains intact;
  the new method is not a native allocation or collection grant.
- Custody/model checks run during staged inference, before native step,
  immediately before row publication and after publication. Query/action/task/
  cursor arithmetic is unchanged. One successful interval queries the teacher
  once, predicts once and steps only the student's action.
- Failure stops the writer and permanently poisons the held context. A failure
  before publication yields no new row or returned cursor. Drift after a row is
  committed retains that row as an incomplete prefix and returns no successful
  successor. The second-interval drift check preserves only its first committed
  predecessor; neither context nor writer can continue.
- The native helper imports through the declared package path without changing
  `sys.path`; the direct historical script import path remains supported.
- `CollectionClockLedger` fixes twelve ordered scene/model owners, 180 seconds
  each / 2160 cumulative, parent 20/20/10 buckets, return 15/20/10/5 buckets and
  2210/2260/2270 stage boundaries. Exceptions, order/type/clock faults, nested
  operations and overrun prevent successful close. Ledger receipts report time
  accounting only, with empty claims and false execution/native/collection flags.
- Every gap is charged: before first owner to pre-admission, between owners to
  launch/reap, after last owner to reduction, between return phases to the next
  return bucket, and after the final guard through receipt construction to that
  guard. Short child runs never expand parent or return allowances. This ledger
  does not replace an operational hard supervisor or establish WCET.

## Verification observed

The root affected command passed **411 tests, six explicitly deselected, in
44.83 seconds**. It covers the twelve test files listed below, including fourteen
new native/import checks and fifty-five clock checks. Native fixtures use the
actual unchanged CPU Torch MLP on temporary authored parameters, faithful fake
MuJoCo/native state and the real disk writer. They do not run actual physics or
read original trained model payloads. Clock tests use controlled monotonic clocks.

```sh
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
  /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
  -m pytest -q --tb=short \
  tests/test_puck_custodied_native.py tests/test_puck_collection_ledger.py \
  tests/test_puck_execution.py tests/test_puck_execution_files.py \
  tests/test_puck_collection_admission.py tests/test_puck_bundle_provenance.py \
  tests/test_puck_on_policy.py tests/test_puck_on_policy_interval.py \
  tests/test_puck_on_policy_native_interval.py \
  tests/test_puck_original_bundle_qualification.py \
  tests/test_bounded_qualification.py tests/test_puck_mechanics.py \
  -k 'not (first_supervisor_exception or historical_construction_pin or progress_timeout or receipt_before_next or startup_timeout or v5_mechanics)'
```

Independent SOURCE GO applies to exact commit `b3d84a6`. The same command
independently passed **411 tests, six deselected, in 44.78 seconds**, exit 0.
The reviewer found no remaining blocking source issue and verified unchanged
HEAD/source bytes. No broader pass is inferred from this selected command.

Meaningful RED checks preceded implementation: twelve native cases failed for the
missing API; the isolated package import failed without the relative helper
import; clock tests first failed for the missing ledger. Review reproduced ten
clock-gap failures and one delayed-receipt failure before their fixes. Earlier
native fixture setup used two differently named imports of the mechanics module;
its ten failed/two passed run was corrected to instrument the actual helper module,
without altering production native semantics.

The initial wider run was **386 passed / 31 failed in 45.21 seconds**:

- Twenty-five original-qualification metadata checks rejected source bytecode
  emitted by the pre-existing isolated import test. `-I` ignores the environment's
  `PYTHONDONTWRITEBYTECODE`; adding explicit `-B` prevents that mutation while
  preserving its Torch/MuJoCo absence check. Only the five newly generated caches
  (255,368 bytes) in this new worktree were removed; no evidence was deleted.
- Six mechanics failures were separately reproduced on unchanged PR #121 base
  `9485df1` (six failed / fifteen deselected, 0.44 seconds). Three fail because
  the old mechanics protocol pins the historical puck profile while the current
  explicit-layout source differs; the immutable protocol/pin is preserved. Three
  fail because this source-test environment lacks `httpx`. These are the six
  explicit deselections in the passing affected command.

Exact baseline failure names:

- `MechanicsFixtures.test_first_supervisor_exception_retains_all_unstarted_rows`
- `MechanicsFixtures.test_historical_construction_pin_is_not_silently_promoted`
- `MechanicsFixtures.test_v5_mechanics_changes_only_identity_and_version_notes`
- `MechanicsFixtures.test_progress_timeout_forces_cleanup_and_never_passes`
- `MechanicsFixtures.test_receipt_before_next_ancestry_poll_waits_for_independent_identity`
- `MechanicsFixtures.test_startup_timeout_identifies_owner_before_any_receipt`

The bounded default repository command (`pytest -q --maxfail=1 --tb=short`,
20-second external limit) exited **1** at its first collection error in **0.32 s**:
`tests/test_lab.py`, missing `fastapi`. It did not run a full suite. Broader
repository/browser/native validation remains unqualified.

## Remaining to reach actual collection

Authentic fresh ref/history/worktree/raw-registry discovery and semantic scene
inventory must precede the durable eight-ID reservation and separately admitted
scene mint. Dedicated exact bundle/runtime views must preserve original bytes.
A fresh worker must bind its running interpreter, exact environment/invocation,
loaded source and external dependency/native image observations before imports.
The existing seven-role 80 MiB custody ceiling remains unchanged; external
runtime/dependency custody needs its own reviewed bounded scheme.

Integrate parent-owned writer lease, durable attempts and owner reservations,
process identity/progress/descendant cleanup, fixed clock/resource supervision,
initial snapshots, owner/manifest close, all twelve-owner coverage and final
publication. Review exact source/runtime/input/allocation freezes before each
actual registry, mint or collection stage. No original-bundle qualification rerun,
original model inference, real native owner, collection, fitting, development,
held-out, memory attempt 02, new navigation attempt, CI or physical rover ran in
this source wave.
