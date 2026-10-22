# Static artwork duration checks — 22 October 2026

**All four automated ten-minute sessions passed. Human acceptance is pending.**
The [prospective protocol](../plans/static-artwork-sessions-2026-10-22.md) and
harness were committed as `99e7b80` before execution. Each mode had its own
single-page, headless Chromium process at 1440×1400; the four sessions ran
concurrently. They are not four sequential human viewing sessions.

## Measured sessions

| Mode | Monotonic duration | Visibility probes | Verified geometry |
| --- | ---: | ---: | --- |
| Borrowed body | 600.692 s | 599 | 376 route points |
| One map, many possible lives | 600.671 s | 599 | 376 parent / 8 branch overlay points |
| Atlas of what disappears | 600.567 s | 599 | 135 dashed removed edges; 3,295 paths, covering the 1,647 before / 1,512 after edges plus annotations |
| The space between two flies | 600.635 s | 599 | 15,942 / 21,065 anatomical segments |

Sessions started at approximately 11:17:14.7 UTC and ended at 11:27:15.4 UTC.
The longest measured probe gap was 1.018205 s; maximum browser animation-frame
callback gap was 16.8 ms. Each page recorded about 36,000 frame callbacks.

Every probe found the selected SVG completely inside the viewport with document
visibility `visible`. No visibility event, SVG mutation, page error, crash or
external request was recorded. Geometry counts were checked before and after.
All four start/end screenshot pairs are byte-identical. The screenshots were
inspected: no selected artwork was clipped. For One map the selected view was
the complete route overlay; this did not hold every provenance panel or final
world view onscreen simultaneously.

All browser connections were closed at completion. No model inference, new
simulation, audio, timed portrait, repeat or accelerated clock was used.

## Independent verification and provenance

The [independent audit](static-artwork-sessions-2026-10-22/independent-audit.json)
checks all per-second traces, UTC/monotonic agreement, visibility and frame/probe
gap bounds, monotonic frame counts, full viewport containment, source hashes,
geometry counts, screenshot hashes and completion receipts. It verifies the
executed script hash against its committed source.

The source encounter ZIP is 15,250,086 bytes, SHA-256
`0ef85fba961c9d207a6023232132929a82f908b6324d3493a4edd31fa8a6230d`.
An additional pre-completion byte comparison and the final audit verified all
18 extracted members, including `checksums.json`, against that ZIP. This closes
a review finding that the harness alone trusted the extracted checksum file
without directly binding it to the ZIP.

The [evidence index](static-artwork-sessions-2026-10-22/index.json) hashes the
retained registration, full traces, results, independent audit, input comparison
and eight screenshots. Intermediate progress files remain local and are not
completion receipts.

## Scope and limitations

- Headless visibility and animation callbacks establish automated browser
  presentation behavior, not physical display output or human attention.
- The 640-second watchdog covers presentation work, excluding Chromium launch
  and final shutdown. It is not claimed as a total process-lifetime watchdog.
- No human artistic, independent-operator or exhibition acceptance follows.
  The short seven-interval branch and all earlier source limitations remain.
- No application code changed. The assertion-based timed harness and independent
  audit ran; the unrelated repository test suite was not rerun.

## Next: human review

Fresh handoff: `runs/static-artwork-sessions-2026-10-22-v1/encounter/index.html`.
The adjacent `palimpsest-human-review-2026-10-22.zip` is 15,257,310 bytes, 20
members, SHA-256 `2eee0b9c731752372fd6a22664226510783c2661bc688accf79c2c487bba867b`.
It adds the duration audit and blank review sheet, updates the guide's completion
status, and preserves all six artwork files byte-for-byte. All ZIP members read
back exactly. Only guide text changed in the encounter HTML; no artwork playback
was repeated for this derivative handoff.

Use the [pending review sheet](../plans/artwork-human-review-2026-10-22.md).
For each mode, a human reviewer must record **keep**, **revise presentation**, or
**insufficient sample**, with one reason. Record actual human exposure, listening
level, interruptions, assistance, intended audience/use, rights review, custodian
and retention. Independent operator handoff remains a separate acceptance gate.
