# Wheel-response diagnostic v2

The separate v2 run at `796854c` passes its frozen development limits in
88.869 seconds. Eight fresh owners each collect 120 ticks and close normally,
with callback restoration and unchanged sources. Fit support excludes the first
20 settling ticks, leaving 100 per trial and 400 per condition. V1's rejected
contact classification remains retained in its [separate report](m6-body-gain-diagnostic.md).

| Condition | Left gain | Right gain | Pooled relative RMS, left/right |
| --- | ---: | ---: | ---: |
| Baseline | 14.878897911 | 14.878897948 | 0.6582% / 0.6582% |
| Left gear × 0.8 | 11.851776562 | 14.374415787 | 5.8042% / 4.0403% |

Gains are empirical rad/s per actual control. Perturbed/baseline ratios are
0.79655 left and 0.96609 right; the change is coupled, not an ideal isolated
left-wheel scaling. Perturbed per-trial range/mean is 11.9500% left and 3.13385%
right, within the fixed 20% bound but materially direction-dependent. These are
settled development fits, not a universal torque-to-velocity model.

The ownership partition binds the pinned base subtree (five bodies/seven geoms)
to the model digest. All 9,600 timed callback stages and 960 cached-end packets
are retained: 633,600 world-only pairs, 61,472 allowed rover-floor support pairs,
zero unexpected robot contacts. World-only supports may move. This is discrete
pipeline coverage, not continuous collision detection. Radius 0.06 m and track
0.36 m remain unchanged; only left motor gear changes from 3 to 2.4.

The [index](m6-body-gains-v2.json) retains source/protocol/model/ownership and
run hashes. Root checked child hashes, native snapshots and interval coverage;
an independent read-only audit also recomputed the pooled fit from raw rows.
Sixteen logs show no semaphore/resource-tracker/traceback failures; ordinary TF32
warnings remain. No compensation or runtime adaptation is enabled by this result.
A separate predeclared verification must test the frozen gains on new commands.
