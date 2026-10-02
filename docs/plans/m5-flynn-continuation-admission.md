# Proposed fixed CPU FLYNN memory continuation admission

**Approved prerequisite implemented with pure fixtures; no actual run is authorized.**
The original proposal/fixtures are retained in commit `143b929`. The 12-stage
neural verifier is prospective; the existing 22-stage manual route is unchanged.
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

The Engine construction API now has optional keywords
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
identity and matching source/case/destination seed; explicit manual-to-FLYNN
replacement requires live/policy source mode.
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

## Implemented scope and remaining callers

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
4. `tests/test_memory_flynn_admission.py` implements focused preflight, atomic
   application restoration, U-only checks, failure cleanup and six conditional
   policy/actions replay-route fixtures. Native/tensor/model boundaries remain
   explicit mocks. No existing test module needed alteration.

The verifier12-stage work described above remains prospective; its production
file is unchanged in this prerequisite. Engine and replay are implemented.
No worker/LabSupervisor, CLI, UI/API, case generator, sensor, snapshot schema,
body-profile or MaleCNS route changes are proposed here. Their existing calls keep
default behavior; product exposure of this script-only experiment remains later
work. Frozen previous data are not rewritten, and this proposal does not enable
held-out cases.

## Current pure checks and honest limits

`tests/test_memory_flynn_admission.py` has eight focused stdlib/NumPy checks:

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
Result: **8 fixture tests passed**, included in the final related engine, replay,
memory, history, world and case checks: **75 passed, no skips, 3.259 seconds**. Existing manual-transfer fixtures separately
passed: **14 tests, no skips, 2.595 seconds**.
Native restore and tensor hashing
are explicitly mocked, policy is `SmallPolicy`, physics is `SmallEnv`, and visible
observations are explicitly synthetic fixture packets. These are not acquired
history, a MuJoCo restore test, an actual FLYNN model run or proof of the proposed
new admission on actual native/model data. Production changes are confined to
Engine atomic admission and conditional replay. Root review/source freeze precedes
any separately bounded actual gate. Failures/nulls remain valid results.

## Read-only resource evidence and prospective fixed bounds

The retained completed CPU/full-FLYNN source is
`../lab-hardening/runs/m3-flynn-smoke-20261002/runs/0ece98c75eb348c3b928aa818dbde15a`.
Existing terminal/chunk/hash readers and registered-snapshot readers validate its
9ticks and four recording files. Its manifest SHA is
`f19e44305b3b867e78c50d892b3748c56dd2e0ab3bd38546452ca2ea30a417ff` and
first chunk SHA is `2f3d25d1fb353ed7ece7cdc1aed66e3bb875ac7f410813513a0b998b06a1e097`.
This is historical resource evidence only, not a new run or memory performance
result. Its first eight-tick chunk shows:

| Field | Per-tick shape/type | Bytes per tick |
| --- | --- | ---: |
| encoded_input | float32[4813] | 19,252 |
| raw_output | float32[2] | 8 |
| all numeric/camera arrays | recorded fixed schema | 216,094 |

Thus300 neural ticks require64,828,200 raw numeric bytes before NPZ headers,
events, snapshots and logs. Registered `initial.snp` is1,043,908bytes, SHA
`c74a8f8ff7f7b3a0849b26368635b98576d5eab13390a676071325332b00adef`;
the later full state is1,084,929bytes, SHA
`fe654bbdc1f0e4098eaf6197b9e2db466f5e96bab665d2f9c9746a6632bf7e7b`.
Policy hidden state is float32[1,138584],554,336bytes. Sample first-chunk mean/max
policy latency is0.0129784/0.0146641s and physics/render latency
0.0033940/0.00375555s; this short trace is not sustained qualification or a
completion guarantee. Memory selector/event resources add to the neural recording.

For the prospective12-stage case, retain192MiB recording/stage after this
neural-specific derivation:64,828,200numeric bytes plus1MiB archive allowance,
128KiB events/tick and16MiB fixed metadata allowance total121,975,592bytes, leaving
79,351,000bytes of recording-cap margin. These are conservative planning
allowances, not measured event usage or a guarantee for other schemas. Declare
16MiB snapshot/stage,1MiB per stdout/stderr stream and160s external/
150s internal wall bounds. Keep300 source ticks, zero-step policy/own anchors and
at most300 neural continuation ticks/condition. Register exactly one initial SNP
per stage,12 total (source, policy anchor, own-U anchor, nine branches), and count
snapshot indexes/control/logs separately from recording bytes. Reserve4GiB for aggregate new
output and a2GiB free floor: require6GiB free before allocation, with existing
StorageBudget preflight/enforcement and finite remaining aggregate headroom.
Existing measured64.8MB numeric cost leaves room for declared memory events;
validate actual schema/bytes and snapshot bound before publication. Retain separate
outer/worker/control bytes. The proposed whole-gate bound is1980s
(12×160+60cleanup grace); independently identify/clean only owned stage process
groups on outer failure. No retries, replacement scenes, tuning or hidden rescue.

These limits and exact task-failure versus infrastructure-failure categories must
be encoded and frozen in the prospective verifier protocol before actualGO.
Declared observed task failures/nulls remain scored data; infrastructure, identity,
hash or watchdog failure stops with remaining rows unattempted. Do not silently
change the old22-stage protocol or reinterpret a failed recording as completed.
At inspection, free disk was36,142,551,040bytes; this is time-dependent and must be
rechecked at launch. No aggregate output has been allocated and no neural verifier
run is ready/authorized in this prerequisite slice.
