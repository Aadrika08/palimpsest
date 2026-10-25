# One interruption, two traces — 22 October 2026

The single obstacle-edit allocation produced a readable continuation for
**One map, many possible lives**. The previous seven-interval goal-edit study
is preserved. This is an exploratory artwork comparison, not a memory-effect
experiment or navigation benchmark.

## Recorded result

Source commit: `efc913b`; [frozen allocation](../plans/route-obstacle-material-2026-10-22.md).
Public LabSupervisor, reproduction/checker, CPU FLYNN, seed 0. No retry.

| | Unchanged parent A | Obstacle-edit branch B |
| --- | --- | --- |
| Run | `99c9983184884b35a2a473293640550d` | `4fdd85003a4048778d3c8189c6dca725` |
| Start tick boundary | 0 | 100 |
| Recorded intervals | 375 | 279 |
| Route points | 376 | 280 |
| Recorded duration | 7.5 s | 5.58 s |
| Final tick boundary | 375 | 379 |
| Natural outcome | Goal | Goal |

At tick 100, obstacle 0 moves from `[1.7531095977, -2.9467300638]` to
`[0.75, -0.75]`. Goal, controller and eye masks are unchanged. Snapshot
`46c9979f208143c281046cc83943e924`, SHA-256
`1dd643ddcde3776568062c42d33df492c3d96af543ace826c49acaee72f3b8c3`.

The common continuation contains **275 intervals / 5.5 s**, recorded tick
indices 100–374 (boundaries 100–375). The branch retains its four additional
intervals. Nothing is cropped, stretched or aligned to exaggerate separation.
The screenshot shows a modest detour in B before the two routes approach the
same goal. This is my visual assessment of the recorded pair, not an audience
study or a statistical effect estimate.

Generation completed in **62.738 s** under its 300 s limit; audited source files
total **141,594,209 bytes**. Both owner processes and the outer process group
were absent after cleanup.

## Audit and presentation

- Independent audit reconstructed the obstacle mutation and `mj_forward` from
  the snapshot without stepping. Integration bytes match that reconstruction;
  only the permitted obstacle position/velocity addresses changed. Native
  model arrays, environment changes, policy/RNG, eyes and lineage were checked.
- The small branch-start pose offset from the parent's cached pose is explained
  by the derived-position refresh, reproduced independently and left unchanged.
- All route points in the SVG and HTML equal recorded coordinates; source hashes
  and the parent event prefix match. The sole edit is recorded at tick 100.
- The overlay now precedes the detailed provenance table. Captions identify
  the edit, unchanged goal, shared comparison window and unequal full lengths.
  Fixed arena axes, solid/dashed lines and distinct start markers remain.
- Focused tests: **32 passed, 1 skipped** (opt-in native snapshot test).
- Offline browser checks at 1440 and 390 px passed: correct counts/lineage,
  keyboard provenance disclosure, all six sections, no document overflow,
  no autoplay, no page errors or external requests.

The other four artwork derivatives remain byte-identical to the prior reviewed
package. Their existing duration evidence remains applicable. Both updated static modes passed fresh concurrent 600-second browser sessions
at commit `93964ad`: Borrowed body **600.480 s**, One map **600.493 s**.
Each produced 599 visible/in-view probes with unchanged geometry, byte-identical
start/end screenshots, no page errors/external requests and confirmed browser
shutdown. The initial sandbox launch failed before registration (`spawnSync git
EPERM`); the same harness then ran with approved execution permissions.

## Portable handoff

Open `runs/route-obstacle-material-2026-10-22-v1/handoff/index.html`.
The sibling `palimpsest-obstacle-review-2026-10-22.zip` contains 20 members,
15,297,520 bytes, SHA-256
`9299bcdad062da11ca3060e1ef2be573aae701d830a40a308b91e1d2a77a3c23`.

The consumed test archive is retained. The final handoff corrects the copied
review sheet's old destination, clarifies tick boundaries in the entry caption,
and adds session results. All six artwork files are byte-identical to the tested
archive; ZIP readback and checksums passed. Its entry page passed a fresh short
browser check at both viewport sizes. Raw camera records and snapshots stay local outside the ZIP.
[Evidence index](route-obstacle-material-2026-10-22/index.json) binds the receipts.

## Acceptance and next step

Agent recommendation: **keep this pair for the next development encounter**.
It resolves the earlier inadequate branch sample without requiring a large
effect. A guided introduction and synchronized input inspection remain later
presentation work; this export is a static recorded comparison.

Next priority from the curatorial review: make Afterimage's source-to-response
relationship legible while retaining its fixed mapping. Human Choir listening,
independent operator acceptance and rights/use/custody declarations remain open.

No full repository suite, new research qualification, physical drawing or human
exhibition acceptance is claimed. The duration checks are headless browser
stability evidence only.
