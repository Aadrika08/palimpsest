# Choir encounter integration — 21 October 2026

The encounter generator now derives its Choir caption and playback duration from
validated PCM and embedded provenance. Version-2 compositions display an
accessible episode table with playback seconds, inclusive source ticks and a
final-prefix notice. Existing audio controls, no-autoplay behavior and the pinned
historical archive remain unchanged.

Validation rejects malformed/truncated WAVs, duplicate chunks, PCM hash mismatch,
unsupported format/voices, inconsistent duration and noncontiguous episode/sample
ranges before using metadata in HTML. Metadata-derived text is restricted to
validated numeric ranges and known population names.

## Checks performed

- Python suites for encounter, sonification, Afterimage, artifacts and records:
  **70 passed**, 15 expected fixture/dependency warnings, 7.22 s.
- UI `npm run typecheck`: passed with the pinned Node 24.21.0 runtime.
- Chromium `tests/choir-composition.spec.ts`: **1 passed**, about two minutes.
  Generated HTML used synthetic 120-second PCM and historical visual derivatives.
  Verified ten visible episode ranges, prefix notice, no autoplay, 390 px viewport
  without document overflow, keyboard play/stop, complete playback ending at 120
  seconds (wall time within two seconds), and no unexpected network requests.
- Historical pinned derivative archive was hash-validated and generated with the
  correct 25.34-second Choir caption.
- The actual sonifier output retained from the previous synthetic 1.10 GiB
  capacity check was accepted: 120 seconds, ten segments, no final prefix.
- `git diff --check`: passed.

`npm run test:artwork` now includes the new composition browser test alongside the
existing historical-pack tests. Historical experiment allocations and published
ZIP bytes were not rerun or replaced.

This completes presentation support for composition metadata. Real FLYNN source
generation, packaging new material, listening/artistic review and independent
operator acceptance remain open. The browser test's silent synthetic PCM checks
transport/timing/controls, not audible quality. No merge was performed.
