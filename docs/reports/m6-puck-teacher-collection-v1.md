# Puck teacher collection v1 — goals completed; batch admission failed

The single frozen collection at `b7db16a3c2a48d22752af8c1e6d405beedd1a8c3` reached
`puck_goal` on all **20 fixed layouts**, but the batch **failed training admission**.
Seed **6004** retained **113 intended-contact intervals** and **zero terminal
`[0, 0]` labels**, below the unchanged requirement of ten. All 20 rows and every
original artifact remain retained. There was no retry, replacement, padding,
post-terminal control, label substitution, threshold relaxation or training.

## Same-source mechanics compatibility

Before collection, a separate accepted gate passed the unchanged ten-owner
mechanics plan on the same producer source: 1,575 rows, both 361-tick teacher
goals, three exact four-tick native continuations, 120-row action replay with
zero teacher calls and full 361-row policy replay. Outer/inner elapsed times
were **45.792629270 / 45.522660192 s**, exit 0. All ten owner groups and twelve
sampled PID/start identities were absent. Callbacks/renderers closed; no forced
cleanup or finalization error occurred. All 83 source hashes remained unchanged.

The local read-only audit passed in 4.769 s. Root's independent audit passed in
5.207 s and additionally compared **all 1,575 numeric rows, every field's dtype,
shape and bytes**, with the retained [historical v5 records](m6-puck-mechanics-v5.md).
Both replays and the default packet/application semantics remained compatible.
This result does not qualify the separate learning teacher envelope for restore.

## Fixed collection and exact failed coverage

Seeds 6000–6015 were training demonstrations; 6016–6019 were recorded development.
All completed naturally within the frozen 600-tick cap. There are **7,070 actual
rows: 5,744 train and 1,326 recorded dev**. Every outcome below is `puck_goal`.
“Admission” records each row's data check; the **whole batch remains ineligible**
when any one row fails.

| Seed | Split | Ticks | Intended-contact intervals | Terminal zero labels | Admission |
| --- | --- | ---: | ---: | ---: | --- |
| 6000 | train | 337 | 137 | 23 | passed |
| 6001 | train | 274 | 161 | 24 | passed |
| 6002 | train | 319 | 193 | 25 | passed |
| 6003 | train | 449 | 239 | 24 | passed |
| 6004 | train | 332 | 113 | 0 | **failed** |
| 6005 | train | 274 | 161 | 24 | passed |
| 6006 | train | 319 | 192 | 25 | passed |
| 6007 | train | 528 | 239 | 22 | passed |
| 6008 | train | 337 | 134 | 24 | passed |
| 6009 | train | 274 | 164 | 24 | passed |
| 6010 | train | 318 | 191 | 24 | passed |
| 6011 | train | 528 | 251 | 23 | passed |
| 6012 | train | 337 | 137 | 23 | passed |
| 6013 | train | 275 | 160 | 25 | passed |
| 6014 | train | 318 | 192 | 24 | passed |
| 6015 | train | 525 | 235 | 22 | passed |
| 6016 | recorded dev | 278 | 143 | 26 | passed |
| 6017 | recorded dev | 312 | 180 | 24 | passed |
| 6018 | recorded dev | 351 | 218 | 25 | passed |
| 6019 | recorded dev | 385 | 251 | 24 | passed |

Seed 6004's final puck distance was **0.19417256244312925 m**. The task's success
predicate permits distance ≤0.2 m, speed ≤0.03 m/s, prior intended contact and
at least 0.5 m of puck displacement for ten completed intervals. The teacher's
stop command is emitted only at distance ≤0.18 m. Thus valid task completion
does not imply ten zero-action labels.

The final dwell occupied completed ticks **323–332**. The puck was nearly
stationary while the teacher and independent own cursor both remained in
`approach`. The last four commands had reverse velocity −0.25; the final command
was `[-0.25, 0.09437987642473056]`. The retained audit contains the exact last
sixteen world states, behind-point geometry, eight/nine inputs, modes, contact,
actions and task states. Independent reconstruction found no sensor-mode,
recording or teacher-call discrepancy. The observed shortfall is the declared
coverage contract, not failed native goal execution. No claim is made that a
teacher/protocol adjustment has solved it.

## Bounds, cleanup and audits

The outer supervisor exited **1** after **172.355729551 s**; inner collection took
**172.108188386 s**. Each of the 20 owner processes exited 0. All owner groups and
22 observed PID/start identities were absent; no forced signals, surviving
processes, sampler errors or finalization errors occurred. All 86 frozen source
hashes and each owner's full model hash remained unchanged. The native slot was
released before the retained-data audits.

The local audit passed on its first invocation in **13.849 s**, rehashing **395
outer / 389 inner indexed files**, **870,797,940 bytes**, 7,070 numeric rows and
20 initial snapshot receipts. It independently reconstructed all eight sensor
projections, named raw-contact classifications/padding/end caches, wheel
conversion, native pose/quaternion/velocity fields, and checked exact float64
labels/own cursors through the recording reader. Re-admission reproduced the
same failed batch and returned no training arrays.

Root's separate audit passed in **13.498 s**, independently reconstructing the
privileged teacher, sensor-only modes, ninth BEFORE-mode, dwell/outcomes and the
6004 shortfall. Its first audit script incorrectly copied the mechanics task
digest without the learning own cursor; that failed script and receipt remain
pinned alongside the corrected audit. Only the audit contract changed; no
producer source, raw data or native execution was changed or repeated. Neither
retained-data audit imported MuJoCo/Torch or deserialized native state.

The [JSON evidence index](m6-puck-teacher-collection-v1.json) pins controls,
primary reports, all source entries, initial snapshot receipts and both audits,
including root's retained first audit failure. Raw runs remain local retained
artifacts, not tracked datasets. The producer is **b7db16a**, not the later
commit publishing this evidence. Native collection required separately reviewed
controls: 1500 s internal, TERM1560/+15, outer1580, 4 GiB stage, 160 MiB per owner,
1 MiB logs, 8 MiB snapshot cap, 1 GiB free floor and 16 GiB aggregate retention.

This is simulator teacher/recording evidence. It establishes neither a trained
puck policy nor learned or physical competence. The failed report cannot be
used by the fixed trainer; closed-loop development and held-out stages remain
unopened. A prospective correction requires a separate contract review before
any new collection, training or native execution.
