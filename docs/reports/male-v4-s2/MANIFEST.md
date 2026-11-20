# MaleCNS v4 stage S2: development evaluation, execution manifest (prospective)

> **Status:** prepared, **not executed**. S2 is a charged research stage (navigation lane, stage name `S2`,
> worst case **4,435 CPU-s**) and `scientific_attempt: true`. It needs an explicit owner GO naming this
> manifest's sha256. **One attempt:** the launcher refuses a repeated `(lane, stage)`; an infrastructure
> failure or kill is charged and, per Amendment 2, is "an operational failure, never a non-goal"; a re-run would
> need a protocol amendment and a new stage name. This is the first stage that can produce a MaleCNS capability
> result. It reads only **development** scenes 3160 to 3163; held-out scenes 3170 to 3177 are unreachable from
> this route (S3 is a separate stage with a separate GO).

Protocol `docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json` sha256
`cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477`. Amendment 2 file sha256
`c4cd3a506b0b468b0d6d4d359dff7ecbd3b3bf0c25c6fe9360207282249f8d6f`. Evaluator
`scripts/evaluate_male_navigation_v4.py`; binding `src/palimpsest/male_navigation_research_v4.py`.

## What S2 does

24 owners (3 training seeds 10/11/12 x 2 arms, old-corpus and augmented, x 4 development scenes 3160 to 3163),
each a fresh spawned process that loads the exact S1 terminal checkpoint for its `(seed, arm)` through
`NavigationBindingV4` and runs one Engine episode (600 intervals max, native-goal outcome) with the teacher
disabled. Per owner: 180 s cap, 1 MiB log caps, recording at most 144 MiB, aggregate storage budget 4 GiB. The
stage deadline is 1,800 s. No retry or replacement: the first owner failure stops the stage and later owners stay
`not_started`.

**Gate (unchanged, not relaxed):** each *augmented* seed must reach at least **3 of 4** development scenes by
native goal; the old-corpus arm is reported, not gated. Passing admits S3 (held-out, needing at least 6 of 8 per
augmented seed), which needs its own manifest, review and GO and spend through S2 of at most 5,643.168 CPU-s.
Not passing is reported as the actual result: S3 is then not run, and no qualification claim is made.

## Inputs (all pinned; nothing else is read)

| Input | Pin |
| --- | --- |
| S1 report | `docs/reports/male-v4-s1/report.json`, sha256 `6ca8af5f9969fd1227d6e9494e9efc334e425c03145998da7a3de3a9d06c3cd2` (hard-coded in the binding) |
| S1 publication | sha256 `fb6f1f38b492979a29e7bb70c091626bb2037354ea26f7e52140751b36c30f90` (hard-coded) |
| S1 checkpoints | six files, shas in `docs/reports/male-v4-s1/checkpoints.sha256`, read from the S1 output tree below |
| Corpus pin (S0z) | `male-v4-data/S0z/corpus-pin.json`, sha256 `f6115c1e03d5aec37ac2463cc833bbd8fbea06403a8ae1c98e6a3f049b6b29b7` |
| Runtime assets | `/home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn`, verified before and after by `verify_assets` |
| Source | exact producer root = `CUR` HEAD; per-owner source pins incl. the amendment sha; rechecked last before publication |

## Roots

| Symbol | Path |
| --- | --- |
| `CUR` | `/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite` |
| `E` | `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence` |
| S1 output | `E/male-v4-data/S1/train` (read-only; the binding refuses any other tree) |
| `E4` | `E/male-v4-s2` (GO record, launcher receipt; holds nothing else before launch) |
| output | `E4/eval` (fresh; must not exist; outside S1 output, assets and `CUR`) |
| ledger | `/home/utkarsh/.local/state/palimpsest/research-ledger.jsonl` |

## Budget and storage (measured admission)

- Worst case **4,435 CPU-s** = k x (RuntimeMaxSec 4,430 + TimeoutStopSec 5) at k = 1, the amendment's S2 row.
  Navigation lane charged before S2: 837.785 CPU-s (P3 included) of 14,400; 837.785 + 4,435 = 5,272.785, under the
  5,643.168 ceiling for S3, so a development pass leaves S3 admissible on budget.
- **Expected** use is far below the worst case: 24 owners each simulating at most 600 intervals on one thread, but
  nothing has measured a v4 owner (v2's owners are the only reference). The 1,800 s runner deadline allows 75 s
  mean per owner; if owners are slower the stage fails operationally and is charged what it used.
- **Storage:** the evaluator requires `combined_incremental_free_reservation_bytes + free_floor_bytes` =
  18,857,590,784 B free on the output volume and an aggregate of 4,271,898,624 B + 10,485,760 B failure margin.
  Measured now: **28,774,936,576 B free** under `E`, which admits the stage. The operator re-measures at launch.

## Steps

1. **Pin.** Record `CUR` HEAD, this file's sha256 and the S1 report sha in the GO. `CUR` must be clean.
2. **Ledger.** No `navigation/S2` row exists.
3. **GO record** at `E4/go-S2.json` (fields checked by `check_go`: decision, lane, stage, base protocol sha, amendment 2
   sha, S1 report sha, granted by and at; the rest is for the audit trail):

   ```json
   {"decision": "GO", "lane": "navigation", "stage": "S2",
    "protocol_sha256": "cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477",
    "amendment_2_sha256": "c4cd3a506b0b468b0d6d4d359dff7ecbd3b3bf0c25c6fe9360207282249f8d6f",
    "s1_report_sha256": "6ca8af5f9969fd1227d6e9494e9efc334e425c03145998da7a3de3a9d06c3cd2",
    "corpus_pin_sha256": "f6115c1e03d5aec37ac2463cc833bbd8fbea06403a8ae1c98e6a3f049b6b29b7",
    "manifest_sha256": "<sha256 of this file>",
    "p3_receipt_sha256": "<sha256 of docs/reports/male-v4-stage-p3/launcher-receipt.json>",
    "current_tree_head": "<CUR HEAD at launch>",
    "cpu_quota_k": 1, "scientific_attempt": true, "held_out_authorised": false,
    "granted_by": "<owner>", "granted_at": "<date>"}
   ```

4. **Stage S2** (charged, one attempt). `E4/receipt` and `E4/eval` must not exist:

<!-- s2-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage S2 --cpu-quota-k 1 --runtime-max-sec 4430 --worst-case-cpu 4435 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s2/go-S2.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s2/receipt \
  -- \
  /usr/bin/env CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl \
  PYTHONPATH=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/src:/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/evaluate_male_navigation_v4.py \
  --go /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s2/go-S2.json \
  --repo /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --s1-output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S1/train \
  --assets /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn \
  --corpus-pin /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0z/corpus-pin.json \
  --output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s2/eval
```

## Pre-launch checks (by hand; `load_go` checks only lane, stage and non-empty fields)

1. Protocol, amendment 2 file, this manifest, S1 `report.json`/`publication.json`, the six checkpoints and the corpus
   pin hash to the values above; `CUR` HEAD equals `current_tree_head`; `git status --porcelain` in `CUR` is empty
   (no untracked `src`/`scripts`).
2. P3 receipt `complete`, `drained`, returncode 0 and a `charged` P3 row exist; the evaluator's `--plan-only` output
   lists 24 owners, scenes 3160 to 3163 only, and no 3170 to 3177.
3. Writer lock free; no other navigation-lane unit running; `E4` holds only `go-S2.json`; no ledger `S2` row.
4. Free bytes on the `E` volume at least 18,857,590,784 (measured immediately before launch).
5. `pacman -Q mesa libglvnd` reports `mesa 1:26.2.5-1` and `libglvnd 1.7.0-3`; `systemctl --user` available.

## Post-run gate

- **Unit:** receipt `complete`, `drained`, returncode 0, no survivors; ledger `charged` S2 row; charged CPU recorded
  against the 4,435 reservation and the 837.785 spent so far.
- **Report (`eval/report.json`, published last with a source-pin recheck):** `route: development`, `status:
  completed` and no `failure.json`; 24 owners all `completed-recording`; `finalization_errors` empty; `assets_after`,
  `identities_after` and `final_source_pins` equal the before values; `teacher_queries` 0 for every owner; 24 `.snp`
  files.
- **Result:** report the per-seed, per-arm count of 4 for the augmented seeds and the old-corpus arm. The `admission`
  field says whether S3 may be prepared. An independent compact AI audit of the report (as for S0z) precedes any
  claim; it is AI review, not human acceptance.

## On failure

An owner timeout, kill or non-normal disposition stops the stage (`failed-infrastructure`, `failure.json`) and is
charged; nothing is replaced or retried. A completed run that does not meet 3 of 4 on every augmented seed is the
real result: it is reported as such and S3 is not run. Evidence is retained either way.

## Dry validation performed (not stage S2)

The evaluator's and binding's tests (46 passed) and the P3 import probe (passed, 29.042 CPU-s) were run. **No S1
checkpoint has been loaded and no Engine owner has run**; the real Engine and checkpoint path is first exercised by
S2 itself, which is the main residual risk beyond the 1,800 s deadline noted above.
