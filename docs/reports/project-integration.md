# Combined checkout verification

The integrated checkout at `0a783af` combines the completed lab/memory mechanics,
recorded memory acquisition, exploration/homing, MaleCNS training/wrapper,
sonification/comparison and rover proposal branches. It does not include the
pending male lab integration or recorded transfer verifier.

An EGL-enabled full suite ran 319 tests in 66.660 seconds: **316 passed and three
explicit MaleCNS asset/opt-in checks skipped**. The supervised child exited 0 in
70.240 seconds under a 240-second bound. Runtime and test hashes stayed unchanged.
The one-off outer reporting script exited 1 because it read `exit_code` instead
of the existing supervisor's `returncode` field. This reporting error and the
unaltered log/report/script are retained; the suite was not rerun.

Cached offline npm installation, production build, seven UI measurement checks
and memory annotation checks passed in this checkout. These are build/fixture
results, not a new browser endurance or full-model navigation claim.

The [evidence index](project-integration.json) preserves logs, bounds, skipped
coverage and hashes. Each historical actual model/task report still names its
original source. Unified qualification and remaining M5–M10 gates remain open.

After the atlas and export-close cleanup merges, 48 focused export/CLI tests
passed at `0693a2f` in 2.755 seconds with no skips. The merged atlas CLI also
exported the pinned actual graph; full task and endurance gates were not rerun.

At `77e69da`, the male controllers are integrated with the acquisition/task
branches. All **330 tests pass, no skips**, in 84.558 seconds with actual EGL,
MaleCNS Torch and native/replay gates enabled. The 300-second supervisor exits
zero in 88.045 seconds; runtime/test hashes remain unchanged. The merged UI
build, seven measurement checks and memory annotations also pass. This regression
does not repeat historical held-out or endurance qualification.

At `7a51346`, the recorded transfer verifier/negative evidence and wheel-response
diagnostic are integrated. All 62 focused memory/history/recording/contact checks
pass in 3.083 seconds, no skips. This checks the merged logic without rerunning
the source-scoped physical simulation experiments.

At `8c74181`, the committed male asset bundle, audited 16-run male evaluation,
visible-preparation memory verifier and measured body compensation are integrated.
All **363 tests pass, no skips**, in 58.919 seconds with actual EGL, male Torch
and native/replay gates enabled. The 300-second supervisor exits zero in
61.363 seconds. Runtime, test and environment-lock hashes remain unchanged.
The actual male mechanism check uses this checkout's tracked inference assets.
This regression preserves the negative task outcomes in their separate reports;
it does not establish useful navigation, memory transfer or online adaptation.

At `68a8f19`, loaded body compensation, goal-handoff memory v4, Afterimage and
anatomical pairs are integrated. All **395 tests pass, no skips**, in 56.706
seconds with actual EGL, male Torch, native continuation and replay gates enabled.
The 300-second supervisor exits zero in 58.875 seconds. Runtime/test/lock hashes
remain unchanged, and the separate actual male mechanism report passes.

The first combined attempt at `3932034` ran 395 tests in 58.927 seconds with one
fixture error. Its scenario loop saved the first profile as a reproduction
snapshot; the newly first manual-only body profile correctly rejected a teacher
replacement. The one-line test fix selects `reproduction` by identity. Product
controller restrictions are unchanged. Both attempts and their hashes are retained
in the evidence index. This regression does not qualify historical task outcomes,
online adaptation, exhibition operation, or physical hardware.

At `eda9ba3`, the all-nine memory dispatcher, corrected body replay metadata and
frozen staged MaleCNS research path are integrated. All **414 tests pass, no
skips**, in 82.272 seconds with simulation, male Torch and native/replay gates
enabled. The 300-second supervisor exits zero in 85.705 seconds. Source/asset
inventories and production model identities remain unchanged; the independently
rehashed evidence index retains every gate artifact. The shared combined asset
root is supplied explicitly. Actual male checks use the original pinned v1
controllers, not the still-untrained research candidates. Adaptive calibration
and fixed-FLYNN acquisition continuation remain separate work. This regression
does not rerun historical task, endurance, held-out, exhibition or physical gates.

At `f233a72`, the adaptive calibration session and Engine/native/replay/UI glue
are integrated. All **427 tests pass, no skips**, in 103.927 seconds under the
300-second supervisor (exit zero, 107.159 seconds). Source/asset inventories and
production model identities remain unchanged; all 50 retained gate artifacts were
independently rehashed. Actual profile coverage includes one adaptive tick. The
full four-probe fit, partial/fitted native continuation, adaptive executable
replays, paired compensation metrics and browser workflow still require their
separate frozen gate. Male runtime checks continue using the production v1 models.

## Atomic fixed-FLYNN memory integration regression

Frozen combined source `a15b07cb88ec30ecc5e1b9a1b7f9c5fbde55f021` passed all 435 tests without skips in 98.824 seconds (101.975 seconds supervised). Simulation, male Torch and male native/replay gates were explicitly enabled using verified shared assets. The 300-second supervisor exited zero; source, assets and production model identities stayed unchanged. Root rehashed all 50 retained files and checked terminal unittest output.

Report: `runs/integration-memory-a15b07c-20261002/report.json`, SHA256 `ae26a7d23472f09891534bf70b864fb8ddadb7673a386d17216b135d5a1cea8b`. The atomic memory admission tests mock native/model boundaries; the separate full CPU FLYNN memory experiment remains unexecuted. Actual male checks retain v1 production assets. This regression does not rerun historical task/endurance qualification.

The subsequent CI fixture run exposed process-environment leakage from the mocked atomic-open failure test: it left `MUJOCO_GL=egl` and `MPLBACKEND=Agg`, so 13 later native snapshot imports failed on runners without EGL. The enabled local suite already supplied EGL and did not expose this ordering bug. The exact absent-setting reproduction failed before fixture-only `4f0df2b` and passed afterward. Eight admission fixtures pass (0.587 s); admission followed by native snapshot checks with both variables initially unset runs 24 tests, 21 passing and three explicit opt-in renderer skips (4.682 s). Runtime code is unchanged; original failed CI logs remain retained in GitHub run 37036574437.

At `f4addb3`, the separate fixed-CPU-FLYNN memory verifier is integrated. All
108 focused memory, Engine, replay and male research checks pass without skips
in 7.795 seconds. This is fixture validation; the 12-stage neural run has not
yet executed. Both CI workflows pass on the preceding `00999c1`; CI for this
new verifier is tracked separately.

At `81dd5f2`, the 12-owner adaptive calibration verifier is integrated. All
73 focused calibration, Engine, replay, memory-admission and male research checks
pass without skips in 21.007 seconds. The replay merge preserves atomic memory
restoration and adds the optional recording cap; default calls are unchanged.
The full adaptive gate remains pending. Both CI workflows pass on the preceding
`b283657`, independently of these focused checks.

At `d2a07eb`, the fixed thin-puck protocol and pure task primitives are integrated.
All 46 focused puck/task/body checks pass without skips in 0.494 seconds. This
covers XML derivation and task arithmetic only; native model construction, contact
dynamics, runtime integration and learned manipulation remain untested.

## Adaptive calibration and staged puck regression

Frozen combined source `54ef2001423c611240f7b6db856737473d909e96` passes all **483 tests without skips** in 114.812 seconds. The 300-second supervisor exits zero in 117.192 seconds. Simulation, male Torch and native/replay gates are enabled with the verified shared assets and unchanged production v1 models. Source/asset inventories remain unchanged; all 50 retained files were independently rehashed. Report `runs/integration-adaptive-puck-54ef200-20261002/report.json` has SHA256 `f199d0e28f0a882c5f769ae0ecc5174169f1550a0b858df8993a3c39041a01e1`.

The combined source includes bounded executable memory replay, the adaptive verifier correction, and staged fixed-puck installation/reset. The preceding 55 focused puck/task/body checks pass in 0.633 seconds; an initial invocation omitted `tests` from `PYTHONPATH` and failed one module import before the corrected command. Puck fixtures check atomic ownership and rollback; native construction remains a separate gate.

The separate [adaptive v2 gate](m6-body-adaptation-v2.md) now passes on its frozen source, and both own-source fixed-FLYNN executable replays pass. Those results supersede the earlier pending-work notes above without changing the historical regression scope. This combined suite does not repeat task, held-out, endurance, exhibition or physical qualification.

## Counterbalance, task phases and defined puck state regression

Frozen combined source `60f8e3306f2da11f4a5f81518ef9a7f671b7f0b8` passes all **506 tests without skips** in 116.115 seconds. The 300-second supervisor exits zero in 117.872 seconds. Actual simulation, male Torch and native/replay checks are enabled with the verified shared assets. Tracked source, assets and production v1 model identities remain unchanged; all 50 retained artifacts were independently rehashed. Report `runs/integration-counterbalance-task-puck-60f8e33-20261003/report.json` has SHA256 `559873a8c5642f9d90d8f06517d1457b69e07dee73344d75dff5f3d1509cd41a`.

This covers the shared subject-ID handoff correction, fixed memory admission, task-phase verifier and defined native-data comparison fixtures. The separate actual task-phase and zero-step puck gates retain their frozen sources. It does not repeat historical experiments or establish held-out, stepped-puck, exhibition or physical qualification.

## Task starts, puck mechanics and memory comparison regression

Frozen combined source `3a0b085ea376d7cedf4bd6d533233e30b1e1b6cc` passes all **534 tests without skips** in 117.106 seconds. The 300-second supervisor exits zero in 119.985 seconds. Actual simulation, male Torch and native/replay checks are enabled with unchanged shared assets and production v1 models. Tracked sources and model/asset identities remain unchanged; all 50 retained files were independently rehashed. Report `runs/integration-starts-mechanics-comparison-3a0b085-20261003/report.json` has SHA256 `eea74d702e234887e71b8662a2fde1f4bab61c6bff5778d5bed9d0d5ba590e90`.

This adds the held-out task-start, fixed puck mechanics and four-cell memory-comparison fixtures. The separate [task-start gate](m6-task-heldout-starts.md) passed its declared four cases and replays. The [first actual puck mechanics run](m6-puck-mechanics-v1.md) passed stability and constant pushes, then failed its first teacher by natural time limit; six later checks remain unstarted. The [first memory comparison launch](m5-counterbalance-stage-c-v1.md) failed UUID path validation before starting any owner. Passing this regression does not change those experiment outcomes or establish learned, broader held-out, exhibition or physical qualification.

The subsequent UUID path fix `c626f3c` passes seven focused comparison checks in 0.412 seconds on its branch, including an unmocked validator with accepted and rejected IDs/paths. Both CI workflows passed at integration `c3aa701` before this fix was merged; that CI result is not attributed to the new source.

## Corrective source and retained-fit turn regression

Frozen combined source `ff0520a5001c7ad2d1a380b7e8b2bbf931506ca5` passes **547 enabled tests without skips** in 122.303 seconds (125.254 seconds supervised, exit 0 under 300 seconds). This includes the UUID path fix, v2 puck target selection, and six-trial turn verifier with the extracted existing metric kernel. Source, assets and production model identities stayed unchanged; all 50 retained files were rehashed. Report `runs/integration-fixes-turns-ff0520a-20261003/report.json`: SHA256 `1ad3e337ceee7c390e48b17da45e0a60338b8bdc7ec01cff5e2e50410f09943c`; launcher SHA256 `bc94ad6bd630b6d37345889cce08df4eff2c52dc007a45160d064e7d41251d87`.

The separate second puck mechanics attempt still fails its positive teacher by natural time limit; its retained evidence is under audit. Memory C1 started no owners, and its fresh C2 controls await the sequential runtime slot. The new body-turn gate has not executed. Regression success does not change those task outcomes.
