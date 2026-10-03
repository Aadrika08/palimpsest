# Balanced puck development: clean execution, failed goal gate

All three balanced models reached **0/4 goals**, failing the unchanged requirement
of at least 3/4 for **each** model. All twelve fixed runs ended normally at the
600-tick task time limit: 7200 recorded intervals and twelve initial snapshots.
Operational `completed` and exit 0 describe execution and cleanup, not successful
puck pushing. Held-out layouts 6200–6207 remain locked. No retry, tuning, model
selection, further training or UI promotion followed.

The [fixed protocol](../plans/m6-puck-balanced-student-development-v1.json),
[source contract](../plans/m6-puck-balanced-development.md) and
[evidence index](m6-puck-balanced-development.json) bind the single invocation on
frozen `d4efa26`, all three existing balanced bundles, the original teacher inputs,
controls and retained records. The earlier [balanced mechanism](m6-puck-balanced-student-mechanism.md),
[negative recorded-input residuals](https://github.com/Aadrika08/palimpsest/blob/808baef73fa4f393e76df118e6e2ce18826a4f78/docs/reports/m6-puck-balanced-residual-v1.md) and
[original-model development](m6-puck-student-development.md) remain separate evidence.

Every row below contains 600 executed intervals. Distances and mode/contact counts
are descriptive; they do not establish a cause of failure.

| Scene | Model | Goal distance at end (m) | Contact intervals | Own push BEFORE-mode intervals |
| --- | ---: | ---: | ---: | ---: |
| 6100 | 21 | 1.200000 | 0 | 0 |
| 6100 | 22 | 1.200000 | 0 | 0 |
| 6100 | 23 | 1.200000 | 0 | 0 |
| 6101 | 21 | 1.232865 | 37 | 0 |
| 6101 | 22 | 1.292401 | 56 | 0 |
| 6101 | 23 | 0.956242 | 372 | 0 |
| 6102 | 21 | 1.265145 | 160 | 0 |
| 6102 | 22 | 1.373878 | 140 | 0 |
| 6102 | 23 | 0.889578 | 413 | 0 |
| 6103 | 21 | 1.216396 | 83 | 173 |
| 6103 | 22 | 1.365214 | 69 | 175 |
| 6103 | 23 | 1.009640 | 455 | 0 |

The own cursor entered push mode only for scene 6103 with model 21 or 22. The
remaining runs stayed in approach mode. Scene 6100 had no rover–puck contact or
planar puck displacement for any model. Across all runs, maximum planar puck
displacement ranged from 0 to 0.790465 m. These observations did not satisfy the
goal gate. Each interval used the same declared eight sensors plus the model's
own BEFORE-mode, with both actions supplied by one MLP prediction and no analytic
fallback or teacher diagnostics.

All three scientific initial fingerprints matched within each scene before action
1: defined native integration/model/runtime/profile, environment, task/world/contact,
inputs and own cursor, and Python/NumPy/environment/space RNG. Model identity,
Torch RNG and raw native allocation/diagnostic bytes retained their predeclared
separate treatment. Full raw snapshots remain unchanged; no new exclusion was added.

The inner report recorded 177.290060120 s. The launcher recorded 181.755467340 s
before publication; the enclosing process observed launcher return/drain at
182.140540510 s and recorded 182.145269681 s before its publication. Tool session
35311 then drained with exit 0. All owners exited 0, callbacks/renderers closed,
both samplers stopped, and all sixteen observed PID/start identities were absent.
There were no forced signals, survivors, sampler or finalization errors. Root's
independent writer-lease probe was free. All 101 producer source pins, fixed bundles
and original teacher provenance remained unchanged.

Normal limits stayed at twelve roots, ≤600 ticks each, 180 s per owner, 60 s
startup / 30 s progress, 1200 s internal / TERM 1260+15 / 1280 s admission through
publication and return. The separately frozen enclosing TERM 1300 / KILL 1315 /
fallback 1318 bounds and 12 s failure-cleanup admission only terminate failure;
they do not extend normal acceptance. Storage stayed at 3 GiB total, 160 MiB per
owner, 8 MiB per snapshot, 1 GiB free and 16 GiB retained-run cap.

The local retained-data audit passed on its first invocation in
22.862629238 s. Root's independent audit passed first in 23.125775618 s, including
NumPy reconstruction of all recorded actions: maximum absolute error
7.152557374157098e-08 within 1e-6. Both checked all numeric rows, snapshots,
initial matches, outcomes, identities and file ledgers. Neither imported Torch
or MuJoCo, deserialized native state through MuJoCo, ran a new episode or changed
raw data. The local checker reuses the pure task transition; root's independent
checks and their exact source/receipt references are indexed separately.

The compact index points to the authoritative 330-file outer and 324-file inner
ledgers. The outer retained inventory is fully drained. Its control inventory can
contain live enclosing log prefixes; the enclosing report separately pins its
final drained supervisor logs. Pure fault/filesystem fixtures remain control
evidence, not task evidence. This result does not establish learned puck-pushing
competence, held-out performance, public UI readiness or physical capability.
