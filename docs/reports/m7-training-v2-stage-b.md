# M7 v2: three completed paired training seeds

All six fixed models completed twenty epochs on the same 1,983 training and 1,228
recorded-dev ticks per epoch. Source was `01523cff9d739f1026299f88ff04fc13dc49e485`;
no retries, replacement models, protocol changes or held-out reads occurred. The
[evidence index](m7-training-v2-stage-b.json) binds the retained launch, complete
primary inventories, immutable model manifest and independent audit.

| Training seed | Variant | Selected epoch | Recorded-dev loss |
| --- | --- | --- | --- |
| 10 | original | 20 | 0.01912509 |
| 10 | degree_rewired | 20 | 0.01774029 |
| 11 | original | 20 | 0.01549869 |
| 11 | degree_rewired | 19 | 0.01578155 |
| 12 | original | 20 | 0.02036772 |
| 12 | degree_rewired | 20 | 0.02725934 |

Each selected epoch is the earliest exact minimum over all twenty recorded-dev
losses. The supervised pairs took 61.079, 62.516 and 69.141 seconds; all exited 0
within the unchanged 600-second training budget and layered external bounds.
No isolated per-epoch timing or peak-RSS claim is made.

The read-only audit rehashed Stage A data and all training source, asset, report
and checkpoint inventories, checked graph/ordered-ID and bounded ZIP contracts,
and verified every twenty-epoch history, selected minimum and shared collection.
It imported neither Torch nor MuJoCo and found no surviving training process.
Checkpoint tensor loading and closed-loop behavior remain separate runtime gates.

The pinned six-model manifest SHA256 is
`7d4b3fd42359aeb119f12c2638006f38ae3ee9afa3f833929c9f6a73cecba26b`.
Production v1 assets and identities remain unchanged. These are recorded-input
imitation results, not evidence of navigation competence or topology benefit.
Stage C development rollouts require their separate release; held-out collection
and evaluation remain closed until the exact predeclared development gate passes.
