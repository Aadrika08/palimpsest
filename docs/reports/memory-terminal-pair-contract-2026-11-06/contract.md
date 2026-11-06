# Task5a: conditional pure pair contract

Source-only proposal against `49304c81ffbdc3630b612fedfa9945a73bf0cc32`; root review precedes implementation.
Future ownership is ONLY `scripts/memory_family_terminal_condition_vnext.py` and
`tests/test_memory_family_terminal_condition_vnext.py`. This document runs no code/tests/probes.

## Useful delta and boundary
Task3a already checks source acquisition/invariants, restoration, registered schedule,
all reached transition bodies, terminal cause, goal radius and endpoint arithmetic.
It accepts a hash-bound, syntactically valid nonoracle selector/U without establishing
its nine-way history/provenance mapping (`terminal_audit_vnext.py:253–280`). Task5a
adds exactly that missing mapping and requires fresh Task3a proof equality. It does
not duplicate the transition auditor, manufacture an actual adapter, or complete Task5.

One API, no class, loader, CLI, public actual replay/seal/read/cell-consumer stub:

```python
prove_pair_vnext(source: dict, condition: dict, *, context: dict,
                 terminal_proof: dict, deadline: float) -> dict
```

This is a value-only theorem conditional on supplied decoded inputs and frozen history
descriptors. No file reads/writes, callbacks, model/native calls, authority flags or
receipt interpretation occur. Actual input authentication and registration remain
6a.2/3b/4b; integrated Engine ownership remains2b; guarded neural replay and sealing
remain Task5 proper, publication6b and analysis7. Authored6a.1 is not actual6a.2.

## Exact input domain
All listed dictionaries have exact key sets. Reject unknown/missing fields, bool for
integers, nonfinite values, opaque array/load proxies, wrong types and expired/nonfinite
deadlines. No fallback. Use the existing pure validators and their bounds directly.
`H` is lowercase SHA256; `D` is exact `{path:str,size_bytes:int,sha256:H}`, validated
by `transition.validate_descriptor_vnext`. UUIDs retain canonical hyphens via Context.

* `source = {application,events,rows,histories}`. `application` is the exact
  `oracle.APPLICATION_FIELDS` source application accepted by Task3a; `events:list[dict]`
  and `rows:list[dict]` are Task3a's decoded source inputs. Rows retain genuine NumPy
  arrays/scalars of the existing raw row schema, NOT compact projections/JSON arrays.
  `histories = {own,swapped}`; each entry is exact `{descriptor:D,bundle:dict}`.
* Each history `bundle = {e,u,history_sha256}` with `e=memory.validate_e(e)`,
  `u=memory.validate_u(u)`, `history_sha256=memory.sha256(e)`, and byte-exact canonical
  `u=memory.fit(e)` (E-only refit). Its D binds `memory.canonical_bytes(bundle)` exactly,
  positive size<=16MiB (inherited history bound). Own/swapped descriptor paths differ;
  `memory_experiment._ids(own.e)` and `_ids(swapped.e)` are disjoint, as old v4 requires.
  These supplied bundles are frozen premises, not proof of physical history acquisition,
  donor independence, current custody or accepted registration. Old v4's exact body has
  no seed/profile fields: upstream role/relation/seed/profile registration remains a
  premise; never infer it from fit(E) or invent fields certifying it. No new donor owner.
* `condition` is exactly the Task3a raw dictionary:
  `{manifest,events,rows,worker_report,job,descriptors}`. `events:list[dict]`,
  `rows:list[dict]` use its original decoded representation; `job:D` is only a descriptor.
  `descriptors={context,job,raw_manifest,raw_events,worker_report}`, each D.
  Task3a owns nested manifest/report/event/row schemas; do not replace them with a
  purported audit receipt, a status-bearing wrapper, or a numeric bundle. All raw fields
  reach3a unchanged; no compact16+3 carrier is consumed or rewritten in5a.
* `context` is the exact `transition._CONTEXT_FIELDS` / `validate_context_vnext` schema:
  `{schema,profile,source_closure,source_registration,source_commit,source_raw_audit,
  source_snapshot,source_application_sha256,source_m_sha256,source_world_sha256,
  source_run_id,case_id,case_sha256,kind,run_id,condition,condition_resources_sha256,
  source_invariant_sha256,schedule}`. Descriptor roles and scalar types are unchanged.
* `terminal_proof` has exactly `audit.PROOF_KEYS` and schema
  `memory-terminal-proof-vnext-v1`; accept it only after the fresh equality below.
  It is not a caller success/status permission or an actual audit receipt.

Representations are exactly Task3a's: source/condition event commitments use its
`_writer` spaced JSON+newline; raw manifest uses `_writer`; worker report/Context and
history bundles use `memory.canonical_bytes`. Raw arrays use existing Task3a validation,
row/camera commitments and legacy projection helpers. No invented serialization/hash.
Source application/events/rows/histories precede condition configuration; histories
contain no Context, proof, pair result or future output digest. Context's resource hash
binds pending `{selector,u}`; pending oracle provenance uses the existing acyclic helper.
Pair output references pre-existing inputs only. Never insert output hashes into source,
source registration, original history bundle, Context or condition job to form a backedge.

## Algorithm and exact nine-way mapping

1. Validate Context, outer shapes, deadline and history values/descriptor commitments.
2. Extract the unique actual `memory_selector_configured` event (existing pure
   `oracle._single`). Let `q=context.condition`, `O/S` be the validated own/swapped
   bundles, `Z=memory.artifact(method='empty-v1')`, `P=memory_experiment.PROTOCOL_SHA256`.
   Require the complete configured selector equal the following expected value:
   `{version:1,condition:q,limit:1,resource:R,resource_sha256:memory.sha256(R),provenance_sha256:V}`,
   and configured `u` canonically equal U. Nothing is accepted merely by its hash.

| q | U | R | V |
| --- | --- | --- | --- |
| own, sham | O.u | null | O.descriptor.sha256 |
| swapped | S.u | null | S.descriptor.sha256 |
| no-U | Z | null | P |
| hand-authored | memory.artifact('local_cue') | null | P |
| history-independent, traversal | Z | null | P |
| retrieval | Z | O.e | O.descriptor.sha256 |
| oracle | Z | [] | transition.pending_provenance_vnext(context) |

These preserve `_condition_mapping`'s nonoracle formulas (`oracle_admission_v4.py:578–651`)
without calling its old prior-own/receipt path. Oracle pending[] is a syntax marker,
not reached gold; no prior-own argument/result is admitted. Reached resolution/cardinality
and selection come only from fresh Task3a reconstruction, including raised local selection
without commit. Context resource equality and retained/source-view equality must still
pass `configure_terminal_condition_vnext`; source hashes cannot substitute for that check.

3. Call `audit.prove_terminal_vnext(condition, context=context,
   source_application=source.application, source_events=source.events,
   source_rows=source.rows, deadline=deadline)` directly. Compare ALL canonical bytes of
   its returned proof with `terminal_proof`; reject any difference. Do not call a
   shallow proof validator in place of replay, reuse caller reached flags, or reinterpret
   malformed normal evidence as a prefix. Recheck deadline before detached return.

## Exact result and endpoint provenance

Return a detached dictionary with canonical bytes<=1MiB, exactly:
`{schema,context_sha256,terminal_proof_sha256,history_bundles,endpoint}`.
`schema='memory-terminal-pair-pure-vnext-v1'`; both hashes are H of canonical complete
validated Context/fresh proof; `history_bundles={own:D,swapped:D}` binds supplied histories.
`endpoint` is exactly `{terminal_sensor_tick,goal,continuation_ticks,capped_ticks,
path_length,outcome,trace_digest,invariant}`. Copy those fields from fresh3a proof,
renaming ONLY `row_count` to `continuation_ticks`. Types: tick int|null, bool goal,
exact int counts0..900, finite nonnegative float path, exact3a outcome dict, H hashes.
No second goal/radius/path/score formula:3a already derives them (`audit:403–480`,
normal-goal checks`:390–400`). Zero retains null motor interval, path0., goal false,
score900 and empty commitments; short natural failure retains actual count/path and900.
Sensor-only terminal packets never become rows or model calls. This result has no actual
admission, qualification, model-equality, physical-accounting or deletion meaning.

## Cross-condition boundary and future acceptance tests

One pair proves no cross-condition equality. No extra family API in5a. Future6b case
close/Task7 analysis must fresh-check all nine pairs against one identical source identity
(six source descriptors, source run/application/M/world/invariant hashes, case/kind/schedule,
and both history descriptors), require exactly the nine registered unique condition slots,
and distinct condition run IDs. Compare own/sham endpoints canonically in every kind;
compare all nine endpoints canonically for no-event, including terminal_sensor_tick,
outcome/count/path/capped score/trace/invariant. Require no-event trigger_reached=false,
world_applied=false, no resolver/selection/install stages or selector invocation from each
fresh proof/raw replay; do not require decision_reached=false (ordinary route commitment
may be reached). These are explicit future6b/7 gates, not an implied5a pass.

Future focused tests must build at least one genuine positive from6a.1's
`_open_authored_source_vnext` with real authored FD/source decoding, detached
`held.context/source_application/_source_events/_source_rows` and `held.recheck()` around
pure proof use; build condition evidence anew from those exact values using Task1/2a's
real transition/persistence fixture patterns. No fabricated holder/qualified receipt.
Existing generic3a fixture is not drop-in: it uses arbitrary nonoracle provenance and
mutates the source endpoint for zero. Freeze correct resources in the authored slot BEFORE
opening; for a zero natural failure author consistent source raw/numeric endpoint bytes
before opening, then require the real transition to terminate without a motor row.
Also cover1/2-row natural failures, pre/post-trigger local cuts, reached null/change gold,
and no-event pending oracle; expected proofs/outcomes come from actual pure worker output.
Parameterize mapping positives/negatives across all nine: wrong U/refit/history role,
retrieval E, fixed provenance, oracle pending/provenance, limit/resource hash, plus history
descriptor bytes/alias/ID overlap; rebind Context/config hashes in negative fixtures so
mapping checks, rather than stale digests, reject them. Reject forged proof endpoints,
reached flags, source M/world/application, normal/failed relabeling, timeout and input mutation.

All inherited900/2100, source1200,7/5MiB events,512/384MiB raw,16MiB SNP,32/25MiB compact
and shared1MiB metadata ceilings remain; pair/proof/history-reference copies consume that
same future physical ledger. Pure5a does not establish ledger completeness or whole CPU/upper
bounds. Raw deletion stays disabled; source03/provider choice pending; full48 development
+48 held-out ×3 kinds ×9 conditions and separate held-out GO remain unchanged.
