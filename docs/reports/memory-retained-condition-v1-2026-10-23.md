# Retained condition reader and current-source profile

The source-only retained reader is implemented for all nine registered conditions.
It checks the staged compact evidence after fixture raw removal without loading
or replaying a model. Results explicitly label saved replay evidence as a retained
attestation. The repository's qualification trust set remains empty; production
calls still refuse before protected evidence access.

## Current-source integration

The first new tests exposed an existing integration boundary: the directory-census
protocol pins older Engine, artifact-reader and recorder sources. Their historical
checks had been skipped on current-source drift. The new prospective
[profile](../plans/memory-family-compact-evidence-v4-retained-condition-v1-protocol.json)
and [condition extension](../plans/memory-condition-seal-v1-retained-condition-v1-protocol.json)
bind this checkout. The two earlier base protocols and two earlier extensions
remain byte-identical. All scientific, ordering, schema, storage and false-claim
fields are preserved. Historical pin checks remain, while the current source
checks run again.

Read-only source review found the drift adds the manual environment constructor,
optional held diagnostics, optional background recording, longer artwork episodes,
recording run-ID checks and accessible SVG descriptions. The inspected memory
pilot keeps its Flynn controller, ambient diagnostics and synchronous recording.
The lower-level artifact helpers and `iter_ticks` retain their historical ASTs.
This is a compatibility argument for source testing, not qualification of actual
memory execution or either new runtime mode.

## Validation

| Check | Result |
| --- | --- |
| Initial current-tree run | 3 failed in 1.16 s; historical Engine pin refused fixture construction |
| First tmpfs reader run after new profile | 45 passed, 1 failed in 80.74 s; natural-failure fixture cursor mismatch |
| Corrected tmpfs reader/profile run | 56 passed in 102.03 s |
| Btrfs reader plus affected memory, recorder, Engine and artifact regressions | 482 passed, 14 dependency deprecation warnings, no skips; 482.55 s |
| Historical byte pins and requirements links after source commit `29b438e` | 19 passed in 0.72 s |

[Logs and source audit](memory-retained-condition-v1-2026-10-23/) retain the failures
and successful reruns. The Btrfs command used the canonical `scripts/run_tests.sh`
with a project-runs basetemp and the fourteen test files named in `checks.json`.
The tmpfs command used the same runner with a `/tmp` basetemp and the two new test
files. The new current-source tests are not added to the historical skip list.
Historical byte-pin checks and documentation links passed after committing the
source profile, because those pins must name bytes present in Git history.


The natural-failure fixture had computed total ticks from the advanced failure
cursor. It now derives the count from the last recorded row. Fixture support was
extended to all nine conditions with distinct controls and registrations; oracle
uses a real authored own-condition pair receipt from the same sealed source.
No production terminal rule was relaxed.

Source review found no blocking implementation issue and requested the oracle
coverage now included. Checks exercise expected-marker binding, early unqualified
refusal, aliases, changed receipts and compact bytes, raw residue, source/snapshot
identity, missing/cross-case prior-own evidence, mutation after pair proof, and
primary-error preservation. Neither a valid hash graph nor a qualification pin
can authenticate a fabricated historical execution: the expected commit must
come from the external audit/registration chain.

## Remaining gates

[The reader contract](../plans/memory-retained-condition-v1.md) grants no pruning,
model qualification, generated-family seed binding, scientific allocation or
case-publication authority. Whole-case validation/publication still needs held
custody through its atomic move; a returned reader dictionary is not that
capability. Oracle ordering, actual qualification and study evidence remain open.
The project goal and remote-main landing remain active.
