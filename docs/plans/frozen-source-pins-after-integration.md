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

The exact node IDs are listed in `tests/frozen_pins.py`. There are 126 test
functions in total; parametrized cases share their function's entry.

| Protocol (pin source) | Pin | Tests |
| --- | --- | --- |
| Memory family compact v4 (`memory-family-compact-evidence-v4-directory-census-v1-protocol.json` `behavior_sources`) | bytes; `engine.py` differs | 66 functions in `test_memory_family_{oracle_admission,producer,condition_close,retained_source,raw_audit,compact}_v4`, `test_memory_staged_pair_v4`, `test_memory_directory_census_protocol_v1` |
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
  `tests/frozen_pins.py`; the registry rejects a test listed twice.
