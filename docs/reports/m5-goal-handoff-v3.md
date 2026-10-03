# Goal handoff v3: retained source guard failure

At frozen `2f43840`, the verifier stops after its source worker fails an exact
handoff guard at paused boundary 300. Run `c86b56841b9344de91ae4c03ba27322c`
contains 300 validated numeric ticks and 61,744,394 recording bytes. The ordinary
goal command **was applied**, at tick 300/revision 301, to canonical float32
`[-0.5,-2.700000047683716]`. It was not rejected. The worker returns 1 with
`ValueError: Goal handoff changed memory/physics or did not apply exactly`.
Anchor, own, swapped, sham and no-U remain unattempted; there are no retries.

The recording itself closes normally as `completed`, phase `paused`,
`operator_closed`, no runtime failure/outcome or cleanup error. This terminal
recording status does not make the verifier successful: `mechanism_unverified`,
`task_pass=false`, `r2_complete=false`. Gate schedule remains pending, memory
cursor remains 299, both M facts retain actual observed open evidence, and E/U
remain empty. No goal probe or native snapshot was captured after the guard.
Root's outer report gives 19.480 seconds/exit 1; the retained child supervisor gives
19.366555624 seconds/exit 1. No replay or simulator run was used in the audit.

The [evidence index](m5-goal-handoff-v3.json) pins manifests, events, chunks, worker,
plan and command details. Primary retained report:
`runs/m5-memory-goal-handoff-20261002/transfer-report.json`, SHA-256
`53c36769a41da7f5939c562c65f9871a28005dc1e60e53a20e28937a00d8d243`.
Terminal checksum/count readers, exact source actions/override, actual memory
evidence linkage and unchanged collector source admission pass. No pre-event
trigger was witnessed.

All 300 source actions, poses, next-poses, controls and simulation times are
bitwise identical to the retained v2 source. Its native boundary stores authoritative
base qpos XY `[-1.2342004354379925,0.6053890620968724]`; the last numeric pose uses
cached body coordinates `[-1.2341991662979126,0.6053884029388428]`. The upstream
`_base_xy` reads float32 `data.xpos`, while the goal intervention calls
`mj_forward`. Refreshing that derived position from the retained authoritative
qpos predicts delta `[-1.3113021850585938e-6,6.556510925292969e-7]` metres, sufficient
to fail the exact `world['pose']` equality without physical movement. Retained v2
obstacle qpos XY exactly matches its recorded before circles.

This is a **matched-prefix inference**, not direct v3 post-guard proof: v3 did not
retain the failed guard's before/after operands. An applied canonical goal is
verified; a site-coordinate mismatch or obstacle displacement is not established.
The compound error cannot be reconstructed directly from this record alone.
A separate later validator bug is verified by reading v2's real snapshot: environment
fields are wrapped under `values`/`absent`, while v3's new goal validator expects a
flat `_goal_xy`. That mismatch did not cause the earlier worker guard failure.

The separately approved v4 correction will preserve exact authoritative physical
and model state rather than compare stale/refreshed display coordinates or widen
a tolerance. It will label both coordinate stages, record invariant pre/post
hashes and bind the post-intervention integration digest to the native snapshot
using the existing state API. Real wrapped-field and derived-refresh fixtures
must reject actual qpos mutation. Goal, source preparation, cue-only continuation
and failure semantics remain fixed. V3 raw evidence and the earlier
[v2 negative result](m5-visible-preparation.md) remain immutable; no v4 runtime
result or invisible-goal capability is claimed here.
