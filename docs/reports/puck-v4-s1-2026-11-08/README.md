# Puck v4 stage S1 — scene-ID collision admission (7–8 November 2026)

**Verdict: REFUSED.** One attempt, consumed. No retry is permitted by the protocol
(`m6-puck-navigation-v4-regenerated-on-policy-relabeling-protocol.json`,
sha256 `f885fc8d…286b`). Puck v4 therefore stops at S1 unless the owner authorises a
new, separately reviewed protocol.

| Item | Value |
| --- | --- |
| Owner GOs | S1 + D8 audit (2026-11-08), D2 scoped to S1 — records in this folder |
| Scope | 24 declared roots: all palimpsest refs + advertisement, every worktree, run registries, surviving Codex `brain` clones (lost-root exception), fixtures, evidence store |
| Collisions (typed scene-ID reuse) | **0** |
| Ambiguous documents | **63** → fail-closed refusal (`"63 ambiguous document(s) mention new IDs"`) |
| Reservation | none published |
| Charged CPU (cgroup census, puck lane) | S1 **86.606110 s** (worst case reserved 660); audit **0.069836 s** |
| Wall / peak memory | 98.6 s / 3.93 GB |
| D8 audit | passed (report canonical, inputs hashed, verdict ↔ no reservation, claims all false, receipt drained and exit code matches) |

## What the ambiguous documents are

All 63 are byte copies (in the main checkout, worktrees, the fresh-reproduction
checkout, run copies such as `paper-authority-replay-v1/fault_matrix/*/` and the
pinned `upstream/fly-gym` submodule) of FLYNN connectome tables, chiefly
`upstream/fly-gym/connectomes/ws_small_world/consolidated_cell_types.csv`. Each
contains all eight new IDs (6510–6513, 6520–6523) as numeric cell/neuron indices.
Raw-format (CSV) numeric mentions without a scene-typed header are classified
"ambiguous" by the reviewed rule, and any ambiguity refuses. No document typed these
numbers as scene, layout, roster, split or held-out fields.

This is an admission-engineering outcome, not a scientific result: no scene was minted,
no simulator or model ran, and no held-out scene was loaded (D2 byte reads only).

## Engineering CPU outside the lane

Plan-time calibration and dry checks before execution (not research processes; disclosed):
calibrations 19.8 s, 23.0 s and 35.6 s (user+sys), final dry check 15.4 s.

## Evidence

`s1-report.json.gz` (report sha256 `4aa9e4c7…0f61`), launcher receipts, D8 audit,
the four GO records, the reviewed declaration (`comparison-set.json`), the final
calibrated plan and a snapshot of the research ledger
(`~/.local/state/palimpsest/research-ledger.jsonl`).
