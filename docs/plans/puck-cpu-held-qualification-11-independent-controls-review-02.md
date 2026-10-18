# Attempt-11b independent controls review 02: GO

**Range:** `facc2a7..8d7a109` (rebuilt on accepted preparation02).
**Reviewer:** the same separate read-only agent that issued review 01's NO-GO.
It ran no admission main, guards, run-once tools, observer, auditor or qualifier,
and did not walk the stage.

## Confirmed

- **Stage/boot guard (review-01 C1 fix).** It checks the boot id, the
  preparation02 result pin, tmpfs/0700/owner on the stage parent, inputs and four
  roots, and the root dev/inode. It runs before the pre-admission and pre-observer
  guards and before run-admission/observer/audit-once. The runtime mounts the
  stage read-only.
- **Config binds exactly preparation02.** It has preparation02's acceptance,
  sources and stage. The parent and auditor pure validators pass:
  `canonical-preflight` passes all six checks.
- **Auditor split is safe.** The current auditor handles the v12 config,
  `historical_acceptance` and `namespace_command`. The old reader keeps
  `Held`, forest, baseline, plan and outcome; their ASTs and constants are
  identical in both auditors.
- **Admission dry run passed.** A read-only rebuild of admission (without its
  main step, SITE census or forest walk) passes on the real files, including
  the 2,463-pin warm hold.
- **Outcome-collection fixes.** I1 is fixed: a missing allocation directory or a
  missing observer/audit terminal is recorded as `FAILED_CONSUMED`. M1 is fixed:
  configuration SHA equality is required.
- **Old packet.** `d83dab3` is recorded as `NO_GO_NEVER_INVOKED` through 73
  Git-object pins.
- **Entry count measured:** 38,290 of 40,000 (margin 1,710). Open descriptors
  would be about 37,219 against 40,000.

## Minor findings and disposition

1. **Fixed before CONTROL.** The archive destination was
   `docs/reports/puck-cpu-held-qualification-11`, which is one of `d83dab3`'s
   must-be-absent outputs. It is now `docs/reports/puck-cpu-held-qualification-11b`.
   The template is bound only through Git at CONTROL.
2. **Noted, not changed.** The freeze's top-level `preparation_acceptance` and
   `changed_preparation_source_paths` still describe preparation01, inherited
   from attempt 10. No control reads them, and the config plus `freeze.preparation02`
   are authoritative. Rename them in the next builder.
3. **Accepted.** The stage guard binds root identities only, because preparation02
   records only those. Contents are re-verified by the forest walk, the qualifier
   and the audit.
4. **Operational.** The run is valid only on this boot (`7f875223…`) and while
   `/tmp` keeps the stage. Run soon. Margins: 1,710 entries, and an estimated
   135–145s against the 180s runtime deadline.

The forest walk itself (`admission.py:672`) was not exercised, by rule. Supporting
evidence: the boot is unchanged, one stat of the roots matches, and preparation02's
PASS audit walked the same forest with identical reader code.
