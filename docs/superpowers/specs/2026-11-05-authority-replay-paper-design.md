# Authority-Aware Replay Paper Redesign

## Intent

Replace the current repository-status-style manuscript with a focused systems
paper that tests one falsifiable claim:

> Explicit authority and replay semantics detect silent evidence errors that
> explicit naive acceptance predicates accept, while preserving executable
> continuation and replay at measured cost.

The paper is about semantic reproducibility for interactive embodied-AI
experiments. It is not a controller-quality, biological-validity, provenance-
standard, deterministic-execution, or crash-consistency paper.

## Why the current draft fails

Three independent reviews converged on the same structural problems:

- the contribution list is a feature inventory rather than a falsifiable result;
- the evaluation does not exercise the motivating failures;
- there is no matched baseline, ablation, or cost decomposition;
- unrelated parity, cadence, endurance, memory, puck, and MaleCNS results form a
  repository ledger rather than one experiment;
- repeated caveats and artifact administration overwhelm the narrative.

Line editing is explicitly out of scope until the new empirical spine exists.

## Paper claim and narrative

Working title:

> **Who Changed the World? Authority-Aware Replay for Interactive Embodied-AI
> Experiments**

The opening incident is a displayed obstacle that is delayed or rejected while a
later visual playback appears to show a response. The retained trace must answer
two separate questions: whether the intervention became authoritative, and
whether the replay recomputed the policy.

The paper will define four category errors:

1. displayed is not applied;
2. pose is not resumable simulator/controller state;
3. playback, action replay, and policy replay are different computations;
4. an output path or completed process is not a supported scientific claim.

Three enforceable invariants organize the design:

- one owner mutates simulator/controller state and emits a terminal receipt for
  every accepted command;
- a resumable snapshot binds physics, controller, wrapper, random, pending-
  command, source, and asset state;
- every replay declares what it executes and validates, with new outputs never
  overwriting their source.

## Study boundaries

The study is local, CPU-only, fixed-seed, and bounded. It may use the existing
FLYNN assets from the main checkout read-only. It must not:

- train or tune models;
- open held-out data;
- run human, artistic, animal, or physical-hardware studies;
- claim CUDA continuation from CPU evidence;
- mutate historical reports, compact evidence, retained raw runs, or source
  assets;
- silently replace a failed repetition;
- describe staged no-overwrite publication as power-loss crash consistency;
- claim independent-machine reproduction from a fresh checkout on the same host.

Raw campaign outputs live under an ignored, campaign-specific run root. Compact
summaries, sanitized fault traces, the frozen protocol, source/config hashes,
commands, failures, and raw-tree inventories are committed. Every run is bound
to the clean campaign commit frozen after study implementation and before the
first result-producing run.

The local campaign is sequential. Its total wall-clock cap is four hours, each
unit has a 15-minute hard timeout, raw outputs may consume at most 8 GiB, each
ordinary unit may consume at most 512 MiB, the offline-checkout unit may consume
at most 2 GiB, and at least 6 GiB of filesystem free space must remain. Crossing
a cap stops new units and retains completed/failed rows; it never authorizes
deletion, replacement, or scope reduction.

## Experimental units and reporting

- A seeded source/restored pair is one continuation unit. Its ticks are repeated
  measurements, not independent samples.
- A seeded source trajectory is one replay unit. Playback, action replay, and
  policy replay are paired conditions on that trajectory.
- A `(fault, condition, repetition)` execution is one fault-matrix unit.
- A seeded matched invocation is one overhead unit.
- No significance test is required. Report exact denominators, paired raw values,
  median, range, and IQR where meaningful.
- Failures, refusals, timeouts, and incomplete runs remain in denominators and in
  the compact summary.

## Evaluation

### RQ1: Can the semantic contract detect silent evidence errors?

Freeze the following matrix. `runtime` cases traverse the actual CPU FLYNN/lab
path with pinned assets. `fixture` cases use production storage/custody
interfaces with deterministic small payloads. Runtime seeds are engineering
repetitions; deterministic fixture variants are distinct fault units.

| ID | Path and repetitions | Injection | Naive predicate or ablation | Expected semantic outcome |
|---|---|---|---|---|
| A1 | runtime, seeds 0--2 | delay an accepted intervention for two control boundaries while retaining the newest display frame | request accepted or obstacle visible means applied | receipt stays queued until one recorded applied tick; no pre-application world change |
| A2 | runtime, seeds 0--2 | submit a stale expected revision | request parsed means applied | rejected receipt; world and application revision unchanged |
| A3 | runtime, seeds 0--2 | repeat an accepted command ID | two accepted requests mean two applications | exactly one application and one authoritative tick |
| R1 | runtime, seeds 0--2 | label playback as policy replay | viewable matching trajectory means policy reproduced | reject because no policy invocation occurred |
| R2 | runtime, seeds 0--2 | label action replay as policy replay | matching trajectory or final state means policy reproduced | reject because the controller was bypassed |
| S1 | runtime, seeds 0--2 | restore pose/integration state but omit controller, RNG, and application state | qpos/qvel restore plus continued execution means continuation succeeded | pose-only ablation diverges or is inadmissible; full snapshot continues under the frozen comparison policy |
| S2 | runtime, seeds 0--2 | remove recurrent hidden/retinal state from a copied snapshot | readable snapshot and process progress mean continuation succeeded | refuse before destination mutation; source remains unchanged |
| D1 | runtime, seed 0, source/lock/hash variants | change one copied runtime source identity after the source run | initial setup succeeded, so replay may run | refuse before first replay step |
| D2 | runtime, seed 0, graph/checkpoint/mapping variants | substitute one copied asset | expected shapes or load success mean compatible | refuse before controller execution |
| C1 | fixture, one unit | same-byte replace a held file | start-time content hash still matches | detect protected identity drift and poison context |
| C2 | fixture, one unit | edit and restore held bytes | exit bytes match initial bytes | detect mutation at protected recheck |
| C3 | fixture, three sibling operations | create/remove unrelated siblings above custody root | no protected content changed | no false rejection |
| P1 | fixture subprocess, three kill points | die before chunk rename, after rename/before event, and before terminal manifest | output path exists or some bytes parse means publication succeeded | no false terminal success; validated prefix retained; unpublished tail ignored |
| B1 | runtime, seeds 0--2 | mutate branch A after a common snapshot while observing parent and branch B | sequential pose copies are independent | separate-owner branches leave parent/sibling digests unchanged |
| B2 | runtime, seeds 0--2 | shared-owner pose-copy ablation | reset plus pose copy is an independent branch | expose contamination through digest or continuation mismatch |
| E1 | fixture, three payload bounds | quota one byte below required publication | write attempted or prefix exists means run succeeded | refuse or fail terminally; retain valid prefix; write no bytes beyond cap |
| E2 | fixture, three queue bounds | fill bounded background queue | producer return means data retained | record bounded backpressure; silently drop no accepted item |
| E3 | fixture, write/flush/fsync variants | inject a writer failure | process continuation or output existence means success | terminal writer error; no retry; valid prefix and resource release |

All copied sources/assets live under the campaign root; retained originals are
read-only and their before/after hashes are checked. Runtime cases A1--A3,
R1--R2, S1--S2, D1--D2, and B1--B2 must not be replaced by unit-test-only
fixtures.

The comparison is explicitly named a **naive acceptance predicate or ablation**,
not a competing harness or claim about existing tools. It is computed from the
same trace:

- request acceptance means the intervention succeeded;
- viewable trajectory/final state means replay succeeded;
- qpos/qvel restoration plus continued execution means continuation succeeded;
- initial-open hash agreement means provenance remained valid;
- output-path existence means publication succeeded;
- clean process exit plus parseable final JSON means the experiment succeeded.

Four narrow executable ablations supplement that common predicate where needed:

- pose-only snapshot;
- start-only hashing without exit recheck;
- direct append/overwrite writer;
- shared-owner branch execution or unbounded resource guard.

Primary outcomes are silent acceptance, explicit detection/refusal, correct
recovery, and false rejection of a benign control. This is not a comparison to a
named competing system.

### RQ2: Does full continuation/replay preserve the declared execution?

- Continuation: seeds 0--9, CPU FLYNN, prefix 8, continuation 100, one fresh
  source/restored pair per seed.
- Full replay: seeds 0--4, one source trajectory per seed, fixed prefix 8 and 100
  source ticks, followed by branch, playback, action replay, and policy replay.
- Compare integer, Boolean, identity, shape, and event fields exactly. Compare
  float32 physics/controller arrays with `atol=1e-6`, `rtol=1e-6`, and finite
  scientific arrays only. Reject any NaN or infinity explicitly; matching NaN
  positions are not accepted. Compare source/asset identities exactly and report the first
  divergent field/tick. This policy is CPU/same-version/same-architecture only
  and may not change after the campaign commit.

Historical R0--M5 results remain context only. Missing old raw bundles are not
presented as newly recomputed evidence.

### RQ3: What does the semantic layer cost?

Split overhead into two experiments. For execution overhead, seeds 0--9 use
matched actions and final-state checks across:

1. benchmark-only null writer;
2. synchronous `RunWriter`;
3. background `RunWriter`;
4. background writer plus actual bounded storage accounting.

Each condition runs in a fresh process for 20 unmeasured warm-up ticks and 200
measured ticks. Model/environment open time is recorded separately and excluded
from the primary steady-state wall/tick result. Condition order uses the four
cyclic Latin-square rotations selected by `seed mod 4`. No OS page-cache flush is
performed, so results are warm-cache and same-host. Record condition ordinal,
load averages, available memory, CPU model/governor when readable, and competing
Palimpsest processes. Retain a seed only when actions, tick count, and final-state
digest match across all four conditions. The execution-overhead match digest
excludes recorder source-run/event-prefix identity and only MuJoCo
`timer.duration` elapsed wall-clock telemetry. Canonicalize those durations to
zero on a private decoded native-data copy and recompute its native hash; never
modify the live engine or retained source snapshot. All seeded RNG, integration,
controller, observation, application, physics, solver and other serialized cache
fields remain in the match. Retain the original full snapshot, canonicalized
snapshot, raw and matched native/final-state hashes, and explicit normalization
descriptor. This telemetry exclusion applies only to execution-overhead matching;
it does not change snapshot restore or replay validation.

Record wall time, wall time per tick, existing policy/physics/camera timing,
bytes per tick, peak RSS, descriptors/threads where available, writer
backpressure, and storage recount work. Record close time separately from
steady-state wall/tick, alongside open time.

Operation cost is separate: for replay seeds 0--4, use the retained full
background-writer-plus-storage source from RQ2 and record capture, save, read,
restore/first-tick, playback, action-replay, and policy-replay times. Null-writer
and other execution-overhead conditions do not produce replay timings. The null
writer is an overhead ablation, not a reproducibility baseline or competing
system. The paper claims **measured cost**, not acceptable, low, or bounded
overhead; no pass threshold is preregistered.

### RQ4: Can a fresh local checkout reproduce the focused workflow?

Run the existing offline fresh-checkout verifier once at the frozen commit with
the full FLYNN path. Label it same-host clean-checkout evidence. A true second
machine/operator reproduction remains an explicit submission gate unless an
external machine becomes available.

## Study implementation

Study-specific code lives under `paper/studies/authority_replay_v1/` and imports
production interfaces rather than weakening them. It contains:

- a frozen JSON protocol;
- a deterministic fault-matrix driver;
- repeatability/replay and overhead drivers or thin wrappers around existing
  verifiers;
- a pure analysis step that validates completeness and produces compact JSON,
  CSV, and LaTeX inputs;
- focused tests for protocol validation, denominators, failure retention,
  baseline predicates, and deterministic analysis.

All driver commands expose output roots and refuse non-empty destinations.
Drivers record environment, Git, asset, protocol, and command identities before
starting. The analysis refuses missing rows, duplicate units, undeclared retries,
hash drift, non-finite values, or outputs from another commit/protocol.

## Manuscript redesign

Target a venue-neutral 7--9 page paper with this order:

1. Introduction: one misleading run, one thesis, three contributions.
2. Failure model and semantic contract.
3. Design and implementation.
4. Evaluation organized by RQ1--RQ4.
5. Related work.
6. Limitations, lessons, and conclusion.

Replace the categorical results bars and linear evidence ladder with:

- an authority-transition sequence diagram;
- a replay-semantics execution/validation matrix;
- a fault-detection matrix;
- an overhead or continuation plot only if supported by the frozen results.

Keep one FLYNN case study. Move memory, puck, and MaleCNS results to a short
failure-preservation paragraph or appendix. Move claim-ledger schema, quota
details, licensing administration, and full artifact status out of the main
narrative unless required to interpret a result.

## Related-work boundary

The paper will compare layers and semantics, not claim universal superiority.
Primary comparators include rosbag2, Gazebo logging, CARLA Recorder, MuJoCo state
and reproducibility, rr, DMTCP, ReproZip, noWorkflow/ProvDB, W3C PROV/RO-Crate,
and application/file-system crash-consistency work. A dash in the comparison
table means “not specified by the cited primary source,” not “cannot do.”

Palimpsest's claimed niche is the domain-semantic contract joining interactive
authority, continuation state, and declared replay computation.

## Completion criteria

The rewrite is complete only when:

- the protocol was committed before campaign execution;
- all planned local units either completed or remain explicitly failed in the
  declared denominator;
- raw outputs and compact summaries have verified hashes and exact provenance;
- analysis and paper tests pass from a clean tree;
- the PDF is rebuilt, text/log checked, and every page visually inspected;
- a fresh independent reviewer finds no critical evidence/claim mismatch;
- remaining external gates, especially second-machine reproduction, venue,
  authorship, licensing, and archive decisions, are explicit.
