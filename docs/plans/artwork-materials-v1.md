# Artwork materials v1: rebuildable public inputs for the six encounters

This plan follows [artwork acceptance v1](artwork-acceptance-v1.md). Work is on `feat/artwork-materials-v1`, branched from `0b9fb7e`. The generators and a scaled-down rehearsal are done. The full-size generation has **not** been run; the operator launches it detached.

## User decisions (19 October 2026)

1. **Choir:** one FLYNN lab run of 10 consecutive 600-tick episodes, 120 s in total. The episodes are sonified in order, and each boundary between them is marked by a short, declared fade. Every sample still maps to a recorded tick. Gain may only be an explicit declared factor, recorded in the metadata; there is no silent normalization.
2. **Afterimage:** both recorded eyes, as the model sees them, shown side by side. The source is 60 s at 10 fps, taken from consecutive public manual episodes (every 5th tick), with the fixed male model, CPU, seed 0.
3. **Inputs:** new material is built only from committed or publicly rebuildable inputs, each with a rebuild recipe and hashes. The 577 MB development archive stays manifest-only.

## What was built (test-first)

- **Afterimage recorded-pair input** (`src/palimpsest/afterimage.py`). Stimulus schema 2 carries a `T×2×128×128×3` array; each eye reaches its own camera channel. Per-eye hashes, a bounded source declaration and `INTERFACE_PAIR` are recorded and checked again before rendering. The input cap for pairs is 64 MiB. The single-frame v1 interface is unchanged.
- **Multi-episode Choir** (`sonify_episodes`, and `palimpsest sonify --episodes A-B`):
  - consecutive episodes sit on one sample axis;
  - each boundary between episodes gets a declared 20 ms linear fade, out then in;
  - a declared duration cap cuts at a recorded tick and says so in the metadata;
  - the declared gain is recorded and refused if it would clip;
  - the written PCM's peak and RMS (dBFS) are recorded in the `plmp` metadata.
- **Generators** (`scripts/artwork_materials.py`). These drive the real lab owner one tick at a time:
  - `manual`: a fixed public action schedule (`[0.8, 0.6·sin(2π·t·0.02/5)]`), consecutive episodes, a snapshot at tick 300 of the first episode, and a branch labelled as a goal move.
  - `flynn`: one run of consecutive episodes.
  - `materials`: the Afterimage pair stimulus and its bounded record and render; the Borrowed body SVG; the One map comparison; the multi-episode Choir; Atlas and Specimens built from the committed portable archive; and the rebuilt six-mode pack.
  - The pack contains: side-by-side recorded-eye PNGs in the Afterimage inspector, `inputs-manifest.json`, `declaration.json`, `recipe.json` and `checksums.json`.
  - `all` runs the three stages in order in one process under one lock.
  - Every stage writes an atomic `progress.json` heartbeat (at least every 5 s) and a `receipt.json`.
- **Harness.** `npm run test:artwork` accepts `PALIMPSEST_ARTWORK_PACK=<pack.zip>`. For a rebuilt pack it also checks the declared Afterimage frames and seconds, the Choir seconds, the route point counts and the recorded-eye images, alongside the existing provenance, viewport, keyboard and audio checks.

## Rehearsal (scaled down, run detached through `systemd-run --user`)

Settings: 2 episodes of 50 ticks for both the manual run and FLYNN, a branch at tick 20, 20 Afterimage frames, and a 2 s Choir.
- The `all` unit completed in 34.6 s, and every stage receipt is `completed`.
- The harness passed 4 of 4 against the rehearsal pack.
- Evidence: `docs/reports/artwork-materials-v1/rehearsal/`.

Measured costs:
- Manual: about 0.2 MB per tick.
- FLYNN: about 0.22 MB per tick, and about 0.13 s per tick end to end, including the per-tick step round trip.

## Full run (operator-launched; command in `docs/reports/artwork-materials-v1/full-commands.txt`)

Launch the `all` unit. Follow it by reading `~/.cache/artwork-materials-v1/all/progress.json` and each stage's `progress.json`.

| Stage | Expected time | Expected size |
| --- | --- | --- |
| manual (5 × 600 ticks plus a 300-tick branch) | about 3 min | about 0.66 GB |
| flynn (10 × 600 ticks) | about 13–20 min | about 1.3 GB |
| materials (600-frame Afterimage, 120 s Choir, pack) | about 2–4 min | about 0.2 GB |
| **Total** | **about 20–30 min** | **about 2.2 GB** |

The outer timeout is 8 h.

**Disk.** Nothing is deleted during the run, so peak use equals the final outputs. The estimate scales the rehearsal's measured per-tick sizes to the full run:

| Output | Size |
| --- | --- |
| Manual (3,300 ticks × 199,219 B) | 0.66 GB |
| FLYNN (6,000 ticks × 217,560 B) | 1.31 GB |
| Materials | 0.19 GB |
| **Peak total** | **about 2.16 GB (2.0 GiB)** |

Materials break down as 59 MB stimulus, 60 MB Afterimage record, about 20 MB exports, and about 24 MB each for the pack and its ZIP. The only transient extras are chunk temporary files (at most about 6 MB).

The project disk had 10.89 GB free (10.14 GiB) at the last check. That leaves about 8.7 GB (8.1 GiB) after the run, which keeps the required 4 GiB free. The detached commands pass `--min-free-bytes 4294967296`. Before writing, `all` checks free space minus a 2.35 GiB estimate against that floor, and every writer checks the same floor while running.

## Still open

- The full-size generation.
- Rebuilding and committing the pack's evidence: the pack ZIP's size and hash, plus a harness run against it.
- Declared-duration sessions for each mode.
- Milestone 4: listening level, the independent operator, and audience, custodian and rights.
- Episode lengths: a FLYNN or manual episode can end early if the goal is reached. The receipts record each episode's actual length and ending. The Choir is then shorter than 120 s, and the declaration and harness report the actual length rather than padding it.
