# Stage-3 guarded rehearsal 07 (diagnostic only, not an allocation)

The rehearsal ran at `cbda0d9` against the real held site. Its stage and outputs
were scratch-only, under the allocation-16 limits: 600s per worker (a user
decision), 2 GiB RSS and 64 MiB output.

## Results

**Before the guarded phases:**

- Characterization-04 source and replay, unguarded: 10.5s and 9.6s.
- Stager: 28.5s, holding 27,286 files (1.59 GB).

**Guarded source phase: completed in 333.1s, peak RSS 904 MB.**

- 48/48 ticks.
- Renderer: Mesa llvmpipe, EGL.
- Bundle: 10,085,155 bytes.

**Guarded replay phase (fresh worker): passed in 378.8s, peak RSS 954 MB.**

- 48 ticks and 100 events compared, with no divergence.
- Bundle: 10,092,230 bytes.

**Both phases:**

- Zero process-creation attempts.
- No guard refusals or poison.
- Denied imports were exactly the 21 declared absences.
- Provenance was equal across phases.

**Late cache key and module aliases:**

- The late delegate `fused_cython_function` was accepted. It is attributed to the
  module execution of `scipy.linalg._cythonized_array_utils`.
- Module aliases `_csparsetools` and `_ni_label` were accepted.

**Allocation-16 checks:** both the parent receipt checks and the episode auditor's
internal checks passed on the rehearsal outputs.

**Headroom and cost:** the slowest worker used 378.8s of 600s. Guard custody checks
take about 75% of each worker's time.

## Earlier rehearsals

Rehearsals 1–6 surfaced five guard and derivation defects; each was fixed before
this run:

- shared-cache key attribution and late-key pending
- export paths across ordinary modules, plus `module_aliases`
- v4 package `__path__`
- v4 directory `locate_file`
- static `$ORIGIN` origins

Rehearsal 6 also showed that replay exceeds a 360s clock.
