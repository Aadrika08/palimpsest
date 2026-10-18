# Offline encounter preparation and handoff

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

The actual retained ZIP was not opened by those software checks. Source
registration and preparation followed the independent review described below.
No old exporter, raw recording decoder, model, native owner, server, held-out data
or scientific renderer ran. Registration/launch commands and the finite allocation
are in the [plan](../plans/artwork-encounter-v1.md).

Real browser/audio/keyboard/viewport checks, human artistic judgment, independently
operated complete sessions and rights/audience/custodian/retention declarations
remain open. Afterimage still contains only eight responses / 0.5 source seconds /
0.16 model seconds and is insufficient for sustained material assessment.
Qualification claims remain empty; account quota is unknown.

## Independent source review and correction

One independent review found no Critical issue and one Important issue: the
consumer required double-precision `pi`, rejecting the renderer's legitimate
float32 endpoint (`3.1415927410125732`). Root reproduced the rejection with a
stdlib-only synthetic fixture, then retained the producer's exact float32 bound.
Both signs are accepted and the next larger representable value is rejected.
All ten component tests passed in 0.038 seconds after the fix; no source renderer
or actual material was invoked by these tests. No Minor findings remain.

Review limits: actual ZIP contents and final preparation/byte retention still
require the registered invocation and independent close; browser/audio/keyboard
and human acceptance need their own evidence. This local preparation assumes a
controlled worktree, not an adversarial concurrent filesystem writer. The
fixed-source pin and exclusive output guards remain mandatory. This review does
not extend the eight-frame material or qualify any scientific behavior.

## Prepared once and independently verified

The registration bound committed implementation `b782a0e` and the three exact
source/test/plan hashes before the single invocation. Its SHA256 is
`94ee16b4209fd0f0536d402008de42bdf4bf634ff8230e8aa77718569e7430b7`.
The command exited zero in **0.464882 seconds outer** under the declared
119-second TERM / one-second KILL ceiling; the passing receipt measured
0.381824 seconds before its publication. No retry or corrective preparation ran.

[Independent verification](artwork-encounter-v1-evidence/independent-verification.json)
found zero discrepancies: source pins and the original 13,529,793-byte ZIP match;
all ten artifact/page hashes match; launch/result registrations match; and the
SVG and HTML alignment data agree exactly for eight responses, 0.5 source seconds
and 0.16 model seconds. All six targets are local. Runtime output is 13,550,103
bytes across twelve files. Qualification lists remain empty.

The [portable encounter ZIP](artwork-encounter-v1-evidence/palimpsest-offline-encounter-v1.zip)
contains those twelve files unchanged. Unzip it into a new directory and open
`index.html` locally. Native audio has no autoplay; Afterimage has manual previous/
next controls plus a full table and original trace. Its SHA256 is
`d10eac2edb52bd5c943c4d51317282afbc81a73f10bdfa2901208311c9c65792`,
size 13,551,423 bytes. Every archived member was compared byte-for-byte against
the prepared directory; runtime plus publication totals 27,120,833 bytes, below
64 MiB. The [handoff receipt](artwork-encounter-v1-evidence/handoff.json) records
these packaging measurements.

## Browser and acceptance boundary

The available computer-use tool reported zero browser surfaces. One request to
open the local encounter in the in-app browser was rejected with
`Browser is not available: iab`; no rendering or audible playback was reached.
Synthetic DOM checks and file integrity do not qualify real browser, keyboard,
viewport, audio, artistic or independent operator acceptance. The unavailable
browser is an environment blocker for that gate, not a diagnosed page failure.

Next: inspect all six modes in an available local browser, record real controls/
keyboard/viewport/audio behavior, and prepare the declared finite operator review.
Adequate new Afterimage material still needs a separate bounded preparation;
this encounter does not stretch its short source into a sustained experience.
