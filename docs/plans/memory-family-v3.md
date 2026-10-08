# Memory family generator and runtime integration

8 October 2026. Software-only implementation plan, based on `599141e` and
[the prospective study design](memory-confirmatory-v3-design.md). No native
allocation, study sample size, held-out assignment or scientific qualification.

## Deliverable

Generate canonically validated version-3 families that the existing private
`memory-decision-v2` Engine interface can actually consume. Preserve every old
case/profile/graph hash and old schedule. Keep the old pilot and audit frozen.
Publish this change on a separate branch, stacked on PR #95; do not merge main.

One family has a fresh scene/controller seed, and change/null/no-event twins.
Twins use identical scene parameters and controller seeds but disjoint case/entity
IDs and separate acquisitions. Conditions, twins and ticks are never extra
independent samples. A deterministic seed design is not proof of statistical
independence, native feasibility or generalization.

## Fixed software candidate

Use 24 assignment rows: three cost strata (south cheaper, north cheaper, exact
tie), each crossed with eight binary rows. For binary row `r`, a factor is the
parity of `r & mask`: learned relation=1, relation physical side=2, fact lexical
side=3, subject/landmark lexical side=4, route lexical side=5, schedule=6.
Zero means local relation / south / early schedule. Publish all rows. This is
pairwise balance with deliberate aliases: fact=relation XOR relation-side;
route=relation XOR subject; schedule=relation-side XOR subject. No separate
interaction-effect claim is permitted. Changed passage is preferred in half of
each cost stratum, including ties. Closure always follows the learned relation.

Each row and block gets a distinct seed; block range is [0, 2^25), row [0,24).
Development seeds are 2^30 + 32*block + row; held-out seeds are 2^31 + 32*block
+ row. These partitions are disjoint. Actual training-seed/entity separation
must also be checked against the frozen training inventory before collection.
No held-out block is selected by this implementation.

Draw geometry deterministically from separately labelled SHA-256 seed digests:
detour x in {0.5,0.6,0.7}, exit x in {1.1,1.2,1.3}, retreat loop radius in
{1.2,1.3,1.4}. Draw unequal offset pairs from {(0.15,0.20),(0.15,0.25),
(0.20,0.25)} and orient by cost stratum; ties draw one shared offset from
{0.15,0.20,0.25}. Both routes contain real detours. Public route cost remains
the sum of actual waypoint segment lengths, with symmetric exact ties.
The separator, apertures, inspection markers, sensors and controller stay fixed.
This is a narrow scene distribution, not arbitrary environments.

Two immutable family profiles schedule (event,decision) at acquired-boundary
offsets (1,2) and (2,3). Both world and supervisor read the registered profile.
There is no motor hold: the later schedule adds a normal motor/sensing interval.
Native evidence must establish event visibility and no new passage evidence
before commitment. Do not add an all-success/all-visible gate to scored arms.

Cases and graphs receive version 3; graph fields remain the same public contract
(IDs, path costs and profile hash). No scene factors, coordinates, gold or closure
enter the supervisor graph. Case validation reconstructs the whole case from its
split/block/row/kind; edits and unknown versions/profiles fail before runtime entry.

## Scope and verification

- Extend `memory_decision_world` in place: frozen family profiles, assignment
  table, deterministic generator, case validation, graph ID/version mapping and
  profile-driven world schedule. Existing replay provenance already hashes it.
- Update supervisor graph validation and schedule consumption, and private
  profile metadata. Engine and replay must admit the actual case through their
  existing validation paths, including acquired snapshot and schedule checks.
- Supply a software-only nine-condition slot producer bound to generated family
  IDs and hashes, compatible with the PR #95 readout. It launches nothing and
  does not invent prerequisites, oracle proof or study allocation.
- Add tests for all factors/aliases, real costs/ties, twin consistency, split
  partitions, mutation rejection, every finite geometry combination, synthetic
  acquisition/selector/schedule behavior, Engine snapshot admission and replay.
  Pin representative historical hashes and compare all 84 retained legacy cases.
- Run focused and full software suites, then one independent source review and
  any required fix verification. Retain exact commands/results in a report.

No native/model owner, physics stepping, fitting, old artifact/SNP decoding,
scientific data reads, retries or new dependencies. Synthetic tests may import
installed runtime libraries and use mocked Engine boundaries. The next phase
still needs the native driver, raw audit adaptation, oracle evidence, source and
profile qualification, sample/inference choices and finite registered allocation.
