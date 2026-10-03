# M5 controller-reference replay v2: six executable replays pass

All six fixed s24 actions/policy replays passed at executor source `9dd805d`, using unchanged reference producer `169e0c8` and its three original recordings. The [JSON evidence index](m5-controller-reference-replays-v2.json) binds source/SNP identities, controls, recording chunks, terminal reports and local/root audits. The [v1 zero-row infrastructure failure](m5-controller-reference-replays-v1.md) remains immutable; v2 applied only the reviewed verifier call-site `Path` conversion, with fresh IDs and output.

| Reference | Actions rows | Policy rows | Goal boundary in both replays |
| --- | ---: | ---: | ---: |
| Original FLYNN checkpoint | 129 | 129 | 429 |
| Visible-goal/contact script | 124 | 124 | 424 |
| Privileged analytical teacher | 118 | 118 | 418 |

The 742 compared rows comprise **371 saved-action rows, 129 real neural policy inference rows and 242 non-neural policy rows**. Actions replay executes saved motors without inference. Sensor/teacher policy replay executes its declared non-neural controller. All six registered initial SNPs match their original sources under exact typed state equality, excluding only `application.source_run_id`, `event_prefix` and `execution_mode`; memory, controller/teacher, RNG, native/environment, case and command state remain in the guard. Runner lifecycle comparisons passed: 521 events per original replay, 501 per sensor replay and 478 per teacher replay.

The local NumPy-only audit passed on its first invocation in 11.406070182 seconds, checking 560 frozen input identity entries, all 742 rows, six destination and three source SNPs, mode/inference flags, source immutability and eight absent sampled non-launcher PID/start identities. Root's independent NumPy-only audit passed on its first invocation in 3.322777538 seconds: all 742 typed numeric rows had maximum absolute error **0**, all six normalized initial SNPs matched, all 622 scoped entries (560 inputs plus 62 destination files) rehashed, and eight sampled exits were absent. Root did **not** independently recompute lifecycle event comparisons; those remain bound runner evidence. Neither retained audit imported a native/model runtime or recomputed neural inference. Root receipt SHA256: `210c212237cecf8881cbaea66384cf314a2164ea8223939cf7f7838656ac1eef`.

Outer supervision completed with exit 0 and operational pass after 153.546908178 seconds including 0.122815781 seconds normal cleanup. Before/after identity inventories are byte-identical; no survivors, forced signals, watchdog messages, monitor errors or retries occurred. The exclusive native slot was released after terminal cleanup. Separate count scopes are retained: 38 recording references; 62 indexed destination recording/SNP/replay/worker files / 155,359,889 bytes; all 89 output files / 155,805,585 bytes; and the broader 78-file evidence index / 156,186,959 bytes. These counts do not include one another interchangeably.

Aggregate report SHA256: `3f36f4a00b89325e08ae050a4f26db2c2603ccebc48ff6f9b2868c31a1bc6465`. Outer report: `027d96e8d2b6398486849e841fa29609fbf05195141336020dbfe123f174b3a3`. Root raw audit JSON: `f696eaa0909f58fbbda333b20a73f51885fe4d7e828282b7ba1947755e3a6323`.

This qualifies executable replay of the three development references. Their information remains unequal: upstream true-pose goal bearing, visibility-limited goal/contact script, and privileged current-map teacher. Replay repeats existing trajectories; it adds no independent task trials, acquisition, held-out result, memory benefit or R2 completion. Earlier own-U null/negative outcomes and the full remaining research scope are unchanged.
