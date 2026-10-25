# Afterimage material allocation — 22 October 2026

Execute the accepted [input contract](../superpowers/plans/2026-10-21-artwork-input-contract.md).
User authorized generation and encounter integration in this session.

1. Record one fresh public Engine manual-controller source, reproduction/checker,
   CPU, initial seed 0; fixed manual action `[1, 0.5]` per episode through queued
   `set_action`. This is scripted steering, not human joystick input. Retain
   natural terminal outcomes and reset with consecutive seeds. Stop after the
   episode crossing 3,000 intervals; ceilings 3,600 intervals, 64 episodes,
   300 wall seconds and 1 GiB source. No retry or alternate input selection.
2. Validate complete source including any unused tail. Select effective
   `cam_left` at indices 0,5,...,2995. Retain native run/episode/tick/time, eye mask,
   frame hashes and source file hashes in a separate provenance index. All 600
   images must be uint8 128×128×3, unmodified. NPY payload 29,491,200 bytes plus
   header fits 32 MiB. Duplicated model camera payload 58,982,400 bytes plus
   record overhead must fit the existing 96 MiB cap.
3. Invoke existing public Afterimage CLI once: male-original, CPU, seed 0,
   one reset then carry across 600 frames. Keep its 120-second supervisor.
   Source presentation timestamps 0–59.9 s at 10 fps; model index 12 s.
4. Render and independently check every source frame, response and SVG point.
   Package this portrait with the existing actual Choir derivative and four
   historical modes. Pin the Choir pack; preserve historical evidence.
5. Add user-started, finite 60-second sample-and-hold presentation, stop/reset,
   manual inspection, fixed axes and source labels. No smoothing or loops.
   Check keyboard, mobile layout, no automatic start, and actual full duration.

Use fresh `runs/afterimage-material-2026-10-22-v1`; 2 GiB aggregate / 2 GiB
free-space floor, existing writer lease and bounded subprocess helpers. Pin
committed code before generation. Store raw source locally, portable derivative
ZIP locally, and compact receipts with scripts in docs/reports. A public recipe
and source hashes accompany the pack; reruns need not reproduce identical bytes.
Do not infer human/artistic acceptance or six-mode duration qualification.

## Execution ledger

- Preflight: clean feature branch c3d69b0; 9.3 GiB free. Required assets present.
- Ruling: constant scripted steering uses the manual API without implying human
  operation; this makes input selection prospective and repeatable.
- Shared interfaces: extraction writes the existing strict stimulus schema and
  a separate source index; encounter uses SVG alignment and source provenance.
- Tasks: selection/driver tests, source allocation, inference/render, encounter
  playback and evidence review.
