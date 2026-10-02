# M7 CPU wrapper validation

At commit `4941468d0a60ed876cf44d21eb0b1e20603b3b94`, both bounded CPU
jobs passed without source edits, retries, simulation, training or selection.
The retained commands, source/artifact hashes, script and reports are identified
in [the machine-readable report](m7-wrapper-validation.json).

The synthetic loader/rollback test passed in 2.478 seconds (3.250 seconds including
process startup). It checks fixed graph weights and buffers, tensor shape/dtype/
finiteness, actual telemetry, reset and rejected-input/raw-output hidden rollback.

The actual comparison loaded both 303,341-byte checkpoints from the completed
training report `594d4d330624ed1040ae2b3ffe2dedfbfacd6a2d360a29dcfcc6584d76b80e28`.
Each variant consumed the same four retained held-out episodes, seeds 112–115,
150 distinct recorded ticks each: **600 ticks per variant**. Cameras, sensors and
all 388 features matched exactly. Every act used one model invocation. First-step
direct-forward and reset-repeat outputs matched exactly for each episode.

Per-step actions and encoder/raw outputs matched the frozen 32-tick-window
evaluation profile with `atol=rtol=1e-6`. Hidden state was finite CPU float32 with
shape `(1,138)` at every tick and compared numerically at every window boundary.

| Variant | Max action difference | Max encoded difference | Max raw difference | Max boundary-hidden difference |
| --- | ---: | ---: | ---: | ---: |
| Original | 1.78814e-7 | 3.87430e-7 | 5.96046e-8 | 1.19209e-7 |
| Degree-rewired | 2.38419e-7 | 7.07805e-7 | 5.96046e-8 | 1.27591e-7 |

The actual process took 10.174 seconds; both jobs together took 13.425 seconds.
Each had an external 120-second hard limit, within a 240-second outer bound.
Captured source and artifact hashes remained unchanged. Retained held-out source
file hashes matched the training manifest; final fingerprints remained unchanged.
The only warning was the pinned upstream Torch sparse CSR beta warning.

Evidence remains in `runs/m7-wrapper-validation-4941468/`: `validate_recorded.py`,
`commands.json`, `synthetic.log`, `actual.log`, `checks-report.json`, and
`actual-report.json`. The tracked JSON records their exact hashes and sizes.

This validates loading and recorded-input parity on this CPU regime. It does not
validate Engine integration, native snapshot continuation, replay, closed-loop
navigation, biological sensing or topology benefit. Training and rewiring each
used one seed; the control's imitation score is not evidence of topology benefit.
