# MaleCNS v4 stage S0e — COMPLETED (9 November 2026)

Owner GO for all four units (reviewed manifest; the review's S0f-safety fix `4d95f77` applied).
Port tree T-e (`703acc50`); advice collection with the regenerated S0d learners 10/11/12 on
scenes 3100–3103; development only, no v4 dev/held-out scenes touched.

| Unit | Result | Charged CPU-s |
| --- | --- | --- |
| S0e launch | `completed-collection`, 12/12 owners, wall 252.3 s | 208.306704 |
| S0e-D drain | `drained`, exit 0, no survivors | 0.056342 |
| S0e-A raw audit | `passed`, `not_covered: []`, no native/model import | 28.694932 |
| S0e-I index | `published` (7 immutable inputs) | 0.059353 |
| **Total** | | **237.117331** |

Navigation lane after S0e: **567.975 s** of 14,400.

Advice ticks per case (learner-3100…3103 × seeds 10/11/12):
`600, 485, 496, 600, 196, 600, 600, 243, 198, 600, 276, 186` (all ≤ 600).

Hashes: collector pin record `2eb64603ba837ac495a75081e11add57fddbdf0b55a70d70b59f107840e84af0`; controller record `32a854e61d2284a0b63b77069870524b79c98f7b9b3950ffdb6e750a7d7eb827`; collection index `3d0ea26c9b4a9293f39d7b54e1e90c52f55bfb07eefec36ea1c8fd7d7ff90972`.

Post-run gate: passed in full (enclosing/terminal, inventories, cleanups, report, collector pin
record chain S0a→S0e, drain, audit incl. `audit_passed()`, index inputs, four receipts and ledger
rows, `previous_chain` for S0f, S0f contact-v2 dry-load against T-f, graphics stack unchanged).

**Observation (descriptive, not a gate):** the 12 regenerated advice lengths are identical,
element by element, to the lost v2 corpus's advice lengths recorded in the v3 protocol
(`600, 485, 496, 600, 196, 600, 600, 243, 198, 600, 276, 186`). Together with S0a (8 teacher
lengths), S0b (67/67) and S0c (2,117/1,228), the regenerated chain reproduces the original
episode dynamics on this host, while file bytes (run IDs, latencies) differ.

Operator note: during the gate a `previous_chain` call with the non-port stage map refused
(operator error); the correct port-aware call succeeds. Nothing was executed or written by it.

Next: fill the data-v2 copy from the S0e records, then the S0f manifest, review and owner GO.
