# Artwork mappings

The integrated project supplies bounded offline presentations for the six concepts
in PRD §20: recorded sound, route comparison, simulated route export, a structural
atlas, an authored model portrait and a curated anatomical pair. Their mappings
and evidence are linked below. These software paths do not complete physical
rover/pen work, declared-duration exhibition trials or independent-operator acceptance.

Sonification verification includes synthetic recording fixtures and two short
offline derivatives of previously recorded actual CPU FLYNN telemetry. That
sonification slice ran no new inference, listening study or exhibition; the
separate Afterimage mechanism check did run the pinned reduced male model.

## Counterfactual choir: implemented offline derivative

```sh
palimpsest sonify runs/lab/<run-id> --episode 0 \
  --population visual_left --population descending --output exports/choir.wav
```

Select at least one population explicitly. Repeat `--population` to enable additional
voices; omit a population to disable its voice. Nothing plays automatically. The command
does not run a controller, open a microphone/camera, or feed anything back into a policy.
It uses the existing recording reader, which also validates the recorded numeric arrays.
It needs the installed NumPy recording dependency, not Torch or MuJoCo execution.

Every output carries this embedded label:

> Composed mapping of recorded model activity, not biological audio; offline derivative, not live inference.

The supported source is a completed `palimpsest-npz-v1` recording whose FLYNN profile
contains `population_stats` columns `count, mean, min, max` on the declared `[-1, 1]`
scale. The three existing population summaries describe selected model units, not
an independent recording of biological neurons. Missing summaries are an error;
manual/teacher runs and action replays lacking neural telemetry cannot be sonified.

| Individually selectable population | Fixed carrier | Mapping |
| --- | --- | --- |
| `visual_left` | 220 Hz | signed recorded mean × 0.25 × sine carrier |
| `visual_right` | 330 Hz | signed recorded mean × 0.25 × sine carrier |
| `descending` | 440 Hz | signed recorded mean × 0.25 × sine carrier |

Sum only the selected voices, in the table's order. Each carrier starts at phase zero
at output sample zero and continues across tick boundaries. Hold each mean constant
for its whole recorded control interval. A zero mean is silent; a negative mean
reverses that voice's phase. Population count/minimum/maximum are validated but do
not drive additional sound. No per-run normalization, smoothing, random notes,
synthetic activity, or clipping is applied. Abrupt changes can produce clicks; these
are consequences of the documented hold mapping, not invented events.

Encode mono 48,000 Hz signed little-endian 16-bit PCM using
`round_to_nearest_even(32767 * mixed_signal)`. The fixed per-voice gain bounds the
three-voice sum to ±0.75. The tones and frequencies are authored choices; audible
differences alone establish neither a causal neural explanation nor a memory effect.
Identical selected telemetry and timing produce identical PCM under the same numerical
runtime, even for different run IDs. Their WAV metadata still identifies distinct runs;
an unchanged signal is kept unchanged rather than embellished into an audible difference.

## Ordered 120-second episode composition

```sh
palimpsest sonify runs/lab/<run-id> --compose-episodes \
  --population visual_left --population visual_right --population descending \
  --output exports/choir-120s.wav
```

This explicit mode consumes a completed recording of 6,000–6,600 intervals at
0.02 seconds and selects exactly its first 6,000 intervals. It produces 5,760,000
samples (120 seconds), without looping, padding, silence insertion or crossfades.
Episodes must be consecutive and begin at tick zero and simulation time 0.02 s
for their first completed interval. The carrier phase continues across resets.
`--episode` and `--compose-episodes` are mutually exclusive; omission still selects
single episode zero.

The WAV's version-2 `plmp` metadata labels concatenated simulation time, records
each episode's source tick/time range and output sample range, and identifies a
final partial episode. Loading/paused wall time is omitted. Presentation tools must
show these composition boundaries when packaging new material; the historical
25.34-second encounter package is unchanged. All source intervals, including an
unused tail, still undergo checksum, telemetry and terminal-count validation.

Composition sources are bounded at **2 GiB and 6,600 intervals**, leaving up to one
600-interval tail after the selected prefix. Metadata is capped at **256 KiB**;
output remains capped at **16 MiB**. These are fixed bounds, not user overrides.
The existing reader loads one chunk at a time (128 MiB numeric chunk ceiling),
retaining compact route summaries; the sonifier retains only selected population
means and timing. It does not retain the full camera recording in memory. Source
validation still performs multiple disk passes. Byte admission does not qualify
inference performance or guarantee a recording will fit; oversized sources fail.
Use lab records with population telemetry: the ordinary `evaluate` writer does
not supply the required population summaries.

## Timing, bounds, and provenance

Export one episode at a time, retaining every recorded tick. Tick boundary `i` maps
to `round_half_up(i * control_interval_seconds * 48000)`, calculated cumulatively
using the decimal control interval as a rational number. Each boundary is at most
half a sample from its specified time; rounding never accumulates per tick. The
recorded time increments must agree with that interval within 10 ns. Start/end ticks,
simulation timestamps, and all sample boundaries are retained. This renders
**simulation time**, regardless of how slowly the original inference ran in wall time;
it is not an inference-speed measurement or real-time reconstruction.

In the default single-episode mode, the entire source recording is limited to 512 MiB and 120 simulated seconds; the
existing reader's chunk/tick bounds also apply. Each output is capped at 16 MiB,
including at most 64 KiB of embedded metadata. Existing managed-storage byte,
free-space, export-count, and single-writer lease checks apply to the CLI. All
numeric/lineage checks precede output creation. Reject incomplete/failed recordings,
checksums or terminal counts that disagree, missing/nonfinite/malformed statistics,
out-of-scale values, changing population counts, inconsistent timing, and malformed
or conflicting recorded lineage. These checks validate the retained records; they
do not independently authenticate the original experiment or its training history.

The output is created exclusively and never overwrites an existing path. A failed
write removes only its own partial WAV. Source fingerprints are rechecked before
and after writing. Output cannot be placed in the authoritative `recording/` directory.

The WAV's custom `plmp` RIFF chunk contains UTF-8 JSON: source run ID and profile,
source evidence label, file SHA-256 hashes, the SHA-256 of their canonical JSON list,
recorded model/graph/checkpoint and branch provenance, exact mapping parameters,
timing boundaries, and a SHA-256 of the PCM bytes. Ordinary WAV readers can ignore
that chunk; preserve the original file when sharing because audio editors may strip
unknown metadata. There is no sidecar that could become separated during publication.

## One map, many possible lives: implemented offline comparison

```sh
palimpsest compare runs/lab/<run-a> runs/lab/<run-b> --output exports/comparison.html
```

Without `--output`, `compare` retains its existing JSON interface. With `--output`,
it creates one exclusive, self-contained HTML document using the existing validated
comparison and route-export data. No server, script, remote font/asset, new simulation,
policy rerun, or browser session is started. The document explicitly identifies an
offline recorded comparison, not live inference.

Source conditions and a list of expandable provenance differences precede the route
overlay. Both run IDs, controllers, profiles, scenarios, recorded eye-mask intervals,
initial memory hashes, U-swap records, parent/source-snapshot references, and final
phases remain inspectable. Mask intervals come from the actual `eyes` arrays: true
means enabled, false means masked, and null means unrecorded. No enabled-state default
is invented for older recordings. Source identities, file hashes, aggregate recording
hashes, complete comparison data, and the renderer's projection are embedded as
escaped JSON in the document's final expandable provenance section.

The two sources must have the same fixed arena projection. The overlay uses recorded
world coordinates unchanged, with y increasing upward, an 800 × 800 view box, and
40-pixel padding. A is solid blue with a circle at each episode's recorded start;
B is dashed amber with a square at each episode's start. Separate episodes are never
joined. Both paths and start markers survive exact coincidence or stationary routes;
no jitter, offsets, smoothing, or independent scaling creates an artificial difference.
Paths outside the fixed arena are rejected rather than silently clipped. Each source's
last recorded world per episode is shown below on the same scale, explicitly labelled
as final geometry rather than the obstacle/goal geometry at every earlier tick.

Exact equality of the recorded route arrays is displayed descriptively, including
episode/start-tick alignment. It is not a statistical null-effect test. Unequal routes
do not establish a causal memory effect; starts, durations, masks, controller state,
and other conditions can differ. Shared recorded parent/snapshot IDs are references,
not independent certification of a matched U-only intervention. The page does not
silently reclassify a general comparison as a controlled experiment.

The existing recording-reader input limits and checksum/count validation apply.
Metadata is capped at 4 MiB and the complete HTML at 16 MiB. The CLI applies the
existing managed-storage byte/free-space/export-count limits and per-user writer
lease; `.html` joins the counted export formats. Existing outputs are never replaced,
source fingerprints are rechecked around publication, and a write failure removes
only the newly created partial file. Authoritative `recording/` directories cannot
be output destinations. Native expandable details, labelled tables, SVG titles and
descriptions, line patterns, and keyboard focus styles provide the accessibility
baseline without JavaScript.

## Other modes and remaining work

| Mode | Existing basis and work still required |
| --- | --- |
| **afterimage** | [Implemented offline portrait](artwork-afterimage.md): explicit operator-supplied RGB sequence and rights statement, one response per frame, fixed response-plane line and exact alignment/provenance. The [eight-frame actual model and browser check](reports/m9-afterimage-validation.md) passed. This is an authored model portrait, not fly perception or independently verified consent; live capture and exhibition acceptance remain open. |
| **borrowed body** | Recorded simulated route export exists. A complete physical drawing work remains unfinished: calibrated rover/pen, independent safety gates, measured coordinates, and substrate provenance; visible pen marks require a new closed-loop scenario if they affect camera input. |
| **atlas of what disappears** | [Implemented offline atlas](artwork-atlas.md): pinned reduced graph, explicit node isolation, directed reachability losses, nonanatomical layout and embedded provenance. Actual graph checks and browser inspection pass; this measures structure, not lost memory or impaired behaviour. Exhibition gates remain open. |
| **the space between two flies** | [Implemented offline anatomical pair](artwork-specimens.md): one curated DNge104 pairing with dataset/version/units, separate native coordinate spaces, a shared scale and unequal-coverage labels. The [actual-source and browser evidence](reports/m9-specimens.md) verifies preserved geometry and provenance. This is not point-to-point homology, biological function or a population-wide sex effect; exhibition acceptance remains open. |

The bounded offline portrait, anatomy-only and selected-population sound paths
are implemented. Live camera acquisition, live sonification and synchronized
multi-run choirs remain unimplemented. Physical drawing, declared-duration trials
and independent operation remain separate open qualifications; these exports do
not establish completion of R5 or all ART-003 extensions.

## Verification

`PYTHONPATH=src:tests python -m unittest test_sonification -v` checks synthetic
RunWriter fixtures for fixed mapping, signed/zero means, independent voice selection,
cumulative sample counts, deterministic bytes, embedded hashes, invalid recordings,
resource bounds, exclusive output, partial-write cleanup, and the actual CLI dispatch.
These checks verify the derivative/export mechanism, not biological fidelity,
perceptual quality, actual FLYNN activity, a research effect, or exhibition readiness.

`PYTHONPATH=src:tests python -m unittest test_comparison -v` checks synthetic
completed-run fixtures for fixed projection and unmodified points, coincident and
stationary routes, actual mask intervals, U/parent provenance, HTML text escaping,
source integrity, bounds, exclusive publication, and unchanged JSON/working HTML CLI
dispatch. These were structural/fixture checks; no browser was started for that
source slice. The later [recorded comparison browser check](#recorded-comparison-browser-evidence)
covered desktop/mobile layout, keyboard disclosure and print output. Screen-reader
validation and independent exhibition usability remain open.

Root verification passed all nine sonification fixture tests (no skips). It also
rendered two prior actual CPU FLYNN recordings (8 and 4 ticks, 0.16 and 0.08 s),
validated embedded source/parent lineage and independently verified PCM hashes.
These short derivatives qualify data compatibility, not exhibition duration or
perceptual quality. Evidence is retained locally in
`runs/m9-recorded-sonification-20261002/report.json` (SHA256
`5879b2d7ea30ec05359d5fe0f6eb31da3f7aeb7bb9e7fb1ec60cf869d2afb88b`).
The pure export function was used for existing records while M3 owned the global
writer lease; CLI dispatch was exercised only by the isolated fixture check.

Root checked 17 comparison/sonification fixture tests (0.350 s, no skips) and
exported a comparison of two retained actual CPU FLYNN branches. Their route
arrays match exactly; both source identities and three SVG views remain present.
This was a compatibility and null-route presentation check; browser validation was
pending at that stage and is recorded in the later section below. The retained local index is
`runs/m9-recorded-comparison-20261002/report.json`, SHA256
`de3b32b7a216bdef49cd0a8fc9b59ddbddf890455974a67512b79f08ce5aba7c`.
These unchanged tested files were moved to the separate `feat/artwork-comparison`
branch for review; the original evidence keeps its observed output path.

## Recorded comparison browser evidence

On 2 October 2026, Chromium opened the unchanged prior actual-branch comparison HTML (SHA-256 `2857dc2118578af71950a7d29f1de9d57b8310747bb15349b7823da7b0523bb1`). Desktop and 390px mobile layouts have no page overflow; the bounded source table scrolls horizontally on narrow screens. Keyboard disclosure, all three SVG views and PDF print generation passed, with zero page exceptions or external requests. Desktop/mobile screenshots were inspected. This verifies a short recorded comparison presentation, not exhibition duration or a causal memory effect.

Retained report: `runs/m9-browser-comparison-20261002/report.json`, SHA-256 `f2357d45889f39077f55a516dfa6b8eeefe12cca285b552d65a6cb719a729f55`. The source HTML stayed unchanged; full M9 qualification remains open.

The [fixed six-mode handoff plan](plans/m9-offline-handoff.md) and
[source manifest](artwork-handoff.json) select a small portable input folder for a
one-pass offline export smoke. Its driver is fixture-checked; actual curated CLI
execution still requires separate approval. Agent-operated exports do not supply
independent operation, physical drawing or exhibition-duration qualification.
