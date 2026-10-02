# Artwork mappings

This is a bounded M9 implementation slice of **counterfactual choir**, not completion
of PRD §20 or ART-003. It creates an offline WAV from completed, validated recorded
FLYNN population summaries. Verification includes synthetic recording fixtures and two short offline derivatives of
previously recorded actual CPU FLYNN telemetry. No new inference, listening study, or
exhibition was run for this slice.

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

## Timing, bounds, and provenance

Export one episode at a time, retaining every recorded tick. Tick boundary `i` maps
to `round_half_up(i * control_interval_seconds * 48000)`, calculated cumulatively
using the decimal control interval as a rational number. Each boundary is at most
half a sample from its specified time; rounding never accumulates per tick. The
recorded time increments must agree with that interval within 10 ns. Start/end ticks,
simulation timestamps, and all sample boundaries are retained. This renders
**simulation time**, regardless of how slowly the original inference ran in wall time;
it is not an inference-speed measurement or real-time reconstruction.

The entire source recording is limited to 512 MiB and 120 simulated seconds; the
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

## Other five modes: separate, unfinished work

| Mode | Existing basis and work still required |
| --- | --- |
| **afterimage** | Not implemented. Requires an explicit consented stimulus-acquisition path, recorded stimulus/controller alignment, and a documented response-to-line mapping. It must label an authored model portrait, not fly perception. |
| **one map, many possible lives** | Run comparisons exist; this curated presentation is unfinished. Requires selected matched conditions, a visible provenance diff, fixed route scales, and distinct labels for U-only versus controller/anatomy changes. Preserve null differences. |
| **borrowed body** | Recorded simulated route export exists. A complete physical drawing work remains unfinished: calibrated rover/pen, independent safety gates, measured coordinates, and substrate provenance; visible pen marks require a new closed-loop scenario if they affect camera input. |
| **atlas of what disappears** | Not implemented. Requires a versioned graph-intervention/analysis path, named structural metrics, and validated visual mappings; disconnected structure is not automatically lost memory or impaired behaviour. |
| **the space between two flies** | Not implemented. Requires curated anatomical correspondences with dataset/version/units and correspondence uncertainty; specimen differences do not establish population-wide sex effects. |

Camera portraits, anatomy-only output, live sonification, and multi-run synchronized
choirs remain unfinished. No empty mode handlers or fabricated demonstration data
stand in for these requirements. ART-003 remains only partially implemented.

## Verification

`PYTHONPATH=src:tests python -m unittest test_sonification -v` checks synthetic
RunWriter fixtures for fixed mapping, signed/zero means, independent voice selection,
cumulative sample counts, deterministic bytes, embedded hashes, invalid recordings,
resource bounds, exclusive output, partial-write cleanup, and the actual CLI dispatch.
These checks verify the derivative/export mechanism, not biological fidelity,
perceptual quality, actual FLYNN activity, a research effect, or exhibition readiness.

Root verification passed all nine sonification fixture tests (no skips). It also
rendered two prior actual CPU FLYNN recordings (8 and 4 ticks, 0.16 and 0.08 s),
validated embedded source/parent lineage and independently verified PCM hashes.
These short derivatives qualify data compatibility, not exhibition duration or
perceptual quality. Evidence is retained locally in
`runs/m9-recorded-sonification-20261002/report.json` (SHA256
`5879b2d7ea30ec05359d5fe0f6eb31da3f7aeb7bb9e7fb1ec60cf869d2afb88b`).
The pure export function was used for existing records while M3 owned the global
writer lease; CLI dispatch was exercised only by the isolated fixture check.
