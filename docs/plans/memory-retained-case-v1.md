# Retained staged case validation

This read-only source slice validates one registered source and all nine sealed
conditions together. It does not publish or prune a case, prove execution order,
qualify the runtime, or authorize a study. Existing protocols and source pins
remain byte-identical; this new reader is not an accepted qualification profile.

`read_retained_staged_case` takes independently registered condition terminal
exports, expected condition commit descriptors and one existing v3 case-table
slot. The slot binds the case hash and ten distinct run IDs. These inputs must
come from the external registration/audit chain, not be manufactured from the
candidate being inspected. No caller-supplied cells or execution-order flag is
accepted. Qualification-pin admission for all conditions precedes protected
source/condition access; the repository's trust anchor remains empty.

All conditions must bind the same case, source registration/commit/snapshot,
source identity and histories. Derive the registered cyclic order and reject
rows whose oracle precedes own. This supports authored positive fixtures for
compatible rows; it does not select those rows as a replacement study or resolve
the 42/48-row ordering conflict. Return `execution_order_verified=False` because
the design's order is not evidence of actual chronology.

Reuse `HeldReplayFiles` for continuous custody of the exact staged tree while
the existing source/condition readers run sequentially. Derive its inventory
from externally bound markers and their conversion descriptors. These hashes
establish stability; the existing readers independently check derivation and
semantics. Hold external registrations, controls, histories, qualification,
source dependencies and the selected behavior-source closure through teardown.
Use the existing validating stack to preserve the primary failure if teardown
also fails. Release decoded condition rows after each projection.

The whole-case boundary requires `.raw` to be absent, including an empty parent;
it never removes it. Refuse final aliases, temporary markers, quarantines,
unknown entries, links and substitutions. Before close there are exactly 33
directories and at most 418 files, with the existing source, condition, snapshot
and per-owner limits. Report actual file/directory/byte counts. No extra files
or disk allowances are introduced: future manifest/close receipt/final marker
still share the existing three-file, 32 MiB budget and 454-entry maximum.

Derive retained cells from validated rows and terminal outcomes. Count only
actual motor rows, compute path length from pose pairs, preserve the normalized
shared-snapshot invariant, check goal geometry against the snapshot and apply
the existing goal-ticks/900 cap. Reject nonterminal and infrastructure outcomes;
a retained sensor-only CueUnavailable terminal adds no motor tick. Check
own/sham equality and all nine no-event outcomes. These cells carry retained
attestation evidence, not a freshly asserted policy-binding pass. Every existing
claim remains false and returned data retains no custody capability.

Verify coherent nine-condition authored fixtures, default refusal, exact slots
and namespaces, cross-condition equality, mutation of earlier evidence during
later validation, primary-error preservation and descriptor cleanup. Keep
publication schemas, authorized mutation/rename, actual-order proof, real
pruning, seed applicability and scientific qualification as separate remaining
work. Strict read-only custody intentionally cannot authorize a directory move.
