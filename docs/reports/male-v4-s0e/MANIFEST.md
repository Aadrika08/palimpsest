# MaleCNS v4 S0e: advice collection (port tree T-e) with S0e-D, S0e-A and S0e-I, execution manifest (prospective)

> **Status:** prepared, **not executed**. S0e is a **scientific attempt**
> (`scientific_attempt: true`) with one attempt only. It consists of four sequential
> `run_research_stage.py` units: **S0e** (launcher and collection), **S0e-D** (drain receipt),
> **S0e-A** (root raw audit) and **S0e-I** (index publication). Each unit needs its own owner GO
> record naming its stage, this manifest's sha256 and the plan sha256s below. Nothing here ran
> the launcher, a controller subcommand, the driver in GO mode or the collector. Every earlier
> review amendment is carried in the body from the start: by-hand GO binding including
> `current_tree_head`, no placeholders, write-order directory preconditions, the writer lock,
> throttling and an extended post-run gate.

Protocol: `docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json`, sha256
`cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477`. It is not edited.

## Prerequisite done in this branch: the S0e pin documents (commit `117d646`)

S0e's driver validates four v4 copies with consumers' rules: contact-v2, recovery index, study
plan and recovery learning. Before this branch, three of them still held placeholders or
inactive Amendment 1 fields: the recovery index `training_source_*`, contact-v2 `prior_version`,
and the whole study-plan copy.

Commit `117d646` activates those fields in `declared-fields.json` (recorded under
`amendment_1_pending.activated`). It gives every field a fill source and adds four checked fill
classes to the driver:

- `commit` is the producing commit;
- `source-map` and `path-keys` are read from the S0d seed `protocol.json`, re-hashed against the
  seed pin records and identical across seeds 10/11/12;
- `port-sha256` is a T-e port byte pin, checked against the T-e worktree file;
- `doc-path` values are repo-relative, as in the originals.

The copies were regenerated at their placeholders and filled with `--fill-document` from the
three S0d seed records (merged with the S0d controller record) and the S0c record (through the
chain), in dependency order:

| Copy | sha256 | Filled from |
| --- | --- | --- |
| `male-recovery-research-development-v1.json` | `ab42f9c55bd110be8a89933aa4f9decf55e7b7827cc1c5d0ef9b47bdde535618` | S0d: producer root (T-d worktree), terminal and supervisor paths and shas, pairs and report shas, inventory sha (controller declared value), `training_source_code` and `model_inputs` (seed `protocol.json`), `training_source_commit` `02e861f8…`; S0c: data manifest path and `052a8dbd…` |
| `m7-navigation-study-protocol.json` | `4939f9c91fd84c74fe1e467b9a231ba86f48694c57159ba50cc26d938a8299f5` | T-e port bytes of `male_recovery_research.py` and `prepare_male_recovery_data.py`; shas of the index and recovery-learning copies |
| `m7-navigation-contact-v2-protocol.json` | `cadd0e45190cc2a6f4bbc742c8b38f065bbe2c831f42b8f84cef4bd75d3b1de3` | index copy path and sha, T-d producer root, three pair report shas, S0c data manifest sha, study-copy path and sha, T-e `collect_male_navigation.py` port bytes `f9655201…` |
| `m7-recovery-learning-protocol.json` (unchanged) | `9c0ae9efb2c70908b755daeba4157d32b5daf792807fcaf18ed05f54d23a77df` | S0a/S0b (filled before S0c) |

`declared-fields.json` now has sha256 `96d5b6634c1e4dd47bfe5bce148024bf2601319ba4c4f99a83acca0290a9d722`.
A test re-traces every S0e copy against the live merged S0d chain through the driver's
`load_pin_documents`, which is what S0e runs. Only the data-v2 copy (consumed by S0f) still holds
placeholders.

## What S0e runs

| Unit | Command (from `CUR`) | Writes |
| --- | --- | --- |
| **S0e** | `run_male_navigation_v4_s0e.py launch`: enclosing supervisor → launcher → driver `--stage S0e` (T-e port `collect_male_navigation_v2.main`, in-process) | `R/collection/` (12 owners), `R/control/` (`invocation.json`, inventories, `terminal.json`, `enclosing.json`, `outer-launch/` and `outer-supervisor/` supervisors, `collector-pin-record.json` and its `.port-pins.json` locator) |
| **S0e-D** | `… drain`: reads the S0e unit's launcher receipt and ledger `charged` row | `R/control/exec-drain.json` |
| **S0e-A** | `… audit`: v2 root raw-audit scope; worker imports the T-e readers read-only | `R/control/root-raw-audit.json` |
| **S0e-I** | `… index`: needs a passed audit, unchanged inputs | `R/control/collection-index.json`, `R/control/controller-record.json` |

- **Stage root `R`:** `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0e`.
- **Worktree:** `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-e`,
  HEAD = recorded port commit `703acc503c43b13d9f2d5f8ddc05b29f72fc0247` (base `736e0cf`, branch
  `port/male-v4-t-e`). The port producer sha256 is `5d7ddef2…`, with port guard
  `collect_male_navigation.py` `f9655201…`. The launcher and the audit both refuse any other HEAD.
- **Previous records:** the three S0d seed pin records, in order 10, 11, 12:
  `…/port-t-d/runs/S0d/control/pairs/seed-{10,11,12}/pin-record.json`, sha256 `4ce884fb…baaa`,
  `6fc8bb5f…38dc` and `bd87a1de…0b7c`. The driver merges them with the S0d controller record
  `831d140a…9823` (`merge_controlled`).
- **Assets:** `/home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn`. Verified with T-e's own
  `verify_assets` against T-e's `model_manifests/flynn-full-vision.json` (`e319bb18…`, identical
  to S0a/S0b): both FLYNN files are `verified`. `male-reduced-v1/source-graph.json` is
  `5aba0fef…`. The worktree's own `data/assets/flynn` lacks the FLYNN files.
- **Cases:** fixed in the producer: scenes 3100–3103 × learners 10, 11, 12, in
  `learner-<scene>-seed-<learner>` order. There are 12 owners, at most 600 ticks each. Learners are
  the S0d `original` checkpoints only; `degree_rewired` fits are never loaded (owner decision 2).
- **Launcher inventories:** source (T-e tracked), upstream, assets, corpus (`male-v4-runs/S0a`,
  `S0b`, `S0c`) and bundle (`port-t-d/runs/S0d`). Controls: the S0e controller, controls module,
  driver, GO and the three seed records.
- **EGL / rendering: applicable.** The collector renders both cameras through MuJoCo EGL
  (`MUJOCO_GL=egl`). The host graphics stack is `mesa 1:26.2.5-1` and `libglvnd 1.7.0-3`,
  checked on 9 November 2026; it must be re-checked before and after S0e and any change reported.
  The stage P EGL identity record (`docs/reports/male-v4-stage-p/probe-report.json.gz`, S2 child)
  is the reference context. Thread environment: `OMP_NUM_THREADS=1` in the controller's child
  environment and in the collector's owner children, matching stage P's S0e entry.

## Plan-only results (nothing executed)

The plans were run in this branch's agent worktree. Each `*.prepared-in-agent-worktree.json` is
the raw output. The `*.json` beside it is the same bytes with the agent-worktree prefix replaced
by `CUR=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/` (the only
difference; a test checks it). Pre-launch check 2 re-derives these from `CUR`.

| Plan | Status | CUR sha256 |
| --- | --- | --- |
| [`driver-plan.json`](driver-plan.json) (`--stage S0e`, seeds as previous) | admissible | `3bd12d9f7b9fe7db68284944d4a9034cff9c7751102be7fbcd8a7ce995c5a997` |
| [`launch-plan.json`](launch-plan.json) | plan-only | `7dd7b72fdb2f2384c4b2b34ca58276857d850af789b390b16cee221b333a8382` |
| [`drain-plan.json`](drain-plan.json) | plan-only | `1a16a802f5cdf372418b8d9ce41145da2986c07974e31dd1dd04121112e1ca35` |
| [`audit-plan.json`](audit-plan.json) | plan-only | `01b69218c23005aea78493e26c1090431114d654541b48b723404a370c24df9b` |
| [`index-plan.json`](index-plan.json) | plan-only | `d809f682df1811e3649367401d9cbbc1cbcc3fb23b55ede7a0f9b57ee9970d95` |

The plans were re-derived after the review fix `4d95f77` (port-byte pins are now checked at the
field's own port tree). All five outputs are byte-identical, because the plans carry no code, so
the sha256s above stand. The driver plan records the T-e port check, the three previous record
shas, all four documents (shas above) and the live locator. The launch plan's `collector_command` producer arguments equal
the driver plan's `would_run`.

## Budget, units and deadlines

Amendment 1 cost table: S0e `RuntimeMaxSec` 2,240 (the owner-resolved kill target; the ceiling
that keeps S0–S2 admissible is 2,285). D, A and I have 30, 150 and 30 s. All use
`TimeoutStopSec` 5 and k = 1. Worst cases are k × (kill + 5):

| Unit (`--stage`) | RuntimeMaxSec | Worst CPU-s | Receipt dir |
| --- | ---: | ---: | --- |
| `S0e` | 2,240 | 2,245 | `…/male-v4-s0e/receipt-S0e` |
| `S0e-D` | 30 | 35 | `…/male-v4-s0e/receipt-S0e-D` |
| `S0e-A` | 150 | 155 | `…/male-v4-s0e/receipt-S0e-A` |
| `S0e-I` | 30 | 35 | `…/male-v4-s0e/receipt-S0e-I` |

**Admissibility.** The navigation lane has been charged 330.857 CPU-s: v3 prior 1.832, P 85.274,
S0a 97.378, S0b 9.472, S0c 6.378 and S0d 130.525, in
`~/.local/state/palimpsest/research-ledger.jsonl`. The worst cases still ahead through S2 are
S0e 2,470 (all four units), S0f 268, S0z 305, S1 2,165 and S2 4,435, a total of 9,643. That gives
330.857 + 9,643 = **9,973.857 ≤ 14,400**, with 4,426.143 CPU-s of slack. Every stage through
development stays admissible even at worst case, and the 2,240 s kill is under the 2,285 s
ceiling.

**Held-out threshold basis.** S3 is admitted only if the measured v4 charge through S2 is
≤ 5,643.168 CPU-s; that charge excludes the 1.832 v3 prior, which the threshold already deducts.
The measured v4 charge so far is **329.025** (330.857 − 1.832). At the protocol's expected costs
for the remaining stages, it would be about **2,555** through S2:

| Stage | Expected (s) |
| --- | ---: |
| S0e | 543.022 |
| S0e-D | 5 |
| S0e-A | 43.1 |
| S0e-I | 5 |
| S0f | 79.46 |
| S0z | 82 |
| S1 | 480 |
| S2 | 988.524 |

That is well under 5,643.168. The threshold is decided by measured charges, not by this estimate.

**Deadline nesting (S0e).**

| Bound | Seconds |
| --- | ---: |
| collector owner child | 180 |
| collector's own stage deadline (`verify`: started + 2,160) | 2,160 |
| launcher's collector supervision, from the enclosing start | normal return 2,210 |
| enclosing launcher supervision | 2,210 + 10 grace |
| unit `RuntimeMaxSec` | 2,240 |

The enclosing evidence (after-inventory, `enclosing.json`) is written after the launcher returns.
A collection that reaches the 2,210 s bound is a failure regardless.

**The binding deadline is the 180 s per-owner cap, not 2,210 s.** Each of the 12 owners runs
under `min(180, collector deadline − now)`. v2's collector took 514 s for 12 owners, about 43 s
per owner, so per-owner headroom is about 4x. Twelve owners at the cap (2,160 s) would still
exhaust the collector's own 2,160 s deadline before the 2,210 s normal-return bound.

**Throttling risk (stated, not blocking).** The v2 historical figures are collector 514 s,
launcher 543 s and enclosing pre-publication 545 s. They were unconstrained wall time; the
per-owner headroom (about 4x against 180 s) is the binding margin. CPU under CPUQuota 100% was never measured; rendering uses
the GPU through EGL, while physics, the learner and the teacher run on the CPU. The
inventories hash about 650 MB of corpus plus the S0d bundle twice, inner and outer. Any timeout,
owner deadline or RuntimeMaxSec kill is an operational failure that ends v4.

## GO records (one per unit)

Write `go-S0e.json`, `go-S0e-D.json`, `go-S0e-A.json` and `go-S0e-I.json` in
`/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/`. Each record's
`stage` is its unit; all other binding fields are identical:

```json
{"decision": "GO", "lane": "navigation", "stage": "S0e",
 "protocol_sha256": "cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477",
 "manifest_sha256": "<sha256 of this file>",
 "plan_sha256": {"driver": "3bd12d9f7b9fe7db68284944d4a9034cff9c7751102be7fbcd8a7ce995c5a997",
                 "launch": "7dd7b72fdb2f2384c4b2b34ca58276857d850af789b390b16cee221b333a8382",
                 "drain": "1a16a802f5cdf372418b8d9ce41145da2986c07974e31dd1dd04121112e1ca35",
                 "audit": "01b69218c23005aea78493e26c1090431114d654541b48b723404a370c24df9b",
                 "index": "d809f682df1811e3649367401d9cbbc1cbcc3fb23b55ede7a0f9b57ee9970d95"},
 "previous_pin_records_sha256": ["4ce884fba00b6d51e162435d4cfa79d1de70e0a6ccca9760f34e0721192fbaaa",
                                 "6fc8bb5fa4fa2888dba0f0f868c98a8f54b0386435e5e9c1b2256b292cf038dc",
                                 "bd87a1debdc92c99417330a4d006d3a9de7cb4e91b9263577125639a2d5b0b7c"],
 "s0d_controller_record_sha256": "831d140ae0edfdc2636196744ac3cbe42a4613d40c0312e4e72455e06c679823",
 "chain_pin_record_sha256": {"S0a": "d8e511b8d8095c8d781a0ecfb2b031571c4f6fd72d0367b88520643d0f653901",
                             "S0b": "b3511f1a3bf625dd4cec20733317b5288bb965cde6873fbb1023a768e02809cb",
                             "S0c": "8044fa1ab5a01db56ae19d1c4ee9a63daba8a670297ab42c4ab83f967e7e657c"},
 "pin_document_sha256": {"male-recovery-research-development-v1.json": "ab42f9c55bd110be8a89933aa4f9decf55e7b7827cc1c5d0ef9b47bdde535618",
                         "m7-navigation-study-protocol.json": "4939f9c91fd84c74fe1e467b9a231ba86f48694c57159ba50cc26d938a8299f5",
                         "m7-navigation-contact-v2-protocol.json": "cadd0e45190cc2a6f4bbc742c8b38f065bbe2c831f42b8f84cef4bd75d3b1de3",
                         "m7-recovery-learning-protocol.json": "9c0ae9efb2c70908b755daeba4157d32b5daf792807fcaf18ed05f54d23a77df"},
 "declared_fields_sha256": "96d5b6634c1e4dd47bfe5bce148024bf2601319ba4c4f99a83acca0290a9d722",
 "worktree": "/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-e",
 "worktree_head": "703acc503c43b13d9f2d5f8ddc05b29f72fc0247",
 "port_tree": "T-e",
 "current_tree_head": "<authority-paper-rewrite HEAD at launch>",
 "cpu_quota_k": 1,
 "scientific_attempt": true,
 "granted_by": "<owner>", "granted_at": "<date>"}
```

## Pre-launch checks (all must hold before the S0e unit; any failure means no launch, and nothing is charged)

1. **Current tree:** `CUR=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite`
   is at the research head carrying `117d646`, the review fix `4d95f77` and this manifest, with
   clean tracked files. In `CUR`, the protocol file is `cd4eb130…`, `declared-fields.json` is
   `96d5b663…` (the GO's `declared_fields_sha256`) and the four copies hash to the GO's
   `pin_document_sha256`.
2. **Plans:** the five plan commands (the launch, drain, audit and index commands below without
   `--go` and without the launcher prefix, plus the driver plan: `regenerate_male_navigation_v4.py
   --stage S0e --worktree <T-e> --previous-pins <seed 10, 11, 12 records> --plan-only -- --repo
   <T-e> --assets <assets> --output R/collection`) must print outputs with the five CUR sha256s
   above when run from `CUR`.
3. **Records:** the three S0d seed records, the S0d controller record and the S0a/S0b/S0c records
   hash to the GO values.
4. **GO binding (by hand, for each of the four GO records; `load_go`/`check_go` do not compare these):**
   - `stage` is the unit's stage, and `manifest_sha256` is the sha256 of this committed file;
   - every `plan_sha256` entry matches check 2, and `declared_fields_sha256` matches check 1;
   - `previous_pin_records_sha256` and the chain and document shas match checks 1 and 3;
   - `cpu_quota_k` is 1, matching `--cpu-quota-k 1`;
   - `worktree_head` is `703acc50…`;
   - `current_tree_head` is CUR's HEAD at launch;
   - no `<…>` placeholder remains anywhere in the record.
5. **Writer lock free:** no palimpsest lab, producer or research stage is running in any lane, and
   nothing holds `~/.cache/palimpsest/writer.lock` (`fuser` empty). The collector takes it for
   the whole collection.
6. **Directories, by write order.**
   - `male-v4-runs/S0e` must **not exist**. The launcher requires it fresh, then creates
     `S0e/control`; the driver then writes `control/collector-pin-record.json.port-pins.json`
     (`open('xb')`) and the collector creates `S0e/collection` exclusively.
   - `male-v4-s0e/` exists and holds the four GO records. `receipt-S0e`, `receipt-S0e-D`,
     `receipt-S0e-A` and `receipt-S0e-I` must not exist.
   - Before D, A and I, their outputs (`R/control/exec-drain.json`, `root-raw-audit.json`,
     `collection-index.json`, `controller-record.json`) must not exist.
7. **Worktree:** `port-t-e` is detached at `703acc50…`, with tracked files clean and no untracked
   `src`/`scripts`; `upstream/fly-gym` is initialised.
8. **Assets and graphics:** the asset check above still reports `ok: true` with the same shas.
   `pacman -Q mesa libglvnd` reports `mesa 1:26.2.5-1` and `libglvnd 1.7.0-3`.
9. **Disk:** free space on `/home` must be at least the collector's up-front full-study admission
   reservation (17,783,848,960 B in v2) plus the 1 GiB floor. The collection itself is capped at
   3 GiB; v2 used 1.14 GB.
10. **Ledger:** no `navigation/S0e`, `S0e-D`, `S0e-A` or `S0e-I` row. No other navigation-lane
    unit is running.

## Launch (charged; four units in order, one attempt each; stop at the first failure)

<!-- s0e-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage S0e --cpu-quota-k 1 --runtime-max-sec 2240 --worst-case-cpu 2245 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/go-S0e.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/receipt-S0e \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_male_navigation_v4_s0e.py launch \
  --worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-e \
  --previous-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d/runs/S0d/control/pairs/seed-10/pin-record.json /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d/runs/S0d/control/pairs/seed-11/pin-record.json /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d/runs/S0d/control/pairs/seed-12/pin-record.json \
  --assets /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn \
  --stage-root /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0e \
  --corpus /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0c \
  --bundle /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d/runs/S0d \
  --go /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/go-S0e.json
```

<!-- s0e-d-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage S0e-D --cpu-quota-k 1 --runtime-max-sec 30 --worst-case-cpu 35 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/go-S0e-D.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/receipt-S0e-D \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_male_navigation_v4_s0e.py drain \
  --stage-root /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0e \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/receipt-S0e \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/go-S0e-D.json
```

<!-- s0e-a-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage S0e-A --cpu-quota-k 1 --runtime-max-sec 150 --worst-case-cpu 155 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/go-S0e-A.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/receipt-S0e-A \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_male_navigation_v4_s0e.py audit \
  --stage-root /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0e \
  --port-worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-e \
  --go /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/go-S0e-A.json
```

<!-- s0e-i-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage S0e-I --cpu-quota-k 1 --runtime-max-sec 30 --worst-case-cpu 35 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/go-S0e-I.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/receipt-S0e-I \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_male_navigation_v4_s0e.py index \
  --stage-root /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0e \
  --go /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0e/go-S0e-I.json
```

**Order and stop rule.** The units run in this order: S0e, then S0e-D after the S0e unit has
exited and its cgroup is collected, then S0e-A, then S0e-I. Before each next unit, confirm that
the previous unit's launcher printed exit 0 and its own gate items below hold. The first failure
ends v4, and later units are not started.

## Post-run gate (before any S0f preparation)

- **S0e unit:**
  - `enclosing.json` and `terminal.json` both `status: completed-collection`;
  - `controls_unchanged`, `inventories_unchanged` and `outer_inventory_unchanged` true;
  - `cleanup` and `outer_cleanup` with `sampler_stopped` true, and `forced_signals`, `survivors`,
    `sample_errors` and `conflicting_owned_identities` `[]`;
  - `wall_seconds ≤ 2210`, and `terminal.head` is `703acc50…`;
  - `terminal.report_sha256` equals `R/collection/report.json`;
  - both supervisors `completed` with returncode 0 and no `error`/`failure`.
- **Collection:**
  - `report.json` has `status: completed-collection`, `owners_completed: 12`, cases in
    `learner-3100-seed-10 … learner-3103-seed-12` order and `qualification_claims: []`;
  - `source_pins == final_source_pins`, `assets_before == assets_after` (ok), and
    `identities_before == identities_after`;
  - `numeric_ticks` equals the sum of the per-case rows, and every case is 1..600;
  - there are exactly 12 initial snapshots.
- **Collector pin record (`R/control/collector-pin-record.json`):**
  - stage S0e, producing commit `703acc50…`, `go_sha256` equal to `go-S0e.json`;
  - chain keys `[S0a, S0b, S0c, S0d, S0e]`, with `chain.S0d` the merged S0d entry (output root
    `port-t-d/runs/S0d`, `producer_records` equal to the three seed shas, `controller_record_sha256`
    `831d140a…`);
  - `port.locator_sha256` equal to the sha256 of the written locator, which names the four copy shas;
  - `counts` holding all 12 advice cases, each 1..600, equal to the report rows.
- **S0e-D:** `exec-drain.json` has `status: drained`, `exec_exitcode` 0 (int), and
  `matching_survivors` and `forced_signals` `[]`. Its `ledger_row` is the S0e `charged` row for
  `receipt-S0e`.
- **S0e-A:** `root-raw-audit.json` has `status: passed`, `failures: []`, **`not_covered: []`** and
  `native_or_model_import: false`. Every check passed, including `reader_isolation` (reader origin
  in `port-t-e`), `shared_validators`, `contact_incidence`, `finite_arrays` and `tick_counts`.
  `run_male_navigation_v4_s0e.audit_passed(path)` (the S0z check) returns it without any waiver.
- **S0e-I:**
  - `collection-index.json` has `status: completed-collection` and `qualification_claims: []`;
  - `immutable_inputs` holds the seven data-v2 S0e inputs, each path, sha256 and bytes equal to
    the file;
  - `coverage.cases` are in order with intervals equal to the report;
  - `audits.root_raw.status: passed`;
  - `controller-record.json` binds every `R/control` document and the collector pin record;
  - `regenerate_male_navigation_v4.previous_chain([collector-pin-record], 'S0f', …)` succeeds.
- **Units:** all four launcher receipts are `complete` and `drained` with returncode 0 and no
  survivors. The ledger has four `charged` rows.
- **S0f dry-load (no producer):** the S0f pin documents the S0e outputs do not change must load
  against T-f. `regenerate_male_navigation_v4.load_pin_documents({'documents':
  ['m7-navigation-contact-v2-protocol.json']}, <CUR pins>, <declarations>, <port-t-f>, <chain>)`,
  with `chain` from the merged S0d records, must return contact-v2 `cadd0e45…`. The T-e collector
  pin is checked at the T-e port commit, not at T-f (`4d95f77`). On the evidence host the test
  `test_s0f_dry_loads_the_contact_v2_copy_against_the_real_t_f_worktree_on_the_evidence_host`
  does exactly this. The data-v2 copy is filled before S0f from the S0e records, so it is not
  dry-loaded here.
- **Recorded limitation (no fix needed now):** T-f carries the T-e collector port, but its v1
  `scripts/collect_male_navigation.py` is the unported `d0decc66…`. T-f's
  `collect_male_navigation_v2.source_pins` would therefore raise, because contact-v2
  `prior_version.collector_sha256` pins the T-e port bytes `f9655201…`. No S0f code path calls
  `source_pins`: S0f's `prepare_male_navigation_v2` uses the collector's `PLAN_SHA`, `PROFILE`,
  `PROFILE_SHA`, `CASES` and `admit_record`.
- **Graphics stack:** unchanged after the run.

Record the collector pin-record, controller-record and index sha256s in the S0e RESULT and the
S0f GO. Only the data-v2 copy remains to fill before S0f (its S0e and S0f fields).

## On failure

Per protocol `execution_stops`, any S0 producer refusal, guard mismatch, pin mismatch, structural
failure, RuntimeMaxSec kill, storage breach or nonzero exit **ends v4**. This includes:

- any unit refused or nonzero;
- a terminal or enclosing `failed-collection`;
- an S0e-D `not-drained` receipt;
- an S0e-A audit that is not `passed`, or that has `not_covered` items, which S0z refuses
  without an owner waiver;
- S0e-I refusing to publish.

Later units and stages stay `not_started`. There is no retry, substitution, filtering,
recollection or budget change. The first fault and all partial outputs are retained as they are,
each started unit's charge stands (census, or its worst case without a complete receipt), and any
further work needs a new protocol version.
