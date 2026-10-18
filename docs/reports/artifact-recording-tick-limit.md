# Long recording episodes admitted by the shared artifact reader

7 October 2026. Software fix `c2dcd4b`, stacked on the preserved
[failed material preparation](artwork-review-development-material.md), `ba8b31e`.
The shared reader no longer rejects every tick identity at or above 600.
This fixes software admission; the longer retained artwork sources have not been
exported under the new code. No artwork or research qualification is claimed.

`records.iter_ticks` permits nonnegative, nonzero starting identities and requires
contiguous rows within an episode. Continued recordings retain those identities.
The shared loader stores tick values rather than allocating by their magnitude.
Its 600 guard contradicted that recording contract and blocked valid long episodes
and short continuations. The fix deletes those two lines, without adding another
identity ceiling. Existing bounds remain: 100,000 total rows, 4,096 chunks, 16 GiB
source bytes, bounded manifests/events, numeric schemas, chunk checksums, terminal
counts, world geometry and mutation fingerprints. Callers retain their narrower
budgets, including sonification's 512 MiB source/120-second duration limits.

Three synthetic regressions first failed at the original 600 guard. The changed
tests then passed with the focused artifact/comparison/sonification/recording/
handoff/CLI checks: **63 passed, 14 warnings in 1.44 seconds**. They cover a
601-row episode's tick-600 playback, 602-point SVG and JSON comparison; two rows
starting at 100,000 with original identities preserved; row-count rejection
before output publication; and fractional-sample WAV timing from tick 600.
These are deliberately synthetic recordings, not new model or task evidence.

The first broader run ended with **18 failed, 924 passed, 26 skipped, 16 warnings,
18 errors in 94.77 seconds**: this new worktree lacked its pinned upstream source.
Its [exact failed/error names and terminal summary](artifact-recording-tick-limit-evidence/initial-suite-summary.txt)
are retained; the full original log remains locally ignored. The failures named
missing mapping/XML/Python files, missing `core`, or missing source inventory.
An unchanged local upstream checkout was cloned without network access, then
checked out at the declared `8d964599119b420de67ee259434d273651a1a76d` gitlink.
No project or upstream source change was needed for that setup correction.

One further broader run passed: **962 passed, 24 skipped, 39 warnings in
92.64 seconds**. [Complete output](artifact-recording-tick-limit-evidence/full-suite-pinned-upstream.txt)
retains the warnings. Actual upstream/EGL and reserved model checks stayed
opted out; their skips prove no capability. The normal suite includes small
Torch/MuJoCo software fixtures, distinct from fresh asset-backed qualification.
Each broader run had a 240-second TERM deadline and five-second KILL grace;
no further broader retries were made. The focused run had a 60-second bound.
Independent source/diff review found no issues; `git diff --check` passed.

Verification used the existing Python 3.11 environment, no new dependency:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:tests \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
PALIMPSEST_SIMULATION_TESTS=0 PALIMPSEST_MALE_TORCH_CHECKS=0 \
timeout --signal=TERM --kill-after=5s 240s \
  /home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python \
  -B -m pytest -q -p no:cacheprovider
```

The original failed producer remains clean at `ba8b31e`; its consumed marker,
failed receipt and absent derivatives remain unchanged. Main remains unchanged.
No source truncation, alternate recording, material-pass retry, held-out access
or human acceptance occurred. A separately named, prospectively allocated
material pass requires an explicit owner decision under the original stopping
rule. The proposal is to retain the verified ZIP and 98-source selection, allow
one fresh relocation and exactly three existing CLI exports, reuse the other
three pinned SVGs, and verify one six-mode review ZIP. Keep the original
300-second aggregate/120-second export-child/2 GiB phase bounds, zero corrective
attempts and stop on any admission/storage/hash/deadline/cleanup failure.
The ten-minute review guide must label the old half-second Afterimage as
insufficient for assessing sustained material. Human aesthetics, accessibility,
independent operation, restore/memory and learned capabilities remain open.
