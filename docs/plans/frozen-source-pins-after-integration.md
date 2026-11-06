# ADR: frozen source pins after integration

**Status:** accepted for Phase 1 foundation repairs (2026-10-19).
**Context:** PR #179 (`8626ecb`) merged every branch into `main`.

## Context

Finished studies and allocations froze exact inputs before they ran. These include:

- the bytes of local behaviour sources, such as `src/palimpsest/engine.py`,
  `artifacts.py` and `puck_profile.py`;
- whole protocol documents;
- source closures;
- in a few cases an absolute repository location.

Their production readers refuse any difference, for example:

- "Behavior source differs: engine";
- "Frozen task/teacher source differs";
- "Frozen execution contract differs".

That refusal is the guarantee that recorded evidence was produced by exactly the
reviewed code.

Integration changed those files on `main`. Each study's frozen bytes are still
intact at its own commit and in its archived evidence. However, tests that run such
a protocol against main's **current** working tree now meet the refusal. On the
merged-main baseline this accounted for about 280 of the failures.

## Decision

1. **Frozen protocols stay bound to their commit.** A finished protocol's pins are
   never edited to match `main`, and the production refusal logic is never
   weakened, bypassed or made conditional.
2. **Evidence keeps archived copies.** Evidence packets keep their own copies of
   the frozen sources. They are verified against the source commit with
   `scripts/verify_evidence_packet.py`, which also resolves `upstream/fly-gym/*`
   through the source commit's gitlink.
3. **Resuming a line on main means re-pinning prospectively.** To continue a study
   on `main`:
   - write a new prospective amendment that pins main's current bytes, with its
     own review;
   - that amendment's tests then run against the current tree again.
   Nothing is silently promoted.
4. **Tests use one shared helper.** It lives in `tests/frozen_pins.py` and is
   applied by `tests/conftest.py`.
   - Every affected test is listed under its protocol.
   - Each protocol's pins are read from the frozen protocol document itself, not
     copied into the test.
   - A listed test is skipped with an explicit historical reason only while one of
     its protocol's pins actually differs in this checkout. The reason names the
     protocol, the differing paths or location, and this ADR.
   - `tests/test_frozen_pins.py` replaces the current-tree comparison. It checks
     every byte pin against the file at a commit in HEAD's history.
     - **Meaning kept:** each pin must name the exact bytes of a real historical
       file.
     - **Stale lists caught:** every listed test must exist.
   - A frozen list that is not a byte pin is checked against the pinned commit's
     tree (`git ls-tree`/`git show`). Allocation 16's episode source closure is
     the case here; it is checked at its evidence index's `source_commit`.

Two protocols also freeze an **absolute repository location**. Their tests are
historical in any checkout other than the original one, including the main
checkout.

- The memory full-cell v4 execution freeze binds
  `.worktrees/memory-replay-custody-v4`.
- Navigation v3's execution manifest binds an output under
  `.worktrees/navigation-v3-matched-budget`.

## Affected protocols and tests

The exact node IDs are listed in `tests/frozen_pins.py`. The registry contains
129 pre-existing function entries and 100 additional
case-publication entries (81 functions and 19 exact parameter nodes). These are
registry strings, not collected-test or passing-test counts. Function entries cover
all their collected parameter descendants; exact entries cover only that node.

| Protocol (pin source) | Pin | Tests |
| --- | --- | --- |
| Memory family compact v4 (`memory-family-compact-evidence-v4-directory-census-v1-protocol.json` `behavior_sources`) | bytes; `engine.py` differs | 66 functions in `test_memory_family_{oracle_admission,producer,condition_close,retained_source,raw_audit,compact}_v4`, `test_memory_staged_pair_v4`, `test_memory_directory_census_protocol_v1` |
| Memory case-publication v1 (active compact `behavior_sources`, condition and publication `source_pins`; documents below) | union of 93 named byte pins, including the helper itself | 100 explicit function/exact-parameter entries in numeric preservation, raw audit, source seal, source runtime, source qualification and publication-profile tests |
| M6 puck learning v2 (`m6-puck-learning-v2.json` task protocol and teacher source) | bytes; `puck_profile.py` differs | 43 functions in `test_puck_{student,balanced_student,collection,development,balanced_development,learning,balanced,model}` |
| M6 puck mechanics v5 (`m6-puck-mechanics-v5.json` `puck_module_sha256`) | bytes; `puck_profile.py` differs | 7 functions in `test_puck_collection`, `test_puck_mechanics` |
| M7 navigation v2 checkpoint support (`m7-navigation-v2-checkpoint-support-v1.json` `reader_sources`) | bytes; `artifacts.py` differs | 2 functions in `test_male_navigation_v2_checkpoint_support` |
| M7 navigation v3 matched budget (protocol `existing_hashes`; execution-v2 manifest output) | bytes and location | 4 functions in `test_male_navigation_v3`, `test_male_navigation_v3_execution` |
| Memory full-cell qualification v4 (`memory-full-cell-qualification-v4-execution.json` `repo_root`) | location | 4 functions in `test_memory_full_cell_amendment_02`, `test_memory_full_cell_qualification_v4` |
| Allocation 16 episode closure (`EPISODE_WORKER_SOURCES`) | closure at `source_commit` | `test_puck_episode_sources::test_episode_closure_registers_every_runtime_read_and_nothing_else`, now checked at the source commit and not skipped |

The held episode-16 and preparation04 configurations pin `engine.py`,
`artifacts.py`, `comparison.py`, `male_policy.py`, `male_research.py` and
`profiles.py`. They are checked by their evidence packets, not by current-tree
tests, and need no skip.

## Consequences

- `main`'s suite is meaningful again. Real failures are not hidden among
  historical refusals, and no production guard changed.
- When a line is resumed through a prospective re-pin, its tests run again
  automatically, because the skip depends on actual drift.
- A new historical protocol with current-tree tests must be added to
  `tests/frozen_pins.py`; the registry rejects duplicate IDs and a function
  registered together with any
  of its exact parameter nodes, even under the same protocol.


## Case-publication historical source policy

`memory-family-compact-v4-case-publication-v1` is distinct from the preceding
retained-condition group. Its pins are the union of the real declarations in:

- `memory-family-compact-evidence-v4-case-publication-v1-protocol.json`,
  `behavior_sources`;
- `memory-condition-seal-v1-case-publication-v1-protocol.json`, `source_pins`;
- `memory-case-publication-v1-protocol.json`, `source_pins`.

Equal path/digest duplicates are accepted; conflicting digests for a path fail.
No digest is copied into the helper. The 93 named source/configuration/document/test
pins, including the JSON model manifest metadata, are historical bytes at main
ancestor `5547efc6dd7210e7a35aa02536140c351c7104b1`. Checking manifest metadata
confers no authority to read its referenced model payloads. The helper and conftest
are themselves pinned; editing them produces expected historical drift. Their old
pins remain intact until a separately reviewed prospective epoch.

Collection selects an exact node first, then falls back to its function entry.
Only actual drift in the selected group's pins produces a historical skip. This
preserves the early raw snapshot-size, run-id and symlink siblings; qualification
failed-owner, corrupt-report, early-profile and early-control siblings; unknown CPU
or non-drained-owner refusals; and the four launch/early-closure qualification
checks excluded during registry review. Other historical groups keep their exact
ownership. Authored current-profile tests and current-semantic copies acquire no
new group marker.

Skipping a historical function loses its assertion coverage, including independent
assertions later in that function. In particular, the old initializer function's
path assertions are no longer reached in this checkout. A historical skip is
neither a pass nor current semantic coverage, qualification, adoption, execution
permission or permission to delete raw evidence. Historical-byte checks prove only
pin provenance. Existing authored current-semantic copies remain independently
active; the active metadata counterpart described below proves neither live
closure completeness nor runtime or research authority. Unmapped closure/contract
assertions remain active and can fail
when the current dependency graph changes; they must be reported and reviewed on
their own terms, never silently hidden by expanding a historical source group.


The reviewed one-node amendment preserves the complete original mixed
`test_complete_declared_closure_excludes_output_cycles_and_real_trust` unchanged
under the historical case-publication group. Its live local-source closure assertion
now observes a new current dependency outside the historical roster. The distinct
active `test_declared_profile_metadata_and_empty_real_trust_remain_active` retains
its three canonical profile reads, exact declared root and excluded-path sets, and
all independent uniqueness, membership, output-cycle, sorted-pin and empty-trust
assertions. That active counterpart has no historical owner or skip/xfail mark. It
verifies declared metadata and empty real trust while source pins drift; it does
not prove completeness of the current import closure. The earlier 99-entry policy
and failing mixed-node evidence remain retained; this amendment adds only that one
historical node and preserves the independent assertions in the active counterpart.
