# M7 paired closed-loop evaluation v2

The frozen sixteen-run evaluation completed at `fefd064` with exact matched
initial states, clean owners and unchanged source/model identities. Navigation
was weak: the original model reached **0/8 goals**; the degree-rewired control
reached **1/8**. This does not qualify useful navigation or show a topology benefit.
The earlier [rejected v1 batch](m7-closed-loop-v1.md) remains unchanged.

Both existing checkpoints were fixed before new scene seeds 128–135. Each model
received one episode per seed, with no training, checkpoint selection, resets,
replacement scenes or retries. The [frozen protocol](../plans/m7-closed-loop-protocol.md)
limits each run to 600 control ticks. All endings below are natural outcomes;
there were no infrastructure failures or artificial early caps.

| Scene seed | Original: outcome / ticks | Rewired control: outcome / ticks |
| --- | --- | --- |
| 128 | time_limit / 600 | stalled / 419 |
| 129 | stalled / 392 | stalled / 279 |
| 130 | stalled / 517 | stalled / 562 |
| 131 | stalled / 569 | stalled / 423 |
| 132 | stalled / 310 | time_limit / 600 |
| 133 | stalled / 347 | goal / 290 |
| 134 | stalled / 358 | stalled / 345 |
| 135 | time_limit / 600 | stalled / 497 |

Original outcomes: six stalled and two time limits. Control outcomes: six stalled,
one time limit and one goal. Sixteen completed episodes contain **7,108 ticks**,
142.16 simulated seconds and **1,419,706,745 bytes** of recordings and initial
snapshots. Internal duration is 545.344234318 seconds; the external supervisor
completed normally in 545.626508883 seconds, exit zero. Wall duration includes
startup, IPC, paused stepping, recording and validation; it is not model latency
or a real-time-factor result. Per-run policy/physics timing remains in the index.

The independent read-only audit checked all seven fixed asset files, 60 source
files, eight exact initial world/physics/input/environment-RNG pairs, all sixteen
recordings, hashes, counts, outcomes and close dispositions. Actual first recorded
float32 inputs match their native snapshots; raw/effective eyes agree, and no
fictitious neural populations are supplied. All owners close with exit zero;
all finalization stages pass. No source, model or earlier completed recording
fingerprint changed. The independent audit loaded no Torch or MuJoCo and took
10.460489023 seconds; it did not rerun inference or physics.

[The evidence index](m7-closed-loop-v2.json) retains the complete evaluation report,
per-file/aggregate recording identities, source and model pins, paired-state
hashes, per-run outcomes and independent audit. Primary local evidence is
`runs/m7-male-closed-loop-v2-20261002/evaluation.json`, SHA-256
`357f8ccdc2faa9ded45c2f9502abe1b05ed835abad907cee8493e4a69b0ded4e`;
outer bounded logs and supervision are in
`runs/m7-male-evaluation-launch-fefd064/`.

This is one trained model seed and eight new fixed scenes, not statistical evidence
of broad generalization or a structural advantage. The small artificial encoder,
reduced graph and short imitation pilot remain material limitations. MaleCNS
extraction/training/runtime/evaluation mechanisms now have retained evidence, but
R3 remains incomplete because the controller has not demonstrated a useful
navigation capability. Future training or model selection requires a separate
protocol and untouched evaluation scenes; these results must remain visible.
