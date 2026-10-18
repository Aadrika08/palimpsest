# Allocation 16: frozen controls review packet (held episode on preparation04)

Status: controls are prepared and frozen. They are not reviewed or pushed, and
nothing has been invoked.

- Branch `research/puck-cpu-held-episode-16` starts from accepted preparation04
  (`4b22f2b`).
- Merge `75df4db` brings in, byte-identically, the reviewed-GO attempt-14 packet
  (controls `eb34d5c`) and the accepted runtime14 outcome (`4fd4f68`), together with
  the 11b, runtime11 and preparation02/03 evidence they carry.
- Source is `cbda0d9`, the last change to `scripts/`, `src/`, `upstream`,
  `pyproject.toml`, `uv.lock` and `model_manifests`.

No admission, guard, run-once tool, SITE/staged census, observer, auditor or
episode ran. These checks never opened `/tmp/palimpsest-puck-cpu-held-04`;
stage-guard proofs used tmpfs fixtures. Diffs below are against the attempt-14
packet (`docs/plans/puck-cpu-held-qualification-14*`). This file is bound by Git
and the guard's control list, not by a freeze pin.

## Counts

| Item | Attempt 14 | Allocation 16 |
|---|---|---|
| Configuration | 9,048B `32f8aeb5…` (qualifier canonical) | 20,132B `01a669fc…` (episode parent canonical) |
| Freeze | 698,687B `7cecde69…`, 2,768 pins / 133.8 MB | 542,502B `a40c0d14…`, 2,128 pins / 66.7 MB |
| Wrapper budgets (admission/audit/observer) | 145 / 145 / 440 s | 145 / **330** / **1300** s |
| GNU timeout outer terms | 155 / 155 / 450 s | 155 / **340** / **1310** s |
| Python tool bounds | 170 / 170 / 470 s | 170 / **360** / **1330** s |
| Run pins / absences | 126 / 23 | 151 / 23 |
| Re-hashed run files | preparation03 and 02 (51 each) | preparation04 (114), preparation03/02 (51 each), characterization-04 (40) |
| Empty directories / process identities | 41 / 18 | 46 / 21 |
| History checks | 41 | 40 |
| Held entries (ceiling 40,000) | 38,681 (measured 34,337 files) | **37,982** (33,824 files + 3,061 directories + 1,097 links; margin 2,018) |
| Held bytes (ceiling 2,147,483,648) | 1,566,986,344 (measured) | **2,044,405,373** (margin 103,078,275) |

The entry model reproduces admission14's measured peak exactly: 34,337 held files
and 1,566,986,344 held bytes. Without evidence-index binding, allocation 16
would be:

- 39,422 entries (margin 578, below the 39,500 stop threshold);
- 2,128,290,671 bytes (margin only 19 MB, about 0.9%).

Because the 2 GiB byte ceiling is a hard Held limit, the consumed history is bound
through the evidence indexes, per the user decision. The 40,000-entry ceiling is
kept.

## Diffs against attempt 14

1. **Configuration (`-16.json`, `port.py`).** This is a new shape: the one
   `run_puck_cpu_held_episode.py` and `audit_puck_cpu_held_episode.py` validate.
   - kind `puck-cpu-held-episode-allocation-v16`, version/id 16;
   - sources: preparation04's 97 plus the episode parent;
   - preparation04's inputs (candidate 02, characterization-04 archive,
     native 06);
   - stage `/tmp/palimpsest-puck-cpu-held-04`;
   - the parent's environment, versions and limits (1200/1215/1230 s), with
     600 s per worker;
   - 42 absent and 4 hidden names;
   - claims;
   - the four archived preparation04 acceptance pins;
   - run ids `6bdba8da…`/`3cdc557f…`, distinct from characterization-04's.

   The schedule (seed 7, 48 ticks, actions at ticks 0 and 24), the renderer
   criteria and the EGL vendor pin (`50_mesa.json`, `cd3881df…`, through native
   metadata 06) are frozen in the source and the native metadata. Before the
   freeze, the parent's `validate_configuration`, `validate_acceptance` and
   `require_declared_misses`, and the episode auditor's `validate_configuration`
   and `validate_acceptance`, all accepted the configuration offline
   (canonical-green01).
2. **Admission (`-16-admission.py`).** This is a counted port
   (`admission-port.py`). It keeps every attempt-14 history function except the
   preparation03 binding. Changes:
   - **Preparation02:** now records its stage as retired.
   - **Empty directories:** 41 → 46.
   - **New paths:** allocation-16 paths and outputs.
   - **Absence probes:** 42 names instead of 32.
   - **Telemetry:** `held16`.
   - **New `main()`:**
     - the held auditor `4ef23799` (preparation04's PASS auditor) supplies
       Held, plan and forest;
     - it asserts the 1200/1215/1230 s parent clocks and 600 s workers;
     - it runs both parent and both episode-auditor validators;
     - it re-hashes the preparation04 receipts and capsule, the SITE census,
       the 60 v6 natives, the EGL vendor JSON, the aliases and the baseline;
     - it re-hashes the forest twice;
     - it publishes `held_entries`.
   - **New history (`history-impl.py`):**
     - runtime14 accepted and consumed;
     - admission14 consumed by runtime14;
     - preparation03 accepted, consumed and retired, plus the shared
       retired-stage check against the retirement record `02fc8419…`;
     - characterization-04 accepted;
     - preparation04 bound;
     - 21 process identities (adding runtime14's three).
3. **Freeze (`freeze-builder.py`).**
   - **Index binding:** the consumed `docs/reports` packets of 05, 07–10,
     10-admission-01, 11b and 14 (1,143 archived files) are bound through their
     evidence indexes.
     - The builder verifies each index lists every packet file byte-identically.
     - 942 attempt-14 pins become index-bound.
     - Files the history checks read stay pinned.
   - **Replaced live sources:** ten have changed since `f05bd69`. They are bound
     by the runtime14 packet's `source/` copies.
   - **Added pins:**
     - the runtime14 `runs/` originals (24);
     - the attempt-14 controls (78, Git-bound at `eb34d5c`);
     - characterization-04, preparation04 and candidate-02 controls and evidence
       (84, Git-bound at `4b22f2b`);
     - the allocation-16 configuration, admission and source evidence.
   - **New fields:** `runtime14`, `evidence_index_binding`, `episode`,
     `episode16_clocks`, `characterization04`, `preparation04`, and the
     retirement records under `preparation02`/`03`.
   - **Commands:**
     - observer → `observe_puck_cpu_held_allocation.py` (episode branch);
     - auditor prefix → `audit_puck_cpu_held_episode.py`;
     - output `/tmp/palimpsest-puck-cpu-held-episode-16-audit-01.json`.
4. **Wrapper and envelope.**
   - **Wrapper:** an exact inverse of attempt 14's, except for the freeze pin,
     the `held16` stems and kind, and the budgets
     `budget=1300 if observer else 330 if audit else 145`.
   - **Envelope:** wraps each budget in a GNU timeout 10 s longer (155/340/1310 s).
     Each budget outlasts its child's own alarm:
     - observer 1275 s plus 5 s cleanup;
     - episode auditor 310 s (deadline 300 s);
     - admission 130 s.
   - **Stage guard:** rebound to preparation04.
5. **Guard template:**
   - origin is `-16`;
   - controls come from `git diff --name-only 75df4db CONTROL`;
   - 2,128 pins and 151 records;
   - it checks the preparation04/03/02 and characterization-04 run files, the
     retired stages' absence, the 46 empty directories, the d83dab3 absences and
     Git pins;
   - it loads the Git-bound `stage_guard.py` first.
6. **`tools/stage_guard.py`.** Requires boot `7f875223…`, result `a76b6148…`,
   stage `-04` and roots at device 55, inodes 317249–317252 (tmpfs, 0700,
   operator-owned). It reads metadata only.
7. **Run-once tools, bind and maker.**
   - names change to `held16`;
   - `run-observer-once` uses `1310s` with a 1330 s Python bound;
   - `run-audit-once` uses `340s` with a 360 s bound;
   - `bind-audit-command` requires an `episode` transport from
     `run_puck_cpu_held_episode.py`;
   - the maker checks `episode16_invoked` false and 151 records.
8. **`collect-outcome`.**
   - **PASS (`AUDIT_PASS_HELD_EPISODE_ONLY`) requires all of:**
     - normal observer and audit terminals;
     - an episode transport with return code 0, not timed out, in under 1260 s;
     - `episode_completed`, `held_episode_observed`, `process_creation_attempts`
       0, `ticks_completed` 48;
     - replay `passed` over 48 compared ticks with no divergence;
     - the Mesa llvmpipe EGL renderer;
     - parent elapsed under 1200 s;
     - both supervisions `completed` and both registrations carrying
       `deadline_seconds` 600 (any other clock is refused);
     - an audit of kind `puck-cpu-held-episode-independent-audit-v1` with PASS
       from auditor `4d8ac17f…`;
     - verified result and transport hashes equal to these bytes,
       `compared_ticks` 48 and `frames_checked` 384;
     - both validated bundle SHA-256s equal to the result's bundles.
   - **Otherwise:** `FAILED_CONSUMED`, recording any missing allocation,
     terminal or receipt, as in 11b/14 (I1).
   - **Kept:** M1 (configuration SHA `01a669fc…`).
9. **`archive-evidence`.**
   - packet `docs/reports/puck-cpu-held-episode-16`;
   - controls counted from `75df4db`;
   - 103 Git-bound sources, with fly-gym files Git-bound at the submodule's
     `8d96459`;
   - the review must be `PASS_HELD_EPISODE_OUTCOME_RECORD_ONLY`, or
     `PASS_FAILED_OUTCOME_RECORD_NO_RUNTIME_ACCEPTANCE` for a failed outcome.
10. **History checks.** These cover:
    - the ported 07–11 and admission cases;
    - runtime14 genuine, plus changed transport, result, audit and post-outcome
      receipts;
    - admission14 genuine, manifest-first and changed;
    - preparation02/03 accepted, consumed and retired;
    - a present retired stage or a changed retirement record (refused);
    - characterization-04 genuine and changed audit;
    - preparation04 genuine and pin drift;
    - preparations 01–03 refused for allocation 16;
    - the episode-16 absences;
    - 46 empty directories;
    - 21 identities;
    - the qualifier-load descriptor baseline.

## Self-check results

| Check | Result |
|---|---|
| canonical-green01 | PASS |
| history | RED 18 errors / 24 passes → GREEN 39/39; red02→green02 (manifest-first runtime14 raw roles); red03→green03 (descriptor baseline) 40/40 |
| selfcheck01 | `PASS_AUTHENTICATED_CONTROL_METADATA_ONLY`, FD 5→5 |
| tools-green01 | 12/12 |
| guard-green01 | PASS |
| entries01 | 37,982 / 40,000 entries; 2,044,405,373 / 2,147,483,648 bytes |

selfcheck01 confirmed:
- every attempt-14 pin is retained, replaced or index-bound;
- the parent and independent auditor v4 registrations are equal, with
  `deadline_seconds` 600;
- the observer `EPISODE_SECONDS` is (1260, 1275) with 5 s cleanup;
- envelope budgets are 145/330/1300 s and outer terms 155/340/1310 s.

`notes.json` records the authoring corrections. Two of them were real admission
defects, found by the self-check trial after GREEN and fixed with retained RED→GREEN
pairs:
- runtime14 streams and baselines were held as metadata before their raw reads;
- the qualifier's `tempfile` import left one `/dev/urandom` descriptor open beyond
  the closure baseline.

## Remaining, with CONTROL/COUNT

1. Independent controls review of this exact branch. Any fix goes in a separately
   named file, and COUNT changes with it.
2. Push. Then `CONTROL=$(git rev-parse HEAD)` and
   `COUNT=$(git diff --name-only 75df4dba55e435eee84d8a0f34b33967b0ac86bf $CONTROL | wc -l)`,
   which is 104 at this commit.
3. Set `PY=/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11`
   and `I=docs/plans/puck-cpu-held-episode-16-control-validation/tools/instantiate.py`, with
   cwd at the worktree. Every `$PY -I -S -B $I <name> $CONTROL $COUNT` writes
   `/tmp/palimpsest-held16-<name>.py` and runs nothing. Then, in order:
   1. `pre-admission-guard`, then run `/tmp/palimpsest-held16-pre-admission-guard.py`.
   2. Only if `/tmp/palimpsest-held16-external.py` (sha `e6d57160…`) is gone:
      `external`.
   3. `run-admission-once`, then run it. Write an independent admission review
      (GO) to `/tmp/palimpsest-held16-independent-admission-review.json`.
   4. `make-observer-guard`, then run it. It writes
      `/tmp/palimpsest-held16-pre-observer-guard.py`; run that next.
   5. `run-observer-once`, then run it. This is the sole allocation 16: two
      600 s workers, up to about 1310 s.
   6. `bind-audit-command`, then run it.
   7. `run-audit-once`, then run it.
   8. `collect-outcome`, then run it. Write an independent outcome review to
      `/tmp/palimpsest-held16-independent-outcome-review.json`.
   9. `archive-evidence`, then run it as
      `$PY -I -S -B /tmp/palimpsest-held16-archive-evidence.py <outcome review sha256>`.
4. A reboot is fatal for preparation04: every guard refuses a changed boot id or a
   changed stage. The admission re-hashes the staged forest twice; nothing else
   reads it before the episode.

Scope: one held public manual episode only. No operator, collection, study,
release, CI, cloud or rover execution. All seven release gates stay open.
