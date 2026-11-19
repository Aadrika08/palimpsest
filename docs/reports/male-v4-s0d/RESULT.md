# MaleCNS v4 stage S0d — COMPLETED (9 November 2026)

Owner GO 2026-11-09. Rebuilt S0d controller on port tree T-d (`19d275d` + listed hunks, port
commit `02e861f8`); recovery learners trained for seeds 10, 11, 12 on the S0c data
(2,117 train / 1,228 dev rows, data manifest `052a8dbd…`).

| Item | Value |
| --- | --- |
| Terminal status | `passed-research-training`; 3/3 pairs `completed` with supervision; stage 134.0 s (≤ 2,160) |
| Inventories | unchanged before/after (tracked 355, upstream 122, raw documents 226, model production 14, runtime 4) |
| Per seed | report `completed-research-training`, both models completed, `training_seed` = 10/11/12 (recorded in `protocol.json`), data manifest `052a8dbd…`, research protocol `9c0ae9ef…`, identical `model_inputs` across seeds |
| Checkpoints | sha256 lists in `seed-N/checkpoints.sha256` (`.pt` files stay local) |
| Charged CPU | **130.524717 s** (worst case 2,165); wall 134.2 s; peak memory 0.46 GB |
| Navigation lane after S0d | **330.858 s** of 14,400 |

Owner decision 2: `degree_rewired` fits were run unchanged and are retained (in `report.json`) but
are not evaluated, quoted or cited here or anywhere. Only the `original` checkpoints become S0e
advice learners.

Gate note: the manifest's gate text placed `training_seed` in `report.json`; it is recorded in
`protocol.json.training` (seeds verified there). Limitation (review item 5): runtime thread/CUDA
facts are set, not re-checked.

Next: fill the recovery index copy (`training_source_*`, `/model_inputs` from S0d;
`/data_manifest` from S0c), then the S0e manifest, review and owner GO.
