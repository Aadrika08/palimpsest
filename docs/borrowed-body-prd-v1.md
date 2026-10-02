# borrowed body
## product requirements document

**document version:** 1.0  
**date:** 2 october 2026  
**status:** implementation proposal, not a report of a working system  
**working name:** borrowed body; the interactive application is borrowed body lab  
**initial platform:** one Linux laptop, with local browser interface and Python simulation backend  
**later platform:** Raspberry Pi 5 + Arduino Uno, controlling one small differential-drive rover

> build a world where a connectome-constrained agent can act, where we can change what it experiences, and where every resulting trajectory can be inspected and compared. later, exchange compact histories without changing the body or neural controller.

---

## 0. how to read this document

This document combines product requirements, an implementation architecture, an experiment plan, and release gates. The name is provisional. The user has chosen simulation before hardware and has proposed a Raspberry Pi 5 + Arduino Uno car. Architecture choices, numerical budgets, effort estimates, and release boundaries below are proposed decisions, not already measured properties or previously approved commitments.

Three evidence classes must remain distinct:

- **source-backed:** capabilities or limitations actually described by upstream code, documentation, or the supplied paper; identified with source references such as [S1].
- **proposed:** behaviour we will implement and test. Requirements use “must” or “should” and do not imply existing functionality.
- **research hypothesis:** an outcome we will investigate. Failure to observe the desired effect is a valid result, not a reason to manufacture different behaviour.

The sources were reviewed for this PRD, but the FLYNN environment and checkpoints were not executed or independently reproduced. The supplied UPSCOPE manuscript was read as a user-provided draft, not treated as an independently verified benchmark result or an established biological theory.

## 1. product definition

### 1.1 one-sentence description

A local, interactive experimental environment for embodied neural controllers, with live intervention, state inspection, reproducible trials, trajectory art, and eventually interchangeable compact revision histories.

### 1.2 what the user can do

The user opens a local application, selects a scenario and controller, watches a rover move, changes the world, pauses at a meaningful event, inspects the agent's actual observations and outputs, and compares the result with another run.

A later release lets the user restore a common starting state, replace only a compact revision-memory artifact, and observe which expectations, actions, and trajectories change.

### 1.3 the central product loop

**choose a world → run an agent → intervene → inspect → replay or branch → compare → export.**

The central research loop is different:

**state a hypothesis → freeze a protocol → run matched conditions → measure the intervention → report the result, including null results.**

The application must support both without presenting an exploratory performance as a controlled experiment.

### 1.4 the first successful demonstration

A live FLYNN checkpoint navigates in its supported arena. The user queues an obstacle relocation at a control-step boundary, watches the response, pauses, and opens the synchronized sensor, action, and event records. The same saved trial can be played back, and a new run can branch before the intervention.

This is the first product milestone. A humanoid, simulated insect body, learned personality, general explorer, and physical car are not prerequisites.

## 2. the problem and intended users

### 2.1 problem

A navigation script can demonstrate a policy but is not necessarily a usable experimental instrument. It can be difficult to distinguish live inference from playback, observation from privileged simulator state, neural effects from an engineered controller, and persistent memory from transient recurrent state.

The proposed lab makes these boundaries visible. It also creates a useful interactive environment before the long-term memory hypothesis or physical deployment succeeds.

### 2.2 users

| user | primary job | successful outcome |
|---|---|---|
| builder, initially Utkarsh | run and modify embodied controllers without rebuilding a viewer and logging stack each time | a change produces an inspectable, repeatable trial |
| experimenter | compare anatomy, history, inputs, and bodies while controlling confounds | a matched experiment bundle with explicit changed variables |
| artist or exhibition operator | turn real behaviour into a legible encounter | viewers see actual routes and can discover what changed |
| future contributor | add a controller, scenario, or output mode | extension passes documented contracts and automated checks |

### 2.3 desired usability

After setup and asset acquisition, starting the lab should require one documented command. A first-time user should be able to start, pause, intervene, and compare two supplied trials without reading source code. These are acceptance targets, not measured usability findings.

## 3. source foundations and what we will reuse

### 3.1 FLYNN

FLYNN trains a recurrent network constrained by female FlyWire connectivity to navigate a simulated wheeled robot. It uses camera, target-bearing, and contact inputs, with imitation learning rather than spontaneous driving from untrained anatomy. This is a baseline to reproduce, not a newly invented component of our project. [S1]

The repository supplies an environment, analytical teacher, model wrappers, evaluation scripts, and pretrained-model references. Its browser export records agent runs; that browser presentation is not the live editable neural sandbox required here. [S2]

**reviewed upstream commit:** `8d964599119b420de67ee259434d273651a1a76d`.

| existing component | integration decision |
|---|---|
| `environment/mujoco_two_cam_env_random_obstacles.py` | retain the physics and sensor implementation behind a lab adapter |
| `agents/connectome_rnn_agent.py` | wrap the original sensory processing and inference path |
| `models/connectome_rnn_model.py` | preserve the baseline model; do not redesign it during reproduction |
| `agents/teacher_analytic_agent.py`, `core/vfhplus.py` | keep an explicitly privileged reference controller |
| `run_connectome_rnn_checkpoint.py` | use as the reference execution path for parity testing |
| `shared_config.py` | capture effective settings in a versioned profile instead of relying on editable global defaults |
| existing analysis scripts | inspect for reuse, but validate all reported metric definitions |
| browser demo assets | inspiration for presentation only; not the execution architecture |

Important code-level findings:

1. The environment already subclasses `gymnasium.Env`; we need instrumentation and isolation, not a new Gymnasium implementation from scratch. [S3]
2. Its raw observation dictionary contains privileged fields and goal-related information. The lab must explicitly project agent-visible inputs rather than hand every controller the entire dictionary. This is a boundary requirement, not an assertion that the published neural agent uses those privileged fields. [S3]
3. The evaluation loader warns that the checkpoint does not identify its source graph. Shape compatibility alone is insufficient to establish graph or neuron-order compatibility. Our asset manifest must close this gap. [S4]
4. Constructor defaults and the effective experiment configuration are not interchangeable. Profile values must come from the actual evaluation path and be checked against the loaded model and XML. [S3, S4, S6]

### 3.2 MaleCNS

MaleCNS is the later anatomical-data track, not a drop-in replacement for FLYNN's graph. Its documented access includes neuron annotations, connectivity, and morphology through neuPrint and downloadable files. Keep the dataset version, neuron identifiers, coordinate units, and extraction procedure. [S7]

The platform must distinguish female FlyWire reproduction, male-derived models, synthetic graphs, and graph-reduced variants. A checkpoint must never silently transfer between them.

### 3.3 UPSCOPE

The supplied paper separates **revision targeting** from rewriting: compact trigger–dependency rules identify which existing memories should be reconsidered. Its consolidator receives past revision episodes, not the future event or current factual bank. It reports a controlled compact-memory swap experiment. [S8, sections 4–6]

It does not provide a robot controller, biological fly memory, a general online-learning algorithm, or evidence of repeated longitudinal reuse. Subsequent rewriting is outside its evaluated scope. [S8, section 7]

Our robotics integration is therefore an extension, not a reproduction of the paper's complete system.

### 3.4 positioning against adjacent work

AntCar demonstrates insect-inspired visual homing on a physical Raspberry Pi robot. MEART is an artistic precedent for a neural system controlling a physical drawing mechanism. These precedents prevent us from positioning either “insect-inspired robot” or “neural system makes physical art” as the invention. [S9, S10]

The candidate distinction is an inspectable combination: a connectome-constrained controller, a controlled compact revision-memory intervention, an embodied feedback loop, and art that exposes that intervention. Do not claim this is the first such system without a separate literature review at publication time.

## 4. goals, non-goals, and release boundaries

### 4.1 goals

| goal | evidence of completion |
|---|---|
| make an agent act in an editable world | live controller, validated interventions, task outcomes |
| preserve an honest observation boundary | policy receives only declared fields; leakage tests pass |
| make experiments recoverable | artifacts include state, configuration, events, and provenance |
| turn behaviour into art without fabricating it | trace coordinates derive from measured simulated or physical motion |
| investigate memory-mediated change | controlled replacement of compact memory with downstream measurements |
| make hardware a later interchangeable embodiment | separate body adapter and independent actuator protections |

### 4.2 non-goals for the first release

No full nervous-system biological simulation, consciousness claims, open-ended natural-language robot agent, online weight learning, multi-robot colony, real-road autonomous driving, cloud dependence, ROS deployment, AxiomOS port, photorealistic world editor, or automatic commercial licensing determination.

A chat box is not part of the control loop. The simulator must remain useful without an LLM or external API.

### 4.3 releases

| release | scope | gate |
|---|---|---|
| **R0: reproduction** | pinned upstream, asset manifests, teacher and FLYNN execution, resource measurements | baseline execution and parity report |
| **R1: interactive lab** | live controls, interventions, sensor boundary, logging, snapshots, playback, branch comparisons, trace export | usable and instrumented simulator |
| **R2: memory laboratory** | expectation bank, revision targeting, bounded reviser, controlled swaps, history-derived rule experiments | targeting and behaviour experiments are runnable and auditable |
| **R3: anatomy expansion** | selected MaleCNS graph, input/output mapping, trained or calibrated model, matched controls | explicitly validated new model profile |
| **R4: physical rover** | pi5 inference, uno motor control, calibration, watchdog, enclosure, physical traces | physical safety and performance gates |
| **R5: exhibition extensions** | sonification, camera portraits, anatomy atlases, optional multi-body work | does not compromise core provenance |

R3 and R4 can be independently gated after R2. MaleCNS is not mandatory for the first hardware experiment if another clearly labelled controller meets deployment requirements.

## 5. user journeys

### 5.1 first run

The application checks runtime dependencies and shows locally available controller assets. Missing assets produce a specific acquisition instruction, expected licence, checksum requirement, and CPU/GPU requirement. The user selects the upstream reproduction profile and starts a trial.

The screen labels controller, input profile, clock mode, asset provenance, and whether inference is live. A teacher-only session is labelled teacher-only. A recorded demonstration is labelled playback.

### 5.2 intervene and inspect

The user drags an obstacle. The UI shows a proposed placement. The backend validates it and returns the exact accepted control tick. The original pose, new pose, actor, and event type are logged. The user pauses and inspects the observations and action around that boundary.

No event is acknowledged as applied merely because the browser displayed a preview.

### 5.3 branch and compare

The user saves a snapshot, runs condition A, restores the snapshot into a new branch, changes one declared variable, and runs condition B. The comparison shows shared provenance and differences before displaying route overlays.

### 5.4 swap compact histories, R2

The user selects a matched snapshot, previews the diff between compact artifacts, and requests a U-only swap. The backend checks schemas, swaps U atomically while paused, and asserts equality of the other state components. It creates a new branch and never overwrites the original trial.

### 5.5 export an artwork

The user exports actual route geometry with run identifiers and a mapping description. The export optionally includes small event annotations. An explanatory overlay can be hidden for exhibition, but the provenance remains available in an accompanying artifact.

## 6. scenarios and capabilities

### 6.1 R1 scenarios

| scenario | description | expected capability versus measurement |
|---|---|---|
| upstream reproduction | original robot and supported arena configuration | reproduction target; record failures as well as successes |
| sparse navigation | seeded obstacles and one reachable target | an experimental variation, not guaranteed pretrained competence |
| blocked route | relocate a pre-existing obstacle during travel | measure response, stalling, collision and recovery |
| target relocation | move the target and update the declared goal cue consistently | measure reaction to an intervention |
| vision ablation | mask either eye or both at an explicit observation boundary | preserve and display any remaining goal/contact inputs |
| texture variation | use the upstream-supported texture variants | out-of-distribution test, not evidence of arbitrary visual generality |

The paper-profile configuration includes 128 × 128 camera frames, 20 obstacles, a seven-metre arena half-extent, and a 600-control-step limit in the reviewed shared settings. Preserve these in the reproduction profile; do not silently substitute smaller arenas or images for performance. [S6]

The exact physics timestep, frame skip, action conversion, sensor preprocessing, termination rules, and duration must be measured from the loaded execution path and serialized. No UI frame count may substitute for simulation ticks.

### 6.2 R2 and later scenarios

| activity | mechanism that must be added | claim boundary |
|---|---|---|
| exploration | explicit coverage objective or exploration supervisor and evaluation | a navigation checkpoint is not automatically an explorer |
| home return | remembered observations or odometry-based estimate of home | hidden true home direction must not be supplied in an unaided-homing condition |
| landmark change | landmark detector or declared symbolic observation channel, expectation dependencies, reviser | event metadata from the editor is not a free sensor |
| passage closure | previously observed route expectations and new contradictory evidence | lack of observation is not proof a passage is open |
| body change | altered calibrated action response and an adaptation mechanism | transient recurrent state is not proof of learning |
| puck pushing | contact dynamics, task objective, demonstrations or learning | separate manipulation skill |
| U-only history swap | matched state, compatible artifact, fixed controller and bridge | test what changes; do not require a visually dramatic result |

### 6.3 scenario format

A scenario declares its ID and version, model asset, world seed, robot starting state, obstacle layout or generation rule, task, sensor profile, controller profile, interventions, success/failure predicates, time limit, and logging profile.

Scenario validation must reject invalid geometry, overlapping spawn bodies, goals inside walls, unsupported observation/controller combinations, and nondeterministic external callbacks in strict experiment mode. Deliberately unreachable tasks are permitted only when explicitly labelled and evaluated as such.

R1 allows moving existing objects. Adding arbitrary articulated bodies requires model recompilation and is outside R1's live editor.

## 7. functional requirements

Priority **P0** blocks R1. **P1** belongs to R2 unless noted. **P2** is later research or exhibition work.

| ID | priority | requirement | acceptance |
|---|---|---|---|
| LAB-001 | P0 | launch locally without mandatory remote services | a cached-asset session runs with network unavailable |
| LAB-002 | P0 | select scenario and controller from validated manifests | incompatible pairs fail before stepping |
| LAB-003 | P0 | run, pause, reset, stop, and advance one control tick | tick counters and state tests verify semantics |
| LAB-004 | P0 | distinguish task termination, time truncation, user stop, and runtime failure | each produces a different recorded reason |
| LAB-005 | P0 | queue validated interventions | every acknowledged intervention has exactly one applied tick or an explicit rejection |
| LAB-006 | P0 | show world, actual policy inputs, and inspection panels | panel samples share run/tick identifiers |
| LAB-007 | P0 | provide manual, analytical teacher, and FLYNN controller paths | no silent substitution between them |
| LAB-008 | P0 | isolate student observations from privileged state | automated leakage tests and adapter schema checks pass |
| LAB-009 | P0 | record actions, observations, events, configuration, and metrics | replay profile contains all required inputs |
| LAB-010 | P0 | support full application snapshots | restored branch includes physics, policy and wrapper state |
| LAB-011 | P0 | distinguish playback, action replay, and policy rerun | visible mode label and different validation checks |
| LAB-012 | P0 | compare two sequentially executed runs | provenance diff precedes interpretation |
| LAB-013 | P0 | export route geometry and a machine-readable run bundle | exported points match recorded world coordinates |
| LAB-014 | P0 | survive renderer or browser disconnect without corrupting a run | process tests verify configured pause/continue behaviour |
| LAB-015 | P0 | stop and preserve diagnostics on invalid policy outputs | NaN, infinity, wrong shapes, and timeouts tested |
| LAB-016 | P0 | provide headless batch evaluation and dependency diagnostics | documented commands work without the browser |
| MEM-001 | P1 | maintain separate factual bank, revision history, and compact U | independent hashes and schemas |
| MEM-002 | P1 | target memories without automatically rewriting them | selection alone cannot change their factual payload |
| MEM-003 | P1 | support abstention and evidence-based revision | uncertain evidence cannot silently create certainty |
| MEM-004 | P1 | exchange U only from a matched snapshot | automated invariant comparison passes |
| MEM-005 | P1 | run no-U, hand-authored-U, own-U, swapped-U and relevant baselines | condition and provenance appear in each bundle |
| MEM-006 | P1 | consolidate history outside the live motor loop | runtime does not wait for an LLM |
| ART-001 | P0 | draw the real trajectory without modifying agent input | toggling overlays leaves policy observations unchanged |
| ART-002 | P1 | show memory events aligned with route segments | each annotation points to logged evidence |
| ART-003 | P2 | add sound, camera portraits and anatomy-only output modes | mappings documented and individually disableable |
| HW-001 | P2 | route all physical commands through independent low-level limits | fault tests pass before floor operation |

## 8. execution semantics

### 8.1 clocks

Use an integer control tick and explicit simulation time. A control tick may contain multiple physics substeps. Record both the physics timestep and control interval.

Rendering and logging do not define simulated time. If full-model inference is slow, wall-clock progress slows while simulation timing stays fixed. Label the real-time factor. Do not silently drop controller updates or stretch simulated dt to make the display smoother.

Hardware later uses a real wall-clock deadline policy and must not inherit this wait-forever simulation behaviour.

### 8.2 deterministic boundary ordering

For a transition beginning at control tick k:

1. Validate and apply interventions addressed to the boundary before observation k, in a stable sequence order.
2. Update geometry-dependent caches and sensor state affected by accepted changes.
3. Capture raw sensor values and create the whitelisted policy observation.
4. Run permitted event detection and memory steps for that profile.
5. Execute one policy update and record both the raw output and converted action.
6. Apply the profile's action limits and advance the configured physics substeps.
7. Compute outcomes, persist records, and publish tick-labelled display samples.

The event engine must distinguish operator knowledge from agent-detectable evidence. An obstacle-moved editor event is visible to the evaluator but does not directly become an agent observation unless the scenario declares a symbolic event channel.

### 8.3 ownership and concurrency

One simulation worker owns all mutable environment and policy state for a run. UI and API processes submit bounded commands; they never mutate MuJoCo arrays or tensors directly. Rendering contexts remain owned by their designated worker/thread.

Workers should communicate through bounded queues. UI frames can be dropped under backpressure; authoritative experiment events cannot be silently dropped. In strict recording mode, pause simulation or abort the trial if the recorder cannot keep up.

### 8.4 intervention rules

Moving a rigid obstacle is an explicit world edit, not a physically simulated push. Validate clearance and reject placements that intersect the rover. Record the edit and invalidate any affected evaluator/planner caches. The analytical teacher may legitimately observe the edited full map; the student may not.

Sensor masks apply to actual policy input, not just the displayed camera. The display should indicate masked pixels rather than show an unmasked feed that the agent never received.

Switching controller or body creates a new branch. A memory swap requires the dedicated transaction described in section 14.

## 9. observation and action contracts

### 9.1 information boundaries

| channel | allowed information | recipients |
|---|---|---|
| raw simulator state | true pose, geometry, goal, contact solution and internal caches | environment, evaluator, declared privileged teacher |
| policy observation | whitelisted images, contact signals, explicit goal-bearing cue, permitted sensor estimates | selected controller |
| operator view | top-down world and selected internal state | UI only |
| memory evidence | outputs of declared detectors or symbolic sensors | revision subsystem |
| evaluation labels | correct dependency, true occupancy, shortest-path reference | evaluator only |

Use Gymnasium's reset/step and termination/truncation contracts, while keeping evaluator-only information outside the policy-facing adapter. [S16]

The adapter must rebuild an observation from an allowlist. Removing just one field named `privileged` is insufficient if other fields carry undeclared true coordinates or target-distance information.

A goal-bearing cue is allowed in the upstream reproduction profile, but the UI must state that it is supplied. “Blind” means vision masked, not absence of all information. A memory/homing profile cannot silently reuse true simulator pose to manufacture an apparently remembered bearing.

### 9.2 controller interface

Proposed interface responsibilities:

- initialize against an immutable model manifest;
- reset all episodic neural, sensory-filter and controller state;
- act on one declared observation with a fixed control interval;
- snapshot and restore the complete persistent execution state;
- expose optional scalar and selected-population telemetry;
- declare supported observations, actions, devices and numerical modes.

Action conversion is part of the profile. Preserve the upstream velocity/heading-to-wheel mapping for reproduction rather than treating every two-number output as an identical motor command.

Hardware actions later use explicit wheel-velocity units or another calibrated documented command. PWM is not synonymous with speed.

### 9.3 failures

Reject unsupported inputs, dimension mismatches, non-finite numbers, wrong graph mappings, and missing state. Never recover by silently changing the model, image size, precision or controller. Any intentional degraded mode creates a newly labelled profile and run.

## 10. model and anatomy management

### 10.1 manifest

Each model manifest records graph dataset/version, graph checksum, ordered neuron IDs checksum, input and output population mappings, threshold/filter rules, recurrent-model implementation, sensory preprocessing, action conversion, parameter checkpoint checksum, inference dtype/device requirements, licence information and citation.

A checkpoint with the same tensor sizes but a different node ordering must fail compatibility checks. When legacy assets lack embedded metadata, create a sidecar binding verified files and the construction procedure; explicitly state the strength and limits of that provenance.

### 10.2 baseline and training

R0 and R1 use fixed pretrained weights. Recurrent state evolves during an episode, but that is not described as weight learning.

Training is a separate command and process, with independent dataset lineage, seeds, budgets and output manifests. Adding memory supervision, a different goal interface, another sensor layout, or a new body may require training; compatibility cannot be assumed from matching shapes alone.

### 10.3 MaleCNS track

Select a documented circuit and publish the query/extraction procedure. Check sensory-to-output reachability, neuron annotation coverage, side conventions, boundary handling and omitted inputs. A small graph is a reduced model, not the complete fly.

Record whether synapse counts only determine topology or also initialize weights. Predicted neurotransmitter information must be labelled predicted, with missing/uncertain values handled explicitly. Do not treat synapse count as a measured effective physiological weight.

Do not load female-trained parameters onto male neuron IDs. Train or otherwise calibrate a new supported interface and report it as a separate model.

## 11. user interface

### 11.1 layout

Use a restrained lab-notebook style: one large arena, a compact control strip, two sensor thumbnails, an inspector, and a timeline. Avoid a permanent full-brain 3D visualization; it would compete with the task and introduce another performance burden.

| region | contents |
|---|---|
| header | scenario, controller, graph identity, run ID, live/playback label, strict/exploratory label |
| world | top-down rover, obstacles, goal, actual trajectory, selected intervention preview |
| sensors | actual eye inputs and declared goal/contact cues; preprocessing stage labelled |
| inspector | policy output, converted action, selected neural populations, latency, termination state |
| timeline | control ticks, interventions, contacts, memory events and snapshots |
| compare | shared/different configuration, overlaid paths, metrics and event differences |

A later memory panel shows facts, confidence states, active rules, selected revision targets and evidence. It must not invent a natural-language account of an opaque policy.

### 11.2 controls

Provide keyboard-accessible start/pause, step, reset, stop, snapshot, branch, and export. Manual driving operates only when the manual controller is selected and has explicit focus. Losing focus clears held keys. Keyboard shortcuts do not override emergency stop in hardware mode.

Display both wall elapsed time and simulated time. Display model-loading, paused, completed, failed, truncated, and degraded-performance states.

### 11.3 visual integrity

Use legends, labels and line patterns, not colour alone, to distinguish conditions. Plot selected neural populations using fixed or recorded scaling; auto-normalized displays must be identified. Do not normalize each branch independently and then infer amplitude differences.

A plotted causal chain represents recorded dependencies and state changes. Temporal correlation between activity and turning is not, by itself, a demonstrated causal role for a neuron.

## 12. proposed implementation architecture

### 12.1 stack

| layer | proposed choice | reason |
|---|---|---|
| physics and sensor rendering | existing MuJoCo Python environment | preserve upstream compatibility |
| environment API | existing Gymnasium plus lab adapters | stable reset/step task boundary |
| policies | PyTorch, upstream wrappers first | avoid model rewrites during reproduction |
| local service | FastAPI with a small HTTP command API and WebSocket telemetry | separate worker ownership from browser controls |
| interface | TypeScript + React + Vite, Canvas2D/SVG for top-down view | local interactive UI without a new physics engine |
| run index | SQLite | searchable local metadata, no hosted database |
| run storage | JSON manifests, append-only event records, typed chunked NumPy arrays | inspectable configuration plus efficient numeric data |
| tests | pytest plus browser interaction tests | cover contracts and complete workflows |
| packaging | pinned Python environment and frontend lockfile | reproducible setup, not latest-version drift |

These are implementation choices, not claims that all integration work is already supported upstream. Pin versions after the first successful reproduction rather than upgrading every dependency before testing.

### 12.2 processes

Use one local API/UI process and one active simulation worker initially. Run comparisons sequentially and display them together afterward. Do not require two full neural models to occupy GPU memory at once.

A headless evaluator uses the same worker and profile contracts without the UI. Training remains a separate executable path. R2 consolidation runs between trials and never acquires ownership of the live physics state.

### 12.3 API outline

| operation | semantics |
|---|---|
| list profiles/assets | return available and unavailable assets with compatibility/licence metadata |
| create run | validate a profile and return immutable run identity |
| start/pause/stop | update run lifecycle through the owner worker |
| step | advance exactly one control tick while paused |
| intervene | validate and schedule a command with an idempotency key and expected state version |
| snapshot | capture a complete state at a defined boundary |
| branch | create a new run from a compatible snapshot and declared intervention |
| replace U | R2-only transaction; separate from arbitrary settings mutation |
| compare | return manifest diff, paired metrics and aligned records |
| export | produce route/artifact files inside a configured output directory |

WebSocket samples carry protocol version, run ID, sample type, tick and simulation timestamp. Reconnecting obtains a fresh authoritative status rather than continuing from stale browser assumptions.

## 13. persistence, snapshots, and replay

### 13.1 run bundle

```text
runs/<run-id>/
  manifest.json
  profile.json
  provenance.json
  events.jsonl
  metrics.json
  observations/
  actions/
  physics/
  neural-selected/
  snapshots/
  memory/                 # R2 and later
  exports/
```

`manifest.json` contains parent run/snapshot IDs, software and asset hashes, seeds, hardware/runtime information, clock profile, observation/action contracts, recording level, experiment condition and completion/integrity status.

Never overwrite a completed bundle when rerunning a trial. Derived plots reference their parent run and renderer configuration.

### 13.2 complete application snapshot

A physics pose alone is not sufficient. Include:

- the full required MuJoCo integration state and every mutable model/world property used by the scenario;
- environment counters, previous observations, collision logic, visited sets and reward/termination state;
- neural hidden state, virtual-retina filters, sensor delays, normalization buffers and policy state;
- teacher planner/PID state when that controller is used;
- random-generator states for Python, NumPy, framework/device and environment;
- pending interventions, sensor queues and action-conversion state;
- R2 factual bank, compact memory, evidence/version state and supervisor state;
- a manifest linking immutable assets and numerical settings.

MuJoCo documents integration-state restoration and notes details such as warm-start state for bitwise repeatability. This does not automatically snapshot our Python wrappers or neural controller. [S11]

### 13.3 three kinds of replay

| mode | what is replayed | what it establishes |
|---|---|---|
| playback | recorded observations, poses and outputs | what was recorded, not fresh inference |
| action replay | saved initial environment plus recorded actions and interventions | physics/environment reconstruction within the declared numerical regime |
| policy rerun | full application state plus observations/world execution, recomputing actions | repeatability of the complete inference pipeline |

A fourth R2 diagnostic replays a frozen observation stream with only U changed. This isolates targeting/controller responses but is not a physically self-consistent new trajectory after actions diverge.

### 13.4 determinism contract

Guarantee exact identity only where verified on a pinned software/hardware profile. PyTorch explicitly warns that reproducibility is not universal across releases, platforms, and devices. [S12]

Each profile declares deterministic settings, unsupported operations, and tolerances. Register tolerances before comparing candidate conditions; do not relax them after observing a desired result. Report the first divergent tick and component. A recorded playback is always available even when policy rerun is numerically non-identical.

## 14. R2 memory design

### 14.1 separate state categories

| symbol | object | persistence and role |
|---|---|---|
| G | connectome graph | immutable within a trial |
| theta | learned parameters and engineered readout | fixed in evaluation trials |
| h | recurrent and sensory-filter execution state | changes each step; not a durable autobiography |
| M | factual expectation bank | beliefs, evidence, dependencies and confidence |
| E | revision episode history | records what change prompted which reconsideration and its outcome |
| U | compact revision-dependency artifact | rules selecting which entries of M should be revisited |
| B | body/environment adapter | calibrated embodiment and action mapping |

The experiment exchanges U, not G, theta, h, M or B at the initial intervention boundary. Subsequent states may diverge because the intervention changes future computation.

### 14.2 factual bank M

A record contains a stable local ID, typed subject/relation, current estimate, uncertainty/status, dependency references, supporting observation IDs, last verification tick, revision version and origin. Prefer domain-specific typed records over free-form prose in the first implementation.

Examples include an observed landmark-to-passage relation, a route segment's last observed passability, and a provisional body-response estimate. These are engineering representations, not claims about representations in fly neurons.

### 14.3 compact memory U

Start with up to four typed rules, following the paper's interface. Use a proposed initial cap of 4 KiB for the canonical robot-rule payload; track schema/provenance overhead separately. This is not the paper's 120-token budget and must not be described as reproducing that compression result. [S8, section 4]

A rule declares a trigger class and a bounded relational predicate over existing memories. The predicate may reference the triggering observation's entity but may not embed current-bank IDs or arbitrary executable code.

Example proposed rule:

```text
trigger: a familiar landmark's observed position changes
select: stored expectations whose validity depends on that landmark
result: candidates for reconsideration, not replacement values or motor commands
```

Rules can abstain, conflict, or match nothing. A deterministic priority/tie-break policy and bounded candidate budget are part of the profile. A proposed initial bank cap is 256 entries and a maximum of eight revision targets per detected event; the controlled diagnostic can use top-two selection separately.

### 14.4 revision pipeline

**observation → detected change → U selects candidates in M → evidence check → versioned belief revision → fixed behavioural bridge → neural controller → action.**

Selection must not directly replace a fact. The reviser may mark an expectation uncertain, request a fresh observation, lower confidence, or update a value using recorded evidence. Every transition includes old value, new value, evidence and reason code.

No new evidence means abstention or continued uncertainty, not an invented belief. Rate limits and hysteresis prevent repeated low-quality observations from producing uncontrolled oscillation.

### 14.5 the bridge to movement

The first bridge is an explicit supervisor that chooses an observation/reverification goal from revised expectations. It can supply the existing kind of relative-goal cue using only the profile's allowed observations or pose estimate. It does not secretly read exact simulator pose or bypass the neural controller with motor commands.

This is a hybrid architecture. Log supervisor proposals, cue values and neural outputs separately. Do not attribute the supervisor's planning to the connectome.

The pretrained FLYNN input/output path stays fixed in the first experiment. Adding new input dimensions, sensory gain modulation, a new readout or a different body requires a new validated controller profile and potentially retraining.

### 14.6 sources of U

Progress through four distinct conditions:

1. hand-authored rules for integration and debugging, labelled hand-authored;
2. deterministic history-to-rule baselines over a restricted rule vocabulary;
3. history-derived structured consolidation, optionally using an LLM between trials;
4. matched-history swaps with held-out events and banks.

An LLM consolidator is not required for R1 or the first R2 integration tests. Any provider is optional, explicitly configured, rate/budget-limited, and absent from the motor loop. Freeze its artifacts for evaluation.

Consolidation receives E only. Do not pass the future event, current M, test labels, active branch identity or future trajectory. Store history hash, method, prompt/template version, output, validation outcome and byte/token counts. Do not repeatedly regenerate until the target behaviour appears.

### 14.7 U-only transaction

While paused at a snapshot boundary:

- validate candidate U's schema, allowed predicates and budget;
- compute its diff and the hashes of all invariant components;
- install it in a new branch without resetting h or changing M;
- recheck invariant hashes and log the intervention;
- resume only after the new state is fully published.

A failure leaves the old branch unchanged. A mid-run exhibition swap is permitted but must identify the actual intermediate state; it is not equivalent to a clean matched-start comparison.

### 14.8 erasure and forgetting

“No U” removes revision guidance, not the factual bank or recurrent state. “Reset h” clears execution state, not history. “Clear M” is a separate intervention. The UI must never label all three as the same amnesia operation.

## 15. experiment protocol and scientific claims

### 15.1 hypotheses

**H1:** replacing U alone changes revision target selection on matched, held-out cases.

**H2:** in the integrated system, those changes can propagate through evidence-based revision and a fixed bridge to actions and trajectories.

**H3:** specific measured connectivity provides a benefit or distinctive response relative to appropriately matched alternatives under equal training and evaluation conditions.

H1 does not imply H2. H2 does not imply H3. None establishes biological fidelity, consciousness or recovered animal experience.

### 15.2 experiment ladder

| test | held fixed | manipulated | primary readout |
|---|---|---|---|
| integration fixture | M, observed event, selector implementation | hand-authored U | exact target IDs, not a learning claim |
| held-out targeting | current bank/event, selector | history-derived own/swapped/no U | target accuracy, abstention and swap direction |
| sensor-stream replay | initial state, recorded inputs, model/bridge | U | targets, revisions, cue/action differences |
| closed-loop simulation | initial world/full state, parameters, seeds | U | belief and trajectory outcomes after sensor divergence |
| graph sensitivity | fixed trained pipeline and intervention definition | lesion or rewiring | sensitivity of this trained system |
| architecture comparison | task, training budget, sensor access, evaluation seeds | graph architecture with separately trained models | learning and performance differences |
| physical replication | calibrated setup and reset procedure | memory condition | repeated, noisy real-world outcomes |

### 15.3 matched histories

For the strongest memory test, E_A and E_B should encode different revision dependencies while the current M and test observation remain identical. Use disjoint historical and test instances to prevent memorizing bank IDs. Store the generating protocol and evaluator labels separately from the agent.

If entire factual banks or controllers differ between two agents, call the result a multi-factor comparison, not a U-only intervention.

A geometry change does not necessarily have two equally correct revision policies. Define what counts as correct targeting from the scenario's dependency model, and distinguish that controlled diagnostic from open-world utility. A visually different route can be worse, neutral or useful.

### 15.4 baselines

Memory baselines: no revision guidance, hand-authored/oracle dependency, fixed-size generic summary where applicable, history retrieval, own U, matched swapped U, and a sham self-swap. Keep information access and runtime budgets explicit.

Controller baselines: analytical privileged teacher, a simple sensor-only controller, the original FLYNN checkpoint, and available matched non-connectome models. The privileged teacher is a performance reference, not an equal-information competitor.

Graph baselines: post-training interventions measure sensitivity. Claims that a topology improves learning require separately trained, budget-matched controls and multiple training seeds. A randomly rewired graph loaded with incompatible pretrained weights is not a fair architecture comparison.

### 15.5 analysis discipline

Separate development and held-out seeds. Start with a proposed 30-layout smoke suite for debugging. Freeze a larger paired evaluation suite before making performance claims; 300 shared layouts is an initial evaluation target, not a power calculation.

Use layout/history pairs, not video frames, as independent sampling units. Report distributions, paired differences, confidence intervals, failures and all chosen conditions. For training comparisons, include multiple training seeds. Register primary outcomes and distinguish exploratory secondary analyses. Do not choose the prettiest traces as the quantitative evidence.

## 16. metrics

| area | metric | interpretation |
|---|---|---|
| task performance | completion rate, time to goal, path length, normalized path efficiency where valid | separate static reference tasks from dynamic-world tasks |
| contact behaviour | collision events, contact duration, maximum penetration proxy, recovery time | define event debouncing; stalled contact is not avoidance |
| activity | stalled time, action saturation, reversals, control smoothness | diagnostics, not measures of intelligence |
| memory selection | precision/recall at k, exact set, abstention, own-versus-partner target margin | use only where gold/foil definitions exist |
| memory revision | false revision, correction delay, evidence latency, oscillation | whether changes are justified |
| swap effect | target/cue/action changes at matched ticks | establish the first downstream difference |
| closed-loop effect | route divergence, completion change, observation reacquisition cost | account for naturally diverging sensory inputs |
| compression | U bytes/tokens, E size, runtime input budget, consolidation cost | do not conflate compact representation with total runtime RAM |
| engineering | policy/render/logging p50/p95/p99 latency, peak RAM/VRAM, real-time factor, disk use | record hardware, dtype and logging level |
| replay | matched-state checks, first divergence, numerical error, missing records | exactness applies only to the stated regime |
| artwork | actual coverage, revisits, dwell distribution, event-linked marks | descriptive form, not a proxy for sentience |

For dynamic worlds, a single static shortest-path denominator may be invalid. Use an appropriate time-dependent reference or report time/path directly with scenario conditions. A change in route shape alone is not a success metric.

## 17. performance and resource requirements

The target development machine is the user's Linux laptop with an RTX 4050-class 6 GB GPU. Actual available system RAM, driver state, rendering backend and performance must be captured by the diagnostics command.

| requirement | proposed target or gate |
|---|---|
| UI responsiveness | 30 FPS display target; command-receipt acknowledgement p95 below 150 ms excluding model loading; application latency reported separately |
| manual/teacher execution | at least real-time in the supplied simple profile on the declared development machine |
| full FLYNN execution | benchmark batch-one inference first; slower-than-real-time is allowed when explicitly labelled |
| time integrity | no silent skipped policy ticks or changed dt to hit UI targets |
| resource isolation | one full policy at a time for default comparisons |
| memory pressure | no out-of-memory termination in the declared release profile; bounded buffers |
| endurance | proposed 60-minute mixed run/pause/intervention test without unbounded growth |
| disk limits | configurable quota, preflight estimate, explicit stop on insufficient storage |
| offline use | required dependencies/assets cached; no mandatory runtime network access |

Selected neural populations are logged by default. Full hidden-state recording is optional and budgeted. For illustration, 139,255 float32 values are about 0.53 MiB per state; recording at an assumed 50 updates/s would be roughly 26.6 MiB/s before other data. This is storage arithmetic, not a measured throughput or a mandatory logging rate.

Full input capture is required for frozen-sensor replay. A compact artwork recording can omit it, but must advertise the reduced replay capability. Camera frames used for exact input replay must preserve the original values; lossy display video is a separate derivative.

## 18. privacy, security, licensing, and research integrity

### 18.1 local application

Bind to loopback by default. Validate origins and use a local session token for mutation endpoints. Do not expose motor or run controls to the LAN automatically. Validate import paths, archive extraction targets, object sizes, schemas and output filenames. Imported JSON must never become executable code.

Only load trusted, verified model assets. Prefer tensor-only/safe loading where supported; legacy serialization that can execute code must not accept arbitrary untrusted checkpoints through a drag-and-drop interface.

### 18.2 privacy

Synthetic sensors are the default. External camera portraits and exhibition footage require explicit recording controls, visible indicators, retention settings and local storage. Do not collect identifying visitor data to make trajectories more interesting. API keys and credentials stay out of run exports.

### 18.3 asset licensing

The reviewed repository identifies its code as MIT. The model-hosting card separately identifies the real FlyWire graph and FLYNN checkpoint as CC BY-NC 4.0, while several synthetic/control assets are MIT. Maintain a per-asset manifest rather than treating a repository-wide label as permission for every file. [S2, S13]

MaleCNS's download page identifies its data as CC BY. Record the exact downloaded asset and applicable terms; adopting MaleCNS does not retroactively change the terms of female-derived assets. [S7]

Do not assume a paid exhibition, sponsored deployment or commercial product is covered. Obtain project-specific permission/review when needed. Do not redistribute the user-supplied anonymous draft in a public repository without permission; cite its ideas appropriately and replace the private citation with a public version only when verified.

### 18.4 claims policy

Use “connectome-constrained network” and “artificial revision memory.” Do not say “a living fly,” “what a fly sees,” “recovered memories,” “proved consciousness,” or “biologically accurate behaviour” unless independent evidence supports the precise claim.

A successful system need not show that biological wiring is superior. Negative and null results remain exportable and presentable.

## 19. R4 physical rover

### 19.1 division of responsibility

| component | responsibility |
|---|---|
| pi5 | perception, supported reduced/full policy inference after benchmarking, memory, telemetry and movement proposals |
| uno | bounded motor commands, encoder/sensor input, command expiry and low-level stop policy |
| motor driver | electrical interface sized to the actual motors and stall current |
| independent disable | wired means to remove or disable motor drive without pi cooperation |
| optional overhead camera | evaluation/trajectory ground truth only unless explicitly declared as an agent sensor |

Confirm the exact Uno variant, motors, chassis, camera layout, driver and power system before choosing pins or firmware timers. The referenced Uno documentation is for the R3. [S14]

### 19.2 communication and control

Use USB serial first. A bounded framed protocol carries protocol version, session identity, sequence number, command mode, wheel targets, a validity duration and error detection. Feedback carries acknowledged sequence, measured wheel state, obstacle/bumper state, faults and stop reason.

The uno defaults to disabled. Reconnection or reset must not replay an old command. Duplicate or stale commands must not renew the motion lease. Freshness uses the uno's local timing contract; do not compare unrelated pi and uno timestamps as if clocks were synchronized. Bound transport queues and explicitly test delayed/reordered traffic.

Do not prescribe the final command rate or expiry without measuring worst-case sensor, inference, transport and stopping behaviour. The hardware timing profile is separate from the simulated fixed-step profile.

### 19.3 safety gates

Hardware operation begins with wheels lifted, then a low-speed floor-level enclosed arena. No roads, stairs, table edges, people or animals inside the test area. Sensor limitations are mitigated by low mass, low speed, enclosure and independent disable, not a claim that a single distance sensor guarantees safety.

Test host process kill, frozen inference, unplugged USB, corrupted frames, stale packets, uno reset, sensor loss, blocked wheel, e-stop, power instability and thermal load. Each must have an explicit safe outcome and recorded recovery policy. Manual, autonomous and replayed commands all pass through the same limits.

A disabled driver may coast rather than brake. Measure the physical stopping envelope across relevant surfaces and battery conditions. Choose speed/clearance from that envelope; software command expiry is not the same as physical stopping time.

### 19.4 power and sensors

Use a motor-power path and a suitable regulated pi supply. Do not drive motors from GPIO. Verify ground/level requirements for the actual driver and avoid applying 5 V signals directly to pi inputs. USB is the initial communication path rather than improvised GPIO serial wiring.

Raspberry Pi recommends a high-quality 5 V/5 A supply and active cooling for best pi5 performance under load. Account for that recommendation when designing the battery/regulator and enclosure rather than assuming any USB source is sufficient. [S15]

The simulator's camera layout is not automatically reproduced by one arbitrary physical camera. Calibrate field of view, image sampling, contact signals, wheel response, delay and frame delivery. Document any mismatch and retrain or adapt as needed.

### 19.5 deployment gate

The pi must meet the measured inference and end-to-end deadline with recording enabled and under thermal load. If the full model fails, use a separately labelled reduced model or continue simulation work. Distillation produces a different controller and must not be advertised as preserving the measured connectome topology.

Physical runs require repeated trials, randomised condition order, calibrated starts and measured uncertainty. Exact identical-world claims do not transfer from simulation to a physical arena.

## 20. art and exhibition extensions

One evidence engine should power multiple presentations rather than six unrelated implementations.

| original idea | integration into this platform | scientific/artistic boundary |
|---|---|---|
| **afterimage** | external movement becomes a declared stimulus and selected responses drive a line renderer | an authored portrait through a model, not literally fly vision |
| **one map, many possible lives** | compare different model assumptions or histories using separately labelled conditions | distinguish parameter changes from U-only changes |
| **counterfactual choir** | selected neural/behavioural telemetry drives a fixed sound mapping | sounds are composed mappings, not recorded biological audio |
| **borrowed body** | simulated and physical rover trajectories, later pen marks | actual actions make the artifact |
| **atlas of what disappears** | a graph-analysis plugin renders connectivity interventions and lost reachability | structural loss does not automatically imply a lost memory or behavioural deficit |
| **the space between two flies** | curated anatomical correspondences rendered as paired structures | specimen differences are not automatically population-wide sex effects |

The R1 trace is evaluator-only. If pen marks later alter the rover's camera input, that is a new closed-loop scenario, not merely a display option. Record the substrate/mark state in snapshots or physical trial documentation.

An exhibition may use longer continuous sessions, but a week-long or 24-hour run is not assumed feasible until storage, resets, power, safety and operator supervision are validated.

## 21. testing and release acceptance

### 21.1 test layers

Unit tests cover observation projection, units, action conversion, manifest validation, scenario rules, event ordering, memory predicates and log serialization.

Integration tests cover a complete trial through the worker, UI reconnection, snapshots, restoring sensor filters, controller replacement, state branching, queue pressure and export.

Reproduction tests compare the instrumented controller with the pinned upstream execution on saved inputs and shared episodes. Performance and scientific-effect tests are separate: reproducing a tensor output is different from replicating a reported success rate.

Hardware tests remain disabled until the hardware release profile and operator setup are explicitly selected.

### 21.2 critical acceptance tests

| test | required result |
|---|---|
| privileged-state test | changing hidden evaluator metadata does not change policy input; permitted sensory changes still do |
| observation-mask test | disabling an eye changes exactly the intended agent channel |
| one-step test | paused step advances exactly one configured control interval |
| intervention test | duplicate request is idempotent; accepted edit appears at one recorded boundary |
| overlay isolation | turning artwork/inspector layers on or off cannot change observations or actions |
| snapshot test | restore checks all declared state components, not just position |
| replay test | exact or tolerance-based result follows the declared numerical profile |
| missing-asset test | informative failure, never a silently substituted model |
| graph-ID test | same-sized but differently ordered graph is rejected |
| recorder test | backpressure produces an explicit pause/abort, not missing authoritative events |
| invalid-output test | non-finite action stops the trial and preserves diagnostics |
| U-only test, R2 | invariant component hashes unchanged at the swap boundary |
| no-evidence test, R2 | target selection cannot fabricate revised facts |
| export test | plotted coordinates and event references round-trip to recorded data |
| disconnect test | worker follows the configured pause/headless policy without state corruption |

### 21.3 R1 definition of done

A clean documented setup can run the pinned teacher and FLYNN profiles, intervene live, display actual inputs, pause/step, preserve state, play back a run, branch a comparison, and export traces with provenance. The smoke evaluation and endurance test complete with known failures documented. Licence notices and asset checks are included.

R1 does not require real-time full-model inference, memory learning, a statistically positive topology result, or hardware. It does require that slow inference and any missing capabilities be labelled honestly.

## 22. implementation roadmap and effort

Effort ranges below are planning estimates for focused engineering work. They are not delivery commitments; model compatibility and hardware can dominate the schedule.

| milestone | deliverables | rough effort | dependency |
|---|---|---|---|
| M0: reproduction | pinned assets, runtime lock, controller/teacher trials, parity and resource report | 3–5 engineering days | none |
| M1: execution core | profile model, worker, observation projection, events, recorder and headless runner | 5–8 days | M0 |
| M2: interactive R1 | local UI, interventions, complete snapshots, replay/branch, compare and exports | 7–12 days | M1 |
| M3: R1 hardening | integration tests, endurance, documentation, quotas, licence/provenance checks | 3–5 days | M2 |
| M4: memory mechanics | typed bank, targeting, reviser, fixed bridge, hand-authored fixtures | 5–8 days | R1 |
| M5: memory experiments | history-derived U, paired held-out cases, swaps and analysis | 7–12 days plus research iteration | M4 |
| M6: MaleCNS | extraction, model definition, training/calibration and comparison | research-dependent; estimate after a pilot | R1 and a scoped circuit |
| M7: hardware | chassis/calibration, firmware, fault tests, pi deployment and physical trials | 10–20 days plus procurement/integration | measured model feasibility |

Do not tie the first release to successful full-model training or a positive research result. Ship the useful laboratory, then extend it.

### 22.1 first implementation tickets

| ticket | deliverable |
|---|---|
| BB-001 | pin upstream commit and create per-asset manifest/checksum tooling |
| BB-002 | make a diagnostics command for dependencies, GPU/rendering, RAM/VRAM and asset availability |
| BB-003 | run upstream teacher and checkpoint smoke tests; retain inputs and outputs |
| BB-004 | build the sensor-only observation projector and leakage tests |
| BB-005 | implement single-owner runner, lifecycle and fixed-tick event queue |
| BB-006 | implement immutable run bundles and bounded recorder |
| BB-007 | define and test complete snapshot/restore for the first controller profile |
| BB-008 | expose local commands and tick-labelled telemetry |
| BB-009 | implement world/sensor/inspector UI and safe intervention previews |
| BB-010 | add playback, branch comparisons and route exports |
| BB-011 | run release acceptance/endurance suite and document numerical limits |
| BB-012 | create R2 memory schemas without adding an LLM dependency |

## 23. proposed repository structure

```text
borrowed-body/
  README.md
  pyproject.toml
  uv.lock                         # or another explicitly selected Python lock
  THIRD_PARTY_NOTICES.md
  upstream/                       # pinned source or recorded vendor reference
  src/borrowed_body/
    profiles/
    assets/
    envs/
    sensors/
    controllers/
    runner/
    events/
    recording/
    snapshots/
    evaluation/
    memory/                       # added in R2
    hardware/                     # added in R4
    api/
  web/
  scenarios/
  model_manifests/
  protocols/
  tests/
    unit/
    integration/
    parity/
    acceptance/
  docs/
    prd.md
    architecture.md
    source-register.md
    reproduction-report.md
    experiment-protocols/
  scripts/
  runs/                           # ignored, except tiny approved fixtures
```

Keep large graphs and model weights out of ordinary Git history. Store hashes and acquisition instructions. Preserve upstream attribution and maintain a small, documented patch surface.

The directories are proposed boundaries, not a requirement to create empty abstractions before the first run works.

## 24. risks and mitigations

| risk | consequence | mitigation or stop rule |
|---|---|---|
| checkpoint/runtime incompatibility | no trustworthy baseline | isolate versions and reproduce first; do not substitute silently |
| full model exceeds laptop/board budget | unusable interaction or missed physical deadlines | asynchronous UI, sequential runs, measured slow mode; reduced model is a separate profile |
| hidden state leaks into student input | invalid navigation/memory claims | allowlist projection and automated boundary tests |
| snapshot misses retina/controller state | misleading memory effects | complete-state tests and first-divergence reporting |
| direct scripted actions masquerade as memory | attractive but empty demonstration | inspect targeting, evidence, bridge and neural output separately |
| no measurable U effect | central hypothesis unsupported | report it; retain lab utility; test selector and bridge independently |
| graph ablation destroys trained mappings | invalid topology conclusion | separate sensitivity from retrained architecture controls |
| learned U overfits IDs or current bank | false apparent personalization | history-only consolidation and held-out instances |
| licences block intended exhibition/use | cannot distribute selected assets | per-asset review/permission; do not erase provenance |
| source-paper interpretation expands unnoticed | overclaiming biology or learning | mode labels, source register and explicit claim boundaries |
| scope creep into a general robot platform | delayed useful product | keep one body, one active worker and R1 boundaries |
| physical recovery learned from collisions | unsafe floor behaviour | low-level stop overrides, retraining/adaptation and enclosure |
| visual success hides safety interventions | misattributed controller competence | log all supervisor and safety overrides |

## 25. unresolved decisions and defaults

| decision | default for implementation | when it must be revisited |
|---|---|---|
| public project name | borrowed body | before public release |
| starting graph | original FLYNN female graph for reproduction | after baseline works; MaleCNS is separate |
| frontend | local browser, top-down view | only if measured constraints justify a different UI |
| clock profile | pinned upstream for reproduction | new task/body profile, never silently |
| memory representation | typed symbolic facts and bounded rules | after integration fixtures demonstrate useful semantics |
| learned consolidation | optional later; no provider required | when history-derived U experiment begins |
| camera/encoder hardware | unspecified, no purchases assumed | before physical design and calibration |
| physical command/stop budgets | measured from selected hardware | before floor tests |
| topology advantage | unproven | after controlled evaluation, not before |
| paid deployment permission | not assumed | before any applicable distribution or exhibition |

## 26. final product criterion

The first release succeeds when the user can run a real supported policy in a world, intervene, inspect what the agent actually received, and reconstruct the resulting behaviour.

The later project succeeds as research only to the extent its controlled experiments support its claims. It succeeds as art when the real computation and its limits remain visible in the artifact.

**one world. one body. inspectable actions. interchangeable histories only when we can show exactly what was exchanged.**

---

## appendix A. source register

Source URLs are supplied as identifiers for implementation review. Asset checksums and licence texts should be captured by the repository's acquisition tooling. Source review does not mean the code was executed.

**[S1] FLYNN paper.** Wang and Chen, “FLYNN: Robust Neural Network for Robot Navigation using Fly Brain Topology,” arXiv:2607.00025v2. Used for task/training framing, not a claim that we reproduced performance.  
`https://arxiv.org/html/2607.00025v2`

**[S2] FLYNN repository README and structure.** Reviewed through the GitHub connector; repository head resolved to `8d964599119b420de67ee259434d273651a1a76d`. README blob SHA `00129865ee06d17df5af273f7303bfd6dbe4a639`.  
`https://github.com/ben-gitdev/fly-gym`

**[S3] upstream environment source.** Reviewed first 180 lines; environment class, constructor, action and observation spaces. Blob SHA `78c0e12763d000e83038b6ac6ce8150e12afa3c3`.  
`https://github.com/ben-gitdev/fly-gym/blob/8d964599119b420de67ee259434d273651a1a76d/environment/mujoco_two_cam_env_random_obstacles.py`

**[S4] upstream evaluation source.** Reviewed first 190 lines, including preprocessing descriptions and graph-provenance warning. Blob SHA `a0ec91f327077c22e2e5e2ee5ae11547e40b57fa`.  
`https://github.com/ben-gitdev/fly-gym/blob/8d964599119b420de67ee259434d273651a1a76d/run_connectome_rnn_checkpoint.py`

**[S5] Google Research MaleCNS overview.** Context for the original anatomical-art project.  
`https://research.google/blog/a-connectomics-milestone-mapping-the-complete-male-fruit-fly-brain/`

**[S6] upstream effective shared configuration.** Reviewed `shared_config.py`; blob SHA `6c07f02cfd394253e003deacaf075559bde3a30e`.  
`https://github.com/ben-gitdev/fly-gym/blob/8d964599119b420de67ee259434d273651a1a76d/shared_config.py`

**[S7] MaleCNS download/access documentation.** Dataset `male-cns:v1.0`, annotations, adjacency, morphology and licence statement.  
`https://male-cns.janelia.org/download/`

**[S8] user-supplied anonymous manuscript.** “Small Memories Steer Big Ones: Compact Revision Dependencies for Personalized Memory Targeting.” File supplied in the conversation: `85_Small_Memories_Steer_Big_On(2).pdf`, 13 pages. Relevant sections: method on pp. 4–5, swap results on p. 6, scope/limitations on p. 8. No public URL or publication decision independently verified. Do not bundle the draft into a public release without permission.

**[S9] AntCar visual homing paper.** Gattaux et al., “Visual Homing in Outdoor Robots Using Mushroom Body Circuits and Learning Walks,” arXiv:2507.09725v1.  
`https://arxiv.org/html/2507.09725v1`

**[S10] MEART.** “MEART: the semi-living artist,” Frontiers in Neurorobotics, 2007.  
`https://www.frontiersin.org/journals/neurorobotics/articles/10.3389/neuro.12.005.2007/full`

**[S11] MuJoCo simulation and reproducibility documentation.** Integration state and deterministic-simulation conditions.  
`https://mujoco.readthedocs.io/en/stable/programming/simulation.html`  
`https://mujoco.readthedocs.io/en/stable/computation/index.html`

**[S12] PyTorch reproducibility documentation.** Device/release limitations and deterministic settings.  
`https://docs.pytorch.org/docs/stable/notes/randomness.html`

**[S13] FLYNN model-hosting card.** Per-asset MIT and CC BY-NC 4.0 labels.  
`https://huggingface.co/datasets/benquan1/fly-gym-trained-policies`

**[S14] Arduino Uno R3 documentation.** Board reference, not a confirmed bill of materials.  
`https://docs.arduino.cc/hardware/uno-rev3`

**[S15] Raspberry Pi 5 official product documentation.** Power and cooling guidance.  
`https://www.raspberrypi.com/products/raspberry-pi-5/`

**[S16] Gymnasium environment API.** Reset/step, termination/truncation and seeding contracts.  
`https://gymnasium.farama.org/api/env/`

## appendix B. acceptance traceability

| release gate | principal requirements | artifact proving completion |
|---|---|---|
| R0 reproduction | model compatibility, LAB-002/007 | pinned reproduction and resource report |
| R1 execution | LAB-001 through LAB-008 | automated lifecycle, observation and intervention results |
| R1 recovery | LAB-009 through LAB-012 | complete snapshot fixtures and replay comparison |
| R1 presentation | LAB-006/013, ART-001 | live demonstration and validated exported route |
| R1 hardening | LAB-014 through LAB-016 | endurance, failure injection and offline setup report |
| R2 memory | MEM-001 through MEM-006, ART-002 | matched experiment bundles and targeting/revision audit |
| R3 anatomy | graph/profile requirements in section 10 | extraction manifest and new model evaluation |
| R4 hardware | HW-001 and section 19 | calibration, timing and fault-injection report |

## appendix C. proposed command surface

These commands describe the intended product interface. They are not existing executable commands.

```text
borrowed-body doctor
borrowed-body assets verify
borrowed-body lab
borrowed-body evaluate --suite <suite-id> --profile <profile-id>
borrowed-body replay <run-id> --mode playback|actions|policy
borrowed-body compare <run-a> <run-b>
borrowed-body export <run-id> --format svg|png|bundle
```

Configuration should be explicit and reviewable. No command should silently download restricted assets, change a licence acceptance, upload run data, or enable physical actuation.
