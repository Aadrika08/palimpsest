# Bounded HTML Comparison Compaction Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans task-by-task. This is an unapproved proposal; do not execute the material allocation until the owner explicitly approves its frozen scope.

**Goal:** Export the existing long recorded comparison within unchanged byte caps by referencing its complete raw event streams instead of embedding repeated inspector payloads.

**Architecture:** Change only the offline HTML presentation in `src/palimpsest/comparison.py`. Preserve `artifacts.compare_runs`, JSON CLI/API responses, every route point/world/provenance/metric, authoritative recordings and the already supplied input ZIP. Reuse the existing validated source ledger and Python stdlib; no new dependencies or generic serializer.

**Tech Stack:** Python 3.11, stdlib JSON/XML/hashlib, existing NumPy-backed recording readers and unittest fixtures.

**Spec:** Existing `docs/plans/artwork-material-v2.md` plus the failed material-v2 receipt at producer `014e1c0`; root's next scope must freeze this proposal prospectively. Both material v2 and manual lab v2 are consumed failures, immutable and unpromoted.

## Global Constraints

- Keep `comparison.MAX_METADATA_BYTES = 4 * 1024**2` and `MAX_HTML_BYTES = 16 * 1024**2`.
- Keep raw source validation, event/run identity checks, exact coordinates, common projection, secret refusal, exclusive publication, source drift checks and storage enforcement.
- Source archive remains the existing 577,247,342-byte, 98-input ZIP, SHA256 `80251ccd5889ce01ac2cf447f7ff591848be69b3d5fb38a70ec6ef55c7708aed`; do not recreate or modify it.
- No scientific, biological, artistic adequacy, human/operator, sustained Afterimage or physical qualification follows from compact HTML or a later material pass.

## Review Focus

1. Repeated inspector events must not inflate HTML or silently disappear: exact raw stream identities/counts and an explicit payload-reference label remain.
2. Credentials in omitted event payloads must still reject publication before any output file is reserved.
3. Route/world geometry must remain exact, including distinct starts/episodes and coincident routes.
4. Shared JSON/API comparisons must retain their event arrays; only HTML uses the presentation projection.
5. Compact provenance can still exceed the unchanged caps: reject oversized outputs, source drift and existing destinations.

## Task 1: HTML-only event references, software checks and review

**Modify:** `src/palimpsest/comparison.py:100-144,147-189`.
**Tests:** `tests/test_comparison.py`, reusing its existing recording fixtures/parser; preserve `tests/test_artifacts.py` coverage of shared comparisons.
**Interface:** `export_comparison(left_path, right_path, output_path, *, storage_budget=None)` is unchanged. The HTML metadata declares a new rendering version and an `event_stream` descriptor on each side; shared `compare_runs()` returns its original schema.

- [ ] Add a failing synthetic test with repeated, realistic `memory_inspected` payloads large enough that the original compact report exceeds 4 MiB. Use temporary recordings and matching generated IDs; do not read retained study data or launch an exporter phase. Confirm refusal is the original metadata-cap error.
- [ ] In `export_comparison`, validate the full raw manifests/events and original report with `_no_secrets` before the projection. Retain existing event identity checks. Replace only each HTML-side `events` array with a descriptor computed from the validated input and existing `_sources` ledger:

```python
from collections import Counter

run_id = item['manifest']['run_id']
side_events = report[key].pop('events')
event_file = next(row for row in _sources(item)['files']
                  if row['path'] == 'recording/events.jsonl')
report[key]['event_stream'] = {
    'path': f'runs/{run_id}/recording/events.jsonl',
    'size_bytes': event_file['size_bytes'],
    'sha256': event_file['sha256'],
    'total_event_count': len(item['events']),
    'visible_event_count': len(side_events),
    'visible_kind_counts': dict(sorted(Counter(e['kind'] for e in side_events).items())),
    'payloads_embedded': False,
}
```

  The path identifies the unchanged member in the supplied input ZIP, not an arbitrary filesystem URL. Keep complete source ledgers and all remaining comparison fields. Do not sample, truncate or deduplicate recorded routes/events in their authoritative files. Avoid mutating cached reader data or shared API reports.
- [ ] Replace the HTML's “Full recorded comparison” wording with “Comparison summary and source provenance”; explicitly state that full event payloads are in the supplied source archive and give both member paths, hashes, byte sizes and counts. Retain privacy/causality limitations and no script/network dependency. Keep the existing metadata and total-HTML caps after projection.
- [ ] Pin meaningful assertions in the synthetic tests:

```python
assert meta['comparison']['left']['traces'] == full_report['left']['traces']
assert meta['comparison']['left']['worlds'] == full_report['left']['worlds']
assert stream['sha256'] == hashlib.sha256(events_path.read_bytes()).hexdigest()
assert stream['visible_event_count'] == len(full_report['left']['events'])
assert artifacts.compare_runs(left, right)['left']['events'] == full_report['left']['events']
```

  Assert total counts/counts by kind and size against original bytes; metadata has no embedded event payload arrays. Compare the actual three SVG views' coordinates/world shapes with the exact source traces/worlds. Include a secret in a payload that compaction omits, an oversized non-event provenance field, source-drift refusal and exclusive-output preservation. Reuse the existing parser and geometry checks.
- [ ] Run the focused software checks once per needed red/green change: `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts /home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python -B -m unittest discover -s tests -p test_comparison.py`, then the affected artifact tests. Retain actual outcomes; these fixtures are software evidence only. Request independent review, freeze verified source/control/runtime identities and commit the narrow change through the existing branch workflow before any new material invocation.

## Task 2: Prospective offline material v3 allocation — owner decision required

**Prepare only after software review:** `docs/plans/artwork-material-v3.md`, `docs/plans/artwork-material-v3-registration.json`, and a minimal v3 producer derived from `scripts/prepare_artwork_material_v2.py`. Update its comparison-metadata/geometry readback for the declared event references; no unrelated artwork/UI changes or broader runner framework.

- [ ] Freeze one new invocation, three existing exporters (route SVG, choir WAV, comparison HTML), three byte-identical reused SVGs, one six-mode/nine-member review ZIP, zero native owners and zero corrective attempts. Require the same original 98-input archive and fresh relocation; preserve every consumed v1/v2 marker and output.
- [ ] Use a distinct worktree, `.superpowers/sdd/artwork-material-v3/launched.json`, output and publication namespace. Bind exact code/runtime/source/archive/member hashes, CLI argv/environment, guide and independent auditor before invocation. Validate all raw stream references/counts, exact SVG/HTML routes/worlds, WAV provenance and unchanged reused files against the frozen sources.
- [ ] Retain 300 seconds aggregate, 120 seconds per child, outer TERM at 290 seconds with five-second KILL grace; final integrity readback/publication shares that original clock. Count controls, relocated inputs, artifacts, child logs, review ZIP and any in-phase publication copies together against 2 GiB; require 4 GiB initially, 2 GiB continuously, 1 MiB headroom and 1 MiB per log stream. No allocation transfer, extra writer lease over a child writer or automatic retry.
- [ ] Refuse nonfresh output/marker, unsafe/duplicate ZIP paths, symlinks, incorrect size/CRC/hash/member sets, source drift, inference imports, failed/incomplete children, surviving owned processes, log/storage/deadline/publication violations. Keep final pass false until independent readback and timely close succeed. Preserve every partial result on failure.
- [ ] Present the concrete committed controls and registration for explicit owner approval. Only that approval permits the one fresh v3 invocation. A pass supplies bounded offline material preparation only; artistic usefulness, accessible real use, adequate sustained Afterimage and independent operator acceptance remain open.

The current draft authorizes no source edit, new extraction/export, data collection, model inference, hardware, human review, CI or merge.
