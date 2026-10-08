# Offline artwork encounter v1

8 October 2026. Software preparation under the simulation completion goal.
Base: `03659c5c244952d3dd92b7450d5d4d45d3fc5535` (retained PR88 material).
The new encounter uses only the six already completed derivatives. It does not
repair, repeat or reopen any historical artwork/browser allocation.

## Bounded preparation

Implement and test the script before root's independent source review. Root must
review a registration of committed sources before the one actual preparation starts.
This plan does not launch it. Input:
`docs/reports/artwork-material-v3-evidence/palimpsest-artwork-review-development-v3.zip`,
13,529,793 bytes, SHA256
`e4994c965d3b2ff18623e39b745dbb4d7f4f36ed2ddecd7f2d6f5fddb7a132de`.

One new derivative-only invocation: 120 seconds from admission through final
receipt; output at most 64 MiB; initial and continuing free-space floor 2 GiB
plus 64 MiB headroom. Fresh absent output directory only, exclusive publication,
no overwrite or cleanup of historical files. Recheck input/source pins at close.
Zero native owners, inference, model imports, raw recording/NPZ/SNP decoding,
held-out access, scientific renderers, servers or browser runs. No retries or
corrective invocations. Retain partial files and a failed receipt on failure.

The nine-member ZIP must match its exact whole-file pin, regular member allowlist,
bounded stored sizes and CRCs. Its checksum manifest must bind all eight remaining
members. Reject duplicate, missing, unsafe, symlink or unexpected members before
publication. Copy derivative bytes unchanged and verify every copied member.
Registration binds committed HEAD, script, plan, input ZIP and fresh destination.
The output receipt reports elapsed time, pins, member checks and empty qualification
claims; its launch marker remains consumed on either success or failure.
Admission refusal also consumes the invocation; root retains its command outcome
even if no marker could be created. There is no automatic retry.

## Encounter

One local `index.html` with six anchored modes, original file links, visible
captions/limitations, provenance and source notices. Use native SVG/image/iframe
and audio controls, no autoplay or loop, no dependencies, network or local server.
Manual Afterimage previous/next controls show each exact response on the same fixed
axes and its source/model times. Full trace and provenance remain available;
coincident points remain coincident. An accessible alignment table is available
without JavaScript. Eight frames / 0.5 source seconds / 0.16 model seconds remains
insufficient for sustained artistic judgment; inspection does not extend it.

Design: white `#ffffff`, slate text `#253746`, pale blue `#edf4f8`, response blue
`#244c5a`, and focus blue `#005fcc`. System sans-serif reading text, familiar serif
headings, one left-aligned column with an anchored mode list. Existing artwork
geometry is the visual emphasis; no cards, decorative motion or new projection.

## Verification and acceptance boundary

Synthetic tests first: archive corruption/allowlist/path/bytes/hash rejection,
output reuse, all six targets, safe HTML/JSON embedding, exact alignment/timing,
coincident/one-frame paths, unchanged copied bytes and bounded failures. Tests
must not use the retained ZIP or import scientific runtime modules.

After source review, the single preparation can validate packaging and hashes.
No real browser/audio/keyboard/viewport or human session is authorized by this
invocation. Those remain explicit acceptance gates, alongside a named independent
operator's setup and entire declared-duration session, audience/custodian/retention
declarations, user artistic judgment, and adequate new Afterimage material.
Account quota telemetry is unavailable; quota is unknown.

## Root-only next actions (not executed during software preparation)

After the committed source review, print the registration with
`python scripts/prepare_artwork_encounter.py --register --output OUTPUT`, where
OUTPUT is a fresh directory under this worktree with an existing parent. Retain
the printed registration outside the checkout or under an ignored path, so its
creation does not dirty the clean source gate; review it before launching once.

For that one launch, use
`timeout --signal=TERM --kill-after=1s 119s python scripts/prepare_artwork_encounter.py --registration REGISTRATION --output OUTPUT`.
The external 119-second TERM / one-second KILL ceiling covers blocked system calls;
the script checks its 120-second deadline at each bounded operation. Root must
retain actual outer start/end, return code and any admission/finalization error.
The receipt's elapsed field is explicitly measured before receipt publication.
Only an exit-zero command plus a passing receipt and independent byte checks can
establish preparation success. None supplies human acceptance.
