# Retained puck report families: source evidence

Eight additional explicit document kinds now connect source-shaped retained
metadata to selected JSON custody: owner_result, construction_result,
mechanics_report, construction_report, development_report, training_report,
prepared_training and model_index. Base PR #126 is `9ebb791`; independent source
review applies to exact `0c2a1b57c5f11cc1fa1b1f1f9eecb361064b1f51`.

This is source verification on authored JSON bytes and temporary files. No actual
catalog/registry/retained-root scan, reservation, mint, publisher, original-model
inference, native owner, collection, training, evaluation or qualification CLI was
invoked. Inherited source tests use synthetic CPU/native fixtures and existing
metadata fixtures; they do not establish new scientific or capability evidence.
All seven simulation gates and full inventory/worker/launcher admission stay open.

## Working path

Pure codecs reuse the existing bounded `_Inventory` contracts. They retain failed,
running, unstarted and partially populated records. Model/training/RNG seeds stay
separate from scenes. Snapshots, final world/task state and binary checkpoint/SNP
receipts are declarations; they are never promoted to authored reset layouts,
current file custody, model acceptance or numerical replay proof.

Report-owned JSON references use declared owner output paths. Baseline dependencies
verify owner ID/model21 and the declared initial snapshot hash, without opening SNP
bytes. Standalone baseline results lacking declared path context remain explicitly
incomplete. No process cwd or relocation silently supplies historical context.
Mechanics catalog identity follows its explicit embedded pushing pin, not the
verifier hash. Development reports have no top-level catalog pin; genuine result/
manifest references or exact embedded student-result pins can bind their rows.
Different referenced catalogs/identities remain conflicts rather than an arbitrary
selected proof. Catalog copies and every authentic occurrence remain retained.

Training report ledgers bind protocol.json in the document directory, checking SHA,
byte length, model seed and balanced objective. Prepared wrappers verify the exact
canonical embedded protocol and preserve prefixed source mentions/references.
Model-index directories use an explicitly declared historical cwd. The index's
protocol/checkpoint declarations agree with the referenced training report ledger;
checkpoint payload authentication remains outside this JSON resolver.

The resolver checks full owner rows, embedded result content, parent/child catalog
pins and model-identity hashes in both owner results and recording manifests.
Expected identity fields missing from an embedded student result remain missing
pins. Exact retained file-receipt maps validate relative paths/hashes/byte lengths;
only file-name keys receive the scoped declaration exemption. Metadata cannot hide
additional scene geometry beneath that exemption.

Existing selected JSON custody, shared byte/reference/occurrence/variant/node/depth
bounds and one absolute <=600-second deadline remain in force. Authenticated
selected bytes while held do not prove complete project discovery, loaded source/
runtime attachment, current allocation or permission to execute. Every inventory,
source-closure, reservation, collection and executable grant remains false.

## Review fixes and verification

`cbf869f` records the plan and initial training API RED: 36 missing-API failures in
0.19 seconds. Owner/report API RED: 24 missing-API failures; an earlier system
Python run stopped pre-collection at missing Pygments. Training implementation
first passed 36 checks in 0.06 seconds; report codec reached 35 checks after its
context regressions. Resolver feature RED: eight unsupported-kind/custody failures
in 0.21 seconds. Source implementation was committed at `c5cd57b`.

Additional REDs exposed missing row/content/catalog comparisons, source-shaped
catalogless development rows and result-only/embedded geometry paths. The initial
development fixture used scene6000 with closed_loop_dev, violating the historical
catalog's split range; correcting it to scene6100 exposed the four intended missing
refusals. A baseline fixture first used an incorrect sibling output spelling,
producing unregistered_target; correcting the declared owner directory verified
the snapshot comparison. Both fixture corrections are retained in the work history.

Independent review found four consistency defects: report/manifest model rows;
explicit parent versus external child catalog pins; index/checkpoint ledger pins;
and report versus embedded student model hashes. All four intended REDs reproduced
before correction. The balanced objective candidate also reproduced two failures.
A second review found the manifest model-hash counterpart; its single RED reproduced
before correction. Source-shaped retained file-name maps reproduced two false
rejections plus one accepted invalid path, then passed strict map validation.
An unhashable kind alias reproduced TypeError and now receives explicit ValueError.
Fix commits are `8032c36` and `0c2a1b5`. No custody guard or qualification threshold
was relaxed.

Final root focused verification: **154 passed in 0.27 seconds** (new three files plus
52 existing resolver checks). Independent new three files: **102 passed in 0.21
seconds**. Final serialized affected verification: **1132 passed, six deselected,
53.48 seconds root / 53.75 seconds independent**, exit0. Independent review found
no remaining concrete source defect within the inspected source/authored scope.

Preserved intermediate broad results:

- 1093 passed / 25 source-inventory failures / six deselected in 54.49 seconds.
  A generated src/palimpsest/__pycache__/__init__.cpython-311.pyc (283 bytes,
  SHA256 007139ec0efdc4d782508a925a528b26551b2c5c8fb4d2e08738b835313589e7)
  caused the expected frozen-source discovery refusal. That generated file and its
  empty cache directory were removed; source discovery checks then passed.
- 1130 passed / one inherited authored custody failure / six deselected in 53.65
  seconds. The failure was Collection root or ancestor changed while held during
  test_custodied_native_interval_on_authored_inputs[success]. Its exact changing
  directory/cause was not captured. Concurrent fixture/temp activity is plausible,
  not established. The same case passed alone in 1.46 seconds, and both final
  serialized broad runs passed. No production fix is claimed for this anomaly.
- Default bounded pytest stopped during tests/test_lab.py collection: missing
  FastAPI, one error in 0.32 seconds. No full-repository-suite pass is claimed.

The six mechanics exclusions are unchanged from the independently reproduced
PR #122/#125/#126 baseline: three construction-pin expectations and three
missing-httpx cases. PR #124's earlier terminal-model anomaly remains in its own
report with cause unknown. No experiment was retried from these source tests.

Exact final affected command:

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
  /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
  -m pytest -q --tb=short \
  tests/test_puck_scene_reports.py tests/test_puck_scene_training.py \
  tests/test_puck_report_family_resolution.py \
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

## Remaining full milestone

Complete Markdown/reference parsing, declared project/repository/retained-root scope
aggregation and semantic inventory admission. Registered historical context and
unsupported embedded protocol variants must remain explicit failures, not omitted
coverage. Then connect collision/reservation checks, fresh-worker source/runtime/
dependencies, exact invocation, model/scene custody, lease/process supervision and
durable terminal publication into the complete launcher.

Memory amendment02 approval, mixed-catalog access and a prospective navigation study
remain pending. Approximately 93.1 GiB free was observed at 14 October 22:25 UTC;
capacity and original input presence must be rechecked immediately before admitted
stages. Clearing space grants no consumed retry. CI and physical rover stay excluded;
all seven simulation release gates remain open.
