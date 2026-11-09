# MaleCNS v4 S0a: teacher collection regeneration, execution manifest (prospective)

> **Status:** prepared, **not executed**. S0a is the first regenerating S0 sub-stage, a
> **scientific attempt** (`scientific_attempt: true`). There is one attempt only. It needs an
> explicit owner GO naming this manifest's sha256 and the plan-only sha256 below. Nothing here
> has run the producer.

Protocol: `docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json`, sha256
`cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477` (Amendment 1 + erratum 1).
Stage P passed on 9 November 2026 (`docs/reports/male-v4-stage-p/RESULT.md`).

## What S0a runs

The unchanged `scripts/collect_male_teachers.py` runs from the detached producing-commit
worktree at `cc1cea93d4c3333a0ee2a091dd34fff0b2986887` (producer sha256 `ca633269…025b`). The
driver `scripts/regenerate_male_navigation_v4.py --stage S0a` executes it as a subprocess. S0a
has no overlay, port or pin document: it is the first sub-stage, so it takes no previous record.

- **Development teacher stage only:** `--research-stage development` runs
  `teacher_collection_stages.development = [train, dev]`. Those are train scenes 1000–1007 and
  recorded-dev scenes 1008–1011, 12 runs, each at most 600 ticks. Held-out teacher scenes
  1012–1015 are never run; `held_out` would require an unlock the driver does not allow.
- **Protocol:** `--protocol` is the original frozen v2 training protocol at cc1cea9,
  `docs/plans/m7-training-v2-protocol.json`, sha256 `8f360289…d69b`. The producer re-checks it
  against `male_research.PROTOCOL_SHA256`, and the driver pins it as a fixed file and a source guard.
- **Repo:** `--repo` is the producing worktree itself (the driver refuses any other).
- **Assets:** `--assets /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn`. Verified on
  9 November 2026 with cc1cea9's own `palimpsest.assets.verify_assets` against cc1cea9's
  `model_manifests/flynn-full-vision.json`. Both pinned files are `verified`:
  `drosophila adult connectome.7z` (45,111,367 B, `49d19491c1df4b8f02af0e285b71dc171f47488a93ee5b91be8ee4e280bee9f1`) and
  `connectome_rnn_dagger_princeton_full_vision.pt` (108,220,841 B, `fde5327c1531f15340385b7a572b5c7a785e1ce29cde622976bee6e398e9d8d6`).
  The worktree's own `data/assets/flynn` lacks both files (`missing`), so it is not used.
- **Output:** `--output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/collection`
  inside the reserved v4 data root. It must be fresh; the producer creates it exclusively.
- **Known drift (protocol):** HEAD differs from cc1cea9 by the research-module refactor
  `6a5cb7e`. Running at cc1cea9 sidesteps it; the driver verifies HEAD, cleanliness, producer
  bytes and the source guard.

## Plan-only result (no producer executed)

```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B \
  /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/regenerate_male_navigation_v4.py \
  --stage S0a --worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/cc1cea9 --plan-only -- \
  --repo /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/cc1cea9 \
  --assets /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn \
  --output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/collection \
  --protocol /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/cc1cea9/docs/plans/m7-training-v2-protocol.json \
  --research-stage development
```

Status `admissible`, exit 0. The saved output is [`plan-only.json`](plan-only.json), sha256
`c52e0e649cf6ad0fc188fdd4bdfb751ae49076bbf7afd1fa036d4d7682e7137f`. It records a detached,
clean worktree at cc1cea9, the producer and source-guard shas, every argument and the exact
`would_run` command. Plan-only never opens a data input or executes a producer.

## Budget and unit

From the protocol's Amendment 1 cost table: S0a expected 277.697 s; `RuntimeMaxSec` 1,260
(`collection_limits.development_seconds` 1,200 + `outer_grace_seconds` 60); `TimeoutStopSec`
5; CPUQuota k = 1 (owner decision 7). The worst case is k × (1,260 + 5) = **1,265 CPU-s**.
Navigation lane charge before S0a: 87.106 of 14,400 CPU-s (v3 prior 1.832 + P 85.274), in the
global ledger `~/.local/state/palimpsest/research-ledger.jsonl`. 87.106 + 1,265 ≤ 14,400, so S0a
is admissible. The admission rule then charges the census CPU, or the full worst case without
a complete receipt.

## GO record

Write it at `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0a/go-S0a.json`.
Both `run_research_stage.load_go` and the driver's `check_go` read it:

```json
{"decision": "GO", "lane": "navigation", "stage": "S0a",
 "protocol_sha256": "cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477",
 "plan_sha256": "c52e0e649cf6ad0fc188fdd4bdfb751ae49076bbf7afd1fa036d4d7682e7137f",
 "manifest_sha256": "<sha256 of this file>",
 "worktree": "/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/cc1cea9",
 "worktree_head": "cc1cea93d4c3333a0ee2a091dd34fff0b2986887",
 "current_tree_head": "<authority-paper-rewrite HEAD>",
 "scientific_attempt": true,
 "granted_by": "<owner>", "granted_at": "<date>"}
```

## Pre-launch checks (all must hold; any failure means no launch, and nothing is charged)

1. `CUR=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite` is at the
   research head carrying this manifest. Its protocol file hashes to `cd4eb130…d477`.
2. The plan-only command above, re-run, prints output whose sha256 is still `c52e0e64…137f`.
   That confirms worktree HEAD, detached, clean tracked files, no untracked `src`/`scripts`,
   producer `ca633269…`, source guard `8f360289…` and argument shapes.
3. The asset check above still reports `ok: true` with the same two shas. Record the sha256 of
   both files and of `graph-49d19491…/palimpsest-prepared.json` before launch, for the
   unchanged-assets check after.
4. `male-v4-runs/S0a/` exists and is empty. `collection` and `pin-record.json` do not exist.
   `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0a/receipt` does not exist.
5. Free space on `/home` ≥ 1 GiB floor + 3 GiB `source_limits.max_bytes` (72 GB free on
   9 November 2026).
6. The ledger has no `navigation/S0a` row. No other navigation-lane unit is running.
7. `upstream/fly-gym` in the worktree is initialised (137 files).

## Launch (charged; one attempt)

<!-- s0a-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage S0a --cpu-quota-k 1 --runtime-max-sec 1260 --worst-case-cpu 1265 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0a/go-S0a.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0a/receipt \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/regenerate_male_navigation_v4.py \
  --stage S0a --worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/cc1cea9 \
  --go /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0a/go-S0a.json \
  --pin-record-out /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/pin-record.json \
  -- \
  --repo /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/cc1cea9 \
  --assets /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn \
  --output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/collection \
  --protocol /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/cc1cea9/docs/plans/m7-training-v2-protocol.json \
  --research-stage development
```

The driver is run with `-B` but not `-I`, because it imports its sibling probe module. It
launches the producer with the locked interpreter and an explicit environment: `PATH`, `HOME`,
`LANG`, `MUJOCO_GL=egl`, `CUDA_VISIBLE_DEVICES=` and `PYTHONPATH=<worktree>/src:<worktree>/scripts`.

## Expected outputs

- `male-v4-runs/S0a/collection/`: `collection.json` (`status: completed`, `stage: development`,
  12 `runs`: 8 `train` 1000–1007 and 4 `dev` 1008–1011, each `completed` with `ticks`, `files`
  and close status; `finalization_errors: []`; `runtime_source_unchanged`, `protocol_unchanged`,
  `script_unchanged`, `recordings_unchanged`, `within_deadline` and
  `research_sources_unchanged` all true), `protocol.json`, `collector.py`, and `runs/<run>/`
  recordings and snapshots.
- **Pin record** `male-v4-runs/S0a/pin-record.json` (fsynced, exclusive). It holds
  schema `m7-navigation-v4-pin-record-1`, stage S0a, producing commit cc1cea9, `go_sha256`,
  sha256 and bytes of every output file, and `counts` read from `collection.json`:
  `{baseline_train: [8 tick counts], dev: [4 tick counts]}`. S0b and the recovery-learning count
  fields trace to these counts. Each train run must have at least 32 ticks (producer rule).
- `male-v4-s0a/receipt/`: `receipt.json` (cgroup census, drained, survivors), `stdout.log`
  (producer progress lines and the driver's `completed` JSON) and `stderr.log`.
- Ledger: one `reserved` row (1,265) and one `charged` row for `navigation/S0a`.
- After the run, the three asset shas from pre-launch check 3 are unchanged.

## On failure

Per protocol `execution_stops`, any S0 producer refusal, guard mismatch, pin mismatch,
RuntimeMaxSec kill, storage breach or nonzero exit **ends v4**. That includes a driver
`refused`, `producer-failed` or `record-refused` status, a failed `collection.json`, a missing
pin record, or a unit that is not drained. Later stages stay `not_started`. There is no retry,
substitution, filtering, recollection or budget change. The first fault and all partial outputs
are retained as they are, the charge stands (census, or 1,265 CPU-s without a complete receipt),
and any further work needs a new protocol version.
