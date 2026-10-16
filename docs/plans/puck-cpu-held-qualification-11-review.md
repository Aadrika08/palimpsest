# Qualification 11: frozen controls review packet

Status: **controls prepared, not reviewed, not pushed, nothing invoked.** No
admission, pre-admission/pre-observer guard, SITE/staged census, observer,
auditor or runtime has run for attempt 11. Source is `1126b71` (policy v5,
epoch 11). This file is written after the freeze, so it is bound by Git and the
guard's control list, not by a freeze pin. The pinned plan is
`-11-source-evidence/plan.md`.

## Pin counts

| Item | Attempt 10 (admission02) | Attempt 11 |
|---|---|---|
| Configuration | 8,988B `4cc0cf9a…` | 9,130B `6e28bef8…` (compact canonical) |
| Freeze manifest | 519,552B `5ece0938…` | 588,680B `d9c34de3…` |
| Pins / pinned bytes | 2,150 / 109,838,923 | 2,427 / 121,346,836 |
| Historical run files / absences | 79 / 20 | 102 / 21 |
| Missing receipts in `absent()` | 16 | 17 |
| Process identities sampled | 12 | 15 |
| Absent-name probes | 19 | 32 |

There are 277 new pins: 140 terminal10 packet files (index, report and
artifacts), 27 terminal10 `source/` archives (5 replace changed live sources),
23 `runs/` originals of terminal10 raw and transport files, 35 admission02
post-freeze control paths (checked against Git `796359a`), 25 v2 contract files
(checked against `1126b71`) and 27 attempt-11 configuration, runner and
source-evidence files. All 1,998 original10 pins and all 2,150 admission02 pins
are retained. The exceptions are the five changed live sources (auditor,
observer, bootstrap, qualifier and `puck_runtime_qualification.py`). Their
historical pins are kept through `docs/reports/puck-cpu-held-qualification-10/source/`.

## Controls and exact diffs against attempt 10

1. **`-11.json`** (base: amendment02 `configuration.json`). Changes:
   `kind` v10→v11, `version` and `allocation_id` 10→11, and `negative_imports`
   19→32. The 13 added names are `backports_abc fx2trt_oss hypothesis onnx
   onnx_tf onnxruntime tabulate tensorflow tensorrt torch2trt tree tvm xarray`.
   Three source rows are re-pinned to `1126b71`: bootstrap (54,769B
   `357115832f33`), qualifier (62,184B `204985f5ed9d`) and
   `puck_runtime_qualification.py` (2,516B `32a1618b5d79`). These are
   unchanged: 16 inputs (candidate D `6eba3555…`), 4 preparation anchors, root,
   stage parent, interpreter, environment, versions, 180s/2GiB limits and
   claims. Hidden imports are not a configuration field; the qualifier fixes
   them.
2. **`-11-admission.py`** (base: amendment02 `admission.py`; `assemble.py`
   made 15 counted substitutions, then `history-impl.py` added the history):
   - Paths and identities: `OUTPUT` is `/tmp/…-11-admission-01.json`.
     `CONFIGURATION`/`CONFIG_SHA` and the manifest path point to the 11 files.
     `AUDITOR_CURRENT_SHA` is `62ab513d…`. Telemetry is
     `held11-data-admission-*` with `check_id=11`. The result kind is
     `puck-cpu-held11-data-only-admission-v1` and the source commit is
     `1126b71`. `absent()` names the -11 allocation, streams and audit output.
     The absence check requires 32 names.
   - History functions: added `HISTORICAL10_JSON` and `check_consumed10`
     (normal return1, FAIL result equal to CLI stdout, `backports_abc` first
     refusal, early audit refusal, absent baseline-after). Added
     `ADMISSION02_PINS` and `check_consumed_admission02` (DATA_ONLY_ADMITTED
     receipt, consumed by runtime10). `check_consumed_admission01` now compares
     to the historical compact allocation10 values. It requires runtime10's
     result to exist, where it used to require runtime10 to be absent.
   - Bookkeeping: raw roles, epoch-10 stream reservations, one more missing
     receipt and 3 more process identities. The result labels
     `qualification10_invoked=True`, `qualification11_invoked=False`,
     `admission_check_id=1`, `admission10_01_*` and `admission10_02_*`.
3. **`-11-freeze.json`** (base: amendment02 freeze, built by
   `-11-source-evidence/freeze-builder.py`):
   - Removed 11 keys, including the admission01/02 flags, `previous09_freeze`
     and `historical09_replaced_live_sources`.
   - Added 14 keys: actual11 flags, `qualifications01…10_failed_consumed`,
     `admission10_01_failed_consumed`,
     `admission10_02_admitted_consumed_by_runtime10`, `admission10_packets`,
     `historical10_replaced_live_sources`, `historical10_missing_receipts`,
     `previous10_admission02_freeze`, `missing_import_policy=v5`,
     `hidden_imports` and `hidden_import_scope`.
   - Commands were retargeted to the -11 configuration, runner, transport and
     audit-01 output. `helper_absence_scope` is 17/6/23 with 32 probes.
     `previous10_control_commit` is now `796359a`.
   - The builder asserts the compact canonical configuration bytes (lesson 1).
     It also checks Git bytes for sources (`1126b71`), archives (`e723db0`),
     admission02 controls (`796359a`) and the v2 contract.
4. **`-11-external.py`** (base: amendment02 `external.py`): six substitutions
   (docstring, freeze path, SHA, size 519,552→588,680, `/tmp` stem
   `held10-amendment02-`→`held11-` ×2, receipt kind
   `puck-cpu-held11-external-transport-v1`). The inverse is exact. The
   145s/240s budgets and 16MiB stream limits are unchanged.
5. **`-11-execution.json`** (base: amendment02 envelope): kind, check id 2→1,
   admission/audit outputs, concrete-audit path, freeze and wrapper pins,
   `/tmp/palimpsest-held11-*` phase outputs, scope and source commit. The
   timeout binary was re-hashed unchanged (coreutils 9.11). Outer limits stay
   155/155/250s with 5s grace.
6. **`-11-wrapper-proof.json`**: exact-inverse proof against the amendment02
   wrapper.
7. **`-11-control-validation/pre-admission-guard.py.in`** (base: the
   *corrected* amendment02 template, lesson 2). Changes:
   - Prefix `BASE`, origin branch -11, and pins fixed at 2,427 (no `@PINS@`).
   - Controls are listed with `git diff --name-only 1126b71 CONTROL`, which
     is the original10 method, instead of `ls-tree`.
   - Prefix file names. The history read is
     `json.loads((ROOT/(BASE+'-control-validation/historical-before-admission.json')).read_bytes())`.
   - Records 79→102 and output `/tmp/palimpsest-held11-pre-admission-guard01.json`.
   - Placeholders: `@CONTROL@`, `@COUNT@`.
8. **`historical-before-admission.json`**: +23 runtime10 run files and the
   runtime10 baseline-after absence.
9. **Tools** (`-11-control-validation/tools/`, derived from the retained
   terminal10 tools by `derive-tools.py` with counted replacements):
   - `run-admission-once.py.in`, `run-observer-once.py.in`,
     `run-audit-once.py.in`: execution path and held11 stems; `@CONTROL@`.
   - `bind-audit-command.py`: prefix paths, held11 kind, -11 transport and
     configuration SHA.
   - `make-observer-guard.py`: held11 paths and the admission11-01 receipt.
     It refuses any admission11-02 receipt where the old version required
     admission10-01 to be absent. It expects check id 1,
     `qualification11_invoked`, 17 absences and 102 records.
   - `collect-outcome.py.in` (hand-adapted): records either outcome.
     `AUDIT_PASS_IMPORT_ROUTE_ONLY` is used only when the observer and audit
     both return 0, the transport returns 0, the result is
     `imports_completed` and the audit is v11 PASS. Every other case is
     `FAILED_CONSUMED`. Missing receipts are recorded, not asserted, and the
     `backports_abc` assertion is gone.
   - `archive-evidence.py.in` (hand-adapted): Git-diff control list with a
     fixed count. The expected outcome-review status depends on the outcome.
   - `instantiate.py` is new; attempt 10 instantiated templates by hand.
10. **`-11-control-selfcheck.py`** (base: amendment02 `selfcheck.py`, plus
    the qualifier checks from the original10 self-check):
    - Uses the authenticated `Held` reader on the compact configuration, the
      pretty freeze and the full 2,427-pin warm roster.
    - Checks that qualifications 07–10 and admission10 01/02 are consumed, and
      that every amendment02/original10 pin is retained or archived.
    - Runs the preparation epoch, candidate projection and the planned-forest
      absence check for all 32 names. Checks that the 4 hidden names are
      undeclared.
    - Calls the qualifier's `validate_configuration` and
      `validate_preparation_acceptance` (5 changed preparation paths) and
      builds worker registration v5.
11. **History checks** (`-11-source-evidence/history-check.py`): the 17
    amendment02 cases become 26. New cases cover genuine10 (FAIL result, no
    success receipt), changed10 transport, fabricated10 baseline-after,
    fabricated10 success result, fabricated11 result and fabricated
    admission11 receipt. They also cover genuine, manifest-first and changed
    admission02, with a 40-pin combined warm read across 07–10. The
    admission01 cases use the historical allocation10 values.
12. Assembly and proof helpers follow the attempt-10 pattern: `assemble.py`,
    `history-impl.py`, `history-batch.py`, `canonical-preflight.py`,
    `postfreeze.py`, `guard-path-check.py`, `check-batch.py` and
    `tools-check.py`.

## Self-check results (metadata only)

- Canonical preflight (`canonical-green01`): PASS. The compact bytes match the
  authenticated formatter AST, and the qualifier and auditor validators accept
  v11.
- History: `history-red01` had 7 errors, 4 failures and 15 passes.
  `history-green01` passed all 26 in 0.11s.
- Freeze: 2,427 pins with 5 changed live sources archived. `runs/` pins are
  read-only metadata (102).
- Control self-check (`selfcheck01`): `PASS_AUTHENTICATED_CONTROL_METADATA_ONLY`
  in 3.52s, FD 4→4, no child or thread, no vendor module loaded.
- Guard history read (`guard-green01`): PASS on an isolated fixture.
- Tools: `tools-green01` failed on two errors in the check script itself,
  which is retained. `tools-green02` passed after correcting only
  `tools-check.py`.

## Risks for the independent review

- Held entry ceiling: 40,000 entries. Attempt 11 adds 277 pinned files and 63
  directories. A metadata estimate puts the admission10 peak at about 37.9k
  entries (33,719 files, plus links and directories), so about 38.2k for
  attempt 11. This estimate is unmeasured.
- The deadline margin is tight. The v2 contract extrapolates 135–145s of
  imports against the unchanged 180s limit. That is an estimate, not a proof.
- The admission probes only the 32 absent names. The hidden-roster
  non-registration is checked by the self-check and enforced by the bootstrap.

## What remains

1. Independent exact-controls and roster review of this branch. Retain the
   verdict as a separately named file; any fix goes in a separately named
   control and never edits the freeze.
2. Push `research/puck-cpu-held-qualification-11` and record the final
   `CONTROL` commit and reviewed `COUNT` (the files listed by
   `git diff --name-only 1126b71 CONTROL`).
3. Fresh pre-admission guard, then one admission11, then an independent
   receipt review.
4. Pre-observer guard, then one runtime11, then bind and run one audit.
5. Collect the outcome, review it independently, archive and report.
