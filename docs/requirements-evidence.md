# Requirements and evidence

**M3 / R1 is complete under the reviewed contract and PRD §21.3, with documented limitations.** This matrix follows the unchanged [PRD requirements](borrowed-body-prd-v1.md#7-functional-requirements), performance/resource requirements (§17), local/privacy/licensing limits (§18), and acceptance criteria (§21). Runtime `c43f5df` has 195 passing EGL-enabled tests, two normal restored full-model CPU-FLYNN close checks, and passing natural manual/teacher throughput. The [fresh mixed hour gate][hour] **passes all eight gates** in 3600.000099 seconds:29 complete cycles (manual 10/teacher 10/Flynn 9),58 passed executable replays and116 closed/completed dispositions. A documentation entry or implementation check is not release qualification.

The [M3 report](reports/m3-release-hardening.md) and [JSON evidence index](reports/m3-release-hardening.json) retain exact identities and limits. Browser/offline/smoke observations below retain their historical source commits; they are not inferred reruns on `c43f5df`. Raw bundles under `runs/` are retained local ignored artifacts; the committed report/JSON index carries their identities and limitations. Test links identify runnable coverage, including fixtures. “Observed” identifies a separately retained actual-runtime result.

## Functional matrix

| PRD ID and acceptance boundary | Runnable coverage | Observed evidence and limits |
|---|---|---|
| LAB-001: cached local launch without mandatory remote services | [Doctor/assets/CLI tests][cli]; [offline driver][offline-script] | [Offline index][offline] passes fresh cached setup, full CPU-FLYNN verification and manual/teacher HTTP/WebSocket smoke in an isolated network namespace on `ec1d2e6`. Caches and verified assets required; no host-network mutation. |
| LAB-002: validated scenario/controller pairs reject incompatibility before stepping | [Profile tests][profiles]; [Engine validation][engine] | [195-test index][suite] includes actual six-scenario/mask/controller-replacement checks. Only registered profiles are supported. |
| LAB-003: run, pause, reset, stop and exactly one control tick | [Engine boundaries/idempotency][engine]; [spawned owner tests][lab] | [Natural completion][performance] records contiguous 20 ms ticks and frozen endings; [suite] includes actual step/branch/disconnect. Queue/receipt checks also use fixtures. |
| LAB-004: distinct termination, truncation, operator stop and runtime failure reasons | [Engine endings][engine]; [evaluation tests][evaluate] | [Performance][performance]: manual time-limit truncation, three teacher goal terminations. Fault/stop tests retain distinct reasons; earlier close failures remain failures, not task endings. |
| LAB-005: each acknowledged intervention applies once at a boundary or explicitly rejects | [Engine duplicate/revision tests][engine]; [preview/edit tests][interventions] | [Suite][suite] includes actual MuJoCo world edits. [Browser workflows][browser] exercise preview/application on `ec1d2e6`; no guarantee for arbitrary articulated-body edits. |
| LAB-006: world, actual inputs and inspection samples share identifiers | [Artifact transition tests][artifacts]; [browser tests][ui] | [Browser][browser] workflows pass aligned panels. Receipt p95 **43.4 ms**, application p95 **53.8 ms**; full-window updates **27.9809 Hz**, below the 30 Hz target. Callback opportunities are not fresh-data frames. |
| LAB-007: manual, privileged teacher and FLYNN paths without substitution | [CLI][cli]; [Flynn loader/adapter][flynn] | [Offline][offline] exercises all three CPU paths; [240-second Flynn smoke][smoke] completes two cycles/four replays. Small inference sample, not continuous inference; CPU Flynn slower-than-real-time is allowed and labelled. |
| LAB-008: student observations exclude privileged evaluator state | [Flynn leakage/camera parity][flynn]; [Engine allowlist/masks][engine] | [Suite][suite] tests real upstream tiny recurrent fixtures and actual masks. Teacher privilege remains explicit. [R0 parity][r0] is historical full-model evidence; original training lineage is unknown. |
| LAB-009: actions, observations, events, configuration and metrics form a replay profile | [Lossless recording/integrity][records]; [recovery][recovery] | [Offline][offline] and [smoke][smoke] retain executable CPU-FLYNN replays. Published-prefix recovery tests include fixture owners/physics; incomplete runs are not completed replay sources. |
| LAB-010: complete physics, policy, wrapper/RNG/application snapshots | [Snapshot tests][snapshots]; [fresh-process verifier][execution-script] | [Suite][suite] includes actual MuJoCo contact/recovery and ending crossings; tiny upstream recurrent-state continuation. [Offline][offline] has four exact full-model CPU continuation ticks; [M1][m1] has historical 100-tick CPU continuation. CUDA exact continuation remains failed/unqualified. |
| LAB-011: visibly distinct playback, action replay and policy rerun | [Replay tests][replay]; [UI tests][ui] | [Browser][browser] labels/control workflows and manual replays pass; [offline][offline] full-FLYNN action/policy replays each pass 8 ticks/22 events. Action replay bypasses inference; completion alone is not agreement. |
| LAB-012: sequential comparison exposes provenance before interpretation | [Artifact comparison tests][artifacts]; [UI comparison][ui] | [Browser][browser] sequential branch comparison passes. Exploratory route differences do not establish a causal intervention effect or scientific improvement. |
| LAB-013: exported route coordinates and machine-readable bundle match records | [Artifact geometry/bundle checks][artifacts]; [CLI export][cli] | [Browser][browser] export workflow and [offline][offline] full-model exports pass on their sources. Bounds, hashes, whitelist and world-coordinate projection are tested; no physical-route claim. |
| LAB-014: configured disconnect/failure behavior preserves records/state | [Owner/watchdog/disconnect][lab]; [recovery][recovery]; [IPC/log completion][worker-logs] | [Suite][suite] passes; [two normal CPU-FLYNN closes][close] exit 0 on `c43f5df`. Earlier failed hour/5-second close remain in [M3 report](reports/m3-release-hardening.md#hour-gate-failure-and-teardown-investigation). [Fresh hour][hour] passes; finite sampled workload, not continuous inference. |
| LAB-015: invalid outputs/timeouts stop and preserve diagnostics | [Flynn NaN/infinity/shape guards][flynn]; [watchdogs][lab]; [log-drain tests][evaluate] | [Suite][suite] passes guard/fault tests; raw invalid values are preserved in bounded diagnostics before sanitization/stepping. Full-model invalid-output fault injection is not claimed. |
| LAB-016: documented headless evaluation and dependency diagnostics | [Doctor tests][doctor]; [CLI/evaluation][cli] | [Final integration index][integration] retains actual 30-tick teacher CLI evaluation on `a24c237`; [offline][offline] retains headless full-model verification. See existing setup/evaluation commands below. |
| ART-001: real trajectory overlay cannot alter agent input | [Artifact geometry][artifacts]; [overlay/input-isolation UI test][ui] | [Browser][browser] actual manual overlay and keyboard/error recovery pass on `ec1d2e6`. This is evaluator-only presentation; marks affecting cameras would require a different scenario. |

## Later requirements: current implementation and missing release evidence

These rows extend the R1 matrix without promoting development observations to
R2–R5 qualification. Full later release gates remain in the
[implementation plan](implementation-plan.md).

| PRD ID | Implemented and runnable evidence | Remaining boundary |
| --- | --- | --- |
| MEM-001 | [M/E/U schemas and hashes](../src/palimpsest/memory.py); `test_memory`, `test_memory_task`; [actual M4 evidence](reports/m4-memory-mechanics.md). | No claim that neural hidden state is this explicit memory representation. |
| MEM-002 | Selection changes uncertainty/inspection requests, never factual payloads; `test_memory` and `test_memory_task`. | Useful held-out targeting and closed-loop effects remain pending. |
| MEM-003 | Explicit abstention, unobserved samples and evidence-only factual revisions; actual one-episode history abstains, four-episode histories fit. [Recorded-history report](reports/m5-recorded-history.md). | Missing evidence is not an unchanged negative label; no R2 result. |
| MEM-004 | Native U-only branching with complete invariant hashes, sham checks and actual full-FLYNN CPU continuation/replay. [M4 report](reports/m4-memory-mechanics.md). | Same software/numerical regime only; CUDA repeatability is unqualified. |
| MEM-005 | [Nine targeting baselines](../src/palimpsest/memory_experiment.py), synthetic development fixtures, recorded E and [one actual four-branch transfer case](reports/m5-recorded-transfer.md), whose combined task outcomes all fail. [Visible-preparation v2](reports/m5-visible-preparation.md) passes initial visibility but loses the goal before committing the observed revision. [Goal-handoff v4](reports/m5-goal-handoff-v4.md) passes six stages: all four continuations repair at354/reach goal426, establishing no own-U task or timing advantage. | [All-nine manual development](reports/m5-all-nine-development.md) completes two cases/18 continuations with identical correction/goal times and no own-U task/timing advantage. [Actual fixed CPU FLYNN development](reports/m5-flynn-memory-transfer.md) completes all nine neural conditions: correction at 358 and goal at 429 in every case, with no own-U task/timing benefit. Actual replay, counterbalanced/null/no-event cases and frozen held-out evaluation remain missing. |
| MEM-006 | Deterministic bounded `fit(E)` outside motor inference; [collector](../src/palimpsest/memory_history.py) verifies complete recorded sensor histories. | No LLM runtime dependency; history information and privileged baseline access must remain labelled. |
| ART-002 | Memory observations/decisions/inspection events carry tick and evidence IDs; route/UI annotations covered by `ui/tests/memory-events.check.ts` and actual M4 browser flows. | No useful-memory or route-improvement inference from an annotation alone. |
| ART-003 | [Sonification and comparison exports](artwork-mappings.md) and [connectivity atlas](artwork-atlas.md) and [curated anatomical comparison](artwork-specimens.md), individually requested offline mappings with embedded provenance; actual short recorded derivatives/browser checks. | Anatomical geometry/provenance and browser checks pass in the [specimen evidence](reports/m9-specimens.md). [Afterimage](artwork-afterimage.md) now passes actual eight-frame reference/render and browser checks with retained [evidence](reports/m9-afterimage-validation.md). Declared-duration exhibition, independent operation and physical drawing remain incomplete; the [operator runbook](exhibition-runbook.md) states the required acceptance record. |
| HW-001 | [Reviewed-cost proposal](rover-procurement-proposal.md); no actuator path released. | Components/operator, electrical and lifted-wheel checks, fault injection, measured stopping/thermal deadlines and enclosed floor trials are required. |

Additional M6 task, M7 model and M9 artwork gates are broader than these IDs.
Exploration and homing have manual development demonstrations with native/replay
evidence; [measured wheel response](reports/m6-body-gains-v2.md) and [fixed-gain compensation](reports/m6-body-compensation.md) pass their standalone development gates. [Loaded runtime compensation](reports/m6-body-runtime-v2.md) passes its bounded actual source/reset/native/replay gate; its [actual UI gate](reports/m6-body-ui.md) passes snapshot/reset, keyboard controls and 26-tick action replay at `cbe1a3d`, with both earlier failed attempts retained. The [measured calibration session](plans/m6-body-adaptation.md) now implements four fixed probes and a new-fit episode with conditional native state and replay handling; fixtures/build and the 435-test combined regression pass. Its first actual gate passes source/native/replay checks before a retained verifier-envelope failure; paired adaptive metrics remain unfinished. The [thin-puck task core](plans/m6-puck-pushing.md) is implemented and fixture-checked; native construction, demonstrations and learned manipulation remain pending.
The reduced MaleCNS pilot has separate training and recorded-input held-out
scores, with a guarded CPU wrapper, native/replay integration and [actual live browser workflow](reports/m7-live-lab.md); it does not establish closed-loop navigation,
biological sensing, topology benefit or population-wide sex differences. The [16-run closed-loop evaluation](reports/m7-closed-loop-v2.md) completed with only 0/8 original and 1/8 control goals; The [three-seed v2 development gate](reports/m7-training-v2-stage-c.md) completes all 24 runs, but original seed 11 reaches only 1/4 goals, failing the frozen per-seed admission threshold. Both held-out stages stay locked; R3 remains incomplete.
The [combined regression](reports/project-integration.md) passes 435 tests without skips at `a15b07c`, including actual EGL/male continuation and replay. M10 handoff remains partial while the task, model, artwork and physical gates remain open.

## Runnable checks and operating instructions

These are references for a future serialized test window; serialize actual jobs and use new output directories. From the prepared checkout:

```sh
PALIMPSEST_SIMULATION_TESTS=1 MUJOCO_GL=egl OMP_NUM_THREADS=2 \
  PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
npm --prefix ui run test:measurement
```

Actual browser workflows use `npm --prefix ui run test:browser` against the existing loopback lab; opt-in cadence measurement uses `npm --prefix ui run test:performance`. [UI configuration](../ui/playwright.config.ts) declares browser/base-URL overrides and one worker. These commands are runnable coverage, not additional passes from this documentation task.

Reuse [README setup/assets/lab/evaluation instructions](../README.md) and the [hardening runbook](reports/lab-hardening-runbook.md): recovery boundaries, natural sustained execution (`--finish-episode`), OS-level offline proof, and the mixed hour gate are separate protocols. New output directories preserve earlier reports. [The full offline driver][offline-script] adds cached setup/full-FLYNN options; existing assets must be supplied explicitly if outside the checkout.

## Operational and qualification limits

| Area | Implemented or observed boundary | Remaining limit |
|---|---|---|
| Setup and trusted assets | Locked Python/Node dependencies, pinned upstream, read-only doctor, explicit fetch/verify/prepare; [manifest][manifest] records hashes/mappings/terms. | Missing assets fail informatively; no controller/device fallback. Offline pass uses caches and shared assets, not an uncached install. |
| Local service/security | [Lab tests][lab] cover loopback host/origin/session, WebSocket authentication, bounded bodies, IDs and path rejection; [artifact tests][artifacts] reject unsafe bundle fields. | Trusted verified checkpoints/snapshots only. Native snapshot decoding is not a hostile-import sandbox. No LAN exposure or arbitrary checkpoint upload claim. |
| Recovery and shutdown | [Runbook](reports/lab-hardening-runbook.md#recovery-boundaries) describes verified published-prefix inspection and fresh owners/registered branches. `c43f5df` finishes runtime/log cleanup and joins outgoing queues before process exit; [close] records exit 0 twice. | Do not promote orphan chunks or unacknowledged commands. Python cannot cancel kernel-blocked I/O; watchdog/diagnostic bounds do not prove universal cancellation. |
| Quotas and retention | [Storage tests][storage] cover aggregate bytes/free-space/counts, staging overlap and single-writer lease; [records] preserve published prefixes. README documents quota flags and manual archive/removal after closing the lab. | No automatic deletion. Quotas bound managed outputs, not an unlimited historical archive; retain failed manifests/events/logs/reports. External portrait/visitor recording is not this synthetic-sensor profile. |
| Performance/endurance | [Performance][performance] passes manual/teacher active RTF **1.000337227 / 1.000342527**; outer RTF **0.998503646 / 0.988887495**. [Browser][browser] receipt target passes; cadence target is explicitly unmet. | Host/profile-specific narrow margins. [Hour][hour] passes with 712 finite resource samples, one owner, bounded growth and explicit server SIGTERM shutdown; no universal no-growth proof. Full-FLYNN CPU has no ≥1× gate; CUDA repeatability is unqualified. |
| Licensing/provenance | [Third-party notices][notices] retain upstream MIT notice and separate CC BY-NC 4.0 graph/checkpoint terms; [manifest] pins downloaded identities. Asset/licence and graph-structure checks are in [assets tests][assets-tests]/[Flynn tests][flynn]. | Notices do not assign a licence to Palimpsest's own code. Per-asset terms are not blanket permission for commercial/exhibition use. Original checkpoint training graph/ordering remains unknown; verified files establish present identity/compatibility only. No MaleCNS licence substitution. |
| Research/hardware | Fixed pretrained weights, labelled privileged teacher, exact cameras/integers and fixed float tolerances; [R0][r0]/[M1][m1] retain source/numerical scopes. | The original FLYNN weights remain fixed; separate reduced MaleCNS pilots were trained. No topology advantage, living-fly/consciousness or physical capability claim. Hardware procurement/qualification is blocked; hardware is not required for R1. |

The documentation matrix, linked operating instructions and licence/provenance limits are prepared. Their commit/publication and final release review remain separate gates in the [M3 contract](plans/m3-release-hardening.md). No unbounded, continuous-inference, full-model real-time or physical qualification claim is made.

[cli]: ../tests/test_cli.py
[profiles]: ../tests/test_profiles.py
[engine]: ../tests/test_engine.py
[lab]: ../tests/test_lab.py
[evaluate]: ../tests/test_evaluate.py
[interventions]: ../tests/test_interventions.py
[artifacts]: ../tests/test_artifacts.py
[ui]: ../ui/tests/lab.spec.ts
[flynn]: ../tests/test_flynn.py
[records]: ../tests/test_records.py
[recovery]: ../tests/test_recovery.py
[snapshots]: ../tests/test_snapshots.py
[replay]: ../tests/test_replay.py
[worker-logs]: ../tests/test_worker_logs.py
[doctor]: ../tests/test_doctor.py
[storage]: ../tests/test_storage.py
[assets-tests]: ../tests/test_assets.py
[offline-script]: ../scripts/verify_offline.py
[execution-script]: ../scripts/verify_execution.py
[suite]: ../runs/m3-module-exit-validation-20261002/report.json
[performance]: ../runs/m3-performance-after-module-exit-20261002/report.json
[offline]: ../runs/m3-offline-full-20261002/offline-index.json
[browser]: ../runs/m3-ui-evidence/20261002T080624Z/final-verification.json
[smoke]: ../runs/m3-flynn-smoke-20261002/report.json
[close]: ../runs/m3-flynn-close-validation-20261002b/report.json
[integration]: ../runs/m3-validation-20261002/report.json
[r0]: reports/r0-reproduction.md
[m1]: reports/m1-execution.md
[manifest]: ../model_manifests/flynn-full-vision.json
[notices]: ../THIRD_PARTY_NOTICES.md

[hour]: ../runs/m3-endurance-hour-20261002b/report.json
