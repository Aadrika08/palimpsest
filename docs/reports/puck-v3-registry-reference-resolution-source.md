# Puck registry declarations and reference resolution: source evidence

This slice continues PR #125 (`07f6450`) with six pure on-policy JSON families
and their selected-document dependencies. It does not complete project inventory,
reservation admission, worker bootstrap, collection, capability qualification or
any simulation release gate. No actual catalogs, retained roots, reservation,
minter, publisher, original model inference, native owner, collection, fitting or
evaluation was invoked. Tests use authored bytes, synthetic CPU/native fixtures
in inherited source checks, and temporary files.

## Working behavior

`parse_puck_registry_document` supports inventory, reservation, scene manifest,
collection projection, publication commit and publication admission. It validates
canonical JSON, duplicate/nonfinite/type aliases, exact schema/roster/lineage,
geometry hash domains, ordered splits, cross-entry collisions and bounded input.
Only supplied layouts have recomputed geometry identities. Prior inventory hashes
remain unbound declarations; historical self-reservation nulls remain unminted.
Metadata cannot hide additional scene or geometry declarations, including nested
and camel/punctuation aliases. Unrelated numeric counters remain valid.

`resolve_puck_registry_documents` verifies dependency byte hashes and kinds,
scene/reservation collision binding, publication target content and byte lengths,
and admission/commit agreement. Local publication names use the document's
parent directory. Content-digest links preserve every identical-content location.
Missing or conflicting evidence remains explicit. It retains variants and every
occurrence without selecting an arbitrary copied location.

The historical resolver and `HeldRetainedPuckDocuments` now accept these families.
Mixed resolution shares total input, reference, occurrence, variant, output and
absolute deadline ceilings. Every unresolved mention, bare hash declaration and
unminted reservation consumes the occurrence budget. The held facade proves only
the registered selected bytes while active. Supplied publication stat tuples are
historical declarations; they are never authenticated filesystem observations.

All inventory/source-closure/reservation/collection/executable grants stay false.
Resolving the selected declared registry edges does not establish full discovery,
current allocation identity, loaded runtime/code proof or authority to execute.
A standalone projection has no invented parent reservation dependency.

## Review and verification

Plan and missing-feature RED tests: `1f14c5e`. Codec API RED: one failure, then
136 missing-API failures before implementation. Root resolver RED: 20 missing-API
failures; the first implementation run also lacked the not-yet-delivered codec.
Initial delivered codec: 143 passing checks. Integrated slice: 166 passing checks
in 0.52 seconds, after three meaningful mixed-budget REDs were fixed. The first
reference-budget fixture used five rather than the actual six registry edges and
failed its precondition; correcting it produced the intended missing-refusal RED.

Independent review found scene declarations hidden in arbitrary inventory metadata.
Root's first regression invocation had a test helper NameError; corrected tests
produced all 16 intended missing-refusal REDs. Recursive typed-declaration rejection
then passed the final focused 182 checks in 0.54 seconds. Independent exact-source
review of `1a93ac8890c04d375cb3073fe09c579929f7a0cb` repeated 182 in 0.56 seconds
and found no remaining concrete source defect. This is source review only.

A pre-fix affected run passed 1014 checks with six inherited exclusions in 53.84
seconds. Final root affected verification passed **1030 checks, six deselected, in
54.64 seconds** on exact source `1a93ac8`. Independent affected repetition passed **1030 checks, six deselected, in
53.79 seconds**; exact-source SOURCE GO applies to `1a93ac8`. Source and focused
test bytes were unchanged after the independent run. The default bounded repository command stopped during test collection:
missing FastAPI in `tests/test_lab.py`, one error in 0.36 seconds. No full-suite
pass is claimed. The six mechanics exclusions are unchanged from PR #122/#125:
three historical construction-pin expectations and three missing-httpx cases,
reproduced on the unchanged earlier base. They were not repaired or reclassified.
PR #124's historical terminal-model anomaly remains in its original report; its
cause is unknown and this slice makes no production fix claim for it.

Exact final source commands use Python 3.11.15 in the existing R0 environment:

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
  /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
  -m pytest -q --tb=short \
  tests/test_puck_scene_registry.py tests/test_puck_registry_reference_resolution.py \
  tests/test_puck_scene_retained.py tests/test_puck_scene_reference_resolution.py \
  tests/test_puck_scene_roots.py tests/test_puck_scene_occurrences.py \
  tests/test_puck_scene_catalog.py tests/test_puck_scene_git.py \
  tests/test_puck_custodied_native.py tests/test_puck_collection_ledger.py \
  tests/test_puck_execution.py tests/test_puck_execution_files.py \
  tests/test_puck_collection_admission.py tests/test_puck_bundle_provenance.py \
  tests/test_puck_on_policy.py tests/test_puck_on_policy_interval.py \
  tests/test_puck_on_policy_native_interval.py \
  tests/test_puck_original_bundle_qualification.py tests/test_bounded_qualification.py \
  tests/test_puck_mechanics.py \
  -k 'not (first_supervisor_exception or historical_construction_pin or progress_timeout or receipt_before_next or startup_timeout or v5_mechanics)'
```

## Next source exit and release boundary

Complete standalone owner/development/mechanics/training-result/prepared/model
index families, Markdown references and declared repository/root scope. Aggregate
all authentic occurrences and legacy-schema conflicts into complete semantic
inventory, then feed collision/reservation checks and the fresh-worker/durable
collection launcher. These selected parsers are prerequisites, not that exit.

Memory amendment 02, mixed-catalog access and the prospective navigation study
remain separate pending decisions. Disk cleanup supplies capacity only. No memory
attempt 02 or navigation attempt 3 ran. CI and physical rover remain excluded;
all seven simulation release gates remain open.
