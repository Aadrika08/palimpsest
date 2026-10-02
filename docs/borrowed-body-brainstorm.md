# Borrowed Body: brainstorm and selected direction

Date: 2 October 2026

Source: [Borrowed Body PRD v1](borrowed-body-prd-v1.md), preserved unchanged.
Source SHA-256: `4ce71144b2ce3b72b5f7318e0d357ee0f13efb20302befe9482650318d2352db`.

This companion records the lab, research, and artistic reviews and the user's selected research direction. It does not rewrite the PRD or report a working application. Upstream code was inspected during planning; no FLYNN checkpoint, performance experiment, or independent UPSCOPE reproduction was executed. UPSCOPE remains described through the supplied PRD, not independently verified here.

## Selected decisions

| Decision | Selected direction | Consequence |
|---|---|---|
| What compact memory U contributes | Transfer revision rules learned from past episodes to unfamiliar instances | Evaluate information learned from history, not merely a different route after swapping a rule |
| First research sensor | Declared symbolic sensor | Expose visible cue identity/change and relative bearing; isolate rule transfer before adding visual detection and localization |

The implementation sequence, example scenario, and presentation below are proposed defaults. The complete R1 requirements in the PRD remain the release gate.

## Lab: one trustworthy trial, then one complete comparison

### R0: establish the baseline

Start with one pinned upstream body, arena, and full-vision profile. Run one bounded teacher trial and one bounded FLYNN trial before expanding to the PRD's proposed 30-layout development smoke suite.

Capture checkpoint and graph identities, ordered neuron IDs, required mappings, effective configuration, runtime versions, inputs, outputs, termination reason, inference latency, and peak resource use. Compare the instrumented inference path with the reference path on identical inputs. Preserve image resolution, control interval, preprocessing, and action conversion; slower-than-real-time execution is acceptable when labelled.

The upstream loader warns that checkpoints do not identify their source graph. A sidecar must record the evidence binding checkpoint, graph, ordering, and construction procedure, including remaining historical uncertainty. Successful loading or matching tensor sizes alone does not establish provenance or reproduce the paper's reported success rate. See the [pinned evaluation source](https://github.com/ben-gitdev/fly-gym/blob/8d964599119b420de67ee259434d273651a1a76d/run_connectome_rnn_checkpoint.py).

R0 acceptance requires bounded execution, an asset/provenance report, reference-versus-instrumented output comparison, and measured resource use. Missing or incompatible assets fail explicitly.

### First R1 demonstration: one interruption, two traces

1. Run one supported FLYNN profile under one simulation owner. Display the actual policy inputs, supplied goal/contact cues, control tick, and actions beside the top-down arena.
2. Pause and capture a complete application snapshot before an intervention.
3. In condition A, relocate one existing obstacle at a validated, recorded tick; retain observations, actions, events, and trajectory.
4. Restore the snapshot into condition B without the relocation. Run comparisons sequentially to avoid holding two full policies in memory.
5. Show shared provenance and the changed variable before overlaying routes. Provide recorded playback and export an SVG trace with its run bundle.

The snapshot must include the PRD's full state inventory: physics/world mutations, wrapper counters and caches, neural hidden state, retina filters, random-generator states, pending commands, and action-conversion state. A pose-only save cannot support the branch claim.

The [pinned agent implementation](https://github.com/ben-gitdev/fly-gym/blob/8d964599119b420de67ee259434d273651a1a76d/agents/connectome_rnn_agent.py#L394-L509) sanitizes nonfinite raw outputs before returning actions. LAB-015 therefore needs a check before sanitization, with raw diagnostics preserved. Keep normal finite-output parity with upstream and document the intentional difference in failure handling.

Acceptance checks for this demonstration:

- Paused stepping advances exactly one control interval; duplicate interventions apply once at the recorded boundary.
- Privileged evaluator data and display overlays cannot leak into policy observations or alter actions.
- Restoring a snapshot reproduces the declared continuation within numerical tolerances fixed before comparison; report the first divergent component and tick.
- Nonfinite raw outputs stop the trial and preserve diagnostics.
- Playback and exported coordinates match the authoritative recorded data.

This demonstration is an intermediate milestone. Additional scenarios, manual/teacher UI selection, all replay modes, disconnect and recorder-failure handling, offline setup, quotas, accessibility, and the endurance test still need completion before declaring R1 finished. Memory, MaleCNS, training, and hardware remain later work.

## Research: transfer learned revision rules

### Give U an identifiable informational role

PRD section 14.2 includes dependency references in M. If those references already encode every correct dependency, ordinary traversal may solve targeting without history. That traversal is an essential baseline.

For the selected transfer experiment, M contains observations and incomplete candidate associations. Complete dependency truth and the current regime belong to the evaluator. History E contains past revision episodes that can teach which relation predicts invalidation. Consolidation receives E only, not the future event, test bank, evaluator labels, or active branch identity.

Historical and test entities use disjoint identifiers. Distinct histories can justify different target selections only when they carry information absent from the current bank/event. Specify that latent regime in the protocol; do not define correct targets using U's own output. Swapped rules may be wrong in the fixed test world even when they were appropriate in another regime.

### Smallest experiment, then movement

First use a small frozen bank, one observed event, and two candidate relation classes. Fit history-derived rules within a restricted typed vocabulary using a deterministic method; an LLM is unnecessary. Hand-authored rules are integration fixtures, not evidence of learning.

Compare learned U with:

- No revision guidance and a history-independent selector under the same target budget.
- Generic traversal over the associations available to the agent.
- Matched swapped U and a sham self-swap, with all other starting state held fixed.
- Oracle guidance using evaluator truth, explicitly labelled as an upper bound with privileged information.

For equal-information comparisons, record whether and how each baseline receives history; do not interpret an information advantage as an algorithmic advantage. Freeze development/test splits, target budgets, and primary metrics before held-out evaluation. Include abstention and events with no justified revision.

Then use two passages with previously observed passability and visible identifying landmarks. A visibility-limited symbolic sensor reports a warning cue change and landmark-relative bearing; it does not expose hidden passage occupancy, exact robot pose, the editor event stream, or evaluator labels. Historical regimes associate the changed cue with different relation classes of passage expectations.

At a matched snapshot, exchange U alone while holding M, recurrent/filter state, controller parameters, body, world, and random state fixed. Targeting selects an expectation for reconsideration. A fixed evidence-check/reinspection procedure can mark it uncertain and request a fresh observation; selection alone cannot rewrite its factual payload. Only new observed evidence justifies a passability update.

The fixed supervisor chooses a permitted reinspection goal and supplies its relative-bearing cue through the validated controller interface. FLYNN still produces motor actions. Log target selection, evidence decisions, belief changes, supervisor cues, and neural outputs separately. This is a hybrid system with engineered symbolic sensing, not a claim that fly circuitry learned these symbolic rules.

### Outcomes and null results

| Observation | Supported interpretation |
|---|---|
| Learned U improves held-out targeting over relevant matched controls | Evidence for rule transfer under this protocol |
| U matches simple traversal | No demonstrated added targeting value over traversal |
| Targets differ but justified revisions do not | Selection changed without demonstrated belief change |
| Beliefs/cues differ but actions do not | No demonstrated behavioural propagation |
| Routes differ without improved reinspection or task outcomes | Causal influence, not demonstrated usefulness |

Measure exact targets, false selections, abstention, false revisions, reinspection cost, and the first downstream difference. Positive results do not establish connectome necessity, topology superiority, biological memory, or consciousness. Those require separate evidence.

## Art: let the computation remain visible

Recommend **one interruption, two traces** as the opening encounter. It uses the lab's comparison workflow rather than requiring another artwork engine.

A proposed two-to-three-minute tour opens an explicitly labelled recorded pair, shows its shared starting state, pauses at the obstacle intervention, reveals the two actual trajectories, and lets the viewer inspect one synchronized sensor/action event before export. A live branch is a separate, clearly labelled run. Never silently replace slow live inference with playback.

Show wall time and simulated time separately. Preserve stalls, failures, overlapping traces, and null results. Distinguish branches with labels and line patterns as well as colour. In R2, show whether targeting, beliefs, actions, and routes changed separately; do not exaggerate route separation to make a swap appear effective.

Two later presentations can reuse the same records:

- **Borrowed eyes:** foreground the actual policy-input images and reveal the overhead evaluator view on demand. These are model inputs, not literal fly experience.
- **A ledger of waiting:** render recorded travel, stationary actions, and event boundaries with a separate wall-time strip so computational waiting is distinguishable from stopped movement.

Keep the initial arena, sensor thumbnails, controls, timeline, and comparison details compact. Exports retain run references and the rendering mapping. Defer a separate gallery application, sonification, portraits, and anatomy displays.

## Follow-up decisions and repository workflow

PRD section 4.3 places R3/R4 after R2, while section 22 lists MaleCNS as depending on R1 and hardware on measured feasibility. Resolve this release-dependency inconsistency before scheduling those tracks. A proposed resolution is to allow independently gated feasibility work after R1 while keeping memory claims dependent on R2; this note does not amend the preserved PRD.

The documentation bootstrap uses `main` because the remote was empty. Keep the preserved PRD and this companion in separate commits. Subsequent implementation milestones use focused branches and incremental commits, with no automatic merge or force-push.

Set commit identity only in this repository to `Aadrika Maurya <aadrikamaurya@gmail.com>`. Push to `https://github.com/Aadrika08/palimpsest` using the existing `Aadrika08` credential scoped to each operation. Leave global Git identity and the globally active GitHub account unchanged; never store tokens in repository configuration or files.

The next implementation milestone is R0. This documentation task adds no application API, runtime dependency, model asset, executable experiment, or physical actuation capability.
