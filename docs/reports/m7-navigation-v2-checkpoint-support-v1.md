# M7 navigation-v2 selected-checkpoint output-support audit

8 October 2026. The sole frozen invocation completed normally under the bound 210-second supervisor. It evaluated the six selected ORIGINAL-graph checkpoints once on the unchanged four-source, 1,228-row recorded-development split: 7,368 row inferences and 234 recurrent windows in 3.219 seconds. The attempt is consumed and must not be repeated.

## Evidence boundary

- Output: five compact files, 185,950 bytes total, below the 16 MiB cap. Report SHA-256 is `847cd6832d083e02071e649492f3a02125671fb4f2b5501f93d661a61a64c791`; compact-array SHA-256 is `f4a7babad062bd7118aef2281f883b5a3aba49350bfbd38247f145d3e8c590ab`.
- Protocol SHA-256 is `ef1d2e1b86028d1bd360e0bb149610043287ecd3f6e735ce6d2d90c5f3ac2f0b`; execution-manifest SHA-256 is `b6e94ebb800b4a0049bed264157ddf495e9e53d61426c50077de684f14065db0`.
- All input and local behavior-source fingerprints agree before and after inference. The compact bundle contains 52 finite `float32`, non-object arrays and is stored without compression.
- `held_out_accessed`, `simulator_executed`, `training_executed`, `fresh_scene_generated`, and `r3_complete` are false. `qualification_claims` is empty.
- Compact verification reopened no checkpoint, transfer, training/data manifest, development trajectory, simulator, or held-out input and did not repeat inference.

## Target support

| Component | Range | Negative / deadband / positive | Within-source sign changes | Consequence |
|---|---:|---:|---:|---|
| Velocity | 0.700 to 0.700 | 0 / 0 / 1,228 | 0 | Recorded-development targets do not test reverse or stopped commands. Velocity support is uninformative. |
| Heading | -0.306 to 3.132 | 179 / 799 / 250 | 8 | Both signs and within-source switches are represented. |

The velocity target is exactly the same positive command on every recorded-development row. Zero reverse ticks in any checkpoint therefore cannot diagnose a missing reverse capability on this split.

## Selected-checkpoint outputs

| Seed | Arm | Epoch | Loss | Velocity MAE | Heading MAE | Velocity range | Heading range | Heading counts - / dead / + | Heading changes | Heading class |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 10 | old-corpus | 20 | 0.02564 | 0.09242 | 0.19285 | 0.446 to 0.872 | -0.066 to 1.436 | 11 / 307 / 910 | 2 | `checkpoint_switches` |
| 10 | augmented | 1 | 0.05646 | 0.30926 | 0.34226 | 0.379 to 0.400 | 0.196 to 0.252 | 0 / 0 / 1,228 | 0 | `checkpoint_sign_missing` |
| 11 | old-corpus | 16 | 0.02962 | 0.04036 | 0.14042 | 0.346 to 0.691 | -0.104 to 0.786 | 150 / 947 / 131 | 5 | `checkpoint_switches` |
| 11 | augmented | 1 | 0.06049 | 0.48690 | 0.22258 | 0.193 to 0.213 | -0.082 to -0.077 | 1,228 / 0 / 0 | 0 | `checkpoint_sign_missing` |
| 12 | old-corpus | 17 | 0.02354 | 0.05725 | 0.17155 | 0.108 to 0.868 | -0.078 to 1.424 | 23 / 452 / 753 | 2 | `checkpoint_switches` |
| 12 | augmented | 7 | 0.05395 | 0.25624 | 0.25943 | 0.442 to 0.446 | -0.125 to -0.117 | 1,228 / 0 / 0 | 0 | `checkpoint_sign_missing` |

All three old-corpus checkpoints express both target-supported heading signs and switch sign within a source. Every augmented checkpoint emits one heading sign only and never switches: seed 10 is positive on all 1,228 rows, while seeds 11 and 12 are negative on all rows. The augmented action and raw-readout ranges are also narrow. This locates a descriptive heading-output-support restriction in the selected augmented checkpoints on common inputs, before closed-loop states diverge.

## Matched action differences

| Seed | First differing row | Mean absolute difference | Maximum absolute difference |
|---:|---:|---:|---:|
| 10 | 0 | 0.3033 | 1.1943 |
| 11 | 0 | 0.2750 | 0.8634 |
| 12 | 0 | 0.2492 | 1.5442 |

Every matched old-versus-augmented checkpoint differs on the first recorded-development row. This confirms that the selected policies already produce different outputs under identical inputs; it does not identify what caused those differences.

## Unequal effective training budgets

| Seed | Old selected budget | Augmented selected budget |
|---:|---|---|
| 10 | epoch 20; 42,340 row presentations; 1,440 updates | epoch 1; 7,197 rows; 236 updates |
| 11 | epoch 16; 33,872 rows; 1,152 updates | epoch 1; 7,197 rows; 236 updates |
| 12 | epoch 17; 35,989 rows; 1,224 updates | epoch 7; 50,379 rows; 1,652 updates |

The full augmented fits also used 143,940 row presentations and 4,720 optimizer updates, versus 42,340 and 1,440 for old-corpus fits. Corpus composition, source order, row exposure, update count, and earliest-minimum checkpoint selection changed together. The selected-budget direction even reverses for seed 12. These results cannot attribute the output restriction to advice labels, augmentation itself, optimizer exposure, source order, or checkpoint selection.

## Decision

The checkpoint-support prerequisite is complete. Another retrospective simulator or checkpoint diagnostic is not justified before a prospective navigation-v3 intervention. That study must change one training factor only, match old and augmented row-presentation and optimizer-update budgets, keep capability separate from topology, and reserve four fresh development scenes plus eight disjoint held-out scenes. The unchanged gates remain at least 3/4 development goals per augmented seed, then at least 6/8 held-out goals per augmented seed.

This audit is descriptive recorded-input evidence. It does not establish causality, fresh-scene navigation capability, topology advantage, biological validity, physical behavior, held-out performance, or R3 completion.
