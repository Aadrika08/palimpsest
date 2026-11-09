# MaleCNS v4 stage S0b — COMPLETED (9 November 2026)

Owner GO 2026-11-09 for `MANIFEST.md` (reviewed; amendments applied and enforced: GO binding
verified, no placeholders). Producer `collect_male_recovery.py` byte-identical at `c382c86`,
CPUQuota k=2 (owner decision 7). Chained to S0a pin record `d8e511b8…3901`.

| Item | Value |
| --- | --- |
| Status | driver `completed`; report `passed`; cases recovery-north-2100, recovery-south-2101 |
| Per-source ticks | 67, 67 (bound 120) |
| Pin record | sha256 `b3511f1a3bf625dd4cec20733317b5288bb965cde6873fbb1023a768e02809cb` |
| Charged CPU (navigation lane) | **9.471548 s** (worst case 970); wall about 11 s |
| Navigation lane after S0b | **193.955 s** of 14,400 |
| Post-run gate | passed: chain [S0a, S0b], previous/GO hashes, report and both results hashed, one run dir per case, receipt drained, ledger charged |
| Assets / graphics stack | unchanged / `mesa 1:26.2.5-1` |

Descriptive: 67 ticks per recovery source equals the hard-coded count in the lost v2 pipeline
(`prepare_male_recovery_data.py`: 67 rows per recovery source). Not a gate.

Operational note: before the launch, a manifest-extraction mistake re-ran the plan-only command
once (no producer, no launcher unit, nothing written or charged); verified by ledger, receipt and
output-root absence before the real launch.
