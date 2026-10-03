# Puck learning v1 — pure contract and staged implementation

This source slice implements the **own sensor-only phase cursor, ninth BEFORE-mode
input, output scaling and teacher-record admission**. It implements no model,
collector, native runtime adapter or training job. The separate
[learning protocol](m6-puck-learning-v1.json) pins the immutable
[v4 task protocol](m6-puck-pushing-protocol-v4.json); `load_protocol` resolves its
32 layouts, limits, original eight-sensor normalization, hyperparameters and
admission thresholds directly. Old task/physics files and production Engine/models
remain unchanged. [Mechanics attempt v5](../reports/m6-puck-mechanics-v5.md) passed
the standalone development gate; this is not evidence of learned pushing.

The existing stateless eight-input proposal cannot represent the teacher over all
admitted states. With the same world, rover `[-.4,0,0]`, puck `[0,0,.062]`, zero puck
velocity and goal `[1.2,0]`, carried approach requests reverse `[-.25,-0.]`, while
carried push requests `[.2,0.]`. Mode is absent from the eight instantaneous
sensors. This is an authored source example, not a claim both states occurred.
At 296 of the 722 retained v4 teacher worlds the two mode arguments yield different
commands; 61 yield opposite velocity signs. Those alternate-mode source evaluations
are not counterfactual rollouts or observed conflicting label pairs. The candidate
sensor-only cursor matched all 722 actual before/after modes, but float32 sensor
quantization can disagree with privileged float64 geometry at future boundaries.

The implemented interface is deliberately small:

- `initial_cursor` creates only approach/tick 0 with the learning protocol identity.
  `validate_cursor` rejects other versions, pins, modes and malformed ticks;
  `prepare` rejects any new decision after completed tick 600.
- `prepare` accepts only the eight float32 sensors and that own cursor. It stages
  the nine-input vector and next cursor without mutation. Component nine is the
  **before** mode, encoded 0 for approach or 1 for push. No teacher, world/native
  state, action, outcome or camera crosses this inference boundary.
- Geometry arithmetic promotes the first four sensor components to float64 before
  undoing `/14`. Stop distance ≤.18 is checked before division, including coincident
  puck/goal. Otherwise the same axial/lateral readiness and behind-point arrival
  conditions choose the next mode. The exact comparisons include equality;
  float32 neighbors around the frozen thresholds have explicit fixtures.
- `commit` checks predecessor, exact completed tick, staged sensor hash, nine input
  bytes and next cursor, then returns a new cursor. The future owner must call it
  only after successful inference/action admission/native interval staging. This
  pure function does not assert that a physics step occurred. Any earlier failure
  retains the old cursor; there is no default reset on restore or retry.

The network remains prospective: `9→32 tanh→32 tanh→2`. It supplies **both** velocity
and heading, with no analytic fallback, action substitution or clipping. The fixed
supervisor supplies phase memory; phase transitions are not learned. Outcome claims
must name this hybrid separation.

## Exact action arithmetic

`float(np.float32(.4))` is `.4000000059604645`, which the unchanged task guard
correctly rejects. Therefore float32 parameters, hidden values, logits and tanh
are followed by **float64 promotion before multiplication by float64 .4**.
`scale_action` accepts finite float32[2] normalized values in `[-1,1]` and returns
float64[2]. Saturated ±1 becomes exact Python ±.4. The actual future path is
`scale_action(...).tolist()` → existing owner finite/bound guard → upstream step
and unchanged float32 wheel converter → `puck_profile.advance` → float64 record.
Pure tests exercise that real converter/advance boundary, the rejected historical
float32 scaling, adjacent out-of-range values and retained signed zero.

Training must use the identical differentiable float64 promotion/scaling and
unchanged normalized MSE against the reader's preserved float64 teacher labels.
Parameter/optimizer tensors remain float32. This is a prospective numerical
clarification before any training, not a relaxation of historical task guards.

## Data admission and evidence limits

`admit_teacher_rows` reconstructs its cursor from reset, independent of all recorded
teacher modes. It requires exact sensor/ninth-input dtype, shape and bytes,
before/after teacher codes 1/2, own codes 0/1 and finite float64[2] labels within .4.
It never seeds its own cursor from a teacher field. A single discrepancy rejects
the fixed data batch; no row or layout is discarded or replaced.

`admit_record` reuses `iter_ticks`, bounded artifact reads/fingerprints and storage
inventory. It checks the pinned completed manifest, one initial episode/reset,
all mode/event/cursor fields, bounded chunks/ticks, recorded goal/dwell/contact
and terminal-stop coverage, and returns source/feature/target hashes. Each owner
directory is capped at 160 MiB, including any snapshots present. `admit_batch`
requires the exact 16 train plus 4 recorded-dev rows in frozen order, rejects
duplicate owners, checks the 4 GiB aggregate, and revalidates all source
fingerprints before returning arrays. A failed batch returns all 20 admission
statuses and **no training arrays**; source files are never rewritten.

These readers validate recorded data contracts. They do not independently prove
native contact, goal physics, faithful teacher execution or a valid initial native
snapshot. The future collector must retain those artifacts and its independent
audit must establish those separate facts. Fixtures are authored data, explicitly
not actual collection, native replay or model validation.

## Next source slices, each reviewed before execution

1. **Fixed teacher collection adapter implemented; native execution pending.**
   `collect_puck_teachers.py` invokes the existing mechanics owner/watchdog for
   exactly 6000–6019. Its explicit `learning_teacher` pin admits typed canonical
   plan rows only: one fresh episode, no restore/replay/source snapshot, reset
   override, alternate split or tick budget. Installation, authored reset, contact
   intervals, wheel conversion, recording and terminal cleanup are shared. Default
   mechanics row/application bytes and historical snapshot admission remain intact;
   Torch remains forbidden in these native teacher owners. The collection branch
   does not admit a student or runtime factory.

   `puck_teacher.decide` calls the privileged expert once, independently prepares
   the sensor-only cursor, and requires agreement before applying control. On
   disagreement, the result/event retains exact float32 sensor bytes, the original
   float64 expert action, both before/after modes and `executed_interval: false`.
   No mode/label is substituted. The own cursor commits only after a completed
   interval's numeric row and event are staged; if later recording fails, its old
   cursor remains and any returned native step/time is reported separately.

   The initial-only `puck-teacher-initial-v1` envelope binds learning/task/teacher/
   supervisor source hashes, declared feature ID, seed/split, profile/full model,
   world/contact/task state and both reset cursors. It has no checkpoint and is
   deliberately rejected by the mechanics restore path. Teacher capture alone
   does not qualify student native restore or replay. Every recorded task digest
   additionally binds the own after cursor; numeric/event modes remain explicit.

   The small stage loop retains all 20 planned statuses. Natural task outcomes
   complete the fixed plan; protocol/infrastructure error stops it with remaining
   rows unstarted. Only all 20 completed owners plus `admit_batch` and unchanged
   source/evidence/storage checks can publish `status: passed`. An unconditional
   final elapsed check includes data admission and finalization within 1500 s.
   The report's `sources` is exactly the ordered `{seed, split, path,
   manifest_sha256}` entry list; `source_hashes` is the separate code inventory.
   `learning_protocol_sha256` and `admission.status` bind the trainer handoff.
   Failed batches remain ineligible; there is no replacement or new manifest.

   Pure fixtures exercise the modified owner with fake native resources and real
   task/record functions, exact float32 threshold disagreement before any step,
   record-failure cursor preservation, completed natural failure, all-20 report
   flow and final-deadline rejection. They are not native evidence. Next gates are
   separate: first the unchanged ten-owner mechanics compatibility plan on this
   source, then (only after review) fixed teacher collection under retained
   TERM1560/+15 and bounded_process1580 with independent descendant containment.
   Both need fresh pinned controls, exclusive slot GO and independent audits.
2. **One bounded trainer and fixed research loader.** Reuse the existing record,
   storage, `bounded_process` and checkpoint admission patterns. One invocation
   trains one fixed seed; a retained ordered launcher admits seeds 21, 22, 23.
   Keep 30 epochs, Adam .001, batch 64, no weight decay, norm cap 1, one CPU thread,
   earliest recorded-dev minimum and all-three reporting. Preserve target dtype
   and exact source/feature/protocol/checkpoint hashes. A tiny opt-in CPU mechanism
   gate must check promotion, finite gradients, loading and deterministic reset
   before actual training approval. No production asset replacement or UI registry.
3. **Owned student runtime and native/replay mechanism gate.** A fixed manifest
   selects only one of the three CPU checkpoints. Snapshot application must bind
   task/learning hashes, actual supervisor source hash, existing normalization
   source hash, model/checkpoint identity, layout/split, completed tick and own
   cursor. Validate/stage all fields before native restore. Action replay uses
   recorded actions and independent cursor checks without teacher/model calls;
   policy replay invokes the model once on actual sensors and restored own cursor.
   Both retain exact before/after fields and application digest. The existing native
   capture/restore and action/policy parity helpers remain the basis, not a new
   serialization format or production Engine controller path.
4. **Frozen collection, training, dev and held-out stages.** Each needs source
   freeze, retained controls, independent audit and separate coordinator GO. No
   collection/training/held-out execution is authorized by this document.

| Stage | Fixed cases | Admission and unchanged external/storage bounds |
| --- | --- | --- |
| Teacher collection | 6000–6015 train; 6016–6019 recorded dev | All 20 goals; each train ≥32 ticks, ≥10 contact intervals, ≥10 final zero labels; 1500 s internal / TERM 1560 +15 / supervisor 1580; 4 GiB |
| Training | Seeds 21, 22, 23; 30 epochs each | Same data, all three models; per seed 120 s internal / TERM 180 +15 / supervisor 200; 16 MiB each, 64 MiB total |
| Closed-loop dev | 6100–6103 × all three models | Each model ≥3/4 goals; exact matched starts; 1200 s internal / TERM 1260 +15 / supervisor 1280; 3 GiB |
| Held-out, still closed | 6200–6207 × all three models | Only after exact passed dev receipt, audit and GO; every model ≥6/8; 1800 s internal / TERM 1860 +15 / supervisor 1880; 4 GiB |

Every episode remains ≤600 control ticks with natural termination, no automatic
reset/retry/replacement, and no winning-seed selection. Keep owner 180 s,
startup/progress 60/30 s, logs 1 MiB, report 4 MiB, snapshot 8 MiB, checkpoint
1 MiB / uncompressed parameter-container 2 MiB, 1 GiB free floor and 16 GiB aggregate retention.
Teacher owners retain two CPU threads; students/training use one. Resource limits
are frozen ceilings, not measured throughput or guarantees of admission success.
