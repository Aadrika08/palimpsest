# Memory family v3 oracle proof verification

8 October 2026. Implementation commit
`46b8488f2a980b88186880c92c8135979c3f5df3`, based on family-generator
commit `35f6a792a226c72290a77b78c72be603167126d0`.

This unit adds a pure, evaluator-only admission boundary for oracle target IDs.
It does not open raw files, launch native owners, step physics, fit an artifact,
select a held-out block or read a scientific outcome.

## Result

The proof builder accepts one canonical version-3 family case, its paused acquired
application state, the retained source and own-continuation event/row projections,
the final continuation world state and caller-validated provenance bindings. It:

- reconstructs every symbolic packet from the frozen geometry and recorded pose;
- replays the source acquisition and the configured, armed own continuation through
  the existing pure supervisor, requiring byte-exact recorded decision audits and
  final acquired memory;
- requires a fitted-history own U, its history and bundle identities, and exact
  replay of the non-oracle own selection;
- verifies native event sequence, run ownership, tick chronology, row continuity,
  restore state, registered schedule, cue transition, gate intervention and the
  one supported sensor-only terminal boundary;
- rejects fresh passage evidence through commitment and independently reconstructs
  pre/post occupancy before calling `memory_experiment.gold_target_ids`;
- exposes the proved IDs and proof hash only to `oracle`; the other eight conditions
  reject any proof or evaluator evidence.

Synthetic coverage exercised all 48 family rows and three case kinds. All 48
change cases produced one expected target; all 96 null/no-event cases produced an
empty target list. Both registered schedules and both closure sides were reached.

## Review corrections

Independent review initially found that a truth-derived hand-authored U and a
structurally valid forged selection could masquerade as an own donor. The final
contract requires fitted-history provenance and replays the shared own selector.

Further Engine-parity probes found incomplete snapshot validation, cross-run or
out-of-order events, discontinuous rows, queued-command continuations, malformed
commitments and fabricated terminal failures. The final implementation mirrors
the Engine application boundary, requires canonical run IDs and native event
chronology, joins every row pose, and replays both source and continuation state
machines. Follow-up review reported no remaining Critical or Important finding.

## Verification

The focused oracle suite passed 5 tests in 64.66 seconds. It covers the complete
144-case cross-product plus mutations of evidence, packets, history/U/selector
provenance, recorded selection and commitment, restore state, schedule, geometry,
event ownership/order, row continuity, intervention, terminal handling, proof
targets and non-oracle leakage.

The affected family, runtime, slot, oracle, decision, task and experiment suite
passed 92 tests in 81.08 seconds. `py_compile` and `git diff --check` also passed.
CI and the full repository suite were intentionally not run for this unit.

Exact hashes and test accounting are retained in
[`memory-family-oracle-v3-evidence/verification.json`](memory-family-oracle-v3-evidence/verification.json).

## Remaining boundary

This verifies the pure admission mechanism against synthetic retained records. A
later driver/auditor must checksum the actual recordings, snapshots, reports and
history bundle; validate owners, manifests and source identity; project the exact
decoded values into this module; and retain the proof hash in the raw audit. No
native allocation, development result, held-out choice or scientific qualification
is implied here.
