# Puck inventory roots implementation plan

Continue the approved [simulation execution goal](https://github.com/Aadrika08/palimpsest/blob/research/simulation-completion-next/docs/plans/simulation-release-execution-goal.md)
from PR #123 (`ef44ce8`). This source unit fills the filesystem root-discovery
portion of the complete inventory-to-collection path. It does not authorize a
real scan or replace semantic closure, collision admission or the full launcher.

## Interface and search contract

Create `src/palimpsest/puck_scene_roots.py` and
`tests/test_puck_scene_roots.py`. Implement:

```python
with HeldSceneInventoryRoots(contract_raw, expected_sha256=external_sha,
                             deadline=absolute_monotonic_deadline) as sources:
    receipt = sources.snapshot()
    sources.recheck()
```

The strict hash-bound JSON contract has exactly `id`, `version`, `search_roots`
and `opaque_subtrees`: ID `puck-scene-root-search-v1`, version integer 1,
nonoverlapping canonical absolute search directories, and explicit existing
opaque subdirectories with a bounded reason. No implicit dependency or evidence
exclusions. Every exclusion is reported and leaves whole-inventory completeness
false. The caller must separately review coverage and supply any excluded-scope
projections. This is not a proof that unlisted external roots do not exist.

Hold ancestor and discovered directory edges with no-follow descriptors.
Observe directory entries and leaf metadata, never leaf payloads or Git commands.
Discover `.git` directory/file repository candidates, including independent
nested repositories and linked-worktree markers. Treat Git control storage as an
explicitly reported automatic opaque scope; authenticate it later through the
existing `HeldGitSceneSources` path. Retained-root names and manifest/registry/
reservation/index filenames are candidate hints only, not schema admission.

Snapshot/recheck/normal close must reject changed namespaces, directory edges,
aliases, symlinks and special entries outside opaque scopes. Metadata does not
establish payload authenticity. Opaque scope contents are not observed or
qualified. Body exceptions remain primary, with final drift/cleanup failures in
notes; failed contexts cannot resume or leak descriptors.

## Bounded implementation and verification

- [ ] Write real temporary-forest tests for root/retained candidates, linked Git
  markers, explicit exclusions, no leaf opens, malformed/ambiguous contracts,
  namespace/edge changes, failure poisoning, descriptor cleanup and deadlines.
  Watch the missing-feature RED before implementing the API.
- [ ] Implement the held discovery component. Fixed source ceilings: 64 KiB
  contract, 32 search roots, 1024 declared opaque subtrees, depth 32, 8192 held
  directories, 65,536 observed entries and 64 MiB receipt/metadata. Deadline no
  later than 600 seconds ahead. These are failure ceilings within the existing
  registry stage, not additional execution/resource grants.
- [ ] Review and verify the source unit and inherited Git/catalog/collection
  checks. Record broad-suite failures and exclusions honestly. Independently
  review the exact commit before publication.
- [ ] Commit/push a stacked draft PR and measured source report; update goal and
  matrix without changing the seven release gates. Continue typed semantic
  assembly, runtime bootstrap and the full durable launcher.

Every receipt keeps `inventory_complete`, `all_repositories_discovered`,
`retained_roots_discovered`, `executable`, `native_authorized` and
`collection_authorized` false, with empty `qualification_claims`.
No actual retained root, project observer, catalog/parser, registry/reservation,
model, native owner, physics, collection, fit, development or held-out path is
opened by this unit. Memory attempt-02 and catalog access remain pending their
separate decisions. Navigation attempt 3, CI and physical rover remain excluded.

## Catalog occurrence assembly in the same source wave

Extend `puck_scene_catalog.py` with
`assemble_task_catalog_occurrences(documents, *, deadline)`; cover it in
`tests/test_puck_scene_occurrences.py`. Documents carry exact repository,
object-format, commit/root-tree/path/OID/mode descriptors plus caller bytes.
Validate framed Git blob OIDs and raw SHA256 separately, parse the supported
catalog, then group exact `(scene_id, canonical_scene_sha256,
scientific_initial_sha256, payload_sha256)` tuples. Retain every distinct
repository/commit/tree/path/OID/pointer occurrence and reject conflicting or
repeated commit/path declarations. Sort output deterministically.

Report all same-ID variants and per-domain hash aliases. The narrowly named
`legacy_scene_rows_compatible` tests the old global identity-row uniqueness,
not root/record completeness, schema admission or source authentication. Caller
commit/tree descriptors do not authenticate attachment. No reservation-ready
snapshot or complete flag is emitted. Unsupported documents fail rather than
become empty scene catalogs. Markdown/reference/raw-registry parsing and full
retained-file custody remain required for the complete inventory path.

Bound 4096 documents/variants, 65,536 scene occurrences, 32 MiB total input bytes
and 64 MiB retained output metadata, under the same absolute deadline. These
source failure ceilings do not expand the actual stage's fixed allocation.
Actual catalogs remain behind the pending access choice.
