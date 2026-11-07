# Fresh-environment reproduction v2 — 7 November 2026

Separately labelled operational reproduction. It does not replace the frozen
campaign's incomplete offline unit or the failed 2026-11-05 follow-up; both stay
retained unchanged under `paper/evidence/authority-replay-v1/`.

## What ran

`scripts/verify_offline.py --setup --full-flynn --duration 55` against clean commit
`94c548865bdae90fb38d32a9a8947ab1c8b18d75`, assets
`/home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn` (same as the campaign).

1. Permitted dependency-cache preparation first: a networked `uv sync --locked
   --extra simulation --extra lab` into a disposable scratch venv populated the uv
   cache with the exact `torch==2.9.0` wheel that the 2026-11-05 follow-up lacked.
   The same offline sync had first been reproduced failing on that missing wheel.
   The scratch venv was then deleted.
2. Inside `unshare --user --net` (no network; `network.json`): fresh shared Git clone
   at the commit plus pinned FLYNN submodule, `uv sync --locked --offline`,
   offline `npm ci` and UI build with pinned Node 24.21.0, API smoke, then an actual
   CPU full-FLYNN lab verification (seed 0: capture, save, branch, playback, action
   and policy replay) — `full-flynn/verification.json`, status `passed`.

Result: `report.json` status **passed**; child exit 0; no owned survivors;
runtime source identical before and after.

## Accounting (final lane)

GNU time over the whole command and its waited descendants (`gnu-time.txt`):
user 128.74 s + system 29.66 s = **158.40 CPU-s**, 161.3 s wall, peak RSS
1,536,568 KiB. Charged to the 2 h final lane. Descendants not waited by their
parent would be missing from this census; none were reported surviving.
Raw output (8.0 GB incl. the fresh checkout/venv) stays local, not deleted.

## Scope limits

Same host and operator. Second-machine/operator reproduction remains open.
Not endurance or browser-performance evidence.

## Also retained

`canonical-94c5488.log.gz`: full four-pass canonical suite at the same commit —
7,878 passed, 625 skipped, 0 failed (passes: 7 / 7,809 / 5 / 57). Ordinary tests
are excluded from research CPU accounting. `SHA256SUMS` covers this folder.
