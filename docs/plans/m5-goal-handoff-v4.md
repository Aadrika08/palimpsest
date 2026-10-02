# M5 goal handoff v4: authoritative state guard

V4 corrects the verifier guard and native field access exposed by the retained
[v3 failure](../reports/m5-goal-handoff-v3.md), evidence commit `936b24e`. It does not
change the goal, acquisition, source orientation, case/regime, histories, sensor
limits, continuation driver or task/failure criteria from
[v3 preparation](m5-goal-handoff.md). Preserve all old records. No v4 runtime result
is available at preparation time.

Transfer protocol SHA-256:
`019c8dcc28a03346c306684dbbcee21ebf1e5043c81d349b7a493acf623d6575`.
Goal-handoff SHA-256:
`cd95786316dc1e1df28761659dabfd7018f1b83c20e23200ab7a167247038bb8`.
The command is now explicitly identified as `source-goal-handoff-v4`; it still uses
ordinary paused `intervene/move_goal` at boundary 300, target `[-0.5,-2.7]`, effective
float32 `[-0.5,-2.700000047683716]`, after unchanged source packet 299 and before
shared native capture. All six stages, bounds, U-only invariants and no-retry rule
remain fixed. Use a new output directory rather than rerun or overwrite v3.

The exact physical guard copies and hashes typed `qpos`, `qvel`, `act`, `ctrl`,
`mocap_pos`, `mocap_quat`, `qfrc_applied`, `xfrc_applied`, and `eq_active` when present,
plus simulation time. It hashes unchanged obstacle-map coordinates and
`jnt_range`, `geom_rgba`, `geom_size`, `site_pos`; only the goal site's two XY
entries are masked. Other site entries, including goal Z, must remain identical.
The target map and actual model site XY must equal the declared effective goal.
The existing immutable model identity protects the remaining model fields.
No tolerance or cached-coordinate equality substitutes for this guard.

A `goal_handoff_state` event records pre/post authoritative hashes, complete memory
hashes, applied command receipt, and both world views **before** admission, so a
future guard failure retains its diagnostic distinction. `before_world` is labelled
`cached-before-forward`; `world` is `refreshed-after-forward`; record the derived
pose delta. The previous row-299 next-pose is bound only to the cached pre-command
view. The refreshed view is not declared identical to that earlier cache.
Ordinary `mj_forward` can refresh derived `xpos`/`geom_xpos` without moving qpos.

After the command, obtain a full integration vector using the exact existing
snapshot `mj_stateSize`/`mj_getState` API and `mjSTATE_INTEGRATION` enum. Record its
typed digest and enum; source admission requires them to match the native snapshot's
`integration` and `integration_enum`. This links the authoritative guard witness to
the captured state without decoding serialized byte offsets or copying giant
arrays into JSON. Native goal-map admission reads the real
`environment.values._goal_xy` wrapper with exact float32 dtype/values.

The separate post-move visibility probe remains unconsumed projection metadata,
not `memory_sensed`, E or a detector/cursor advance. Bind state event, applied
receipt and probe ordering to the snapshot event prefix. Real branch packet 300
must expose the moved goal and both candidate landmarks; its goal bearing is
checked against actual world geometry with unchanged range/FOV/LOS. The first
physical action still uses the actual pre-move packet-299 published bearing.

Fixtures reproduce a forward-style derived-pose refresh with unchanged qpos and
real wrapped native fields. They reject actual qpos changes, all protected optional
physical inputs, model/site changes, time advance, altered integration digest,
command receipt, packet/probe or prefix. A failed physical guard emits a state event
but no admitted visibility probe. Small-environment and fake integration API
fixtures are not MuJoCo execution evidence. Reuse existing collector admission,
source evidence linkage, historical E-only refits and exact action checks unchanged.

After root review, freeze and exclusive runtime GO, run:

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/verify_memory_transfer.py --repo "$PWD" --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn --output runs/m5-memory-goal-handoff-v4-20261002
```

Adding `--plan-only` performs no runtime work and creates no run directory.
Keep all failed stages and mark later stages unattempted. This remains a single
development fixture check, with no invisible-goal navigation or held-out/R2 claim.
