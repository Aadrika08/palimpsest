# MaleCNS v4 stage S0f — COMPLETED (9 November 2026 UTC)

Owner GO; port T-f (`88c1a0f6`) with historical reader T-h (`0789b2ed`). Builds the v4
navigation corpus manifest from the regenerated S0a–S0e data.

| Item | Value |
| --- | --- |
| Data manifest | `prepared-navigation-advice-research-only`, no claims, sha256 `4a1be0920f01a3d36df4f9a48b7906fefbd4efd128e1ffaa1ff2759a010e2fa3` |
| Old arm | 10 train sources `[277,182,315,245,199,265,243,257,67,67]` = **2,117** rows; dev `[189,338,319,382]` = 1,228; held-out 0 |
| Augmented arm | old prefix + 12 advice `[600,485,496,600,196,600,600,243,198,600,276,186]` = **7,197** rows |
| Identities | 26 unique feature/target hashes; old hashes equal S0c's |
| Schedule derivation (M4 `derive`, dry, no arrays/Torch) | succeeds: 46,080 presentations, 1,440 updates per model; derivation sha256 `81cd9a49…83cb` (`derivation.json`) |
| Pin record | sha256 `635d7ebcbcafece61b84bf49ee3d43cc30cd75e984680b17cfa6367e5cf9cc42` (chain S0a→S0f) |
| Charged CPU | **36.535275 s** (worst case 268); navigation lane **604.510 s** of 14,400 |
| Post-run gate | passed (receipt, pin record, outputs, data manifest arms and hashes, derive dry-load, npz loads with allow_pickle=False) |

Descriptive: the v4 corpus has exactly the v2 corpus's sizes (2,117 old / 5,080 advice / 7,197
augmented). Operator note: a first gate script serialised `derive()`'s tuple-keyed result
incorrectly (operator error); `derive()` itself succeeded on the first call.

Next: implement and review S0z (keyed arrays bundle + compact audit; design risks in MANIFEST),
then S1 (training) and S2 (development, needs the real episode runner).
