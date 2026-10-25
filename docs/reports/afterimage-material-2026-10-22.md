# Afterimage camera portrait — 22 October 2026

**Material generation and full-duration browser presentation passed. Human
artistic acceptance remains open.**

Executed the [prospective allocation](../plans/afterimage-material-2026-10-22.md)
once from committed source `0a51ddd369df238b58cdc47dd4babc7b648c6938`.
The [receipt index](afterimage-material-2026-10-22/index.json) hashes retained
registration, manifests, audit, browser results, screenshots and scripts.

## Actual material

| Item | Observed result |
| --- | --- |
| Manual source | 3,543 intervals, eight natural episodes, 697,712,617 bytes |
| Source controller | Public Engine manual, scripted constant `[1, 0.5]`, consecutive seeds 0–7; not human joystick input |
| Source generation and extraction | 23.361 s, exit 0, 300 s supervisor; process group absent |
| Selection | Effective `cam_left`, indices 0,5,…,2995 of the first 3,000 intervals; all 3,543 validated |
| Stimulus | 600 uint8 128×128×3 frames; NPY 29,491,328 bytes, below 32 MiB |
| Portrait | `male-original`, CPU, seed 0; 600 actual responses in 3.732 s including loading, exit 0 under unchanged 120 s supervisor |
| Portrait recording | 59,458,069 bytes, below 96 MiB |
| Timing | Source sample times 0–59.9 s; sample-and-hold display 60 s; model index time 12 s |
| SVG | 289,373 bytes; SHA-256 `19112974f2332be3109c4aaa72005715a846ddd022b8b33c634940182988c2cc` |

One model reset precedes the portrait; hidden state carries across every frame,
including source episode changes. Each selected RGB frame enters both camera
channels with the existing fixed sensors. No resize, interpolation, smoothing,
frame repetition, aesthetic selection or extra inference allocation was used.
Source simulation timestamps mark interval ends; the companion index also
retains observation start times, run/episode/tick, eye masks and frame hashes.
The last selected source episode uses its first 57 intervals; 543 trailing
recorded intervals are omitted. The sampled last frame is native tick 52.

The [independent audit](afterimage-material-2026-10-22/independent-audit.json)
rehashes the source and portrait files, validates all source intervals, compares
every selected image byte with both recorded model inputs, checks timestamps,
sensors, raw-output/action scaling, and every actual SVG polyline point. It
does not execute a second independent model forward pass; the earlier eight-frame
mechanism gate remains separate evidence. Generation source pins were unchanged.

## Encounter and checks

The updated encounter validates the companion camera index against SVG frame
hashes and source timestamps before enabling the 60-second controls. It labels
manual source and male portrait separately. Playback is user-started, holds each
sample on fixed axes at 10 fps, ends without looping, supports stop/reset and
manual stepping, and stops on panel collapse or a hidden-page event.

- **74 focused Python tests passed:** extraction/driver, encounter, Afterimage,
  records, sonification and artifacts. Expected duplicate-ZIP fixture warning
  and existing Matplotlib/Pyparsing deprecation warnings remain.
- UI TypeScript check passed; `git diff --check` passed.
- Actual Chromium presentation: **60.0117 s, all 600 frames in order**, maximum
  observed frame timing error 0.0144 s; 600 final prefix points.
- Keyboard start, stop and manual step, panel-collapse stop, no automatic start
  or repeat, 1440 px and 390 px layout passed. Zero page errors/external requests.
- Screenshots inspected: fixed axes retain the small response extent, mobile
  controls and source labels fit. No artistic expressiveness claim follows.
- Fresh read-only code review: no concrete blocking issues; 16 focused tests
  independently rerun. Hidden-tab behavior was not exercised by the browser
  harness; the handler is present. This is a remaining browser coverage limit.

The renderer remains unchanged. Existing short-artifact behavior is covered by
the focused tests; the full repository suite and unrelated runtime campaigns
were not rerun.

## Local review pack and rebuild

- Encounter: `runs/afterimage-material-2026-10-22-v1/encounter/index.html`
- ZIP: `runs/afterimage-material-2026-10-22-v1/palimpsest-afterimage-choir-encounter-2026-10-22.zip`
- ZIP: **23,723,504 bytes**, 15 members, SHA-256
  `afd7e147c398bd39f3896ed8679484742dfafe98b3cf234d810273bf8f402a80`.
- All members read back byte-exact. Pack combines this portrait with the audited
  actual Choir WAV and four historical development modes. Raw camera/portrait
  records and the NPY remain local, outside Git and the portable derivative ZIP.

The ZIP contains the source index, source registration, stimulus manifest,
audit, source notices and public rebuild instructions. Rebuild on pinned source
with a fresh output path, then use the public Afterimage CLI with the generated
stimulus and registered portrait UUID. Fresh reruns need not be byte-identical.
Retained audit/package scripts are evidence of this consumed allocation; do not
overwrite or automatically rerun the allocation.

**Storage deviation:** the source/package stages used the planned 2 GiB aggregate
and 2 GiB floor. The actual public record/render CLI invocations used their
default 20 GiB aggregate and 1 GiB floor; the unchanged 32 MiB input, 96 MiB
record and 120 s inference caps still applied. Measured allocation stayed below
1 GiB and free disk space above 8 GiB. Future invocations should pass
`--storage-max-bytes 2147483648 --min-free-bytes 2147483648` explicitly.

## Remaining work

Next technical material blocker: **a public lab run and labelled branch** for
One map, many possible lives and Borrowed body. The historical mirrored routes
have no parent/branch relationship. Then run the four declared ten-minute viewing
sessions. Human viewing/listening decisions for Afterimage and Choir, independent
operator acceptance, audience/rights/custodian declarations and physical work
remain open. No scientific or full six-mode exhibition qualification is claimed.
