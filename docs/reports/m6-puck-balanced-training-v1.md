# Puck balanced-loss pilot: recorded-input fitting

All three fixed seeds **21, 22 and 23 completed 30 epochs** on 2026-10-03 at
producer `ec7a11322ca9f4d94b3cbe7ad8f5bae42603d08c`. The actual invocation ran
once and exited 0. All three models and 90 epoch records are retained. This is
fitting and artifact-integrity evidence; no new student rollout, task-success,
held-out or physical qualification is claimed.

The [frozen objective](../plans/m6-puck-balanced-loss.md) reused the same admitted
5710 teacher training rows (layouts 6000–6015) and 1314 recorded-development rows
(6016–6019). Training gave each of the six nonempty phase/action strata equal
total mass using the declared float64 weights. Histories explicitly name
`weighted_train_loss`. The MLP, inputs, float64 targets/output scaling, optimizer,
30-epoch budget and **earliest unweighted development minimum** selection were
unchanged. There was no winning-seed selection or replacement of old models.

| Seed | Completed epochs | Selected epoch | Unweighted dev normalized MSE | Supervised seconds |
| --- | ---: | ---: | ---: | ---: |
| 21 | 30 | 22 | 0.06030484144030176 | 17.314973 |
| 22 | 30 | 24 | 0.06008515803120118 | 12.756833 |
| 23 | 30 | 15 | 0.06074273400721579 | 12.514639 |

These unweighted development losses are higher than the corresponding
[original fits](m6-puck-training-v2.md). Weighted training losses are a different
objective and are not directly comparable with historical training losses.
Whether particular residual strata improved remains a separate diagnostic;
neither fitting objective nor residuals substitute for the task gate.

Each 7266-byte checkpoint has six finite float32 arrays, 1442 parameters total.
The [compact index](m6-puck-balanced-training-v1.json) pins all three checkpoint,
protocol and report files; each raw report retains its complete 30-epoch history.
It also points to the original inventories instead of duplicating them. The
raw outputs remain under
`.worktrees/puck-balanced-loss/runs/puck-balanced-training-v1-20261003/`.

The stage reported 53.818398 s before publication, and its launcher reported
58.539173 s before publication. The separate enclosing supervisor measured
**58.884401 s through launcher process return and log drain**; the envelope
reported 58.937196 s before its own publication. Normal acceptance remained
680 s. The independent termination envelope declared TERM at 700 s, KILL at
715 s, a 718 s supervisor fallback and separately bounded failure cleanup;
none was needed. The 64 MiB aggregate cap and 1 GiB free-space floor remained.
All three finite samplers stopped, all ten sampled PID/start identities were
absent, and no forced signals, conflicts, survivors or finalization errors
occurred. The global writer lease was acquired and released after exit to
confirm it was free. Source, controls, teacher data and original bundles stayed
unchanged.

The independent root audit passed its first invocation in **1.475517 s**. It
checked all 90 histories, the exact earliest minima, finite numeric checkpoints,
438 source/artifact references including 267 unique teacher-data files, logs,
controls and cleanup without Torch, native imports or predictions. Its receipt
and script are pinned in the index. Inventory stages remain explicit: the stage
self-entry and still-live enclosing logs record prefixes; final bytes are bound
by the enclosing drained ledger and root audit.

Before execution, the first pure launcher fixture exposed a misplaced monitor
startup block in finalization. The draft and failure log remain unchanged;
correcting that placement and binding control hashes produced 11 passing
launcher fixtures. Two further filesystem fixtures checked normal and forced
enclosing disposition. Those fixtures started no training child or native
runtime. The later actual training was a single invocation with no retry.

The historical student result remains **0/4 goals for each original model**.
Any later use of these new bundles requires a separately reviewed binding,
native/replay mechanism check and the fixed development gate of **at least 3/4
goals for each model on 6100–6103**. Held-out 6200–6207 remains locked.
