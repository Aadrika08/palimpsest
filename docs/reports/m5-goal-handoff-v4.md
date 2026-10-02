# Goal handoff v4: recorded development mechanism check

At frozen `03ac888`, all six stages complete and the verifier reports
`mechanism_checked`, unchanged source, exit 0. The independently revalidated
recordings contain 804 numeric ticks, 165,424,026 bytes and 38 manifest/event/chunk
files. The retained outer supervisor records 70.348526107 seconds. All owners close
normally with `operator_closed` and no cleanup error. This is one development case,
not held-out evaluation or R2 completion. Earlier v1/v2/v3 negative records remain
unchanged.

| Stage | Numeric ticks | Selection and inspection | Evaluator outcome |
| --- | ---: | --- | --- |
| Source | 300 | Unknown initial M; actual open evidence lower 29, upper 299; paused handoff | Paused at 300 |
| Own-U anchor | 0 | Exact own U; no step | Paused at 300 |
| Own U | 126 | Correct lower target; requested/started 300, resolved 354 | Lower repaired 354; goal 426; task passes |
| Swapped U | 126 | Wrong upper target; refreshed directly at 300, no inspection route | Lower repaired directly 354; goal 426; task passes |
| Sham | 126 | Same target and inspection as own | Same repair/goal/task as own |
| No U | 126 | Abstains; no inspection route | Lower repaired directly 354; goal 426; task passes |

Task scores above come from `comparison.runtime`, independently recomputed from
terminal navigation outcomes, final evidence and evaluator-only geometry. Every
worker's conservative `task_pass=false` placeholder remains unchanged; it is not
that evaluator score. All four runtime scores have navigation/revision/task true,
no timeout or unresolved request, and evidence-backed final lower blocked/upper
open. Final lower evidence is 385 and upper evidence 314; freshness here means an
observation after the trigger, not a new observation on the final frame. The
existing simulator goal condition terminates at final distances 0.789975 m
(own/sham) and 0.789501 m (swapped/no-U).

The paused source command applies at 300/revision 301, changing only the declared
goal to effective float32 `[-0.5,-2.700000047683716]`. Authoritative pre/post state
hashes match exactly (`5670d66d…`), complete memory hashes match (`e846b255…`), and
the post-intervention integration digest binds to the native snapshot, enum 8191.
The actual cached-to-refreshed pose delta is
`[-1.3113021850585938e-6,6.556510925292969e-7,0]`; it is explicitly distinguished
from physical movement. The separate actual visibility-only probe, command receipt
and state event lie within the source's durable native event prefix. That probe
never enters E, memory sensing or the detector/cursor.

Recorded source packet 299 and every branch's real packet 300 meet visibility
admission. All six native snapshots preserve the same non-U invariants; initial
U identities independently match source/no-U empty, anchor/own/sham historical
local U, and swapped historical paired U. Both immutable historical bundle hashes
and exact E-only refits pass. Every source action/override and continuation action
matches the declared float64 manual conversion and previous-published-bearing
contract. No private pose/map/gold input is added to continuation control.

Own/sham commit reconsideration at 300 and blocked occupancy plus inspection
resolution at 354. The relocated common goal is visible at that handoff. Swapped
and no-U also encounter the lower passage on their ordinary common-goal path and
commit the same blocked sample at 354. Own/sham match bitwise across all 126 tested
numeric/camera fields; swapped/no-U likewise match bitwise physically. Own versus
those controls diverges in published sensors at 300 and subsequent actions, but
all finish in the same 126 continuation ticks. Thus U changes targeting and
inspection state; this fixture shows **no task-success, lower-repair-timing or
completion-tick advantage** for own U. Goal attainment does not demonstrate crossing
the blocked aperture.

All nine targeting scores are independently recomputed with target budget one and
declared differing access. Own, sham, hand-authored, history-independent, traversal,
retrieval and oracle select the gold lower fact; swapped misses it and no-U
abstains. Only four conditions execute embodied continuations. One case that
matches simple baselines establishes no useful-memory/generalization effect;
branch frames are correlated, not independent samples. Operator blindness is not
verified, and the source acquisition uses declared privileged manual pose control.

The [evidence index](m5-goal-handoff-v4.json) contains full stage identities,
recording/snapshot/worker hashes, source/protocol/history pins, handoff proof,
revision timing, nine access budgets and exact parity checks. Retained primary
artifacts under `runs/m5-memory-goal-handoff-v4-20261002`:

- `transfer-plan.json`: `675ebbc5d3d435c87ae1b810288fbef54dbb48a879c313ec47f70e0a1867ad6b`.
- `transfer-report.json`: `09ec6deca4ab567b60ed84b5f58c6e8224753fb68643b2dc63f7e5d82b3793e0`.

The audit used only retained readers, hashes, pure geometry/selection and native
snapshot parsing. No runtime, replay, raw-data mutation or frozen source change
was performed.
