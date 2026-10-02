# M5 v2 fixed visible-boundary preparation

Preparation only; no v2 actual run has been authorized or performed. This is a
separately versioned source preparation for the existing six-stage verifier,
not a replacement interpretation of the negative v1 result. No held-out split,
R2 qualification or invisible-target capability is claimed.

The retained v1 source at frozen `8420247`, run
`12f3211e524a43c6a73f3da0ae07460b`, already has both facts observed at tick200.
Its actual pre-control pose is
`[-1.2999999523162842, 0.626152515411377, 1.570796326794896]`.
The lower fact links to its open observation at tick29; the upper fact links to
its open observation at tick200. E/U is empty and the manual velocity command
is zero. Thus preparation starts from the measured upper waypoint, not an
assumed tick299 ideal pose. The record is retained in
`runs/m5-memory-transfer-20261002/runs/12f3211e524a43c6a73f3da0ae07460b`.
Tick200 is row8 of retained `recording/chunks/000006.npz` (start192), SHA256
`72d95a280263c55cc79a9115b0388fa18d96c63f18d89f87991f6d4c99de7659`.
V1's report SHA256 remains
`5d3cfc220fb50b78490c541d18df9c5538074b274de5be780d90216bb6555ee6`;
own/sham failed with a queued invisible lower inspection, swapped/no-U reached
the common goal with the changed fact stale, and all four task results were
false. That evidence and its protocol are unchanged.

The fixed v2 source-preparation profile is
`fixed-visible-boundary-source-v2`. Ticks0..199 retain the original public
acquisition schedule. Ticks200..299 explicitly override it with velocity command
0 and heading error `remainder(pi/20 - actual_yaw, 2*pi)`, clamped to
[-.35,.35] radians. The target orientation is 9 degrees; achieved orientation
and displacement are not assumed. No reset, teleport, model/geometry edit,
sensor/FOV enlargement, private bearing, fallback or later rescue is added.

`source_action(schedule, pose, tick)` accepts only the original public schedule,
explicitly privileged source pose and source tick. The override is fixed before
execution and depends on neither U, regime, evaluator gold nor branch outcome.
All four continuations keep the unchanged previous-published-declared-bearing
driver, velocity .65, heading conversion and one-tick delay. Source pose access
does not enter that driver. Source M still starts unknown, E/U empty; every
known fact must originate in actual recorded declared passage observations.

Each manifest records the complete source-preparation protocol/hash and an
explicit acquisition_schedule_override. A `source_preparation_declared` event
records the same data before native capture; the registered snapshot's durable
event-prefix hash binds it. Each override tick additionally records its
privileged pose, action and preparation hash. Admission checks exact manual
float64 actions against the actual recorded poses, preserving Engine's existing
action conversion. The original case/acquisition schedule hash is not relabeled
as the applied source driver. The unchanged geometry case ID/SHA is combined
with the distinct preparation, transfer-protocol, driver and recording identity;
v1 and v2 preparations are not interchangeable.

Admission requires the **actual recorded** tick299 packet, before any anchor or
continuation is launched, and each branch's actual tick300 packet immediately
after its first attempted step. Both packets must expose the declared cue with
its expected 0/1 token, common goal and both candidate inspection landmarks,
under unchanged capture range/FOV/LOS rules. The lower occupancy must remain
unobserved at both boundaries and throughout source ticks200..299, so preparation
does not directly reveal the changed answer. Both pre-event M facts must remain
observed and link exactly to retained source sensor samples. Packet identity,
episode/tick, subject and evidence inconsistencies reject. Missing visibility
or evidence aborts admission; no alternative pose, retuning, retry or replacement
source is permitted. The parent independently checks the same admission again
from terminal recordings.

The registered pre-event native cursor must be at tick299. Its packet hash,
episode, common-goal identity, effective bearing and cue detector must equal
the actual admitted packet299. Each branch also binds its committed tick300
cursor/detector to packet300, the complete recorded memory inspection and the
published memory_cue bearing. Altered packet hashes, detector tokens/boundaries,
or native cursor boundaries reject; a reported visibility claim alone cannot
admit a branch.

Pure capture geometry at the measured upper position with yaw9 degrees shows
the cue, goal and both landmarks visible while the lower occupancy remains
unobserved. This is a fixture feasibility check, not measured rotation or task
success. The 100-tick bounded preparation has not been validated physically in
the simulator. Initial visibility also does not guarantee continued visibility:
the existing north goal can become invisible during lower-target homing or
resolution. Such subsequent cue loss remains failure under the existing
verifier's failure contract. A visibility-ready start does not establish a
general search mechanism or support invisible-target inspection.

The existing six stages, pinned historical E/U bundles, unknown initial M,
zero-step own-U anchor, U-only invariants, nine targeting baselines, independent
geometry gold, task accounting and first-failure stop remain. Each child retains
the 160s watchdog, 150s internal wall bound, 192MiB recording cap and 1MiB per-stream
logs. The source prefix remains 300 ticks and continuations at most 300 each.
No old v1 recording is modified or silently admitted under v2.

Pure checks:

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest \
  test_memory_transfer test_memory_experiment test_memory_cases \
  test_memory_history test_memory_task test_memory test_records -v
```

Plan-only command (reads historical inputs, creates no run output):

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/verify_memory_transfer.py \
  --repo "$PWD" \
  --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn \
  --output "$PWD/runs/m5-memory-visible-preparation-20261002" --plan-only
```

The future exact bounded gate command is the same without `--plan-only`; it must
wait for root review/commit/freeze and explicit exclusive-runtime GO. Any actual
result requires retained source/branch packets and terminal accounting.
