# M7 first closed-loop evaluation: rejected batch

The frozen evaluator at `039119b` attempted the first planned owner, original
model / scene seed 120. The batch failed validation and did not run the remaining
15 rows. There is no paired or complete-batch result.

The owner itself completed 268 ticks and naturally stalled, with recorded final
goal distance 7.760767459869385 m. Its manifest is completed/operator_closed;
the supervisor recorded closed status, exit code zero and no live owner. The
external parent exited one after 22.025696216 seconds. These are distinct from
the evaluator's failed status.

Validation rejected the first input hash because the evaluator constructed a
float64 sensor vector while Engine records the declared sensor projection as
float32. An independent read of the initial snapshot and retained first row
confirmed exact equality of both RGB cameras and the float32 Engine projection.
Both corrected input hashes are
`69b6d911e2b91788a1f160eaae763de4f89a0d8f90471868331c27594f43cd67`.
The fixture had used float64 too and missed that representation mismatch.

Finalization also recorded `ValueError: process object is closed`; consequently
its shutdown/source-recheck fields were not written. A separate root audit
confirmed all source hashes still matched the frozen inventory before any repair.
No evaluation owner or resource-tracker process remained in the subsequent
process inventory. A lightweight completed-owner reproduction then isolated the
cleanup defect: supervisor shutdown completed and disposed its process handle;
the evaluator subsequently queried that closed handle. No shared supervisor fix
was needed. The separately versioned evaluator captures terminal facts before
disposal and runs evidence checks independently after cleanup failures. Twelve
pure checks pass, including actual float32 records and a disposed-handle fixture;
this repair does not change the v1 batch's failed status.

The original protocol, report and recording remain unchanged. Any subsequent
evaluation uses a separately versioned protocol and new scene seeds. The stalled
episode is retained, never replaced or counted as a successful complete batch.

Local evidence:

- `runs/m7-male-closed-loop-v1-20261002/evaluation.json`, SHA-256
  `379c7a5f3775a3c5b71c4dfcfc1ab9084fca9a438c661c820abf9906b039bc6d`.
- Owner `84909fa80f484c01a9bd7d2f55060e96` under that directory's `runs/`.
- `root-failure-audit.json` retains snapshot/recording sizes and hashes, exact
  camera/sensor checks and the independent source inventory.
- `runs/m7-male-evaluation-launch-039119b/` retains bounded logs, command and
  outer supervision. TERM/KILL limits were not reached.
