# Fixed visible preparation: retained negative result

At frozen `b17d006`, v2 passes source visibility admission but the own-U continuation
fails at boundary 354. Its actual sensor packet observes the lower passage blocked;
the memory revision **does not commit**. The verifier reports `mechanism_unverified`,
exits 1, and stops before swapped, sham and no-U. No task pass, four-condition
comparison, held-out result or R2 completion is claimed. The original
[v1 negative evidence](m5-recorded-transfer.md) remains unchanged.

| Stage | Run ID | Numeric ticks | Terminal result |
| --- | --- | ---: | --- |
| Source | `eb3b3327a1304cf8a2b37d349e002d33` | 300 | Completed; paused at boundary 300 |
| Own-U anchor | `0a6d507fd7234d3b89d7f09f3e1481a5` | 0 | Completed; paused at boundary 300 |
| Own U | `181b660c01994c7a80c588ad76c15697` | 54 | Failed, `CueUnavailable`, boundary 354; gate closed |

All three close with `operator_closed` and no reported cleanup error. Together their
validated manifests, events and numeric chunks contain 354 ticks and 72,892,829
bytes. Root's outer terminal report records 39.225659174 seconds and exit 1.
The later three stages are unattempted, rather than failed or successful.

The source uses the declared privileged manual pose schedule. Its separately
versioned ticks 200–299 command velocity zero and yaw 9 degrees; actual drift is
retained. Recorded packets 299 and 300 contain the common cue, common goal and both
inspection landmarks. Lower occupancy remains unobserved during preparation. Both
pre-event M facts come from actual retained observations: lower at 29 and upper at
299. Source starts with unknown M and empty E/U. Anchor and own register the exact
historical own-U artifact; all three native snapshots have equal non-U invariants.
Historical bundle hashes and exact E-only refits pass independently.

At 300, the cue flips and the physical gate closes. Own U selects the independently
identified changed lower fact, commits `open/uncertain`, and starts inspection with
deadline 500. The unchanged continuation uses only the previous published declared
bearing. The common goal is last visible at 306, while lower inspection guidance
continues through 353. Packet 354 first observes lower `blocked`; its inspection
landmark remains visible, but the common goal is absent.

`advance_memory` works on a validated copy. It computes the fresh occupancy update
and inspection resolution, then requests the common-goal bearing before returning.
`CueUnavailable` prevents that return and Engine assignment. The recorded blocked
sample is real evidence; it is not a committed revision. Final M remains lower
`open/uncertain` with evidence 29, the cursor/detector remain at 353, and the active
inspection remains from 300. No decision, resolved inspection or published cue is
recorded at 354; no numeric transition 354 is fabricated. All 300 source actions,
100 override events and 54 own actions match the existing float64 manual conversion;
one additional attempted driver input at 354 is retained.

The [evidence index](m5-visible-preparation.json) includes packet, recording,
worker-report, snapshot, historical E/U and protocol hashes. The immutable primary
artifacts are under `runs/m5-memory-visible-preparation-20261002`:

- `transfer-plan.json`: `53753016e39cf164d5efdeba6804ac7ef0533169d25ea56bfd1d495548f921ec`.
- `transfer-report.json`: `bc22336c26725e840569c63255a5362a84ec1cf4552545275ddfdbab49379b7e`.

A pure geometry check of proposed goal `[-0.5,-2.7]` passes clearance and unchanged
range/FOV/LOS at all 55 retained own poses (300–354). A static replacement fails the
unchanged source: that goal is invisible at ticks 0–254. The smallest separate
preparation can use the existing paused `intervene/move_goal` command after source
acquisition, before shared native capture. Its explicit event, effective float32
goal and refreshed observation are snapshot-covered; M/E/U/cursor remain unchanged.
A distinct post-intervention visibility probe must not impersonate a memory tick.
All U-only forks must share the same moved world and unchanged driver.

This is a proposed development fixture repair, with no v3 runtime evidence. General
invisible-goal recovery would require a separate bounded search protocol. No sensor
enlargement, private-bearing fallback, replay, rerun or frozen source edit was used
for this audit.
