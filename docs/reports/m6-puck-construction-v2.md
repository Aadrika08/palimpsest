# M6 puck construction v2: pre-install task-bound admission failed

The separately approved v2 gate failed on its first owner before compiling the
derived puck model. `_admit_owner` called `native_state`, whose authored-world
validator requires the goal within ±5. The pinned upstream constructor first
samples its temporary goal within ±5.5 (`arena=7`, margin 1.5). Applying the
authored task bound before installing the fixed model and authored layout was
an admission defect. The reported error was `ValueError: Goal outside fixed
arena`. The actual sampled coordinates were not retained; they were not
recovered by rerunning the constructor.

The attempt used frozen source `1828d2fd72ce5bf702db9f034dd56bb17cdf35ea` and the
unchanged [construction protocol](../plans/m6-puck-construction.json). Its
launcher corrected the [v1 outer-lease failure](m6-puck-construction-v1.md).
Outer supervision ended with exit 1 after **1.575148 seconds**; the inner verifier
ended after **1.396989 seconds**. The baseline constructor completed, including
its baseline compilation/reset rendering. No derived model or retained camera
artifact was produced, no control/physics step occurred, and the second owner
remained `not_started`. This was one attempt, without replacement or retry.

The [evidence index](m6-puck-construction-v2.json) pins the launcher, prepared
plan, primary reports and independent stdlib-only audit. The audit rehashed all
74 source inputs and 11 primary retained files (33,450 bytes). Source hashes
were unchanged and both finalization-error lists were empty. The baseline
renderer was closed; PID 487473, start tick 5972556, and its process group were
absent in the independent audit. Root independently verified the retained inner
inventory and process identity. The actual slot was released.

The failed raw output remains unchanged. Root authorized a source-only split
between generic native/reset admission and authored task validation. The next
fixture must accept a valid constructor goal between 5 and 5.5 while preserving
the task's ±5 rejection; neither the seed nor any task parameter changes. A
fresh pinned gate requires separate review and execution approval. The two
owners, zero steps, 60-second owner/150-second internal/180-second TERM plus
15-second KILL grace/200-second supervisor limits, 64 MiB storage, 1 GiB free
space floor and 1 MiB logs remain fixed. Native construction/determinism,
contact stability, pushing, learning and Engine integration remain unqualified.
