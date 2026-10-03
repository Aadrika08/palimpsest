# Puck student development: clean execution, failed goal gate

The fixed development gate **failed**: models 21, 22 and 23 each reached **0/4
goals**, against the unchanged requirement of at least 3/4 for every model. All
twelve owners completed cleanly at the natural 600-tick task time limit, totaling
7200 recorded intervals and twelve initial snapshots. Exit 0 and operational
`completed` describe successful collection and cleanup; they do not pass the goal
gate. Held-out layouts 6200–6207 remain locked. No retry, tuning, model selection,
retraining or UI promotion followed this result.

The [protocol](../plans/m6-puck-student-development-v1.json),
[implementation contract](../plans/m6-puck-student-development.md) and
[compact evidence index](m6-puck-student-development.json) bind the single
execution on frozen `77f4d49`, all three immutable fitting bundles, controls, raw
records and independent audits. The prior [native/replay mechanism](m6-puck-student-mechanism.md)
remains separate evidence.

| Scene | Model | Ticks | Goal distance at end (m) | Contact intervals | Own push-mode intervals |
| --- | ---: | ---: | ---: | ---: | ---: |
| 6100 | 21 | 600 | 1.173090 | 180 | 0 |
| 6100 | 22 | 600 | 1.104057 | 376 | 0 |
| 6100 | 23 | 600 | 1.118688 | 390 | 0 |
| 6101 | 21 | 600 | 1.170474 | 334 | 0 |
| 6101 | 22 | 600 | 1.000697 | 392 | 0 |
| 6101 | 23 | 600 | 0.962649 | 413 | 0 |
| 6102 | 21 | 600 | 1.473491 | 453 | 0 |
| 6102 | 22 | 600 | 1.027827 | 286 | 0 |
| 6102 | 23 | 600 | 1.056870 | 476 | 0 |
| 6103 | 21 | 600 | 1.414199 | 403 | 0 |
| 6103 | 22 | 600 | 1.133415 | 473 | 0 |
| 6103 | 23 | 600 | 1.084427 | 469 | 0 |

Every model used the same declared eight virtual sensors and its own BEFORE-mode
as feature nine. Both continuous actions came from one MLP prediction per interval;
there was no analytic fallback or teacher diagnostic. The own mode remained
`approach` throughout. Contact and puck displacement occurred, but no episode
satisfied goal success. Maximum displacement ranged from 0.026916 to 0.715606 m.
These observations describe the traces; they do not establish a cause of failure.

Within each scene, all three initial scientific fingerprints matched before action 1:
defined native integration state, full native model/runtime/profile, environment
caches, task/world/contact, sensors[8], inputs[9], own cursor and Python/NumPy/
environment/space RNG. Model identity and Torch RNG remained separately pinned;
raw native allocation/diagnostic bytes were retained without modification. The
cross-constructor exclusions were declared before execution. Every full raw SNP
remains available; production restoration semantics were unchanged.

The inner stage reported 188.895204370 s; bounded supervision completed with exit
0 in 189.105893136 s; the launcher reported 194.751241512 s elapsed. All twelve
owners exited 0. Their callbacks and renderers closed normally. Both the outer
sampler and all fourteen observed PID/start identities were terminal, with no
forced signals, survivors, reuse conflicts or sampler/finalization errors. The
writer lease was independently verified free. All 94 source pins, original teacher
provenance and fixed bundles remained unchanged.

The limits remained twelve roots, one episode ≤600 ticks each, 180 s per owner,
60 s startup / 30 s progress, 1200 s internal, TERM 1260+15, and 1280 s enclosing
wall admission through publication/return. Storage remained 3 GiB total, 160 MiB
per owner, 8 MiB per initial SNP and a 1 GiB free floor. There was no budget extension.

The local retained-data audit passed on its first invocation in 12.548300095 s.
It checked all numeric rows/events, independent sensor/phase arithmetic, pure task
transition readmission, initial matching, file ledgers and process identities.
Root’s independent first-pass audit took 14.110189622 s and also reconstructed
the MLP outputs with NumPy: maximum absolute error 9.536743164617612e-08, within
the declared 1e-6 tolerance. Neither audit imported Torch, decoded native data
through MuJoCo, ran another episode or changed the raw evidence.

The index references the authoritative outer 330-file and inner 324-file ledgers
without duplicating them. The outer control inventory contains a prepublication
prefix of its enclosing console; the final drained console is pinned separately.
The pure controls fixture intentionally completed twelve synthetic rows with a
negative admission and rejected false promotion; it is not task evidence.

This negative development result supports neither held-out performance nor learned
puck-pushing competence. Headless runtime integrity, task success, public UI
integration and physical capability remain distinct gates.
