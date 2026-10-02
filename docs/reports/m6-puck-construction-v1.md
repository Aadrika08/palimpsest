# M6 puck construction v1: launcher admission failed

The approved construction gate failed before either native owner started. Its
outer launcher held `StorageBudget.lock()` while the inner verifier tried to
acquire the same per-user, nonreentrant writer lease. The guard rejected that
second acquisition with `StorageLimitError`. This is a launcher lease-composition
defect, not a native model, contact or controller result.

The one attempt used frozen source `11ae7d6aaf62ce77fa19ed9b475027dabce90a99`, the
[construction protocol](../plans/m6-puck-construction.json), and the reviewed
retained launcher. Outer supervision ended with exit 1 after **0.171157 seconds**.
Both planned owners remain `not_started`; the inner report was never written.
No native model was compiled, no camera was rendered, and no physics/control
step or policy invocation occurred in this attempt. It was not retried.

The [evidence index](m6-puck-construction-v1.json) pins the unchanged launcher,
prepared plan, primary terminal report, traceback and independent stdlib-only
audit. The audit rehashed all 74 source inputs and all five primary retained
files (20,474 bytes). Source and pinned upstream were clean at admission; the
source inventory still matched after failure. A read-only `/proc` argv scan
found no matching launcher/verifier processes. There are no exact child PID/PGID
receipts because failure preceded native-owner creation; this report does not
invent them or claim retrospective exact-PID verification.

The frozen limits were two owners, zero steps, 60 seconds per owner, 150 seconds
internally, outer TERM at 180 seconds with 15 seconds of KILL grace inside
200-second supervision, 64 MiB output, a 1 GiB free-space floor and 1 MiB per log.
The failed v1 output is retained unchanged. No test or threshold is relaxed.

Root approved preparing a separate v2 launcher that removes only the outer
`budget.lock()` block while retaining its storage checks and bounded logs. The
inner verifier alone will own the lifetime lease. Shared storage code, model
code, the two-owner protocol and all numerical limits remain unchanged; actual
v2 execution still requires a reviewed frozen launcher and a separate GO.
Native construction/determinism, contact stability, pushing, learning and Engine
integration remain unqualified.
