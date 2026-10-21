# Artwork runtime and capacity check — 21 October 2026

Scope: fresh-checkout setup and source-derived capacity checks for the accepted
[artwork input contract](../superpowers/plans/2026-10-21-artwork-input-contract.md).
No artwork generation or scientific allocation was invoked.

## Verified setup

- Upstream initialized at `8d964599119b420de67ee259434d273651a1a76d`, clean.
- All seven committed reduced MaleCNS bundle files match manifest sizes/SHA-256.
- Full FLYNN graph archive and checkpoint fetched through the existing asset
  command; both match their pinned sizes/SHA-256. This verifies distributed file
  identity, not original training provenance.
- Initial dependency installation failed extracting Torch into the task cache
  under `/tmp` with `Disk quota exceeded`. The task cache was moved to ignored
  project storage at `runs/setup-artwork-readiness/uv-cache`; setup resumed there.
- Locked environment installed successfully with CPython 3.11.15, simulation/lab extras and dev dependencies.
- `palimpsest assets prepare` passed graph extraction/validation.
- `MUJOCO_GL=egl palimpsest doctor --probe-renderer` exited 0 with `ready: true`; MuJoCo 3.3.6 rendered a 32×32 RGB frame using NVIDIA RTX 4050 EGL. This is a renderer/setup check, not full-model inference qualification.
- Focused existing Afterimage/sonification synthetic tests: **23 passed in 0.65 s**.
- Final disk observation: approximately 18 GiB available; refresh before generation.
- Shell Node is 25.2.1; the UI pins 24.21.0. Browser setup is not verified.

## Capacity findings

These are exact array-size calculations from the current source, not measurements
of generated material. NPZ recording uses uncompressed `ZIP_STORED` arrays.

| Item | Array payload bytes | Existing limit | Result |
| --- | ---: | ---: | --- |
| Afterimage 600 input frames | 29,491,200 | 33,554,432 | Raw input fits, including normal NPY header |
| Afterimage two recorded camera arrays | 58,982,400 | 100,663,296 total record | Camera payload fits; full record and runtime still require verification |
| Choir 6,000 intervals, two cameras only | 589,824,000 | 536,870,912 total source | Exceeds source cap before other arrays/metadata |
| Choir lab source, four camera arrays | 1,179,648,000 | 536,870,912 total source | Exceeds source cap by more than twofold |
| Choir 120-second mono int16 PCM | 11,520,000 | 16,777,216 total output | PCM fits; metadata still needs checking |

The Choir's 6,001 sample boundaries alone consume 46,847 compact JSON bytes.
The 65,536-byte metadata cap must also accommodate file identities, source
provenance and episode ranges; fit is not yet established.

## Required implementation work before generation

1. Choir still selects one episode. Implement explicit ordered composition with
   per-episode provenance and retain the existing default.
2. Resolve source capacity prospectively. The current reader validates and loads
   the entire source, so selecting a prefix does not avoid its byte cap. Account
   for validation memory as well as file size before changing limits. Do not
   discard authoritative camera arrays to make the current reader accept it.
3. Use the lab Engine's population telemetry for Choir. The ordinary `evaluate`
   writer records cameras/actions/neural outputs but no `population_stats`, and
   cannot directly supply this artwork.
4. Verify a complete 600-frame Afterimage record against the existing 96 MiB
   record limit and 120-second supervisor timeout. Raw byte fit does not prove
   inference timing. Select effective `cam_left` and retain source eye-mask state
   so the selected input is not confused with `raw_cam_left`.
5. Prepare finite source-generation registration and portable input custody;
   early episode termination may require more than five/ten episodes.

The accepted artistic choices remain settled. Source composition and capacity
are concrete downstream blockers; no source limits were changed by this check.

## Retained receipts

[Setup receipts](artwork-runtime-capacity-2026-10-21.json) retain the doctor, asset acquisition/preparation and focused-test results. The ignored task cache remains on project disk for reuse; no experiment outputs were deleted. Browser workflows, full-model inference, 600-frame timing and actual artwork generation were not run.
