# Selected memory pilot v2 software

The approved six-case/four-condition pilot now has a distinct opt-in protocol,
30 frozen owner slots, byte-only admission from the passing v3 close, a bounded
registration preparer and one original-clock launcher. Existing controller,
world, sensor, task, historical U and legacy worker behavior are preserved.
The current prerequisite/inventory helpers and diagnostic must match their old
pins; runtime/executable identity must match the admitted v3 registration exactly.

The driver retains complete inline audits in separate bounded owner files and
uses compact references in its receipt. Independent close re-reads jobs,
supervision, raw records and source SNPs, accounts for partial allocations,
recomputes own/sham/opportunity and mechanism predicates, and checks original
clocks, owner exits and final inventories. Only an admitted natural continuation
failure receives900; incomplete infrastructure receives no task score.
Independent full audits live under the counted publication root so readback
leaves the raw-output inventory unchanged. R2 remains false, claims empty and
held-out unused on every result.

No new dependency/framework was added. The shared restore supervisor has one
additional campaign mode; the selected wrappers reuse its foreground watchdog,
original clock and owner cleanup. Preparation180 seconds includes the commit;
invocation is6000 seconds plus at most600 seconds of independent close, hard
ancestor6600 seconds. Max30 owners,8GiB aggregate,2GiB continuing floor,
64MiB headroom, zero retries/corrective studies. The resource projection is an
estimate and preserves full individual recording caps; it guarantees no owner count.

## Software evidence

The first baseline lacked the required CPU/EGL environment:32failed61passed;
its corrected rerun passed93. Focused admission/terminal/registration/launcher/
pipeline checks subsequently passed112 in106.59 seconds. An initial bare suite
reported3failed1137passed24skipped293.08 seconds; all failures were child-process
ModuleNotFound errors from the reused environment, so explicit checkout
PYTHONPATH was added to the invocation, without an unrelated source change.
The original logs remain retained.

One independent whole-branch review found0Critical/3Important issues: exact
runtime equality, current helper pins and native float32 action threshold.
Six regression cases failed before the narrow fixes (7.18 seconds;49.04 wall
seconds includes waiting for the shared lease). Final fullsuite1146passed24skipped287.41seconds, exit0 (292.186seconds outer); validation is recorded in
[full-suite-final.json](full-suite-final.json) and [full-suite-final.log](full-suite-final.log).
Skips are software opt-in limitations, not project capability evidence.

Reproduce from this checkout with the existing Python3.11 simulation/dev setup:

```sh
export PYTHONPATH="$PWD/src:$PWD"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1
export MUJOCO_GL=egl CUDA_VISIBLE_DEVICES=
python -m pytest -q
```

The software and review receipts precede registration/native execution. They
neither qualify a native pilot nor replace missing project capability or human
artwork/operator acceptance. Original prerequisite evidence remains immutable.
