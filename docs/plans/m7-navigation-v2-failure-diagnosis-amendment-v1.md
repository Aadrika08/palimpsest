# M7 navigation-v2 failure diagnosis amendment v1

8 October 2026. This amendment permits one replacement invocation after the
original diagnosis failed on its owner-result schema. The canonical
[amendment protocol](m7-navigation-v2-failure-diagnosis-amendment-v1.json)
binds the original protocol, failed execution receipt, failure receipt, failed
analyzer source, corrected analyzer source and the exact one-line correction.
It does not reinterpret the failed invocation.

## Unchanged analysis

The original 24 cases remain in the same order. Numeric fields, thresholds,
case values, per-run measures, terminal classes, aggregation keys, arm order,
pairing rule, input inventory and resource limits are copied verbatim and
individually SHA-256 bound in the amendment. The fixed analyzer differs from
the failed analyzer only by reading the producer's string `outcome` directly:

```diff
-    outcome = result.get("outcome", {}).get("reason")
+    outcome = result.get("outcome")
```

The amended runner may add admission and evidence orchestration around that
fixed analyzer. It may not change trajectory fields, measures, thresholds,
classes, pairing or aggregation.

## Admission before trajectory decode

Before any NPZ trajectory member is decoded, the amended runner must validate
all 24 owner results against the frozen case inventory. Each result must be a
completed recording with the exact four-field case identity, integer executed
tick count, and a string outcome from `goal`, `stalled` or `time_limit` equal
to the frozen outcome. Tests must exercise the real producer contract through
`run_episode` returning a string, `owner_payload` serializing it, and diagnosis
admission parsing it. Object, missing, invalid and mismatched outcomes must all
fail. The complete ledger path set must be rejected if any path names held-out
scene 3120–3127.

The existing full-ledger before/after hashes, input cap, 300-second deadline,
16 MiB output cap, free-space floor, selective six-field decode and forbidden
Torch/MuJoCo/model/physics/camera/snapshot boundaries remain in force.

## One-shot execution

The only allowed destination is the fresh directory
`runs/m7-navigation-v2-failure-diagnosis-amendment-v1-d582eca`. Execution may
begin only after focused tests pass and an independent reviewer who did not
author the one-line correction reports no Critical or Important finding. This
is retained attempt two and the sole amended invocation. Any admission error,
runtime mismatch or analysis failure must leave failure evidence and end this
diagnosis permanently; there is no third attempt.

On success, verification may read only the compact output and committed source
hashes. It must not run the raw analysis again. The report is descriptive and
cannot establish causality, capability, topology, biological validity,
held-out performance, simulator qualification, hardware qualification or R3
completion. `qualification_claims` stays empty and `r3_complete` stays false.
