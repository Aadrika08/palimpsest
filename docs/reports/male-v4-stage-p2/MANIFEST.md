# MaleCNS v4 stage P2: import-closure re-probe for the new entry points, execution manifest (prospective)

> **Status:** prepared, **not executed**. P2 is a charged research stage (navigation lane, stage
> name `P2`, worst case 125 CPU-s) and `scientific_attempt: false`. It needs an explicit owner GO
> naming this manifest's sha256 and the P2 locator sha256 below. One attempt: a refusal or kill is
> charged and blocks S1. Nothing here runs a producer `main`, the S0z controller, the S1 child or
> any data input. It follows the first stage P manifest
> (`docs/reports/male-v4-stage-p/MANIFEST.md`) and carries its review amendments.

Protocol: `docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json`, sha256
`cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477`. Probe:
`scripts/probe_male_navigation_v4_imports.py`. Interpreter: `/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python`.

## Why P2, and what it covers

Stage P (PASSED, 21/21, 85.274 CPU-s) predates three files that S1 and S0z depend on. The S0z
review ruled that stage P must be re-run with them before S1:

| Key | Module | Worktree | Notes |
| --- | --- | --- | --- |
| `S0z-controller` | `run_male_navigation_v4_s0z` | `CUR` | imports `male_navigation_v4_controls`; `palimpsest.male_matched_budget_v4` and `run_male_navigation_v4_s0e` are function-level imports the probe resolves |
| `S0z-audit` | `audit_male_navigation_v4_s0z` | `CUR` | stdlib; NumPy function-level |
| `S1-data-child` | `derive_male_navigation_v4_s1_data` | `CUR` | the child's own file: stdlib, NumPy and T-f modules imported **by name** at run time |
| `S1-data-child-closure` | `prepare_male_navigation_v2` | `T/port-t-f` (port commit `88c1a0f6f53274fe663f4cdad3be5ae2743af558`) | the child runs under `python -I -B` with **only the T-f port on `sys.path`** and imports this module, so its closure is probed in the T-f tree with `OMP_NUM_THREADS=1`; it uses the same locator as the `S0f-port` entry |
| `S1` (re-probe) | `train_male_navigation_v4` | `CUR` | changed since P (`d537a96`, the child launch and `SOURCES`) |
| `S2` (re-probe) | `evaluate_male_navigation_v4` | `CUR` | unchanged; kept as the single EGL-context carrier, as in P |

`probe_male_navigation_v4_imports.py` declares these as `P2_ENTRIES` (+ `P2_REPROBE`), and the first
P manifest test now compares against the 21 pre-P2 keys, so P's recorded evidence stays valid.

## Budget: honest estimate and the decision to split

P measured **85.274 CPU-s (wall 86.4 s) for 21 entries**, about 4.1 CPU-s each including the one EGL
context (~3.2 CPU-s) and several Torch/MuJoCo imports (~1.3 CPU-s each). A full re-run of all 25
entries (21 + the 4 new keys) would extrapolate to about **103 CPU-s and wall**. That is under the
125 CPU-s worst case but only **15% under the 120 s `RuntimeMaxSec`**, and nothing was measured for
the new entries (the S0z controller's import of the S0e controller and the T-f closure are the
unmeasured parts). A kill at 120 s would be charged, block S1 and need a further GO.

**Decision: split.** P2 probes only the six entries above, which are the only ones changed or
unprobed since P: expected about 25 CPU-s (6 × ~4.1) and well under 60 s wall, a 2x or more margin
against the 120 s kill. The other 19 entries are covered by P's recorded evidence (their trees and
bytes are unchanged: producing commits and port commits are fixed by `ports.json`; the controllers
`S0d`/`S0e*`, `controls` and the S0e audit worker are re-verified only if their bytes changed since P;
the operator checks that in pre-launch check 3). Cost-table slack justifies it: the protocol's
worst case through S2 is 6,905 CPU-s still ahead of S1 against 14,398.168 total
(measured v4 charge 603.404 excluding the v3 prior), so the 125 CPU-s worst case for P2 fits many times
over, and splitting costs no budget beyond one extra reservation. `RuntimeMaxSec` 120 and
`TimeoutStopSec` 5 at k = 1 give the **125 CPU-s worst case** (the amendment's P row, reused).

## Roots

| Symbol | Path |
| --- | --- |
| `T` | `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees` |
| `CUR` | `/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite` |
| `E2` | `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p2` (fresh; outside every root) |
| ledger | `/home/utkarsh/.local/state/palimpsest/research-ledger.jsonl` (the single global ledger) |

## Port locator at P2 time

Unchanged decision from P: port entry points read `PALIMPSEST_M7_V4_PINS` at import, which opens only
the locator and the one import-time document (`plan()` in `collect_male_navigation_v2.py`, carried in
T-f). Since P, every v4 copy has been filled (no `PENDING-` remains); the P2 locator names the five
copies by absolute path and current sha256, with `data_manifest` still the explicit
`PENDING-S0c` placeholder (never opened). It is written by the probe's `--write-port-pins` to a fresh
path outside every probed root. Its expected sha256 (computed over `CUR`'s copies) is
**`278219f4b364ae53d4942c2020cf69dd100cad376c5a320b0e4a1c88633dbb69`** (1,793 bytes, no pending
pointers); any other digest refuses the GO.

## Forbid list

Every forbid entry of the first P command is kept (other worktrees' `runs` and `data/assets`, the lost
`brain` checkout, all other evidence-store directories). New roots are added: `male-v4-data` (S0f and
S0z outputs), `male-v4-trees/port-t-d/runs/S0d`, `male-v4-trees/port-t-e/runs`, and the first P output
directory `male-v4-stage-p`. `male-v4-runs` and every tree's `runs` and `data/assets` were already
listed. As in P, the audit hook sees Python-level `open` calls only.

## Steps

1. **Merge and pin.** `CUR` carries this branch (the P2 entry points and this manifest). Record `CUR`'s
   HEAD and this file's sha256 in the GO.
2. **Ledger.** The same global ledger. There must be no `navigation/P2` row (the launcher refuses a
   repeated `(lane, stage)`; the earlier `P` row is unrelated).
3. **P2 locator** (uncharged; opens no data; writes one file):

   ```sh
   mkdir -p /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p2
   /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -I -B \
     /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/probe_male_navigation_v4_imports.py \
     --python /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python \
     --write-port-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p2/port-pins.json \
     --stage S1-data-child-closure=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-f \
     --stage S1=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite
   ```

4. **GO record** at `E2/go-P2.json`:

   ```json
   {"decision": "GO", "lane": "navigation", "stage": "P2",
    "protocol_sha256": "cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477",
    "manifest_sha256": "<sha256 of this file>",
    "port_pins_sha256": "278219f4b364ae53d4942c2020cf69dd100cad376c5a320b0e4a1c88633dbb69",
    "declared_fields_sha256": "<sha256 of declared-fields.json in CUR>",
    "t_f_head": "88c1a0f6f53274fe663f4cdad3be5ae2743af558",
    "current_tree_head": "<CUR HEAD at launch>",
    "entries": ["S0z-controller", "S0z-audit", "S1-data-child", "S1-data-child-closure", "S1", "S2"],
    "cpu_quota_k": 1, "scientific_attempt": false,
    "granted_by": "<owner>", "granted_at": "<date>"}
   ```

5. **Stage P2** (charged, one attempt). `E2/receipt` must not exist:

<!-- stage-p2-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage P2 --cpu-quota-k 1 --runtime-max-sec 120 --worst-case-cpu 125 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p2/go-P2.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p2/receipt \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -I -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/probe_male_navigation_v4_imports.py \
  --python /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python --egl --egl-stage S2 --timeout 30 \
  --port-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p2/port-pins.json \
  --stage S0z-controller=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --stage S0z-audit=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --stage S1-data-child=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --stage S1-data-child-closure=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-f \
  --stage S1=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --stage S2=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/data/assets \
  --forbid /home/utkarsh/Work/shraddha/brain \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-ci-repair/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-ci-repair/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-study-final/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-study-final/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-study-recovery/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-study-recovery/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/paper-systems/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/paper-systems/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/ci-isolated-first-20261106/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/worktrees \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.claude/worktrees \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/puck-v4-go \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/puck-v4-s1-20261108 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/puck-v4-s1-20261108b \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/puck-v4-s1-20261108c \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/puck-v4-s1-20261108d \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/puck-v4-s1-20261108e \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/puck-v4-s1-20261108f \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/puck-v4-s1-20261108g \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/puck-v4-s1-attempt-2-ledger \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/puck-v4-s1-attempt-ledger \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/custody-extraction-20261107.075cy2 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/custody-extraction-20261107.LAsiKE \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/custody-extraction-20261107.T7N2nJ \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-custody-extraction-20261107.07zE7v \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-custody-extraction-20261107.S7OZx8 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-custody-extraction-20261107.SJb3Y5 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-custody-extraction-20261107.X2cmS2 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-fix1-covering-01 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-fix1-covering-02 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-fix1-green-01 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-fix1-green-02 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-fix1-green-03 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-fix1-red-01 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-green-20261106-03 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-green-20261106-04 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-green-20261106-05 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-green-20261106-06 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-integration-20261106-10 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-paper-tests.2eXSgv \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-paper-tests.KSbbb5 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-paper-tests.XnuA8j \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-paper-tests.b7am0n \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-paper-tests.jhIGsU \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-paper-tests.uylAaa \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-scratch-20261106-10 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-scratch-20261106-11 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/fresh-reproduction-v2-20261107-94c5488 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/fresh-reproduction-v2-20261107-94c5488.log \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/fresh-reproduction-v2-20261107-94c5488.time \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/ci-sim-bt \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/ci-sim-bt2-d5b04c7 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/ci-sim-clone \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/ci-sim-clone2 \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/paper-verify-20261107.log \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/paper-verify-rq5.log \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/paper-verify-rq5b.log \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/paper-verify-rq5c.log \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/paper-verify-v2.log \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/canonical-94c5488-20261107.log \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/canonical-ab1e927-20261107.log \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/cc1cea9/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/cc1cea9/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/c382c86/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/c382c86/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/7d5fc1f/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/7d5fc1f/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/19d275d/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/19d275d/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/736e0cf/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/736e0cf/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/4ecb354/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/4ecb354/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/217cbee/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/217cbee/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-c/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-c/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-e/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-e/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-f/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-f/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-h/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-h/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/runs \
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/data/assets \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d/runs/S0d \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p
```

## Pre-launch checks (by hand; `load_go` checks only lane, stage and non-empty fields)

1. The protocol, this manifest, the P2 locator (step 3) and `declared-fields.json` hash to the GO values;
   `CUR` HEAD equals `current_tree_head`; `git status --porcelain` in `CUR` is empty.
2. `port-t-f` is detached at `88c1a0f6…` with clean tracked files (the probe also checks HEAD).
3. Bytes of the 19 entries P covered are unchanged where they could matter: `git diff <P-time CUR head>..HEAD
   -- scripts/run_male_navigation_v4_s0d.py scripts/run_male_navigation_v4_s0e.py
   scripts/male_navigation_v4_controls.py scripts/audit_male_navigation_v4_s0e_raw.py` is reviewed; a
   change is either accepted with a one-line reason or the entry is added to the P2 command (new manifest).
4. Writer lock free and no other navigation-lane unit running; `E2` does not exist beyond what step 3 creates;
   `E2/receipt` and the ledger `P2` row do not exist.
5. Graphics stack: `pacman -Q mesa libglvnd` reports `mesa 1:26.2.5-1` and `libglvnd 1.7.0-3`.

## Post-run gate

- **Unit:** receipt `complete`, `drained`, returncode 0, no survivors; ledger `charged` P2 row; wall well under 120 s.
- **Report (`receipt/stdout.log`, a single JSON):** `status: passed` and exactly 6 probes, each `passed`
  with no unresolved import, no blocked open, `forbidden` none and CUDA uninitialized.
- **Entry facts:** `S1-data-child-closure` resolved from `port-t-f` at `88c1a0f6…` with `httpx` 0.28.1 and
  `verify_endurance` present; `S0z-controller` resolves `palimpsest.male_matched_budget_v4` and
  `run_male_navigation_v4_s0e`; the CUR entries import no module from outside `CUR`; exactly one non-null
  `runtime.egl`, from `S2`; per-entry stderr lines exist for all six.
- **Cost:** charged CPU recorded; compare with the ~25 CPU-s estimate and with P's 85.274.

## On failure

`scientific_attempt: false`, as in P. Per the protocol, a probe failure reports blocked: environment
repair and any re-probe need a new manifest and owner GO, and every probe is charged. A P2 failure or
RuntimeMaxSec kill blocks S1 (S0 stages are already complete; S0z is passed and pinned).

## Dry validation performed (not stage P2)

`tests/test_male_navigation_v4_probe.py` checks the P2 entry declarations, probes the two small CUR entries
(`S0z-audit`, `S1-data-child`) with the real probe in a synthetic dry run, and verifies that the child's
source sets only the T-f port on its path. A binding test parses the command above against the declared
entry points, the unit parameters, the new roots and the output paths. No real data was opened and P2 was
not run.
