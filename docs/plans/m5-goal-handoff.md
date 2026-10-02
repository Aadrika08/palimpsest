# M5 development goal handoff v3

This separately versioned preparation repairs the v2 fixture's return from lower
inspection to common-goal guidance. It does not provide invisible-goal navigation.
The retained [v2 failure](../reports/m5-visible-preparation.md) remains unchanged:
blocked occupancy at 354 was observed but its memory revision did not commit.
No v3 runtime result is available at preparation time.

Transfer protocol SHA-256:
`7ed387974a6d81cb48a6c183269b34e6e4cdf5a2dc4621be60053a74a59acc60`.
Goal-handoff SHA-256:
`1d78092ac228875fdbaa3e1abfd3835fac85c0d505640169a9c5f01cef4bd6e1`.

Use the existing six-stage verifier, fixed development-test seed 8/local/change,
source 300 ticks, zero-step own-U anchor, then own/swapped/sham/no-U. Keep both
historical E/U bundle identities, E-only refits, initial unknown M, original case
and acquisition schedule, source ticks 200–299 orientation override, all controller
and sensor limits, continuation velocity 0.65, and previous-published-bearing delay.
No held-out execution, retries, replacement scenes or tuning is allowed.

At paused boundary 300, after the actual source packet 299 and its evidence/visibility
admission, submit one ordinary Engine command:

```json
{"id":"source-goal-handoff-v3","kind":"intervene","expected_state":"paused","expected_episode":0,"expected_revision":"actual current revision","payload":{"kind":"move_goal","xy":[-0.5,-2.7]}}
```

The example revision placeholder is replaced by the actual integer. Require an
applied receipt at the same episode/control boundary, unchanged simulation time,
robot pose, obstacle geometry and complete memory state, and the effective float32
goal `[-0.5,-2.700000047683716]` in both map and model site. Existing intervention
validation supplies clearance and observation refresh. Record the command,
intervention/receipt, actual world, unchanged memory hashes and a separate
`goal_handoff_probe` before initial native capture. The original case initial goal
`[-1.3,2.5]` remains declared; the relocation is explicit rather than a new case.

The post-intervention probe projects actual geometry through unchanged
`capture_symbolic`. Its packet uses boundary 300 only as projection metadata;
it is never logged as `memory_sensed`, passed to `advance_memory`, or used as
historical E. It must show cue token 0, common goal and both inspection landmarks,
with lower occupancy still unobserved. Packet 299 stays the actual pre-move memory
observation and cursor. No detector advance or fabricated observation is allowed.

The shared source snapshot covers refreshed observations, effective goal/site
arrays and the durable event prefix. Admission binds the source proof to the
command receipt, packet projection, actual last recorded next-pose and native
memory. All subsequent U-only forks restore this same world and preserve non-U
invariants. Each real branch packet 300 must show token 1 plus the relocated goal
and both landmarks; verify its goal bearing against actual geometry, range/FOV/LOS.
The first action still uses the previous packet-299 bearing. Later actions receive
only the existing published declared bearing, without pose, map, private truth,
new search inputs or fallback bearings.

Preserve failed terminal recordings and stop at the first inadmissible/failed
stage. List all remaining planned stages as unattempted. Existing queued-only
expected-failure handling is unchanged; an active-inspection failure is not
coerced into an accepted result. Every worker retains the existing 160-second
external/150-second internal bounds, 192 MiB recording cap and 1 MiB log bounds.
The history collector already permits an ordinary goal intervention; reuse its
source admission without changing global rules or fitting the new source.

Pure fixtures check ordinary paused command execution without physics ticks,
unchanged memory, command/effective goal/probe/prefix tampering, actual packet-300
world/bearing mismatch, existing action bindings and first-failure accounting.
Their patched small environment is not MuJoCo evidence. A prior pure projection of
retained v2 poses found the proposed goal visible at all 55 own boundaries 300–354,
but invisible during source ticks 0–254; this supports relocation after acquisition,
not a static initial-goal replacement. Future trajectory/task success remains
unknown, and simple/no-U conditions may also inspect lower occupancy directly.

After root review and source freeze, the fixed gate command is:

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/verify_memory_transfer.py --repo "$PWD" --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn --output runs/m5-memory-goal-handoff-20261002
```

Do not launch it without root's exclusive runtime GO. A plan-only check adds
`--plan-only` and writes no run. Protocol hashes are recorded in every plan,
manifest and worker source identity; use the frozen values rather than v1/v2 IDs.
