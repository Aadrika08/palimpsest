# Proposed fixed CPU FLYNN memory continuation admission

**Proposal only: production/runtime code is unchanged; no actual run is authorized.**
The completed all-nine gate remains manual development evidence at `0a05233`.
This prerequisite implements the PRD14.5 fixed pretrained motor path, not a claim
that FLYNN can complete this scene. It must not overload the independent MaleCNS
research-binding route.

## Existing boundary and decision

`Engine.open` validates the case before writer/environment/policy allocation;
`Engine.__init__` repeats that validation. `_validate_memory_case` rejects
`acquisition=True` with any controller except manual. `validate_application` then
requires the destination's exact case, original unknown initial bank, supported
application schema, immutable controller tensors, paused/fresh destination and
memory/world cursor agreement. A script-only override cannot satisfy this contract
without patching validation, assigning internal case fields, or lying about the
case. Regenerating `acquisition=False` changes start, goal, cue, schedule and hashes;
changing just its flag fails canonical case validation. **Engine admission is
required.** Keep ordinary fresh-run admission unchanged.

Existing `restore_branch(replace_controller=True)` already replaces controller/
Torch state, cancels inherited command history/manual intent, binds the actual new
policy tensors, and restores M/E/U, world/environment, eye state and non-Torch RNG.
It increments revision and records `controller_replaced`. This preparatory boundary
is not U-only. After capturing its new native/controller anchor, every neural fork
must preserve actual tensors, policy hidden state and all RNG, not merely checkpoint
names or output similarities.

## Exact proposed API and atomic ordering

Extend only the Engine construction API with optional keywords
`restore_snapshot=None, replace_controller=False, memory_u=None` on `Engine.open`
and its construction path. Defaults retain current behavior. These arguments
select existing operations, not a new application schema:

- No snapshot: both other arguments must be their defaults. The existing fresh
  acquisition/manual restriction remains in force.
- Snapshot plus `replace_controller=True`: `memory_u` must be absent. Execute the
  existing controller replacement, never a simultaneous U replacement.
- Snapshot plus `memory_u`: execute existing `restore_memory_branch`; its exact
  scientific-state guard and action-stream rejection remain intact.
- Snapshot with neither option: execute existing ordinary `restore_branch`, used
  for policy/actions replay of an already admitted neural snapshot.

Preflight a normalized/copied snapshot and case before allocation. The exception
is restricted to `memory-passages`, fixed CPU FLYNN and an exact, valid original
acquisition case bound to that snapshot's world state. Require a paused source,
supported application schema/finite bounded memory/world state and exact case
identity; explicit manual-to-FLYNN replacement requires live/policy source mode.
Do not weaken subsequent application/native model/tensor/RNG validation. Reject
invalid flags, ambiguous operations, unrelated profiles, malformed/mismatched
cases and U artifacts before allocation where their validation is pure.

Construction must perform the selected existing restoration **before returning
an Engine object**. No public fresh run/step/reset is available before restoration
success. Initialization may reset/configure the destination to allocate its native
model, but executes no control tick or inference and fabricates no memory packet.
On failure, `Engine.open` retains a failed destination recording and closes only
its owned writer/environment; the source remains untouched. No returned admission
flag or later caller promise may substitute for this atomic ordering. Validate
both the early `open` gate and repeated constructor gate using the same context.

A successful restored object uses existing live stepping. No manual `set_action`,
`advance(action_override=...)`, replay driver, hidden steering, robot teleport or
true-goal fallback is permitted in the prospective neural continuation. The bridge
changes only declared wind bearing; cameras, other sensor components, checkpoint,
graph, preprocessing, action conversion and 0.02-second interval remain fixed.

## Exact callers and scope for a subsequent implementation

1. `src/palimpsest/engine.py`: shared preflight and atomic open/constructor routing
   to existing restore methods; ordinary admissions/restore validators unchanged.
2. `scripts/verify_memory_transfer.py`: manual acquisition source unchanged; open
   a zero-step FLYNN replacement from its registered verified source snapshot,
   capture a distinct empty-U policy anchor, then create the existing own-U anchor
   from that policy anchor. Fork the nine selectors from the shared own-U anchor.
   This is **12 fixed stages** for the first prospective seed16/local/change case:
   source, policy anchor, own-U anchor, nine continuations. Preserve fresh actual M,
   source command/case/schedule identity and all history/refit checks. Log/pin the
   newly loaded CPU policy and both preparation boundaries. No manual continuation
   velocity/heading driver remains active after the policy anchor.
3. `src/palimpsest/replay.py`: its existing reader must still validate terminal
   recordings, registered initial snapshot/hash/prefix and manifest/snapshot case
   equality. Pass that verified snapshot into atomic `Engine.open` with unchanged
   case/controller/CPU identity, and remove the second ordinary restore call.
   Preserve compatibility checks. `policy` mode reexecutes `policy.act`; `actions`
   mode uses only the exact recorded action stream and continues to declare
   `inference_executed=false`. It is never counted as neural experimental evidence.
   Without this narrow glue, executable replay of the admitted acquisition neural
   anchor remains rejected; do not bypass case validation to claim replay support.
4. Focused fixtures: `tests/test_memory_flynn_admission.py`, existing transfer and
   replay test modules. Add atomic preflight/failure cleanup/no premature tick,
   ambiguous operation, double-restore, provenance/case mismatch, exact neural
   action binding, and admitted policy/actions replay regressions when the runtime
   change is reviewed.

No worker/LabSupervisor, CLI, UI/API, case generator, sensor, snapshot schema,
body-profile or MaleCNS route changes are proposed here. Their existing calls keep
default behavior; product exposure of this script-only experiment remains later
work. Frozen previous data are not rewritten, and this proposal does not enable
held-out cases.

## Current pure checks and honest limits

`tests/test_memory_flynn_admission.py` has four focused stdlib/NumPy checks:

- actual current `Engine.open` rejects acquisition/Flynn before writer, diagnosis
  or policy allocation;
- flag forgery rejects and regenerated non-acquisition geometry cannot restore the
  acquisition application (native restore is not called);
- current replacement on a permitted **non-acquisition fixture** preserves complete
  M/E/U/cursor and world task state, clears commands/manual intent without inference,
  records its boundary and subsequently uses projected `policy.act` inputs/actions;
- post-anchor invariant hashes permit only U/recording identity changes and detect
  native, hidden-policy, Torch/NumPy RNG, M/E, detector/cursor/request/active mutation.

Command: `PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest test_memory_flynn_admission`.
Result: **4 tests passed, no skips, 0.235 seconds**. Native restore and tensor hashing
are explicitly mocked, policy is `SmallPolicy`, physics is `SmallEnv`, and visible
observations are explicitly synthetic fixture packets. These are not acquired
history, a MuJoCo restore test, an actual FLYNN model run or proof of the proposed
new admission. No production code changed. Root review precedes implementation;
a separately frozen bounded actual gate is required afterward. Failures/nulls
remain valid results.
