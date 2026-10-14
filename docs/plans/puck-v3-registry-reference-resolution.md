# Puck registry reference implementation plan

Continue the approved simulation execution goal from PR #125 (`07f6450`).
Complete the on-policy inventory/reservation/scene/projection/publication JSON
families and connect them to selected-document custody. All remaining report,
Markdown, project/root aggregation and runtime/launcher admissions stay required.

## Components and interfaces

Create `puck_scene_registry.py` with pure
`parse_puck_registry_document(raw, *, kind)`. Explicit kinds cover the on-policy
inventory, reservation, scene manifest, collection projection, publication commit
and publication admission. Reuse existing pure on-policy shape/hash validators.
Preserve prior identity assertions and intentional unminted self-reservation
nulls; only scene entries with exact layouts can have recomputed identity binding.
Stored file-stat tuples are historical declarations, not current filesystem proof.

Extend `puck_scene_reference_resolution.py` with
`resolve_puck_registry_documents(documents, *, deadline)` and dispatch these kinds
through `resolve_retained_puck_documents` and `HeldRetainedPuckDocuments`.
Verify raw SHA and target kind for every reference. Publication target/receipt
names are relative to the document directory; scene manifests bind reservation
bytes by content digest. Preserve every identical-content location and occurrence,
never manufacture a path or choose an arbitrary authentic source. Bind scene
manifests to reservations using existing pure validation, commit receipts to their
actual target bytes/size/lineage and admission records to their target plus commit.
A naked prior hash claim remains unbound unless separate authentic layout evidence
binds it; never mark complete collision admission from a syntactically valid row.

Keep verified layout variants, unbound scene declarations and intentional unminted
reservations distinct, all with provenance. No inventory role is silently promoted
to the current allocation's self-reservation. Aggregate old/new diagnostic output
within the same selected input/output/clock ceilings; no discovery or numerical
authority follows from resolving selected references.

## Steps and verification

- [x] Write missing-feature RED tests on authored canonical inventory/reservation/
  scene/projection/receipt bytes and real temporary selected files. No actual
  registry, minter, publication writer or model/native owner is invoked.
- [x] Implement strict registry codec and integrated pinned reference resolution.
  Exercise changed layout/hash/roster, missing/wrong dependencies, local-target
  aliases, size/lineage/receipt mismatches, copied content paths, null assertions,
  mixed historical/registry inputs and selected-file drift/cleanup.
- [x] Independently review exact source and repeat affected tests. Retain any
  intermediate failures, default-suite errors and inherited exclusions.
- [x] Commit/push a stacked draft PR and report; update goal/matrix without closing
  any of the seven simulation release gates.

Limits remain source failure ceilings within the unchanged registry stage:
4 MiB per JSON; 512 selected files; 32 registered roots; 64 MiB aggregate input
and output metadata; depth 32 and 65,536 JSON nodes; 4096 scenes/references/variants
per applicable phase and 65,536 occurrences; absolute deadline at most 600 seconds
from construction. Component work shares those limits rather than borrowing time.
Pure inputs do not prove source/runtime attachment or full project/root coverage.

No actual project/catalog/retained scan, reservation/mint/publication stage,
original model inference, native owner, collection, fitting or evaluation runs.
Memory attempt-02 and catalog access remain pending; navigation attempt3 remains
unauthorized. Preserve original hashes/thresholds and consumed failures. CI and
physical rover remain excluded; all seven simulation release gates stay open.

## Delivery

Draft PR #126 stacks on PR #125. Source GO applies to exact `1a93ac8`;
182 focused and 1030 affected checks pass independently, with six inherited
exclusions. The source report records exact results and retained failures.
Goal PR #94 and evidence-matrix PR #102 carry the updated continuation goal.
No actual-input execution or release gate is granted by this source delivery.
