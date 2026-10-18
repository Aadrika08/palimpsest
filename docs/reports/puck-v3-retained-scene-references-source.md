# Retained puck scene references and selected-document custody

Continue PR #124 (`0b125ff`) with working retained parser, reference resolver
and selected JSON payload custody. Final source is
`7ae648eb30d870059fa0ff2ea5905acfa13cf2a4`.
Root focused checks: **216 passed in 0.38 seconds** (164 parser, 52 resolver).
Independent focused repetition: **216 passed in 0.38 seconds**.
Root final affected command: **848 passed, six explicitly deselected, 53.63 seconds**.
Independent final affected repetition: **848 passed, six deselected, 55.46 seconds**.
Independent SOURCE GO applies to the exact clean commit above after all review
fixes. No complete inventory or execution admission follows.

## Implemented working path

`parse_retained_puck_document` supports the six actual historical recording
manifest schemas, the actual teacher collector report fingerprint (which has no
schema field), and the two original/balanced training protocol schemas. It reads
caller bytes only, with no model/native/filesystem access. Strict duplicate-key,
nonfinite, structure, schema, field-path, reference and scalar/alias checks precede
its extraction receipt.

Scene seeds and splits come only from their typed writer paths. Model/training
seeds remain model identities. Top-level/row, collector source/owner/admission,
and embedded result row aliases must agree. Running, failed and not-started
records retain their scene mentions; nullable manifest pins retain references
and missing-pin pointers. Current world, final state and snapshot coordinates
are validated only within their genuine receipt paths, never promoted to authored
reset geometry. Unknown scene/geometry declarations, including camel-case and
punctuation aliases, fail outside the known paths. Explicit verified source-hash
map filenames remain receipts, not geometry declarations.

Historical manifests have no collision geometry hash. Their declared
`pushing_protocol_sha256` binds a catalog's raw bytes. Known source-hash catalog
receipts must include that pin when present; original base and active versioned
catalog hashes can legitimately differ in the same construction/source closure.
No highest-version guess, sibling hash substitution or inferred missing pin occurs.
Training source `source_hashes['manifest.json']`, when supplied with a non-null
manifest pin, must bind the same bytes. Null references remain null.

`resolve_retained_puck_documents` consumes registered typed byte views. Recording
source paths name directories, whose exact target is `<path>/manifest.json`;
collection-report paths already name files. Relative references need an explicit
recorded cwd for that source document. No process-cwd or report-directory default
is used. References bind target raw SHA, kind, scene seed/split and declared
catalog pin. Training protocols must match the pinned collection report's ordered
source scene/split/path/manifest-pin roster, as the real writer does.

Geometry comes only from the matching raw catalog SHA and exact seed/split row,
using the existing historical parser's genuine canonical/scientific/payload
hash domains. A training source without its own catalog pin follows its pinned
manifest; a supplied catalog pin is enforced. All authentic identity variants,
occurrences, catalog paths and pointers remain in the result. A contradictory
reference becomes unresolved while independently supplied variants are preserved.
Missing pins, catalogs, targets, origins or geometry never silently become empty
history. Legacy row uniqueness incompatibilities remain explicit.

`HeldRetainedPuckDocuments` reuses `HeldCollectionFiles` under a canonical,
externally SHA-bound JSON registration. It holds no-follow selected file/ancestor
custody through reads, parsing, resolution, rechecks, snapshot copying and close.
Drift, links/aliases, namespace changes, expiry and lifecycle failures poison
and close the context. Caught payload failures cannot produce a successful
nominal close. Body failures remain primary with final drift/close/deadline notes.
No descriptor or file-path escape API is added.

## Scope, source ceilings and incomplete coverage

Selected-file authentication does not prove that registration covers all files,
roots, repositories, histories, schemas or references on the machine. Pure byte
views do not authenticate source attachment. `declared_reference_closure_resolved`
concerns exactly the supplied typed document set and its recorded references,
not complete collision inventory. Every whole-inventory/source-closure/
reservation/collection/executable grant remains false, with empty qualification
claims. The held facade states only that registered document bytes are currently
authenticated. Catalog-coordinate exposure is reported separately from runtime
held-out access; no actual catalog or held-out runtime input was opened.

Source ceilings within the future registry stage: 4 MiB JSON documents;
512 selected files, 32 nonoverlapping roots, 64 MiB aggregate selected input and
output metadata; 4096 reference/variant rows; 65,536 occurrences; an absolute
monotonic deadline at most 600 seconds ahead. The per-document parser caps
65,536 nodes, depth 32 and 4096 combined mentions/references. The registration
itself is bounded to 1 MiB. Receipt prefixes and snapshot/recheck/close costs stay
inside the same source caps/deadline. These are operational failure ceilings,
not extra execution budgets, atomic filesystem guarantees, hostile-process
isolation or a hard RSS/WCET proof.

Unsupported families still stop explicitly: standalone mechanics/development/
owner/training-result reports, prepared outputs, model indexes, on-policy
registries/publication records, general Markdown and source/reference families
outside these kinds. Unknown model-seed array declarations in copied training
learning metadata fail closed; compatibility with every real historical input
is unqualified because actual protocol/catalog files were not scanned. Complete
schema dispatch, retained/project scope and aggregation remain required.

## Verification and review fixes

Authored tests use bounded JSON bytes and real temporary selected files. No
actual retained registry, project catalog, original checkpoint, model, minter,
native owner, collection, fitting, development or held-out stage ran.
Source tests may repeat; no consumed frozen qualification was rerun.

Initial resolver RED: **28 missing-feature assertion failures**. Parser's initial
missing-module RED was a collection import error; subsequent behavioral REDs
preceded its guard fixes. Resolver guards then exposed recorded-root-cwd rejection,
failed nominal close and an unbounded receipt prefix: **three failed, 45 passed**,
followed by the fixes. Initial combined source was **196 passed**, and the initial
affected command was **828 passed, six deselected, 53.98 seconds**.

Independent source inspection nevertheless found four concrete missing contracts:
report/manifests with conflicting catalog pins, training/report source roster
mismatches, contradictory training manifest receipts, and hidden geometry field
aliases. Authored regressions reproduced each; they were fixed before final
review. Root's additional explicit-training-catalog-pin regression failed before
its correction. Passing initial checks were not treated as proof against these
findings. The final 216 new checks and 848 affected checks include those regressions.

The six inherited baseline exclusions remain unchanged and are documented with
unchanged-base reproduction in the
[launcher report](puck-v3-collection-launcher-source.md): three historical-profile
pin mismatches and three missing-httpx mechanics cases. The bounded default
repository command stops at `tests/test_lab.py` collection, missing FastAPI:
**exit 1, one error, 0.31 seconds**. No full-suite pass is claimed. PR #124's earlier
intermittent terminal-model failure remains preserved in its
[root/occurrence report](puck-v3-inventory-roots-source.md); its cause was not
established or attributed to these changes.

Exact affected command (18 files, same six inherited exclusions):

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
  /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
  -m pytest -q --tb=short \
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

## Required next work

Complete other retained/raw-registry/Markdown/reference families and matching
repository/root scope, then aggregate every authentic occurrence and historical
variant without bypassing the old uniqueness conflict. Bind source/transport/
runtime/dependencies, exact stage invocation, durable attempt/reservation,
one-owner lease and process/storage/clock/owner-close evidence into the working
launcher. Actual inventory, scene mint and collection need their separate exact
admissions and the pending catalog-access decision.

Memory qualification attempt-02 remains pending its own approval. Navigation
attempt 3 remains unauthorized. Preserve all original protocols, hashes, task
thresholds and consumed failures. All seven simulation release gates remain open;
CI and physical rover work remain outside this source wave.
