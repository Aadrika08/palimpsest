# Held public manual episode v1 (milestone 1)

**Goal:** run one bounded public manual CPU episode inside the held, import-guarded
worker and prove four things about it:

- it records with a registered tick-0 snapshot;
- a fresh owner replays it tick by tick against a comparison frozen before execution;
- it exports portable source and replay bundles;
- independent checks accept the result.

This proves the engineering, operator and renderer route only. A natural task
failure is acceptable. It proves no controller capability, study result or
release gate.

**Prerequisite (met):** runtime14 accepted the held CPU four-import route
(`research/puck-cpu-held-qualification-14`, `4fd4f68`). Offline census:
`research/public-episode-census-v1`.

## User decisions (2026-10-17)

1. **Two workers.** Worker A records the source episode. Worker B is a fresh-owner
   process that replays and exports it. Each worker has a 360s clock; the whole
   allocation has about 720/735/750s.
2. **About 48 ticks.** The file and output limits stay at 16 MiB per file and
   64 MiB in total.
3. **Held entries.** If the projected count would exceed 39,500, bind consumed
   history through committed evidence-index hashes instead of every file. The
   40,000 ceiling stays.
4. **One stdlib exception.** Allow exactly `_sysconfigdata__linux_x86_64-linux-gnu`,
   bound to the pinned interpreter file bytes. scipy requests it, and it is missing
   from `sys.stdlib_module_names`.

## Design

- **Construction.** Use the reviewed direct public constructor (`52a8f5d`,
  cherry-picked) with no training runner. Profile `reproduction`, texture
  `checker`, controller `manual`, seed 7, CPU.
- **Diagnostics.** Add an explicit, type-checked `diagnostics=` argument to
  `Engine.open` and `replay_run`, filled from `held_provenance.py`.
  - That module derives the record only from the authenticated registration:
    the interpreter pin, upstream file hashes and registered distributions.
  - It uses no subprocesses, `importlib.metadata` or `platform`.
  - Monkeypatching `doctor` instead would trip the function-binding guard.
- **No child processes.** Add an audit hook that refuses process creation.
  Freeze these environment values:
  - `PYGLFW_LIBRARY`, set to the staged path
  - `MESA_SHADER_CACHE_DISABLE=true`
  - `PYGAME_HIDE_SUPPORT_PROMPT=hide` (gymnasium sets it, and the guard requires an
    unchanged environment)
  - `__EGL_VENDOR_LIBRARY_FILENAMES`, pointing at a staged Mesa JSON
- **Imports.** No torchvision. The new episode descriptor drops torchvision from
  the expected versions.
- **Renderer.** Check the renderer in-process on the renderer's current EGL
  context:
  - expected strings: Mesa, llvmpipe, OpenGL 4.6, Mesa 26.2.2;
  - EGL backend and mujoco 3.3.6;
  - every frame is `uint8[128,128,3]` and not constant.

## Stages

Each source stage is test-first and gated by an independent review. Each one-shot
stage gets independent controls review, fresh admission, a single invocation and
outcome audits, and its outputs are never overwritten or retried.

1. **Source A:** the constructor seam, `held_provenance.py`, and `diagnostics=` in
   `engine.py` and `replay.py`.
2. **Source B:**
   - **Bootstrap:** registration v4, the episode descriptor
     (`puck-held-public-episode-v1`, phase `source` or `replay`), the exact
     `_sysconfigdata` exception, and the process-creation audit hook.
   - **New modules and scripts:** the entry module `src/palimpsest/puck_held_episode.py`,
     the parent `scripts/run_puck_cpu_held_episode.py`, the auditor
     `scripts/audit_puck_cpu_held_episode.py`, the stdlib bundle validator
     `scripts/validate_palimpsest_bundle.py`, and the characterization-04 scripts.
   - **Registration and namespace changes:** native metadata v6 support (a leaf limit
     of at least 256 MiB, because `libLLVM` is 171 MB), a read-only source-run mount
     for worker B, and upstream/src module naming.
3. **Diagnostic guarded rehearsal.** No allocation, scratch tmpfs only, and a
   registration built from the census. It measures time, memory and entries, and
   surfaces guard refusals.
4. **Native metadata v6:** about 55 host files covering GLVND, EGL, Mesa,
   llvmpipe, LLVM and glfw.
5. **Characterization-04 (one-shot)** plus an independent audit. It observes the
   real source, replay and export closure, which yields import-profile
   candidate 02.
6. **Preparation04, allocation 15 (one-shot)** plus an independent audit.
7. **Episode allocation 16 controls** (`puck-cpu-held-episode-allocation-v16`),
   then re-measure entries.
8. **Admission16** (data only), then the pre-observer guard.
9. **One invocation:** worker A, then worker B.
10. **Audits:** outcome, byte, bundle and cleanup audits, then the outcome review
    and archive.

## Acceptance (to freeze before execution)

- **Episode:** seed 7, about 48 ticks, with actions set at tick 0 and tick N/2 and
  one step per tick. The manifest must be `completed` with recorded ticks equal to N.
- **Provenance and snapshot:** the diagnostics event equals the precomputed held
  provenance, and the environment event equals the pins. There is exactly one
  initial snapshot at tick 0, and its hash matches the index and the event.
- **Renderer:** the criteria in the Design section.
- **Replay:** status `passed`, compared ticks equal N, compared events equal the
  source, and no divergence. The comparison block equals the frozen one. The
  auditor independently re-checks cameras and integers exactly and floats within
  1e-6.
- **Bundles:** format `palimpsest-bundle-v1`, stored uncompressed (`ZIP_STORED`).
  The exact member set, sizes and SHA256s must match the on-disk runs, with no
  path traversal, valid CRCs, and every file within the limit.
- **Process and file hygiene:** zero process-creation attempts and no survivors.
  The output directory has exactly the expected members. Staged and native
  originals and the baseline are unchanged. Each worker finishes in under 360s.

## Risks

- scipy's Cython modules may extend the shared `_cython_3_0_12` module, which the
  q4 cache/binding checks guard. Stage 3 will show this.
- The held-entry margin is thin.
- Timing is about 300s ±25% (an estimate). Stage 3 measures it.
- Every one-shot stage is bound to the boot it runs on. A reboot between
  preparation04 and the episode forces a new preparation.
