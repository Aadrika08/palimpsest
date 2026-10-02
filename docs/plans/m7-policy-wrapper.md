# M7 separate male policy wrapper

This bounded slice loads a completed offline training artifact. It does not add an
Engine controller, API choice, snapshot format, replay path, retina state, or
population mapping. Those require a separately reviewed integration gate.

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

## Proposed integration contract, not implemented

Use two explicit controller IDs, `male-original` and `male-control`, mapping only
to `original` and `degree_rewired`. Admit CPU, reproduction and checker initially;
other scenarios/devices fail explicitly. The existing API request schema keeps
only scenario/texture/controller/device/seed, with no user-provided model paths.

Place retained artifacts in the fixed `asset_root/male-reduced-v1/` subdirectory.
A tracked `data/manifests/male-reduced-policy-v1.json` pins the completed report
hash, the fixed artifact names/hashes and source-graph hash. Keep the existing
tracked extraction manifest and pinned upstream cell source. A small helper in
`male_policy.py` resolves these fixed names and calls the validated loader; no
general registry or fetching subsystem is required.

Retain a server-derived `policy_identity` in the run manifest and native snapshot
configuration: controller/variant, model-manifest hash, report/checkpoint/protocol/
graph/topology/ordered-ID/feature/cell hashes. Record full loader provenance in
`policy_loaded`. The worker passes an expected identity internally to Engine;
fresh starts bind current pinned identity, same-controller branches and replay
require the recorded identity before restore. Changing `male-original` to
`male-control` is an explicit controller replacement with fresh hidden state and
the existing replacement event; it must not reuse the source model identity.

Add an explicit male snapshot policy state containing `kind`, finite float32
`hidden[1,138]`, and bounded failure diagnostics. Keep existing FLYNN snapshots
compatible. Stage and validate male state before native mutation, preserve the
full policy/runtime identity comparison, and invalidate cell caches on restore.
Do not add retina attributes or invent visual populations. Existing
`agent=model` supports tensor hashing and the current 136+2 neural-byte estimate.

Engine needs the two policy creation/reset/action branches and a male population
guard. Profiles/Lab need fixed choices and verified availability. Worker and
replay snapshot registration must retain `policy_identity`; replay must mark male
policy inference correctly and include male source files in its relevant runtime
hash checks for male replays only. Policy/action replay keeps its existing labels.
Actual snapshot continuation and replay must pass a separately bounded runtime
gate before claiming this integration works.
