# Runtime and evidence architecture

Palimpsest keeps one mutable simulator/controller owner and derives presentation
from its records. Start with the [installation and commands](../README.md),
[operating runbook](reports/lab-hardening-runbook.md), and
[requirements-to-evidence matrix](requirements-evidence.md). The combined branch
is under review; the [progress brief](progress.md) identifies unfinished releases.

## A live control tick

```mermaid
flowchart LR
  UI[Browser] -->|validated command| API[Loopback API / supervisor]
  API -->|bounded command queue| Owner[Worker / Engine]
  Owner -->|declared cameras and sensors| Policy[Selected controller]
  Policy -->|validated action| Physics[Pinned MuJoCo environment]
  Physics -->|next observation| Owner
  Owner -->|lossless ticks and events| Records[Authoritative recording]
  Owner -->|latest display sample| UI
  Records --> Playback[Playback / exports / comparisons]
```

[lab.py](../src/palimpsest/lab.py) validates API/session/origin and path inputs,
admits one owner, supervises progress and reaps it before the next run.
[worker.py](../src/palimpsest/worker.py) owns queue transport, recording admission,
initial snapshot registration and display publication. Display samples can be
replaced by newer samples; authoritative events cannot be silently dropped.

[Engine](../src/palimpsest/engine.py) applies idempotent commands at control
boundaries, checks expected state/episode/revision, projects allowed observations,
validates the selected controller's output, and advances physics. Tick rows
record inputs and pose before the step, then actual controls, next pose, reward
and simulation time after it. A browser receipt is distinct from application at
a simulation boundary. Wall-clock display/inference timing is distinct from
advanced simulation time.

The policy receives two RGB eyes and declared contact/relative-bearing sensors.
Evaluator geometry, overlays and path exports are not extra policy inputs.
The analytical teacher and privileged acquisition scripts declare their broader
access explicitly. Manual control, the legacy FLYNN profile and reduced male
CPU profiles have separate identities; failure never silently selects another.

## Durable state and recovery

| Module | Responsibility |
| --- | --- |
| [records.py](../src/palimpsest/records.py) | Manifests, ordered JSON events, checksummed numeric chunks, completion and bounded recovery of a published prefix. |
| [snapshots.py](../src/palimpsest/snapshots.py) | Complete native physics, mutable model/environment fields, observation, controller state, application state and RNG; identity validation before restore. |
| [replay.py](../src/palimpsest/replay.py) | Registered snapshot provenance, executable action/policy replay and first-divergence reporting. |
| [storage.py](../src/palimpsest/storage.py) | Per-user writer lease, fresh disk accounting, free-space floor and configured byte/count limits. |
| [artifacts.py](../src/palimpsest/artifacts.py) | Validated recording reader, playback, comparison provenance and bounded SVG/PNG/bundle export. |

Run directories and snapshots are authoritative local evidence; the SQLite index
is rebuildable. A recovered incomplete prefix is not silently relabelled as a
completed experiment. Snapshots carry software/model/numerical identity and a
durable event prefix. Preserving a controller restores its state; replacing one
preserves the world but explicitly starts fresh controller state.

Playback displays recorded values without running physics. Action replay runs
physics with recorded actions and skips inference. Policy replay recomputes
inference and compares it with the record. Successful execution alone does not
mean agreement. Exact CPU continuation is scoped to retained measurements;
strict CUDA continuation remains unqualified.

## Memory, task and model extensions

[memory.py](../src/palimpsest/memory.py) separates factual M, episodic E and revision
rules U. Fitting reads E; selecting with U changes uncertainty and inspection
requests, not factual payloads. [memory_task.py](../src/palimpsest/memory_task.py)
uses visibility-limited declared packets and evidence-based revisions. A U-only
branch validates all declared non-U invariant hashes. Missing observations are
explicitly unobserved, never treated as evidence of unchanged occupancy.

[task_profiles.py](../src/palimpsest/task_profiles.py) supplies visible-landmark
exploration and encoder-odometry homing. [task_mechanics.py](../src/palimpsest/task_mechanics.py)
contains bounded selection, odometry, wheel fitting and compensation helpers.
Standalone diagnostic success does not make an unintegrated task profile ready.

[male_policy.py](../src/palimpsest/male_policy.py) resolves a fixed seven-file CPU
bundle and verifies model/training/graph/interface identities before loading.
Its hidden state and artificial encoder are distinct from the legacy FLYNN
retina/population state. The [training report](reports/m7-training-pilot.md)
describes the reduced graph and one-seed pilot; it is not a biological mapping
or a topology-benefit result.

Research scripts freeze source identities, protocols and output bounds before
execution. Their reports distinguish collection, cleanup, validation and task
outcomes. Preserve failed outputs and use a new version for a changed protocol.
Run actual model, renderer, browser and performance jobs serially. Fixture CI
does not replace asset-backed simulation, held-out task evaluation, physical
qualification or independent exhibition operation.

Offline [artwork mappings](artwork-mappings.md) and the [atlas](artwork-atlas.md)
reuse validated evidence, label authored transformations and retain provenance.
They do not change sensor inputs. The [rover proposal](rover-procurement-proposal.md)
has no released physical actuation path; procurement and measured physical gates
remain separate requirements.
