# MaleCNS v4 stage S1 — COMPLETED (19 November 2026)

Owner GO. Six models (old-corpus and augmented × seeds 10, 11, 12), 46,080 real-row presentations
over 1,440 optimizer updates each, terminal checkpoint only, ORIGINAL topology, Adam 0.001, clip 1,
float32 CPU one thread. Advice arrays derived in-process by the hash-gated child (S0z ruling).
**This stage produced checkpoints only. It evaluated nothing and gates nothing; no capability
result exists yet (S2 development gate: ≥ 3/4 per augmented seed).**

| Item | Value |
| --- | --- |
| Status | `completed-navigation-v4-training`; `success_admitted` true; no failure file |
| Models | 6/6 `completed`, 1,440 updates, 46,080 presentations, selected update 1,440, schedule shas equal the derivation |
| Selection | `terminal-only-before-recorded-development`; held-out `locked_unopened`; no claims |
| Report sha256 | `6ca8af5f9969fd1227d6e9494e9efc334e425c03145998da7a3de3a9d06c3cd2` |
| Publication sha256 | `fb6f1f38b492979a29e7bb70c091626bb2037354ea26f7e52140751b36c30f90` |
| Checkpoints | six sha256 in `checkpoints.sha256` (`.pt` files local) |
| Charged CPU | **173.589483 s** (estimate 250–330; worst case 2,165); wall 178.6 s |
| Navigation lane after S1 | **808.743 s** of 14,400 |

The held-out admission threshold governing S3 is 5,643.168 CPU-s of measured v4 charge through S2
(Amendment 1); older protocol text showing 5,648.168 is superseded. The recorded development
losses in `report.json` are retained but were not used for any selection and are not cited here.

Next: S2 development evaluation needs a protocol amendment and independently reviewed
implementation of a v4 Engine research binding (`docs/reports/male-v4-s2/NOTES.md`).
