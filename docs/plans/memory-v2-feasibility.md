# Memory-v2 feasibility implementation and execution contract

Approved in conversation on 4 October 2026. Base `0b5365346ed7eea4ada0d9fb6723db15840aa666`.
This authorizes implementation of the previously design-only
[memory-v2 specification](m5-v2-decision-scene.md) and a staged development pilot.
It does not authorize R2 confirmation, new fitting, reserved data, hardware or merge.

## Binding scope

Implement the shared memory-v2 supervisor, visibility-limited arrival tokens,
complete continuation state, headless-only development admission and a bounded
pilot. Begin with the specification's exact candidate cylinder geometry. Complete
authored public acquisition/crossing/retreat landmark chains before native runs;
freeze the single candidate. Invalid geometry or failed native prerequisite ends
that attempt without an automatic revised layout or replacement run.

All conditions retain cameras/contact, 4 m/90-degree visibility, .75 m passage
sampling and .35 m visible arrival. Missing selected bearings are CueUnavailable.
M starts unknown. CPU FLYNN obtains both open observations and returns to the
decision boundary. Scored actions remain CPU FLYNN actions through one bearing
bridge; no manual rescue, ground-truth bearing, route pose or private planner input.
Selector resources may vary; the shared categorical route policy cannot.

Exclude blocked routes, prefer observed-open over uncertain, then fixed public
route cost and lexical ID. Inspect the selected route before crossing; retreat
and replan on blocked evidence. Deferred requests for unchosen routes cannot
suppress goal completion. Bound attempts to two and each inspection to 150 ticks.
Each waypoint gets a 300-tick deadline; acquisition gets 1200 ticks, and scored
continuation gets 900 ticks. The profile admits at most 2100 total ticks at .02 s.
Do not change the legacy profiles' tick budgets or readers.

Packet version 2 adds visible landmark arrivals without coordinates/distances.
Memory-task state version 3 and application snapshot version 8 hold all supervisor
state; the snapshot container stays version 1. Restore must validate before
allocation and preserve native/model/RNG/M/E/state except declared recorder and
selector/U substitutions. The legacy lab API does not admit the headless profile.

Use frozen recorded local/paired historical rule artifacts with original v1
provenance; do not relabel those histories as v2 acquisition or fit U on pilot data.
All nine selectors receive fixture checks. Four native conditions are own,
swapped, no-U and sham, forked from identical pre-event snapshots.

## Work and evidence

1. Pure geometry/free-space/bypass checks; shared supervisor and sensor tests;
   versioned Engine/snapshot/headless admission and legacy compatibility.
2. CPU route, blocked-retreat, real acquisition and deterministic restore
   prerequisites. No paired pilot if a mandatory prerequisite fails.
3. Six paired development cases: local/paired relation crossed with preferred
   closure on north/south (four change cases), one cue-change/no-closure null,
   and one no-event case. These are correlated development variants, not six
   established independent samples. The four conditions share each base snapshot.
4. Offline puck residual/boundary/support and heading-magnitude audits, including
   existing full-feature versus geometry/mode-matched nearest neighbors. Navigation
   declared-sensor recovery replay and retained response loss decomposition. No
   new optimization, collection, gate revision or automatic follow-on intervention.
5. Bounded TestClient ordering investigation and appropriate regression; preserve
   unresolved environment/baseline limits. Publish actual attempts, failures,
   incomplete jobs, hashes, raw traces and scoped conclusions.

## Fixed execution budgets

| Stage | Seconds |
|---|---:|
| Combined offline control diagnostics |600|
| Native memory prerequisites |1800|
| Paired pilot |4200|
| Readout |600|

Total execution <=7200 seconds, startup/admission/analysis included. Implementation
and software tests are excluded. Sequential native owners, pinned CPU one thread,
no automatic retry or time transfer. A stage admits another owner only if its
remaining allocation can accommodate the owner's outer bound and cleanup.

Global new run outputs <=8 GiB; require10 GiB free before execution and maintain
2 GiB free. Existing StorageBudget/bounded_process enforce actual bytes/deadlines.
Each acquisition/prerequisite recording <=512 MiB; scored continuation <=384 MiB;
snapshot <=16 MiB; each stdout/stderr <=1 MiB. Reserve64 MiB for concurrent control
files/logs. Native prerequisite owners:150 s internal/160 s external; paired owners:
120 s internal/130 s external. Preserve incomplete artifacts on resource refusal.
No deletion of historical evidence, camera duplication in published Git evidence,
or extra generic execution/audit framework.

## Acceptance and stopping

Geometry must show valid open/closed crossings and no end bypass. Native
prerequisites must show both crossings/retreats, real observations, and restore
identity plus a five-tick repeat. A failed mandatory prerequisite stops native
progress; an invalid candidate is reported, not silently replaced.

Pilot audits independently reconstruct packets and commitments. Require commitment
before post-event passage evidence, an M-caused route difference, own/sham identity,
observable closed-route cost and observable false-targeting cost. Record success,
capped time, path length, inspections, replans, unavailable cues and bypasses.
Every failed continuation receives the same full900-tick score. No successful-only
analysis, model selection, inferential independence or R2 benefit claim follows.

Fresh branches and verified incremental commits use repository-local Aadrika Maurya
<aadrikamaurya@gmail.com>. Push via the provided SSH remote; API PR submission
requires actual Aadrika08 identity. No account switch, force push or automatic merge.
