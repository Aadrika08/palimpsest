# Loaded-calibration body runtime: development verification v2

One actual manual-CPU MuJoCo/EGL invocation passed at frozen commit `5dcd125d78fc228afacdc582f54ac612a8e59aa8`. This verifies execution, native continuation and same-source replay for a fixed loaded wheel calibration; it does not demonstrate online adaptation, learning or physical rover qualification. UI build/browser verification remains pending.

The [primary report](../../runs/m6-body-runtime-development-v2-20261002/report.json) SHA256 is `7a02137402ba64c8235e252a808c9690691d19c13118dc31463703b2c9f9059f`. [Invocation and outer supervision](../../runs/m6-body-runtime-launch-5dcd125/invocation.json) retain the exact argv/environment and 780-second watchdog; inner owners each had 180 seconds. Outer elapsed time was 19.614429357 seconds, inner 19.279546719 seconds. All four owner leaders and the outer verifier exited 0.

| Owner | Numeric ticks | Pre-control caches | End caches | Retained contact pairs |
|---|---:|---:|---:|---:|
| Source: 24 + 4 + reset 8 | 36 | 360 | 36 | 26,136 |
| Fresh native-restored continuation | 4 | 40 | 4 | 2,904 |
| Actions replay | 36 | 360 | 36 | 26,136 |
| Policy replay | 36 | 360 | 36 | 26,136 |
| Total | 112 | 1,120 | 112 | 81,312 |

An [independent raw-record scan](../../runs/m6-body-runtime-development-v2-20261002/independent-audit.json), using `iter_ticks` without the harness audit or comparator, checked all 45 indexed artifact hashes, retained contact classifications and finite distances, all unused zero slots, stage times/controls, encoder increments/continuity and effective float32 control round-trips. The four native continuation ticks and both 36-tick replays had exact equality in checked cameras, action/control and every raw body array; maximum absolute floating difference was zero. The declared comparator permits floating absolute/relative tolerance 1e-6 and requires exact cameras/integers.

Forward nominal action `[0.3, 0]` produced controls `[0.7532490491867065, 0.6210575103759766]`; the reverse episode produced their exact negatives. Maximum observed absolute shaft rate was 9.11128620965 rad/s. Across owners, the retained pairs were 73,920 world-only and 7,392 allowed rover-floor support, with zero unexpected robot contacts. World-only pairs remain recorded and may move. Coverage is ten discrete pre-control caches plus the repeated final cache, not continuous collision or an additional post-integration contact computation.

The fresh destination rejected both a malformed typed encoder and a finite encoder inconsistent with native data before mutation. Full captured state digest and native model/data addresses remained unchanged. Reset retained the pinned model and loaded fit while clearing manual intent and initializing the new episode's encoder/time cursor. Both replays compare 36 ticks; action replay applies recorded effective action once, while policy replay recomputes from nominal manual intent.

The loaded fit artifact is pinned to SHA256 `9d2cd4729d32f84b490db3a6726764111989fcc80be74c7a2ba44a97cb419331`; actual perturbed native model SHA256 is `bf3ca4b0d32600444e0f23e658c790da50a7675fb3c26fee8f9b0a16e0839d67`. Body profile SHA256 is `e4d16329c12fbd91b09e6eb98894b2c9d86b4b086b34409054d5a134b0bd2751`. V2 separately records the historical calibration world identity and current full world identity; fresh setup pins current authoring source and semantic geometry. Strict same-software replay compatibility remains unchanged.

Runtime source, assets and the progress snapshot were unchanged. Each owner reported Engine closure and restored global contact callback. All four finitely sampled PID/start-time identities were absent at the final check; the sampler stopped without errors. No server/listener was created. Sampling at 0.25 seconds cannot prove observation of every transient descendant. The existing supervisor performs TERM/KILL group cleanup after leader exit; this evidence makes no stronger signal-disposition claim. Retained logs contain four existing PyTorch TF32 API deprecation warnings, with no semaphore/resource-tracker/Traceback/Error match.

The [v1 zero-tick startup failure](m6-body-runtime-v1.md) and immutable raw report remain preserved. V2 corrects its stale source-inclusive authored-world guard without changing fits, actions, scene geometry, bounds, trial counts or replay source checks. This gate does not refit gains, change odometry, qualify transient/combined-motion performance, demonstrate task completion or expand the prior calibration evidence. See the [frozen protocol](../plans/m6-body-runtime.md) and [machine-readable evidence index](m6-body-runtime-v2.json).
