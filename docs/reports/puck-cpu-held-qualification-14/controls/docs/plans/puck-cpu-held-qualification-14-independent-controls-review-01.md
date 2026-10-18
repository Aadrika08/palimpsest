# Attempt-14 independent controls review 01: GO

**Range:** `44e9712..4560606`. **Reviewer:** separate read-only agent. It ran
`canonical-preflight` and `history-check` directly, plus a read-only run of the
admission main body up to the forest walk against the real state. It ran no
admission main, guards, run-once tools, observer, auditor or qualifier, and
walked neither stage.

## Confirmed

1. **Config.** It binds exactly preparation03, `QUALIFY14_LIMITS` 360/375/390s
   and sources f05bd69. Its bytes are compact canonical (9,048 B, `32f8aeb5…`),
   and all five parent/auditor validators pass.
2. **Merge.** `54c8b15` is a documentation-only merge: its tree is identical to
   `git merge-tree` of `44e9712` and `92de987`. The control list counts the
   changes since `54c8b15`, and every listed file is under the `-14` prefix.
3. **Stage/boot guard.** It is bound to preparation03 (roots dev 55, inodes
   43194–43197; result `c7e6c0e8…`; boot `7f875223…`) and runs before every
   one-shot step.
4. **Clocks are ordered:**
   - worker 360s
   - parent child-hard 375s, hard 390s
   - observer 400s, hard 415s
   - wrapper 440s, GNU timeout 450s, run-observer-once 470s

   No layer of the qualify run is left at an old value.
5. **Epoch-aware bounds.** Admission, self-check and collect-outcome all use
   them. The 11b fixes for a missing allocation or terminal (I1) and for
   configuration SHA (M1) are kept.
6. **History.** It passes against the real state:
   - runtime11 `FAILED_CONSUMED`
   - admission11b and preparation02 consumed by runtime11
   - preparation03 accepted
   - d83dab3 never invoked
   - preparation01 superseded
7. **Entries.** Re-measured at 38,681 of 40,000 (margin 1,319).
8. **Freeze.** All 2,768 pins match.

## Minor findings (none blocking)

1. **Stale field.** `-14-freeze.json` `changed_preparation_source_paths` is
   relative to preparation01. Nothing reads it.
2. **Memory.** About 4.1 GB of swap is in use, and part of the two retained
   stages may be swapped out. Budgets have room: admission 120s against about
   14s, runtime 360s against an estimated ~200s. Keep other load off the host
   during the run. Preparation02's stage is kept: 6.8 GB of RAM is available.
3. **Guard binding.** The stage guard compares only the four root inodes; the
   parent and `inputs` inodes are recorded but not compared. This is inherited
   from 11b.
4. **Entry margin.** It is now 3.3%. A future epoch will need pin pruning or a
   ceiling change.
