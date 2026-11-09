# MaleCNS v4 S0b: recovery first-cycle collection, execution manifest (prospective)

> **Status:** prepared, **not executed**. S0b is a **scientific attempt**
> (`scientific_attempt: true`) with one attempt only. It needs an explicit owner GO naming this
> manifest's sha256, the plan-only sha256 and the S0a pin-record sha256 below. Nothing here has
> run the producer. Every applicable S0a review amendment is carried in the body from the start.

Protocol: `docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json`, sha256
`cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477` (Amendment 1 + erratum 1).
Previous sub-stage: S0a COMPLETED (`docs/reports/male-v4-s0a/RESULT.md`). Its pin record is
`/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/pin-record.json`,
sha256 `d8e511b8d8095c8d781a0ecfb2b031571c4f6fd72d0367b88520643d0f653901`, and the copy in
`docs/reports/male-v4-s0a/pin-record.json` is byte-identical.

## What S0b runs

The unchanged `scripts/collect_male_recovery.py` runs from the detached producing-commit
worktree at `c382c86781a7a5d6651af721119789729cc890ae` (producer sha256 `17d94832…6f60`). The
driver `scripts/regenerate_male_navigation_v4.py --stage S0b` executes it as a subprocess. S0b
has no overlay, no port and no pin document (`source_guards` is empty for this stage).

- **Previous record:** the driver takes `--previous-pins <S0a pin record>` and checks that the
  record's protocol, stage, producing commit and cumulative chain are consistent. The producer
  itself reads nothing from S0a. Its output must not overlap any chain output root, and it does
  not: S0a output is `male-v4-runs/S0a/collection`.
- **Seeds:** fixed in the producer, with no argument. `CASES` holds `recovery-north-2100` (seed
  2100, start pose `[-.95, .12, 0]`) and `recovery-south-2101` (seed 2101, start pose
  `[-.95, -.12, 0]`), run in that order. Protocol `M7-REC-COVER-1` v3 (`teacher-recovery-development-v3`):
  `source_max_ticks` 120, `maximum_numeric_ticks` 240, two owners, two initial snapshots.
- **Repo:** `--repo` is the producing worktree. Its default is the same path; it is given
  explicitly so the plan binds it.
- **Assets:** `--assets /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn`. Verified on
  9 November 2026 with c382c86's own `palimpsest.assets.verify_assets` against c382c86's
  `model_manifests/flynn-full-vision.json`, which is byte-identical to cc1cea9's (`e319bb18…97e5`).
  Both pinned files are `verified`: `drosophila adult connectome.7z` (`49d19491…e9f1`) and
  `connectome_rnn_dagger_princeton_full_vision.pt` (`fde5327c…d8d6`). The worktree's own
  `data/assets/flynn` lacks both files (`missing`), so it is not used. The producer re-verifies
  the assets before and after (`assets_before`/`assets_after`).
- **Output:** `--output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b/collection`.
  The producer creates it exclusively and refuses overlap with the assets.
- **Producer controls (unchanged at c382c86):** a 180 s owner child, a 420 s inner gate, its own
  0.25 s PID/start sampler and cleanup, a 1 GiB output cap and a 1 GiB free-space floor. It
  takes the per-user `StorageBudget.lock()` writer lock for the whole run, and children use
  `OMP_NUM_THREADS=2`. The driver also launches the producer with `OMP_NUM_THREADS=2`, the
  stage-P-declared thread environment for S0b.

## Plan-only result (no producer executed)

```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B \
  /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/regenerate_male_navigation_v4.py \
  --stage S0b --worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/c382c86 \
  --previous-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/pin-record.json --plan-only -- \
  --repo /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/c382c86 \
  --assets /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn \
  --output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b/collection
```

Status `admissible`, exit 0. The saved output is [`plan-only.json`](plan-only.json), sha256
`1ed0dfdc71df98242c31930e20c6abe7cf371c45c059eebf47eb42b67b2e3ef3`. It records a detached,
clean worktree at c382c86, producer `17d94832…`, `previous_record_sha256` equal to the S0a pin
record (`d8e511b8…3901`), every argument and the exact `would_run` command. Plan-only never
opens a data input or executes a producer.

## Budget and unit

The protocol's Amendment 1 cost table row for S0b gives expected 15.565 s (coverage v3 outer);
`RuntimeMaxSec` 480 (`outer_timeout_seconds`); `TimeoutStopSec` 5; CPUQuota k = **2** (owner
decision 7; the producer runs two-thread children). The worst case is k × (480 + 5) =
**970 CPU-s**.

These agree. `run_research_stage.py` refuses unless `--worst-case-cpu` ≥ `cpu_quota_k` ×
(`RuntimeMaxSec` + `STOP_TIMEOUT` 5) = 2 × 485 = 970, and sets `CPUQuota=200%`. The protocol row
records `cpu_quota_k` 2, `runtime_max_sec_kill_target` 480 and `worst_case_cpu` 970. The original
table's 960 (k × kill) is superseded by Amendment 1's stop-time rule.

The navigation lane stood at 184.484 of 14,400 CPU-s before S0b (v3 prior 1.832 + P 85.274 +
S0a 97.378), in the global ledger `~/.local/state/palimpsest/research-ledger.jsonl`.
184.484 + 970 ≤ 14,400, so S0b is admissible. The charge is the census CPU, or the full 970
without a complete receipt.

## GO record

Write it at `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0b/go-S0b.json`.
Both `run_research_stage.load_go` and the driver's `check_go` read it:

```json
{"decision": "GO", "lane": "navigation", "stage": "S0b",
 "protocol_sha256": "cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477",
 "plan_sha256": "1ed0dfdc71df98242c31930e20c6abe7cf371c45c059eebf47eb42b67b2e3ef3",
 "previous_pin_record": "/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/pin-record.json",
 "previous_pin_record_sha256": "d8e511b8d8095c8d781a0ecfb2b031571c4f6fd72d0367b88520643d0f653901",
 "manifest_sha256": "<sha256 of this file>",
 "worktree": "/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/c382c86",
 "worktree_head": "c382c86781a7a5d6651af721119789729cc890ae",
 "current_tree_head": "<authority-paper-rewrite HEAD>",
 "cpu_quota_k": 2,
 "scientific_attempt": true,
 "granted_by": "<owner>", "granted_at": "<date>"}
```

## Pre-launch checks (all must hold; any failure means no launch, and nothing is charged)

1. **Current tree:** `CUR=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite`
   is at the research head carrying this manifest. Its protocol file hashes to `cd4eb130…d477`,
   and `git status --porcelain --untracked-files=no` is empty in `CUR`.
2. **Plan:** the plan-only command above, re-run, prints output whose sha256 is still
   `1ed0dfdc…3ef3`. That confirms worktree HEAD, detached, clean tracked files, no untracked
   `src`/`scripts`, producer bytes, the S0a record sha and argument shapes.
3. **Previous record:** `sha256sum male-v4-runs/S0a/pin-record.json` is `d8e511b8…3901`.
4. **Assets:** the asset check above still reports `ok: true` with the same two shas. Record the
   sha256 of both files and of `graph-49d19491…/palimpsest-prepared.json` before launch, for the
   unchanged-assets check after.
5. **Writer lock free:** no palimpsest lab, producer or research stage is running in any lane, and
   nothing holds `~/.cache/palimpsest/writer.lock` (`fuser` empty). The producer takes that
   per-user non-blocking lock; contention would fail it at startup and end v4.
6. **Directories:** create `palimpsest-authored-test-evidence/male-v4-s0b/` (GO record) before
   launch. `male-v4-s0b/receipt` must not exist. `male-v4-runs/S0b/` must be absent or empty, and
   `collection` and `pin-record.json` must not exist. (`male-v4-runs` is the v4 output root chosen
   for these runs, not a protocol reservation.)
7. **Disk:** free space on `/home` ≥ 1 GiB floor + 1 GiB producer output cap.
8. **Ledger:** no `navigation/S0b` row. No other navigation-lane unit is running.
9. **Upstream:** `upstream/fly-gym` in the worktree is initialised at `8d96459` (137 entries, 123
   regular files). The producer's `upstream_contract` refuses otherwise.
10. **Graphics stack (EGL identity):** `pacman -Q mesa libglvnd` reports `mesa 1:26.2.5-1` and
    `libglvnd 1.7.0-3`, as recorded for P and S0a on this host. Re-check after S0b; report any
    change. The stage P S2 EGL record (`docs/reports/male-v4-stage-p/probe-report.json.gz`) is
    the context reference.

## Launch (charged; one attempt)

<!-- s0b-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage S0b --cpu-quota-k 2 --runtime-max-sec 480 --worst-case-cpu 970 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0b/go-S0b.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0b/receipt \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/regenerate_male_navigation_v4.py \
  --stage S0b --worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/c382c86 \
  --previous-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/pin-record.json \
  --go /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0b/go-S0b.json \
  --pin-record-out /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b/pin-record.json \
  -- \
  --repo /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/c382c86 \
  --assets /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn \
  --output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b/collection
```

The driver is run with `-B` but not `-I`, because it imports its sibling probe module. It
launches the producer with the locked interpreter and an explicit environment: `PATH`, `HOME`,
`LANG`, `MUJOCO_GL=egl`, `CUDA_VISIBLE_DEVICES=`, `OMP_NUM_THREADS=2` and
`PYTHONPATH=<worktree>/src:<worktree>/scripts`.

**Throttling risk (stated, not blocking).** The 15.565 s historical figure is unconstrained
outer wall time; S0b CPU was never measured. Under CPUQuota=200%, each owner child runs with
`OMP_NUM_THREADS=2`, and the producer's sampler and supervisors poll. Headroom is about 31x
against the 480 s kill and about 27x against the 420 s inner gate. Each owner has a 180 s child
deadline, with at most 120 ticks per source. Any producer timeout or RuntimeMaxSec kill is an
operational failure that ends v4. The producer's thread environment is left exactly as at c382c86.

## Expected outputs

- `male-v4-runs/S0b/collection/`:
  - `report.json` with `status: passed`, `protocol_status: completed`, `owners_completed: 2`,
    `snapshot_files: 2` and `numeric_ticks` ≤ 240;
  - both cases `completed-recording` with `coverage.passed: true`;
  - `inner_supervision` completed with returncode 0;
  - `cleanup` with empty `forced_signals`, `survivors` and `sample_errors`, and `sampler_stopped: true`;
  - `assets_before == assets_after` (ok), `runtime_source == final_source` and
    `harness_sha256 == final_harness`;
  - per case, `recovery-*-210x/result.json` (`recorded_ticks` equals its rows) and a run directory
    with a recording and initial snapshot.
- **Pin record** `male-v4-runs/S0b/pin-record.json` (fsynced, exclusive). It holds schema
  `m7-navigation-v4-pin-record-1`, stage S0b, producing commit c382c86, `go_sha256`,
  `previous_record_sha256 = d8e511b8…3901`, the cumulative chain `{S0a, S0b}`, sha256 and bytes of
  every output file, and `counts` from the case results:
  `{"recovery-north-2100": n1, "recovery-south-2101": n2}`. The driver refuses a result whose
  `recorded_ticks` differs from its rows. The S0c recovery-learning count fields trace to these
  counts.
- `male-v4-s0b/receipt/`: `receipt.json` (cgroup census, drained, survivors), `stdout.log`
  (the producer's final status line and the driver's `completed` JSON) and `stderr.log`.
- Ledger: one `reserved` row (970) and one `charged` row for `navigation/S0b`.

## Post-run gate (before any S0c GO)

Read `male-v4-runs/S0b/collection/report.json` and the pin record. Require all of:

- `status: passed` and `protocol_status: completed`;
- cases in order `recovery-north-2100` (seed 2100), then `recovery-south-2101` (seed 2101), both
  `completed-recording` with coverage passed and no other case;
- per-source ticks `n1`, `n2` each in 1..120 (`source_max_ticks`), with `n1 + n2 = numeric_ticks` ≤ 240;
- pin-record `counts` equal to `{recovery-north-2100: n1, recovery-south-2101: n2}`, read from
  each case's `result.json` rows and `recorded_ticks`;
- clean producer cleanup, unchanged assets (the producer's comparison and the pre-launch shas)
  and an unchanged graphics stack.

Record the pin-record sha256 in the S0b RESULT and in the S0c GO.

## On failure

Per protocol `execution_stops`, any S0 producer refusal, guard mismatch, pin mismatch,
RuntimeMaxSec kill, storage breach or nonzero exit **ends v4**. This includes:

- a driver `refused`, `producer-failed` or `record-refused` status;
- a `report.json` with `failed-functional` or `failed-infrastructure` (the producer exits 1);
- a missing pin record;
- a unit that is not drained.

Later stages stay `not_started`. There is no retry, substitution, filtering, recollection or
budget change. The first fault and all partial outputs are retained as they are, the charge
stands (census, or 970 CPU-s without a complete receipt), and any further work needs a new
protocol version.

## Review amendments (independent AI review, 2026-11-09)

- **A. GO binding (pre-launch, by hand):** `load_go`/`check_go` do not compare these fields, so
  before launch verify: `manifest_sha256` = sha256 of this committed file; `plan_sha256` =
  `1ed0dfdc…3ef3`; `previous_pin_record_sha256` = sha256 of the `--previous-pins` file
  (`d8e511b8…3901`); `cpu_quota_k` = 2 (= `--cpu-quota-k 2`); `worktree_head` = c382c86…; no
  `<…>` placeholder remains anywhere in the GO record.
- **B. Post-run gate additions:** pin record `chain` keys exactly `[S0a, S0b]` with `chain.S0a`
  equal to the S0a record's own entry; `previous_record_sha256` = `d8e511b8…`; `go_sha256` =
  sha256 of the GO file; `outputs` contains `report.json` and both `<case>/result.json`, each
  result sha equal to `report.cases[*].result_sha256`; each case has exactly one uuid-hex run
  directory; launcher receipt `complete`, `drained`, returncode 0, no survivors; ledger has a
  `charged` S0b row; the driver printed `status: completed`.
- **C. Wording:** RuntimeMaxSec 480 covers the driver as well as the producer; about 60 s beyond
  the producer's 420 s gate remains for outer startup, cleanup and output hashing. A kill in that
  window is an operational failure that ends v4.
