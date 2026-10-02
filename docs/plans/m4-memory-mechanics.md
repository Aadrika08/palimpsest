# M4 memory mechanics and M5 development contract

Implementation contract fixed on 2 October 2026 before memory development. This isolated dependent draft does not qualify R2. Its M3 base remains frozen in a separate worktree for the actual 60-minute gate; R1 qualification remains pending. The engineering defaults below are fixed for development, not measured research outcomes. Held-out M5 evaluation requires a later explicit protocol freeze.

## Product constraints and development choices

**Approved:** history-to-unfamiliar-instance rule transfer; declared symbolic cue, bearing and local passage sensing; separate M/E/U; finite two-relation vocabulary or abstention; independent regime-generated truth; no unobserved negative labels; fixed reinspection bridge; nine conditions; atomic U-only branching; original FLYNN weights/input dimensions remain fixed. See implementation-plan M4/M5 and the brainstorm research section.

**Development choices fixed here:** exact schemas, relation names, support thresholds, freshness rules, one-target diagnostic budget, visibility defaults, baseline algorithms and integration details. Keep these in the versioned development protocol; they are engineering defaults, not measured properties or statistically justified thresholds. Use ordinary validated dictionaries/dataclasses and existing JSON/event/snapshot machinery; no new dependency or generic rule language.

## 1. `memory.py`: typed state and pure operations

All objects reject unknown fields, nonfinite values, booleans where integers are required, duplicate IDs, unknown enums and dangling references. IDs are nonempty strings of at most 128 characters. Tick/version integers are nonnegative. Canonical JSON is UTF-8, sorted keys, compact separators, `allow_nan=False`; array order is meaningful unless explicitly sorted below.

### Exact JSON shapes

`M = {"version":1,"facts":[Fact,...]}`; maximum 256 facts, sorted by `id`.

```
Fact = {
  "id": ID, "subject_id": ID, "kind": "passability",
  "estimate": "open" | "blocked" | null,
  "status": "unknown" | "observed" | "uncertain",
  "associations": [{"cue_id": ID, "relation": "local_cue" | "paired_cue"}],
  "inspection_landmark_id": ID,
  "evidence": EvidenceRef | null, "revision": int,
  "origin": "observed" | "initial_unknown"
}
EvidenceRef = {"id": ID, "episode_id": ID, "tick": int}
```

Associations are candidate spatial/task relationships, **not the complete causal dependency graph**. Sort them by `(cue_id, relation)`; at most one association per cue/relation. `unknown` requires null estimate/evidence and origin `initial_unknown`; known seeded facts require retained observation references and origin `observed`. Status `observed` requires a supported nonnull estimate. `uncertain` retains the last estimate/evidence, if any. Complete history of supporting/changed evidence lives in the authoritative event log rather than an ever-growing list inside each fact. Seed facts only from retained declared observations, not a truth-to-bank shortcut.

```
PassageObservation = {
  "id": ID, "episode_id": ID, "tick": int, "subject_id": ID,
  "passability": "open" | "blocked" | "unobserved"
}
Trigger = {
  "id": ID, "episode_id": ID, "tick": int,
  "kind": "cue_changed", "cue_id": ID,
  "before": 0 | 1, "after": 0 | 1,
  "before_observation_id": ID, "observation_id": ID
}
E = {"version":1,"episodes":[RevisionEpisode,...]}
RevisionEpisode = {
  "id": ID, "trigger": Trigger,
  "checks": [{"subject_id": ID, "relation": "local_cue" | "paired_cue",
              "before": PassageObservation, "after": PassageObservation}]
}
```

E is ordered historical episodes, containing the actual observed before/after values; it contains no gold target list, latent regime, test bank, test event, branch identity or future trajectory. Each prototype episode has at most one checked subject per relation; missing checks are permitted and are not negative examples. Before/after subjects and episode IDs must match, and `before.tick < trigger.tick <= after.tick`. Conflicted evidence is excluded. The source event/evidence bundle remains hash-linked for audit.

```
UArtifact = {
  "payload": {"version":1,"vocabulary":"passage-relations-v1",
              "rules":[{"trigger":"cue_changed","relation": Relation}]},
  "provenance": {"method": "history-fit-v1" | "hand-authored-v1" | "empty-v1",
                 "history_sha256": SHA256 | null,
                 "protocol_sha256": SHA256, "producer_sha256": SHA256,
                 "support": {"local_cue":{"observed":int,"changed":int},
                             "paired_cue":{"observed":int,"changed":int}}},
  "payload_sha256": SHA256
}
```

Hard limit: 4 KiB canonical **payload**, separately count provenance; full envelope at most 8 KiB, fitting the existing 16 KiB HTTP request ceiling. PRD maximum four rules is retained as a general bound, but this first vocabulary has one trigger and permits zero or one rule. Duplicate/conflicting trigger rules are rejected rather than resolved by order. Payloads contain no entity/bank IDs, replacement values, arbitrary expressions or motor instructions. Runtime selection reads payload only; provenance is not an input to behaviour.

### Operations and fixed semantics

```
fit(E) -> UArtifact
select(M, Trigger, UArtifact, *, limit=1) -> Selection
revise(M, Trigger | None, Selection, [PassageObservation], *, episode_id, tick)
    -> (new_M, [RevisionEvent], [ReinspectionRequest])
Selection = {"event_id": ID | null,"target_ids":[ID],
             "reason":"matched"|"no_rule"|"no_match"|"budget"}
ReinspectionRequest = {"event_id":ID,"fact_id":ID,"requested_tick":int}
RevisionEvent = {"fact_id":ID,"event_id":ID|null,"tick":int,
                 "before":Fact,"after":Fact,"evidence_ids":[ID],
                 "reason":"reconsider"|"direct_observation"|"conflict"}
```

Run `palimpsest memory-fit historical-observations.json > rules.json` to fit a validated E file offline. Input is bounded to 4 MiB; stdout contains the U artifact, and invalid input exits nonzero. This command uses no simulator/model or current test bank. Retain the source E with its artifact for audit.

`select` is pure and cannot mutate M. It matches the event's cue ID and the rule's relation; sorts matching fact IDs; returns at most the protocol budget. Use `limit=1` for the initial two-passage task, with the existing proposed maximum eight as a validation ceiling. The same budget applies to every comparison condition. Rule/target sorting is independent of regime and ID assignment is counterbalanced across conditions.

`fit(E)` takes **E only**, with immutable algorithm constants; no callback or optional M/event argument. For each relation, count independently verified episode checks where both before and after are observed; changed means unequal observed values. Count each episode/relation at most once. Require at least four valid episodes **for each relation within each history**. Four independent histories per regime may each contain four or more episodes; histories and episodes are distinct sampling levels. Emit the sole relation having changed/observed >= 3/4 while the other is <= 1/4; use integer cross multiplication. Otherwise emit no rule. Equal rates, insufficient support or ambiguous histories abstain. These conservative toy thresholds are fixed protocol choices, not significance tests. No automatic refitting during a trial.

Freshness/duplicates/conflicts:

- Live observations must be from the current episode and control tick. Future/wrong-episode evidence is invalid; older evidence is logged as stale and cannot change a fact. Historical observations can initialize M and enter E, but cannot masquerade as fresh live samples.
- The task owns a `(episode_id,tick,packet_sha256)` ingestion cursor. A fresh episode starts at tick zero and requires consecutive packets; restore resumes the retained cursor. The public common-goal ID is pinned on first ingestion and cannot change mid-episode. Replaying the identical packet at the same boundary is a no-op. Reusing an observation/event ID with different content fails validation. Canonical packet IDs derive from episode/tick/channel, not random UUIDs.
- Different fresh observation IDs giving conflicting values for one subject at one tick yield `uncertain`, retain the previous estimate, and log both references; neither wins. They generate no fit label. A subsequent unambiguous fresh observation can resolve uncertainty.
- First process reconsideration, then all fresh direct observations. Selection plus an observed cue change can mark a last-known expectation uncertain and request inspection; it never sets open/blocked. Fresh direct evidence resolves a selected expectation immediately and cancels that inspection request. **All conditions assimilate direct observations, including no-U and unselected facts.**
- `unobserved` neither asserts a value nor supplies an unchanged/negative training label. Repeated unchanged direct evidence may refresh its reference but does not increment revision unless estimate/status changes. Duplicate triggers neither re-mark facts nor restart the supervisor deadline.

## 2. `memory_task.py`: declared sensing and fixed bridge

Only `capture_symbolic(world, pose, occluders, episode_id, tick)` sees geometry/true pose. It returns:

```
SensorPacket = {"version":1,"id":ID,"episode_id":ID,"tick":int,
                "common_goal_id":ID,
                "cues":[{"id":ID,"state":0|1,"bearing_rad":float}],
                "landmarks":[{"id":ID,"bearing_rad":float}],
                "passages":[PassageObservation]}
```

Cues/landmarks list only presently visible entities. Passage entries cover the two known passage subjects; unseen/out-of-range entries say `unobserved`. Proposed profile defaults: visibility requires line of sight, <=4 m range and bearing within +/-90 degrees; passability additionally requires <=0.75 m distance to its inspection landmark and an unobstructed inspection sightline. Ground-truth occupancy is accessed only after visibility eligibility is satisfied. No exact position, distance, hidden occupancy, regime, scheduled intervention metadata or gold enters the packet. Concrete world geometry and physical acquisition remain a separate design step. The precise geometric probes and layout must be frozen in the scenario manifest and fixture-tested before M5; a virtual symbolic sensor is explicitly an engineered capability.

`detect(previous_sensor_state, packet)` produces triggers only for a cue seen on consecutive control ticks whose token changed. First sight, reacquisition after a gap, disappearance and an unchanged token do not produce a change event. Snapshot the detector state, including last tick and seen token; a missed hidden change remains a measured sensor limitation.

`advance_memory(memory_state, packet)` performs detection, selection, revision, request management, and returns effective bearing plus audit records. The bridge receives only M, requests and SensorPacket—not env or evaluator truth. One active request at a time, deterministic target order; hold the selected landmark until a fresh local passage observation resolves it or 200 control ticks expire. Do not preempt it with repeated triggers. Expiry logs failure and returns to the common task goal; no fabricated revision follows.

The common task-goal landmark is declared in the profile and must also be observed through this sensor. For an active visible inspection landmark, feed `[cos(bearing),sin(bearing)]` into the existing `sensors.wind_direction` channel. Preserve cameras/contact/preprocessing, learned weights and action conversion. A requested but currently invisible landmark remains pending while the common visible goal is followed. If the active landmark or common required goal becomes invisible, stop the trial with explicit `goal_cue_unavailable`; do not fall back to true goal bearing, invented `[0,0]`, direct steering or hidden pose. This conservative failure policy is a proposed first-profile ceiling, not a general search planner.

State to snapshot: M, E, U, ingestion cursor, cue detector's last observations, pending requests, active target, its start/deadline tick, and immutable task/protocol hashes. Separate `world_task_state` (cue values, gate mechanism/schedule) from the memory state; it belongs to world/evaluator snapshot state and is never passed to the bridge. Reset restores the recorded initial M and clears episodic detector/bridge state while preserving current E/U, including an applied U-only swap; reset neither consolidates nor erases a swap.

## 3. `memory_experiment.py`: independent generation and nine conditions

`make_case(seed, regime, split)` returns separately `(public_fixture, private_truth)`. Do not call `fit`, `select`, `revise` or a U interpreter to generate gold. The independent world mechanism couples cue changes to one passage grouping. Compute gold stale expectations from recorded pre/post occupancy changes, not from the selected rule or its predicted IDs. Preserve both states and the mechanism/seed in evaluator-only artifacts. Null cases can change the cue without changing occupancy; they have empty gold and expose false targeting. A repeated cue token is a distinct no-event case.

Training histories inspect **both** relation classes by a fixed data-collection schedule before/after events, independent of U. Publish only observations actually made; do not backfill hidden negatives. Test IDs are disjoint from training IDs; randomize/counterbalance lexical IDs, passage side and relation assignments. A test world has one fixed regime and a unique evaluator answer; swapped U is not equally correct merely because it came from a different regime. Each U-only comparison branches the same complete state within that world.

| Condition | Offline access | Runtime access and selector |
|---|---|---|
| own | E_A -> fitted U_A | M, observed event, U_A |
| swapped | disjoint E_B -> fitted U_B | identical M/event, U_B |
| sham | E_A -> exact copy U_A | same as own; transaction exercised |
| no-U | none | M/event; empty target set; direct evidence still assimilated |
| hand-authored | fixed developer rule, frozen before test | M/event plus fixed `local_cue` rule; no test regime/gold |
| history-independent | none | first fact by canonical ID, ignoring event/entity relation |
| traversal | none | all associations mentioning observed cue, canonical ID order, truncate at same budget |
| retrieval | same E_A as own, uncompressed | M/event and E_A; use the latest complete matching-trigger episode with exactly one observed changed relation; otherwise abstain |
| oracle | evaluator dependency/occupancy truth | capped gold IDs; explicitly privileged upper bound |

Retrieval has additional runtime history bytes; report actual access/budget rather than calling it equal-memory. Hand-authored guidance is not learned U or oracle. In the minimal bank some simple baselines may coincide; report that rather than treating nine labels as nine independent mechanisms. Only own/swapped/sham/no-U/hand-authored artifact replacement can be described as U-only under the same selector. Other conditions change the targeting method or information access and are labelled baseline comparisons.

Freeze protocol hash, generator/fit/selector versions, separate development/held-out seeds, complete history pairs, visibility/budget/timeout constants, metrics and tolerances before held-out use. Targeting primary outcome: paired exact-set correctness across case/history pairs (not frames), with false targets and abstention. Embodiment outcomes: first target/belief/cue/action divergence, reinspection success/cost and common task outcome. Keep null outcomes and failures. No claim of topology advantage follows.

## 4. Existing integration hooks and incompatibilities

- `Engine._step` (`engine.py:407`) is the boundary hook: capture symbolics after queued world edits, run memory, then construct the policy input. Its `sensor_vector` is currently built before policy projection; it must record the **effective** supervised bearing and separately retain the original/raw cue for audit. Never hand `self.observation` or `env` to selectors/revisers/supervisor. Existing upstream `_sensor_vec` calculates true-goal bearing from exact pose; that value must not become a fallback in this profile.
- `Engine.application_state/validate_application/restore_application` (`574/600/653`) enforce exact schema v2 keys. Add application schema v3 with nullable memory/task state and full validation. Accept legacy v2 only for non-memory profiles through explicit normalization; never fill missing memory state when restoring a memory trial. The outer snapshot schema can stay unchanged because `snapshots.capture` already copies a pure application dictionary, provided compatibility hashes bind the new profile and state semantics.
- `Engine.restore_branch` (`673`) is the restore hook. A new dedicated `POST /api/v1/memory/branches` takes exactly `{source_run_id,snapshot_id,u}`; returns the existing loading response then durable applied/failure status. It accepts no controller/world changes and requires an already closed source with no active owner. Validate the complete U and source snapshot before allocating a destination; failures preserve the immutable source. The current general `/api/v1/branches` close-before-validation path is not used for this transaction. Restore a fresh destination, hash all scientific state excluding only U and destination bookkeeping, replace U, rehash, then register/publish its initial snapshot. Failure preserves the source bundle and never advertises an applied swap. Log old/new U hashes and all invariant hashes; do not reset h/M or start the bridge during the transaction.
- Existing `worker._snapshot`/initial registration (`246`, `335–364`) already provides durable registered snapshots. Add memory inspection to `_sample` (`73`) from copied owner state, using the same tick IDs: hashes/counts, at most 16 selected facts and 8 recent transitions per sample; retrieve larger state on explicit inspection rather than broadcasting E at display frequency. Variable-size memory decisions belong in existing authoritative JSON events, not new shape-changing numeric arrays (`RunWriter.tick` requires fixed array shapes).
- `replay.py:_EVENTS` currently excludes every memory event and `_RUNTIME` excludes the three new modules. Extend both, and bind memory profile/U hashes. Policy replay must recompute and compare symbolic observations, selection, revision and bridge records as well as neural outputs. Action replay bypasses the policy and can reconstruct physical inputs; it must not claim to rerun neural inference or certify memory causality. Recorded playback simply displays retained memory events.
- Existing outcome handling calls upstream navigation termination (`Engine._step:467`). The memory task needs its own declared outcome predicate for reinspection/common-goal completion, while retaining timeout/failure handling; otherwise an unrelated upstream target can terminate a reinspection. This is a new validated task profile, not silent reproduction-profile behaviour.

M4 symbolic inputs are labelled fixtures until an actual world/sensor acquisition implementation is validated; M4 fixture success is not an embodied result.

## 5. Smallest meaningful checks before integration

One focused memory test module can cover: fit only from verified paired E, held-out IDs, insufficient/equal/conflicted support abstention, no labels from `unobserved`, input immutability, traversal control, payload/cap/unknown-field rejection, stale/future/duplicate/conflicting evidence, all-condition direct assimilation, hidden-state changes leaving declared packets unchanged, and fixed bridge bearing/timeout behaviour. Add focused existing-engine tests for full memory snapshot continuation, no-op self-swap, U-only invariant equality/rollback, replay first divergence and inspector consistency. Run asset-backed closed-loop validation separately in M5; synthetic tests cannot qualify embodied performance or R1.
