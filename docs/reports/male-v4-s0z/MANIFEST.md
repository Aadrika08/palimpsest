# MaleCNS v4 S0z: corpus pin and independent compact audit, execution manifest (prospective)

> **Status:** prepared, **not executed**. S0z is a **scientific attempt** (`scientific_attempt:
> true`), one attempt, one `run_research_stage.py` unit. It needs an explicit owner GO naming this
> manifest's sha256, the plan sha256 and the S0f record, data-manifest and derivation sha256s
> below. Nothing here ran the controller or opened real data. Every earlier review amendment is
> carried in the body: by-hand GO binding (incl. `current_tree_head` and `declared_fields_sha256`),
> no placeholders, write-order directories, writer lock, throttling and an extended post-run gate.

Protocol: `docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json`, sha256
`cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477`. It is not edited.

## Scope statement (supersedes the earlier S0z design note)

The protocol's S0z is "pin + independent compact audit": it **freezes the v4 data-manifest sha256
and the source rosters before any training reads them**, and S1 cannot start before S0z passes
review. It has no producer and **no array bundle**. The earlier note in `male-v4-s0f/MANIFEST.md`
that S0z would re-derive the advice arrays and publish a keyed bundle was a design error: M4's
keyed-array loader was an invented format, and v3 never used a bundle
(`train_male_navigation_v2.prepare`, `train_male_navigation_v3.py`).

**Advice arrays are derived at S1, in-process, hash-gated, exactly as v3 did.** Commit `d537a96`
changes M4's data path to v3's design:

1. Before Torch, S1 runs `scripts/derive_male_navigation_v4_s1_data.py` as a `python -I -B` child
   with only the T-f port on `sys.path` and S0f's live locator. (A child is required: the S1
   process already holds the current `palimpsest` modules, whose `artifacts.py`/`records.py`/
   `male_research.py` bytes differ from the port's, so the S0f readers cannot be imported
   in-process.)
2. **Before reading anything**, the child requires T-f's own `reader_identity` to equal the S0f
   manifest's `current_reader_sources` (95 files), `SELF_SHA` to equal `adapter_sha256` and the
   feature-protocol digest to equal `feature_protocol_sha256`. S1 also checks the T-f and T-h
   worktree HEADs against the S0z record.
3. Old arrays come from `read_old_transfer` over S0f's `historical-arrays.npz` (re-checked against
   the T-h historical identity); advice arrays from `advice_arrays(iter_ticks(...))` over the S0e
   recordings after `admit_collection`/`admit_record`.
4. **Every source must hash (features + targets bytes) to its manifest `feature_target_sha256`,
   and both arms must equal the manifest's ordered `arms`** (v3's exact check); any drift ends S1.
   The parent re-validates the transient `.npz` (float32, `(rows, 388)`/`(rows, 2)`, finite, exact
   key set) and hashes again.

This derivation is identical to v3's and gated by equality to the hashes S0z pins, so it is
**not a new data-producing stage and needs no amendment**. S0z does **not** vouch for advice-array
identity (they are not published by S0f): that is enforced at S1 by the fts gate, and the audit
report says so. S0z does vouch for the 14 old/dev arrays it can re-hash from S0f's own output.

## What S0z runs

`scripts/run_male_navigation_v4_s0z.py` from `CUR` as unit `S0z`. There is no driver invocation, no
locator and no producer, so S0z is not in the driver's stage map: the controller validates the S0f
record with the audit's explicit S0a..S0f chain check instead of `previous_chain`.

1. **Gates:** protocol bytes, GO (stage S0z), absolute paths, `run_research_stage.py` work leaf,
   a fresh stage root, the two expected shas.
2. **Independent audit** (`scripts/audit_male_navigation_v4_s0z.py`, stdlib + NumPy only; no Torch,
   no `palimpsest`, no schedule code). Checks: `s0f_record` (schema, S0a..S0f chain, T-f head,
   locator sha), `outputs` (all 11 S0f outputs, 5,554,710 B, re-hashed), `manifest_pin`,
   `structure` (8+2 old, 12 advice in scene 3100..3103 × learner 10/11/12 order, 4 shared dev, no
   held-out, recovery ≤ 120, advice ≤ 600, 26 unique fts, counts equal to the sums, run ids),
   `old_corpus` (old and dev identities equal the S0c manifest, in order), `historical_arrays`
   (28 members, float32, shapes, finite, each source hashes to its fts) and `derivation` (N, q, r
   and source rows of both arms recomputed by independent divmod of 46,080).
3. **`derive()` reproducibility:** M4's pure `derive` run twice, byte-identical, sha256 equal to
   the expected `81cd9a49…83cb`.
4. **Publication, only if all pass:** `corpus-pin.json` in M4's `m7-navigation-v4-corpus-pin-1`
   schema. It holds stage S0z, status passed, the data manifest, the reader context S1 needs (T-f
   and T-h path and head, locator, S0f data root), the 26 ordered roster hashes, the derivation sha,
   the S0f record, the audit and the chain S0a..S0z.

Writes only under the stage root `male-v4-data/S0z/`: `derivation.json`, `audit.json`,
`corpus-pin.json`. A failed audit leaves `audit.json` and `derivation.json` and no pin.

## Plan-only result (nothing executed)

```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B \
  /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_male_navigation_v4_s0z.py \
  --s0f-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0f/pin-record.json \
  --stage-root /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0z \
  --expected-manifest-sha256 4a1be0920f01a3d36df4f9a48b7906fefbd4efd128e1ffaa1ff2759a010e2fa3 \
  --expected-derivation-sha256 81cd9a496ec25762b106276fbfb87754593c668d6159adf5c15b30df38ff83cb
```

Plan-only reads only the S0f pin record's JSON (a pin document, also committed under
`docs/reports/male-v4-s0f/`); it opens no data and writes nothing. The raw output (run in this
branch's agent worktree) is [`plan-only.prepared-in-agent-worktree.json`](plan-only.prepared-in-agent-worktree.json)
(`2dbfd9444b5deeb87fb5c0131bdebc688b5a527b81a8683c4fa612496428baa0`); from `CUR` it differs only
in the controller path. The expected `CUR` plan is [`plan-only.json`](plan-only.json), sha256
**`17d4ee6c67cdd198d8da214850e867f0e92aa06edce141812adc6def9fc9a66d`**; a test checks the
derivation.

## Budget, deadlines and throttling

Amendment 1 row: S0z expected ≈ 82 s, `RuntimeMaxSec` 300, `TimeoutStopSec` 5, k = 1, worst case
k × (300 + 5) = **305 CPU-s** (matches `run_research_stage.py`'s rule).

**Estimate from S0f.** S0f measured **36.535 CPU-s**, which read 26 recordings through the T-e
collector's `admit_record`, computed 7,197 + 1,228 feature rows and re-hashed ~650 MB of source
files. S0z does none of that: it hashes S0f's 11 output files (**5.55 MB**, of which
`historical-arrays.npz` is 5.23 MB), loads 14 arrays (2,117 + 1,228 rows × 388 float32 ≈ 5 MB) and
builds six schedules of 1,440 updates twice. It does **not** read the S0e recordings (~1.14 GB);
even re-hashing them at 0.5 GB/s would add only a few seconds. Estimate **well under 40 CPU-s**
(the derive time was not measured separately), giving ≥ 7x headroom against the 300 s kill and
about 8x against S0f's own 36.5 s ceiling. **Throttling risk (stated, not blocking):** under
CPUQuota 100% the work is single-threaded NumPy and hashing; the pure schedule build is the
unmeasured part. Any timeout or kill is an operational failure that ends v4.

**Admissibility.** The measured v4 charge excluding the v3 prior is 602.678 (ledger lane total
604.510). Worst cases ahead through S2: S0z 305, S1 2,165, S2 4,435 = 6,905. So
602.678 + 6,905 = **7,507.678 ≤ 14,398.168**. **Held-out basis:** at expected costs (S0z 82, S1 480
plus ≈ 37 for the in-S1 data derivation, S2 988.524) the charge through S2 would be about 2,190
against the 5,643.168 S3 threshold, which is decided by measured charges. S1's worst case (2,165)
already covers the derivation child.

## GO record

Write it at `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0z/go-S0z.json`:

```json
{"decision": "GO", "lane": "navigation", "stage": "S0z",
 "protocol_sha256": "cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477",
 "manifest_sha256": "<sha256 of this file>",
 "plan_sha256": "17d4ee6c67cdd198d8da214850e867f0e92aa06edce141812adc6def9fc9a66d",
 "s0f_pin_record": "/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0f/pin-record.json",
 "s0f_pin_record_sha256": "635d7ebcbcafece61b84bf49ee3d43cc30cd75e984680b17cfa6367e5cf9cc42",
 "data_manifest_sha256": "4a1be0920f01a3d36df4f9a48b7906fefbd4efd128e1ffaa1ff2759a010e2fa3",
 "schedule_derivation_sha256": "81cd9a496ec25762b106276fbfb87754593c668d6159adf5c15b30df38ff83cb",
 "declared_fields_sha256": "<sha256 of declared-fields.json in CUR>",
 "t_f_head": "88c1a0f6f53274fe663f4cdad3be5ae2743af558",
 "t_h_head": "0789b2ed54117c01c40ab5818148cc0515eb4fb5",
 "current_tree_head": "<authority-paper-rewrite HEAD at launch>",
 "cpu_quota_k": 1,
 "scientific_attempt": true,
 "granted_by": "<owner>", "granted_at": "<date>"}
```

## Pre-launch checks (all must hold; any failure means no launch, and nothing is charged)

1. **Current tree:** `CUR=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite`
   is at the research head carrying the S1 data-path change (`d537a96`), the S0z controller
   (`5a19054`) and this manifest, with clean tracked files; its protocol is `cd4eb130…` and
   `declared-fields.json` hashes to the GO's `declared_fields_sha256`.
2. **Plan:** the plan-only command above, run from `CUR`, prints output with sha256 `17d4ee6c…`.
3. **S0f inputs:** the S0f pin record is `635d7ebc…`, the data manifest `4a1be092…` and the derivation
   (`docs/reports/male-v4-s0f/derivation.json`) `81cd9a49…`; `historical-arrays.npz` and the other
   outputs still match the record (the audit re-checks).
4. **GO binding (by hand; `load_go`/`check_go` do not compare these):** `manifest_sha256` is the sha256
   of this committed file; `plan_sha256` matches check 2; the S0f record, manifest and derivation shas
   match check 3; `declared_fields_sha256` matches check 1; `t_f_head` and `t_h_head` equal the
   current HEADs of `port-t-f` and `port-t-h`; `cpu_quota_k` is 1 (= `--cpu-quota-k 1`);
   `current_tree_head` is CUR's HEAD at launch; no `<…>` placeholder remains.
5. **Writer lock free:** no palimpsest lab, producer or research stage is running in any lane, and
   nothing holds `~/.cache/palimpsest/writer.lock` (`fuser` empty).
6. **Directories, by write order.** S0z has no driver and writes no locator, so the order differs
   from S0f: `male-v4-data/S0z` must **not exist** (the controller requires it fresh, then
   `mkdir`s it before writing); its parent `male-v4-data` exists. Create
   `palimpsest-authored-test-evidence/male-v4-s0z/` for the GO record; `male-v4-s0z/receipt` must
   not exist.
7. **Ledger:** no `navigation/S0z` row. No other navigation-lane unit is running.
8. **Not applicable:** no rendering, no EGL, no native import, no Torch (the audit asserts it).

## Launch (charged; one attempt)

<!-- s0z-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage S0z --cpu-quota-k 1 --runtime-max-sec 300 --worst-case-cpu 305 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0z/go-S0z.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0z/receipt \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_male_navigation_v4_s0z.py \
  --s0f-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0f/pin-record.json \
  --stage-root /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0z \
  --expected-manifest-sha256 4a1be0920f01a3d36df4f9a48b7906fefbd4efd128e1ffaa1ff2759a010e2fa3 \
  --expected-derivation-sha256 81cd9a496ec25762b106276fbfb87754593c668d6159adf5c15b30df38ff83cb \
  --go /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0z/go-S0z.json
```

## Post-run gate (before any S1 preparation)

- **Unit:** receipt `complete`, `drained`, returncode 0, no survivors; ledger `charged` S0z row; the
  controller printed `status: passed`.
- **Outputs:** exactly `audit.json`, `corpus-pin.json`, `derivation.json` under `male-v4-data/S0z`.
  `audit.json` has `status: passed`, `failures: []`, all seven checks `ok`, `torch_imported: false`.
  `derivation.json` hashes (as written bytes) to a document whose `derive()` sha256 is `81cd9a49…`.
- **Corpus pin** (`corpus-pin.json`): schema `m7-navigation-v4-corpus-pin-1`, stage `S0z`, status
  `passed`, protocol sha `cd4eb130…`, `qualification_claims: []`, `scientific_attempt: true`; `go_sha256`
  equals the GO file; `data_manifest` equals the S0f manifest (path, `4a1be092…`, bytes);
  `schedule_derivation_sha256` equals `81cd9a49…`; chain keys exactly `[S0a, S0b, S0c, S0d, S0e,
  S0f, S0z]` with `chain.S0a..S0f` equal to the S0f record's chain and the `S0z` entry binding the
  stage root and the `derivation.json`/`audit.json` shas; `s0f_pin_record` sha `635d7ebc…`;
  `roster_feature_target_sha256` is 10 old + 12 advice + 4 dev, 26 unique, equal to the manifest's
  arms in order; `reader` has `t_f` at `88c1a0f6…` and `t_h` at `0789b2ed…` (both equal
  `ports.json`), the S0f locator path and sha (equal to the S0f record's `port.locator_sha256`) and
  `data_root` = the S0f output root; **no `arrays` key**.
- **Dry-load of what S1 consumes (no arrays, no Torch):** `train_male_navigation_v4.read_corpus_pin`
  returns the record and its sha256, and `derive_schedules(record)['sha256']` equals `81cd9a49…`
  (old N 2,117 q = 21 r = 1,623; augmented N 7,197 q = 6 r = 2,898).
- **Graphics/CUDA:** not applicable.

Record the corpus-pin and audit sha256s in the S0z RESULT and the S1 GO. **S1 prerequisites that
are not part of S0z:** (a) an independent review of S0z's audit and of the S1 data-path change
(`d537a96`); (b) Stage P never probed the new files (`derive_male_navigation_v4_s1_data.py`, the S0z
controller and audit); their import closures are stdlib/NumPy plus `palimpsest.male_matched_budget_v4`
and, for the child, the T-f closure already probed as S0f-port, so extending the P entry points
needs its own reviewed decision before S1; (c) the S1 manifest must restate the new
`SOURCES` entry and the T-f/T-h head checks.

## On failure

Per protocol `execution_stops`, any pin or structural mismatch, failed audit, non-reproducible
`derive()`, RuntimeMaxSec kill or nonzero exit **ends v4**: S1 and later stages stay `not_started`.
There is no retry, substitution, filtering or recollection; the first fault and its outputs are
retained, the charge stands (census, or 305 CPU-s without a complete receipt), and further work
needs a new protocol version.
