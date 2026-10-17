# Attempt-11 independent controls review 01: NO-GO

**Range:** `1126b71..d83dab3`. **Reviewer:** separate read-only review agent.
It did not run admission, guards, observer, auditor or qualifier, and wrote nothing.

## Critical: the preparation01 staged forest no longer exists

The host rebooted after runtime10: boot 0 started 2026-10-16 21:33 IST, and
runtime10 ran at 10:59 IST. `/tmp` is tmpfs, and `/tmp/palimpsest-puck-cpu-held-01`
is gone. Preparation01 bound its four staged roots by tmpfs identity (device 55,
inodes 1831915–1831918).

- The pre-admission guard never checks the stage parent, so it would pass.
- Admission11 would then fail at `-11-admission.py:628` (forest → `directory(stage_parent)`
  → `FileNotFoundError`), consuming the attempt.
- Runtime11 and the v5 auditor need the same roots
  (`qualify_puck_cpu_held_runtime.py:547`, `verify_staged_roots`).
- Recreating matching identities would forge custody and is not a fix.

**Disposition:** controls `d83dab3` are not executed. A new, independently accepted
preparation epoch must precede attempt 11. Every guard before a one-shot step
must stat-check the stage parent and roots against the accepted preparation
identities, so a future reboot fails closed before anything is consumed.

## Important

**`collect-outcome` cannot record two failure shapes:** a refusal during resource
admission leaves no allocation directory, and an observer timeout means there is
no audit terminal. Both must be recorded as missing evidence (`FAILED_CONSUMED`).

## Minor

- **M1:** collect-outcome should require `configuration_sha256` equality explicitly.
- **M2:** the history "fake" cases fail at hash pins, not the semantic predicates.
  This is acceptable, but it should be stated.
- **M3:** three empty directories are covered by neither a pin nor an absence check.
- **M4:** the entry-ceiling margin is small (next item).

## Measured

The reviewer's read-only model reproduces admission02's measured peak of 33,719
held files exactly.

| Attempt | Held entries | Limit |
| --- | --- | --- |
| 11 (projected) | 38,243 | 40,000 (margin 1,757) |
| 10 | 37,903 | 40,000 |

Also checked:

- All 2,427 freeze pins match their current bytes.
- The config diff is minimal and compact canonical.
- The consumed-history functions pass against the real retained files.
- Envelope limits are unchanged.
