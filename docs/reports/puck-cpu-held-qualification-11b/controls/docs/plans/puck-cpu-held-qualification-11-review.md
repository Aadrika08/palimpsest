# Qualification 11 (packet 11b): frozen controls review packet

Status: controls are prepared and frozen. They are not reviewed or pushed, and
nothing has been invoked.
- Branch `research/puck-cpu-held-qualification-11b` starts from the accepted
  preparation02 evidence `facc2a7`.
- Source is `8f3a138`.
- Packet `d83dab3`, on `research/puck-cpu-held-qualification-11`, was reviewed
  NO-GO (review 01, `0b9c67f`) and never invoked. That branch is unchanged.

This packet reuses d83dab3's paths, so the diffs below are against d83dab3. No
admission, guard, run-once tool, SITE/staged census, observer, auditor or runtime
ran. None of these checks touched `/tmp/palimpsest-puck-cpu-held-02`:
stage-guard proofs used tmpfs fixtures. This file is written after the freeze, so
it is bound by Git and the guard's control list, not by a freeze pin.

## Counts

| Item | d83dab3 | 11b |
|---|---|---|
| Configuration | 9,130B `6e28bef8…` | 9,048B `4ab0ef1b…` |
| Freeze | 588,680B `d9c34de3…`, 2,427 pins | 617,268B `19f930d0…`, 2,463 pins / 121,576,773B |
| Wrapper | 4,194B `b536be80…` | 4,227B `d5ec3a6a…` |
| Run pins / historical absences | 102 / 21 | 103 / 21, plus 51 preparation02 run files, 35 empty directories and 39 absent d83dab3 outputs |
| History checks | 26 | 33 |
| Held entries (ceiling 40,000) | 38,243 (review-01 projection) | **38,290** (34,032 files + 3,187 directories + 1,071 links; margin 1,710) |

The entry model reproduces the measured values exactly: admission10-02's 33,719
held files and review 01's 37,903 entries. Its counts come from pins, the plan
and metadata. Relative to d83dab3, the freeze adds:
- 26 preparation02 controls and evidence files;
- the review-01 port;
- 11b source evidence.

It drops d83dab3's `assemble.py`, and 25 same-path pins now have 11b or 8f3a138
bytes. d83dab3's 73 files are recorded as Git-object pins, checked by the
self-check and the guard.

## Diffs against d83dab3

1. **`-11.json`:** only three fields change:
   - `stage_parent` → `/tmp/palimpsest-puck-cpu-held-02`.
   - The qualifier source pin → 8f3a138; all 24 sources now equal preparation02's.
   - `preparation_acceptance` → the four archived preparation02 pins
     (config `1acfb10b…`, result `4ef13965…`, audit `fe155208…`, CLI record
     `50e452aa…`).

   Bytes are compact canonical. Before the freeze, it passed offline the parent's
   `validate_configuration` and `validate_preparation_acceptance` and the
   auditor's `configuration`, `preparation_epoch` and `historical_acceptance`
   (port.py and canonical-green01).
2. **`-11-admission.py`:**
   - Renamed to held11b telemetry and outputs: `…-11b-admission-01`,
     `…-11b-audit-01`.
   - `CONFIG_SHA`, auditor `04192a3b…`, `PREP_SHA`/`RESULT_SHA` of
     preparation02, and source `8f3a138`.
   - `prepbase` is now `runs/puck-cpu-held-preparation-02`.
   - New `check_preparation02` reads preparation02's v12 configuration through
     the current auditor, then checks its outcome, staged roots, configuration
     copy, sources and `historical_acceptance`.
   - The invocation uses the current `namespace_command`; the self-check
     confirms the legacy one would differ.
   - The legacy reader keeps Held, plan, forest and baseline, which are
     identical in both auditors.
   - Added `record_preparation01` (superseded, stage lost, not required),
     `check_unexecuted11` and `check_empty_directories` (M3), with their result
     fields.
3. **`-11-freeze.json`:**
   - New `kind` and branch, source `8f3a138`, and `evidence_commit`.
   - Added `preparation02` (acceptance, stage, roots, boot `7f875223…`, guard
     text), `preparation01_superseded` and `attempt11_d83dab3`.
   - The audit output is now `…-11b-audit-01`.
4. **Wrapper, envelope and proof:**
   - The wrapper changes only freeze SHA/size, the held11b stems and the receipt
     kind; the inverse is exact.
   - The envelope gains held11b paths, `evidence_commit` and `stage_guard`.
     Limits and timeout are unchanged.
5. **Guard template** (corrected form):
   - Origin is `-11b`; controls are `git diff --name-only facc2a7 CONTROL`;
     2,463 pins; 103 records.
   - **C1:** loads the Git-bound `tools/stage_guard.py` before anything else
     acts.
   - Checks preparation02 run files, the 35 empty directories (M3), the 39
     absent d83dab3 outputs and d83dab3's 73 Git-object pins.
6. **`tools/stage_guard.py`** (new, C1):
   - Requires boot `7f875223-b4cf-421e-b04d-81e3c1f19460`.
   - Requires the result pin `4ef13965…`.
   - Requires the stage parent, `inputs` and `root-0000..0003` to be tmpfs,
     0700, operator-owned directories, with roots (55, 10400–10403).
   - It opens metadata only (`O_DIRECTORY|O_NOFOLLOW`): no listing, no writes.
7. **Run-once tools and pre-observer guard maker:**
   - run-admission/observer/audit-once load the stage guard before writing
     anything and record it.
   - The pre-observer guard inherits it from the pre-admission guard.
   - Other changes are held11b names; the maker refuses any `…-11b-admission-02`
     and expects 103 records.
8. **`collect-outcome`:**
   - **I1:** a missing allocation directory or missing observer/audit terminal
     is recorded as `FAILED_CONSUMED`.
   - **M1:** the admission, transport, result and audit must all carry
     configuration SHA `4ab0ef1b…`.
   - Also checks preparation02 run files, empty directories and d83dab3
     absences, and records the stage after the run.
9. **`archive-evidence`:** accepts 0 or 1 audits, but only for
   `FAILED_CONSUMED`; requires the configuration SHA; records missing tools;
   counts controls from `facc2a7`.
10. **History checks:** the 26 d83dab3 cases plus seven new ones:
    - genuine preparation02 binding;
    - preparation02 pin drift;
    - preparation01 recorded but refused for epoch 11;
    - d83dab3 never invoked, and a fabricated d83dab3 receipt;
    - empty directories, and an inserted file.

    **M2:** the fabricated and changed cases are refused at the authenticated
    hash pins, which proves immutability, not the semantic predicates.

## Self-check results

| Check | Result |
|---|---|
| canonical-green01 | PASS |
| history | RED 7 errors / 26 passes; GREEN 33/33. One authoring failure is retained; it happened before any runner edit. |
| selfcheck01 | `PASS_AUTHENTICATED_CONTROL_METADATA_ONLY` in 7.28s, FD 4→4 |
| guard-green01 | PASS |
| tools-green01 | 7/7 |
| entries01 | 38,290 / 40,000 |

## Remaining, with CONTROL/COUNT

1. Independent controls review of this exact branch (review 02 for attempt 11).
   Any fix goes in a separately named file, and COUNT changes with it.
2. Push. Then `CONTROL=$(git rev-parse HEAD)` and
   `COUNT=$(git diff --name-only facc2a7 $CONTROL | wc -l)`, which is 85 at
   this commit.
3. With `PY=…/python3.11` and `I=…-11-control-validation/tools/instantiate.py`:
   - `$PY -I -S -B $I pre-admission-guard $CONTROL $COUNT`, then run
     `/tmp/palimpsest-held11b-pre-admission-guard.py`.
   - `run-admission-once` (one admission), then an independent admission review
     written to `/tmp/palimpsest-held11b-independent-admission-review.json` with
     decision GO.
   - `make-observer-guard`, then the pre-observer guard.
   - `run-observer-once` (the sole runtime11).
   - `bind-audit-command`, then `run-audit-once`.
   - `collect-outcome`, then an independent outcome review, then
     `archive-evidence <review sha256>`.
   - If `/tmp/palimpsest-held11b-external.py` is gone, recreate it with
     `$I external` first.
4. A reboot at any point is fatal for this preparation and needs a new
   preparation epoch: every guard refuses a changed boot id or a changed stage.
