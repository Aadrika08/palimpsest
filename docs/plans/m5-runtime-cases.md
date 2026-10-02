# M5 live development cases and manual acquisition probe

This contract parameterizes the actual M4 two-passage cylinder world. It does
not freeze or enable held-out experiments. The existing profile without
`memory_case` retains its original IDs, layout and tick-10 change. Source hashes
pin the new implementation; snapshots from older source versions are not claimed
compatible.

`make_world_case(seed, regime, split, *, kind='change', acquisition=False,
change_tick=None)` accepts only development-history/development-test and returns
a strictly validated bounded JSON case. It reuses the synthetic generator's
independent side/relation/lexical counterbalance, but starts live M unknown and
E/U empty. Its live entity IDs are disjoint from synthetic fixture IDs and other
seed/split instances. No synthetic observations seed live beliefs. `change`
flips the cue and requests the gate assigned the chosen relation; `null` only
flips the cue; `no-event` does neither. Actual clearance supplies passage labels
and an explicit gate outcome. Hidden schedule/regime/geometry never enter the
controller observation: the existing declared symbolic sensor supplies visible
cue identity/state/bearing, landmarks, local passage observations and common goal.

`Engine.open(..., memory_case=case)` records the exact case and case/acquisition
protocol hashes. World/application snapshots bind that same identity and reject
mismatches. `replay_run` validates and propagates the manifest case before opening
the destination. Any Engine-only U branch runner must open its destination with
the exact validated source case; copying a snapshot into a default M4 destination
is invalid. Acquisition cases require manual control; they do not demonstrate a
FLYNN controller's inspection, exploration or manipulation capability.

The separate public acquisition schedule is explicitly
`privileged-manual-pose-supervision`: `acquisition_action(schedule, pose, tick)`
uses actual body pose, fixed north-facing lane waypoints and fixed phase times.
It uses neither U nor passage truth. The lane is x=-1.3, starts at y=-1.1, visits
y=.6, then reverses toward the start while facing the common goal at y=2.5. The
cue is at [-.8,1.5]. Default event/reference tick is 300, return begins at 330,
and the ceiling is 600 ticks. Heading/proximity controls and velocity .65 are
uncalibrated development choices; pure planned-pose visibility checks do not
prove the motion succeeds. Live coverage must be checked in retained sensor
packets, including consecutive visible cue packets at the change. A missing or
occluded sample remains unobserved. The driver and schedule hashes are recorded;
operator blindness and source authenticity are not established.

The first authorized probe is seed 0/local_cue/development-history/change, one
manual episode, at most 600 ticks, 150-second internal and 180-second external
wall bounds, and 192 MiB recording quota. It must retain a normal terminal
recording, recording file hashes, actual M/E/U, observed pre/post subject coverage,
trigger identities and geometric gate outcome. Full existing reader validation
checks terminal counts and chunk hashes after cleanup. Probe coverage may be
partial or fail; neither a favorable gate outcome nor synthetic expectations can
replace missing sensor evidence. No collector fitting or held-out run is part of
this slice. One actual episode cannot satisfy the existing four-check-per-relation
learning support requirement or qualify R2 transfer/closed-loop effects.

## Initial acquisition observation, 2026-10-02

The single authorized seed-0/local-cue change probe completed normally at 410
ticks in 30.089 seconds. Run ID is `9c24f25d6f7d4eeeb70bf2bc62b658f2`, retained
under ignored `data/runs/m5-acquisition-probe/`. `acquisition-probe.json` retains
actual M/E/U and complete recording/source/case/protocol hashes;
`sensor-evidence-audit.json` retains exact bracketing evidence and trigger links.
The acquisition report SHA256 is
`a7a9629c28552b75bc02fc5caf567fb41c04b083d271cde03ae1e930c7af28e5`.
Existing artifact-reader validation exhausted all 410 ticks and checked terminal
counts/chunk hashes; recording size is 84,293,986 bytes. Normal Engine cleanup
completed and the runtime slot was released. No second case was run.

The actual nearest observed local-cue samples were open at tick 29 and blocked
at tick 409. The paired-cue samples were open at ticks 299 and 300. Consecutive
visible cue packets at 299/300 witnessed the 0-to-1 change. The geometric gate
outcome was `closed`. Initial unknown-M/empty-E/empty-U hashes were reconstructed
and matched the manifest. One `no_rule` selection had no targets; no U replacement
or inspection occurred. Final M reflects those actual direct observations, while
live E and U remain empty. These records demonstrate one manual acquisition's
coverage and no engine U guidance; they do not establish operator blindness,
authenticity outside recording integrity, learned U, held-out transfer, or R2
completion. The separate historical collector and sufficient independent
acquisitions remain pending. This one lane/seed/regime result does not qualify
all counterbalanced cases or null/no-event acquisition schedules.
