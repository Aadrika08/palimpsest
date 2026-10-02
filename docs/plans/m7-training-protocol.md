# M7 initial male-reduced training protocol

Frozen before teacher collection or model execution. This prepares a separately
trained **male-reduced model with an artificial boundary interface**, not a biological
sensor mapping, intact male nervous system, female-checkpoint transfer, topology
benefit result, or runtime-integrated R3 profile. The frozen first pilot has now completed its actual CPU mechanism check, 16-scene teacher collection and paired training/recorded-input held-out evaluation. See the [measured pilot](../reports/m7-training-pilot.md). Runtime-integrated closed-loop qualification remains open.

## Frozen first pilot

| Item | Fixed choice |
| --- | --- |
| Train scene seeds | 100–107, independent root teacher run per seed |
| Dev scene seeds | 108–111, independent root teacher run per seed |
| Held-out scene seeds | 112–115, independent root teacher run per seed |
| Collection | Existing LabSupervisor/worker, teacher controller, reproduction scenario, checker texture, one fresh episode per root run |
| Duration | At most 150 control ticks at 0.02 s/tick; stop at the first natural terminal state or the cap |
| Short episodes | Retain actual goal/stall/contact/time outcomes; never pad, reset, replace a failing scene, or recollect based on held-out results |
| Minimum | Each training run needs at least 32 usable ticks; otherwise fail the whole frozen pilot as insufficient data. Dev/held-out need at least one valid tick |
| Collection storage | 32 MiB per recording plus initial snapshots; 1 GiB aggregate. Preflight and exhaustion failures remain failures, not shortened substitute scenes |
| Variants | Extracted topology and one degree-preserving rewired topology |
| Training/control seed | 0 for initialization and 0 for rewiring; same initialization and budgets for the paired variants |
| Training | Five epochs, 32-tick windows, Adam learning rate 0.001, gradient norm capped at 1.0 |
| Selection | Lowest dev loss across all five epochs; first epoch wins an exact tie. No early stopping or held-out selection |
| Held-out | Evaluate once only after both dev-selected checkpoint files are written |
| Runtime | CPU float32, one Torch thread, deterministic algorithms, pinned Torch 2.9.0 and NumPy 2.2.5 |
| Output/time | Exclusive new output directory; 64 MiB artifact cap, 8 MiB per file; 600-second wall budget checked at each sequence window |

The Python constant `INITIAL_PROTOCOL` in `scripts/train_male_reduced.py` is the
machine-readable source of these choices. Its containing frozen protocol and source
hashes are written before training. Changing this protocol creates a different pilot;
do not change it in response to held-out outcomes. The per-window wall check is not
a process-group watchdog; an external bounded owner is still required for an actual
supervised pilot if native execution stalls.

## Teacher recording and collection manifest contract

Use existing UUID-named R1 lab runs, not legacy `evaluate` output. Each source must
be completed and integrity-valid under `artifacts._load` / `records.iter_ticks`, with
`controller=teacher`, `profile=teacher`, `teacher_privileged=true`, no parent/replay,
controller replacement, or memory-supervisor history. No obstacle/goal edits or
eye-mask interventions are allowed; recorded eye flags, when present, must show both
channels enabled. The manifest seed and episode-0 start-event seed must agree.
Each frozen source has exactly one episode numbered 0,
contiguous ticks starting at zero, and matching post-step simulation times. A run that
ends before 150 ticks needs a recorded natural terminal phase and outcome. An operator
abort or recorder failure is not silently reclassified as a short successful episode.

Required recording declarations:

- `observation_profile`: `two-rgb-eyes-contact-relative-goal-bearing-v1`.
- `sensor_order`: `collision`, `collision_angle`, `wind_cos`, `wind_sin`.
- `control_interval_seconds`: `0.02`.
- `cam_left` and `cam_right`: actual used 128 × 128 × 3 uint8 RGB observations.
- `sensors`: four finite values in the declared order; contact 0/1, angle in radians,
  unit-length relative-goal-bearing cosine/sine. No world coordinates or privileged
  teacher fields enter the learned encoder.
- `action`: the finite teacher action paired with those pre-step inputs, containing
  velocity scalar in ±3 and relative heading in ±π radians. `control`/motor commands
  are not substituted as labels. Poses, rewards, future observations and outcomes
  remain recording/evaluation data, not feature inputs.

The privileged teacher is permitted to use simulator information to produce
demonstrations. This is teacher imitation with a restricted student input boundary;
it does not claim the teacher is sensor-only.

The collector should retain a small `collection.json` with `version: 1` and a `runs`
list. Each entry records `split` (`train`, `dev`, `held_out`), `seed`, absolute
`run_path`, `run_id`, actual `recorded_ticks`, `final_phase`, `last_outcome`, and
`recording_and_snapshot_bytes`, with a collection-level status. These are copied
from completed authoritative records, not promises made at job submission. Keep
failed/missing/insufficient scenes visible in that manifest. Do not create a second
collector abstraction; the existing runtime owner supplies these records.

The trainer independently derives its own `protocol.json.collection` manifest from
the listed runs. It includes every recording file's size/hash, aggregate recording
hash, episode seed/count, feature-and-target hash, final phase/outcome, counted snapshot
inventory, and local validation fingerprints. Snapshots are counted for the storage
bound and fingerprinted; their payload is not used as a model input or independently
restored. Duplicate UUIDs, cross-split scene-seed reuse, branches/replays, and identical
feature/target episodes across splits are rejected. Every source is rechecked after
all feature preparation and before checkpoint/final-report publication.

## Model and matched topology control

The pinned graph is `male-cns:v1.0`'s extracted 138-node, 1,647-edge neighborhood,
raw graph SHA-256 `5aba0fef99afba666b88e40fc535091454e46d9330580d9280b203e8da0abac0`.
Ordered IDs, extraction manifest/protocol hashes, type labels and missing-type IDs,
cut-boundary information, source licence and attribution remain in each model graph
artifact. Missing type annotations use an explicit unknown bucket; the acquired graph
currently has 59 recorded type labels and zero missing labels. Neurotransmitter signs
were not acquired. Positive connection counts are not physiological signed weights.

All 136 selected non-output boundary IDs receive the authored learned encoder.
They are input locations in this reduced computational model, not anatomically
validated visual/contact/goal neurons. Each eye is reduced by nonoverlapping 16 × 16
block means to 8 × 8 RGB, divided by 255, then flattened left-first. Append contact,
contact-angle/π, and goal-bearing cosine/sine: 388 features in total. One learned
`Linear(388, 136)` plus tanh projects them onto the declared node order. There is no
female retina, female neuron mapping, pretrained female weight, hidden pose/goal
coordinate input, or language model.

Load only the pinned upstream `LeakyConnectomeRNNCell` source file, SHA-256
`707cba79e7bf92923618ccc596e3d7a2d779edc02a970b0949f6dd3c0d28ae80`, from the read-only
upstream checkout. Its sparse recurrent orientation is **W[post, pre]**. Retain its
readout from endpoint IDs 12781 and 556329; these two model endpoints do not imply
biological output laterality. Outputs use `3*tanh(raw_velocity)` and
`π*tanh(raw_heading)`, with finite checks on inputs, encoding, hidden state, raw
readout and final action before returning any action. Train the new encoder, readout,
bias and recorded-type leak logits; hold anatomical edge weights fixed.

Normalize original counts by one shared scalar, `0.9 / max(original incoming weight
sum)`, and reuse that scalar for the rewired graph. The directed control performs
exactly ten successful destination swaps per edge, with at most 200 attempts per
edge. It retains node count, edge count, each node's in/out degree, weight multiset,
input/output IDs, types and training budget; duplicate edges and self-loops are
rejected. Weighted incoming strength and biological circuit organization are not
preserved. Record directed reachability for both variants without screening/retrying
controls for a desired reachability or outcome. Paths alone do not establish a
biological interface or task capability.

Reset recurrent state only at episode starts; carry it across windows and detach at
training window boundaries for truncated backpropagation. Minimize mean
`0.5*((velocity_error/3)^2 + 1-cos(heading_error))`; report velocity MAE and wrapped
heading MAE as well. Both variants see the same frozen run/episode/tick order. Dev
selects a checkpoint; held-out labels never affect fitting or selection. Reading
held-out records for structural validation/feature preparation is not permission to
inspect outcomes and tune the protocol.

## Deferred commands and acceptance

NumPy/stdlib checks, currently allowed:

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest test_male_model test_malecns_pilot -v
```

Ordinary graph validation, directed weight orientation, type missingness, and
degree-control checks use an authored eight-node fixture. A separate pinned
138-node asset check skips explicitly when the ignored fetched graph is absent;
clean CI does not require downloaded anatomical data. The opt-in CPU check also
requires the fetched graph and pinned upstream cell source.

After the runtime window is explicitly released, first run the queued CPU mechanism
check (no simulator). It is skipped unless explicitly enabled:

```sh
PALIMPSEST_MALE_TORCH_CHECKS=1 PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest test_male_model -v
```

After the existing owner has collected all frozen teacher scenes, this command builds
arguments from the retained collection manifest without inventing UUIDs:

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python - runs/m7-teacher-collection/collection.json --prepare-only <<'PY'
import json, subprocess, sys
from pathlib import Path
collection = json.loads(Path(sys.argv[1]).read_text())
flags = {'train': '--train', 'dev': '--dev', 'held_out': '--held-out'}
args = [sys.executable, 'scripts/train_male_reduced.py', '--cell-source',
        '../memory-mechanics/upstream/fly-gym/models/connectome_rnn_model.py']
for run in sorted(collection['runs'], key=lambda row: row['seed']):
    args += [flags[run['split']], run['run_path']]
subprocess.run(args + sys.argv[2:], check=True)
PY
```

Once that preparation succeeds, repeat the command replacing `--prepare-only` with
`--output runs/m7-male-training-pilot-v1`. Actual training takes the existing per-user
storage lease and refuses an existing output directory. Successful output includes
the complete protocol/collection and source hashes, both graph artifacts, fresh
checkpoint state dictionaries with ordered-ID/protocol/graph identities, checkpoint
file hashes, every epoch's train/dev losses, selected epochs, and final held-out
metrics. Failure remains explicit; a directory without a completed report is not a
trained-profile release. The first frozen execution completed; its measured results and file hashes are linked above. Repeating this command is a new execution, not an extension of the original held-out evaluation.

This first single-seed paired pilot can establish code/data compatibility and bounded
recorded-input imitation results. It cannot establish a topology advantage, navigation
success, robustness, biological sensor mapping, or R3 completion. Multiple training
and rewiring seeds with matched budgets, a frozen outcome analysis, and separately
qualified closed-loop runs are later gates, not implied by a successful checkpoint.
