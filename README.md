# Palimpsest

A local, inspectable lab for embodied neural controllers, with actual sensor inputs, world edits, full snapshots, sequential branches, recorded artifacts and bounded research profiles.

The project combines the completed R0–R1 lab and memory mechanics with development memory acquisition, exploration/encoder-homing, a trained reduced MaleCNS pilot and offline artwork exporters. The full simulation release remains incomplete; physical rover deployment is deferred. The recorded hour gate passed its scoped R1 contract. The later [manual lab refresh v5](docs/reports/manual-lab-refresh-v5.md) passed its declared browser cadence tolerance, superseding the earlier 27.98 Hz observation for that manual session only. See the [R0 evidence](docs/reports/r0-reproduction.md), [M1 evidence and CUDA limitation](docs/reports/m1-execution.md), [M2 interactive lab evidence](docs/reports/m2-interactive-lab.md), [implementation plan](docs/implementation-plan.md), [current progress](docs/progress.md), and preserved [Borrowed Body PRD](docs/borrowed-body-prd-v1.md). A completed evaluation means the bounded experiment finished; inspect its outcomes before making a navigation or performance claim.

The [completion checklist](docs/plans/project-completion-2026-10-23.md) tracks remaining work and delivery to remote `main`. The [integration report](docs/reports/main-integration-2026-10-25.md) distinguishes verified local changes from published work. Historical evidence identifies its original source commit and does not certify a newer combined source.

The [architecture guide](docs/architecture.md) maps live control, snapshots,
recordings and research extensions to their implementation and evidence boundaries.

## Setup

Use Linux, Git, and [uv](https://docs.astral.sh/uv/getting-started/installation/). Python 3.11 and package versions are recorded in `.python-version` and `uv.lock`.

```sh
git clone --branch main --recurse-submodules https://github.com/Aadrika08/palimpsest.git
cd palimpsest
uv python install 3.11
uv sync --locked --extra simulation --extra lab
uv run --no-sync palimpsest doctor
```

These commands install published `main`; changes listed as local in the integration report are still awaiting delivery. For an existing checkout, initialize the pinned submodule with `git submodule update --init upstream/fly-gym`. Keep it unchanged at `8d964599119b420de67ee259434d273651a1a76d`. The locked Linux environment includes the selected PyTorch/CUDA distribution; installing it can download several GiB even when inference uses CPU.

Commands use [`uv run --no-sync`](https://docs.astral.sh/uv/concepts/projects/sync/) to keep the explicitly prepared environment. When intentionally syncing again, include `--locked --extra simulation --extra lab`. `doctor` is read-only and exits nonzero for missing requirements, including model assets; the teacher can run without those assets. Rendering still requires a working OpenGL backend: evaluation defaults to `MUJOCO_GL=egl`; test it explicitly with:

```sh
uv run --no-sync palimpsest doctor --probe-renderer
```

Before fetching FLYNN assets, an `assets: missing` check and exit status 1 are expected. If the remaining required checks pass, continue to [Interactive lab](#interactive-lab) for manual or teacher control. Inspect the renderer check separately; missing assets can still make the probe command exit 1 even when rendering works.

## Model assets

Read [third-party notices](THIRD_PARTY_NOTICES.md) before acquisition or reuse. The graph archive and full-vision checkpoint are distributed under **CC BY-NC 4.0**. Their exact URLs, sizes, hashes, source revisions, mappings, and provenance limitations are recorded in [the model manifest](model_manifests/flynn-full-vision.json).

```sh
uv run --no-sync palimpsest assets fetch
uv run --no-sync palimpsest assets verify
uv run --no-sync palimpsest assets prepare
```

`fetch` explicitly downloads the two pinned files into `data/assets/flynn/`, validating temporary downloads before publication. `verify` performs no downloads. `prepare` performs no downloads and extracts only a verified archive into its dedicated graph directory. It verifies the extracted edge list and preserves the archived mapping CSVs unchanged; their CRLF bytes and the upstream Git LF copies have separately pinned identities and must match after CRLF-to-LF conversion. Verified files establish present file identity; the legacy checkpoint does not establish its original training graph or neuron ordering.

Global options precede the command, for example `uv run --no-sync palimpsest --assets /path/to/assets assets verify`. Once dependencies and assets are cached, these commands require no model-hosting service during execution.

The two reduced male CPU controllers use a separate, committed 836,835-byte
bundle in `data/assets/flynn/male-reduced-v1/`; they need no FLYNN checkpoint
download. [Its manifest](data/manifests/male-reduced-policy-v1.json) pins all seven
files. The normal lab validates these identities before loading either model.
If using a custom `--assets` directory, copy that complete subdirectory there
unchanged. These are the existing five-epoch pilot checkpoints, not a newly
trained or navigation-qualified release. Their artificial sensor mapping,
training lineage and limits are in the [training report](docs/reports/m7-training-pilot.md).
See [MaleCNS attribution and modifications](THIRD_PARTY_NOTICES.md#malecns-reduced-pilot).

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

To recover a closed run's snapshots after reloading, select its entry in
**Recorded run**, then select a **Snapshot** and choose **Start branch**.

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

## Development profiles and artwork

For the recorded six-work encounter, extract the [guided offline ZIP](docs/reports/guided-encounter-2026-10-23/palimpsest-guided-encounter-2026-10-23.zip) and open `index.html`. It includes the 600-frame Afterimage presentation, 120-second Choir and source notices; no model runtime is needed. Human viewing/listening and independent operator acceptance remain pending.

| Capability | Entry point and current boundary |
| --- | --- |
| Memory mechanics | Select **Memory passages** in the lab. Typed M/E/U, visibility-limited sensing, evidence-backed revision and U-only snapshot branches are implemented. [Mechanics evidence](docs/reports/m4-memory-mechanics.md). |
| Recorded revision histories | [Memory v1 is retired at 44/48 accepted development cells](docs/reports/m5-v1-structural-null.md), with no demonstrated own-U task benefit. Its four missing cells and held-out outline are not active work. R2 requires the separate memory-v2/family path: [current retained-condition checks](docs/reports/memory-retained-condition-v1-2026-10-23.md) cover all nine conditions with authored fixtures, while real qualification, whole-case publication, pruning and scientific studies remain open in the [completion checklist](docs/plans/project-completion-2026-10-23.md). |
| Exploration and encoder homing | Select the corresponding lab scenario. Use manual or FLYNN control through the declared cue. [Manual homing evidence](docs/reports/m6-homing-driver-v2.md) covers one bounded cue-following driver; it does not establish pretrained FLYNN competence. |
| Loaded wheel compensation | Select **Calibrated wheel compensation (development)** with manual CPU control. [Fixed calibration/native/replay evidence](docs/reports/m6-body-runtime-v2.md) passes; online adaptation, mixed-motion navigation and physical motors remain unqualified. |
| Measured wheel calibration | Select **Measured wheel calibration (development)** with manual CPU control. Four fixed probes lead to an explicitly accepted fitted episode; Reset clears measurements. [Measured simulator calibration](docs/reports/m6-body-adaptation-v2.md), native continuation and both replays pass the bounded development gate. The [actual browser workflow](docs/reports/m6-body-adaptation-ui.md) also passes all four probes, fitted controls, Reset and 492-tick action replay. Held-out task and physical qualification remain pending. |
| Calibrated encoder homing | Select **Calibrated encoder homing (development)** with manual CPU control. Complete the four calibration probes using **Next calibration trial**, then **Start fitted episode** to activate the encoder-only task; Reset clears the fit and task. The [fixed simulator composition and browser workflow](docs/reports/m6-body-homing-composition-v2.md) pass homing, native continuation, both replays, calibration and Reset, with 0.1196 m home error in the mechanism gate. This is one simulated body/world/seed composition. |
| Learned puck research | [Three separately trained models](docs/reports/m6-puck-training-v2.md) have native/replay evidence, but the [fixed development](docs/reports/m6-puck-student-development.md) scores 0/4 goals per model. The balanced-loss candidates pass their [native mechanism](docs/reports/m6-puck-balanced-student-mechanism.md), but their [completed development evaluation](docs/reports/m6-puck-balanced-development.md) also scores 0/4 for each model. Both arms fail the unchanged 3/4 gate; held-out stays locked and automatic fitting has stopped. These are headless research runners; learned manipulation and lab UI integration remain incomplete. |
| Reduced MaleCNS pilot | [Training protocol](docs/plans/m7-training-protocol.md), `scripts/collect_male_teachers.py`, and `scripts/train_male_reduced.py`. Separate artificial input mapping, trained weights and degree-rewired control; recorded-input parity is measured. Two pinned CPU lab controllers, native continuation and executable replay are implemented; the live browser workflow also passes. The [16-run closed-loop evaluation](docs/reports/m7-closed-loop-v2.md) completed with 0/8 original and 1/8 control goals; navigation qualification remains incomplete. A [separate three-seed development protocol](docs/plans/m7-training-v2-protocol.md) has six trained candidates and a [completed 24-run development gate](docs/reports/m7-training-v2-stage-c.md). Its per-seed threshold fails, leaving that protocol's held-out evaluation locked; it does not replace these production checkpoints. A separate [recovery held-out evaluation](docs/reports/m7-recovery-heldout-closed-loop.md) completes 48 runs: originals reach 5/24 goals and controls 8/24. No useful-navigation or topology advantage is established. R3 remains open for the [new navigation study](docs/plans/m7-navigation-study.md); its [six frozen research models](docs/reports/m7-navigation-training-v2.md) complete the [24-case development study](docs/reports/m7-navigation-development-v2.md): old-corpus models reach 2/4, 1/4 and 1/4 goals; augmented models reach 0/4 each. The unchanged 3/4 per-augmented-seed gate fails. Held-out stays locked, the single aggregation round is exhausted, and R3 remains open. |
| Afterimage portrait | [Authorized local frames, bounded fixed-model inference and offline SVG](docs/artwork-afterimage.md). The [600-frame source/response presentation](docs/reports/afterimage-presentation-2026-10-22.md) has exact frame and browser checks; human artistic acceptance remains pending. No fly-perception or exhibition qualification claim. |
| Anatomical pair | [Curated MaleCNS/FlyWire DNge104 skeletons](docs/artwork-specimens.md), with distinct provenance, separate coordinate spaces and one shared scale. Actual geometry and browser checks pass; no registration or population sex-effect claim. |
| Recorded artwork | [Fixed sound mapping and offline comparison](docs/artwork-mappings.md): `sonify` renders selected neural telemetry, `compare LEFT RIGHT --output comparison.html` renders labelled route panels. Neither performs inference or modifies source records. |
| Physical rover | [Procurement proposal](docs/rover-procurement-proposal.md). No physical operation is qualified. |

Run each command with `--help` and retain new output directories. Research runners
have frozen protocols, explicit source identities and finite resource limits.
Earlier failures remain part of the evidence. A completed mechanism check is not
held-out competence or a demonstrated advantage from connectome topology.

Use the [supervised exhibition runbook](docs/exhibition-runbook.md) for mode labels, source retention, pause/recovery and independent-operator acceptance. Physical drawing and declared-duration exhibition qualification remain open.

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

After a quota, process or recording failure, preserve the diagnostics and published recording prefix, close the failed owner, then start a fresh run or branch from a registered compatible snapshot. Do not treat orphan chunks or incomplete commands as applied data. Archive or remove selected old output directories yourself after the lab is closed; the application does not choose evidence to delete. See the [hardening verification and recovery runbook](docs/reports/lab-hardening-runbook.md) for cached offline setup, sustained execution, failure checks and endurance commands. The retained R1 release observations and explicit limits are indexed in [requirements and evidence](docs/requirements-evidence.md); later release gates remain pending.

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
scripts/run_tests.sh
PALIMPSEST_SIMULATION_TESTS=1 scripts/run_tests.sh
```

The [canonical runner](docs/testing.md) separates ordinary, process-isolated, runs-directory and tmpfs fixtures. The second command also enables actual EGL world edits, teacher contact/recovery and termination continuation. The CI configuration uses the default fixture passes and downloads no model assets; its current hosted result is recorded in the integration report. Actual full-model evidence remains separate from fixture results.
