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

The [accepted input contract](../superpowers/plans/2026-10-21-artwork-input-contract.md) fixes selection, timestamps, provenance and rejection rules. **Blocker 1 is closed.** Afterimage, Choir and public route/branch material passed their technical checks. All six automated duration checks passed on 22 October, including four concurrent ten-minute static sessions. Human viewing/listening, independent-operator and exhibition acceptance remain pending.

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
2. **Material generation (complete for the declared source requirements; artistic acceptance open).**
   - [Real Choir material and browser check](../reports/choir-material-2026-10-22.md) passed on 22 October: 6,004 actual CPU FLYNN intervals, independently audited 120-second export, local encounter package and full playback. Human listening acceptance remains open.
   - [Afterimage material and browser check](../reports/afterimage-material-2026-10-22.md) passed on 22 October: 3,543 scripted manual-controller intervals, 600 selected left-eye frames, actual male-original inference in 3.73 s, independent mapping audit and all 600 responses displayed in 60.012 s. Human viewing acceptance remains open.
   - [Public route and labelled branch](../reports/route-material-2026-10-22.md) passed on 22 October: FLYNN parent 375 intervals, snapshot at tick 100, sole goal edit and seven-interval branch continuation. All exported coordinates and lineage audited. The short branch and cached-pose refresh offset are explicitly retained; human suitability judgment remains open.
3. **Declared-duration sessions (automated gate passed).** Each mode is held open for its declared time, with an automated record and interruption labelling where relevant.
   - Afterimage's 60-second and Choir's 120-second sessions passed.
   - [Four static sessions](../reports/static-artwork-sessions-2026-10-22.md) each exceeded 600 s with 599 visible/in-view probes, unchanged geometry and screenshots, and zero browser errors or external requests. These ran concurrently in independent headless browsers; they do not count as human viewing.
4. **Milestone 4 (next).** The [agent curatorial review](../reports/artwork-curatorial-review-2026-10-22.md) identified One map's short comparison first. The [new obstacle comparison](../reports/route-obstacle-material-2026-10-22.md) supplies 279 continuation intervals (5.58 s), with a 5.5 s shared window; The [Afterimage source-frame presentation](../reports/afterimage-presentation-2026-10-22.md) pairs all 600 original frames and responses on unchanged axes. A guided encounter follows. Human listening and viewing, the independent operator, and the rights, audience and custodian declarations remain open. Use the [pending human review sheet](artwork-human-review-2026-10-22.md); no human judgments are prefilled.

## Notes and open technical points

The [21 October runtime/capacity check](../reports/artwork-runtime-capacity-2026-10-21.md) passes locked setup, asset validation, EGL rendering and 23 focused synthetic tests. It establishes that the complete Choir source exceeds the original 512 MiB reader cap. The subsequent explicit `--compose-episodes` implementation admits up to 2 GiB / 6,600 source intervals, validates the entire recording, and exports its first 6,000 intervals with version-2 episode provenance. Actual Choir generation and browser playback subsequently passed; human listening acceptance remains pending.

- **Which input archive backs which pack.** The current encounter pack derives from `palimpsest-artwork-inputs-development-v1.zip`, which is 577,207,446 bytes and stays local. GitHub limits files to 100 MB. Its 98-file manifest is committed (`docs/reports/artwork-review-development-evidence/input-manifest.json`), and the harness checks provenance against it. The committed 4.86 MB archive backs the earlier six-mode offline handoff (`docs/artwork-handoff.json`). New material should be built from committed or public-rebuildable inputs.
- **Afterimage feasibility (passed).** The actual NPY is 29,491,328 bytes and portrait record 59,458,069 bytes; inference completed in 3.73 s under the unchanged 120-second supervisor. The report records storage-floor/default deviations and remaining browser coverage limits.
- **Choir implementation and capacity (passed).** Labelled episode concatenation is implemented through `--compose-episodes`; the single-episode default is preserved. Composition limits are 2 GiB source, 256 KiB metadata and 16 MiB output. Synthetic tests and the actual 6,004-interval lab source pass exact 120-second PCM and prefix checks. Insufficient telemetry must fail without padding or automatic retries.
- **Choir loudness.** The actual 22 October WAV peaks at −31.813 dBFS (RMS −40.088 dBFS). The fixed mapping has no normalisation, so the listening-level policy for milestone 4 should take this into account.
