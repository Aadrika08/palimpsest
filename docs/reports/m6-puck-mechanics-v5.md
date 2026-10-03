# M6 puck mechanics attempt v5 — complete simulator gate passed

The single approved attempt at `eba4c397b883da717130d8ea1d65cc42f23a2cff`
**passed all ten owners**. Attempt v5 retains the v4 teacher, task/mechanics
protocols, layouts, physics, objectives and bounds. Its only runtime source
change normalizes recorded NumPy scalar modes before the unchanged strict
action-replay checks. The [v4 failed attempt](m6-puck-mechanics-v4.md) remains
failed and retained; this was a separately reviewed execution with fresh output.

| Owner | Recorded ticks | Result |
| --- | ---: | --- |
| zero, push-positive, push-negative | 120 each | All fixed mechanics checks passed |
| teacher-positive | 361 | `puck_goal`; final distance .159238796 m |
| teacher-negative | 361 | `puck_goal`; final distance .169534687 m |
| continue-tick1 | 4 | Exact source successors from completed tick 1 |
| continue-contact | 4 | Exact source successors from completed tick 112 |
| continue-dwell | 4 | Exact source successors from completed tick 352 |
| replay-actions | 120 | Exact full fixed-action source; zero teacher calls |
| replay-policy | 361 | Exact full teacher source, including carried mode and goal |

The three native continuations and both full replays matched **every numeric
field's dtype, shape and bytes**, including input cameras, controls, contact
intervals, before/after mode codes and task digests. Snapshot applications,
raw native payloads and integration arrays matched their source boundary.
First contact/dwell snapshots were the first qualifying boundaries; no later
boundary was selected. Both teachers retained 15 signed reverse approach commands
and reached the unchanged ten-tick dwell criterion.

Outer supervision exited 0 after **45.694474692 s**; inner elapsed time was
**45.456802609 s**. All ten recordings completed normally. All callbacks and
retired/current renderers closed. No forced signals, sampler errors, survivors,
supervision errors or finalization errors were reported. All **13 observed
PID/start identities and ten owner groups** were independently absent. All 81
frozen source hashes and every owner's full model hash stayed unchanged. The
native slot was explicitly released before the retained-data audit.

The local NumPy-only audit passed in **2.678 s**, checking **1,575 rows**, 13
snapshot receipts and **146 indexed files / 198,032,371 bytes**. Root's independent
audit passed in **3.953 s** and independently reconstructed both teacher episodes,
task/contact/mode transitions, goal dwell and exact continuation/replay rows.
Neither audit imported MuJoCo or Torch or restored native state. No audit failure
or rerun occurred. Native restoration and stepping occurred in the approved
actual gate only.

The [JSON evidence index](m6-puck-mechanics-v5.json) pins both audits, all owner
receipts, controls and raw reports. Output is
`runs/m6-puck-mechanics-v5-20261003/`; controls and local audit are under
`runs/m6-puck-mechanics-v5-prepared/`.

- Inner report: `0180cd00ad89a17fa2e57eb41211009836f54f5e53d1790a867373fe8b44ae42`.
- Outer report: `4b6c8028f63bc359130f98ce0858d641a7f14c6cafe019cde68002259111a6f5`.

This qualifies the bounded standalone simulator mechanics and exact replay
contract on the inspected development layouts. It does not qualify physical
contact behavior, a learned pushing controller, unseen layouts or production
Engine/UI integration. Teacher collection and training remain closed pending
a separately reviewed mode-observability and learning contract.
