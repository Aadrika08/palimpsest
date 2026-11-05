# Retained case semantic core: source verification

This source slice extracts explicit `staged` / `published` semantic reading.
Public staged entry points retain their signatures and reject final aliases.
The private published core requires three externally expected case-file descriptors,
checks their combined 32 MiB allowance, holds the exact final subtree, and derives
all retained source/condition/cell semantics again. It does not authenticate the
future manifest/close/commit chain or accept an execution-order attestation.
Those are separate public-reader/publication tasks; no public final-path admission
route is introduced here.

## Verification and acceptance boundary

Normal canonical selected commands now run without an external plugin flag:

- `scripts/run_tests.sh --` with the eight retained/source/seal/pair/custody
  modules: **209 passed, 186 skipped**, exit 0, 291.99 seconds. These are source
  checks, not full qualification. `canonical-selected.log` and
  `canonical-verification.json` retain the actual command, environment and hashes.
- `scripts/run_tests.sh -- tests/test_memory_publication_current_semantics_v1.py`:
  **63 passed, zero skipped**, exit 0, 90.62 seconds. NEW node IDs deliberately
  reuse unchanged prior assertion functions/parameter matrices against declared
  current-source authored profiles. `current-semantics.log` and its verification
  JSON retain the actual command and result.
- The collection-only audit records all **395 selected node IDs** and the exact
  **186 historical frozen-pin skips** in `historical-skip-nodeids.json`. Neither
  the old node IDs nor `tests/frozen_pins.py` were changed. The skips are historical
  source-drift policy, not evidence of successful execution of those old cases.

`tests/memory_publication_authored_profiles.py` is the explicit test-owned
prospective-profile fixture. Seven affected test modules opt in by importing
that fixture. It copies structural profiles and binds their declared behavior
identities to current bytes in ephemeral authored profile files; it changes no
historical JSON. The oracle module's current-semantic profile object and path
refer to the same authored file. Raw-auditor subprocesses receive that exact
fixture profile. No qualification or execution pin is populated by this helper.

The original Task2 module separately tests an unpatched subprocess explicitly
selecting the old profile and refusing changed behavior, plus byte identity of
that historical profile. `historical-profile-readback.json` independently checks
both original compact and condition-seal JSONs byte-for-byte against `dbadf42`.

These results are authored current-profile **semantic software regressions**.
They are not historical-profile acceptance, genuine observer/model qualification,
actual study evidence, pruning authority or scientific/capability acceptance.
No public final-path admission API is added; accepted case publication and the
manifest/close/commit authority chain remain later tasks.

The earlier `memory_publication_profile_plugin.py`, `regression.log`, and
`verification.json` preserve the failed external-plugin experiment: 150 passed,
103 skipped, one historical-path assertion failed before the tail was reached.
That experiment is superseded for the ordinary selected-command gate by the
explicit owned-fixture results above. Its 103 skips were a partial run; the final
186 skip list was independently collected. Nothing in the old log is relabeled
as passing, and no coverage is inferred for unexecuted historical cases.

Parent independent focused verification also passed **3 checks** in 18.85 seconds: published/staged semantic equality, unpatched historical behavior refusal and historical JSON identity. Its command, output and five source hashes are retained in `parent-focused.log` and `parent-verification.json`.

## Preserved development outcomes

- Initial paired test failed because `_read_retained_case` did not exist.
- The first post-extraction run correctly refused historical behavior identities.
- An initial function-scoped test plugin did not precede existing module fixtures;
  the explicit harness was corrected to module scope.
- A broader run passed 131 cases before detecting that staged retained reading
  bypassed its existing public pair-admitter hook. Restoring that route made all
  five existing post-pair custody-mutation tests pass. Published reading alone
  uses the new private location-aware pair helper.

No historical measurements, profiles, allocations, thresholds, held-out locks or
accepted qualification pins were changed. No native model/physics owner was run.
