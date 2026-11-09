# Puck v4 stage S1 attempt 2 — ADMITTED (9 November 2026)

Protocol: Amendment 1 (sha256 `8d852971…b20f`), approved by the owner 2026-11-09 after
attempt 1 refused (`../puck-v4-s1-2026-11-08/`). GO for attempt 2 and its D8 audit granted
the same day; D2 (scope S1) carried to Amendment 1 (`d2-scope-s1-amendment1.json`).
See `MANIFEST.md` for the frozen-window procedure that preceded execution.

| Item | Value |
| --- | --- |
| Verdict | **admitted** (report sha256 `406438fe…94cf`) |
| Typed collisions / ambiguous | **0 / 0** |
| Non-scene asset mentions | 63 — all the single allowlisted content (`52c1b234…`) |
| Untyped mentions (diagnostic only) | 3,038 |
| Reservation | scenes 6510–6513 (collection), 6520–6523 (development) |
| Held-out IDs observed as text (D2 byte reads) | 6200–6207, 235 occurrences each; nothing loaded or compared |
| Charged CPU (cgroup census, puck lane) | S1 attempt 2 **86.457007 s**; audit **0.064385 s** |
| Puck lane total after attempt 2 | **173.197 s** of 18,000 (attempt 1: 86.676 s) |
| Pre-run checks | calibrated projection 451.1 + preflight 15.1 = 466 ≤ 528 CPU-s; declaration rebuilt; advertisement unchanged |
| D8 audit | passed |

This admits scene IDs for later stages; it is not a capability result. The next puck stages
(S0a–S0d regeneration, mechanism, collection, development) each need a reviewed execution
manifest and an explicit owner GO.
