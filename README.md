# Palimpsest

A local, inspectable lab for embodied neural controllers. The current implementation is the **M0 / R0 reproduction harness**: setup diagnostics, pinned FLYNN assets, bounded teacher/FLYNN evaluation, reference preprocessing parity, and recorded inputs, actions, outcomes, and resource measurements.

M1 and later milestones are not implemented: there is no interactive lab, snapshot continuation, replay command, memory learning, additional task controller, MaleCNS profile, or hardware control. See the [R0 evidence report](docs/reports/r0-reproduction.md), [implementation plan](docs/implementation-plan.md), [current progress](docs/progress.md), and preserved [Borrowed Body PRD](docs/borrowed-body-prd-v1.md). A completed evaluation means the bounded experiment finished; inspect its outcomes before making a navigation or performance claim.

## Setup

Use Linux, Git, and [uv](https://docs.astral.sh/uv/getting-started/installation/). Python 3.11 and package versions are recorded in `.python-version` and `uv.lock`.

```sh
git clone --recurse-submodules https://github.com/Aadrika08/palimpsest.git
cd palimpsest
uv python install 3.11
uv sync --locked --extra simulation
uv run --no-sync palimpsest doctor
```

For an existing checkout, initialize the pinned submodule with `git submodule update --init upstream/fly-gym`. Keep it unchanged at `8d964599119b420de67ee259434d273651a1a76d`. The locked Linux environment includes the selected PyTorch/CUDA distribution; installing it can download several GiB even when inference uses CPU.

Commands use [`uv run --no-sync`](https://docs.astral.sh/uv/concepts/projects/sync/) to keep the explicitly prepared environment. When intentionally syncing again, include `--locked --extra simulation`. `doctor` is read-only and exits nonzero for missing requirements, including model assets; the teacher can run without those assets. Rendering still requires a working OpenGL backend: evaluation defaults to `MUJOCO_GL=egl`; test it explicitly with:

```sh
uv run --no-sync palimpsest doctor --probe-renderer
```

## Model assets

Read [third-party notices](THIRD_PARTY_NOTICES.md) before acquisition or reuse. The graph archive and full-vision checkpoint are distributed under **CC BY-NC 4.0**. Their exact URLs, sizes, hashes, source revisions, mappings, and provenance limitations are recorded in [the model manifest](model_manifests/flynn-full-vision.json).

```sh
uv run --no-sync palimpsest assets fetch
uv run --no-sync palimpsest assets verify
uv run --no-sync palimpsest assets prepare
```

`fetch` explicitly downloads the two pinned files into `data/assets/flynn/`, validating temporary downloads before publication. `verify` performs no downloads. `prepare` performs no downloads and extracts only a verified archive into its dedicated graph directory. It verifies the extracted edge list and preserves the archived mapping CSVs unchanged; their CRLF bytes and the upstream Git LF copies have separately pinned identities and must match after CRLF-to-LF conversion. Verified files establish present file identity; the legacy checkpoint does not establish its original training graph or neuron ordering.

Global options precede the command, for example `uv run --no-sync palimpsest --assets /path/to/assets assets verify`. Once dependencies and assets are cached, these commands require no model-hosting service during execution.

## Bounded evaluation

```sh
uv run --no-sync palimpsest evaluate --controller teacher --device cpu \
  --episodes 1 --max-steps 600 --timeout 900 --output runs/teacher-smoke

uv run --no-sync palimpsest evaluate --controller flynn --device cuda \
  --episodes 1 --max-steps 600 --parity --timeout 900 --output runs/flynn-smoke
```

Use a new output directory each time; existing runs are never overwritten. Omitting `--output` creates a timestamped directory under `runs/`. FLYNN defaults to `--device cpu`; CUDA is an explicit selection and must be available. This flag selects inference placement, independently of the renderer. The analytical teacher reads privileged simulator geometry and is a labelled reference, not an equal-information controller baseline.

`--parity` compares each FLYNN tick with upstream observation conversion and checks encoded input, raw output, action, hidden state, and retinal state within recorded tolerances. It adds work and does not establish original checkpoint training provenance. Non-finite neural outputs fail before upstream sanitization or a world step.

The subprocess timeout includes loading and renderer stalls. The recording quota defaults to 2 GiB (`--max-bytes 2147483648`); it covers recording files, including atomic manifest staging, and excludes supervisor logs. Episode counts are bounded to 1–1000, steps to 1–600, and worker threads to 1–16 (default 2). Inspect free RAM, VRAM, and disk before increasing budgets. For a sequential development batch of seeds 0–29:

```sh
uv run --no-sync palimpsest evaluate --controller flynn --device cuda \
  --episodes 30 --seed 0 --max-steps 600 --parity \
  --timeout 7200 --max-bytes 17179869184
```

Each run retains `supervisor.json`, `stdout.log`, `stderr.log`, and a `recording/` bundle containing `manifest.json`, `events.jsonl`, and typed numeric chunks. The manifest records configuration and completion status; events record provenance and episode outcomes. Camera inputs, declared sensors, poses, actions, controls, and timings are retained; FLYNN also records encoded inputs and raw outputs. A timeout or failure is retained explicitly. These records are not full resumable snapshots.

## Tests

```sh
uv run --no-sync pytest -q
```

CI runs all fixture tests on Python 3.11 using CPU PyTorch and small synthetic graphs/checkpoints/archives. It downloads no model assets, requires no GPU or renderer, and makes no full-model runtime or performance claim. Real teacher/FLYNN evaluation and resource evidence remain separate from fixture results.
