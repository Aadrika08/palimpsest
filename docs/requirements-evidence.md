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
| MEM-005 | [Nine targeting baselines](../src/palimpsest/memory_experiment.py), recorded E, full CPU FLYNN continuation and executable replay. [C3](reports/m5-counterbalance-stage-c-v3.md) and [C4](reports/m5-counterbalance-stage-c4.md) cover eight selected development cells, 80 owners and 9,349 neural intervals; all 72 evaluator task checks pass. C4 verifies sixteen strict U-only core forks. | No own-U correction/goal benefit was observed. Null cells have seven false-targeting selectors each; no-event conditions have zero invocations. The [first remaining admission](reports/m5-remaining-01-admission.md) completes twelve owners/1,204 rows/four calls, independently audited; its task/timing fields are censored. The [first remaining comparison](reports/m5-remaining-01-comparison.md) completes forty owners/4,626 rows and all 36 evaluator task checks, with no own-U timing benefit. This brings comparison coverage to twelve of 48 development cells. The [second admission](reports/m5-remaining-02-admission.md) completes twelve owners/1,204 rows; its [comparison](reports/m5-remaining-02-comparison.md) completes forty owners/4,650 rows and all 36 task checks under independent raw/outcome audits, bringing coverage to sixteen of 48 cells. The [third comparison](reports/m5-remaining-03-comparison.md) adds forty owners/4,626 rows, sixteen strict U-only core boundaries and all 36 task passes, bringing coverage to twenty of 48 cells. Independent raw/outcome audits pass and all 424 references rehash. No own-U correction or goal-timing benefit is observed. The [fourth comparison](reports/m5-remaining-04-comparison.md) adds forty owners/4,626 rows and all 36 task passes under independent audits, bringing coverage to 24/48. It also shows no own-U correction/goal-timing benefit. The [fifth comparison](reports/m5-remaining-05-comparison.md) adds forty owners/4,617 rows and all 36 task passes, bringing coverage to 28/48. Independent raw/outcome audits pass, with no own-U task or timing benefit; the changed lower fact is corrected at358 for all nine conditions. The [sixth comparison](reports/m5-remaining-06-comparison.md), `0b30585`, adds forty owners/4,687 rows, forty snapshots and all 36 task passes; first-pass raw/outcome audits bring coverage to 32/48. Own/sham reaches the changed-case goal one tick later than no-U/swapped; no own-U benefit is observed. All 570 unique publication/raw/history references rehash. The [seventh attempt](reports/m5-remaining-07-comparison-failure.md) stops at an internal wall timeout after 38 normal owners and one 90-row partial owner; its last oracle remains unattempted. Retained-failure audits and all 595 publication references pass, but this incomplete batch does not increase coverage. The separate [remaining-08 admission](reports/m5-remaining-08-admission.md), `ba48305`, passes twelve owners / 1,204 rows / four calls under an independent retained audit; all 162 publication references rehash. Its comparison is still pending. Sixteen development cells still lack admitted comparisons, and frozen held-out evaluation remains missing. Frozen-observation [A](reports/m5-frozen-observation-wave-a.md)/[B](reports/m5-frozen-observation-wave-b.md) complete 36 instances and 4,156 policy calls with zero physics rows. A own/no-U actions are identical; B differs in three cue-flip contexts, without correction-timing benefit. This measures supplied-observation response sensitivity, not physical task success. The [remaining forty-cell plan](plans/m5-counterbalanced-development.md#approved-remaining-development-scope-3-october-2026) preserves the fixed lower route. |
| MEM-006 | Deterministic bounded `fit(E)` outside motor inference; [collector](../src/palimpsest/memory_history.py) verifies complete recorded sensor histories. | No LLM runtime dependency; history information and privileged baseline access must remain labelled. |
| ART-002 | Memory observations/decisions/inspection events carry tick and evidence IDs; route/UI annotations covered by `ui/tests/memory-events.check.ts` and actual M4 browser flows. | No useful-memory or route-improvement inference from an annotation alone. |
| ART-003 | [Sonification and comparison exports](artwork-mappings.md) and [connectivity atlas](artwork-atlas.md) and [curated anatomical comparison](artwork-specimens.md), individually requested offline mappings with embedded provenance; actual short recorded derivatives/browser checks. | Anatomical geometry/provenance and browser checks pass in the [specimen evidence](reports/m9-specimens.md). [Afterimage](artwork-afterimage.md) now passes actual eight-frame reference/render and browser checks with retained [evidence](reports/m9-afterimage-validation.md). The [six-mode offline handoff](reports/m9-offline-handoff.md) completes one six-export pass from nineteen pinned inputs. Independent raw/derivative audits and seven merged source checks pass; no new inference occurs. Declared-duration exhibition, independent operation and physical drawing remain incomplete; the [operator runbook](exhibition-runbook.md) states the required acceptance record. |
| HW-001 | [Reviewed-cost proposal](rover-procurement-proposal.md); no actuator path released. | Components/operator, electrical and lifted-wheel checks, fault injection, measured stopping/thermal deadlines and enclosed floor trials are required. |

Additional M6 task, M7 model and M9 artwork gates are broader than these IDs.
Exploration and homing have manual development demonstrations with native/replay
evidence; [measured wheel response](reports/m6-body-gains-v2.md) and [fixed-gain compensation](reports/m6-body-compensation.md) pass their standalone development gates. [Loaded runtime compensation](reports/m6-body-runtime-v2.md) passes its bounded actual source/reset/native/replay gate; its [actual UI gate](reports/m6-body-ui.md) passes snapshot/reset, keyboard controls and 26-tick action replay at `cbe1a3d`, with both earlier failed attempts retained. The [measured calibration session](plans/m6-body-adaptation.md) now implements four fixed probes and a new-fit episode with conditional native state and replay handling; fixtures/build and the 506-test combined regression pass. Its [v2 actual gate](reports/m6-body-adaptation-v2.md) passes 2,276 numeric intervals, native continuations, both replays and all six paired compensation improvements; the separate expected rejection is verified. Failed v1 remains retained. The [adaptive browser gate](reports/m6-body-adaptation-ui.md) passes four probes, fitted control/snapshot, Reset and 492-tick action replay with normal cleanup. The [fitted-body homing composition](plans/m6-body-homing-composition.md) is implemented and covered by the 711-test regression. Its first actual attempt fails before any owner or tick because verifier storage admissions omit the required path; the zero-owner failure and cleanup are independently audited. The separate two-call verifier correction is integrated and covered by the 717-test enabled regression; the corrected composition now passes four owners/853 rows, five snapshots, native continuation and both complete replays, with independently recomputed home error 0.119643 m below 0.25 m. The [new-profile browser gate](reports/m6-body-homing-composition-v2.md) passes 491 source plus 491 actions-replay rows, three snapshots, fresh calibration and Reset. Independent raw audit passes after a retained checker-only initial-event-prefix count correction; this is one fitted simulator body, not held-out or physical qualification. The [new-body plan](plans/m6-new-body-response.md) freezes a standalone two-owner calibration/homing study with left gear2.1 and unchanged fit/home criteria; standalone verifier `4c4bca2` is integrated after seventeen root focused checks pass without skips and all seventeen protected sources rehash. Twelve root mocked control checks and full preflight pass; its [first actual run](reports/m6-new-body-response-v1.md), `c048586`, stops before any tick or SNP because the verifier compares float64 native ranges with coordinates rounded through a float32 cache. Homing stays unstarted; cleanup and retained-failure auditing pass. The narrow caller correction `1e904c0` is integrated after eighteen root pure checks, preserving strict native equality and all seventeen protected sources. Fresh v2 controls pass twelve independent mocked checks and full preflight; the corrected one-shot study passes 480 calibration and 283 homing rows, five snapshots and 0.091607 m actual home error under the unchanged 0.25 m gate. Root outcomes and retained raw audits pass; both root checker-only failures remain retained. The [focused publication](reports/m6-new-body-response-v2.md), `0b1af16`, is integrated after 143 unique references rehash; the result covers one standalone simulated actuator-response case. Scoped exploration, homing and measured-adaptation subgates are met as mapped in the [implementation plan](implementation-plan.md); broader layout/body/population claims remain unmade and physical qualification remains separate. The [task-phase restoration gate](reports/m6-task-phases.md) passes all 12 owners/1,470 numeric ticks at `8a931cf`, including six four-tick native windows and four complete replays; all actual windows remain nonterminal. The [puck task core](plans/m6-puck-pushing.md) has native construction, teacher, continuation and replay evidence. The [fresh twenty-owner collection](reports/m6-puck-teacher-collection-v2.md) supplies 7,024 admitted rows; [all three frozen fits](reports/m6-puck-training-v2.md) complete thirty epochs. The [student mechanism](reports/m6-puck-student-mechanism.md) passes four owners, 364 intervals and 244 exact continuation/replay rows. The [twelve-owner development evaluation](reports/m6-puck-student-development.md) completes 7,200 ticks with all three models scoring 0/4 goals; independent raw audits pass and held-out stays locked; learned manipulation, product wiring and unseen/physical performance remain unqualified. The [residual diagnosis](reports/m6-puck-student-diagnosis.md) finds all three models predict abs(v)>0.05 on all 106 original recorded-dev turn-only examples; the [balanced-loss fits](reports/m6-puck-balanced-training-v1.md) complete all three fixed seeds. The [fixed residual comparison](reports/m6-puck-balanced-residual-v1.md) finds higher aggregate and approach-turn joint losses, with 104–105/106 turn rows still above the velocity threshold. The [balanced research binding](plans/m6-puck-balanced-student.md) passes 49 focused integrated checks and strict six-bundle admission; the [balanced native/replay mechanism](reports/m6-puck-balanced-student-mechanism.md) passes four owners/364 rows, five snapshots and 244 exact derivative rows under an independent audit. The [fixed balanced-development binding](plans/m6-puck-balanced-development.md) is implemented and passes 54 focused checks; the [twelve-owner evaluation](reports/m6-puck-balanced-development.md) now completes all 7,200 intervals, but every model scores 0/4 against the unchanged 3/4 goal gate. Root raw/NumPy action audit passes; held-out remains locked. Earlier construction, collection and launch failures remain retained in their reports.
The [current development paired readout](reports/m5-development-readout-24.md)
provides runnable analysis for 24 completed memory cells and 192 pairs, with explicit
missing-cell coverage, eight namespace blocks, censored timings and separate
historical/strict fork strata. It does not complete R2 or held-out evaluation.

The reduced MaleCNS pilot has separate training and recorded-input held-out
scores, with a guarded CPU wrapper, native/replay integration and [actual live browser workflow](reports/m7-live-lab.md); it does not establish closed-loop navigation,
biological sensing, topology benefit or population-wide sex differences. The [16-run closed-loop evaluation](reports/m7-closed-loop-v2.md) completed with only 0/8 original and 1/8 control goals; The [three-seed v2 development gate](reports/m7-training-v2-stage-c.md) completes all 24 runs, but original seed 11 reaches only 1/4 goals, failing the frozen per-seed admission threshold. That failed protocol remains locked. The separate [recovery development](reports/m7-recovery-development.md) completes 24 owners with original goals 2/4, 2/4, 3/4 and control goals 3/4, 1/4, 3/4. Its [four held-out teachers](reports/m7-recovery-heldout-teachers.md) complete 1,154 ticks and four goals with independently audited records and source disjointness; the [recorded-input held-out evaluation](reports/m7-recovery-heldout-recorded.md) then completes all six fixed candidates over 1,154 rows each (6,924 model-row evaluations). Root independently verifies identities, disjointness and cleanup; neural losses remain runner-reported. The [closed-loop held-out evaluation](reports/m7-recovery-heldout-closed-loop.md) then completes all 48 fixed runs and 21,461 ticks: originals reach 5/24 goals, controls 8/24. Both raw audits pass, including 48 native initial snapshots and all 885 file hashes. Evaluation is complete; useful-navigation/R3 qualification and topology benefit remain unestablished. The user confirmed on 3 October that R3 stays open for a new navigation study with a prospective capability threshold and fresh held-out reserve. The [source-only study plan](plans/m7-navigation-study.md) is now frozen with one advice-label aggregation round and prospective all-seed 3/4 development then 6/8 held-out criteria. Sixteen scene IDs were prospectively reserved. Collector/admission source `13a1afe` is integrated; ten root synthetic checks, ten preloaded-module checks and nine independent control fixtures pass. Its [one-shot collection](reports/m7-navigation-collection-v1.md) stops after twelve intervals of scene3100/learner10 because the guard intentionally rejects a base/floor contact. Eleven later owners remain unstarted. Root retained-failure audit passes in 3.787 s with unchanged inventories, all four sampled identities absent and a free writer lease. This is no admitted collection or capability result. The separately reviewed [v2 contact plan](plans/m7-navigation-contact-v2.md), `d2f7358`, fixes 125 declared robot-world pairs without changing support classifications, goal criteria or resource ceilings; the narrow validator/collector `736e0cf` is integrated after eighteen focused and eighteen preloaded-module root checks pass. V1 remains failed. The [v2 collection](reports/m7-navigation-collection-v2.md), `c56a9b4`, completes twelve owners, 5,080 intervals and twelve snapshots: one goal, six stalls and five time limits. Root raw audit passes first in 43.100 s, and all 304 unique publication/raw references rehash. This completes collection admission; training-data admission and useful navigation remain unqualified. The separate [data-admission plan](plans/m7-navigation-data-v2.md), `b3cbb67`, is integrated after exact source/metadata review; the named preparer `4ecb354` is integrated after eleven independent synthetic/source checks pass without skips. The one-shot data preparation on frozen `4ecb354` now completes with normal shutdown: 7,197 augmented train / 1,228 unchanged recorded-development rows. Independent control, source/cleanup and raw data audits pass, checking all 26 sources / 8,425 rows and byte-exact historical transfer. The [focused publication](reports/m7-navigation-data-v2.md), `2d4a7b8`, is integrated after all 652 retained references rehash. The paired original-graph trainer `6feade9` is integrated after eleven independent pure checks pass; all 95 admitted reader sources and six helper/lock pins remain unchanged. Its producer fixture-only failure is retained. Training controls and actual fitting/development/held-out outcomes remain pending; R3 stays open.
The [combined regression](reports/project-integration.md) passes 717 enabled tests without skips at `db59a56`, including actual EGL/male continuation/replay, puck CPU checks, balanced-development routing and the body verifier storage-path fix. Hosted CI at `f78f087` did not start because of the account billing/spending-limit block. Sources, assets and production model identities remain unchanged. M10 handoff remains partial while the task, model, artwork and physical gates remain open.

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

The [fixed CPU FLYNN own-branch executable replays](reports/m5-flynn-replay.md) pass both actions and policy modes (129 transitions and 835 events each) with unchanged initial state/source and normal cleanup. The original nine-condition own-U task/timing benefit remains absent. The separate [eight-cell admission gate](reports/m5-counterbalance-stage-b.md) passes all 24 owners/2,408 ticks with independently audited actual policy bindings, null/no-event controls and normal cleanup. It scores one-tick admission only; the full condition comparison and held-out R2 evaluation remain open.

The separate [manual held-out-start diagnostic](reports/m6-task-heldout-starts.md) passes four task criteria and four actions replays on two symmetric starts of one layout (1,980 total ticks). Both declared-origin homing errors are 0.162834 m. Native initials, raw rows/events and previous-sensor driver inputs were independently audited; new-body, learned-policy, task/body-composition and physical claims remain outside this result.

The [first four-cell comparison launch](reports/m5-counterbalance-stage-c-v1.md) failed before starting any owner because its validator joined a UUID object as a path. The narrow fix has a real validator regression check; no condition outcomes exist for this attempt. The [first puck mechanics gate](reports/m6-puck-mechanics-v1.md) passes stability and opposite pushes, then its teacher times out after 600 ticks. Independent audits preserve the failure and identify the target-selection defect; native continuation, replay and learned manipulation remain unqualified.

The [retained-fit turn gate](reports/m6-body-turn-transfer.md) passes six owners/720 intervals and all six strict paired improvements in wheel-rate RMSE, wrapped yaw and lane-Y deviation. Independent audit binds every metric to raw arrays and six exact initial integration states. This extends one existing fitted body to opposite-wheel turn commands; it does not establish a new body, general planar tracking, task/body composition or hardware qualification. Both [puck mechanics attempts](reports/m6-puck-mechanics-v2.md) remain failed and audited.

The [second four-cell comparison attempt](reports/m5-counterbalance-stage-c-v2.md) stopped on a process-monitor indexing error after fourteen terminal worker records and 1,561 intervals; only thirteen child supervisors finalized and twenty-six owners never started. Both independent retained-data audits passed, but no aggregate comparison report exists. First-cell correction times are equal across all nine conditions, with no own-U timing advantage; the interrupted run does not close R2.

The [third puck mechanics attempt](reports/m6-puck-mechanics-v3.md) preserves explicit controller mode through records and snapshots, but still reaches its 600-tick limit 0.443812 m from goal. Independent audits verify 960 intervals and six snapshots with normal cleanup. Turning moves the rover across approach/push boundaries; the retained trace motivates a separately reviewed signed-approach change, without widening the task limit. Learned manipulation and the six later native/replay checks remain unqualified.

The [puck learning contract](plans/m6-puck-learning.md) at `0fd589c` passes nineteen pure learning/record checks; sensor-only phase memory, ninth input and float64 output scaling are implemented. Demonstrations, learned control and runtime integration remain pending. The [recovery v3 collector](plans/m7-recovery-coverage.md) at `c382c86` passes eight source checks but has not executed; it measures the earliest complete-cycle-plus-clearance collection boundary and deliberately excludes later driving. Earlier failed rollouts retain their original outcomes.

The combined source at `c7b4436` passes **579 enabled tests without skips**, including simulation, production male Torch/native/replay and the new puck CPU model fixtures. [The fixed puck trainer/model mechanism](reports/m6-puck-model-mechanism.md) passes all four checks; actual demonstration training and learned manipulation remain pending. [Recovery v3](reports/m7-recovery-coverage-v3.md) passes its changed first-cycle collection estimand on both sources (134 rows), with later driving censored and no natural task outcome. This preserves prior failures and does not admit the sources to the existing production loader. [C4](reports/m5-counterbalance-stage-c4.md) passes forty owners/4,689 intervals with sixteen strict core forks and no own-U correction/goal advantage; combined C3/C4 covers eight selected cells, not the full matrix or held-out R2 evaluation.


The earlier full enabled regression at `1d97787` passes **646 tests without skips**; the
earlier two historical-reader fixture errors remain retained, with actual
admission pins unchanged. The
[fixed controller references](plans/m5-controller-references.md) add exact
physical restoration with frozen unused memory; their six-owner native gate
passes all navigation goals across 744 intervals (260 actual neural, 484
non-neural reference). Independent audits pass; no memory-task benefit follows.
The [twenty-layout puck collection](reports/m6-puck-teacher-collection-v1.md)
completes all goals and 7,070 intervals, but seed 6004 fails the unchanged
terminal-stop coverage requirement. Both independent raw audits confirm the
failure, and the entire batch remains excluded from training. The separate
[recovery adapter](plans/m7-recovery-learning.md) prepares 2,117 training and
1,228 development rows with no held-out sources; independent feature/action
reconstruction passes. The [six recovery research fits](reports/m7-recovery-training.md) complete all
twenty epochs each in 194.681 s outer. Independent artifact/graph/history audits
pass. [Fixed recovery development](reports/m7-recovery-development.md) passes all
24 owners and 8,552 intervals: original goals 2/4, 2/4, 3/4; rewired goals
3/4, 1/4, 3/4. Independent raw audits pass. Both total 7/12; topology benefit
and held-out qualification remain unestablished. The separately versioned .2 puck stop correction passes
its [ten-owner mechanics gate](reports/m6-puck-learning-v2-mechanics-v1.md),
including 1,569 intervals, thirteen snapshots and exact native/replay checks.
The [fresh twenty-owner collection](reports/m6-puck-teacher-collection-v2.md)
passes unchanged admission over 7,024 rows, including seventeen actual terminal
zero labels for seed 6004. The old v1 batch remains excluded. Active task v5
trainer binding passes twenty-four focused checks. [All three prescribed
fits](reports/m6-puck-training-v2.md) then complete thirty epochs each, with all
ninety histories and finite numeric artifacts audited. Student execution and
closed-loop task capability remain separate gates. [Reference replay v1](reports/m5-controller-reference-replays-v1.md)
failed before its first comparison; the isolated Path correction passes nineteen
focused checks. [Fresh v2 replay](reports/m5-controller-reference-replays-v2.md)
passes all six destinations and 742 comparisons: 371 saved-action, 129 actual
neural-policy and 242 non-neural-policy rows. Independent numeric/native-initial/
hash/cleanup audit passes with zero numeric difference; lifecycle event agreement
remains the bound runner result. This closes the fixed reference replay gate,
not the full matrix, frozen-stream diagnostic or held-out R2 qualification.

The [headless puck student](plans/m6-puck-student.md) is integrated at `3f6a2fd`.
All 103 focused pure checks pass in 7.198 seconds; before/after actual teacher-data
and strict trained-bundle admission are unchanged apart from elapsed time. These
checks cover its declared-input, own-cursor, record and replay contracts using
fixtures. The first runtime launch failed before any owner because the stage
runner did not create its report directory; its evidence remains retained. The
separate single-line v2 correction passes real-filesystem fixtures and root
control review. Its [native gate](reports/m6-puck-student-mechanism.md) passes four owners, 364 intervals and five
snapshots, including 244 exact continuation/replay rows. Both raw audits pass;
the root checker first needed an array-to-list conversion at the existing typed
transition boundary, with that failure preserved. Fixed development, UI and
learned manipulation remain unqualified.

The [frozen-observation diagnostic](plans/m5-frozen-observation-diagnostic.md)
is integrated with the bounded atomic terminal-report correction at `5d1b2b8`;
all 46 focused root checks pass in 10.616 s. The first real-file control fixtures
exposed create-only late report updates; the failure and narrow fix are retained. A
read-only source audit reconstructs 1,039 historical intervals without inference
or native execution. [Actual wave A](reports/m5-frozen-observation-wave-a.md) completes sixteen owners
and 2,084 responses with zero physically stepped rows. Root shared-validator
revalidation passes; own/no-U actions are identical and swapped U changes actions
in the three cue-flip contexts. This diagnostic establishes no navigation benefit;
[wave B](reports/m5-frozen-observation-wave-b.md) subsequently completes twenty instances and 2,072 policy calls with zero physics rows. Its own/no-U actions differ, with unchanged correction timing and no demonstrated task advantage. The full matrix and held-out R2 outcomes remain pending.

The [fixed recovery held-out source](plans/m7-recovery-heldout.md), `6a5cb7e`,
passes 74 root checks with one explicit Torch opt-in skipped (2.586 s). Its
retained-data admission passes in 8.036 s without inference, native execution or
held-out reads. This prepares separate teacher/recorded/closed-loop evaluation;
all four teachers complete goals over 1,154 ticks, independently audited. The [recorded-input](reports/m7-recovery-heldout-recorded.md) and [closed-loop](reports/m7-recovery-heldout-closed-loop.md) stages now also complete, with six fixed candidates and all 48 reserved native runs. These are completed evaluations, without a useful-navigation threshold or R3 qualification.

The [fixed puck development source](plans/m6-puck-student-development.md),
`77f4d49`, is integrated at `225941c`. All 109 selected root pure checks pass in
4.267 s with no skips, including pre-action initial-state matching, typed fresh
envelopes, each-model goal admission and late-return failure. All twelve native owners complete 600 ticks each, but every model scores 0/4
goals. Independent audits verify all rows, initial states and normal cleanup.
The failed goal admission keeps held-out locked; learned manipulation remains
unqualified.
