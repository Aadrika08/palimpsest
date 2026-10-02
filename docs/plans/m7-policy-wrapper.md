# M7 separate male policy wrapper

The wrapper loads a completed offline training artifact. The initial lab slice
adds two fixed CPU controllers and explicit identity/native-state handling.
Pure fixture checks cover admission, propagation and rejection. Actual native
continuation, replay and UI validation remain pending their runtime gates.

`palimpsest.male_policy.load_policy` requires explicit arguments:

- `directory`: completed training output containing `report.json`, `protocol.json`,
  both `original`/`degree_rewired` graph JSON files and checkpoints.
- `variant`: exactly `original` or `degree_rewired`.
- `expected_report_sha256`: caller-retained identity of the completed report.
- `graph_path`, `graph_manifest`, `cell_path`: pinned anatomical extraction,
  extraction manifest, and pinned upstream cell source.
- `device='cpu'`, bounded integer `seed`: no device fallback.

The caller must retain the expected report hash independently of its directory
lookup. The loader validates the complete five-file ledger, completed paired
training status, exact frozen training/feature protocol, collection digest,
graph topology, ordered neuron IDs, type missingness and deterministic rewiring.
Each file is capped at 8 MiB; six fixed files bound retained artifact input to
48 MiB. Symlinks, unexpected ledger paths, duplicate entries and changed files
are rejected. Teacher recordings are not reopened: provenance binds their
retained training collection manifest rather than asserting they remain present.

Before Torch import, checkpoint ZIP members must be uncompressed, unique,
unencrypted, at most 128 entries and at most 8 MiB in total expanded size. Legacy
pickle checkpoints and compressed archives are rejected. Checkpoint bytes are
loaded with `weights_only=True` on CPU. Every state tensor
must have the reconstructed name, shape, dtype, layout and finite values. All
graph buffers **and fixed `cell.W_values`** must equal the independently rebuilt
graph. The selected checkpoint is then frozen in evaluation mode. Provenance
keeps separate training and serving source hashes, plus report/checkpoint/
protocol/graph/ordered-ID/feature/cell identities and the authored-interface limit.
Hashes bind retained artifacts; they are not an external attestation of training.

`MalePolicy` exposes `agent=model`, `hidden`, `torch`, `device`, `dtype`,
`provenance`, `failure_diagnostics`, `reset()` and `act(observation)`. Only two
128x128 uint8 RGB eyes and collision/contact-angle/relative-bearing sensors feed
the unchanged 388-feature protocol. Extra fields never enter inference. An absent
contact angle (`None`) means zero, as in the recorder. Bearing must be finite and
unit length. Each call runs exactly one timestep and returns independent finite
float32 `action[2]`, `encoded_input[136]`, and `raw_output[2]` arrays for the actual
138-node graph. Actions retain velocity `3*tanh(raw[0])` and relative heading
`pi*tanh(raw[1])`. Diagnostics come from the same invocation. Hidden state commits
only after feature, raw-output, shape, dtype and action checks succeed.

The optional `male_model.forward(..., diagnostics=True)` return exposes already
computed encoder/raw tensors. Its default two-value return and training path are
unchanged. The frozen training worktree and output files are not modified.

Pure checks:

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest test_male_policy test_male_model -v
```

The synthetic CPU loader/state/rollback check is skipped unless
`PALIMPSEST_MALE_TORCH_CHECKS=1` is explicitly authorized. That check and loading
both actual checkpoints passed at `4941468`, including all 600 held-out recorded
inputs per variant compared against frozen 32-tick-window evaluation. See the
[validation report](../reports/m7-wrapper-validation.md) for exact scope and
hashes. Engine integration and closed-loop/native continuation remain separate
unexecuted gates. Fixture checks and single-seed imitation metrics establish
neither topology benefit nor biological sensing or navigation competence.

## Initial lab integration, awaiting actual gate

Two explicit controller IDs, `male-original` and `male-control`, map only
to `original` and `degree_rewired`. Admit CPU, reproduction and checker initially;
other scenarios/devices fail explicitly. The existing API request schema keeps
only scenario/texture/controller/device/seed, with no user-provided model paths.

Retained artifacts use the fixed `asset_root/male-reduced-v1/` subdirectory.
`data/manifests/male-reduced-policy-v1.json` pins the completed report
hash, the fixed artifact names/hashes and source-graph hash. Keep the existing
tracked extraction manifest and pinned upstream cell source. A small helper in
`male_policy.py` resolves these fixed names and calls the validated loader; no
general registry or fetching subsystem is required.

Retain a server-derived `policy_identity` in the run manifest and native snapshot
configuration: controller/variant, model-manifest hash, report/checkpoint/protocol/
graph/topology/ordered-ID/feature/cell hashes. Full loader provenance is recorded in
`policy_loaded`. The worker passes an expected identity internally to Engine;
fresh starts bind current pinned identity, same-controller branches and replay
require the recorded identity before restore. Changing `male-original` to
`male-control` is an explicit controller replacement with fresh hidden state and
the existing replacement event; it must not reuse the source model identity.

The explicit male snapshot policy state contains `kind`, finite float32
`hidden[1,138]`, and bounded failure diagnostics. Keep existing FLYNN snapshots
compatible. Stage and validate male state before native mutation, preserve the
full policy/runtime identity comparison, and invalidate cell caches on restore.
Do not add retina attributes or invent visual populations. Existing
`agent=model` supports tensor hashing and the current 136+2 neural-byte estimate.

Engine has two policy creation/reset/action branches and a male population
guard. Profiles/Lab have fixed choices and verified availability. Worker and
replay snapshot registration retain `policy_identity`; replay marks male
policy inference correctly and include male source files in its relevant runtime
hash checks for male replays only. Policy/action replay keeps its existing labels.
Actual snapshot continuation and replay must pass a separately bounded runtime
gate before claiming this integration works.

Stage exactly seven files, without changing the frozen training outputs:
`report.json`, `protocol.json`, `original-graph.json`, `original.pt`,
`degree_rewired-graph.json`, `degree_rewired.pt`, and `source-graph.json` (the
unchanged 101,560-byte raw extraction graph). The tracked extraction manifest
stays at `data/manifests/malecns-reduced-neighborhood-v1.json`; the cell source uses
the normal pinned `repo_root/upstream/fly-gym/models/connectome_rnn_model.py`.
The resolver verifies every fixed file's hash and size. No downloads or data
copies happen in controller admission. This worktree's upstream submodule must
be populated before actual runtime validation.

Pure checks, with Torch/native/build work gated off:

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest test_male_lab test_male_policy test_male_model test_male_runtime test_engine test_profiles test_worker test_replay -q
```

After review, source freeze, pinned asset staging and explicit runtime release,
the proposed retained CPU/EGL gate is:

```sh
timeout --signal=KILL 180s env PALIMPSEST_MALE_RUNTIME_TESTS=1 \
  PALIMPSEST_TEST_ASSETS="$PWD/data/assets/flynn" \
  PALIMPSEST_MALE_RUNTIME_OUTPUT="$PWD/runs/m7-male-lab-gate-v1" \
  PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest test_male_runtime -v
```

The test exclusively creates its output directory. It retains source hashes and
all UUID runs; each source executes three control ticks. Both controllers undergo
two-tick native continuation, invalid state/identity rejection before mutation,
action replay and policy replay, followed by explicit original-to-control
replacement. It does not score navigation or tune/select models. A live Lab owner
and browser/build check remain separate gates; pure API fixtures use a mocked
supervisor and acquire no runtime/storage-owner slot.
