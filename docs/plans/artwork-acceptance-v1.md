# Artwork acceptance v1: decisions, declared durations and mappings

**Gate SIM-ARTWORK:** sufficient portable inputs, and visual, audio, keyboard, viewport, faithful-mapping, control and provenance checks that pass for every encounter over its declared duration.

This plan records the user's decisions of 19 October 2026 and the input-contract decisions accepted on 21 October 2026. The original work on `feat/artwork-acceptance-v1`, branched from `b4b239c`, was merged into `main` at `0b9fb7e`. Human listening and viewing judgement, the listening-level policy, and the operator, audience and custodian declarations stay with milestone 4 (artistic acceptance).

## User decisions

1. **Afterimage input:** the fly's own recorded camera frames from a public lab run (an accepted episode, or the v5 runs). 60 s at 10 fps, so 600 frames, using the fixed male model on CPU with seed 0.
2. **Declared durations:** a 10-minute viewing session for each static mode (Atlas, The space between two flies, One map, Borrowed body SVG); 120 simulated seconds of FLYNN audio for the Choir; 60 s for Afterimage.
3. **One map:** a public lab run and a labelled branch from it.
4. **Inputs:** the portable artwork input ZIP is committed to the repo (`docs/reports/artwork-portability-preparation-evidence/`).

5. **Afterimage eye selection (21 October):** left camera only, every fifth interval from 3,000 chronological 50 Hz source intervals, producing 600 frames. Keep the existing duplicated-image `male-original` CPU mapping, seed 0 and one initial model reset. Retain source episode boundaries and distinguish concatenated source time from model time.
6. **Choir episode handling (21 October):** explicitly concatenate chronological episodes from one public FLYNN CPU recording, mapping exactly 6,000 genuine intervals to 120 seconds. Label episode boundaries and any final-episode prefix; retain fixed audio mapping and continuous carrier phase without looping, normalization or crossfades.

The [accepted input contract](../superpowers/plans/2026-10-21-artwork-input-contract.md) fixes selection, timestamps, provenance and rejection rules. **Blocker 1 is closed.** Runtime readiness, source capacity, implementation and actual material generation remain pending.

## Per encounter

"Faithful" means every output element is a deterministic function of hash-identified public records. Nothing is interpolated, stretched, normalised or looped, and every artifact carries its provenance: SVG `<metadata>`, the WAV's `plmp` chunk, or the run ids embedded in the HTML.

| Encounter | Declared duration | Faithful mapping, checked automatically | Source |
| --- | --- | --- | --- |
| Afterimage | 60 s of source at 10 fps (600 frames) | One recorded frame gives one male-model response gives one line point, with an exact prefix on fixed axes. The point count equals the frame count, and the frame hashes match the record. | Recorded left-camera frames from a public manual lab run: every fifth interval across 3,000 chronological intervals, with episode boundaries retained. |
| One map, many possible lives | 10-minute viewing | Route points equal the recorded poses of each run. Branch origin, intervention and source ids are visible. | A public lab run and a labelled branch |
| Counterfactual choir | 120 s of simulated FLYNN telemetry, so the WAV is exactly 120 s | Fixed 48 kHz voices per population, one control tick per sample block, no normalisation. The decoded duration equals the declaration, and the `plmp` hashes equal the source. | Exactly 6,000 chronological intervals from a completed public FLYNN CPU recording, with episode composition and any final prefix labelled |
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

The [21 October runtime/capacity check](../reports/artwork-runtime-capacity-2026-10-21.md) passes locked setup, asset validation, EGL rendering and 23 focused synthetic tests. It establishes that the complete Choir source exceeds the original 512 MiB reader cap. The subsequent explicit `--compose-episodes` implementation admits up to 2 GiB / 6,600 source intervals, validates the entire recording, and exports its first 6,000 intervals with version-2 episode provenance. Actual source-generation and browser acceptance remain pending.

- **Which input archive backs which pack.** The current encounter pack derives from `palimpsest-artwork-inputs-development-v1.zip`, which is 577,207,446 bytes and stays local. GitHub limits files to 100 MB. Its 98-file manifest is committed (`docs/reports/artwork-review-development-evidence/input-manifest.json`), and the harness checks provenance against it. The committed 4.86 MB archive backs the earlier six-mode offline handoff (`docs/artwork-handoff.json`). New material should be built from committed or public-rebuildable inputs.
- **Afterimage feasibility.** Left-eye selection is accepted. Require 3,000 actual source intervals; early terminations may require more than five episodes. Verify the 32 MiB input / 96 MiB recording caps and the existing 120-second inference timeout before generation.
- **Choir implementation and capacity.** Labelled episode concatenation is implemented through `--compose-episodes`; the single-episode default is preserved. Composition limits are 2 GiB source, 256 KiB metadata and 16 MiB output. Existing synthetic tests cover exact 120-second PCM and prefix provenance; actual full-size lab material still needs verification. Insufficient telemetry must fail without padding or automatic retries.
- **Choir loudness.** The current WAV peaks at −31.1 dBFS (RMS about −38.6 dBFS). The fixed mapping has no normalisation, so the listening-level policy for milestone 4 should take this into account.
