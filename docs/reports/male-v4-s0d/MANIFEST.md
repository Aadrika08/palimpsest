# MaleCNS v4 S0d: recovery training (rebuilt controller, port tree T-d), execution manifest (prospective)

> **Status:** prepared, **not executed**. S0d is a **scientific attempt**
> (`scientific_attempt: true`) with one attempt only. It needs an explicit owner GO naming this
> manifest's sha256, the four plan sha256s and the chain pin-record sha256s below. Nothing here
> ran the controller, the driver in GO mode or the trainer. The S0a/S0b/S0c review amendments
> are carried in the body from the start: by-hand GO binding, no placeholders, an extended
> post-run gate, the writer lock, directory preconditions and the throttling note.

Protocol: `docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json`, sha256
`cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477`. It is not edited. S0d is the
first stage run by a reconstructed controller (Amendment 1 `reconstructed_controllers` S0d).

| Chain record | Path | sha256 |
| --- | --- | --- |
| S0a | `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/pin-record.json` | `d8e511b8d8095c8d781a0ecfb2b031571c4f6fd72d0367b88520643d0f653901` |
| S0b | `…/male-v4-runs/S0b/pin-record.json` | `b3511f1a3bf625dd4cec20733317b5288bb965cde6873fbb1023a768e02809cb` |
| S0c (previous; chain S0a→S0c) | `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0c/pin-record.json` | `8044fa1ab5a01db56ae19d1c4ee9a63daba8a670297ab42c4ab83f967e7e657c` |

## Pin documents and live locator: no new fill needed

T-d consumes one v4 document and one locator value (`ports.json` T-d: documents
`[m7-recovery-learning-protocol.json]`, `locator_values [data_manifest]`):

- the recovery-learning copy, already filled from S0a/S0b before S0c, sha256 `9c0ae9ef…7df`,
  with no placeholder;
- `data_manifest`, which the driver builds from the **S0c pin record**: `S0c/data/data-manifest.json`,
  sha256 **`052a8dbd7428ffa064a74dfd71792ca6c0f2ae54ea9564ce68eb0a94d5220c72`** (101,620 B).
  This is not the stage-P `PENDING-S0c` placeholder. T-d reads it at import
  (`train_male_recovery.py:19`, `DATA_SHA256`).

The driver writes this live locator per seed as `<pin-record-out>.port-pins.json` (all three
seeds are identical). It is shown in each driver plan below.

## What S0d runs

The rebuilt controller `scripts/run_male_navigation_v4_s0d.py` runs from `CUR`. It runs seeds
**10, 11 and 12 once each, in that order**. Each seed is one driver invocation:
`regenerate_male_navigation_v4.py --stage S0d --worktree T-d --previous-pins <S0c record> --go <GO>
--pin-record-out <stage root>/control/pairs/seed-N/pin-record.json -- --data-manifest <S0c data
manifest> --training-seed N --output <stage root>/seed-N`. The driver runs the T-d port of
`train_male_recovery.py` **in-process**, with the live locator.

- **Worktree:** `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d`,
  HEAD = recorded port commit `02e861f8be9877dd183a659ed1b70d66a9141052` (base `19d275d`, branch
  `port/male-v4-t-d`). The port producer sha256 is `b9cc181f…` and the port reader is `ddefc34d…`;
  guards are listed in the driver plans. The controller refuses any other HEAD.
- **Stage root:** `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d/runs/S0d`.
  It sits inside the T-d worktree **by design**: the recovery index `producer_root` is the
  worktree, and the ported `_gate` reads historical sources there. `runs/` is gitignored and
  untracked. Pairs go to `seed-N/`, controller documents to `control/`.
- **Trainer defaults** (no `--graph`/`--graph-manifest`/`--cell-source` passed; checked
  pre-launch): `data/assets/flynn/male-reduced-v1/source-graph.json` `5aba0fef…`,
  `data/manifests/malecns-reduced-neighborhood-v1.json` `7a205342…` and
  `upstream/fly-gym/models/connectome_rnn_model.py` `707cba79…`. These equal the driver's pins and
  the protocol's ORIGINAL graph and cell.
- **Per pair:** 20 epochs each for the `original` and `degree_rewired` models, Adam .001,
  grad cap 1, CPU float32, one thread. The 600 s trainer wall budget and the 64 MiB pair cap are
  unchanged.
- **Rewired by-products (owner decision 2):** the `degree_rewired` fits are run unchanged and
  retained, and are **never evaluated or cited**. Only `original` checkpoints become S0e advice
  learners.
- **Thread environment:** the controller's child environment sets `OMP_NUM_THREADS`,
  `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` and `NUMEXPR_NUM_THREADS` to 1,
  `CUDA_VISIBLE_DEVICES=` and `MUJOCO_GL=egl`. This matches stage P's S0d entry
  (`OMP_NUM_THREADS=1`). The trainer runs in that process.
- **Inventory** (five parts, before and after). Tracked and upstream counts are derived and
  asserted: on 9 November 2026, `port-t-d` gave tracked **355** and upstream **122**, and HEAD was
  the port commit. The remaining parts are caller-listed (the documented limitation: 181/16/7
  membership did not survive):
  - `raw_documents`: the whole of `male-v4-runs/S0a`, `S0b` and `S0c`, every trainer input
    including pin records and the locator;
  - `model_production`: both seven-file `male-reduced-v1` bundles (T-d worktree and main
    checkout);
  - `runtime`: the interpreter binary, `pyvenv.cfg`, and the torch 2.9.0 and numpy 2.2.5
    `METADATA`.

## Plan-only results (nothing executed)

The plans were run in this branch's agent worktree. Each `*.prepared-in-agent-worktree.json` is
the raw output. The `*.json` beside it is the same bytes with that worktree prefix replaced by
`CUR=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/` (the only
difference; a test checks it). It is what pre-launch check 2 re-derives from `CUR`.

| Plan | Status | CUR sha256 |
| --- | --- | --- |
| [`controller-plan.json`](controller-plan.json) (controller, no `--go`) | plan-only | `b8889dce3ca107cf386ea8349761d9d5b08c8dea6c9a470946b958ecf4c900ec` |
| [`driver-plan-seed-10.json`](driver-plan-seed-10.json) | admissible | `6f2fd6f29cb5c3e3c54ea112340b41812019446d83d8fd2fb6ae1cb4fe3ce63c` |
| [`driver-plan-seed-11.json`](driver-plan-seed-11.json) | admissible | `7b3daee053d74d8af111460d9dc1dfcc231d994d92efe709314a718ac01ebdfa` |
| [`driver-plan-seed-12.json`](driver-plan-seed-12.json) | admissible | `ba1ee07efd24da6db1007f48fbcfc8a899821d52d5091a1ce711130cd503a96c` |

The raw agent-worktree sha256s are `1e26adf5…88b5` (controller) and `6f572f8c…8b0a`,
`8605ca97…1974`, `03b52c65…6b42` (seeds 10–12). Each driver plan records:
- the port check (T-d at `02e861f8…`, detached, clean);
- the previous record `8044fa1a…`;
- the document `9c0ae9ef…`;
- the live locator (`data_manifest` `052a8dbd…`);
- the record argument `--data-manifest` (bytes and sha from the S0c record);
- a fresh `--output <stage root>/seed-N`.

## Budget, unit and deadline nesting

The protocol's Amendment 1 cost table row for S0d gives expected 194.681 s (the historical
enclosing wall); `RuntimeMaxSec` 2,160 (the stage enclosing bound, including the controller);
`TimeoutStopSec` 5; CPUQuota k = 1 (owner decision 7). The worst case is k × (2,160 + 5) =
**2,165 CPU-s**, which matches `run_research_stage.py`'s rule. The navigation lane stood at
200.333 of 14,400 CPU-s before S0d; 200.333 + 2,165 ≤ 14,400, so S0d is admissible.

The controller's deadlines are bound to `docs/reports/m7-recovery-training.json` at `217cbee`:

| Bound | Seconds | Enforced by |
| --- | ---: | --- |
| pair internal | 600 | the trainer's own `deadline` and wall budget; also the controller (a normal exit after 600 s fails the pair) |
| pair supervised | 660 | the controller kills the pair's process group |
| stage internal | 2,100 | the controller: each pair's timeout is min(660, 2,100 − elapsed), and no pair starts after 2,100 |
| stage enclosing | 2,160 | the controller's outer supervisor of its inner process (also `elapsed_seconds ≤ 2160`) |
| unit | 2,160 + 5 stop | `RuntimeMaxSec` / `TimeoutStopSec` |

The bounds nest. Sequential seeds fit even at their supervised caps (3 × 660 = 1,980 ≤ 2,100).
The internal stage bound leaves 60 s before the enclosing and unit bound for the after-inventory
(about 650 MB of hashing), the terminal, the outer supervisor document, `recovery-index-values.json`
and the controller record.

**Throttling risk (stated, not blocking).** 194.681 s is historical unconstrained wall time, so
headroom is about 11x against 2,100 s and about 3x per pair against 600 s (historical pairs ran
59–65 s). The before and after inventories each hash about 650 MB at CPUQuota 100%. The unit's
2,160 s starts before the controller's outer clock, so the two coincide at worst. Any controller
timeout, trainer `TimeoutError` or RuntimeMaxSec kill is an operational failure that ends v4.

**EGL / graphics: not applicable.** Training renders nothing and creates no GL context. The host
stack (`mesa 1:26.2.5-1`, `libglvnd 1.7.0-3`) is recorded only for continuity.

## GO record

Write it at `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0d/go-S0d.json`.
The controller and each per-seed driver check it with `check_go`, and the launcher with
`load_go`:

```json
{"decision": "GO", "lane": "navigation", "stage": "S0d",
 "protocol_sha256": "cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477",
 "plan_sha256": {"controller": "b8889dce3ca107cf386ea8349761d9d5b08c8dea6c9a470946b958ecf4c900ec",
                 "seed-10": "6f2fd6f29cb5c3e3c54ea112340b41812019446d83d8fd2fb6ae1cb4fe3ce63c",
                 "seed-11": "7b3daee053d74d8af111460d9dc1dfcc231d994d92efe709314a718ac01ebdfa",
                 "seed-12": "ba1ee07efd24da6db1007f48fbcfc8a899821d52d5091a1ce711130cd503a96c"},
 "previous_pin_record": "/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0c/pin-record.json",
 "previous_pin_record_sha256": "8044fa1ab5a01db56ae19d1c4ee9a63daba8a670297ab42c4ab83f967e7e657c",
 "chain_pin_record_sha256": {"S0a": "d8e511b8d8095c8d781a0ecfb2b031571c4f6fd72d0367b88520643d0f653901",
                             "S0b": "b3511f1a3bf625dd4cec20733317b5288bb965cde6873fbb1023a768e02809cb",
                             "S0c": "8044fa1ab5a01db56ae19d1c4ee9a63daba8a670297ab42c4ab83f967e7e657c"},
 "pin_document_sha256": {"m7-recovery-learning-protocol.json": "9c0ae9efb2c70908b755daeba4157d32b5daf792807fcaf18ed05f54d23a77df"},
 "locator_data_manifest_sha256": "052a8dbd7428ffa064a74dfd71792ca6c0f2ae54ea9564ce68eb0a94d5220c72",
 "manifest_sha256": "<sha256 of this file>",
 "worktree": "/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d",
 "worktree_head": "02e861f8be9877dd183a659ed1b70d66a9141052",
 "port_tree": "T-d",
 "seeds": [10, 11, 12],
 "current_tree_head": "<authority-paper-rewrite HEAD>",
 "cpu_quota_k": 1,
 "rewired_by_products": "run unchanged, retained, never evaluated or cited (owner decision 2)",
 "scientific_attempt": true,
 "granted_by": "<owner>", "granted_at": "<date>"}
```

## Pre-launch checks (all must hold; any failure means no launch, and nothing is charged)

1. **Current tree:** `CUR` is at the research head carrying this manifest, with clean tracked
   files. Its protocol file is `cd4eb130…`, its recovery-learning copy `9c0ae9ef…`, and its
   controller, controls module, driver and probe are the committed bytes.
2. **Plans:** the controller plan (the command below without `--go` and without the launcher
   prefix) and the three driver plans (`regenerate_male_navigation_v4.py --stage S0d --worktree
   <T-d> --previous-pins <S0c record> --plan-only -- --data-manifest <S0c data manifest>
   --training-seed N --output <stage root>/seed-N`) must print outputs with the four CUR
   sha256s above. They must be run from `CUR`, and all must be `admissible` / `plan-only`.
3. **Records and inputs:** the S0a, S0b and S0c pin records hash to the chain table. The S0c data
   manifest hashes to `052a8dbd…`. The three trainer default files hash to `5aba0fef…`,
   `7a205342…` and `707cba79…`.
4. **GO binding (by hand; `load_go`/`check_go` do not compare these):**
   - `manifest_sha256` is the sha256 of this committed file;
   - every `plan_sha256` entry matches check 2;
   - `previous_pin_record_sha256` is the sha256 of the `--previous-pins` file;
   - `chain_pin_record_sha256`, `pin_document_sha256` and `locator_data_manifest_sha256` match
     checks 1 and 3;
   - `cpu_quota_k` is 1, matching `--cpu-quota-k 1`;
   - `worktree_head` is `02e861f8…`;
   - `seeds` is `[10, 11, 12]`;
   - no `<…>` placeholder remains anywhere in the GO record.
5. **Writer lock free:** no palimpsest lab, producer or research stage is running in any lane, and
   nothing holds `~/.cache/palimpsest/writer.lock` (`fuser` empty).
6. **Directories (S0d differs from S0c):** the stage root `port-t-d/runs/S0d` must **not exist**.
   The controller requires it fresh and creates `S0d/` and `S0d/control/` itself. Each
   `control/pairs/seed-N/` (where the driver writes that seed's locator with `open('xb')` before
   training) is created by the controller before that seed's driver starts. `port-t-d/runs/` may
   be absent. Create `palimpsest-authored-test-evidence/male-v4-s0d/` (GO record);
   `male-v4-s0d/receipt` must not exist.
7. **Worktree:** `port-t-d` is detached at `02e861f8…`, with tracked files clean and no
   untracked `src`/`scripts`. Tracked 355 and upstream 122 (the controller asserts both).
8. **Disk:** free space on `/home` ≥ 1 GiB floor + 192 MiB aggregate pair caps.
9. **Ledger:** no `navigation/S0d` row. No other navigation-lane unit is running.

## Launch (charged; one attempt)

<!-- s0d-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage S0d --cpu-quota-k 1 --runtime-max-sec 2160 --worst-case-cpu 2165 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0d/go-S0d.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0d/receipt \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_male_navigation_v4_s0d.py \
  --go /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0d/go-S0d.json \
  --worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d \
  --previous-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0c/pin-record.json \
  --data-manifest /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0c/data/data-manifest.json \
  --stage-root /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d/runs/S0d \
  --raw-documents /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0c \
  --model-production /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d/data/assets/flynn/male-reduced-v1 /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn/male-reduced-v1 \
  --runtime /home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11 /home/utkarsh/Work/shraddha/palimpsest/.venv/pyvenv.cfg /home/utkarsh/Work/shraddha/palimpsest/.venv/lib/python3.11/site-packages/torch-2.9.0.dist-info/METADATA /home/utkarsh/Work/shraddha/palimpsest/.venv/lib/python3.11/site-packages/numpy-2.2.5.dist-info/METADATA
```

The controller checks the protocol, GO stage, unit `work` leaf, T-d HEAD, absolute paths and the
fresh stage root before creating anything. Its outer supervisor (2,160 s) runs its inner
controller. The inner controller takes the 0.25 s PID/start sampler, runs the before-inventory
and count assertion, runs seeds 10→11→12, then cleanup, the after-inventory and the terminal.

## Expected outputs

- `runs/S0d/seed-{10,11,12}/`: each holds `report.json` (`completed-research-training`),
  `protocol.json`, `original-graph.json`, `original.pt`, `degree_rewired-graph.json` and
  `degree_rewired.pt`.
- `runs/S0d/control/`:
  - `invocation.json`, `before.json`, `after.json`;
  - `terminal.json` (training_terminal) and `outer-supervisor/supervisor.json` (training_supervisor);
  - `pairs/seed-N/{stdout.log, stderr.log, pin-record.json, pin-record.json.port-pins.json}`;
  - after a pass, `recovery-index-values.json` and `controller-record.json`.
- **Three per-seed pin records**, one per seed, in that seed's control directory. Each holds
  schema `m7-navigation-v4-pin-record-1`; stage S0d; producing commit `02e861f8…`;
  `training_seed` N; `previous_record_sha256` `8044fa1a…`; `go_sha256`; `port` (T-d, locator path
  and sha); chain `[S0a, S0b, S0c, S0d]`; and outputs = the six `seed-N` files with sha256 and
  bytes. The driver merges the three, in seed order, with the controller record for S0e
  (`merge_controlled`).
- `male-v4-s0d/receipt/`: `receipt.json`, `stdout.log` (the controller's summary JSON) and
  `stderr.log`. Ledger: `reserved` (2,165) and `charged` rows for `navigation/S0d`.

## Post-run gate (before any S0e preparation)

- **Controller summary:** `status: completed`. The outer supervisor has `status: completed`,
  `returncode: 0`, `elapsed_seconds ≤ 2160` and `timeout_seconds: 2160`, with no `error` or
  `failure`.
- **Terminal (`_gate` field set):**
  - `status: passed-research-training`;
  - `head` is `02e861f8…`;
  - `inventories_unchanged: true`, with `before_inventory_sha256 == after_inventory_sha256`;
  - `completed_pair_content_unchanged: true`;
  - `inventory_counts` tracked 355 and upstream 122;
  - `cleanup` with `sampler_stopped: true` and `sample_errors`, `forced_signals` and `survivors`
    all `[]` (and `remaining_after_forced` and `conflicting_owned_identities` `[]`);
  - `pairs` = seeds `[10, 11, 12]` in order, each `status: completed` with
    `supervision.status: completed`, `supervision.returncode: 0`, no `error`/`failure`, and
    `supervision.elapsed_seconds ≤ 600`;
  - `stage_seconds ≤ 2100`;
  - no `failure` key.
- **Seed pin records:**
  - exactly three, seeds 10, 11, 12;
  - each with chain keys `[S0a, S0b, S0c, S0d]`, the S0a–S0c entries equal to the published
    records, `previous_record_sha256` `8044fa1a…` and `go_sha256` equal to the GO file sha;
  - outputs exactly the six pair files, each sha256 and bytes equal to the file;
  - `report.json` sha256 equal to `recovery-index-values.json` `pairs[i].report_sha256`.
- **Driver merge (no producer):** `regenerate_male_navigation_v4.previous_chain([seed-10, seed-11,
  seed-12 records], 'S0e', …)` succeeds. That proves the ordered set and the controller record
  (`stage_root`, producer-record shas, document hashes).
- **Recovery index values (for S0e/S0e-I):** `recovery-index-values.json` has `producer_root` =
  the T-d worktree, `training_source_commit` = `02e861f8…`, `training_terminal` and
  `training_supervisor` path and sha equal to the files, `before_after_inventory_sha256` = the
  terminal's, and three `pairs` with `directory` `runs/S0d/seed-N` and `report_sha256`.
- **Unit:** launcher receipt `complete`, `drained`, returncode 0, no survivors; ledger `charged`
  S0d row.
- **Rewired fits:** retained in place, never evaluated or cited.

Record the three seed pin-record sha256s and the controller-record sha256 in the S0d RESULT and
in the S0e GO.

**Known S0e prerequisite (not part of S0d):** before S0e, the v4 recovery index copy
(`male-recovery-research-development-v1.json`) must be filled from the merged S0d chain. Its
`training_source_code`/`training_source_commit` fields are still in `amendment_1_pending`, and its
`path`, `sha256` and `path-keys` fields need named fill sources, as the recovery-learning copy
had before S0c. That needs its own reviewed change.

## On failure

Per protocol `execution_stops`, any S0 producer refusal, guard mismatch, pin mismatch,
RuntimeMaxSec kill, storage breach, nonfinite value, wrong count or nonzero exit **ends v4**.
This includes:

- the controller being `refused` or `failed`;
- any pair `failed` (later seeds stay `not_started`);
- a terminal `failed-research-training`;
- a missing seed pin record or controller record;
- a unit that is not drained.

Later stages stay `not_started`. There is no retry, seed replacement, substitution or budget
change. The first fault and all partial outputs are retained as they are, the charge stands
(census, or 2,165 CPU-s without a complete receipt), and any further work needs a new protocol
version.

## Review amendments (independent AI review, 2026-11-09)

1. **Deadline wording corrected:** `stage_seconds` is measured after cleanup and the
   after-inventory, so both count against the controller's 2,100 s internal bound. The 60 s gap to
   RuntimeMaxSec 2,160 covers only the terminal, supervisor, index-values and controller-record
   writes.
2. **Post-run gate additions, per seed (10, 11, 12):** `report.json` status
   `completed-research-training`, both models `completed`, `training_seed` = N,
   `data_manifest_sha256` = `052a8dbd…`; `protocol.json` `training.research_protocol_sha256` =
   `9c0ae9ef…`; `protocol.json` `model_inputs` names the three default T-d paths with
   `5aba0fef…`/`7a205342…`/`707cba79…`, identical across the three seeds. This `model_inputs`
   block is the named fill source for the recovery index copy's `/model_inputs`.
3. **GO check 4 addition:** `current_tree_head` equals CUR's HEAD at launch (by hand).
4. **Rewired by-products:** `report.json` contains `degree_rewired` histories and dev metrics; per
   owner decision 2 they are retained but the RESULT will not quote, evaluate or cite them.
5. **Limitation recorded:** the v2 run verified one intra-op and one inter-op thread, CUDA
   uninitialised and no MuJoCo import; the rebuilt controller sets the environment and the trainer
   sets intra-op threads, but none of these runtime facts is re-checked. No numerical effect.
6. **S0e prerequisite (complete):** before S0e, fill the recovery index copy's
   `training_source_*` fields and `/model_inputs` from S0d, and `/data_manifest/path` and
   `/data_manifest/sha256` (still PENDING-S0c) from the S0c record.
