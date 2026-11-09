# MaleCNS v4 stage S0a — COMPLETED (9 November 2026)

Owner GO 2026-11-09 for `MANIFEST.md` (reviewed; amendments applied). Producer
`collect_male_teachers.py` byte-identical at `cc1cea9`, development teacher stage only.

| Item | Value |
| --- | --- |
| Status | collection `completed`, stage `development`, 12/12 runs `completed`, every run reached the goal |
| Seeds | train 1000–1007, dev 1008–1011 (in order); no held-out entries |
| Per-source ticks | train `[277, 182, 315, 245, 199, 265, 243, 257]`; dev `[189, 338, 319, 382]` |
| Pin record | `pin-record.json` sha256 `d8e511b8d8095c8d781a0ecfb2b031571c4f6fd72d0367b88520643d0f653901` (published before any consumer) |
| Charged CPU (navigation lane) | **97.377754 s** (worst case 1,265); wall 152.0 s; peak memory 1.32 GB |
| Navigation lane after S0a | **184.484 s** of 14,400 |
| Assets | unchanged (sha256 before/after identical) |
| Graphics stack | `mesa 1:26.2.5-1`, `libglvnd 1.7.0-3` (unchanged) |
| Raw output | 614 MB, local only (`palimpsest-authored-test-evidence/male-v4-runs/S0a/collection`) |

**Observation (descriptive):** the regenerated train lengths equal, element for element, the
first eight old-arm source lengths recorded for the lost v2 corpus
(`277, 182, 315, 245, 199, 265, 243, 257`; v3 protocol). Episode dynamics reproduced on this
host although file bytes (run IDs, latencies) differ. This is not used as a gate.

Post-run gate (manifest review amendment): **passed**. Next: S0b (recovery collection,
CPUQuota k=2 per owner decision 7) needs its own reviewed manifest and owner GO, citing this
pin-record sha256.
