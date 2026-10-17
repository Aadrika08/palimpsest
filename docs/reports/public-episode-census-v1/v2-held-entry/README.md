# Census v2: held episode entry with process creation refused (diagnostic only)

Source `65b19fa` (`research/public-held-episode-v1`): `puck_held_episode.run()`, with
held provenance passed as `diagnostics=`. The run used a stand-in admission object,
so no guard was active. It ran in the same read-only bwrap sandbox, with
`PATH=/nonexistent` and these settings:

- `MESA_SHADER_CACHE_DISABLE=true`
- `PYGAME_HIDE_SUPPORT_PROMPT=hide`
- `PYGLFW_LIBRARY` set
- `__EGL_VENDOR_LIBRARY_FILENAMES` pointing at a scratch Mesa JSON

A refusing audit hook was active the whole time. This is diagnostic evidence only,
not admission.

## Source phase

- 48/48 ticks recorded, with zero process-creation attempts.
- Renderer: Mesa llvmpipe, OpenGL 4.6 Mesa 26.2.2, EGL 1.5.
- 6.6s, 1,500 modules, 487 MiB RSS.

## Replay (separate fresh process)

- Status passed: 48 ticks and 100 events compared, no divergence.
- 6.3s, 593 MiB RSS.

## Imports and native libraries

- No torchvision and no `torch._dynamo` were loaded.
- `_sysconfigdata__linux_x86_64-linux-gnu` was requested, as the v4 exception expects.
- 21 absent names were requested: 11 of the v5 names plus the 10 census names.
- 49 host native files (281 MB) were mapped, the same in both processes
  (`out/h1/native-libraries.json`). This list is the input for native metadata v6.

## Bundles

About 10.1 MB each, roughly 210 KB per tick. Bundle zips and recordings were not retained.

The held site metadata hash is unchanged (`fdeb7899…`).
