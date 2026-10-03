# One new actuator body: calibration and encoder homing

The fixed v2 study passed on source `1e904c0`: four calibration trials used 480
control intervals, followed by a fresh owner completing encoder homing in 283
intervals. The measured final distance to the start was **0.091607 m**, below the
unchanged 0.25 m evaluator limit. The private task reached its outbound condition,
returned within the estimated-home radius and completed five stationary
quantized-encoder dwell ticks. The original Engine outcome remained `None`.

This is one simulated actuator-body case (left gear **2.1**, right **3.0**) and one
fixed development route, following fresh calibration. It is not zero-shot or
population generalization, a comparative task-benefit result, physical evidence,
learned puck competence or closure of all M6 requirements. The preserved
[v1 initialization failure](m6-new-body-response-v1.md) is not reinterpreted.
[The compact evidence index](m6-new-body-response-v2.json) binds controls, raw
ledgers, the fit, terminal receipts and all checker attempts.

Each 120-interval calibration trial contributed its last 100 samples. The 400-row
zero-intercept fit produced gains of **10.47633445** and **14.27151557** rad/s per
control unit, with relative RMSE **0.07130284** and **0.04103654**. Between-trial
gain ranges divided by their means were **0.15490922** and **0.02923115**, within
the unchanged 0.2 bound. The second owner consumed this exact frozen fit. Its
controller received only the previous float32 study cue derived from quantized
encoders; native pose, evaluator closure and upstream true-goal bearing remained
outside that action path. Root independently reconstructed all 400 fit samples,
checked a separate `fsum` least-squares calculation, and reconstructed all 283
task, cue, hold, requested-action and compensated-control transitions.

The raw checks covered **763 rows and five raw initial SNPs**, all ten discrete
contact callback stages per row and the end cache. The recorded classifications
contained 503,580 world-only and 46,712 allowed ground-support incidences, with
zero unexpected robot-contact incidences. These count repeated stages and caches,
not unique physical contacts. Cache arrays exactly match stage nine; cache times
use the existing 1e-9-second tolerance against accumulated simulation time.
Raw initial default Engine envelopes, event prefixes, cameras, sensor projection
and original/actual world and model identities were checked. Full-model hashes
remain bound producer observations: these audits did not deserialize native
model bytes. The five SNPs do not qualify private task/fit restoration, native
continuation or generic replay.

Exec session 24620 drained with exit 0. The owners took 30.579450 and 22.495598
supervised seconds; the enclosing child took 57.061437 seconds. The enclosing
receipt's 59.383577 seconds is measured before publication, not process return.
All five sampled PID/start identities were absent, both samplers stopped, and no
forced signals, survivors or sampler/finalization errors were reported. The home
writer lease was available after drain. Sources and controls stayed unchanged;
the entire 45-file v1 control family, including bytecode and its failed preflight,
also remained unchanged. Reported study storage was 170,063,490 bytes.

Source and control checks passed 18 and 12 tests respectively. The local retained
raw audit passed in 2.238284 seconds after one preserved checker correction: the
snapshot sensor dictionary needed the pinned Engine's four-value float32
projection. Root's outcomes audit passed on its first execution in 1.636240
seconds. Its raw audit passed in 7.335370 seconds after two retained checker
failures: an invocation omitted the pinned environment, then an assertion used
exact cache-time equality instead of the declared tolerance. Original scripts,
logs, failure receipts and corrected checks are indexed. These were read-only
checker reruns, separate from the single actual v2 study invocation; no native
experiment, source or raw data was repeated or changed.
