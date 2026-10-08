# Memory family v3 oracle evidence and selector admission

8 October 2026. Software-only implementation plan, based on `35f6a79` and the
[prospective nine-condition design](memory-confirmatory-v3-design.md). This unit
does not grant native owners, select a held-out block, read a scientific result,
or qualify the family runtime.

## Deliverable

Add one evaluator-only module that derives oracle target IDs from an admitted
version-3 acquired snapshot plus a retained non-oracle continuation. The module
must independently reconstruct the source observations, event schedule, cue
transition, gate edit and pre/post passage occupancy. It must reject a proof that
differs from those supplied records and expose only the proved target-ID list and
proof hash to the existing oracle selector.

The existing runtime selector remains unchanged. It already restricts historical
E to retrieval and target IDs to oracle, but its provenance field is only a hash;
it does not establish that the IDs are true. The new adapter supplies that missing
admission check before selector configuration. Existing v1/v2 pilot scripts and
their recorded evidence remain frozen.

## Fixed contract

The proof builder takes the canonical family case, the source snapshot application
state, bounded source events/rows, bounded continuation events/rows, the final
continuation world state, and explicit artifact/protocol hash bindings. The caller
owns checksum-validating file reads and exact extraction from those files; the
module never opens a recording or snapshot.

Admission requires:

- a canonical version-3 case and unarmed, paused, acquired source boundary whose
  graph, case, seed, episode, memory cursor and world cursor agree;
- exact fact evidence matched to independently reconstructed recorded packets and
  actual source poses, with both factual estimates observed open;
- the registered profile's event and decision offsets, reached in the retained
  continuation with exact packets for every boundary through decision tick;
- consecutive visible cue observations and the exact recorded trigger for change
  and null, or no cue/trigger/selection/world event for no-event;
- one exact scheduled gate edit and matching intervention for change, no gate edit
  for null/no-event, and rejection of missing, duplicate, rejected or wrong edits;
- retained world geometry equal to independently reconstructed geometry before and
  after the event, and no fresh passage observation through commitment;
- gold recomputed only by `memory_experiment.gold_target_ids` from the admitted
  source M, reconstructed occupancy and actual trigger. Null/no-event gold is empty.
- the donor's own U has fitted-history provenance bound to its admitted history,
  and its recorded selection is replayed through the shared non-oracle selector;
  that replay authenticates the donor and is never an input to evaluator gold.

The retained proof binds case/family/profile hashes; protocol, plan and source
identity hashes; source/post run, recording, report and snapshot hashes; source M
and observation hashes; schedule; event/gate evidence; occupancy; and final target
IDs. Its canonical hash is oracle selector provenance. A shared selector-resource
adapter rejects any supplied proof for the other eight conditions.

## Verification and limits

Synthetic tests cover all 48 rows, three case kinds, both schedules and both
closure sides. Mutation tests cover source evidence, packets, geometry, schedule,
trigger, intervention, artifact bindings, proof targets/provenance and non-oracle
proof leakage. Proof construction must not fit; only donor authentication may call
the shared own selector, while evaluator gold remains occupancy-derived.

This proof contract validates supplied retained evidence; it is not a raw-file
reader or a native driver. A later driver/auditor must first checksum files,
validate owner/manifests/snapshot registration, then pass the exact decoded values
to this module. That later unit also owns the historical namespace inventory,
1,440-candidate matrix, finite allocation, owner cleanup and complete raw audit.
At current per-owner ceilings, one full block projects a 558 GiB raw plus 22.5 GiB
snapshot worst case before logs and prerequisites, so no allocation is inferred.
