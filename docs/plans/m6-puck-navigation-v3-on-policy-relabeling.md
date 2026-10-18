# M6 puck navigation v3: one on-policy relabeling round

> **Status:** prospective documentation only. This commit authorizes no retained-input access, scene minting, model loading, Torch or MuJoCo import, collection, fitting, simulator execution, development, or held-out access.

**Goal:** Test whether one fixed round of analytic-teacher labels on states reached by the existing original puck students can meet the unchanged fresh-scene capability gates.

**Base and predecessor:** [`feat/puck-balanced-development`](https://github.com/Aadrika08/palimpsest/pull/56) at `dac56f95ad29cb1ad19e7a64aa8df4023ea27f9b`, the exact remote PR #56 head. The machine-readable [protocol](m6-puck-navigation-v3-on-policy-relabeling-protocol.json) is authoritative.

## Why this intervention

The retained diagnosis measured **0 teacher-training rows versus 1,575 student-development rows** in the joint BEFORE-approach condition “contact true, ready corridor, and behind-point arrival still greater than 0.08 m.” That is a support gap and a plausible compounding-error mechanism. It is not proof that new labels will repair control: all original models also fit some existing teacher strata poorly, and the balanced-loss arm failed the same 3/4 development gate.

This study freezes one intervention only: **one offline aggregation round of the unchanged teacher's actions on states visited by the existing original students**. Existing original models 21, 22, and 23 collect; the teacher labels each pre-action state exactly once; only the student's action advances the world. Every admitted new row is appended to the original training split and shared by all three fresh fits. There is no state filtering, coverage-triggered stop, teacher takeover, action blending, weighting, architecture change, feature change, objective change, training-clock change, checkpoint rescue, or second aggregation round.

The primary estimand is the complete fixed aggregation procedure. Adding rows under an unchanged 30-epoch clock also adds optimizer updates, and all visited-state labels—not only the measured joint condition—enter training. A result therefore cannot isolate targeted-state coverage from added data volume, other newly visited states, or extra updates.

## Frozen identities and contamination gate

The scene IDs are reserved prospectively:

| Role | Exact IDs | Use |
| --- | --- | --- |
| On-policy collection | `6110–6113` | Existing original models 21/22/23, twelve owners |
| Closed-loop development | `6120–6123` | Existing original and new relabeled models, twenty-four owners |
| Held-out | `6200–6207` | Existing task-v5 authored rows; locked from access or execution before a separate reviewed plan and GO |

The numeric reservations are not yet evidence of disjoint geometry. Before any ID is minted into a scene registry or any geometry is generated, a separately reviewed admission must:

1. enumerate every reachable commit under all local heads/tags, remote-tracking refs, and freshly advertised remote heads/tags/pull refs, plus every registered worktree;
2. parse scene/layout fields in every tracked plan, report, manifest roster, and evidence index rather than substring-matching unrelated byte counts or hashes;
3. parse every retained raw scene registry and manifest and every prior evidence root, without executing a model or simulator;
4. reject an exact ID reuse against any earlier train, recorded-dev, development, evaluation, or held-out roster; and
5. allow only this protocol's exact eight-ID roster and its one hash-bound reservation/scene-manifest lineage, reject every occurrence outside that lineage as a collision, and atomically publish one reservation manifest for all eight collection/development IDs.

Task v5 intentionally admits only its 32 explicit authored rows: the current `puck_profile.layout` and `authored_reset` cannot accept these new IDs, and this plan does not pretend otherwise. The source phase must add one pure v3 layout minter plus a narrow keyword-only explicit-layout reset seam. Before the minter is called with any reserved ID or can write a candidate, an independent review freezes its deterministic one-to-one ID mapping, finite parameter domain and exact arithmetic, exact source/runtime/argv, and synthetic-fixture proof that the historical layout/reset call path is unchanged and still rejects every unlisted ID. Each ID yields one payload; there is no candidate search or geometry replacement after a collision. This is task plumbing shared by both development arms; the XML, physics, sensors, contact/task arithmetic, teacher, and original authored layouts remain unchanged.

After that source freeze, reservation, and a separate execution GO, one bounded scene-mint attempt generates all eight candidate payloads without loading a model or running an episode. Before any candidate is admitted for use, it must satisfy the unchanged task-v5 numeric layout invariants and reject duplicate canonical scenes, scientific initial states, or complete payloads against every earlier split and between new collection and development. It then atomically publishes one exact scene manifest. Collection processes receive only a collection projection; development payload paths and bytes remain unresolvable to collection, preparation, fitting, and checkpoint selection until the single development stage. Any collision, missing root, unreadable registry, incomplete remote-ref inventory, minter drift, or generator failure stops this protocol and retains inadmissible failure evidence. IDs are never substituted in place. A replacement needs a versioned protocol and another independent review. The already authored task-v5 held-out rows `6200–6207` are not regenerated, opened, or executed by this protocol.

A planning-time tracked-document scan found no candidate ID used as a puck scene in current local and remote-tracking ref tips or reachable documentation history. Textual matches were non-scene material such as hash substrings and an unrelated 6,112-byte count. This is a candidate screen, not the required fresh remote-ref, raw-registry, geometry, initial-state, or payload admission.

## One collection round

Collection order is scene `6110,6111,6112,6113`, then original model `21,22,23`: twelve owners and at most 7,200 completed intervals. Each owner starts one fresh natural episode from its exact admitted v3 scene-manifest row through the narrow reset seam, with the task-v5 XML, physics, sensors, task, contact rules, own phase cursor, runtime, and original checkpoint identity already pinned by the predecessor. The owner ends naturally or at 600 intervals. There is no reset, replacement, retry, perturbation, prefix, rescue, or post-terminal continuation.

At each pre-action state:

1. retain the exact float32 eight-sensor packet and independently prepared float32 nine-input vector with the student's own BEFORE-mode bit;
2. query the unchanged analytic teacher exactly once and retain its float64 two-action label and before/after private cursor fields;
3. prove the query left native state, effective student observation/input bytes, the student's cursor, and relevant Python/NumPy/Torch/environment/space RNG states unchanged;
4. call the frozen student policy exactly once and retain its predicted/executed float64 action separately; and
5. execute only that student action, then atomically commit both cursors and the row after the native interval completes.

Teacher diagnostic state may advance only as already declared and is audit metadata, never a student feature. Teacher and independently reconstructed sensor-only modes must agree before and after every complete interval; disagreement stops the batch without repairing either cursor. A query, inference, action, step, record, or cursor failure commits neither a row nor a cursor and stops later owners. No teacher action is executed. All complete admitted rows and natural outcomes remain, including rows outside the motivating condition.

The motivating condition is evaluated with the existing predicates: own BEFORE-mode is approach, contact is true, axial distance is in `[0.35,0.63]` m, absolute lateral distance is at most `0.06` m, and behind-point distance is greater than `0.08` m. The collection gate requires all twelve owners to finish with normal admission and at least one admitted motivating-condition row from each collector model. Zero such rows for any model is a valid falsification: preserve the collection, publish failure, and do not train. Counts are diagnostic and cannot be used to crop, weight, choose a collector, extend a trajectory, or run another round.

## Unchanged fit with one data addition

The base data remain exactly 5,710 teacher-training rows from `6000–6015` and 1,314 recorded-development rows from `6016–6019`. The new training corpus is the ordered base 5,710-row split followed by every admitted collection source in the fixed scene/model order. With twelve natural sources of 1–600 rows, the new corpus contains `5,710 + C` rows, where `12 ≤ C ≤ 7,200`; the maximum is 12,910. There is no row removal, duplicate weighting, balancing, oversampling, target mixing, or use of development or held-out rows.

Fresh models 21/22/23 train from their normal deterministic initializations. These items remain unchanged:

- `9→32 tanh→32 tanh→2 tanh`, 1,442 float32 parameters;
- float32 inputs and model arithmetic, float64 teacher targets, and float64 `0.4` action scaling;
- unweighted mean normalized MSE over both action components;
- 30 epochs, batch 64, the existing seeded training-only permutation, ordinary final partial batch, Adam `0.001`, weight decay `0`, gradient-norm cap `1`, CPU and one thread;
- the unchanged 1,314-row recorded-dev mean loss each epoch; and
- the earliest strict recorded-dev minimum independently for each seed.

At the maximum corpus size this is at most 202 updates per epoch, 6,060 per model, and 18,180 across all three. This bound follows mechanically from the data intervention and does not redefine the clock. The maximum is 2.2445 times the original 2,700 updates per model; the pinned historical report records 6.90–7.97 seconds fit/finalize and 12.47–17.07 seconds supervised per seed, so the unchanged 120/200-second bounds are feasible planning limits, not a runtime promise. All 90 epoch records, three checkpoints, exact row/source order, and before/after source/data hashes are retained. An operational or numeric failure stops later seeds; there is no retry, warm start, winning seed, epoch extension, or partial-model promotion.

The existing original checkpoints are not refit. They are immutable paired baselines and collection policies. Balanced-loss checkpoints are excluded. Before development, a compact review must admit all three new bundles and one prospectively fixed reuse of the existing four-owner native/replay mechanism. It uses relabeled-v3 model `21` and the exact admitted scene-manifest row for collection scene `6110`, after the fixed collection stage has already spent that row. The mechanism source is a new bounded v3-model-21 trajectory on the same scene row; it does not reuse an original-collector trajectory or open another scene.

The four owners run in this exact order: (1) source acquisition from the scene-6110 reset for at least 5 and at most 120 complete intervals, retaining `initial` and `tick1`; (2) native continuation from `tick1` for exactly the next four complete intervals; (3) saved-action replay from `initial` for the complete source duration with zero predictions; and (4) policy replay from `initial` for the complete source duration with one prediction per interval. Source and native-continuation owners also predict once per interval. Every owner constructs the same pinned relabeled-v3 seed-21 CPU MLP before capture or restore; there is no controller replacement. A natural source outcome remains an outcome, and missing tick-1-plus-four successor coverage fails admission. This fixed operational check permits no post-training model or source choice and is not another scientific arm or a task-success result.

## One development pass and locked held-out

Development uses scenes `6120–6123` in scene-major order, then seed `21,22,23`, then existing-original followed by relabeled-v3: exactly 24 owners and at most 14,400 intervals in one stage attempt. For each scene, all six owners must match the same scientific initial state before action 1; model identity and Torch RNG retain their established separate treatment. Each owner runs one natural, teacher-free episode of at most 600 intervals with one policy prediction per interval and no intervention, reset, fallback, or rescue.

All natural outcomes are collected before functional scoring. Infrastructure or admission failure stops later owners and retains `not_started`; a natural non-goal is a functional failure and does not stop the remaining fixed owners. Development passes only if all 24 owners are normal and admitted and **each relabeled-v3 model independently reaches at least 3/4 goals** under the unchanged native goal result. Original-model outcomes and paired per-scene differences are descriptive; there is no comparative threshold, pooling, or winning-model selection.

Even a passed development report does not authorize held-out. Scenes `6200–6207` remain unreachable until a separate held-out protocol and execution manifest bind the exact 48-owner paired order, source/model/manifests, disjointness proof, resources, invocation, one-attempt policy, independent review, and explicit GO. The later unchanged gate is all 48 owners normal and each relabeled-v3 model at least 6/8 goals. No development or held-out result may change data, labels, thresholds, seeds, epochs, selection, or runtime.

## Attempts, deadlines, and storage

Every retained-input or numerical stage gets one durable attempt reservation before its first input/runtime access. Crash, timeout, partial output, or outer termination consumes the stage attempt. Success is the last atomic publication after source/input rehash, final caps, fsync, process drain, and lease release. Failure evidence is retained atomically and can never be interpreted as success.

| Stage | Fixed work | Deadline ledgers | Output cap |
| --- | --- | --- | ---: |
| Ref/registry admission and reservation | one scan/reservation attempt | 600 s internal + 50 s normal-return + 10 s hard margin = 660 s | 64 MiB |
| Collection/development scene mint | 8 scenes, 180 s each | 1,440 s child + 50 s parent = 1,490 s internal; +50 s normal-return = 1,540 s; +10 s hard = 1,550 s | 256 MiB |
| Collection | 12 owners, 180 s each | 2,160 s child + 50 s parent = 2,210 s internal; +50 s normal-return = 2,260 s; +10 s hard = 2,270 s | 3 GiB |
| Data preparation | one attempt | 180 s internal + 50 s normal-return + 10 s hard = 240 s | 64 MiB |
| Training | 3 seed owners, 200 s each | 600 s child + 50 s parent = 650 s internal; +50 s normal-return = 700 s; +10 s hard = 710 s | 64 MiB |
| Mechanism admission | 4 owners, 180 s each | 720 s child + 50 s parent = 770 s internal; +50 s normal-return = 820 s; +10 s hard = 830 s | 1 GiB |
| Development | 24 owners, 180 s each | 4,320 s child + 50 s parent = 4,370 s internal; +50 s normal-return = 4,420 s; +10 s hard = 4,430 s | 4 GiB |
| Held-out, only after separate GO | 48 owners, 180 s each | 8,640 s child + 50 s parent = 8,690 s internal; +50 s normal-return = 8,740 s; +10 s hard = 8,750 s | 8 GiB |

The 50-second parent ledger is 20 seconds pre-owner admission/reservation, 20 seconds cumulative launch/reap/accounting, and 10 seconds reduction/pending-report staging. The separate 50-second normal-return ledger is 15 seconds final source/input/cap checks, 20 seconds fsync/atomic publication, 10 seconds release/identity drain, and 5 seconds return guard. Unused time never moves between child, parent, normal-return, or hard ledgers.

Per native owner remains 160 MiB; each initial snapshot remains 8 MiB; each log remains 1 MiB. Owners run sequentially, and every active stage process tree, including parent plus child, has a 1 GiB RSS ceiling. Every stage retains a 1 GiB free-space floor and the existing 16 GiB retained-run cap. The pre-held-out stage caps sum to 8.4375 GiB; including the free floor requires 9.4375 GiB before collection and fits that cap. Retaining every earlier stage at its maximum plus a later 8 GiB held-out stage would require 17.4375 GiB including the floor, which exceeds the current cap. The separate held-out review must therefore prove measured retained bytes plus the full held-out allowance and floor fit within 16 GiB, or freeze and independently approve a larger retention contract. It may not delete evidence or loosen a live check to proceed.

## Source plan and required synthetic proof

Use one named `puck_on_policy` adapter and thin stage entrypoints around the existing record, teacher, student, trainer, bounded-process, storage, and development helpers. The only shared-path edits are the keyword-only explicit-layout seam in `puck_profile.authored_reset` and one explicit on-policy/development envelope route in `verify_puck_mechanics.py`; historical calls and envelopes keep their behavior. Preserve historical loaders and default paths. Do not add a generic policy registry or change production Engine/UI behavior.

The runtime remains Python 3.11.15, NumPy 2.2.5, Torch 2.9.0, MuJoCo 3.3.6, EGL, CPU, and one training/inference thread. Before any protected access, the execution manifest must bind the protocol, minter, every new/edited source and test, package initializer, complete transitive local behavior-source closure, upstream/runtime identities, exact argv/environment/cwd/output paths, immutable input hashes, and the stage supervisor. The direct hashes recorded in the machine-readable plan are orientation only and cannot authorize execution.

Before any source or execution freeze, synthetic tests must prove:

- exact scene/model/source order, strict old/new schema separation, and held-out arguments rejected before Torch or MuJoCo import;
- typed all-ref/worktree/raw-registry roster scanning, including the sole exact self-reservation exception plus collision, missing-root, stale-ref, symlink, and partial-inventory rejection;
- current task-v5 APIs rejecting the new IDs; fake-minter fixtures proving exact eight-scene staging order, unchanged numeric layout checks, cross-split canonical/initial/payload duplicate rejection, collection-only projection, development path denial, and no model or episode execution; and pure minter arithmetic exercised only with nonreserved fixture IDs;
- exactly one teacher query and one student inference per complete interval, query isolation, student-only action execution, and commit-after-step cursor semantics;
- every admitted row enters the common corpus once, fixed concatenation order, exact motivating-condition counts, and no filtering or coverage-triggered stop;
- unchanged feature, dtype, scale, loss, 30-epoch/batch/shuffle/optimizer/selection semantics and the 12,910-row/6,060-update maxima;
- strict model-index admission, fixed mechanism replay, matched scientific initials, exact 24-owner development reduction, and held-out unreachability;
- durable reservation and first-failure retention under crash, timeout, fsync, rename, source drift, nonfinite values, RSS/storage/output overflow, and final publication failure; and
- exact-boundary success plus one-tick child, parent, normal-return, or hard-deadline failure for every multi-owner stage, including scene minting.

Implementation ends with a hash-bound execution manifest and independent review before any raw registry, retained input, model, Torch, MuJoCo, scene minter, or simulator access.

## Evidence boundary and stop conditions

A passed development stage would support only simulator capability of this fixed one-round relabeling procedure on four fresh scenes. A later passed held-out stage would support only its declared eight-scene simulator criterion. Neither result establishes that the measured support gap was causal, that the analytic teacher is correct or fully student-observable, that more rounds would help, or that the system has physical, biological, safety, UI, release, or general-purpose capability. `qualification_claims` remains empty at planning time.

Stop and retain failure on any protocol/source/runtime/ref inventory/ID/scene/initial/payload/model/data/order/count/dtype/query-isolation/cursor/finite/deadline/RSS/storage/publication/cleanup mismatch. Stop after a failed collection coverage gate, incomplete training set, failed mechanism admission, or failed development gate. Do not repair, retry, replace, tune, reopen a consumed attempt, or touch held-out.
