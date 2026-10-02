# M2 interactive lab implementation contract

This implements the approved PRD §§6.1, 8, 11–13 and milestone M2. M3 retains endurance/release qualification. No new product scope or hardware purchase is introduced.

## Architecture and ownership

One loopback FastAPI/UI process supervises one spawned simulation worker. The worker creates and exclusively uses Engine, MuJoCo, renderer and policy. Commands and replies are bounded; only latest display samples may be dropped. A worker timeout terminates its process group and records failure. Comparisons/replays/branches run sequentially. No silent device/controller substitution.

- Parent owns `engine.py`, `snapshots.py`, `interventions.py`, new `profiles.py` and `replay.py`, CLI/dependencies/integration.
- Worker/API owner: new `lab.py`, `worker.py`, API/worker tests.
- UI owner: `ui/` only, including exact package pins/lock, TypeScript protocol and browser checks.
- Artifact owner: new `artifacts.py`, its tests. Playback, provenance comparison, SVG/PNG/bundle exports and rebuildable SQLite index.

## Runtime additions

`Engine.open(..., scenario='reproduction', texture='checker')` preserves the reproduction profile. `profiles.list_profiles(root, assets)` returns scenarios/controllers with availability/limitations. `profiles.validate(scenario, texture, controller)` returns fixed scenario configuration; no callbacks or arbitrary XML. Scenario IDs: reproduction, sparse-navigation, blocked-route, target-relocation, vision-ablation, texture-variation. Use upstream checker/realistic variants only; confirm names from source. Other IDs reject before stepping.

Engine exposes `revision` (increments for applied lifecycle/configuration changes and endings, not autonomous ticks or manual intent updates). Commands may supply `expected_revision`; lab always supplies it. Existing phase/episode/idempotency semantics remain. Edits require exact payload validation before queueing. Add `set_eyes` payload `{'left': bool, 'right': bool}`; true means enabled. Record raw and effective camera inputs. Goal/contact cues remain unchanged. Snapshot eye settings/revision; new application schema rejects older incompatible captures. Add `last_transition` containing copied actual inputs/action/control/raw output/neural summaries/latency and episode/tick. Rendering never feeds into policy observations.

`Engine.preview(payload)` validates an intervention against current world without mutation; application always revalidates. UI previews are advisory. World bounds remain pinned; arbitrary body additions unsupported.

Initial snapshots are captured before stepping. A snapshot request requires paused state and writes an exclusive file under the current run's snapshots/. Branching closes the current worker then starts a fresh destination, restores a registered compatible snapshot and optional declared edit. Explicit controller replacement preserves world and begins fresh destination controller state; record this difference and do not label it a full-state matched continuation.

## API v1

All requests use same-origin loopback and a per-process session token. Host/origin checks reject other hosts/origins, including WebSockets. No credentials in URLs or exports. `GET /api/v1/session` returns `{'token': string}` to same-origin JavaScript; authenticated HTTP uses `X-Palimpsest-Session`. WS first message is `{'token': string}`. No CORS wildcard. Bound request bodies to 16 KiB. Paths in API bodies are forbidden: use generated IDs registered under configured runs/output roots.

- `GET /api/v1/profiles` → `{'scenarios': [...], 'controllers': [...], 'textures': [...]}`. Entries have id, label, description; controllers additionally available, reason and privileged.
- `GET /api/v1/runs` → `{'runs': [manifest summaries]}`.
- `POST /api/v1/runs` with `{scenario,texture,controller,device,seed}` → `{run_id,status:'loading'}`. Defaults reproduction/checker/manual/cpu/0. Only one active worker. Explicit close before replacing a live run.
- `GET /api/v1/runs/{id}` → latest authoritative state/sample plus loading/failure state.
- `POST /api/v1/runs/{id}/commands` with Engine command → queued receipt. Later GET/WS receipts report applied tick/rejection. Queue-full is explicit, never drop accepted commands.
- `POST /api/v1/runs/{id}/previews` with `{payload,expected_revision}` → preview result, no mutation.
- `POST /api/v1/runs/{id}/snapshot` with `{expected_revision}` → `{snapshot_id}` or job accepted, paused only.
- `POST /api/v1/branches` with `{source_run_id,snapshot_id,controller?,intervention?}` → new run ID/loading. Same controller by default; explicit close/replacement is recorded.
- `POST /api/v1/runs/{id}/close` → final recorded status and no active worker.
- `GET /api/v1/runs/{id}/events?after=0&limit=200` → `{events,next}` using durable event ordinal cursor.
- `GET /api/v1/runs/{id}/playback?episode=0&tick=0` → recorded sample, always labelled playback.
- `POST /api/v1/runs/{id}/replay` with `{mode:'actions'|'policy'}` → supervised sequential replay job/run ID, requires compatible initial snapshot and complete source recording; no silent replacement with playback.
- `GET /api/v1/compare?left={id}&right={id}` → provenance differences, traces, metrics and event differences. Display provenance before overlays.
- `POST /api/v1/runs/{id}/exports` with `{format:'svg'|'png'|'bundle'}` → `{artifact_id,download_url}`; fixed local output directory and generated names.
- `GET /api/v1/artifacts/{id}` → registered generated artifact only.
- `WS /api/v1/stream` → copied sample/status/receipt messages with version/run ID, no controller objects. Reconnection fetches authoritative status/events.

Browser disconnect clears manual input and pauses at the next control boundary; explicit headless continuation is a separate operator option. A queue-independent pause request must not disappear under command pressure. Startup/step watchdogs stay active during disconnect/loading. Receipt latency and actual boundary application latency remain different measurements.

## Sample contract

A display sample is `{version:1,type:'sample',run_id,mode:'live'|'playback',state,world,inputs,transition,trace,wall_elapsed}`.

- `state`: Engine public_state plus revision, simulation_time and receipts. Phase may additionally be loading before Engine exists. Last outcome remains explicit.
- `world`: `{arena,pose:[x,y,yaw],obstacles:[[x,y,r],...],goal:[x,y,r]}` at the current boundary.
- `inputs`: `{episode,tick,stage:'used'|'next',cam_left,cam_right,sensors:[collision,angle,wind_cos,wind_sin],eyes:{left,right}}`; cameras are PNG data URLs of the actual effective input. Used inputs come from last_transition; next inputs at an initial boundary are labelled accordingly.
- `transition`: null or `{episode,tick,action,control,raw_output?,populations:[{name,count,mean,min,max,scale:[-1,1]}],latency,step_latency}`. Explicit transition tick avoids pairing preceding action with fresh images.
- `trace`: current episode's recorded world-coordinate positions, bounded by 600 steps, not interpolated browser samples. Branch origin is labelled.

Playback uses the same shape from authoritative recorded arrays, does not import Torch/MuJoCo, and never invokes inference. Missing optional neural fields are displayed as unavailable.

## Artifact module contract

`list_runs(root) -> list[dict]`: discover only registered UUID-named immediate run directories, rebuild SQLite summary index from manifests. A run directory contains recording/, snapshots/initial.snp and snapshot-IDs, and exports/.

`playback(run_path, episode=0, tick=0) -> sample`: exhaust integrity validation before exposing a completed recording, select the exact requested tick or reject. Construct world configuration from environment/episode/intervention events and manifest scenario metadata.

`compare_runs(left_path,right_path) -> dict`: IDs, `differences`, `left/right` traces and metrics, events and shared-parent/snapshot lineage. Reject incomplete/corrupt runs. Avoid inferred causality.

`export_run(run_path, output_path, format) -> Path`: exclusive artifact, SVG/PNG same fixed world-coordinate projection; bundle only known manifest/events/chunks/snapshots and derived metadata with relative paths/checksums. No credentials, arbitrary neighboring files or symlink traversal. Validate source completion/integrity first. PNG can use installed Matplotlib Agg; SVG stdlib text/XML; ZIP stdlib. No new rendering dependency.

## Design

Use the PRD's lab-notebook layout: large arena at left, narrow inspector at right, compact controls above, two eyes below the arena, timeline across the bottom. Real run data is the focal point; the empty state invites creation of a run without fabricated traces.

Palette: cool paper #edf2f4, white #ffffff, ink #203444, blue #245b84, amber #8b5b12, berry #9a4265. Verdana/system sans for readable controls/data, Georgia for the single Palimpsest title. Left-aligned labels, native select/input/button controls, visible keyboard focus, route line patterns plus color. No external fonts/services or decorative animations. Scale the arena responsively; all controls remain usable at narrow widths.

## Verification and commits

- [x] Scenario/mask/revision/preview tests, upstream preprocessing parity and state continuation with masks.
- [x] API session/origin/path/admission checks, one-worker ownership, disconnect pause and watchdog failure fixtures.
- [x] Recorded playback, three-mode distinction, replay first-divergence report, provenance differences, export coordinates/integrity tests.
- [x] UI build/type check and actual browser workflow: create/run/pause/intervene/snapshot/two sequential branches/compare/export; manual blur clears input.
- [x] Full fixture suite plus actual manual/teacher workflow and one full-FLYNN CPU sample; retain evidence and limitations.
- [ ] Commit final implementation/evidence, push Aadrika08, stacked draft PR against feat/execution-recovery; no automatic merge. The scenario increment is already committed/pushed as `3b25f5e`.
