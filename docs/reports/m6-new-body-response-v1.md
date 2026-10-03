# New-body response study: retained initialization failure

The single approved attempt on `4c4bca2` failed infrastructure admission in the
first calibration owner, before any control interval or snapshot. Its exact
error was `ValueError: Undeclared native model mutation: jnt_range`. Homing stayed
`not_started`; no fit or functional task result exists. The protocol and all raw
failure bytes remain unchanged. [The compact index](m6-new-body-response-v1.json)
pins the original reports, complete retained ledgers, controls and both audits.

The frozen source passed 17 pure checks and the controls passed 12 mocked checks.
Those checks did not expose this actual float32 coordinate boundary. The final
read-only preflight first failed because its invocation omitted `MUJOCO_GL=egl`
and `OMP_NUM_THREADS=2`. That receipt is retained. Correcting only the invocation
to the exact admitted environment passed; the actual study then launched once.

Exec session 7624 drained with exit 1. Calibration recorded zero accepted and
zero executed ticks; the recording closed normally with four initialization
events. A completed recording manifest means the writer closed, not that the
study passed. The owner reported 4.385625 seconds, its supervisor 5.191246 seconds,
and the enclosing child supervisor 7.397053 seconds. The enclosing receipt's
8.974802 seconds is measured before publication, not the process-return duration.
All four sampled PID/start identities were absent after drain, with no forced
signals, survivors, sampler errors or finalization errors. Root separately
verified the writer lease was free.

The local NumPy-only retained audit passed on its first execution in 2.206547
seconds. It rehashed 523 tracked files, 122 pinned upstream files, 20 asset files,
17 protected source pins and all retained control/output files twice. Root's
independent audit passed in 2.479265 seconds after correcting one checker-only
event-name assumption: the original checker expected `source_revision` where the
pinned Engine and raw event say `environment`. Its first script, log and failure
receipt are preserved. Neither audit constructed a model, imported MuJoCo/Torch,
replayed data or repeated the study.

The supported defect is in the verifier's guard caller. `memory_world.configure`
writes joint ranges using the declared Python-float layout, then copies positions
into the upstream float32 `_obstacle_xy` cache. The new verifier reconstructs its
expected float64 ranges from that rounded cache. In the retained literal fixture,
authored `3.7` becomes `3.700000047683716`; each reconstructed endpoint shifts by
approximately `4.76837e-8`. The unchanged exact guard rejects that cache-derived
range and accepts the original authored coordinate. This is source and NumPy
evidence; no native model dump was retained before the failed guard, so it is not
a retrospective native-state reconstruction.

The proposed narrow correction is to bind the guard to the same declared authored
layout and validate the float32 cache separately. This report does not apply that
correction or qualify a retry. Calibration, encoder homing, true closure and
contact coverage remain untested in this attempt; M6 and physical qualification
remain open.
