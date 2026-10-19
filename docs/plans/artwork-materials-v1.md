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

## First full launch failed; fixed and rehearsed again

**What failed.** At 14:38:21Z the operator launched `palimpsest-art-all` on `8faab2b`. It failed after 464 s, in the `manual` stage. The receipt says `OwnerError: idempotency limit reached; a new session is required`. The run was `95485a8806c8445889532f67e993dd36`, with 2,000 ticks recorded across 4 finished episodes (600, 255, 526 and 600 ticks).

**Why.** The client sent `set_action` plus `step` for every tick, so it used up the engine's per-run idempotency store after 2,048 ticks. That store holds at most 4,096 commands (`Engine.MAX_IDS`). It is carried in snapshots, so the cap is deliberate and it stays. Two episodes also ended early because the rover stalled.

**What changed** (`e297968` failing test, `4c8a02e` fix):
- The manual schedule now holds each action for 25 ticks (0.5 s), and `set_action` is sent only when the action changes. 3,000 ticks then take about 3,125 commands.
- FLYNN free-runs each episode to its own end. It has no inputs, so every tick is still deterministic, and it uses about 2 commands per episode.
- Both stages run consecutive episodes until a declared total: 3,000 manual ticks (enough for 600 Afterimage frames) and 6,000 FLYNN ticks (the 120 s Choir). `--episodes` is now only an upper bound.
- A fake owner with the same 4,096 cap reproduces the failure, and the new tests pass against it.
- The failed partial output (392 MB) was removed. Its receipt and progress files are kept in `docs/reports/artwork-materials-v1/failed-launch-8faab2b/`.

**Rehearsal past the old failure point** (`--scale cap`, detached `palimpsest-art-all-cap-rehearsal`). It completed in 370.7 s:

| Stage | Result | Time |
| --- | --- | --- |
| manual | 2,400 ticks in 5 episodes (600, 174 stalled, 600, 600, 426); branch of 300 ticks | 227 s |
| flynn | 4,312 ticks in 14 episodes, 13 ending at the goal | 119 s |
| materials | 480 frames, 84 s Choir | 24.5 s |

The browser harness passed 4 of 4 on its 15.8 MB pack, including all 480 frames by keyboard and a full 84 s play. Evidence is in `docs/reports/artwork-materials-v1/cap-rehearsal/`.

**Needs the user's confirmation.** FLYNN usually reaches the goal in 200–550 ticks, so "10 consecutive 600-tick episodes" cannot happen in this scenario. The generator records about 20 consecutive, goal-ended episodes up to 6,000 ticks, sonifies them in order with marked boundaries, and cuts at 120 s. Every episode's length and ending is in the receipt and the WAV metadata.

## Full run (operator-launched; command in `docs/reports/artwork-materials-v1/full-commands.txt`)

| Stage | Expected time | Expected size |
| --- | --- | --- |
| manual (3,000 ticks plus a 300-tick branch) | about 5 min | about 0.63 GB |
| flynn (6,000–6,600 ticks) | about 3 min | at most about 1.36 GB |
| materials (600 frames, 120 s Choir) | about 0.5 min | about 0.17 GB |
| **Total** | **about 9 min** | **about 2.2 GB** |

**Disk.** Nothing is deleted during the run, so the peak is about 2.2 GB. The project disk had 9.94 GB free at the last check, which leaves about 7.7 GB (7.2 GiB) afterwards. That keeps the required 4 GiB free (`--min-free-bytes 4294967296`).

## Still open

- The full-size generation.
- Rebuilding and committing the pack's evidence: the pack ZIP's size and hash, plus a harness run against it.
- Declared-duration sessions for each mode.
- Milestone 4: listening level, the independent operator, and audience, custodian and rights.
- Episode lengths: a FLYNN or manual episode can end early if the goal is reached. The receipts record each episode's actual length and ending. The Choir is then shorter than 120 s, and the declaration and harness report the actual length rather than padding it.
