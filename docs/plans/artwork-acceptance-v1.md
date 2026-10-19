# Artwork acceptance v1: decisions, declared durations and mappings

**Gate SIM-ARTWORK:** sufficient portable inputs, and visual, audio, keyboard, viewport, faithful-mapping, control and provenance checks that pass for every encounter over its declared duration.

This plan records the user's decisions of 19 October 2026 and the per-encounter contract. Work is on `feat/artwork-acceptance-v1`, branched from `b4b239c`. Human listening and viewing judgement, the listening-level policy, and the operator, audience and custodian declarations stay with milestone 4 (artistic acceptance).

## User decisions

1. **Afterimage input:** the fly's own recorded camera frames from a public lab run (an accepted episode, or the v5 runs). 60 s at 10 fps, so 600 frames, using the fixed male model on CPU with seed 0.
2. **Declared durations:** a 10-minute viewing session for each static mode (Atlas, The space between two flies, One map, Borrowed body SVG); 120 simulated seconds of FLYNN audio for the Choir; 60 s for Afterimage.
3. **One map:** a public lab run and a labelled branch from it.
4. **Inputs:** the portable artwork input ZIP is committed to the repo (`docs/reports/artwork-portability-preparation-evidence/`).

## Per encounter

"Faithful" means every output element is a deterministic function of hash-identified public records. Nothing is interpolated, stretched, normalised or looped, and every artifact carries its provenance: SVG `<metadata>`, the WAV's `plmp` chunk, or the run ids embedded in the HTML.

| Encounter | Declared duration | Faithful mapping, checked automatically | Source |
| --- | --- | --- | --- |
| Afterimage | 60 s of source at 10 fps (600 frames) | One recorded frame gives one male-model response gives one line point, with an exact prefix on fixed axes. The point count equals the frame count, and the frame hashes match the record. | Recorded camera frames from a public manual lab run of at least 60 s simulated. At 50 Hz ticks that means taking every 5th tick, across episodes if needed. |
| One map, many possible lives | 10-minute viewing | Route points equal the recorded poses of each run. Branch origin, intervention and source ids are visible. | A public lab run and a labelled branch |
| Counterfactual choir | 120 s of simulated FLYNN telemetry, so the WAV is exactly 120 s | Fixed 48 kHz voices per population, one control tick per sample block, no normalisation. The decoded duration equals the declaration, and the `plmp` hashes equal the source. | A completed FLYNN CPU run of 120 simulated seconds, on public assets |
| Borrowed body (SVG) | 10-minute viewing | Polyline points equal the recorded route points | A public lab run |
| Atlas of what disappears | 10-minute viewing | Removed (dashed) edges equal the metadata's removed edges, and edges before and after are drawn. The graph and manifest hashes equal the inputs. | MaleCNS v1.0 reduced-neighbourhood extract (CC-BY-4.0) |
| The space between two flies | 10-minute viewing | Rendered segments equal the SWC edges (15,942 + 21,065), with a shared scale and the coverage labels shown | MaleCNS 12781 and FlyWire 720575940640723315 SWCs |

No encounter needs the protected catalog (PR123).

## Automated real-browser checks (`npm run test:artwork`)

`ui/tests/artwork-encounter.spec.ts` serves the committed encounter ZIP through request interception. It aborts and records every other request, so the page runs with the network blocked. It checks:
- **Provenance:** SVG metadata and WAV `plmp` hashes match the committed input manifest, and the PCM hash matches.
- **Element counts:** each artifact's drawn elements match its own metadata.
- **Layout:** labels and artifact links are visible at 1440 px and 390 px, with no horizontal scroll.
- **Keyboard:** tab order runs through all six modes; Afterimage previous and next work from the keyboard.
- **Choir:** no autoplay; keyboard play and the explicit stop work.
- **Audio:** decoded sample rate, duration, RMS and a peak at or below −1 dBFS, plus `ended` firing at the declared length.

When new material replaces the current derivatives, the same harness runs against the new pack, together with a declared-duration session record for each mode.

## Order

0. **Storage-budget recount fix (done).** The lab owner now recounts its storage at most every 5 s instead of before every write. This fixes the v5 late-session cadence drift.
1. **Harness and committed inputs (done).**
2. **Material generation (detached runs, waiting for a green light).**
   - A ≥60 s public manual lab recording and the Afterimage inference over 600 of its frames.
   - A 120 s FLYNN CPU run and the Choir export.
   - A public lab run plus a labelled branch for One map and Borrowed body.
3. **Declared-duration sessions.** Each mode is held open for its declared time, with an automated record and interruption labelling where relevant.
4. **Milestone 4.** Human listening and viewing, the independent operator, and the rights, audience and custodian declarations.

## Notes and open technical points

- **Which input archive backs which pack.** The current encounter pack derives from `palimpsest-artwork-inputs-development-v1.zip`, which is 577,207,446 bytes and stays local. GitHub limits files to 100 MB. Its 98-file manifest is committed (`docs/reports/artwork-review-development-evidence/input-manifest.json`), and the harness checks provenance against it. The committed 4.86 MB archive backs the earlier six-mode offline handoff (`docs/artwork-handoff.json`). New material should be built from committed or public-rebuildable inputs.
- **Afterimage frames.** The recorder stores both eyes. Which eye, or both, becomes the 600-frame `.npy` must be fixed before generation. Episodes of 600 ticks mean at least five consecutive episodes, or a scenario with longer episodes.
- **Choir length.** 120 s at a 0.02 s control interval is 6,000 ticks. That exceeds one 600-tick episode, and the current sonifier maps episode 0. Material generation needs either a FLYNN scenario with at least 6,000 ticks per episode, or a defined multi-episode concatenation. That choice needs a decision.
- **Choir loudness.** The current WAV peaks at −31.1 dBFS (RMS about −38.6 dBFS). The fixed mapping has no normalisation, so the listening-level policy for milestone 4 should take this into account.
