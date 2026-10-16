# Public manual episode: offline import and timing census v1

**Diagnostic only.** This is not admission, runtime qualification or episode
evidence. It sizes the held episode route for milestone 1 before any one-shot
allocation is designed. No release gate changes.

## What ran

- **Source:** this branch's constructor seam (`52a8f5d`, exported with `git archive`).
- **Upstream:** a clean fly-gym clone at `8d96459`.
- **Sandbox:** the same read-only bwrap sandbox as the
  [v2 import contract](../plans/puck-cpu-optional-import-contract-v2.md)
  diagnostics: CPython 3.11.15 `-I -S -B`, the retained held site first on
  `sys.path`, and the qualification environment.
- **Episode:** manual `reproduction` profile, checker texture, seed 7, CPU.
  Twelve ticks with an initial snapshot, normal close, then actions replay and
  SVG and bundle export.
- **Rendering:** used EGL on Mesa llvmpipe and needed no `/dev/dri`.
- **Held site:** metadata hash `fdeb7899…` is unchanged before and after.

**First blocker.** With the exact qualification environment, `Engine.open` fails
in `diagnose`:

- `dependency:palimpsest`: the held site has no palimpsest distribution metadata.
- `upstream`: git is not available on `PATH`.

A scratch dist-info, `PATH=/usr/bin` and the real git clone let the whole path
complete. Replay then matched all 12 ticks and 28 events with no divergence.

## Timings and modules (unguarded)

The whole run took 6.7s and loaded 2,375 modules.

| Phase | Seconds | Modules loaded |
| --- | --- | --- |
| numpy / torch / torchvision / mujoco | 0.11 / 1.38 / 1.96 / 0.10 | 106 / 870 / 990 / 70 |
| palimpsest import | 0.02 | 10 |
| `Engine.open` | 1.04 | 324 |
| 12 ticks | 0.77 | 1 |
| actions replay | 1.22 | 2 |

Peak memory was 742 MiB RSS and 2.8 GiB virtual, with 35 threads (llvmpipe).
The episode does not need Torchvision: without it, 1,415 modules load, and the
hidden names and 21 of the 32 absent names are never requested.

## Import categories against runtime10's registry

- **Needs registration:** 308 unregistered modules that actually execute.
  - scipy 198, gymnasium 54, numpy 46 (pulled in by scipy), `OpenGL.arrays.*` 5,
    glfw 2, farama_notifications 1.
  - Two Cython short-name modules, `_csparsetools` and `_ni_label`.
  - 18 palimpsest modules and 4 fly-gym modules need local-source registration.
- **Needs declared absence:** 10 new names, all absent from the site and all
  caught by their callers:
  - `cffi`, `glfw_preview`
  - `charset_normalizer`, `cython`, `scikits`
  - `scipy._distributor_init_local`
  - `scipy.linalg._cblas`, `_clapack`, `_fblas_64`, `_flapack_64`
- **Hidden:** no new names beyond the existing four.

A v5-semantics rerun (42 absent, 4 hidden) completed with identical results. Its
one refusal was `_sysconfigdata__linux_x86_64-linux-gnu`, requested uncaught at
`scipy/_lib/_testutils.py:43`. That module comes from the standard library but is
not listed in `sys.stdlib_module_names`, so the guard's stdlib rule needs a
reviewed exception or registration.

## Child processes

- Each `Engine.open` runs git 3 times and `nvidia-smi` once (exit 9).
- Each process runs `uname -p` once.
- `import glfw` spawns one `python3.11 -c` child; setting `PYGLFW_LIBRARY` removes it.

## Risks for a held episode allocation

1. **Time.** Applying runtime10's guarded per-module cost to the extra modules
   projects roughly 150–175s with Torchvision. Dropping Torchvision from the
   episode route removes about 990 modules. This is an estimate, not a measurement.
2. **`diagnose` dependencies.** It needs git and palimpsest metadata, and the
   held namespace has neither. It needs a declared policy.
3. **Child processes.** git, uname, `nvidia-smi` and the glfw probe all count
   against `max_processes=3`.
4. **Missed module.** The `_sysconfigdata` stdlib-name gap and the Cython
   short-name modules.
5. **Software rendering.** It needs about 60 host native libraries bound into
   the namespace. Mesa writes a shader cache under `$HOME/.cache`
   (`MESA_SHADER_CACHE_DISABLE` avoids it).

Probe scripts and full JSON outputs are in [the census directory](public-episode-census-v1/).
Recordings, bundle zips and the upstream clone were not retained.
