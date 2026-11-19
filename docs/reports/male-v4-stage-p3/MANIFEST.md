# MaleCNS v4 stage P3: import-closure probe for the Amendment 2 entry points, execution manifest (prospective)

> **Status:** prepared, **not executed**. P3 is a charged research stage (navigation lane, stage name
> `P3`, worst case 125 CPU-s) and `scientific_attempt: false`. It needs an explicit owner GO naming this
> manifest's sha256 and the P3 locator sha256 below. One attempt: a refusal or kill is charged and blocks
> S2. Nothing here reads S1 checkpoints, runs the evaluator, an Engine owner or any data input.

Protocol: `docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json`, sha256
`cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477`. Amendment 2 file sha256
`c4cd3a506b0b468b0d6d4d359dff7ecbd3b3bf0c25c6fe9360207282249f8d6f` (unchanged; see the erratum below).
Probe: `scripts/probe_male_navigation_v4_imports.py` (`P3_ENTRIES`, `P3_REPROBE`). Interpreter:
`/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python`.

## What P3 covers

Amendment 2 gates S2 on an import-closure probe of the new code before any launch. P3 probes three entries,
all in `CUR`:

| Key | Module | Notes |
| --- | --- | --- |
| `S2-binding` | `palimpsest.male_navigation_research_v4` (`src/palimpsest/male_navigation_research_v4.py`) | class `Binding` (alias `NavigationBindingV4` in `engine.py`); module-level `from . import artifacts, male_model, male_policy`, Torch only inside functions |
| `S2-owner-worker` | `evaluate_male_navigation_v4` | the S2 owner worker is a mode of the evaluator module; import-only here |
| `S2` (re-probe) | `evaluate_male_navigation_v4` | the single EGL-context carrier, as in P and P2 |

All other entries are covered by P and P2 evidence. S1 has since run (173.589 CPU-s charged); its two source files are unchanged since P2 (pre-launch check 2).

## Budget

P2 charged 29.918 CPU-s for six entries (about 5 each, including one EGL context of about 3.2). The S2 entries pull in
Engine, replay, snapshots, Torch, MuJoCo and matplotlib, so three entries are expected at about 15 to 20 CPU-s and under
90 s wall (3 x the 30 s per-entry timeout) against `RuntimeMaxSec` 120 and `TimeoutStopSec` 5 at k = 1, giving the
**125 CPU-s worst case** (the amendment's P row). Navigation lane charged before P3: 808.743 CPU-s of 14,400.
S3's held-out threshold needs spend through S2 of at most 5,643.168 CPU-s: 808.743 + 125 (P3 worst case) + 4,435
(S2 worst case) = 5,368.743, under it.

## Roots

| Symbol | Path |
| --- | --- |
| `CUR` | `/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite` |
| `E3` | `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p3` (fresh; outside every root) |
| ledger | `/home/utkarsh/.local/state/palimpsest/research-ledger.jsonl` |

## Port locator

As in P2: port entry points read `PALIMPSEST_M7_V4_PINS` at import. The P3 locator is written by the probe's
`--write-port-pins` to `E3/port-pins.json` and must equal P2's, sha256
`278219f4b364ae53d4942c2020cf69dd100cad376c5a320b0e4a1c88633dbb69`; any other digest refuses the GO.

## Forbid list

P2's list plus the P2 output directory. `male-v4-data` stays forbidden, so S1 checkpoints and S0 data cannot be
opened by an import (the audit hook sees Python-level `open` calls only).

## Steps

1. **Pin.** Record `CUR` HEAD (after PR #192 merges) and this file's sha256 in the GO.
2. **Ledger.** No `navigation/P3` row may exist.
3. **P3 locator** (uncharged; opens no data; writes one file):

   ```sh
   mkdir -p /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p3
   /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -I -B \
     /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/probe_male_navigation_v4_imports.py \
     --python /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python \
     --write-port-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p3/port-pins.json \
     --stage S2=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite
   ```

4. **GO record** at `E3/go-P3.json`:

   ```json
   {"decision": "GO", "lane": "navigation", "stage": "P3",
    "protocol_sha256": "cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477",
    "amendment_2_sha256": "c4cd3a506b0b468b0d6d4d359dff7ecbd3b3bf0c25c6fe9360207282249f8d6f",
    "manifest_sha256": "<sha256 of this file>",
    "port_pins_sha256": "278219f4b364ae53d4942c2020cf69dd100cad376c5a320b0e4a1c88633dbb69",
    "current_tree_head": "<CUR HEAD at launch>",
    "a2_erratum_ack": "<id of the decisions-2026-11-08.md row acknowledging the A2 wording erratum>",
    "entries": ["S2-binding", "S2-owner-worker", "S2"],
    "cpu_quota_k": 1, "scientific_attempt": false,
    "granted_by": "<owner>", "granted_at": "<date>"}
   ```

5. **Stage P3** (charged, one attempt). `E3/receipt` must not exist:

<!-- stage-p3-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage P3 --cpu-quota-k 1 --runtime-max-sec 120 --worst-case-cpu 125 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p3/go-P3.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p3/receipt \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -I -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/probe_male_navigation_v4_imports.py \
  --python /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python --egl --egl-stage S2 --timeout 30 \
  --port-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p3/port-pins.json \
  --stage S2-binding=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
  --stage S2-owner-worker=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite \
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
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p \
  --forbid /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-stage-p2
```

## Pre-launch checks (by hand; `load_go` checks only lane, stage and non-empty fields)

1. Protocol, Amendment 2 file, this manifest and the locator (step 3) hash to the GO values; the erratum
   acknowledgement row named by `a2_erratum_ack` exists in `decisions-2026-11-08.md` (`load_go` does not enforce it); `CUR` HEAD equals
   `current_tree_head`; `git status --porcelain` in `CUR` is empty.
2. `git diff <P2-time CUR head>..HEAD -- scripts/train_male_navigation_v4.py scripts/derive_male_navigation_v4_s1_data.py`
   is empty or reviewed (S1 is not re-probed here).
3. Writer lock free; no other navigation-lane unit running; `E3` holds only the locator; no ledger `P3` row.
4. `pacman -Q mesa libglvnd` reports `mesa 1:26.2.5-1` and `libglvnd 1.7.0-3`.

## Post-run gate

- **Unit:** receipt `complete`, `drained`, returncode 0, no survivors; ledger `charged` P3 row; wall under 90 s.
- **Report (`receipt/stdout.log`, a single JSON):** `status: passed`, exactly 3 probes, each `passed`, with no
  unresolved import, no blocked open, `forbidden` none and CUDA uninitialized.
- **Entry facts (read by hand from the report):** the `modules` paths of each entry lie under `CUR` or the
  interpreter prefixes; exactly one non-null `runtime.egl`, from `S2`; CUDA not initialized. The probe imports
  function-level targets during its scan, so Torch presence in the report does not show import-time behaviour;
  by source review the binding's own module-level code does not import Torch.
- **Cost:** charged CPU recorded against the 15 to 20 CPU-s estimate.

## On failure

`scientific_attempt: false`. A probe failure reports blocked: repair and any re-probe need a new manifest and
owner GO, and every probe is charged. A P3 failure or RuntimeMaxSec kill blocks S2.

## Erratum to Amendment 2 wording (owner acknowledgement required; the A2 file is not edited)

Source review of the A2 implementation (independent AI review, not human acceptance) found wording
mismatches between the approved A2 text and the implementation. The A2 file sha stays `c4cd3a50...`.

1. The "index builder" in `planned_create`, the tests list and `stage_p3.covers` / `rule` ("all four") is not
   built: the binding reads S1 `report.json` and `publication.json` directly against hard-coded shas (A2's
   second option). P3 therefore covers three entries, not four.
2. "checkpoint `graph_sha256` and `ordered_ids_sha256` equal the S1 report values": the S1 report has neither
   field. They are re-derived from the pinned graph and enforced by `_load_checked_policy` (`docs/reports/male-v4-s2/NOTES.md`).
3. "success_admitted true" names the `success_admitted()` predicate, not a report field.
4. "reduce and check_protocol imported" is satisfied by same-module definitions.
5. Review change applied in code (`e72ca7f`): S2's `--s1-output` must be the binding's hard-coded S1 tree, and
   the report sha the hard-coded one.

Acknowledgement row for `docs/reports/user-authority-2026-11-07/decisions-2026-11-08.md`:
"A2 erratum 1: wording mismatches 1 to 5 acknowledged; implementation is A2's second option; P3 covers 3 entries."

## Dry validation performed (not stage P3)

`tests/test_male_navigation_v4_probe.py` checks the P3 entry declarations and the command below against them.
No data was opened and P3 was not run.
