# Afterimage: source and response together

22 October 2026. Follow-up to the [curatorial review](artwork-curatorial-review-2026-10-22.md).

## What changed

Afterimage now opens its inspection panel by default. The selected recorded
left-camera frame appears beside its model response on desktop, and above it
on mobile. Previous/next and the existing 60-second playback update both.
The page identifies episode/tick, source observation time, concatenated source
time, model time, exact action and response coordinates. It explains that the
image was supplied to both model cameras with fixed sensor values.

The original SVG stays available through its existing provenance link. All six
artwork files are byte-identical to the preceding obstacle-review package.
The response plane retains its fixed ±360 axes, chronological prefix and exact
coordinates. Small responses remain small; there is no zoom, smoothing, source
selection or new inference. Older packs without camera previews still work.

## Source verification

The existing NPY contains 600 RGB uint8 frames of 128×128 pixels, SHA-256
`94618320460eded8b95fce07ba0f89abeaf22a6b9d94bf6a92c2108b45c1823b`.
The package script verifies that file and every frame against the original
source index. It creates a lossless PNG with ten columns and sixty rows and
checks every decoded tile against its original pixel array. No resizing occurs
in the stored image; browser enlargement uses nearest-neighbor display.

PNG SHA-256:
`595bf473923c5808abdc840570926d3339394b8df1be571845406fa7b0160fd2`.
The bounded presentation manifest checks dimensions, RGB format and PNG hash
before the page is generated. The browser disables playback until the sprite
loads; a failed load retains an explanation even if Stop is pressed.

## Verification

- 14 focused encounter tests passed, including historical packs, preview
  metadata/hash rejection and exact response-prefix controls.
- Package assertions checked all 600 decoded tiles, six unchanged artwork
  hashes, storage limits, all member checksums and exact ZIP readback.
- Final browser check passed: all 600 rendered RGB frames match source hashes;
  all 600 responses displayed in order and synchronized over **60.012 s**.
  Desktop (1440 px), mobile (390 px), keyboard stepping/play/stop, collapse-stop,
  no autoplay/repeat and image-load failure behavior passed. No page errors or
  external requests occurred. [Evidence index](afterimage-presentation-2026-10-22/index.json)
  binds the receipts, verification scripts and screenshots.

The first local presentation (`…-v1`) passed 600 browser RGB-frame hash checks
and a 60.012-second playback. Review then corrected stale review-sheet wording
and preserved the load-error explanation on Stop. The final package is v2;
the initial package remains intact. No source or model rerun occurred.

## Handoff

Open `runs/afterimage-presentation-2026-10-22-v2/encounter/index.html`.
Portable ZIP: `palimpsest-afterimage-presentation-2026-10-22.zip` beside it,
22 members, 17,269,977 bytes, SHA-256
`91e14087ca31bd3ab2a30c51e34420a6016a2e0709c5a9659109567188d774b5`.

The package receipt and README were created before browser verification and
therefore say that verification is pending; this report and the separate browser
receipt record its subsequent outcome. Human decisions remain pending.

Agent assessment from the desktop/mobile screenshots: the source transformation
is now inspectable even though the trace is small. This is suitable for the next
development presentation. A guided introduction is next; human viewing, Choir
listening and independent operator/use declarations are still open.

No full repository regression, new inference or human/exhibition acceptance is
claimed. The four other unchanged visual derivatives and Choir retain their
previous evidence; they were not replayed for this presentation change.
