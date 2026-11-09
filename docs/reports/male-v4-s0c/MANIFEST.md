# MaleCNS v4 S0c: recovery data preparation (port tree T-c), execution manifest (prospective)

> **Status:** prepared, **not executed**. S0c is a **scientific attempt**
> (`scientific_attempt: true`) with one attempt only. It needs an explicit owner GO naming this
> manifest's sha256, the plan sha256 and both previous pin-record sha256s below. Nothing here
> has run the producer. The S0a and S0b review amendments (writer lock, directories, throttling,
> by-hand GO binding, extended post-run gate) are carried in the body from the start.

Protocol: `docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json`, sha256
`cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477` (Amendment 1 + erratum 1;
owner decision A1). The protocol is not edited.

| Previous record | Path | sha256 |
| --- | --- | --- |
| S0a (teacher collection) | `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/pin-record.json` | `d8e511b8d8095c8d781a0ecfb2b031571c4f6fd72d0367b88520643d0f653901` |
| S0b (recovery collection; chain S0a+S0b) | `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b/pin-record.json` | `b3511f1a3bf625dd4cec20733317b5288bb965cde6873fbb1023a768e02809cb` |

## Prerequisite done in this branch: the live v4 recovery-learning copy

S0c is the first consumer of a v4 pin document. Before this branch, plan-only **refused**:
`v4 pin copy still holds PENDING placeholders at: /baseline_collection_sha256,
/recovery_report_sha256, /recovery_sources/{0,1}/{result_sha256,run_id}`.

A second defect sat behind that one. The copy's count fields still held the original values,
including the scalar `recovery_ticks_each: 67`. The T-c port indexes it per source (`:90`,
`:140`, `:198`), so a launch would have failed with a TypeError and ended v4. Amendment 1 lists
the needed follow-up: "regenerate the pin copies with PENDING- placeholders for the
`amendment_1_pending` fields". Commit `f62ef5b` therefore:

1. **Activates** the recovery-learning count fields (`/counts`, `/recovery_ticks_each`,
   `/recovery_windows`, schemas `recovery-learning-counts-v4`, `recovery-ticks-v4` and
   `recovery-windows-v4`) as declared fields in `declared-fields.json`. It records them under
   `amendment_1_pending.activated` and gives every declared field its fill source. The other
   pending fields stay inactive.
2. **Regenerates** `docs/plans/m7-navigation-v4-pins/m7-recovery-learning-protocol.json` from the
   original (`091c4e98…`) with every declared field at its placeholder.
3. **Fills** it in place with the new driver mode `--fill-document`. That mode reads **only** the
   previous pin records (here the S0b record, whose chain carries S0a), fills only placeholder
   fields, and re-traces every value with the driver's `check_document_values`. The values are:
   - `baseline_collection_sha256` `7c5fabc2…614f`, the S0a `collection.json`;
   - `recovery_report_sha256` `2a54c2a5…2974`, the S0b `report.json`;
   - result sha256s `e050065c…73e8` and `f6ae433a…b594`;
   - run ids `f10998ca8ed246059193ca87a9a19a7b` and `a3a272518cfe41f0971631439ce1e84c`;
   - `recovery_ticks_each` `[67, 67]`;
   - `recovery_windows` `[[32,32,3],[32,32,3]]`, derived per source;
   - `counts.per_source.baseline_train` `[277,182,315,245,199,265,243,257]` and
     `counts.per_source.dev` `[189,338,319,382]`;
   - train 2,117 (1,983 + 134), dev 1,228, held_out 0;
   - `v2_reference_counts` unchanged and descriptive.

   The resulting copy has sha256 **`9c0ae9efb2c70908b755daeba4157d32b5daf792807fcaf18ed05f54d23a77df`**
   and no placeholder; `declared-fields.json` has sha256 `c4d35e46…f439`. Tests bind the
   tracked copy to the committed S0a/S0b records and to a refill of the placeholder copy.

The **live locator** the driver writes at launch is not the P-time PENDING locator. It is built
from the validated copy and names the copy above by absolute path and sha256 `9c0ae9ef…`. It is
written next to the pin record as `male-v4-runs/S0c/pin-record.json.port-pins.json`.

## What S0c runs

The T-c port of `scripts/prepare_male_recovery_data.py` runs from the detached worktree
`/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-c`. Its HEAD
is the recorded port commit `c06b4976f30b86455dc9ea3406bad6fab42371e1` (branch
`port/male-v4-t-c`, base `7d5fc1f`). The port producer's sha256 is `ddefc34d…e24c`, and the six
reader source guards are those listed in `plan-only.json`. The driver runs the port
**in-process** (`prepare_male_recovery_data.main`) with `PALIMPSEST_M7_V4_PINS` set to the live
locator; the port's H1 hunks read the copy path and sha from it at import.

Producer arguments (all `record` kind, so the driver checks each against the chain's recorded
bytes and sha):
- `--baseline-collection .../male-v4-runs/S0a/collection/collection.json` (49,105 B, `7c5fabc2…`)
- `--recovery-report .../male-v4-runs/S0b/collection/report.json` (61,806 B, `2a54c2a5…`)
- `--output .../male-v4-runs/S0c/data` (fresh; the producer creates it exclusively and refuses overlap with its inputs)

The producer re-admits 14 sources in a fixed order: 8 baseline train, then 2 recovery, then 4
recorded-dev, with zero held-out. It applies v2's reader, the per-source pins and the 120-row
bound, and publishes `data-manifest.json` within the protocol's 180 s `preparation_limits`.
It reads S0a/S0b recordings, chunks and events only through the pinned readers, with no native
decode.

## Plan-only result (no producer executed)

```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B \
  /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/regenerate_male_navigation_v4.py \
  --stage S0c --worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-c \
  --previous-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b/pin-record.json --plan-only -- \
  --baseline-collection /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/collection/collection.json \
  --recovery-report /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b/collection/report.json \
  --output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0c/data
```

Status `admissible`, exit 0, with port check T-c at `c06b4976…`, previous record `b3511f1a…`,
document `m7-recovery-learning-protocol.json` `9c0ae9ef…` and the live locator. It was run in
this branch's agent worktree, so its document paths name that worktree's pins directory. That
raw output is kept as [`plan-only.prepared-in-agent-worktree.json`](plan-only.prepared-in-agent-worktree.json)
(`1c07b3b43d73dd06946cc4fafb86cef6052da656cdcef6a002d59b1076834fd0`). Run from `CUR`, the same command differs only in those two path strings. The
expected `CUR` plan is [`plan-only.json`](plan-only.json), sha256
**`41d53b28af3f13513aa0ee92f1b4da4c55aabc84a31c1389048fef2e5bc4a853`**, and a test checks that
it equals the raw output with that prefix replaced. Pre-launch check 2 re-derives it from `CUR`.

## Budget and unit

The protocol's Amendment 1 cost table row for S0c gives expected 13.701 s (launch/cleanup);
`RuntimeMaxSec` 180 (`preparation_limits.seconds`); `TimeoutStopSec` 5; CPUQuota k = 1 (owner
decision 7). The worst case is k × (180 + 5) = **185 CPU-s**. That matches
`run_research_stage.py`'s rule (`worst ≥ k × (RuntimeMaxSec + 5)`). The navigation lane stood at
193.955 of 14,400 CPU-s before S0c, in the global ledger
`~/.local/state/palimpsest/research-ledger.jsonl`. 193.955 + 185 ≤ 14,400, so S0c is admissible.

**Throttling risk (stated, not blocking).** 13.701 s is a historical unconstrained wall figure,
so headroom is about 13x. The 180 s `RuntimeMaxSec` starts at unit start and covers the driver
too: worktree, port and copy verification, the in-process import closure, the producer's own 180 s
deadline, and output hashing for the pin record. So the producer deadline and the unit kill
coincide. Any `TimeoutError` or kill is an operational failure that ends v4. The thread
environment is the driver's and P's for S0c: none set beyond the unit.

**EGL / graphics: not applicable.** S0c renders nothing and creates no GL context: the feature
encoder reads recorded uint8 camera arrays. The host graphics stack (`mesa 1:26.2.5-1`,
`libglvnd 1.7.0-3`) is recorded only for continuity with P, S0a and S0b.

## GO record

Write it at `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0c/go-S0c.json`:

```json
{"decision": "GO", "lane": "navigation", "stage": "S0c",
 "protocol_sha256": "cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477",
 "plan_sha256": "41d53b28af3f13513aa0ee92f1b4da4c55aabc84a31c1389048fef2e5bc4a853",
 "previous_pin_record": "/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b/pin-record.json",
 "previous_pin_record_sha256": "b3511f1a3bf625dd4cec20733317b5288bb965cde6873fbb1023a768e02809cb",
 "chain_pin_record_sha256": {"S0a": "d8e511b8d8095c8d781a0ecfb2b031571c4f6fd72d0367b88520643d0f653901",
                             "S0b": "b3511f1a3bf625dd4cec20733317b5288bb965cde6873fbb1023a768e02809cb"},
 "pin_document_sha256": {"m7-recovery-learning-protocol.json": "9c0ae9efb2c70908b755daeba4157d32b5daf792807fcaf18ed05f54d23a77df"},
 "manifest_sha256": "<sha256 of this file>",
 "worktree": "/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-c",
 "worktree_head": "c06b4976f30b86455dc9ea3406bad6fab42371e1",
 "port_tree": "T-c",
 "current_tree_head": "<authority-paper-rewrite HEAD>",
 "cpu_quota_k": 1,
 "scientific_attempt": true,
 "granted_by": "<owner>", "granted_at": "<date>"}
```

## Pre-launch checks (all must hold; any failure means no launch, and nothing is charged)

1. **Current tree:** `CUR=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite`
   is at the research head carrying this manifest and commit `f62ef5b`, with clean tracked files.
   Its protocol file hashes to `cd4eb130…d477`, its `docs/plans/m7-navigation-v4-pins/m7-recovery-learning-protocol.json`
   to `9c0ae9ef…7df` and its `declared-fields.json` to `c4d35e46…f439`.
2. **Plan:** the plan-only command above, run from `CUR`, prints output whose sha256 is
   `41d53b28…a853`. That confirms the port branch and HEAD, detached, clean, producer and
   guards, both previous records and the live locator.
3. **Previous records:** `sha256sum` of the S0a and S0b pin records gives `d8e511b8…3901` and
   `b3511f1a…09cb`, and the two `--baseline-collection` and `--recovery-report` files hash to
   `7c5fabc2…614f` and `2a54c2a5…2974`.
4. **GO binding (by hand; `load_go`/`check_go` do not compare these):**
   - `manifest_sha256` is the sha256 of this committed file;
   - `plan_sha256` is `41d53b28…a853`;
   - `previous_pin_record_sha256` is the sha256 of the `--previous-pins` file;
   - `chain_pin_record_sha256` matches check 3;
   - `pin_document_sha256` matches check 1;
   - `cpu_quota_k` is 1, matching `--cpu-quota-k 1`;
   - `worktree_head` is `c06b4976…`;
   - no `<…>` placeholder remains anywhere in the GO record.
5. **Writer lock free:** no palimpsest lab, producer or research stage is running in any lane, and
   nothing holds `~/.cache/palimpsest/writer.lock` (`fuser` empty).
6. **Directories:** create `palimpsest-authored-test-evidence/male-v4-s0c/` (GO record) before
   launch. `male-v4-s0c/receipt` must not exist. `male-v4-runs/S0c/` must be absent or empty, and
   `data`, `pin-record.json` and `pin-record.json.port-pins.json` must not exist.
7. **Disk:** free space on `/home` ≥ 1 GiB floor + 4 MiB manifest cap.
8. **Ledger:** no `navigation/S0c` row. No other navigation-lane unit is running.

## Launch (charged; one attempt)

<!-- s0c-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage S0c --cpu-quota-k 1 --runtime-max-sec 180 --worst-case-cpu 185 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0c/go-S0c.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0c/receipt \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/regenerate_male_navigation_v4.py \
  --stage S0c --worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-c \
  --previous-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b/pin-record.json \
  --go /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0c/go-S0c.json \
  --pin-record-out /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0c/pin-record.json \
  -- \
  --baseline-collection /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0a/collection/collection.json \
  --recovery-report /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0b/collection/report.json \
  --output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0c/data
```

With `--go`, the driver re-reads both record inputs and refuses unless their bytes match the
chain. It writes the live locator `male-v4-runs/S0c/pin-record.json.port-pins.json` (exclusive,
fsynced), sets `PALIMPSEST_M7_V4_PINS`, runs the port in-process and re-verifies the worktree. It
then writes the pin record.

## Expected outputs

- `male-v4-runs/S0c/data/data-manifest.json` (no `data-manifest.pending`, no `failure.json`).
- **Pin record** `male-v4-runs/S0c/pin-record.json`. It holds schema `m7-navigation-v4-pin-record-1`;
  stage S0c; producing commit `c06b4976…`; `previous_record_sha256` `b3511f1a…`; `go_sha256`; and
  `port` {tree T-c, branch, head, base `7d5fc1f…`, locator path and sha256}. Its chain is
  `[S0a, S0b, S0c]`, and its outputs are `data-manifest.json`'s sha256 and bytes. It has no
  `counts` (S0c has none).
- `male-v4-s0c/receipt/`: `receipt.json`, `stdout.log` (the driver's `completed` JSON) and `stderr.log`.
- Ledger: one `reserved` row (185) and one `charged` row for `navigation/S0c`.

## Post-run gate (before any S0d GO)

Require all of the following:

- **Data manifest:**
  - `status: prepared-research-only` and `qualification_claims: []`;
  - `protocol` equals the v4 copy `9c0ae9ef…`; `baseline_collection.sha256` is `7c5fabc2…`
    and `recovery_report.sha256` is `2a54c2a5…`;
  - `ordered_sources.train` holds 10 sources: the 8 S0a train runs in collection order with
    ticks `[277,182,315,245,199,265,243,257]`, then `f10998ca…` (67) and `a3a27251…` (67);
  - `ordered_sources.dev` holds 4 sources with ticks `[189,338,319,382]`, and
    `ordered_sources.held_out` is `[]`;
  - `counts` is `{train: 2117, dev: 1228, held_out: 0}`;
  - `recovery_admission` has the two sources in case order with `windows`
    `[[32,32,3],[32,32,3]]` and matching run ids;
  - every `feature_target_sha256` is present.
- **Pin record:**
  - chain keys exactly `[S0a, S0b, S0c]`, with `chain.S0a` and `chain.S0b` equal to the
    records' own entries;
  - `previous_record_sha256` is `b3511f1a…`, and `go_sha256` is the sha256 of the GO file;
  - `port.locator_sha256` is the sha256 of the written locator, and that locator names the copy
    `9c0ae9ef…`;
  - `outputs` holds exactly `data-manifest.json`, with sha256 and bytes equal to the file.
- **Unit:** launcher receipt `complete`, `drained`, returncode 0, no survivors; ledger `charged`
  S0c row; the driver printed `status: completed`.
- No held-out path was named or read: the producer takes no held-out argument, and the manifest
  shows zero held-out sources.

Record the S0c pin-record sha256 in the S0c RESULT and in the S0d GO.

## On failure

Per protocol `execution_stops`, any S0 producer refusal, guard mismatch, pin mismatch,
structural-admission failure, RuntimeMaxSec kill, storage breach or nonzero exit **ends v4**.
This includes:

- a driver `refused`, `producer-failed` or `record-refused` status;
- `failure.json` in the output;
- a missing pin record;
- a unit that is not drained.

Later stages stay `not_started`. There is no retry, substitution, filtering, recollection or
budget change. The first fault and all partial outputs are retained as they are, the charge
stands (census, or 185 CPU-s without a complete receipt), and any further work needs a new
protocol version.

## Review amendments (independent AI review, 2026-11-09)

- **Required — pre-launch check 6 replaced:** `male-v4-runs/S0c/` must **exist and be empty**
  (create it before launch). In GO mode the driver writes the locator
  `S0c/pin-record.json.port-pins.json` with `open('xb')` before the producer runs, and only the
  producer creates `S0c/`; an absent directory would fail after the ledger reservation and end v4.
  An empty `S0c/` does not conflict with the producer's `exist_ok=False` on `S0c/data`.
- **Gate wording:** the data manifest's `protocol_sha256` must equal the filled copy sha
  `9c0ae9ef…`; its `protocol` field holds the whole document, not a sha.
- **Line references:** the T-c port reads `counts.per_source` at `:141` and `:207`.
- **Fill fix f62ef5b:** within Amendment 1's declared pins (`added_pins`: recovery-learning copy
  counts/ticks/windows pinned from S0a/S0b); no owner acknowledgement required. Note: consumer-side
  `check_document_values` only checks a sha matches some stage output (weaker than fill's exact
  named output); the GO binds the copy sha and the producer re-checks file shas.
