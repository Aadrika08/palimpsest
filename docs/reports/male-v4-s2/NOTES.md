# MaleCNS v4 S2: the episode-runner blocker (design note, no code)

> **Status:** design note only. No code, no execution. It lists what a later milestone must port
> and flags the `engine.py` change as **needing independent review**.

## What exists

`scripts/evaluate_male_navigation_v4.py` already holds the S2/S3 gates: scene IDs 3160..3163 (24
owners) and 3170..3177 (48), the 3/4 and 6/8 per-augmented-seed thresholds, per-scene six-owner
initial matching, disjointness and the held-out admission. Its header states that **the native
owner (an Engine episode of a v4 checkpoint) is deliberately not bound there**. This note covers
that missing owner.

## The blocker

1. **Engine admits research bindings only by exact type** (`src/palimpsest/engine.py`, about lines
   438-454): `type(research_binding) is Binding`, `RecoveryBinding`, `RecoveryHeldoutBinding` or
   `NavigationBinding` (`male_navigation_research.Binding`); otherwise
   `ValueError('unsupported trusted research binding')`. A subclass or a new class is refused.
2. **`NavigationBinding` is hard-wired to v2** (`src/palimpsest/male_navigation_research.py`):
   `INDEX_PATH = data/manifests/male-navigation-research-development-v2.json`, `INDEX_SHA256 =
   f938d979…`, `PROTOCOL_SHA256 = 76a502de…`, `PAIR_SEEDS = (10, 11, 12)`, and train rows 2117 /
   7197 in `_history` and `_admit`. `resolve` goes through the v2 index (`_index`, `_gate`,
   `_admit`) and `load_policy`.
3. The v4 S1 output (six terminal checkpoints, seed × {old-corpus, augmented}, plus
   `report.json` and `publication.json`) is not an index of that shape, and the v4 protocol
   sha256 is `cd4eb130…`, not the v2 one.

## Needed (two pieces, a later milestone)

- **`NavigationBindingV4`** (new class in a new module, e.g. `male_navigation_v4_research.py`):
  the v4 index of the six terminal checkpoints (path and sha256 of S1's `report.json`,
  `publication.json` and each `seed-N-arm.pt`), the v4 protocol sha256, `PAIR_SEEDS`, train rows
  from the S0z corpus pin (2,117 old / 7,197 augmented), the same `resolve`/`load_policy`/
  `provenance` surface as v2's `Binding`, and an admission gate that re-verifies S1's publication
  (`success_admitted`) before any checkpoint loads.
- **A one-line type allow-list entry in `engine.py`:** import the new `Binding` and add
  `admitted = type(research_binding) is NavigationV4Binding` next to the v2 entry, keeping the
  "fresh roots only" restriction (`restore_snapshot`, `replace_controller`, `memory_u` refused).
  **This edit to the shared Engine needs independent review**: it widens the set of types allowed
  to substitute a policy, and it changes a file every stage imports.

## What v2's owner worker does (`scripts/evaluate_male_navigation_v2.py`), to port

The v2 `verify` + `worker` pair is the template. A v4 port changes the binding, the scene IDs
(3160..3163), the case table (seed × arm × scene, 24 owners) and the pins, and nothing else.

- **Per-owner process:** `bounded_process([python, <script>, '--worker', <json>], …)` with env
  `PYTHONPATH=src`, `MUJOCO_GL=egl`, `OMP_NUM_THREADS=1`, `CUDA_VISIBLE_DEVICES=''`; a **180 s
  per-owner cap** (`min(180, deadline − now)`), a **1,800 s stage deadline** and 1 MiB log caps.
  The unit's RuntimeMaxSec (4,430 s in the protocol) encloses it.
- **Worker admission:** `check_case`, `check_pins(root, source_pins)`; CUDA hidden; Torch intra- and
  inter-op threads 1; MuJoCo 3.3.6 with `get_mjcb_control() is None`; runtime identity recorded.
- **`Engine.open(root, assets, run/'recording', controller='male-original', device='cpu',
  seed=<scene_seed>, scenario='reproduction', texture='checker', run_id=run.name,
  max_bytes=144 MiB, storage_budget=budget, research_binding=<Binding(index, sha, training_seed,
  arm)>, expected_policy_identity=<identity>)`**, then the fresh-boundary checks (tick 0, no
  teacher, zero velocity/control/time, eyes unmasked, `max_steps 600`, `n_obstacles 20`,
  `_action_scale 2`, `end_on_collision False`), `numeric_admission` and `validate_world`.
- **Contact probe and ownership:** `ContactProbe(mujoco, engine.env)` and
  `contacts.compiled_ownership(mujoco, model, _model_digest(model))`, compared with the probe's
  ownership (base body, robot bodies, geometries) before the first action; `probe.install()` only
  after all scientific-initial checks.
- **Initial binding:** `_register_initial`, `initial_ready` (SNP ≤ 16 MiB), `initial_contact_binding`,
  `initial_match` (scientific initial equal across the six owners of a scene) and
  `initial_admission` (disjointness against earlier scenes and the prior corpus).
- **Episode:** `run_episode` defers `writer.tick`, wraps `policy.act` to count exactly one policy
  prediction per interval, forbids teacher access, steps up to 600 intervals and binds each
  interval (`bind_interval`) to contact incidence; the outcome is read from the natural boundary only.
- **Caps and publication:** recording ≤ 144 MiB and recording + snapshot ≤ 160 MiB per owner,
  aggregate StorageBudget 4 GiB (`max_runs 24`, `max_snapshots 1`), the result published through
  `common.publish` with a source-pin recheck last. A wall-clock kill or timeout is an
  operational failure (never a non-goal) and stops the stage.
- **Reduction:** `reduce_results`; only augmented seeds gate, and any non-normal owner means not
  admitted (already in `evaluate_male_navigation_v4.reduce`).

## Cost and review flags

S2 is the largest stage (worst case 4,435 CPU-s). The port is mostly mechanical, but two pieces
are new trust boundaries, each needing independent review before an owner GO: the `engine.py`
allow-list entry and `NavigationBindingV4`'s admission of the S1 publication. The v4 Stage P probe
covers `evaluate_male_navigation_v4.py` but not the new binding module, so P coverage of the binding
is a precondition for S2.

## Amendment 2 implementation notes (branch `impl/male-v4-a2`; no stage run)

**Resolved open item (identity payload and derivations).** `male_policy.validate_identity` accepts exactly
`{controller: 'male-original', variant: 'original', profile: male_policy.PROFILE, <the 11 IDENTITY_HASHES>}`,
all lowercase 64-hex. `NavigationBindingV4` builds it from evidence S1 already published, with no new
derivation of anything S1 did not write:

| field | source |
|---|---|
| `checkpoint_sha256` | hard-coded per `(seed, arm)`; equals `checkpoints.sha256` (a test compares all six) |
| `protocol_sha256` | digest of S1's `run_protocol` (= `report.run_protocol_sha256`, sha of `protocol.json` `3769df74...`), the lineage each checkpoint carries; the base sha `cd4eb130...` is checked separately against the receipt and report |
| `model_manifest_sha256`, `training_report_sha256` | S1 `report.json` sha `6ca8af5f...` (there is no separate model index file; the report is both) |
| `graph_sha256` | `male_model.digest(graph)` of the pinned reduced graph (what S1 wrote into every checkpoint) |
| `ordered_ids_sha256`, `topology_sha256`, `source_graph_sha256`, `graph_manifest_sha256` | fields of the loaded pinned graph (`source-graph.json`, input shas pinned from S1's `protocol.json` `model_inputs`) |
| `feature_protocol_sha256` | `male_model.digest(male_model.FEATURE_PROTOCOL)` |
| `cell_source_sha256` | `male_model.CELL_SHA256` (the pinned upstream cell) |

The S1 report does not list `graph_sha256` or `ordered_ids_sha256`; both are re-derived from the pinned graph and
then enforced by `male_policy._load_checked_policy`, which requires the five-key checkpoint
(`format, protocol_sha256, graph_sha256, ordered_ids_sha256, state_dict`) and lineage equal to the provenance.
Checkpoint internals are only readable after `torch.load(weights_only=True)`, so `resolve` verifies payload sha256 and
archive safety (`_check_archive`) and `load_policy` enforces the five keys and lineage; nothing is unpickled before the
sha matches.

**No separate index builder.** A2 allows either a published index or a binding that reads S1 `report.json` and
`publication.json` directly against hard-coded shas; the second is implemented (constants: report `6ca8af5f...`,
publication `fb6f1f38...`, six checkpoint shas, S1 output root). `Binding(training_seed, arm)` takes nothing else.
Stage P3 therefore probes the binding module and the evaluator (also entry `S2-owner-worker`): `P3_ENTRIES` in the
probe. P3 has not been run.

**Owner worker** (`scripts/evaluate_male_navigation_v4.py`): port of v2's worker and `verify` with the A2 changes only.
The S2 GO must name the base sha and `amendment_2_sha256` (`c4cd3a50...`); the file sha is also pinned in every
owner's source pins. `native_owner` stays refused when called directly; owners run only through `run_development`
(GO, S1 admission, `inside_research_stage`). Output, S1 output, assets and corpus pin are absolute paths; the output
must not overlap S1 evidence, assets or the tree. Report publication rechecks source pins last.
