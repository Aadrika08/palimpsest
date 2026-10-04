# Memory v2: passage beliefs that affect route commitment

**Design only — not approved for runtime implementation or experiment execution.**
Research-phase deliverable, 4 October 2026, against base `ee6bf61`. The binding
phase scope is [research-capability-phase.md](research-capability-phase.md).
Memory v1 is retired for the allocation reasons in
[the retirement report](../reports/m5-v1-structural-null.md); R2 remains open.

## Question and claim boundary

Does history-fitted invalidation of previously observed passage beliefs improve
the cost of reaching a goal under one fixed, shared routing policy? Compare own
with no-U and swapped on paired continuations, including failed continuations.
This would be a symbolic-memory intervention with a fixed CPU FLYNN motor
controller. It would not demonstrate neural memory learning, biological sensor
mapping, general memory ability, or physical qualification.

V1 cannot answer this question: its operational route choice does not consume
passability estimates. Its inspection requests can nevertheless change motors,
so a universally forced outcome or forced held-out null is not established.

## Candidate geometry and public routes

Start with the pinned 7 m half-width arena, rover radius .3 m, twenty cylinders
of radius .4 m, and .05 m wall inset. A candidate separator has thirteen post
centers at x=0 and y=0, ±2, ±2.9, ±3.8, ±4.7, ±5.6, ±6.5. Gate cylinders park
at [2.5,-1] and [2.5,1], closing at [0,-1] or [0,1]. The other five cylinders
park away from routes, provisionally [4.2,-4.8], [4.2,4.8], [5.4,-4.8],
[5.4,4.8], and [6.4,0]. Goal is provisionally [2.5,0].

These are development candidates, not a claim of validated collision clearance
or feasible navigation. Before a pilot, independently verify exact placement
guards, both open crossing corridors, closure exclusion, and separation of the
free body-center space. Inflate obstacles by the rover radius and account for
wall/body clearance. The posts must prevent end bypasses; a public graph alone
does not prevent the motor controller from taking an unmodeled bypass. Retain
the independent geometric check and actual path traces. Reject or revise the
candidate if any bypass exists. Any layout revision creates a new profile hash.

The initial decision node is provisionally [-1.8,0]. Each public route uses its
inspection marker [-.8,±1], a crossing waypoint, a far-side exit [1.2,±1], and
the common goal. Public graph edges declare landmark IDs, direction, route
subject, fixed authored length, and allowed retreat edges. They do not expose
live pose, closure state, ground-truth passability, or a private bearing.
Refine waypoint positions on development to ensure visible, executable chains,
including return to the decision node after a rejected crossing. Counterbalance
small public route-length differences and ties; never derive a cost from secret
closure state. Freeze graph, lengths, tolerances, and profile before confirmation.

## Sensing and actual acquisition

Keep the existing symbolic visibility rules: at most 4 m distance, ±90° field
of view, and circular line-of-sight occlusion. Sample passability only when the
inspection landmark is visible and within .75 m. Bearing packets are the only
directional input to the controller. A required missing bearing is a declared
failure (`CueUnavailable`), never repaired using hidden pose or true-goal angle.

The future versioned packet additionally needs an explicit landmark-arrival
token to advance a multi-waypoint route. A candidate rule is a visible landmark
within .35 m; all nine conditions receive exactly the same projection. Its
private geometry remains inside the sensor producer, with independently checked
packet provenance. This is a declared sensor-contract change requiring approval
and validation, not an implicit distance channel. Passage observations remain
governed by the separate .75 m rule. Goal termination uses the existing declared
goal predicate, identically in every condition.

Start M with unknown estimates. The common prefix must obtain two real `open`
samples, with episode/tick evidence, while gates are open; then return to the
decision node. Do not seed beliefs as known facts. Capture a common continuation
snapshot only after both samples and before the event. Acquisition and return
with CPU FLYNN are separate feasibility obligations; manual placement or manual
steering can help geometry development but cannot qualify this prefix.

Require two consecutive visible cue packets to establish a cue change. The
decision event occurs while outside both passage-sampling radii. Independently
admit that no post-event passage sample occurred before commitment. Change,
null, and no-event trials all commit at the same public scheduled decision tick;
the planner receives the tick and observed cue packets, not the case kind.
Schedules must not move a gate through the body. A rejected intervention invalidates
the case rather than silently changing its intended mechanism.

## One finite-state supervisor

Replace competing travel and inspection overrides with one shared owner. Its
inputs are M's current estimate/status/evidence, declared current packets,
selector-generated requests, public route graph, and public elapsed ticks.
Only the selector/resources vary by condition. The supervisor never receives
evaluator gold, private geometry, or source-history access outside that selector.

States are `acquire`, `await_decision`, `commit`, `follow_route`, `inspect`,
`retreat`, `replan`, and terminal `goal`/`failure`. Transitions and route changes
are recorded with their exact inputs. Requests may flag a belief as uncertain
and create pending work; they cannot independently command a second steering
policy or skip the route decision.

At commitment or replanning, exclude known-blocked routes. Prefer observed-open
routes to uncertain routes; among equal classes, choose the lowest fixed public
path cost, then a deterministic lexical tie rule. Counterbalance lexical IDs
and the physically cheaper side. If both routes are uncertain, choose the
cheaper one for inspection. If both are blocked, terminate with `no_route`.
This minimal categorical policy needs no fitted uncertainty penalty.

Lock the selected route until its next inspection or a declared route failure;
do not switch opportunistically using private state. At its marker, assimilate
the real passage sample. Open means continue through the visible waypoint
chain; blocked means follow the declared retreat chain, then replan. An
uncertain belief without a valid sample cannot authorize crossing. Retain a
bounded inspection deadline and a bounded number of route attempts, frozen
after development. Unresolved samples, invisible selected waypoints, or exhausted
budgets terminate as failures. Every scored motor action is supplied by CPU
FLYNN through the same bearing bridge. No manual rescue enters scored traces.

This provides the intended opportunity: no-U can retain a stale open belief
and commit to a newly closed cheaper route; own can invalidate that belief and
prefer the still-observed-open alternative. A null cue can wrongly invalidate
an actually open cheaper route and incur a detour. These mechanisms must be
observed in a pilot, not inferred from this specification.

## Conditions, history, and snapshots

Retain all nine existing conditions and their declared resource boundaries:
own, swapped, sham, no-U, hand-authored, history-independent, traversal,
retrieval, and oracle.
Oracle receives only the declared gold target IDs for its selector. It does not
gain a private planner or steering oracle. All other conditions have no gold
access. Own and sham provide an invariance check; retrieval is a history-access
reference and need not be worse than own. Freeze selector target budget and
resource limits together with the future protocol.

Use disjoint historical training episodes, development scene families, and
prospective untouched test families. Learn U only from historical training;
design graph/costs and feasibility thresholds only on development. Preserve
existing historical evidence instead of relabeling v1 as a v2 training result.

Fork every condition from the same complete application snapshot: physics,
controller neural/retina state, all RNG states, current and initial M, detector,
selector resources, request queues, inspector state, world schedule, and new
supervisor state. Include phase, route/edge/waypoint IDs, commitment tick,
inspection and attempt deadlines, pending requests, and accumulated costs.
Version and validate this schema; a hidden route cursor outside the snapshot
would break the paired comparison. Require deterministic prefix/restore checks
before any qualification claim.

## Counterbalancing and analysis

Cross learned relation, physical side, lexical subject/landmark identities,
cheaper or tied preferred route, closure side, and admissible event schedule.
Within change cases, balance closure of the initially preferred route against
closure of the alternative. Include cue-change/no-closure nulls and no-event
controls. Pair conditions within a case family and keep families independent;
ticks, repeated seeds within a family, and nine condition branches are not
independent samples. List rejected generated families and reasons, rather than
silently dropping inconvenient outcomes.

Primary endpoint is case-paired capped time-to-goal from the common decision
boundary. Any failure gets the same full time cap; do not analyze successes
alone. Primary contrasts are own minus no-U and own minus swapped, with a
prospectively frozen multiplicity rule. Report null/control costs separately
and across the frozen case mixture. Supporting outcomes are success, first
commitment to an actually blocked route (evaluator-only label), travel length,
inspection time/count, replans, unavailable-cue failures, and path bypasses.
Report acquisition cost separately because it is common before the scored fork.

A prospective development pilot determines variance, meaningful benefit and
acceptable null cost, case-family count, cap, controller settings, and rejection
rules. Freeze them before assigning or accessing test IDs. No current evidence
justifies numeric effect thresholds or a confirmatory sample count.

## Separate pilot and stop rules

Runtime/spec approval and a separately bounded pilot are future work. Before
confirmation, the pilot must demonstrate all of the following:

- Geometric separation and valid open/closed labels, with no end bypass.
- Real initial evidence for both beliefs and complete reproducible snapshots.
- Commitment before passive post-event correction and outside both sample radii.
- Different decisions caused by M interventions under the identical supervisor.
- Measurable closed-route/retreat cost, and measurable false-targeting cost in nulls.
- Visibility of every required travel/retreat waypoint under the existing sensor
  limits, with arrival-token provenance independently checked.
- CPU FLYNN acquisition and reliable execution of both routes and retreat;
  symbolic tests and manual geometry trials are insufficient.
- Equal condition budgets, correct failure accounting, and disjoint access logs.

Stop before held-out if any item fails. Revise the development design explicitly
rather than calling an uninformative task null a memory result. A technically
valid confirmatory null can complete the declared study; it does not establish
benefit. This phase implements none of the runtime changes or pilots above.
