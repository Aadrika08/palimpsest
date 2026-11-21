# MaleCNS v4: the augmented arm underfit its training budget (retained S1 evidence, no new compute)

Source: S1 `report.json` (sha256 `6ca8af5f9969fd1227d6e9494e9efc334e425c03145998da7a3de3a9d06c3cd2`), read only. Each model had the same
1,440 optimizer updates, 46,080 real-row presentations and 32 rows per update (matched budget, protocol
`cd4eb130…`). "Recorded development" is teacher imitation on recorded inputs, not closed-loop navigation.

| Seed | Arm | Train loss | Recorded-dev loss | Velocity MAE | Wrapped heading MAE (rad) |
| --- | --- | --- | --- | --- | --- |
| 10 | old-corpus | 0.0209 | 0.0183 | 0.0183 | 0.118 |
| 10 | augmented | 0.2383 | 0.0748 | 0.2147 | 0.426 |
| 11 | old-corpus | 0.0197 | 0.0188 | 0.0203 | 0.109 |
| 11 | augmented | 0.2400 | 0.0691 | 0.1596 | 0.402 |
| 12 | old-corpus | 0.0216 | 0.0197 | 0.0241 | 0.146 |
| 12 | augmented | 0.2416 | 0.0599 | 0.1718 | 0.334 |

**Reading.** Terminal training loss of the augmented arm is about 12x the old-corpus arm on all three seeds, and
recorded-input velocity error is 7 to 12x worse. Together with the S2 observation of near-constant augmented
actions, this is consistent with the augmented policies having underfit the larger, more varied corpus (7,197 vs
2,117 rows) within the fixed budget, rather than with a harness or scene effect. It is a descriptive
consistency, not a controlled test: no ablation (longer budget, learning rate, corpus mix) was run, and the
protocol's one-attempt rule forbids one under `cd4eb130…`.

**What it implies.** Passing the unchanged 3/4 development and 6/8 held-out thresholds would need a *new* protocol
(e.g. a larger training budget for both arms, fresh pre-registered development and held-out scenes because
3160 to 3163 were read and 3170 to 3177 are locked under v4). That is a new study with its own stage chain and
budget, not a continuation of v4. No such protocol exists or is authorised.
