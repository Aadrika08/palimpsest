# Qualification 14: frozen controls review packet (extended clocks on preparation03)

Status: controls are prepared and frozen. They are not reviewed or pushed, and
nothing has been invoked.
- Branch `research/puck-cpu-held-qualification-14` starts from preparation03
  evidence `44e9712`.
- Merge `54c8b15` brings in the reviewed-GO 11b packet (`27780dd`), the runtime11
  outcome (`92de987`) and the preparation02 evidence (`facc2a7`) byte-identically.
- Source is `f05bd69`.

No admission, guard, run-once tool, SITE/staged census, observer, auditor or
runtime ran. These checks never opened `/tmp/palimpsest-puck-cpu-held-02` or
`-03`; stage-guard proofs used tmpfs fixtures. Diffs below are against the 11b
packet (`docs/plans/puck-cpu-held-qualification-11*`). This file is bound by Git
and the guard's control list, not by a freeze pin.

## Counts

| Item | 11b | 14 |
|---|---|---|
| Configuration | 9,048B `4ab0ef1b…` | 9,048B `32f8aeb5…` |
| Freeze | 617,268B `19f930d0…`, 2,463 pins | 698,687B `7cecde69…`, 2,768 pins / 133,828,234B |
| Wrapper | 4,227B, observer 240s | 4,226B `caa13c29…`, observer **440s** (outer term 450s) |
| Run pins / absences | 103 / 21 | 126 / 23, plus preparation03 and preparation02 run files (51 each), 41 empty directories, 39 d83dab3 outputs |
| Missing receipts / process identities | 17 / 15 | 19 / 18 |
| History checks | 33 | 41 |
| Held entries (ceiling 40,000) | 38,290 (34,032 files measured) | **38,681** (34,337 files + 3,273 directories + 1,071 links; margin 1,319) |

The entry model reproduces the measured values exactly: admission10-02 (33,719
files, 37,903 entries) and admission11b (34,032 files). The freeze adds 305 pins
and drops none:
- the runtime11 outcome packet and its 22 `runs/` originals;
- 11b controls, Git-bound at `27780dd`;
- 28 preparation03 files, Git-bound at `44e9712`;
- the 5 replaced live sources, archived via the 11b packet `source/` at
  `8f3a138`;
- the 14 source evidence.

## Diffs against 11b

1. **`-14.json`:** only these fields change:
   - kind `…-v14`, version and allocation_id 14;
   - `limits` = `QUALIFY14_LIMITS` (normal/child-hard/hard 360/375/390);
   - stage `/tmp/palimpsest-puck-cpu-held-03`;
   - sources = preparation03's (bootstrap, qualifier and `puck_dependency_files`
     at f05bd69);
   - `preparation_acceptance` = preparation03's four archived pins (config
     `f9150235…`, result `c7e6c0e8…`, audit `c5c7da42…`, CLI record
     `53b7f6e5…`).

   Inputs (candidate D), the 32-name roster, environment, interpreter and claims
   are unchanged. Before the freeze, it passed offline the parent's
   `validate_configuration` and `validate_preparation_acceptance` and the
   auditor's `configuration`, `preparation_epoch` and `historical_acceptance`
   (`port.py`, canonical-green01).
2. **`-14-admission.py`:**
   - Renamed to held14 telemetry, the `…-14-admission-01` / `…-14-audit-01`
     outputs and the `runs/…-14` new paths, with auditor `6292b550…` and source
     f05bd69.
   - Preparation constants and `check_preparation03` are bound to preparation03
     (audit allocation 13).
   - Asserts the 360/375/390s clocks.
   - New history functions:
     - `check_consumed11`: runtime11 failed on its 180s deadline, with no result
       or baseline-after; the early audit refusal was by `04192a3b`.
     - `check_consumed_admission11b`: admitted and then consumed by the sole
       runtime11.
     - `check_preparation02_consumed`: accepted and consumed; the stage is not
       inspected.
   - Missing receipts 19, empty directories 41, 18 process identities, and
     runtime11/admission11b streams and pins as raw roles.
3. **`-14-freeze.json`:** adds `attempt11b`, `preparation03`, `epoch14_clocks`,
   `evidence_commits`, `previous11b_freeze`,
   `historical11b_replaced_live_sources`, `historical11_missing_receipts` and the
   `…_11_failed_consumed` and admission11b flags. Updated: `preparation02`
   (consumed), `limits` and `preparation_acceptance` (now preparation03's), and
   commands retargeted to -14 with audit output `…-14-audit-01`.
4. **Wrapper and envelope** (review-04 Important 2):
   - Wrapper: freeze path/SHA/size, held14 stems, receipt kind, and
     `budget=440 if phase=='observer' else 145`. The inverse is exact.
   - Envelope: observer cap 440s, outer GNU timeout 450s; admission and audit
     stay 145s/155s. It also gains `stage_guard` for preparation03 and
     `epoch14_clocks`.
5. **Guard template:**
   - Origin `-14`; controls `git diff --name-only 54c8b15 CONTROL`; 2,768 pins;
     126 records.
   - Checks preparation03 and preparation02 run files, the 41 empty directories,
     the d83dab3 absences and Git pins.
   - Loads the Git-bound `stage_guard.py` before anything else acts.
6. **`tools/stage_guard.py`:** requires boot `7f875223…`, the result pin
   `c7e6c0e8…`, stage `-03` and roots at device 55, inodes 43194–43197 (tmpfs,
   0700, operator-owned). It reads metadata only.
7. **run-admission/observer/audit-once, bind and pre-observer guard maker:**
   held14 names and the -14 execution and transport paths. run-observer-once
   now uses `450s` with a 470s Python bound. The maker expects 19 missing
   receipts and 126 records.
8. **`collect-outcome`** (epoch 14):
   - A registration without `deadline_seconds` 360 is refused.
   - PASS additionally needs parent elapsed < 360, transport elapsed < 400 and
     four imports each < 360s; otherwise the result is `FAILED_CONSUMED` with
     `epoch14_clocks` recorded.
   - Also checks preparation03 run files.
   - Kept from 11b: I1 (missing allocation or terminal is FAILED_CONSUMED) and
     M1 (configuration SHA `32f8aeb5…`).
9. **`archive-evidence`:** packet `docs/reports/puck-cpu-held-qualification-14`,
   controls counted from `54c8b15`, preparation03 evidence commit.
10. **History checks:** the 33 11b cases are retargeted (preparation03/epoch 14,
    19 receipts, 41 directories, a 50-pin warm read) plus 8 new ones:
    - genuine, changed and fabricated runtime11;
    - genuine, manifest-first and changed admission11b;
    - preparation02 consumed;
    - preparation02 refused for epoch 14.

    Fabricated and changed cases are refused at the authenticated hash pins,
    which proves immutability, not the semantic predicates.

## Self-check results

| Check | Result |
|---|---|
| canonical-green01 | PASS |
| history | RED 9 errors / 6 failures / 26 passes; GREEN 41/41 |
| selfcheck01 | `PASS_AUTHENTICATED_CONTROL_METADATA_ONLY` in 8.58s, FD 4→4 |
| guard-green01 | PASS |
| tools-green01 | 10/10 |
| entries01 | 38,681 / 40,000 |

selfcheck01 confirmed:
- v5 worker registration with `deadline_seconds` 360, with 180 and 361 refused;
- the epoch-14 limits;
- the observer caps 440/450.

`notes.json` records two authoring corrections made before the retained runs.

## Remaining, with CONTROL/COUNT

1. Independent controls review of this exact branch. Any fix goes in a
   separately named file, and COUNT changes with it.
2. Push. Then `CONTROL=$(git rev-parse HEAD)` and
   `COUNT=$(git diff --name-only 54c8b15df97f881570c6e1d6c50f1f8a4e2a45c8 $CONTROL | wc -l)`,
   which is 77 at this commit.
3. With `PY=…/python3.11` and `I=…-14-control-validation/tools/instantiate.py`:
   - `$PY -I -S -B $I pre-admission-guard $CONTROL $COUNT`, then run the guard.
   - `run-admission-once`, then an independent admission review (GO) written to
     `/tmp/palimpsest-held14-independent-admission-review.json`.
   - `make-observer-guard`, then the pre-observer guard.
   - `run-observer-once` (the sole runtime14; up to ~450s).
   - `bind-audit-command`, then `run-audit-once`.
   - `collect-outcome`, then an independent outcome review, then
     `archive-evidence <review sha256>`.
   - If `/tmp/palimpsest-held14-external.py` is gone, recreate it with
     `$I external` first.
4. A reboot is fatal for preparation03: every guard refuses a changed boot id or
   a changed stage. Preparation02's stage stays as it is.
