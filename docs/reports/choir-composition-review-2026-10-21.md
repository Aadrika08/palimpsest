# Choir composition review — 21 October 2026

Reviewed source: `45f1e5d`, branch `feat/choir-episode-composition`.

## Result

No exporter correctness defect found in the source review and checks performed.
The browser encounter is not yet integrated with new 120-second compositions.

A fresh synthetic recording contained 6,000 intervals across ten episodes, four
128×128 RGB camera arrays per interval, and fixed population statistics. This is
not FLYNN execution or scientific/artistic acceptance. The script ran under a
180-second outer timeout and completed normally.

- Source: **1,181,417,589 bytes** (about 1.10 GiB), above the historical 512 MiB cap.
- WAV: **11,597,338 bytes**; metadata **77,285 bytes**, within the new bounds.
- Audio: **5,760,000 samples**, 48 kHz mono, exactly **120 seconds**.
- Source construction: **7.11 s**; export: **3.95 s**.
- Peak process RSS: **72,612 KiB** (about 71 MiB), including fixture construction,
  export and output inspection. This is one process measurement, not a general
  peak-memory bound. The newly written source was likely in the filesystem cache.
- Verified PCM hash, ten episode segments, final output sample endpoint and no
  partial final episode. Existing tests separately cover final-prefix selection.
- Focused and shared-reader tests: **58 passed**, 14 dependency deprecation
  warnings, **8.86 s**. `git diff --check` passed before this report.

[Receipts and reproducible check script](choir-composition-review-2026-10-21/result.json)
are retained beside this report. The 1.10 GiB synthetic source and WAV remain in
ignored `runs/choir-review-2026-10-21/`; they are not production artwork material.
The check script uses exclusive WAV creation and must use fresh paths for another
invocation; this review does not instruct repeating an existing allocation.

## Remaining work

1. `scripts/prepare_artwork_encounter.py:153` and `:164` still describe the pinned
   historical 25.34-second artifact. A new encounter must derive duration from the
   new WAV and expose version-2 episode boundaries and any final prefix. Do not
   substitute the new WAV into that old pack with unchanged captions.
2. Register a bounded source-generation run using lab population telemetry;
   collect actual FLYNN records. Ordinary `evaluate` records omit those summaries.
3. Check actual recording size, provenance, cleanup and audio content; run the
   new encounter's full-duration browser/audio acceptance.

Source byte caps, complete-record checksum/aggregate validation, unused-tail
validation, exclusive publication and partial-write cleanup remain in place.
The unchanged single-episode path retains version-1 metadata and its old bounds.
No real model inference, listening assessment, browser session or merge occurred.
