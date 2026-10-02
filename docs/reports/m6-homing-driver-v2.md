# M6 separate manual homing driver v2 observation

The single declared v2 development path passed actual home closure: true distance
0.1524490 m was within the predeclared 0.25 m evaluator gate, with estimated
distance 0.1075682 m and `task_completed` after 300 ticks. This is an artificial
manual previous-bearing fixture on one development path, not learned competence,
held-out generalization, true stopping or complete M6 qualification. The earlier
[v1 actual-home failure](m6-task-development.md) remains unchanged.

At unchanged `2cfaa2097d10dd098bde675bd4ac37c4949572b4`, one invocation completed
in 63.052259 seconds, exit 0. V2 turns in place with heading capped ±0.4 while
cue angle magnitude exceeds 0.1; otherwise it commands forward 0.4 with that angle.
Initial/neutral cues command zero. It reads only the previous recorded effective
bearing. Original radius 0.06 m, track 0.36 m and nominal quantized odometry stayed
unchanged. No fitted coefficients or true-pose correction entered online control.

| Check | Actual observation |
| --- | --- |
| Declared outbound/home/dwell completion | Passed, 300 source ticks |
| Isolated evaluator actual-home gate | 0.1524490 m <=0.25 m, passed |
| Native paused tick-8 outbound snapshot | Four continuation ticks/task states matched |
| Full actions replay | 300 ticks matched |
| Full policy replay | 300 ticks matched; manual command timeline, not learned policy |
| Source/script/runtime identity | Unchanged; source recording immutable |
| Owned process/recording cleanup | Four completed owners/exit 0; four completed manifests |

Continuation used exact cameras/integers and `atol=rtol=1e-6` floats. Maximum
encoder-versus-true local position error was 0.1622430 m. During counted dwell,
maximum per-tick actual translation was 0.0000410993 m and yaw change 0.00000396185
rad. These measurements do not establish exact body rest from quantized encoders.

The [immutable raw report](../../runs/m6-homing-driver-v2-development/report.json)
has SHA-256 `a6c90d137c2c714abd454a9f67e4caf6e818ce3bcd5f4c34c654571498f7a703`.
The [compact artifact index](m6-homing-driver-v2.json) retains invocation,
source/script identities, snapshot/replay/lifecycle results and file hashes without
duplicating raw evaluator rows. Script SHA-256 was
`ec94a0a95d3e90ed9f9a008025b08d8da72949637144782655273d254948668b`.

No scoped worker command line remained after completion, and no semaphore warning
or traceback appeared; each native stderr log contains the common Torch TF32 API
warning. Supervisors lack persisted PID/start-time identities, so process waits
and this finite check do not prove every possible transient descendant. No retry
or tuning followed the observation.

The independent [fixed-trial calibration](../plans/body-calibration-development.md)
excluded settling intervals and does not validate all mixed/transient dynamics.
Snapshots during turning/home arrival/dwell and exploration target/dwell,
additional development trajectories, held-out paths/layouts, learned-policy task
performance and body-adaptation integration remain separate pending work.
