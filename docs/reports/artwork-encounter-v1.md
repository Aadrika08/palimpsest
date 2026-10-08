# Offline encounter software preparation

8 October 2026. Branch `feat/artwork-encounter-v1`, base
`03659c5c244952d3dd92b7450d5d4d45d3fc5535`. The bounded plan was committed first
as `5d63f1e`. Repo-local Git identity remains Aadrika Maurya
`<aadrikamaurya@gmail.com>`; no global identity was changed.

The new stdlib-only script prepares a local six-mode HTML encounter from the
checksum-pinned PR88 review ZIP. Original derivative bytes remain unchanged.
Native audio controls and an explicit stop button accompany the choir. Afterimage
has manual previous/next inspection, exact prefix coordinates, an accessible full
alignment table and the unchanged full-trace artifact. Fixed scales and coincident
responses are preserved; no playback interpolation or extra frames are invented.

Synthetic software check:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p test_artwork_encounter.py -v
```

Nine tests passed in 0.034 seconds. They cover corrupt/unsafe/missing/duplicate/
nonregular archive members, size/hash mismatch, exact source/model/action/point
alignment, coincident and single-frame boundaries, safe HTML/JSON embedding,
six local targets, output reuse, deadline/free-space/output bounds, byte-preserving
synthetic preparation and retained failure, plus the emitted JavaScript's manual
prefix/previous/next/audio-stop behavior using the existing Node runtime and a
minimal synthetic DOM. The duplicate-member fixture emits the expected stdlib
ZIP warning. `git diff --check` and CLI `--help` also passed.

The initial test invocation failed because the script had not yet been implemented;
two test-fixture placement/type errors were corrected during development. No
synthetic result represents browser rendering, audible playback or real usability.

The actual retained ZIP was not opened by these checks; source registration and
the actual one-shot preparation remain unexecuted, pending root's source and
registration review. No old exporter, raw recording decoder, model, native owner,
browser, server, held-out data or scientific renderer ran. No PR or push occurred.
Root-only registration/launch commands and the finite allocation are in the
[plan](../plans/artwork-encounter-v1.md).

Real browser/audio/keyboard/viewport checks, human artistic judgment, independently
operated complete sessions and rights/audience/custodian/retention declarations
remain open. Afterimage still contains only eight responses / 0.5 source seconds /
0.16 model seconds and is insufficient for sustained material assessment.
Qualification claims remain empty; account quota is unknown.
