# Real FLYNN Choir material — 22 October 2026

**Completed:** one bounded public CPU FLYNN recording, independent PCM audit,
120-second offline export, local encounter package and real-audio browser check.
Source commit: `a8f7ac2`. No retry or replacement controller was used.

## Recording and export

- Reproduction/checker, seeds **0–17** in order, one FLYNN policy load.
- **6,004 control intervals / 18 episodes**, with **17 goals and one time limit**.
  These are retained artwork-source outcomes, not a navigation benchmark or a
  topology/memory benefit claim.
- Source bytes: **1,298,650,530** (about 1.21 GiB), below the 2 GiB cap.
- Recording supervisor: exit 0, **119.843 seconds**, including model loading.
- Export supervisor: exit 0, **5.938 seconds**. Both recorded process identities
  and process groups were absent after shutdown; the writer lease was released.
- Audio selects exactly the first **6,000 intervals / 5,760,000 samples / 120 s**.
  All 6,004 intervals were validated. The final four intervals are excluded and
  the final episode prefix is labelled. No normalization or crossfade was applied.
- All selected PCM bytes equal an independent recomputation from population
  telemetry. All source files match the WAV's hashes. Frozen source pins match
  before and after the run.
- Peak **−31.813 dBFS**, RMS **−40.088 dBFS**. Listening level and artistic usefulness
  require human review.

## Encounter and browser

The new local encounter updates Choir only; the other five modes retain historical
material and limits, including the short Afterimage. Its README explicitly records
that distinction. Original archives were preserved.

Chromium loaded the real WAV with other network requests blocked. Checks passed:
120-second caption; 18 episode rows; final-prefix label; no autoplay; keyboard play
and stop; 1440/390 px layouts without document overflow; full playback ending at
**120 seconds**, with **120.132 seconds** measured wall time; zero page errors and
unexpected requests. Screenshots were inspected; the mobile table scrolls within
its container. This is software/presentation verification, not human listening or
independent-operator acceptance.

## Artifacts and evidence

Local output root: `runs/choir-material-2026-10-22-v1/`.

- `choir.wav`: **11,614,700 bytes**.
- `encounter/index.html`: offline six-mode review with the new Choir.
- `palimpsest-choir-encounter-2026-10-22.zip`: **22,718,753 bytes**, byte-checked after
  ZIP readback; SHA-256 `16f2dfd7fd30d11cff13f5c564780927e1400626f55be37d2f9b3fa2fe85c81b`.
- Full source recording remains local under its registered UUID. The derivative
  ZIP excludes that 1.21 GiB recording. Public assets and the committed runner
  provide a rebuild recipe; an independent rerun is not promised byte-identical.

[Retained evidence index](choir-material-2026-10-22/index.json) binds registration,
supervisor/cleanup receipts, source manifest, audit, browser results, screenshots
and artifact hashes. Standalone audit/package/browser scripts are retained for
review, not instructions to overwrite or repeat the consumed allocation.

The recording driver passed three synthetic contract tests before execution;
Torch/Torchvision/MuJoCo and the upstream runner passed import preflight. No new
full-suite regression is claimed for this material run. Human acceptance, fresh
Afterimage material, full six-mode acceptance and final release remain open.
