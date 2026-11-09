# MaleCNS v4 stage P: execution manifest (prospective)

> **Status:** prepared, **not executed**. Stage P is a charged research stage (navigation lane,
> worst case 125 CPU-s). It needs an explicit owner GO naming this manifest's digest and the
> P-time locator digest below. One attempt: a refusal or kill ends v4 at P and is charged.
> Nothing here runs a producer `main`, opens a data input, trains or simulates.

Protocol: `docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json`, sha256
`cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477`. Probe:
`scripts/probe_male_navigation_v4_imports.py`. Interpreter:
`/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python` (Python 3.11.15, NumPy 2.2.5,
Torch 2.9.0+cu128 CPU, MuJoCo 3.3.6).

## Port locator at P time (decision)

The `*-port` entry points read `PALIMPSEST_M7_V4_PINS` at import. No S0 pin record exists at
P, so the driver's run-time locator (`<pin record>.port-pins.json`) cannot be used. Reading the
port code (`docs/plans/m7-navigation-v4-pins/ports.json` trees T-c, T-d, T-e, T-f, T-h):

- Every H1 hunk evaluated at import reads only the locator file and keeps string values:
  `['documents'][<copy>]['path'|'sha256']` and, in T-d `train_male_recovery.py:19`,
  `['data_manifest']['sha256']`. None opens the named document at import.
- The single import-time document open is `collect_male_navigation_v2.py:50`
  (`CONTACTS = plan()['contacts']`, in T-e and carried in T-f). `plan()` checks only the
  contact-v2 copy's digest against the locator sha and its `contact_profile` identity
  (`1593421a…`). It never reads a `PENDING-` field. The tracked v4 copy passes both checks.
- No `main` is called, so `source_pins`, `_gate`, `resolve` and every other reader of
  `PENDING-` values stay unexecuted.

**PENDING placeholders are therefore acceptable at P.** The P-time locator names the five
tracked v4 copies (absolute paths, current sha256, with their `PENDING-` pointers listed under
`pending`) and sets the S0c `data_manifest` value to the explicit placeholder
`{"path": "PENDING-S0c", "sha256": "PENDING-S0c"}`. It is written by
`probe_male_navigation_v4_imports.py --write-port-pins` (`write_port_pins`), which refuses a
relative, existing or in-root path. The locator file and the copies sit outside every probed
port worktree, so the probe's audit hook allows those opens unless a `--forbid` root covers them.

What P proves for the ports: their full import closure (including function-level imports)
resolves in the locked interpreter against v4 documents, with no data open. It does **not**
exercise pin values; those are checked by each S0 stage against its own pin records.

## Roots

| Symbol | Path |
| --- | --- |
| `T` | `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees` |
| `CUR` | `/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite` (controllers, S1, S2, probe, pins) |
| `E` | `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p` (fresh; outside every root) |
| ledger | `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-ledger/ledger.jsonl` |

Entry points (every `ENTRYPOINTS` key once). The probe checks HEAD for commit and port entries.
For the remaining entries the operator checks that `CUR` is at the merge commit that carries this
manifest.

| Key | Module | Worktree | Expected HEAD |
| --- | --- | --- | --- |
| S0a | collect_male_teachers | `T/cc1cea9` | cc1cea93d4c3333a0ee2a091dd34fff0b2986887 |
| S0b | collect_male_recovery | `T/c382c86` | c382c86781a7a5d6651af721119789729cc890ae |
| S0c | prepare_male_recovery_data | `T/7d5fc1f` | 7d5fc1f4ecd1bbd6a5a139bde3585fb2255ce2fe |
| S0d | train_male_recovery | `T/19d275d` | 19d275d7ba3d8c7da642a4b41d3a6a8f2d5c720f |
| S0e | collect_male_navigation_v2 | `T/736e0cf` | 736e0cf0a71f6d700bd67836ee5f83911ceff90a |
| S0f | prepare_male_navigation_v2 | `T/4ecb354` | 4ecb354efa4223abdbe3d09be118fe5402fec1a1 |
| S0f-historical | prepare_male_recovery_data | `T/217cbee` | 217cbee8399dcb25045a079af012beecbbdae29e |
| S0c-port | prepare_male_recovery_data | `T/port-t-c` | c06b4976f30b86455dc9ea3406bad6fab42371e1 |
| S0d-port | train_male_recovery | `T/port-t-d` | 02e861f8be9877dd183a659ed1b70d66a9141052 |
| S0e-port | collect_male_navigation_v2 | `T/port-t-e` | 703acc503c43b13d9f2d5f8ddc05b29f72fc0247 |
| S0f-port | prepare_male_navigation_v2 | `T/port-t-f` | 88c1a0f6f53274fe663f4cdad3be5ae2743af558 |
| S0f-historical-port | prepare_male_recovery_data | `T/port-t-h` | 0789b2ed54117c01c40ab5818148cc0515eb4fb5 |
| S0d-controller | run_male_navigation_v4_s0d | `CUR` | merge commit carrying this manifest |
| S0e-launch / S0e-D / S0e-A / S0e-I | run_male_navigation_v4_s0e | `CUR` | same |
| S0e-A-worker | audit_male_navigation_v4_s0e_raw | `CUR` | same |
| controls | male_navigation_v4_controls | `CUR` | same |
| S1 | train_male_navigation_v4 | `CUR` | same |
| S2 | evaluate_male_navigation_v4 | `CUR` | same |

`--forbid` (never opened): `<root>/runs` and `<root>/data/assets` for every worktree root.
Inside a worktree the hook already blocks anything outside `src`, `scripts`, `docs`, `upstream`,
`data/manifests`, `pyproject.toml` and `uv.lock`, so these entries make that explicit. The list
also forbids the main checkout's `runs` and `data/assets`, the lost `brain` checkout, and the
reserved v4 data root `palimpsest-authored-test-evidence/male-v4-runs`. Held-out scenes
3170–3177 have never been generated, so no held-out root exists to open.

## Steps

1. **Merge and pin.** Merge `impl/male-v4-p` so `CUR` carries `--write-port-pins`. Record `CUR`'s
   HEAD and this file's sha256 in the GO.
2. **Ledger.** Use the single global research ledger `~/.local/state/palimpsest/research-ledger.jsonl`
   (the same ledger as puck, so the 24 CPU-hour aggregate cap is enforced across lanes). Before P,
   append exactly one seed row for the prior v3 charge (owner decision 3):
   `{"cpu_seconds": 1.832, "event": "charged", "lane": "navigation", "stage": "v3-prior", "basis": "v3 attempts 1 (0.431) and 2 (1.401), docs/reports/m7-navigation-v3-matched-budget-attempt-{1,2}.md"}`.
   `run_research_stage.py` then admits P against 14,400 − 1.832 (the launcher now creates a
   missing ledger directory before writing).
3. **P-time locator** (uncharged; opens no data; writes one file):

   ```sh
   mkdir -p /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p
   /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -I -B \
     /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/probe_male_navigation_v4_imports.py \
     --python /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python \
     --write-port-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p/port-pins.json \
     --stage S0c-port=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-c \
     --stage S0d-port=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d \
     --stage S0e-port=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-e \
     --stage S0f-port=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-f \
     --stage S0f-historical-port=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-h \
     --stage S1=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite
   ```

   With the copies unchanged, the expected output is sha256
   `1843879539a610955ad608038fd06975f5a953becfd2645a6ce27e1d93c9e4c4` (4,527 bytes; computed from
   `p_time_locator` over `CUR`'s copies). It holds `PENDING-` counts contact-v2 9, data-v2 34,
   study 4, recovery-learning 6 and recovery index 15. Put this digest in the GO record; any
   other digest refuses the GO.
4. **GO record** at `E/go-P.json`:
   `{"decision": "GO", "lane": "navigation", "stage": "P", "protocol_sha256": "cd4eb130…dcd477",
   "granted_by": …, "granted_at": …, "manifest_sha256": …, "port_pins_sha256": "1843879…c9e4c4",
   "current_tree_head": …}`.
5. **Stage P** (charged, one attempt). `E/receipt` must not exist:

<!-- stage-p-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage P --cpu-quota-k 1 --runtime-max-sec 120 --worst-case-cpu 125 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p/go-P.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p/receipt \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -I -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/probe_male_navigation_v4_imports.py \
  --python /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python --egl --egl-stage S2 --timeout 30 \
  --port-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p/port-pins.json \
  --stage S0a=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/cc1cea9 \
  --stage S0b=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/c382c86 \
  --stage S0c=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/7d5fc1f \
  --stage S0d=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/19d275d \
  --stage S0e=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/736e0cf \
  --stage S0f=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/4ecb354 \
  --stage S0f-historical=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/217cbee \
  --stage S0c-port=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-c \
  --stage S0d-port=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-d \
  --stage S0e-port=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-e \
  --stage S0f-port=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-f \
  --stage S0f-historical-port=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-h \
  --stage S0d-controller=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --stage S0e-launch=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --stage S0e-D=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --stage S0e-A=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --stage S0e-A-worker=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --stage S0e-I=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --stage controls=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
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
  --forbid /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/data/assets
```

6. **Outputs.** `E/receipt/stdout.log` holds the probe's single JSON report (`status`,
   per-entry `modules`, versions, thread environment, CUDA state, EGL identity and any blocked
   opens). `E/receipt/receipt.json` is the cgroup census. The ledger's `charged` row is the
   census CPU, or the full 125 CPU-s without a complete receipt. P passes only when the report
   status is `passed` for all 21 entries and the unit exits 0.

## Budget and risks

- Kill target 120 s plus `TimeoutStopSec=5` at k=1 gives a worst case of 125 CPU-s (the
  amendment's stage-cost row). Admission uses the ledger; there is no retry.
- One invocation runs 21 sequential `python -I` children. Several import Torch and MuJoCo, and
  `--egl --egl-stage S2` creates the protocol's single offscreen context, in the S2 (renderer) child only;
  measured cost of one context is about 3.2 CPU-s and of a torch+mujoco import about 1.3 CPU-s, so
  21 children are expected to need roughly 30 CPU-s. (Before this change `--egl` created one context per child.) The protocol's ≤30 s expectation is an
  estimate. Real entries were **not** probed for timing (that would be stage P). `--timeout 30`
  bounds any single child. If the sum exceeds 120 s, the unit is killed: an operational failure
  that ends v4 at P. Reviewers may instead choose to split P into per-entry units, which needs a
  new budget row.
- A refusal (unresolved import, blocked open, local module outside its worktree, initialized
  CUDA, wrong HEAD) is a P failure. There is no environment repair inside this GO.

## Dry validation performed (not stage P)

`tests/test_male_navigation_v4_probe.py` checks the locator answer statically against the port
branches and probes **one ad-hoc synthetic entry** that mimics an H1 hunk against a written P-time
locator. That entry passes, and it is refused when the pins directory is forbidden. A test also
parses the command above and checks that every `ENTRYPOINTS` key appears exactly once, the unit
parameters, `--egl`, `--port-pins`, the forbid list and that every output path sits outside all
roots. No real entry point was probed.

## Review amendments (independent AI review, 2026-11-09)

- **Stage classification:** `scientific_attempt: false`. Protocol `on_failure`, verbatim:
  "Report blocked. Environment repair and any re-probe require a new manifest and owner GO;
  every probe is charged." A P failure or a RuntimeMaxSec kill ends MaleCNS v4 at P.
- **Forbid scope:** the audit hook sees Python-level `open` calls only; C-level reads inside
  MuJoCo or Torch are not audited. The forbid list now also covers every other worktree's `runs`
  and `data/assets`, `palimpsest/worktrees`, `palimpsest/.claude/worktrees` and the other
  evidence-store directories (puck evidence, fixtures, reproductions, CI simulations).
- **Pass conditions (step 6):** every entry `passed`; `verify_endurance` and `httpx` 0.28.1 present
  in the S0b–S0f and port reports; exactly one non-null `runtime.egl`, from S2. The v2-trainer head
  of the must-cover chain is not a v4 entry point; it is covered only by
  `test_real_v3_trainer_chain_resolves_in_locked_environment`.
- **Pre-launch operator checks (by hand; `load_go` checks only lane, stage and non-empty fields):**
  sha256 of the protocol, this manifest and `port-pins.json` equal the GO; `CUR` HEAD equals
  `current_tree_head`; `git status --porcelain` in `CUR` is empty.
- **Hardening applied:** probe children run `-I -B` (no `__pycache__` written into the trees);
  `--egl-stage` is validated against the declared entry points; each entry result is also written
  to stderr as it completes, so a kill keeps the completed diagnostics.
