# M7 navigation-v2 failure diagnosis amendment v1

8 October 2026. The sole amended invocation completed. It admitted all 24 owner results before trajectory decode, analyzed the frozen 10,822 ticks, and published a compact descriptive report. The original development gate remains failed and R3 remains open.

## Evidence boundary

- Amended execution: `completed-amended-diagnosis` in 5.439 seconds; this was retained attempt two and no third attempt is allowed.
- Report SHA-256: `42f11c9380d449205aa1451d8538dbe6db007f2367a819936ab02f6406a6e855`; runner SHA-256: `018df14736bd06b5fa563e135d0aae54cbf9696e004cc1fa7602ed05d483aa97`; fixed analyzer SHA-256: `a9242aad83fb69a12fd351eaa9af826bbe1df05be166094f8cb54d944509ace7`.
- Input ledger: 542 files / 2,382,058,832 bytes, canonical SHA-256 `d84998e73aee2c0136383420dba9f3668b26475f45b40f5f72cad724201b3b15`; complete before/after checks agree.
- Owner-result prevalidation: 24 results; zero trajectory members decoded during prevalidation; zero held-out paths.
- The pre-run structural metadata probe is preserved in clarification SHA-256 `2d03e2aaedc8ada337a0b8315126eb665c8f6667273ea8306303f8bb7227f588`; it printed no case, result, outcome or trajectory value.
- Compact-output verification reopened no retained producer file and did not repeat the raw analysis. Total amended output is 50,277 bytes, below the 16 MiB cap.
- `held_out_accessed`, `model_or_simulator_executed`, and `r3_complete` are false. `qualification_claims` is empty.

## Outcomes and terminal classes

| Arm | Goals | Stalled | Time limit | Terminal classes |
|---|---:|---:|---:|---|
| old-corpus | 4 | 6 | 2 | goal: 4, terminal-clear-time-limit: 1, terminal-contact-stall: 6, terminal-contact-time-limit: 1 |
| augmented | 0 | 6 | 6 | terminal-clear-time-limit: 6, terminal-contact-stall: 6 |

The augmented arm recorded no goals: six runs ended as terminal contact stalls and six as clear time limits. The old-corpus arm recorded four goals, six terminal contact stalls, one clear time limit and one contact time limit. Contact stalls therefore occur equally often in both arms; their presence alone does not explain the goal difference.

## Descriptive measures by arm

| Measure | Old median | Augmented median | Old mean | Augmented mean |
|---|---:|---:|---:|---:|
| Best progress (m) | 3.744 | 1.011 | 3.863 | 1.283 |
| Net progress (m) | 3.744 | 1.010 | 3.431 | 1.012 |
| Regression from best (m) | 0.004 | 0.002 | 0.432 | 0.272 |
| Path length (m) | 7.428 | 4.541 | 7.700 | 4.961 |
| Contact ticks | 54.500 | 26.000 | 85.333 | 45.583 |
| Terminal contact suffix | 4.500 | 24.500 | 63.833 | 42.417 |
| Terminal stall-like suffix | 26.500 | 25.000 | 25.250 | 25.000 |
| Reverse-command ticks | 0.000 | 0.000 | 0.750 | 0.000 |
| Stopped-command ticks | 0.000 | 0.000 | 49.583 | 0.000 |
| Velocity sign changes | 0.000 | 0.000 | 0.333 | 0.000 |
| Heading sign changes | 1.000 | 0.000 | 2.000 | 0.000 |
| Mean |velocity command| | 0.558 | 0.387 | 0.556 | 0.348 |
| Mean |heading command| | 0.145 | 0.121 | 0.165 | 0.148 |

Across these 12 development runs per arm, augmented trajectories had lower median best progress (1.011 m versus 3.744 m), net progress (1.010 m versus 3.744 m), and path length (4.541 m versus 7.428 m). All augmented runs had zero reverse-command ticks and zero velocity or heading sign changes under the frozen deadband; old-corpus heading sign changes ranged from 1 to 7. These are behavioral descriptions, not evidence for a causal mechanism.

## Seed-specific pattern

| Training seed | Old-corpus outcomes | Augmented outcomes | Augmented terminal classes |
|---:|---|---|---|
| 10 | goal: 2, stalled: 2 | stalled: 2, time_limit: 2 | terminal-clear-time-limit: 2, terminal-contact-stall: 2 |
| 11 | goal: 1, stalled: 2, time_limit: 1 | time_limit: 4 | terminal-clear-time-limit: 4 |
| 12 | goal: 1, stalled: 2, time_limit: 1 | stalled: 4 | terminal-contact-stall: 4 |

The augmented failures differ by training seed: seed 11 produced four clear time limits, seed 12 produced four contact stalls, and seed 10 split two-and-two. Every stalled run in either arm had a 50-tick terminal stall-like suffix, while terminal contact persistence varied. This makes a single universal failure explanation unsupported.

## Matched action divergence

Every old-versus-augmented pair crossed the frozen action-difference threshold at tick 0. The policies therefore differed from the first recorded command in every matched scene/seed; this report cannot attribute the later outcome to any one downstream event.

| Scene | Seed | First divergent tick | Mean absolute difference | Maximum absolute difference | Outcomes old -> augmented |
|---:|---:|---:|---:|---:|---|
| 3110 | 10 | 0 | 0.412 | 1.369 | goal -> stalled |
| 3110 | 11 | 0 | 0.207 | 0.467 | stalled -> time_limit |
| 3110 | 12 | 0 | 0.298 | 1.712 | stalled -> stalled |
| 3111 | 10 | 0 | 0.376 | 1.205 | goal -> stalled |
| 3111 | 11 | 0 | 0.202 | 0.455 | stalled -> time_limit |
| 3111 | 12 | 0 | 0.220 | 1.253 | goal -> stalled |
| 3112 | 10 | 0 | 0.317 | 0.426 | stalled -> time_limit |
| 3112 | 11 | 0 | 0.235 | 0.458 | goal -> time_limit |
| 3112 | 12 | 0 | 0.124 | 0.345 | stalled -> stalled |
| 3113 | 10 | 0 | 0.339 | 1.265 | stalled -> time_limit |
| 3113 | 11 | 0 | 0.117 | 0.455 | time_limit -> time_limit |
| 3113 | 12 | 0 | 0.199 | 1.535 | time_limit -> stalled |

## Per-run compact table

| Scene | Seed | Arm | Outcome / terminal class | Ticks | Best (m) | Net (m) | Path (m) | Contact ticks | Contact suffix | Stall-like suffix | V/H sign changes |
|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 3110 | 10 | old-corpus | goal / goal | 348 | 4.413 | 4.413 | 8.884 | 0 | 0 | 0 | 0/4 |
| 3110 | 10 | augmented | stalled / terminal-contact-stall | 256 | 0.000 | -1.072 | 2.794 | 52 | 49 | 50 | 0/0 |
| 3110 | 11 | old-corpus | stalled / terminal-contact-stall | 147 | 0.000 | -1.277 | 1.982 | 35 | 1 | 50 | 0/1 |
| 3110 | 11 | augmented | time_limit / terminal-clear-time-limit | 600 | 2.338 | 2.338 | 4.541 | 0 | 0 | 0 | 0/0 |
| 3110 | 12 | old-corpus | stalled / terminal-contact-stall | 475 | 3.076 | 3.076 | 5.972 | 150 | 8 | 50 | 4/2 |
| 3110 | 12 | augmented | stalled / terminal-contact-stall | 369 | 1.333 | 1.331 | 4.378 | 76 | 50 | 50 | 0/0 |
| 3111 | 10 | old-corpus | goal / goal | 415 | 6.252 | 6.252 | 10.751 | 0 | 0 | 0 | 0/2 |
| 3111 | 10 | augmented | stalled / terminal-contact-stall | 198 | 0.000 | -1.443 | 1.685 | 87 | 84 | 50 | 0/0 |
| 3111 | 11 | old-corpus | stalled / terminal-contact-stall | 271 | 0.000 | -2.422 | 4.478 | 64 | 61 | 50 | 0/1 |
| 3111 | 11 | augmented | time_limit / terminal-clear-time-limit | 600 | 2.210 | 2.210 | 4.541 | 0 | 0 | 0 | 0/0 |
| 3111 | 12 | old-corpus | goal / goal | 543 | 6.243 | 6.243 | 12.138 | 0 | 0 | 0 | 0/2 |
| 3111 | 12 | augmented | stalled / terminal-contact-stall | 419 | 2.256 | 2.256 | 5.420 | 81 | 81 | 50 | 0/0 |
| 3112 | 10 | old-corpus | stalled / terminal-contact-stall | 268 | 1.644 | 1.644 | 4.981 | 72 | 55 | 50 | 0/1 |
| 3112 | 10 | augmented | time_limit / terminal-clear-time-limit | 600 | 0.024 | -0.598 | 8.346 | 0 | 0 | 0 | 0/0 |
| 3112 | 11 | old-corpus | goal / goal | 533 | 9.281 | 9.281 | 12.460 | 0 | 0 | 0 | 0/1 |
| 3112 | 11 | augmented | time_limit / terminal-clear-time-limit | 600 | 2.850 | 2.767 | 4.541 | 0 | 0 | 0 | 0/0 |
| 3112 | 12 | old-corpus | stalled / terminal-contact-stall | 294 | 1.413 | 1.377 | 4.908 | 53 | 50 | 50 | 0/1 |
| 3112 | 12 | augmented | stalled / terminal-contact-stall | 344 | 2.999 | 2.997 | 3.795 | 107 | 104 | 50 | 0/0 |
| 3113 | 10 | old-corpus | stalled / terminal-contact-stall | 594 | 7.009 | 6.787 | 14.088 | 57 | 57 | 50 | 0/7 |
| 3113 | 10 | augmented | time_limit / terminal-clear-time-limit | 600 | 0.664 | 0.629 | 8.323 | 0 | 0 | 0 | 0/0 |
| 3113 | 11 | old-corpus | time_limit / terminal-contact-time-limit | 600 | 0.000 | -1.221 | 1.277 | 537 | 534 | 0 | 0/1 |
| 3113 | 11 | augmented | time_limit / terminal-clear-time-limit | 600 | 0.037 | 0.037 | 4.541 | 0 | 0 | 0 | 0/0 |
| 3113 | 12 | old-corpus | time_limit / terminal-clear-time-limit | 600 | 7.031 | 7.023 | 10.483 | 56 | 0 | 3 | 0/1 |
| 3113 | 12 | augmented | stalled / terminal-contact-stall | 548 | 0.688 | 0.688 | 6.632 | 144 | 141 | 50 | 0/0 |

## What this supports next

The smallest prospective follow-up is seed-stratified: inspect the augmented seed-11 clear-time-limit/no-sign-change pattern separately from the augmented seed-12 contact-stall pattern, using a new frozen study and fresh development scenes. The present report should be used to form that protocol, not to select among explanations after seeing new held-out data.

This diagnosis is descriptive. It does not establish that augmentation caused the failures, identify a model-internal cause, qualify navigation capability or topology, access held-out scenes 3120–3127, run a simulator or model, complete R3, or provide hardware evidence.
