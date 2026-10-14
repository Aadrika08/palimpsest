# Retained puck scene reference implementation plan

Continue the approved simulation execution goal from PR #124 (`0b125ff`).
Root discovery and catalog occurrence assembly are working source components;
complete retained/reference/Markdown dispatch, scope aggregation and executable
stage admission remain required. This wave connects actual retained writer shapes
to genuinely hash-bound catalog identities using authored inputs only.

## Working path

Explicit typed retained-document parser -> registered reference target/hash
resolution -> exact catalog seed/split selection -> variant/occurrence diagnostics.
Then reuse `HeldCollectionFiles` for a hash-bound registration of selected JSON
inputs, keeping actual payload custody active through parsing/resolution/recheck.
No new generic native loop, filesystem holder or scene hash domain is introduced.

## Interfaces

Create `puck_scene_retained.py` with
`parse_retained_puck_document(raw, *, kind)`. Kinds are `recording_manifest`,
`teacher_collection_report`, and `training_protocol`. Recognize literal writer
schemas/fingerprints from `verify_puck_mechanics`, `collect_puck_teachers` and
`train_puck`; distinguish scene seeds from model/training seeds. Preserve
running/failed/not-started scene mentions, null pins, typed pointer provenance
and unresolved references. Recording source paths name directories; the target
is `<path>/manifest.json`. Collection-report paths already name files. Current
world/snapshot geometry is not an authored reset identity.

Create `puck_scene_reference_resolution.py` with
`resolve_retained_puck_documents(documents, *, deadline, origins=None)`.
Each document has exactly `path`, `kind`, `raw`; `task_catalog` joins the three
retained kinds. Origins explicitly bind a relative reference's recorded cwd;
never use the process's current cwd or the report's directory by default.
Authenticate target bytes against the exact reference SHA and kind before
following them. Select catalog rows only by exact raw catalog SHA plus genuine
scene seed/split, through the existing historical catalog parser. Preserve every
four-identity variant and document/pointer/catalog occurrence. Missing pins,
targets, catalogs and conflicting fields remain explicit incomplete findings.
Do not substitute owner/model/snapshot/row hashes for geometry identities.

Add `HeldRetainedPuckDocuments(registration_raw, *, expected_sha256, deadline)`
in the resolver module. Its context reuses existing descriptor-held file custody
for explicitly registered bounded JSON documents, handles drift/failure/close,
and returns independently copied resolution receipts while custody remains
active. Selected-document authentication is not declared-root completeness,
loaded source/runtime admission or permission to reserve/execute.

## Verification and delivery

- [ ] Write failing authored tests for genuine manifest/report/training shapes,
  redundant identity conflicts, failed/null-pin records, exact reference path
  semantics, unrecognized declarations and finite structure bounds.
- [ ] Implement parser and pure resolver; test real temporary file custody,
  wrong/missing target pins, unavailable catalog geometry, explicit origins,
  alias/drift poisoning, copied receipts and exception continuity.
- [ ] Independently review exact source and run affected inherited checks;
  retain full-suite failures, exclusions and any intermediate failed checks.
- [ ] Commit/push a stacked draft PR and source report; update the active goal
  and requirement matrix without promoting the seven release gates.

Source ceilings remain inside the existing registry allocation: 4 MiB per
JSON document, 512 registered documents, 64 MiB aggregate input/output metadata,
32 roots, depth 32 for parsed JSON, 4096 resolved variants/references and 65,536
occurrences, under an absolute monotonic deadline at most 600 seconds ahead.
Per-parser ceilings may be smaller; a cap failure stops, never expands allocation.

Caller descriptors do not prove source attachment, project/retained scope or
reference completeness beyond the supplied set. Every receipt denies complete
inventory, reservation, collection and executable admission and has no
qualification claim. No actual project/catalog/retained scan, model/native/study
stage, memory attempt-02, navigation retry, CI or physical rover runs in this
wave. Pending catalog-access and consumed-attempt decisions remain unchanged.
