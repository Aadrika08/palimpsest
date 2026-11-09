# MaleCNS v4 stage P — PASSED (9 November 2026)

Owner GO (2026-11-09) for the reviewed manifest in this folder (`MANIFEST.md`); protocol sha256
`cd4eb130…d477` (Amendment 1 + erratum 1). Not a scientific attempt.

| Item | Value |
| --- | --- |
| Entry points probed | 21 / 21 **passed** (7 producing commits, 5 port branches, rebuilt S0d/S0e controllers, controls, v4 trainer S1, v4 evaluator S2) |
| v3 failure chain | `verify_endurance` → `httpx` 0.28.1 resolved in S0b–S0f and all five ports |
| EGL | exactly one offscreen context, in the S2 child |
| Data opened | none (audit hook + 90 forbidden roots; Python-level opens only) |
| Charged CPU (cgroup census, navigation lane) | **85.273669 s** (worst case 125; RuntimeMaxSec 120) — above the 30–60 s pre-estimate |
| Navigation lane after P | **87.106 s** of 14,400 (incl. v3 prior 1.832 s) |
| Wall | 86.4 s; unit drained, exit 0 |

Next MaleCNS stages (S0a–S0z regeneration, then S1 training, S2 development) each need a reviewed
manifest and explicit owner GO. The real episode runner for S2 and stage S0z are not yet implemented.
