# M4 development world adapter

Own files: `memory_world.py`, `test_memory_world.py`; no runtime qualification.

API: `initial_state(*, close_subject_id='passage-a', change_tick=10)`,
`validate_state(state)`, `initial_facts()`, `validate_layout(positions=None)`,
`passage_status(occluders)`, `configure(env,state)->state`,
`advance_world(env,state,tick)->(state,events)`,
`sensing_inputs(env,state)->(world,pose,occluders)`; export `PROFILE_SHA256`.

Pinned arena half-width 7m, twenty actual radius .4m cylinders, body clearance
radius .3m. Posts indices 0–2: (0,-2),(0,0),(0,2). Gates indices 3/4 park at
(2.5,-1)/(2.5,1), close at (0,-1)/(0,1). Others use x={3.7,4.9,6.1},
y={-5.6,-4.4,-3.2,3.2,4.4}. Start (-2.5,0,yaw0); goal site (-1,0).
Declared virtual cue (-1.2,0), inspection markers (-.8,±1); no new model geoms.

Passability is the existence of a straight horizontal body-center crossing
from x=-1 to1 within the lower [-2,0] or upper [0,2] aperture. For each actual
circle compute dx=distance(x,[-1,1]); only dx<r+.3 contributes forbidden y
interval y±sqrt((r+.3)^2-dx²). Union intervals; uncovered space means open.
This labels a local crossing, not whole-world reachability. Truth never derives
from U or the requested schedule. Symbolic packet projection enforces visibility.

State is bounded plain JSON: version,profile_sha256,cue_state,change_tick,
close_subject_id,applied,gate_result,last_tick. Tick0 then consecutive ticks;
same tick is idempotent, stale/invalid/skipped ticks fail. At tick10 default
cue flips; gate placement can fail explicitly without changing the geometry.
Null close_subject_id flips only the cue. Scheduled mechanism stays world-only.

`configure` is reset-only, uses existing slide qpos/qvel, locked joint ranges,
obstacle cache and goal site position, asserts actual pinned radii, refreshes
forward dynamics/cache/previous pose/speed/action/exploration baseline. Engine
refreshes observations externally. Restore uses existing physical snapshots and
validated worldstate rather than calling configure. Reset initializes schedule
again while Engine preserves current E/U. M starts unknown; no synthetic known
seed or history is presented as physically acquired evidence.

Pure checks do not load MuJoCo/EGL/torch/models. Actual acquisition, policy
continuation and outcomes remain for the root's exclusive runtime gate.
