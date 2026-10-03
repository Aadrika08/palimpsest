# Puck teacher collection v2 — fixed dataset admitted

**Passed once** on producer `69fd44504f8c7cd836c0f53176cfea881e848912` after the
[new-stop mechanics gate](m6-puck-learning-v2-mechanics-v1.md). All 20 fresh
owners reached natural goals and passed the unchanged complete-batch admission:
7024 recorded intervals, comprising 5710 train and 1314 recorded-dev intervals.
No model was trained, and dev/held-out rollouts remain closed.

The existing 0.2 m task radius is now also the teacher/supervisor stop boundary.
Seed 6004 supplied **17 actually executed terminal zero labels**, 124 contact
intervals and 333 ticks; final distance was 0.19206372897283402 m. This measured
new trajectory is distinct from the source-only counterfactual review. The
[rejected v1 batch](m6-puck-teacher-collection-v1.md) is unchanged and ineligible.

| Seed | Split | Ticks | Contact intervals | Terminal zero labels |
| --- | --- | ---: | ---: | ---: |
| 6000 | train | 335 | 135 | 24 |
| 6001 | train | 271 | 156 | 23 |
| 6002 | train | 316 | 186 | 25 |
| 6003 | train | 447 | 234 | 25 |
| 6004 | train | 333 | 124 | 17 |
| 6005 | train | 272 | 161 | 25 |
| 6006 | train | 315 | 191 | 24 |
| 6007 | train | 527 | 240 | 24 |
| 6008 | train | 336 | 136 | 25 |
| 6009 | train | 272 | 160 | 24 |
| 6010 | train | 316 | 191 | 25 |
| 6011 | train | 526 | 248 | 24 |
| 6012 | train | 336 | 137 | 25 |
| 6013 | train | 272 | 160 | 25 |
| 6014 | train | 315 | 189 | 24 |
| 6015 | train | 521 | 230 | 22 |
| 6016 | recorded_dev | 274 | 139 | 25 |
| 6017 | recorded_dev | 310 | 178 | 25 |
| 6018 | recorded_dev | 347 | 213 | 24 |
| 6019 | recorded_dev | 383 | 249 | 25 |

All sixteen training owners exceed the fixed minima of 32 ticks, 10 contact
intervals and 10 terminal exact-zero labels. Every own BEFORE/AFTER mode was
reconstructed from reset using float32 sensors; actual expert labels remained
float64. No row substitution, padding, post-terminal steps, retry or replacement
occurred. Twenty initial native snapshots and every declared source/feature/
label hash are retained.

Outer exit was 0 after 159.607045387 s; inner elapsed time was 159.362579150 s.
The frozen 1500/1560/+15/1580 s limits, 4 GiB stage cap, 160 MiB owner caps,
1 GiB free floor and 16 GiB retention bound were unchanged. All 86 source pins
and previously completed owner evidence stayed unchanged. All twenty child exits
were 0, callbacks/resources closed, all twenty owner groups and all 22 sampled
PID/start identities were absent. No forced signal, survivor, sampler error or
finalization error occurred; the runtime slot was released before raw auditing.

The local NumPy audit passed first in 16.718877355 s: 393 outer/387 inner indexed
files, 865,192,450 bytes, all 7024 rows and 20 snapshot payloads. It independently
reconstructed every teacher command/mode, sensor/native pose/contact stage and
wheel control, then re-admitted all twenty records and matched feature/target
hashes. It imported no Torch/MuJoCo and deserialized no native data.

The separate root audit passed in 13.263437835 s after preserving an auditor-only
failure: its first run completed all row/snapshot checks but used `dev` rather
than the actual `recorded_dev` split in the final count assertion. Only that
literal changed; both failed script/receipt and corrected script/report are
indexed. No source data or native execution was changed or repeated.

The [evidence index](m6-puck-teacher-collection-v2.json) pins the original report
inventories, controls, both audit versions, all twenty manifests and feature/
target hashes. The exact completed collection report is the future trainer
handoff; admission is not authorization to fit a model. Separate combined-source
review and runtime GO are still required under the unchanged three training
seeds 21/22/23, thirty epochs and all-model development/held-out thresholds.
