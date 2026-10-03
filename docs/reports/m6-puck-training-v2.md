# Puck learning v2: three fixed recorded-input fits

All three prescribed CPU training seeds **21, 22 and 23 completed 30 epochs** on
2026-10-03 at producer `82e2bd97b37832c2a7f84f6eda6a3eca98e02362`.
Each checkpoint passed the bounded numeric reader and exact source/data/protocol
checks before the next seed started, then again after the enclosing logs drained.
This establishes recorded-input fitting and artifact integrity. No student native
run, closed-loop development result, held-out result or physical capability is claimed.

The [audited learning-v2 collection](m6-puck-teacher-collection-v2.md) supplies
**5710 training ticks from layouts 6000–6015 and 1314 recorded-dev ticks from
6016–6019**. Inputs remain float32 `[N,9]`; targets remain float64 `[N,2]`.
The failed learning-v1 collection stays ineligible. No source, dataset, numerical
procedure or threshold changed during this run. The combined trainer preparation
changed only its source-inventory task-protocol reference from v4 to the active v5;
the model and optimizer implementation remained unchanged.

| Training seed | Epochs completed | Earliest dev minimum | Normalized recorded-dev MSE | Supervised seconds |
| --- | ---: | ---: | ---: | ---: |
| 21 | 30 | 30 | 0.05303843069523647 | 17.071748335 |
| 22 | 30 | 27 | 0.05333465722333698 | 12.709538026 |
| 23 | 30 | 26 | 0.05388683384742532 | 12.465234904 |

All three models are retained; no winning seed was selected. The [JSON index](m6-puck-training-v2.json)
contains all **90 epoch records**, the three distinct checkpoint/report/protocol
identities, array hashes and exact local artifact references. Each 7266-byte NPZ
contains six finite float32 parameter arrays, 1442 parameters total, with no
pickle or compressed members. Raw models and reports remain in
`puck-training-v2/runs/puck-training-v2-20261003/seed-{21,22,23}` under the local
`.worktrees` directory; these generated artifacts are indexed, not committed.

The fixed procedure was `9→32 tanh→32 tanh→2 tanh`, Adam .001, no weight decay,
batch64, gradient norm cap1, seeded training-only permutations, one CPU thread and
earliest recorded-dev minimum. Float32 tanh outputs were promoted to float64
before multiplication by .4; the unchanged normalized MSE used float64 labels.
Runtime was Python3.11.15, NumPy2.2.5 and Torch2.9.0. Losses across epochs are
recorded-input evidence, not task-success estimates or a topology comparison.

The inner stage completed in **55.178901457 s**; the enclosing invocation completed
in **59.819789009 s**, including final validation and cleanup. All trainer and
supervisor exit codes were zero. Per-seed bounds stayed120 s internal,
TERM180 s plus15 s grace,200 s supervised including admission; the enclosing
stage used TERM660 s plus15 s grace and680 s supervised/final-wall acceptance.
The budget counted both controls and outputs under64 MiB with a1 GiB free-space
floor. Only the trainer held the existing writer lease. Both finite descendant
samplers stopped normally; all eight sampled outer PID/start identities were
independently absent, with no forced signals, sampler errors, survivors or
finalization errors. Source and dataset identities remained unchanged.

The local NumPy-only audit passed on its first invocation in **11.904787501 s**,
including a fresh full20-record admission, exact split arrays, all90 histories,
checkpoint headers/arrays, earliest selection, final output hashes and cleanup.
The independent root audit passed first in **1.368422392 s**, checking81 sources,
267 unique teacher-data files and416 scoped source/artifact entries, all histories
and finite numeric models. Neither audit imported Torch/MuJoCo or ran a model.
Their scripts, reports, the root control review and source-only preparation are
hash-pinned in the index. Before GO, a pure control preflight initially included
an extra newline when hashing the copied cleanup function; correcting only that
auditor convention produced six passing mocked checks. The launcher function
itself was unchanged, and the actual training batch was invoked once.

Inventory timing is explicit. The stage inventory captured three still-live
entries before publication: `stage-report.json`, `outer/stdout.log`, and
`outer/supervisor.json`. Their final bytes are bound by the enclosing final
inventory; the index preserves both versions' hashes and does not claim those
inner entries were final. Every enclosing control-inventory entry matches. No
separate enclosing console file was used; the terminal stdout is tool-retained.

The [learning protocol](../plans/m6-puck-learning-v2.md) still requires a separately
reviewed student owner, native/replay mechanism checks and fixed closed-loop dev
**6100–6103 × all three models**, with **at least3/4 goals for each model**.
Held-out6200–6207 remains locked. No development or held-out invocation followed
this training receipt.
