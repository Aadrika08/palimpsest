# Census v3: episode auditor and bundle validator on a real recording (diagnostic only)

This checks the auditor and bundle validator, built on synthetic data, against a
real recorded episode. It is diagnostic evidence only, not admission.

## Setup

- **Source:** `ae9bd81`, whose episode path is byte-identical to `65b19fa`.
- **Runtime:** the real `puck_held_episode.run`, run in the held path layout with
  the auditor's exact `ENVIRONMENT`. The source phase recorded 48/48 ticks
  (llvmpipe), then a fresh process ran the replay, which passed (48 ticks, 100
  events). There were zero process-creation attempts.

## Results

1. **Bundle validator.** `validate_palimpsest_bundle.py` passes on both bundles,
   checked alone and against their run directories.
2. **Episode auditor.** Its checks pass on the real directories: entry,
   payload members, recording, snapshot identity, provenance equality, compare,
   and replay report. Specifically:
   - the run_id matches the directory name;
   - event counts are 107 and 110;
   - two chunks per run (32 and 16 ticks), in one episode;
   - four cameras, each `uint8[128,128,3]`, none constant;
   - the snapshot index matches its registration event;
   - every physical field is bitwise equal between source and replay, so the
     1e-6 tolerance was never used.
3. **npz reader.** The stdlib npz/npy reader matches numpy byte for byte on all
   chunks.

## Latent assumptions

These hold today but would break if the episode changed:

- Disabling an eye zero-fills its camera, which trips the constant-frame check.
- A reset or a multi-episode schedule trips the single-episode check.

Run directories and bundles were not retained; sizes and hashes are in `out/`.
The held site hash is unchanged.
