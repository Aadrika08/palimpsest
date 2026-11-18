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
