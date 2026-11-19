# MaleCNS v4 S1: six-model matched-budget training, execution manifest (prospective)

> **Status:** prepared, **not executed**. S1 is a **scientific attempt** (`scientific_attempt:
> true`), one attempt, one `run_research_stage.py` unit. It needs an explicit owner GO naming this
> manifest's sha256, the plan sha256 and the corpus-pin, audit and derivation shas below. Nothing
> here ran the trainer, the data child or Torch. Earlier review amendments are carried in the
> body: by-hand GO binding (incl. `current_tree_head` and `declared_fields_sha256`), no placeholders,
> write-order directories, writer lock, throttling and an extended post-run gate.

Protocol: `docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json`, sha256
`cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477`. It is not edited. Cohorts,
updates, thresholds and the matched clock are fixed there: **6 models** (seeds 10/11/12 ×
old-corpus/augmented, in that order), **1,440 Adam updates of exactly 32 real rows (46,080
presentations) each** (8,640 updates, 276,480 presentations in all), lr .001, gradient cap 1,
CPU float32, one thread, ORIGINAL graph `5aba0fef…`, cell `707cba79…`, terminal update-1,440 state
only.

## Inputs (all pinned)

| Item | Value |
| --- | --- |
| Corpus pin (S0z) | `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0z/corpus-pin.json`, sha256 `f6115c1e03d5aec37ac2463cc833bbd8fbea06403a8ae1c98e6a3f049b6b29b7` (equal to the committed `docs/reports/male-v4-s0z/corpus-pin.json`) |
| S0z audit | sha256 `2bef156950ddea57191dd0e5ade16326d90f08f1f53c820f46b70f33b7230119` (`passed`, S0e-A not_covered empty, no waiver) |
| Schedule derivation | sha256 `81cd9a496ec25762b106276fbfb87754593c668d6159adf5c15b30df38ff83cb` (old N 2,117 q 21 r 1,623; augmented N 7,197 q 6 r 2,898) |
| Data manifest (S0f) | sha256 `4a1be0920f01a3d36df4f9a48b7906fefbd4efd128e1ffaa1ff2759a010e2fa3` |
| Reader trees | T-f `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-f` at `88c1a0f6f53274fe663f4cdad3be5ae2743af558`; T-h `…/port-t-h` at `0789b2ed54117c01c40ab5818148cc0515eb4fb5` |
| Receipts | stage P `docs/reports/male-v4-stage-p/launcher-receipt.json` `e6c42703…260b`; stage P2 `docs/reports/male-v4-stage-p2/launcher-receipt.json` `67a2e508…0dd0b5` (6/6 entries, incl. S1, S2, the S0z controller/audit and the S1 data child with its T-f closure) |

## What S1 runs

`scripts/train_male_navigation_v4.py` from `CUR`, inside one unit. Plan-only (the default) opens no
array and imports no Torch; with `--go` it:

1. checks the GO (lane, stage S1, protocol, corpus-pin sha, derivation sha, `granted_by`/`granted_at`),
   the research-stage work leaf, a fresh output and the free-space floor;
2. `hooks.runtime` (Python 3.11.15, NumPy 2.2.5, Torch distribution 2.9.0) and **`CUDA_VISIBLE_DEVICES`
   explicitly empty**; the launcher passes the caller's environment, so the command below sets it with
   `env` (otherwise the trainer refuses inside the charged unit);
3. admits the pinned graph, extraction manifest and cell (`5aba0fef…`, `7a205342…`, `707cba79…`);
4. **before Torch**, runs the data child (`derive_male_navigation_v4_s1_data.py`, `python -I -B`, only the
   T-f port on `sys.path`, S0f's locator) which verifies T-f's reader identity, adapter and feature
   digest against the S0f manifest, derives the arrays exactly as v3 did and requires every source and
   both arms to hash to the manifest `feature_target_sha256`; the parent re-validates the transient
   `transient-arrays.npz` (float32, `(rows,388)`/`(rows,2)`, finite, exact keys). S1 also refuses a dirty or
   untracked `src`/`scripts` tree in T-f/T-h and a T-f/T-h HEAD other than the pin's;
5. imports Torch (one intra-op thread, deterministic algorithms) and trains the six models in order, one
   `zero_grad`/backward/clip/step per 32-row unit, writes each terminal checkpoint, evaluates the recorded
   development set **once afterward** (it cannot alter selection), then publishes `report.json` and the
   receipt `publication.json` last. The first fault is retained in `failure.json`, later models stay
   `not_started`; there is no retry.

Caps in the trainer: output 256 MiB (`OUTPUT_BYTES`), RSS 2 GiB, free-space floor 1 GiB (plus the 256 MiB
cap at preflight), 8 MiB per file. This trainer keeps **no CPU accounting** and **no internal wall
deadline** for training: the unit's `RuntimeMaxSec` and the child's 180 s (`DATA_SECONDS`, kill 210 s)
are its only clocks.

## Plan-only result (nothing executed)

```sh
PYTHONPATH=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/src:/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts \
  OMP_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B \
  /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/train_male_navigation_v4.py --plan-only \
  --corpus-pin /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0z/corpus-pin.json
```

Exit 0; the saved output is [`plan-only.json`](plan-only.json), sha256
**`8d86c177af8022e9f3d38adc5a74ec947fa4037bfd60f3f891c98cadc0134267`** (it holds no path, so it is
identical from `CUR`). It lists the six fixed trainings and the schedule derivation (sha `81cd9a49…`). A
test regenerates the derivation from the committed S0f manifest and compares it.

## Budget, deadlines and an honest CPU estimate

Amendment 1 row S1: expected 480 s; `RuntimeMaxSec` 2,160 (the v3 training enclosing bound);
`TimeoutStopSec` 5; k = 1; worst case k × (2,160 + 5) = **2,165 CPU-s** (the launcher's rule).

**Estimate, from measurements.** The v2 navigation training
(`docs/reports/m7-navigation-training-v2.md`) ran six fits of the same unchanged fitter, cell and
one-thread CPU float32 loop: pair wall 145.2, 140.0 and 138.5 s, a launcher pre-publication wall of
429.6 s for **~559k row presentations, 18,480 updates and ~147k forward-only dev rows** (about 0.023 s per
update, ~1,300 presentations/s including per-epoch dev evaluation). S1's 276,480 presentations and 8,640
updates are 49.5% of v2's presentations and 46.8% of its updates, plus only 7,368 terminal dev rows.
That predicts **about 200 s** of training wall. Adding the data child (S0f, which did the same reads and
feature work, charged 36.5 CPU-s), Torch import and six model builds, checkpoint writes and the per-model
dev pass, I estimate **S1 ≈ 250–330 CPU-s (wall about the same, single thread)**, against the protocol's
**480** expectation and the **2,160 s** kill. Single-threaded CPU time equals wall time, so
`CPUQuota=100%` does not stretch it; the risk of exceeding the 2,160 s kill is **low** (headroom ≈ 6–8x
against the estimate, ≈ 4.5x even against the protocol's 480). It is not zero: v2 ran on a different host
state, the model construction cost of `male_model.make_model` per model is unmeasured, and there is no
internal training deadline to fail early. **Options if the estimate proves wrong are limited by the
protocol:** cohorts, updates, thresholds and the budget cannot change. A kill is an operational failure
that ends v4; the only protocol-compatible mitigation is a new protocol version with a new
`RuntimeMaxSec` row, which the slack below would allow (a kill target up to ≈ 9,000 s would still fit before S2).

**Lane math (ledger `~/.local/state/palimpsest/research-ledger.jsonl`).** The navigation lane stands at
**635.154** CPU-s (635.153 as rounded in the P2 RESULT; v3 prior 1.832 + P 85.274 + S0a 97.378 + S0b 9.472 + S0c 6.378 + S0d 130.525 +
S0e 237.117 + S0f 36.535 + S0z 0.726 + P2 29.918), a **measured v4 charge of 633.322** excluding the
prior. Worst cases still ahead: S1 2,165 and S2 4,435 = 6,600. So 633.322 + 6,600 = **7,233.322 ≤
14,398.168** (remaining at start): S1 and S2 are admissible even at their limits. **Held-out (S3):**
admitted only if the measured v4 charge through S2 is **≤ 5,643.168** (S3's worst case 8,755 against
14,398.168). At expected costs (S1 ≈ 300, S2 988.524) the charge through S2 would be about **1,920**,
far under; if both S1 and S2 hit their worst cases it would be 7,233 and S3 would be inadmissible, which
is why the threshold is decided by measured charges.

**Throttling / threads.** `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`,
`NUMEXPR_NUM_THREADS=1` and `CUDA_VISIBLE_DEVICES=` in the command; the trainer sets Torch intra-op threads
to 1 and requires it. EGL and MuJoCo are not used (the trainer refuses if `mujoco` is imported).

## GO record

Write it at `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s1/go-S1.json`. The
trainer's `check_go` verifies lane, stage, protocol, corpus-pin sha and derivation sha, not the rest:

```json
{"decision": "GO", "lane": "navigation", "stage": "S1",
 "protocol_sha256": "cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477",
 "corpus_pin_sha256": "f6115c1e03d5aec37ac2463cc833bbd8fbea06403a8ae1c98e6a3f049b6b29b7",
 "schedule_derivation_sha256": "81cd9a496ec25762b106276fbfb87754593c668d6159adf5c15b30df38ff83cb",
 "s0z_audit_sha256": "2bef156950ddea57191dd0e5ade16326d90f08f1f53c820f46b70f33b7230119",
 "data_manifest_sha256": "4a1be0920f01a3d36df4f9a48b7906fefbd4efd128e1ffaa1ff2759a010e2fa3",
 "manifest_sha256": "<sha256 of this file>",
 "plan_sha256": "8d86c177af8022e9f3d38adc5a74ec947fa4037bfd60f3f891c98cadc0134267",
 "p_receipt_sha256": "e6c427033e173c9c91d522e37319efdd637a7ffea4f9d7b419f17d3a3b2b260f",
 "p2_receipt_sha256": "67a2e508eeb7ffa3f13a6155339132a563b5ec799500ec1bc19634ad47dda0b5",
 "t_f_head": "88c1a0f6f53274fe663f4cdad3be5ae2743af558",
 "t_h_head": "0789b2ed54117c01c40ab5818148cc0515eb4fb5",
 "declared_fields_sha256": "<sha256 of declared-fields.json in CUR>",
 "current_tree_head": "<authority-paper-rewrite HEAD at launch>",
 "cpu_quota_k": 1,
 "scientific_attempt": true,
 "granted_by": "<owner>", "granted_at": "<date>"}
```

## Pre-launch checks (all must hold; any failure means no launch, and nothing is charged)

1. **Current tree:** `CUR=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite` is at
   the research head carrying this manifest, with clean tracked files; protocol `cd4eb130…`.
   **Stage P2 probed S1 at that tree: if any of `train_male_navigation_v4.py`,
   `derive_male_navigation_v4_s1_data.py`, `male_matched_budget_v4.py`, `male_matched_budget.py`,
   `male_model.py` or `train_male_reduced.py` changed since the P2 GO, S1 needs a new P-type probe.**
2. **Plan:** the plan-only command above, run from `CUR`, prints output with sha256 `8d86c177…`.
3. **Inputs:** the corpus pin hashes to `f6115c1e…`, the S0z `audit.json` to `2bef1569…`, the S0f data
   manifest to `4a1be092…`; `port-t-f`/`port-t-h` are detached at the pinned heads with clean tracked
   files and no untracked `src`/`scripts` (S1 re-checks); the trainer defaults `data/assets/flynn/male-reduced-v1/source-graph.json`,
   `data/manifests/malecns-reduced-neighborhood-v1.json` and `upstream/fly-gym/models/connectome_rnn_model.py`
   in `CUR` hash to `5aba0fef…`, `7a205342…`, `707cba79…`.
4. **GO binding (by hand; `check_go` checks only six fields):** `manifest_sha256` is the sha256 of this
   committed file; `plan_sha256`, `s0z_audit_sha256`, `data_manifest_sha256`, both receipt shas, both heads
   and `declared_fields_sha256` match checks 1–3 and the committed evidence; `cpu_quota_k` is 1 (= `--cpu-quota-k 1`);
   `current_tree_head` is CUR's HEAD; no `<…>` placeholder remains.
5. **Writer lock free:** no palimpsest lab, producer or research stage is running in any lane.
6. **Directories, by write order.** S1 writes no driver locator, so only the parent must exist:
   `mkdir -p …/male-v4-data/S1` then confirm it is **empty**; the output `…/male-v4-data/S1/train` must **not
   exist** (the trainer's `preflight_output` refuses a consumed output; one attempt). Create
   `…/male-v4-s1/` (GO record); `…/male-v4-s1/receipt` must not exist. The output is outside the repository.
7. **Disk:** free space on `/home` ≥ 1 GiB floor + 256 MiB output cap (the trainer checks; 53 GB free on 19
   November 2026) and the output writes ≤ 256 MiB (checkpoints ≈ 0.3 MB each, transient arrays ≈ 13 MB).
8. **Ledger:** no `navigation/S1` row; no other navigation-lane unit running.
9. **Not applicable:** no EGL, no MuJoCo, no data beyond the pinned corpus.

## Launch (charged; one attempt)

<!-- s1-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage S1 --cpu-quota-k 1 --runtime-max-sec 2160 --worst-case-cpu 2165 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s1/go-S1.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s1/receipt \
  -- \
  /usr/bin/env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  PYTHONPATH=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/src:/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/train_male_navigation_v4.py \
  --go /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s1/go-S1.json \
  --corpus-pin /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0z/corpus-pin.json \
  --output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S1/train
```

## Expected outputs

`male-v4-data/S1/train/`: `reservation.json`, `protocol.json`, `schedule-derivation.json` (bytes equal to the
S0z `derivation.json`), `transient-arrays.npz` (unpinned, hash-gated, retained), six checkpoints
`seed-{10,11,12}-{old-corpus,augmented}.pt`, `report.json` and the receipt `publication.json`; no
`failure.json`, no `report.pending`. S1 writes **no separate pin record**: the pin S2 consumes is
`report.json` + `publication.json` (their sha256 and each checkpoint's sha256), recorded in the S1 RESULT
and bound by S2's GO.

## Post-run gate (before any S2 preparation)

- **Unit:** receipt `complete`, `drained`, returncode 0, no survivors; ledger `charged` S1 row; the trainer's
  summary `status: completed-navigation-v4-training`; charged CPU compared with the 250–330 estimate.
- **Terminal-only publication:** `trainer.success_admitted(output)` returns the report (report + matching
  `publication.json`, no `failure.json`, every checkpoint unchanged). `publication.json` has
  `report_sha256` equal to the file; during training no `report.json`/`publication.json` existed.
- **Six models, in order** `(10,old)(10,aug)(11,old)(11,aug)(12,old)(12,aug)`: each `completed`,
  `optimizer_updates` 1,440, `real_row_presentations` 46,080, `selected_optimizer_update` 1,440,
  `schedule_sha256` equal to the derivation's (`derive_schedules(record)['schedules'][seed, arm]`), recorded
  development `ticks` 1,228 and finite metrics; only terminal checkpoints exist (six `.pt`, no epoch files).
- **Nothing selected on dev loss:** `selection: terminal-only-before-recorded-development`,
  `held_out_status: locked_unopened`, `held_out_used_for_selection: false`, `qualification_claims: []`;
  the dev loss is reported but not used by anything in S1.
- **Hashes:** each checkpoint is a weights-only CPU file with keys `format, protocol_sha256, graph_sha256,
  ordered_ids_sha256, state_dict`, `protocol_sha256` equal to `report.run_protocol_sha256`, sizes and
  sha256 equal to the report's file list; `protocol.json` pins `corpus_pin_sha256` `f6115c1e…`,
  `schedule_derivation_sha256` `81cd9a49…`, `model_inputs` the three trainer defaults and `source_code`
  equal to the trainer's `SOURCES` hashes (including the data child).
- **Data child:** `transient-arrays.npz` has exactly the 26 sources' `features`/`targets` keys.
- Record the report, publication and six checkpoint sha256s in the S1 RESULT and the S2 GO. S2 also needs the
  v4 Engine binding (see `docs/reports/male-v4-s2/NOTES.md`).

## On failure

Per protocol `execution_stops`, any guard or pin mismatch, wrong count, nonfinite value, source drift,
byte drift in the data child, RSS/storage breach or RuntimeMaxSec kill **ends v4**: S2 and S3 stay
`not_started`. There is no retry, replacement seed, extra update, or threshold or budget change. The first fault
is retained in `failure.json`, the charge stands (census, or 2,165 CPU-s without a complete receipt) and
further work needs a new protocol version.
