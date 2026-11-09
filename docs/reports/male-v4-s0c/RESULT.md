# MaleCNS v4 stage S0c — COMPLETED (9 November 2026)

Owner GO 2026-11-09; first port-tree stage (T-c = `7d5fc1f` + listed hunks, port commit
`c06b4976`). Reads S0a/S0b outputs through the recovery-learning copy filled only from their pin
records (`9c0ae9ef…`; independent review: within Amendment 1 declared pins).

| Item | Value |
| --- | --- |
| Data manifest | `prepared-research-only`, no qualification claims |
| Train sources | 10: S0a train `[277,182,315,245,199,265,243,257]` then recovery 67, 67 → **2,117** rows |
| Dev sources | 4: `[189,338,319,382]` → **1,228** rows; held-out 0 |
| Recovery windows | `[32,32,3]` per recovery source |
| Pin record | sha256 `8044fa1ab5a01db56ae19d1c4ee9a63daba8a670297ab42c4ab83f967e7e657c` (chain S0a→S0b→S0c) |
| Charged CPU | **6.377708 s** (worst case 185); navigation lane **200.333 s** of 14,400 |
| Post-run gate | passed (all manifest, pin-record and unit checks) |

Descriptive: 2,117 / 1,228 are exactly the original v2 recovery-learning counts (the hard-coded
values the ports replaced with pinned structural checks). Not a gate.
