# Palimpsest

A local, inspectable lab for embodied neural controllers. Includes the **M0 / R0 reproduction harness**, **M1 execution/recovery**, and the **M2 interactive lab** with actual sensor inputs, world edits, snapshots, sequential branches and recorded artifacts.

Release endurance, memory learning, additional task controllers, MaleCNS and hardware control remain incomplete. See the [R0 evidence](docs/reports/r0-reproduction.md), [M1 evidence and CUDA limitation](docs/reports/m1-execution.md), [M2 interactive lab evidence](docs/reports/m2-interactive-lab.md), [implementation plan](docs/implementation-plan.md), [current progress](docs/progress.md), and preserved [Borrowed Body PRD](docs/borrowed-body-prd-v1.md). A completed evaluation means the bounded experiment finished; inspect its outcomes before making a navigation or performance claim.

## Setup

Use Linux, Git, and [uv](https://docs.astral.sh/uv/getting-started/installation/). Python 3.11 and package versions are recorded in `.python-version` and `uv.lock`.

```sh
git clone --recurse-submodules https://github.com/Aadrika08/palimpsest.git
cd palimpsest
uv python install 3.11
uv sync --locked --extra simulation --extra lab
uv run --no-sync palimpsest doctor
```

For an existing checkout, initialize the pinned submodule with `git submodule update --init upstream/fly-gym`. Keep it unchanged at `8d964599119b420de67ee259434d273651a1a76d`. The locked Linux environment includes the selected PyTorch/CUDA distribution; installing it can download several GiB even when inference uses CPU.

Commands use [`uv run --no-sync`](https://docs.astral.sh/uv/concepts/projects/sync/) to keep the explicitly prepared environment. When intentionally syncing again, include `--locked --extra simulation --extra lab`. `doctor` is read-only and exits nonzero for missing requirements, including model assets; the teacher can run without those assets. Rendering still requires a working OpenGL backend: evaluation defaults to `MUJOCO_GL=egl`; test it explicitly with:

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

## Interactive lab

Use Node 24 (exact version in `ui/.node-version`) to prepare the local UI once:

```sh
npm --prefix ui ci
npm --prefix ui run build
uv run --no-sync palimpsest lab
```

Open `http://127.0.0.1:8765`. The service binds to loopback and authenticates browser requests with a process-local session token. Manual and teacher controllers need no model download. FLYNN requires verified assets and an explicit CPU/CUDA choice; it never silently substitutes another controller or device.

Create a run, start or step it, then pause to capture a snapshot. World edits have a validated preview and are rechecked at the application boundary. An eye mask changes the actual policy input; the inspector distinguishes the input/action tick from the resulting world boundary. Focus the manual drive control for arrow keys; losing focus clears held input. Closing the browser pauses at the next boundary. Only the explicit `--headless-continue` option changes disconnect behavior.

Branches run sequentially in fresh workers. Preserving the controller restores its state; choosing a different controller retains the world but starts fresh controller state and records that distinction. Compare provenance before interpreting route overlays. Loading, replay, failure, termination and time limits retain explicit labels. CPU full-model continuation is qualified only for the measured profile; CUDA has the known strict-continuation limitation described below.

The inspector reports measured active execution time and real-time factor (advanced simulated seconds divided by active wall seconds). Loading and paused periods are excluded; logging, rendering and waiting for a requested pause boundary are included. A value below one means slower than real time. Trajectory visibility is a presentation-only control and sends no simulation command. Close the active owner before exporting a completed recording.

The lab stores UUID-named directories under `runs/lab/`. Playback reads recorded values without simulation or inference. Action replay advances physics using recorded actions and skips inference. Policy replay recomputes the recorded controller. Both executable replays check compatible source provenance, snapshots and numeric records, then report agreement or the first divergence under fixed tolerances; completion alone is not agreement.

```sh
uv run --no-sync palimpsest replay runs/lab/SOURCE_UUID --mode playback --tick 0
uv run --no-sync palimpsest replay runs/lab/SOURCE_UUID --mode actions
uv run --no-sync palimpsest replay runs/lab/SOURCE_UUID --mode policy
uv run --no-sync palimpsest compare runs/lab/LEFT_UUID runs/lab/RIGHT_UUID
uv run --no-sync palimpsest export runs/lab/SOURCE_UUID --format svg --output route.svg
```

Replace UUID placeholders with recorded run IDs. A branch can begin at a nonzero episode/tick; select its first recorded transition. Exports also support `png` and `bundle`, never overwrite existing files, and exclude session credentials. Executable replay uses a bounded child process (`--timeout 900` by default); replay job pause/resume controls affect transport only, preserving the recorded engine timeline. Old runs without registered snapshot hashes cannot be replayed as compatible evidence.

## Bounded evaluation

```sh
uv run --no-sync palimpsest evaluate --controller teacher --device cpu \
  --episodes 1 --max-steps 600 --timeout 900 --output runs/teacher-smoke

uv run --no-sync palimpsest evaluate --controller flynn --device cuda \
  --episodes 1 --max-steps 600 --parity --timeout 900 --output runs/flynn-smoke
```

Use a new output directory each time; existing runs are never overwritten. Omitting `--output` creates a timestamped directory under `runs/`. FLYNN defaults to `--device cpu`; CUDA is an explicit selection and must be available. This flag selects inference placement, independently of the renderer. The analytical teacher reads privileged simulator geometry and is a labelled reference, not an equal-information controller baseline.

`--parity` compares each FLYNN tick with upstream observation conversion and checks encoded input, raw output, action, hidden state, and retinal state within recorded tolerances. It adds work and does not establish original checkpoint training provenance. Non-finite neural outputs fail before upstream sanitization or a world step.

The subprocess timeout includes loading and renderer stalls. The per-recording quota defaults to 2 GiB (`--max-bytes 2147483648`), including atomic manifest staging. Shared storage limits below additionally cover logs and other outputs. Episode counts are bounded to 1–1000, steps to 1–600, and worker threads to 1–16 (default 2). For a sequential development batch of seeds 0–29:

```sh
uv run --no-sync palimpsest evaluate --controller flynn --device cuda \
  --episodes 30 --seed 0 --max-steps 600 --parity \
  --timeout 7200 --max-bytes 17179869184
```

Each run retains `supervisor.json`, `stdout.log`, `stderr.log`, and a `recording/` bundle containing `manifest.json`, `events.jsonl`, and typed numeric chunks. The manifest records configuration and completion status; events record provenance and episode outcomes. Camera inputs, declared sensors, poses, actions, controls, and timings are retained; FLYNN also records encoded inputs and raw outputs. A timeout or failure is retained explicitly. These records are not full resumable snapshots.

## Storage and recovery

Lab, evaluation, executable replay and export accept `--storage-max-bytes` (default 20 GiB), `--min-free-bytes` (1 GiB), `--max-runs` (1024), `--max-snapshots` (64 per run), `--max-exports` (1024), and `--log-max-bytes` (1 MiB per stdout/stderr stream). Use `--help` for accepted bounds. The lab counts its configured run/export roots; CLI writers count the output's parent directory. Assets must be outside those roots. Existing and interrupted files count, including temporary publication files; nothing is automatically deleted.

Preflight estimates use the loaded profile's actual camera/neural dimensions and the serialized snapshot. Every subsequent write is checked too, so resets do not bypass the quota. Log pipes cap native and Python output and retain its prefix on failure. Reserved space supports bounded failure reports. One per-user writer lease serializes Palimpsest lab/CLI writers, including overlapping output directories; close another running lab before starting a separate writer.

After a quota, process or recording failure, preserve the diagnostics and published recording prefix, close the failed owner, then start a fresh run or branch from a registered compatible snapshot. Do not treat orphan chunks or incomplete commands as applied data. Archive or remove selected old output directories yourself after the lab is closed; the application does not choose evidence to delete. See the [hardening verification and recovery runbook](docs/reports/lab-hardening-runbook.md) for cached offline setup, sustained execution, failure checks and endurance commands. Release qualification remains pending while those gates are incomplete.

## Execution and snapshots

`palimpsest.engine.Engine` owns simulation/controller state on its creating thread. `submit()` queues an idempotent command; `advance()` applies pending commands at a control boundary and advances at most one tick. Receipts distinguish queued, applied, rejected and failed operations. Supported commands are run, pause, step, stop, reset, manual action, and validated goal/obstacle edits.

`palimpsest.snapshots` captures/restores paused application state, native MuJoCo state including derived caches, controller/retinal state, RNGs and pending commands. Restore into a fresh compatible engine, validate application metadata before restoring physics, then restore application metadata. New branches retain their own run IDs and the original event-prefix identity. Snapshot files are trusted local artifacts tied to their software/model/numerical profile; the native decoder is not a hostile-import sandbox.

Run the fresh-process verification on the real environment and full model:

```sh
uv run --no-sync python scripts/verify_execution.py --controller flynn --device cpu \
  --assets data/assets/flynn --continuation 100 --output runs/cpu-continuation
```

Use `--controller manual` or `teacher` for those paths. The verifier preserves a goal edit and a queued command, checks recording integrity and branch lineage, and compares inputs, actions, physics, RNGs, full hidden state and retinal state. It reports failures and exits nonzero. Camera/integer values must match exactly; float tolerances are fixed at `atol=rtol=1e-6`.

CPU continuation passed on the measured host. CUDA inference remains available, but upstream CUDA sparse matrix multiplication varied on repeated identical inputs; one saved continuation failed the strict check. No device fallback or tolerance relaxation occurs. Reproduce that kernel diagnosis with `scripts/probe_cuda_repeatability.py --assets data/assets/flynn --output runs/cuda-kernels`.

## Tests

```sh
uv run --no-sync pytest -q
PALIMPSEST_SIMULATION_TESTS=1 MUJOCO_GL=egl uv run --no-sync pytest -q
```

The second command also exercises actual EGL world edits, teacher contact/recovery and termination continuation. CI runs CPU fixture tests and skips renderer-dependent cases. It downloads no model assets and makes no full-model runtime or performance claim. Actual full-model evidence remains separate from fixture results.
