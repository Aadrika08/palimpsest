# Public route and labelled branch — 22 October 2026

**Route generation, lineage/geometry audit and short browser checks passed.**
Ten-minute static viewing sessions and human artistic acceptance remain open.
This closes the source relationship requirement in the artwork plan; the branch
is very short and is not represented as sustained material or a causal result.

## Allocation and observed outcomes

Executed [the fixed prospective allocation](../plans/route-material-2026-10-22.md)
once from commit `681486f`, via the existing public `LabSupervisor` and worker.
The [evidence index](route-material-2026-10-22/index.json) hashes the retained
receipts, source manifests, snapshot registries, scripts and browser screenshots.

| Item | Actual result |
| --- | --- |
| Parent | `fceb1ae711ef455ebee50484ae47831c`, FLYNN CPU, reproduction/checker, seed 0 |
| Parent outcome | Goal at 375 intervals; 376 recorded route points; 7.5 simulated seconds |
| Snapshot | `8266994da7704ddfa4fc7c3ce4d9cd6c`, paused episode 0 / tick 100 |
| Snapshot bytes / SHA-256 | 1,215,990 / `392e97fca1bf0eb21ab91b2bc29cac4b109e9c57aa9166a79e13435f07a463c6` |
| Branch | `c068a4352868451ca712aed1cb8f39b0`, same controller, registered parent snapshot |
| Sole edit | Move goal from `[4.509548664093018, -5.026264190673828]` to `[0, 0]` at tick 100 |
| Branch outcome | Goal after seven continuation intervals, ticks 100–106; eight points; 0.14 simulated seconds |
| Source recording bytes | Parent 81,225,512; branch 1,546,452, excluding snapshots and supervisor logs |
| Allocation runtime | 60.735 s, exit 0 under 300 s watchdog |
| Cleanup | Both lab owners and outer process groups absent; no live owned workers |

The branch's final absolute simulation clock is 2.14 s and its episode counter
107, because both inherit the first 100 parent intervals. Its own recorded
continuation is only seven intervals. The parent export includes its full route;
the branch export includes only its continuation. No reset, extra seed, repeat,
controller replacement, input masking or aesthetic selection was used.

Source generation used 2 GiB aggregate and a 2 GiB free-space floor, with capped
1 MiB logs. The local allocation including pack and browser evidence is about
117 MB. The public worker's native snapshot and branch checks were reused.

## Boundary observation and independent audit

An initial audit assertion expecting identical recorded start poses failed.
The measured branch-minus-parent tick-100 pose difference is
`[0.0018410682678222656, -0.0017110705375671387, 0]` world units/radians.
This was investigated, not rounded away or corrected in the data.

The parent snapshot contains the pre-refresh cached MuJoCo body `xpos`. The goal
edit calls `mj_forward`, refreshing that derived position without advancing
integration state. Reconstructing the parent native snapshot and calling only
`mj_forward` reproduced the branch's XY value exactly. The audit confirms
bit-exact integration state before/after, unchanged controller state and RNG,
and the expected single revision increment. Thus identical saved integration
state does **not** mean identical recorded cached-pose coordinates at this edit.

The [independent audit](route-material-2026-10-22/independent-audit.json) also:

- Checks the authoritative snapshot registration, snapshot hash and exact parent
  event-prefix hash/count.
- Checks restored parent/snapshot IDs and the sole recorded goal edit.
- Validates all source intervals, eye flags and native timestamps; rehashes every
  source file referenced by the comparison.
- Compares every raw route point with the Borrowed body metadata/polyline and
  both One map overlay polylines. All coordinates are exact and unmodified.
- Revalidates the committed generation source pins after the audit.

This is a descriptive parent/branch comparison. It does not establish a memory
effect, identical route-start coordinates, matched full-episode durations,
generalization, physical drawing or biological behavior.

## Encounter and verification

The encounter validates route derivative hashes, source IDs, the parent/snapshot
relationship, tick ranges and goal edit before displaying new captions. It shows
375/7 intervals, 7.5/0.14 s, tick 100 and the measured XY offset. Historical packs
without the new route provenance retain their original captions.

- **50 focused tests passed, one skipped.** The skipped test is the opt-in native
  snapshot quota-failure test (`PALIMPSEST_SIMULATION_TESTS`); it was not counted
  as passed. Existing duplicate-ZIP fixture and Matplotlib/Pyparsing warnings remain.
- TypeScript check and `git diff --check` passed.
- Chromium at 1440 px and 390 px: all six modes present, correct overlay point
  counts 376/8, source and snapshot IDs verified, keyboard provenance disclosure,
  no document overflow, no automatic media start, zero errors/external requests.
- Screenshots inspected: routes and labels are visible; mobile source tables
  retain bounded internal scrolling. Iframe viewing has its own vertical scroll.
- Fresh read-only review found no blocking issue and reran 16 focused tests.
  The new driver tests do not inject watchdog/owner-cleanup failure paths; actual
  successful-owner cleanup is recorded. The full repository suite was not run.

## Local pack and reproducibility

- `runs/route-material-2026-10-22-v1/encounter/index.html`
- `runs/route-material-2026-10-22-v1/palimpsest-route-encounter-2026-10-22.zip`
- ZIP: **15,250,086 bytes**, 18 members, SHA-256
  `0ef85fba961c9d207a6023232132929a82f908b6324d3493a4edd31fa8a6230d`.

Every ZIP member read back byte-exact. The pack replaces only the two route
derivatives and their presentation/provenance; actual Afterimage/Choir and the
historical Atlas/specimen derivatives are retained. Raw route records and native
snapshots stay local outside Git and this derivative ZIP. Retained source hashes,
registration and public generation recipe provide a rebuild path; fresh reruns
are not guaranteed byte-identical. The scripts in this evidence directory refer
to this consumed allocation and must not overwrite it or automatically rerun it.

## Next gate

Run the four declared **ten-minute static viewing sessions**: One map, Borrowed
body, Atlas and The space between two flies. These short browser checks do not
satisfy those durations. Then obtain human keep/revise/insufficient-sample
judgments, including the seven-interval branch, independent operator acceptance
and the required rights, audience and custodian declarations.
