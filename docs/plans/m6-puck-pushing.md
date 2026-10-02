# M6 thin-puck manipulation: proposed bounded implementation

Plan-only branch `feat/puck-pushing`, based on integration
`fb778e83fb635bb45da3a983bf03841d5b6e0fc0`. No Engine/UI source, upstream file,
model, runtime, training or browser job has changed or run here. The
[prospective protocol](m6-puck-pushing-protocol.json) fixes the proposed geometry,
32 layouts, three training seeds, budgets and acceptance gates. Root review must
approve the plan and each actual execution window. Parameter changes after an
observed result require a new version, preserving the failed run and old protocol.

The intended result is a **separately trained controller pushing a thin disk by
native simulated contact**, with declared observations, failures and held-out
evaluation. A constant push verifies mechanics only. The analytical demonstrator
is a reference, not learned competence. A small task-specific CPU MLP is the
recommended first student; reusing a navigation checkpoint would not establish
the required skill, while modifying a connectome/retina architecture would widen
this slice. The proposed MLP makes no connectome, biological or visual-perception
claim and leaves every existing male/FLYNN asset pin unchanged.

## Traced paths and necessary differences

| Existing symbol at the base | Consequence for this profile |
| --- | --- |
| `profiles.configure_world`, lines 107–122 | With `n_obstacles=1`, park and disable the other nineteen named bodies; do not delete topology. |
| Pinned checker XML, lines 27–32 | `obstacle0_body` has three slide joints and no rotation, but currently describes a tall, 30 kg locked obstacle. Compile a derived thin disk. |
| Upstream environment constructor, lines 99–200; `Engine.open`, lines 295–302 | The constructor loads a fixed XML and resets once. Replace the constructed model/data/renderer before Engine construction, then use the owned reset path. No upstream mutation or monkeypatch. |
| `snapshots._bindings`, lines 414–439; staged `restore`, lines 531–570 | Reuse named-ID rebinding and allocate-before-commit ordering. Add explicit puck XYZ joint/qpos/dof validation; these are not all covered by `_bindings`. |
| Upstream `place_obstacles`/`reset`, lines 203–309 | Reset rewrites obstacle positions and locks XY joint ranges. The puck reset adapter must reapply the reviewed free ranges and authored state after reset. |
| Upstream `step`, lines 313–369; `Engine._step`, lines 643–797 | Native outcome/reward concern the rover reaching a navigation goal; existing task profiles also reject contact. Neither is the pushing objective. |
| `body_profile.contact_ownership`/`ContactProbe`, lines 77–245 | Reuse actual ancestry, ten timed contact-cache samples and callback cleanup. Derive puck classifications without treating intended puck contact as a calibration rejection. |
| `worker._episode_preflight`, lines 240–258 | Currently assumes every policy has `agent.cell.Nin` and `hidden`. Add explicit puck diagnostic/contact bytes and the trusted case's tick allowance, preserving defaults. |
| `snapshots._stage_policy`, `Engine.validate_application`, `replay._same_tick` | Add a stateless puck policy kind, versioned task cursor, and explicit puck numeric replay fields. Preserve historical schemas and checks. |

All upstream references mean the pinned
`8d964599119b420de67ee259434d273651a1a76d` checkout. The plan inspected that source
read-only in the sibling training worktree; this worktree has not initialized or
compiled its upstream dependency.

## Fixed derived model, with a narrow constructor hook

Read at most 128 KiB of the hash-pinned checker XML. Parse it with stdlib
ElementTree; require exactly one match for every selector in the protocol and
apply only those attribute edits. Retain all bodies, joints, geoms, cameras,
actuators and their names. The protocol pins the resulting 16,778 XML bytes and
SHA256 `f6a781836d21c5fd8ffb6b1e35f7ca47586772e11e2b1329695a6965ea5fb06a`.
Compile that string with the existing pinned MuJoCo. This is a fixed M6 model,
not an R1 live model editor or an arbitrary model-path API.

The disk has radius 0.25 m, thickness 0.12 m, mass 0.25 kg, body height 0.062 m
and explicit solid-cylinder diagonal inertia
`[0.00420625, 0.00420625, 0.0078125] kg m²`. XY slide limits are ±5.5 m and the
Z slide limit is ±0.002 m. There are no rotational degrees of freedom: this is
an authored near-planar contact model, not proof about a freely tipping or spinning
physical puck. Friction is `[0.25,0.005,0.0001]`, priority 1, condim 3; contact
solver settings are pinned too. Higher-priority geom parameters control the
contact mixture, so changing just a lower-friction puck at equal priority would
not give the declared friction. Verify realized contact settings in the native
gate. [MuJoCo 3.3.6 contact rules](https://mujoco.readthedocs.io/en/3.3.6/modeling.html#contact-parameters)

Do not mutate `geom_size` on an already compiled model and assume `mj_setConst`
rebuilds collision bounds. Its pinned implementation recomputes constants and
statistics, not geom/BVH boxes. The fixed XML compile owns those derived values.
[Pinned implementation](https://github.com/google-deepmind/mujoco/blob/3.3.6/src/engine/engine_setconst.c)

Proposed new helper: `puck_profile.install_fixed_model(env, repo_root)`. The only
constructor change is an exact `puck-pushing-development` branch in `Engine.open`
after `_make_env(None,1,'checker')` and before `configure_world`/`Engine.__init__`.
No generic environment factory or new dependency is needed. The helper stages:

1. New compiled model, `MjData`, renderer at 128×128, and `_view_scn` at the old
   explicit capacity. Require no window, `_view_ctx`, active callback or tick.
2. Exact named structural signature and dimensions (`nq/nv/nu/nbody/njnt/ngeom/
   ncam/nsite`), joint types/axes, base and wheel addresses, actuator order/ranges/
   gear, geometry ownership, camera dimensions and fixed environment settings.
   Check all cached IDs/lists plus `_obstacle_x_qposadr`/`_obstacle_y_qposadr`,
   `_obstacle_xy` shape `(1,2)`, goal/previous/action array shapes, `_action_scale`
   and `k_nearest`. Rebind by name even if integer IDs happen to remain equal.
3. Commit the staged objects/bindings together, then close the old renderer.
   Close every newly allocated renderer on staging failure; leave the old owner
   unchanged or fail construction before an Engine exists.

Reset uses `mj_resetData`/upstream reset, then restores wide puck XY limits,
places the declared rover/puck/goal with zero velocities, fixes colour, resets
task caches and refreshes native state once before observation. No reset,
teleportation, applied puck force or world edit occurs during an episode. Update
the obstacle cache from actual puck state after each step; never move the puck to
make that cache agree. Require only the original two wheel actuators, zero
`qfrc_applied`/`xfrc_applied`, and no hidden global control callback.

The native model hash is **unmeasured**. The first approved construction gate must
compile twice in fresh owners and pin the deterministic model/profile identity.
No compilation success or contact stability is inferred from this XML review.

## Observation, control and objective

The student receives eight float32 values only: body-frame puck XY and goal XY,
each divided by 14 m; puck world velocity expressed in body axes, divided by
2 m/s; previous-interval rover–puck and other-rover-contact booleans. These are
explicit **virtual geometry/velocity/contact sensors**, with omnidirectional
availability. They are not camera detections or physically implemented sensors.
Reject missing, stale, nonfinite or out-of-range values; do not clip or substitute.
Two ordinary RGB eyes may remain in the record/viewer, but are not model inputs.

Use current native qpos and the base-free quaternion for position/yaw, and named
puck slide qvel for velocity. Do not silently combine post-integration qpos with
older `data.xpos` caches. Contacts refer to the preceding ten pre-integration
stages, ending at `t-0.002`, not an invented contact sample at `t`. The first
packet explicitly marks its initial forwarded cache. Record packet index,
source interval and the exact vector supplied to each one-step policy invocation.
No extra `mj_forward` is inserted during stepping to change this contract.

Raw world coordinates, full native state, contact pairs and exact puck-goal
distance remain evaluator/declared privileged demonstrator data. Only the packet
crosses the learned controller boundary. Record both roles explicitly. Reuse
`ContactProbe` without changing its calibration semantics: retain its raw packet,
then classify named puck–rover pairs as intended, named wheel/floor pairs as
support, and remaining robot contacts or puck/wall contact as failure. This is
sampled native contact evidence, not continuous contact or force measurement.

The profile runs at 0.002 s × 10 physics substeps, one 0.02 s control tick, at most
600 ticks and one episode. Success requires puck center within 0.20 m of the
goal, puck speed ≤0.03 m/s for ten consecutive ticks, prior actual rover–puck
contact, and puck displacement ≥0.5 m. The drawn goal disk radius is 0.45 m.
Success reason is `puck_goal`. Outcome/reward come from puck state; reward is only distance-before minus
distance-after in metres. Retain upstream navigation reward/flags as diagnostics,
not task outcomes. A rover reaching the goal without the puck cannot pass.

Stop on nonfinite state, unexpected contact, recorded penetration beyond 0.02 m,
|rover/puck XY| beyond 5 m, puck Z deviation beyond 0.02 m, puck speed above
2 m/s, or 100 consecutive ticks with both bodies moving <0.002 m while commanded
|velocity|>0.05. Tick 600 is a natural time limit. These are prospective simulation
admission limits, not physical safety limits. Record the final interval before
halting, zero controls, and retain the exact failure/outcome.

## Demonstrations and the separately trained controller

`puck-teacher` is an explicit privileged analytical demonstrator, distinct from
the navigation teacher. It aims at a point 0.55 m behind the puck along the
puck-to-goal direction. Approach at 0.25 command units only after heading error
is within 0.12 rad; otherwise turn in place with heading capped at ±0.4 rad.
Push at 0.20 when axial separation is 0.35–0.63 m, lateral error ≤0.06 m and
heading is aligned. Otherwise return to the approach rule. Stop at puck-goal
distance ≤0.18 m, with this rule taking precedence, including zero distance.
All stated thresholds include equality. Use the goal direction when the rover
is within 0.08 m of the behind point; otherwise aim at that point. A zero-length
aim vector also uses the goal direction. Heading error beyond 0.12 rad gives
zero forward action; otherwise choose push velocity only when both axial/lateral
conditions hold, approach velocity otherwise. Derive decisions from current
geometry; no hidden recovery retry, teleport, or replacement scene. Pure fixtures
must exercise each boundary. Demonstrator success is unmeasured.

The student is exactly `8→32 tanh→32 tanh→2`, with `0.4*tanh` outputs for velocity
and heading. It is stateless across invocations; no fake retinal, recurrent or
population fields are exposed. Use the existing pinned CPU Torch, float32 and one
thread; the existing teacher owner keeps two CPU threads. Seeds 21/22/23,
thirty epochs, Adam 0.001, batch 64, gradient norm cap 1,
no weight decay/augmentation. Normalize both action residuals by 0.4 for MSE.
Select each model's earliest minimum recorded-dev loss; report all three models.
Preserve fixed data/protocol/source/feature/checkpoint hashes and actual histories.
Bounds and artifact guards reuse existing trainers/readers, not the male
architecture, targets, losses or production asset resolver.

Use explicit `puck-mlp` identity with a fixed task manifest and checkpoint hash;
reject production male/FLYNN weights, wrong feature/profile hashes, tensors with
wrong finite shape/dtype, or incomplete training reports. Check file and ZIP
uncompressed caps before `weights_only=True` loading. A narrow trusted Python
research binding may select only one of the three manifest-pinned models; no
arbitrary REST/UI asset path or registry. This binding and the exact Engine
controller admission changes require root source review before implementation.

## Prospective stages and stopping rules

All 32 authored layouts are explicit in the JSON, rather than regenerated after
failure. They include different push axes, lateral offsets, distances and initial
heading errors; held-out combinations are disjoint. Absolute orientation alone
does not create independent information for an egocentric virtual-sensor policy.
The claim remains these bounded layout families, not general manipulation.

1. **Native mechanics/continuation gate:** fixed physics seeds 5990–5994. Zero
   controls must not translate the puck; two opposite-direction constant pushes
   must produce ≥0.10 m native displacement with actual contact. Two analytical
   demonstrations must complete the task. These are mechanics/reference checks.
   Qualify native continuation from approach, first contact and first stopped
   success-dwell boundary, plus one action and one teacher-policy replay. All
   trigger boundaries are predeclared; absent contact/dwell is failure. Ten
   owners maximum; no manual push is counted as learned success.
2. **Teacher collection:** train 6000–6015, recorded dev 6016–6019; twenty fresh
   owners. Require all twenty goals, each training run ≥32 ticks, ≥10 intended
   contact ticks and ≥10 terminal zero-action labels. Retain every natural
   outcome; a failed teacher/data admission prevents training. Infrastructure
   failure stops immediately and leaves later rows `not_started`.
3. **Training:** all three fixed seeds in order, same data and thirty-epoch
   budget. Stop first failure, retain all planned model statuses. Publish the
   immutable manifest only when all three finish. No hidden held-out loader.
4. **Closed-loop dev:** scenes 6100–6103 × all three models, twelve owners.
   Require all owners to finish without infrastructure errors and each model
   to reach ≥3/4 goals. Match initial native world and declared-input hashes across
   models. No winning-seed selection or dropped outcomes. Audit before root review.
5. **Held-out:** only after exact dev receipt and separate root GO, scenes
   6200–6207 × all three, twenty-four owners. Require ≥6/8 goals for every model
   to pass this bounded learned gate. Report every result, including failure.
   Never tune, retry or select models using these results. Failed admission keeps
   this stage unopened.

All owners serialize through existing LabSupervisor/worker ownership and retained
`bounded_process` supervision. Preserve full plans, stdout/stderr, source/assets/
model inventories, source/asset immutability checks, PID/start-identity cleanup
and independent record audits. Natural task failure is distinct from an owner,
storage, protocol or watchdog failure. No fallback to a demonstrator at inference.

| Stage | Internal seconds | TERM / KILL grace / supervisor seconds | Storage cap |
| --- | ---: | --- | ---: |
| Mechanics | 600 | 660 / 15 / 680 | 1 GiB |
| Twenty teacher episodes | 1500 | 1560 / 15 / 1580 | 4 GiB |
| Training, each of three seeds | 120 | 180 / 15 / 200 | 16 MiB each; 64 MiB total |
| Twelve dev episodes | 1200 | 1260 / 15 / 1280 | 3 GiB |
| Twenty-four held-out episodes | 1800 | 1860 / 15 / 1880 | 4 GiB |

Per owner: startup 60 s, progress 30 s, total 180 s. A 600-tick recording plus
snapshots is capped at 160 MiB; 120-tick roots at 64 MiB; four-tick branches at
32 MiB. Each snapshot ≤8 MiB, report ≤4 MiB, log ≤1 MiB. Checkpoint ≤1 MiB with
≤2 MiB uncompressed ZIP members. Require 1 GiB free and a 16 GiB aggregate
retention cap. Reserve complete planned allowances before opening a stage.
The mechanics plan's three short roots, two long roots, three short branches and
two replays allow 832 MiB, leaving 192 MiB for reports/logs under 1 GiB. The trusted
fixed case supplies its 120/600-tick estimate, and a branch supplies its four-tick
limit; do not apply the default 600-tick estimate to a 64 MiB short-run allowance.
This is a validated internal case contract, not an arbitrary UI duration override.

Resource estimates are provisional: previous 128×128 native M7 rollouts took
685.8 s for 7,668 ticks, including owner overhead. Linear scaling suggests roughly
18 minutes for maximum-length teacher data, 11 for dev and 22 for held-out. It is
not a measured puck throughput prediction. The small MLP has no measured training
timing yet. Hard caps above do not extend if either estimate is wrong.

## Small source slices and verification

First approval should cover only new `puck_profile.py`/pure fixtures: exact XML
derivation, structural checks, fixed layouts, sensor/goal/failure contracts and
demonstrator arithmetic. Root then reviews the native constructor hook and
owned Engine wiring as a separate slice. No generic simulator/controller layer.

Later narrow integration touches `profiles.validate`, `Engine.open`/reset/step/
outcome/application staging, `worker._episode_preflight`, snapshot staging and
replay source/field admission. Store an explicit `puck_state` (cursor, prior
contact interval, initial puck pose, success/stall counters, protocol identity).
Use a new scenario-only application schema, preserving old ones. Validate the
native disk geometry/inertia, joint ranges, puck state and all source identities
before committing restoration; the existing model digest intentionally excludes
`jnt_range`, so that range check cannot be omitted. Rebuild puck bindings after
native restore. Policy replay compares actual task inputs/raw outputs/actions;
action replay compares physics, contacts, task state and outcomes without claiming
inference. Old snapshots and production resolvers remain strict.

Meaningful pure fixtures: malformed/duplicate XML selectors; exact named topology;
all split layouts and geometry clearances; egocentric rotation/velocity units;
contact-time indexing and stale packet rejection; rover-at-goal/puck-away failure;
goal dwell reset; finite/action guards; data split and no-held-out admission;
loader byte/schema/hash rejection; staged restore rollback and legacy defaults.
The actual gate separately proves compile/binding/renderer cleanup, native contact,
no external puck actuation, cache timings, deterministic continuation and replay.
Training and learned held-out behavior are later evidence. UI listing/controls,
browser testing, exhibition and physical qualification are outside this first plan.

Preparation checks used stdlib only: exact XML byte/hash derivation, preservation
of every element/tag/name, 32 unique finite layouts with disjoint split IDs and
spawn clearance, ten planned mechanics owners, and all stage/aggregate storage
arithmetic passed. `git diff --check` passed. These checks did not import Torch or
MuJoCo, compile a model, execute the proposed controller, or validate dynamics.
