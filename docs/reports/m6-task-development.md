# M6 manual task development evidence

**Actual home closure failed.** The encoder-homing supervisor reported completion
at an estimated home distance of 0.0897618 m, while the isolated evaluator measured
1.5006287 m from the true start. The retained verifier's `passed` result covers its
declared estimated-state, snapshot and replay checks; it does not qualify actual
homing, learned competence or M6 release.

One invocation on unchanged `05d788b7485a216e3592ef71d74ebb2d23118c96` completed
in 101.513572 seconds, exit 0. The fixed artificial manual driver used only the
previous recorded effective bearing, starting with zero action. No retry,
parameter fitting or runtime changes followed the result.

| Development profile | Recorded source result | Native continuation | Executable replays |
| --- | --- | --- | --- |
| Exploration landmarks | Both declared IDs inspected; `task_completed`, 182 ticks | Four ticks from paused tick-8 snapshot matched | Actions and policy each matched all 182 ticks |
| Encoder homing | Estimated arrival/dwell `task_completed`, 197 ticks; actual home closure failed | Four ticks from paused tick-8 snapshot matched | Actions and policy each matched all 197 ticks |

Continuation used the existing exact camera/integer comparison and float
`atol=rtol=1e-6`, with complete task-state comparison. Source recordings remained
immutable. Here policy replay re-executes the manual controller's recorded command
timeline; it is not a learned FLYNN task result.

The loaded body has radius 0.06 m, track 0.36 m and the declared encoder quantum
0.001 rad. Positive shaft rotation and forward body displacement were observed
on straight intervals in both profiles. Exploration's maximum encoder-versus-true
local position error was 0.019714 m; homing's was 1.445710 m. Maximum measured
per-tick translation during counted dwell was 0.000038147 m and 0.000017047 m,
respectively. These small motions still preclude an assertion of exact body rest
from zero quantized shaft increments.

## Read-only homing diagnosis

All 197 recorded `task_sensed` angle pairs equal the evaluator's measured angles
exactly. Replaying the existing quantization and stdlib odometry reconstructs
every evaluator estimate and recorded `task_inspected` odometry exactly, with
maximum discrepancy zero. No acquisition, quantization or integration error was
identified.

The no-slip yaw estimate diverges during high-amplitude turning. Over the run,
raw shaft increments predict −3.028027 rad versus actual −1.565932 rad. The 15
zero-forward turning intervals predict −1.928804 rad versus actual −0.761540 rad.
At tick 74, shaft increments `[+0.54580855, −0.45261141]` predict −0.16640333 rad
using the loaded dimensions; measured yaw changes −0.06596149 rad. Significant
turn signs agree. Later near-straight travel preserves the resulting heading
offset and grows the position error. The records support failure of the no-slip
turn relationship, but do not isolate wheel slip from other 3D contact/dynamic
effects. A sign reversal or a universal effective-track correction is unsupported.

## Evidence and cleanup

[Raw terminal report](../../runs/m6-tasks-development-20261002/report.json), SHA-256
`cc0d263d04d28d737ef9241c2ad7a1d39fc9d7332ec5e8ad0dc9e57a8314d53b`,
is retained unchanged. The [compact JSON index](m6-task-development.json) records
the exact invocation, source/script identities, per-profile results, audit and
60 artifact hashes without duplicating raw evaluator rows. Script SHA-256 was
`77b647f96da6248402986098a9d1f0076712a10d5f0013ca1459f8ccecfd208e`.
All eight bounded owners exited 0 and all eight recording manifests completed.
No scoped worker command lines remained after completion; no semaphore warnings
appeared. Each stderr log contains the same Torch TF32 API warning. Supervisor
files do not retain PID/start-time identities, so cleanup evidence is limited to
the observed process waits and finite command-line check.

One progress snapshot per task does not cover target dwell or both homing phases.
Held-out paths/layouts, physical sensors/stopping and learned-policy behavior
remain unqualified.

## Proposed next independent experiment

Before another homing demonstration, predeclare bounded low-amplitude straight
and left/right turn calibration trials, with separate transient and settled
intervals. Evaluate raw shaft increments against measured body translation/yaw
offline. Preserve physical radius/track separately from any proposed empirical
turn coefficient. Require agreement across direction and amplitude, with explicit
residual bounds; reject a constant coefficient if contact dynamics prevent that
agreement. Any accepted coefficient needs a new declared calibration identity
and separate validation paths. True pose must remain evaluator-only, never an
online correction or driver input. This proposal has not been implemented or run;
the failed homing path supplies diagnosis, not calibration data for a qualified
replacement.
