# Puck scene inventory: prospective admission amendment 01

Status: source implementation and review only; no actual inventory reservation,
scene mint, original-model/native/held-out access or collection authorization.
Continue the approved simulation goal from PR #122 (`fc04598`). Preserve the
original on-policy protocol SHA
`fe8b2615f965a114274a13aeb2d49c26d3f79e0920eee72bce4eb671adff3d13`
and every original task/study/model/capability threshold. This document proposes
an explicit catalog-access boundary; it does not retroactively change that protocol.

## Problem to resolve before actual inventory

The [frozen protocol](m6-puck-navigation-v3-on-policy-relabeling-protocol.json)
requires every reachable ref/history/worktree and every prior scene registry,
manifest and evidence root to contribute to collision admission. It also states:

> The existing task-v5 authored rows 6200-6207 are not regenerated, opened, or executed by this protocol.

The public task JSON contains train/development and held-out coordinates in one
`layouts` array. Reading/decoding its complete bytes reads the catalog coordinates,
even if the parser later ignores those rows. Do not describe this as unopened
held-out geometry. Separately, historical plans/reports/refs repeat legitimate
scene definitions, while the supplied-inventory validator rejects duplicate
prior IDs and identities.

## Proposed boundary; approval required before actual catalog scanning

Allow read-only parsing of already-public historical task catalogs for collision
admission only. Record `held_out_catalog_read:true` when those bytes contain held-out
rows. Keep actual held-out registries, recordings, runtime payloads, native scenes,
training/evaluation paths and policy inputs unopened and unreachable. No held-out
coordinates or trajectories enter collection/fitting/selection/development.
An identity-only independently prepared projection is the alternative if the
literal catalog-byte lock is retained; that projection must bind the exact Git
blob/document identity and genuine scene/initial/payload identities.

This proposed exception concerns catalog access, not held-out evaluation or a
claim that layouts were secret. It requires explicit approval and independent
review before a registered real scan; source fixtures may use authored catalogs.
No approval is inferred from creating this amendment, a source test, disk cleanup,
or continued implementation of the simulation goal.

## Authentic discovery path

- Observe local heads/tags/remote-tracking refs, freshly advertised remote heads/
  tags/pull refs, registered worktrees including detached heads, every reachable
  commit/tree, and tracked JSON/Markdown document objects. Reject shallow history,
  replacements/grafts, ambiguous alternates, missing advertised objects, linked
  document entries, unreadable/changing roots or incomplete enumeration.
- Bound command output while reading and enforce deadline/reap/drain on the owned
  process group. Preserve observations and Git object identities. Git binary,
  environment/SSH/dependency binding remains a later execution-freeze requirement;
  an authored Git fixture does not qualify the installed project runtime.
- Discover all matching repository roots, including separately owned nested Git
  repositories, and all retained registry/evidence roots under a reviewed root
  contract. A component enumerating one known repository cannot assert complete
  project inventory or infer that unlisted roots are empty.
- Dispatch scene parsers by exact path/schema/version and typed field paths;
  distinguish scenes from model/RNG seeds, counters and hash substrings. Unknown
  scene-bearing schemas, unsupported Markdown declarations, unresolved references
  or geometry fail closed. No bare number search or invented identity hashes.
- Normalize identical semantic scene definitions into one prior identity row and
  retain every original occurrence in bounded provenance. Preserve all distinct
  historical variants; if the old admission schema cannot represent them, stop
  and make that prospective decision explicit. Never drop a variant to pass.
- Aggregate only the exact hash-bound prospective lineage into one eight-ID
  self-reservation with null geometry identities. An actual duplicate reservation,
  minted scene outside that lineage or ID reuse is a collision.
- Hold/recheck all input/root/object/ref observations through final publication.
  Use the existing durable reservation/scene publication helpers after complete
  admission. A supplied `complete:true` is not a discovery receipt.

## Source implementation wave

1. Implement `HeldGitSceneSources` and meaningful real temporary Git/bare-remote/
   branch/history/detached-worktree fixtures. This component proves bounded
   discovery for one declared repository, with explicit false whole-inventory/
   reservation/native/collection grants.
2. Implement pure historical task-catalog normalization using the same geometry
   and scientific-initial hash domains as v3. Preserve genuine historical layout
   payloads; do not invent v3 slots or confuse a full native/RNG fingerprint with
   the geometry-only scientific initial. Report public held-out catalog exposure.
3. Independently review source and repeat affected checks. Commit/push an evidence
   report and this concrete prospective amendment for the catalog-access decision.
4. Continue root discovery, strict reference/Markdown/raw-registry parsers and
   complete custody/assembly; then review exact source/runtime/input/argv/allocation
   before any real stage. Do not substitute this component for the full launcher.

Unchanged prospective registry stage: one durable attempt before retained access,
600 seconds internal / 650 normal / 660 enclosing hard, 64 MiB stage output,
1 GiB sampled RSS/free-space floor, 16 GiB retained-run cap. Source component caps
are finite failure ceilings inside that stage, not extra time/storage grants.
No actual scene registry, raw manifest, original checkpoint, model inference,
minter, native owner, fitting, development, held-out evaluation, memory attempt 02,
navigation retry, CI or physical rover work is authorized by this source wave.
