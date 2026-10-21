# Artwork input contract plan

> **For agentic workers:** Use superpowers:executing-plans for subsequent implementation. This document plans blocker 1 only; it does not authorize material-generation runs.

**Goal:** Fix the Afterimage eye selection and Choir episode semantics before preparing longer artwork material.

**Architecture:** Reuse recorded camera arrays, the existing Afterimage model mapping, and the fixed Choir population-to-audio mapping. Use explicit episode composition while retaining simulation episode limits.

**Tech Stack:** Existing Python/NumPy record readers, JSON provenance, PCM WAV and browser encounter.

**Spec:** [Artwork acceptance v1](../../plans/artwork-acceptance-v1.md).

## Accepted decisions

Accepted by the user on 21 October 2026. Blocker 1 is closed: the input contract is fixed; implementation and material-generation qualification remain pending.

### Afterimage: left eye, 600 frames

- Select the recorded left camera only, before inspecting artistic results. Do not alternate eyes, combine images or select frames by response.
- Select every fifth control interval from a declared chronological source sequence at 50 Hz, starting at sequence index zero: indices 0, 5, ..., 2995. Require 3,000 complete source intervals, representing 60 simulated seconds. Preserve actual observation timing and each source run/episode/tick in a separate provenance index.
- The presentation shows 600 samples at 10 fps over 60 seconds. The sample timestamps span 59.9 seconds; this is consistent with 60 seconds of sample-and-hold presentation. For multiple episodes, label the presentation clock as concatenated source time and retain native episode timestamps separately.
- Keep the existing artificial interface: duplicate each selected image into both model camera inputs, fixed other sensors, `male-original`, CPU, seed 0, one initial hidden-state reset followed by state carry through all 600 frames. Source episode transitions do not reset this separately authored portrait model.
- Label source controller and portrait controller separately: a manual lab recording is simulated robot camera footage processed by the fixed male model, not footage produced by that model driving.
- Reject wrong shape/dtype, missing frames, gaps inside an episode or mismatched hashes. Do not resize, pad, repeat or interpolate frames. Existing input remains uint8 `(600, 128, 128, 3)`.

### Choir: ordered episode composition, 6,000 intervals

- Use chronologically ordered episodes from one declared public FLYNN CPU recording with unchanged model/profile/population identities and a 0.02-second control interval.
- Map exactly the first 6,000 genuine intervals to 120 seconds at 48 kHz: 960 audio samples per interval, 5,760,000 samples total. End at an interval boundary; declare any final-episode prefix explicitly. Do not silently include further recorded intervals.
- Early goal/termination may shorten an episode. Ten episodes are sufficient only if each supplies 600 intervals. A later generation protocol must bound episode count and runtime; insufficient telemetry is a failure, not permission to loop or retry automatically.
- Preserve native episode resets and mark every boundary in provenance and presentation. Describe the result as a composition of episodes, not one uninterrupted trajectory. Omit loading/paused wall time explicitly.
- Preserve existing signed population means, three fixed voices, gains, PCM rounding and 48 kHz mono format. Use a continuous output carrier phase; do not normalize, crossfade, insert silence or smooth episode transitions. Audible discontinuities remain reviewable.
- Keep existing single-episode exports backward compatible. A subsequent implementation adds explicit multi-episode selection rather than changing the default.

## Scope and files

Blocker 1 closes with a reviewed contract and an update to the current artwork plan. No runtime code needs changing to make these decisions concrete.

- This document: accepted selection, timing and failure rules.
- `docs/plans/artwork-acceptance-v1.md`: records the accepted contract and links here; retain historical decisions.
- Later implementation scope: `src/palimpsest/sonification.py`, its CLI caller in `src/palimpsest/cli.py`, `tests/test_sonification.py`, `docs/artwork-mappings.md`, and the artwork encounter consumer/tests if new episode metadata requires display changes.
- Later Afterimage preparation must reuse `src/palimpsest/afterimage.py`'s strict stimulus schema; put run/episode/tick selection provenance in a companion index rather than injecting unrecognized fields into that schema. Identify the actual camera field through the recording schema before implementing extraction.
- Historical `prepare_artwork_material_v2.py` and `v3.py` controls remain evidence of their original allocations; they are not fresh generation commands.

## Tasks to close blocker 1

- [x] User accepted the left-eye and episode-composition choices, including reset labels and the single-eye artificial mapping (21 October 2026).
- [x] Record accepted choices in the current artwork plan. This resolves selection semantics only.

## Follow-up before generation

- [ ] Carry the feasibility checks below into the next material-preparation plan before registering any actual generation.

## Feasibility checks required before generation

1. **Afterimage capacity:** 600 frames require 29,491,200 raw image bytes plus the NPY header, within the existing 32 MiB input cap. Check actual record overhead against 96 MiB. The fixed inference supervisor allows 120 seconds including loading; 600-frame completion within that wall bound is unmeasured. Any changed bound needs a prospective amendment.
2. **Choir input capacity:** the current reader validates the entire recording and caps it at 512 MiB and 120 simulated seconds. Full camera/neural records may exceed the byte cap. Estimate actual schema/chunk bytes before choosing a source layout. Do not silently strip authoritative arrays or raise limits; any bounded reader/limit change belongs in the implementation plan.
3. **Choir output capacity:** 120 seconds of mono int16 PCM needs 11,520,000 bytes, before headers/provenance, within the 16 MiB output cap. Check the 64 KiB embedded-metadata cap against 6,001 sample boundaries, source hashes and episode ranges.
4. **Timestamp and identity checks:** prove exact source-to-frame/sample mapping across early terminations, episode resets and a final prefix. Reject reordered, duplicated, missing or corrupt inputs and model/population changes.
5. **Portability:** pin required source files and extraction instructions. A local-only archive cannot be the sole reproducibility path for the new material.

## Later implementation acceptance

- Synthetic tests verify left-eye extraction, source identity and sample count without model inference.
- Audio tests verify exact PCM equivalence to the fixed mapping, 5,760,000 samples, labelled boundaries and unchanged single-episode behavior.
- Negative tests cover insufficient source duration, discontinuities within episodes, corrupt hashes, incompatible populations, byte/metadata limits and existing output paths.
- Actual inference timing, audio listening, full-duration browser sessions and independent operator review are subsequent gates, not evidence supplied by this plan.

## Exit

Blocker 1 is resolved: both choices and their timing/provenance semantics are accepted and reflected in the current artwork plan. Source-generation feasibility may still block later work; resolving a contract is not a claim that 600-frame inference or 120-second sonification already works.
