# MaleCNS v4 S0f: navigation data preparation (port tree T-f, historical reader T-h), execution manifest (prospective)

> **Status:** prepared, **not executed**. S0f is a **scientific attempt**
> (`scientific_attempt: true`) with one attempt only. It needs an explicit owner GO naming this
> manifest's sha256, the plan sha256 and the record and document sha256s below. Nothing here ran
> the driver in GO mode or the producer. Every earlier review amendment is carried in the body
> from the start: by-hand GO binding including `current_tree_head` and `declared_fields_sha256`,
> no placeholders, the writer lock, write-order directories, a throttling note and an extended
> post-run gate with dry-loads of what S0z and S1 consume.

Protocol: `docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json`, sha256
`cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477`. It is not edited.

## Prerequisite done in this branch: the data-v2 copy (commit `480c741`)

Every remaining data-v2 field is now active; `amendment_1_pending` holds no pending field or
document. The copy was regenerated at its 41 placeholders and filled with `--fill-document --stage
S0f --worktree <T-f> --historical-worktree <T-h> --previous-pins <S0e collector record>`. That
mode reads only pin records, the files they bind, validated copies and git objects of the
recorded port commits, and it re-checks every value:

| Field group | Source |
| --- | --- |
| `immutable_inputs` (9 × path/sha256/bytes) | merged S0e chain (collector record + controller record): `collection/report.json` and `control/{terminal, enclosing, outer-launch/supervisor, outer-supervisor/supervisor, exec-drain, root-raw-audit, collection-index}.json`; `old_manifest` is the S0c `data-manifest.json`. They equal the published collection index's bindings. |
| `old_baseline_document`, `old_recovery_document` | the S0a `collection.json` and S0b `report.json` records |
| `parent_study` | the contact-v2 copy (repo-relative path, sha256 `cadd0e45…`) |
| `source_binding.old_historical_reader` (H4) | `root` is the T-h worktree, checked at the T-h port commit. `head` is `0789b2ed…`. The tracked Python inventory is computed from git objects at that commit: **70** files, canonical map from the same algorithm, which reproduces the original `217cbee` pin `ef29698a…` exactly. `adapter_sha256` is the T-h port reader `ddefc34d…`, and the six `code` pins are unchanged. |
| `source_binding.navigation_producer_commit` | the S0e producing commit = T-e port `703acc50…` |
| `counts` | `data-v2-counts-v4` from the S0a/S0b/S0e records: old 2,117 (8 teacher + 67 + 67), advice 5,080 (`600, 485, 496, 600, 196, 600, 600, 243, 198, 600, 276, 186`), dev 1,228, augmented 7,197, combined 8,425, held-out 0 |

The filled copy `m7-navigation-data-v2-protocol.json` has sha256
**`41c1bb9ae511f64e581265ce15b89b3313fe1813651d589bb54f6678a34261ae`**; `declared-fields.json` has
**`8877390c230e6371d6130abf3f4ff874639c00a9fa8d872c322251375d7ce208`**. Tests re-check the copy
against the committed S0e index and records. On the evidence host, a test loads all three S0f
documents (data-v2, recovery learning, contact-v2) through the driver's `load_pin_documents`
against the live S0e chain and the real T-f/T-h worktrees. That test also confirms the T-h
worktree's actual Python inventory equals the git-object pin.

## What S0f runs

The T-f port of `scripts/prepare_male_navigation_v2.py` runs **in-process** in the driver with the
live locator. That locator names data-v2 `41c1bb9a…`, recovery learning `9c0ae9ef…` and
contact-v2 `cadd0e45…`. The producer starts its own historical child with `python -I` (the old
reader from the T-h root) and inherits the locator environment.

- **Port tree T-f:** `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-f`,
  HEAD = port commit `88c1a0f6f53274fe663f4cdad3be5ae2743af558` (base `4ecb354`, branch
  `port/male-v4-t-f`). The producer sha256 is `b819af26…`, with port guard
  `collect_male_navigation_v2.py` `5d7ddef2…` (the T-e collector port it carries).
- **Historical reader T-h:** `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-h`,
  HEAD = port commit `0789b2ed54117c01c40ab5818148cc0515eb4fb5` (base `217cbee`, branch
  `port/male-v4-t-h`). The driver verifies both HEADs and both trees clean (`port_check`,
  `historical_port_check`).
- **Previous record:** the S0e collector pin record
  `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0e/control/collector-pin-record.json`,
  sha256 `2eb64603ba837ac495a75081e11add57fddbdf0b55a70d70b59f107840e84af0`. The driver merges it
  with the S0e controller record `32a854e6…` (stage root `male-v4-runs/S0e`, which also binds the
  drain, audit and the collection index `3d0ea26c…`).
- **Output:** `--output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0f/data`.
  It **cannot** be under `male-v4-runs`: T-f's `output_path` refuses any output overlapping
  `accepted_collection.parents[2]`, which is `male-v4-runs` itself, and every input parent.
- **Reads:** S0a/S0b raw recordings through the T-h reader (historical child), S0e recordings
  through the T-e collector port's `admit_record`, and the pinned documents. There is no native
  decode or model import, and **no rendering: EGL is not applicable**. The host stack
  (`mesa 1:26.2.5-1`, `libglvnd 1.7.0-3`) is recorded only for continuity.
- **Recorded limitation (note only):** T-f's ported `collect_male_navigation_v2.source_pins` would
  raise, because contact-v2 pins the T-e collector port while T-f's v1 collector is unported
  `d0decc66…`. No S0f path calls it: S0f compares the report's `source_pins` fields and uses
  `PLAN_SHA`, `PROFILE`, `PROFILE_SHA`, `CASES` and `admit_record`.

## Plan-only result (nothing executed)

```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B \
  /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/regenerate_male_navigation_v4.py \
  --stage S0f --worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-f \
  --historical-worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-h \
  --previous-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0e/control/collector-pin-record.json \
  --plan-only -- --output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0f/data
```

The result is `admissible`, exit 0, with port check T-f `88c1a0f6…`, historical port check T-h
`0789b2ed…`, previous record `2eb64603…`, three documents and the live locator. It was run in this
branch's agent worktree; that raw output is
[`plan-only.prepared-in-agent-worktree.json`](plan-only.prepared-in-agent-worktree.json)
(`e4b89a1a64573b3a3fb9b9a6cf65e7077f0a06fb5de8b6b2d7534fbb8c12a873`). Run from `CUR`, it differs
only in the document paths. The expected `CUR` plan is [`plan-only.json`](plan-only.json), sha256
**`79a7a23ea53bf742fdb8c0c714cae3a665d00cc7a3c7f421191269fde6f91954`**, and a test checks the
derivation.

## Budget, deadlines and throttling

Amendment 1 cost table: S0f expected 79.460 s (pre-publication). `RuntimeMaxSec` is 263, the
nominal failure envelope; `TimeoutStopSec` is 5; CPUQuota k = 1 (owner decision 7). The worst case
is k × (263 + 5) = **268 CPU-s**, which matches `run_research_stage.py`'s rule.

**Admissibility.** In the protocol's form, the measured v4 charge excluding the v3 prior is
566.143. The worst cases still ahead through S2 are S0f 268, S0z 305, S1 2,165 and S2 4,435, a
total of 7,173. That gives 566.143 + 7,173 = **7,739.143 ≤ 14,398.168** (remaining at start).
Equivalently, in the ledger's form, the lane total of 567.975 including the prior gives
567.975 + 7,173 = 7,740.975 ≤ 14,400.

**Held-out basis.** The measured v4 charge excluding the v3 prior is **566.143** now. At expected
costs (S0f 79.46, S0z 82, S1 480, S2 988.524) it would be about **2,196** through S2, against the
5,643.168 S3 threshold. The threshold is decided by measured charges.

**Deadline nesting.**

| Bound | Seconds |
| --- | ---: |
| historical child (`min(120, deadline − now)`) | ≤ 120 |
| producer internal deadline (`prepare`: entry + 180, `internal_seconds_from_entry`) | 180 |
| protocol normal-through-exit | 230 |
| unit `RuntimeMaxSec` | 263 |

The driver's verification, document loading and import closure run before the producer clock
starts, and the output hashing for the pin record runs after it. Both count against the unit's
263 s. The historical figure (79.46 s) gives about 2.3x against the 180 s internal bound.

**Throttling risk (stated, not blocking).** The run was historically unconstrained; under CPUQuota
100% the in-process driver has no thread variables set beyond the unit's environment (stage P's
S0f entry declares none). It re-hashes about 650 MB of S0a/S0b/S0e source files, re-reads 26
recordings and computes 7,197 + 1,228 feature rows. Any `TimeoutError`, historical-child kill or
RuntimeMaxSec kill is an operational failure that ends v4.

## GO record

Write it at `/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0f/go-S0f.json`:

```json
{"decision": "GO", "lane": "navigation", "stage": "S0f",
 "protocol_sha256": "cd4eb1307f4be6f2d924142eb4202e001918c81660145db26764a410b9dcd477",
 "manifest_sha256": "<sha256 of this file>",
 "plan_sha256": "79a7a23ea53bf742fdb8c0c714cae3a665d00cc7a3c7f421191269fde6f91954",
 "previous_pin_records_sha256": ["2eb64603ba837ac495a75081e11add57fddbdf0b55a70d70b59f107840e84af0"],
 "s0e_controller_record_sha256": "32a854e61d2284a0b63b77069870524b79c98f7b9b3950ffdb6e750a7d7eb827",
 "s0e_collection_index_sha256": "3d0ea26c9b4a9293f39d7b54e1e90c52f55bfb07eefec36ea1c8fd7d7ff90972",
 "pin_document_sha256": {"m7-navigation-data-v2-protocol.json": "41c1bb9ae511f64e581265ce15b89b3313fe1813651d589bb54f6678a34261ae",
                         "m7-recovery-learning-protocol.json": "9c0ae9efb2c70908b755daeba4157d32b5daf792807fcaf18ed05f54d23a77df",
                         "m7-navigation-contact-v2-protocol.json": "cadd0e45190cc2a6f4bbc742c8b38f065bbe2c831f42b8f84cef4bd75d3b1de3"},
 "declared_fields_sha256": "8877390c230e6371d6130abf3f4ff874639c00a9fa8d872c322251375d7ce208",
 "worktree": "/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-f",
 "worktree_head": "88c1a0f6f53274fe663f4cdad3be5ae2743af558",
 "historical_worktree": "/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-h",
 "historical_worktree_head": "0789b2ed54117c01c40ab5818148cc0515eb4fb5",
 "port_trees": ["T-f", "T-h"],
 "current_tree_head": "<authority-paper-rewrite HEAD at launch>",
 "cpu_quota_k": 1,
 "scientific_attempt": true,
 "granted_by": "<owner>", "granted_at": "<date>"}
```

## Pre-launch checks (all must hold; any failure means no launch, and nothing is charged)

1. **Current tree:** `CUR=/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite`
   is at the research head carrying `480c741` and this manifest, with clean tracked files. In
   `CUR`, the protocol file is `cd4eb130…`, `declared-fields.json` is `8877390c…` and the three
   copies match `pin_document_sha256`.
2. **Plan:** the plan-only command above, run from `CUR`, prints output with sha256 `79a7a23e…`.
3. **Records:** the S0e collector record is `2eb64603…`, the S0e controller record `32a854e6…` and
   the collection index `3d0ea26c…`. Every `immutable_inputs` file still has its recorded
   size and sha256.
4. **GO binding (by hand; `load_go`/`check_go` do not compare these):**
   - `manifest_sha256` is the sha256 of this committed file;
   - `plan_sha256` matches check 2;
   - `previous_pin_records_sha256`, `s0e_*` and `pin_document_sha256` match checks 1 and 3;
   - `declared_fields_sha256` is `8877390c…`;
   - `cpu_quota_k` is 1, matching `--cpu-quota-k 1`;
   - `worktree_head` is `88c1a0f6…` and `historical_worktree_head` is `0789b2ed…`;
   - `current_tree_head` is CUR's HEAD at launch;
   - no `<…>` placeholder remains anywhere in the record.
5. **Writer lock free:** no palimpsest lab, producer or research stage is running in any lane, and
   nothing holds `~/.cache/palimpsest/writer.lock` (`fuser` empty).
6. **Directories, by write order:**
   - run `mkdir -p /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0f`,
     then confirm it is empty (`ls -A` prints nothing). `male-v4-data/S0f/`
     must **exist and be empty**: in GO mode the driver writes `S0f/pin-record.json.port-pins.json`
     (`open('xb')`) inside the charged unit before the producer runs. If the directory is missing,
     that write raises and ends v4;
   - `S0f/data` must not exist: the producer checks it is fresh, then runs `mkdir(parents=True,
     exist_ok=False)`;
   - `S0f/pin-record.json` must not exist;
   - create `palimpsest-authored-test-evidence/male-v4-s0f/` (GO record); `male-v4-s0f/receipt`
     must not exist.
7. **Worktrees:** `port-t-f` and `port-t-h` are detached at their port commits, with tracked files
   clean and no untracked `src`/`scripts`.
8. **Disk:** free space on `/home` ≥ 1 GiB floor + 64 MiB output cap (`StorageLimits`).
9. **Ledger:** no `navigation/S0f` row. No other navigation-lane unit is running.

## Launch (charged; one attempt)

<!-- s0f-command -->
```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/run_research_stage.py \
  --lane navigation --stage S0f --cpu-quota-k 1 --runtime-max-sec 263 --worst-case-cpu 268 \
  --ledger /home/utkarsh/.local/state/palimpsest/research-ledger.jsonl \
  --go-record /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0f/go-S0f.json \
  --receipt-dir /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0f/receipt \
  -- \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B /home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite/scripts/regenerate_male_navigation_v4.py \
  --stage S0f --worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-f \
  --historical-worktree /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-trees/port-t-h \
  --previous-pins /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-runs/S0e/control/collector-pin-record.json \
  --go /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-s0f/go-S0f.json \
  --pin-record-out /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0f/pin-record.json \
  -- \
  --output /home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/male-v4-data/S0f/data
```

## Post-run gate (before any S0z preparation)

- **Unit and driver:** the launcher receipt is `complete` and `drained` with returncode 0 and no
  survivors. The ledger has a `charged` S0f row. The driver printed `status: completed`. There is
  no `S0f/data/failure.json`.
- **Pin record (`male-v4-data/S0f/pin-record.json`):**
  - stage S0f, producing commit `88c1a0f6…`, `go_sha256` equal to the GO file;
  - `port.tree` T-f, `port.head` `88c1a0f6…` and `port.locator_sha256` equal to the locator file,
    which names the three copies. The T-h historical reader is bound by the driver's
    `historical_port_check` and by the data manifest's `historical_reader`;
  - chain keys `[S0a, S0b, S0c, S0d, S0e, S0f]`, with `chain.S0e` the merged S0e entry (output
    root `male-v4-runs/S0e`, `producer_records` `[2eb64603…]`, `controller_record_sha256`
    `32a854e6…`) and `chain.S0d` the merged S0d entry;
  - outputs include `data-manifest.json` and `historical-arrays.npz`, each sha256 and bytes equal
    to the file.
- **Data manifest (`S0f/data/data-manifest.json`), per-source ordered equality with the pin records:**
  - `status: prepared-navigation-advice-research-only`, `qualification_claims: []`, and
    `protocol_sha256` equal to the data-v2 copy `41c1bb9a…`;
  - `input_documents` equals the copy's `immutable_inputs`;
  - `historical_reader.head` is `0789b2ed…`, with an inventory of 70 files equal to the pins;
  - `labels` is `{old: unchanged executed targets, new: nav_advice_action}`, and `counts` equals the
    copy's counts.
  - **Old arm:**
    - `arms.old.train` holds 10 sources: the 8 S0a train runs in collection order with ticks
      `[277,182,315,245,199,265,243,257]`, then the two S0b recovery runs (67, 67) in case order;
    - `arms.old.dev` holds 4 sources `[189,338,319,382]`, and `held_out` is `[]`.
  - **Augmented arm:**
    - `arms.augmented.train` is the exact old prefix, then 12 advice sources;
    - the advice sources are in `new_sources` order: scene 3100…3103 × learner 10, 11, 12, run ids
      equal to the S0e cases' runs, ticks `600, 485, 496, 600, 196, 600, 600, 243, 198, 600, 276, 186`,
      each 1..600, equal to the S0e record `counts`;
    - recovery sources are ≤ 120 rows;
    - `arms.augmented.dev == arms.old.dev`, and `held_out` is `[]`.
  - **Hashes:** every source carries a `feature_target_sha256`, and all 26 training and dev
    identities are unique. Old-source hashes equal the S0c data manifest's `ordered_sources`.
    `new_sources[*].label` is `returned-analytic-teacher-advice`. No held-out source, path or row
    appears anywhere.
- **Dry-load of what S1 consumes (pure, no arrays, no Torch):**
  `palimpsest.male_matched_budget_v4.derive(<data-manifest bytes>, <its sha256>)` succeeds. It
  runs M4's `admit_rosters`: 8 + 2 old, + 12 advice in scene/learner order, 4 shared dev, 0
  held-out, bounds 120/600. It yields both arms' N (old 2,117, augmented 7,197) with q/r and
  per-seed schedule shas. Record the derivation sha256.
- **Dry-load of what S0z consumes:** `historical-arrays.npz` loads with `allow_pickle=False`, and
  its arrays cover the 14 old sources' rows (2,117 train + 1,228 dev, in the manifest's order).
  Its key layout is S0f's own; S0z re-keys it (design note). The driver's port-aware `previous_chain`
  with `driver.port_stages(driver.STAGES, driver.load_ports())` returns the S0f chain. S0f is the
  last driver stage, so S0z reads the S0f record directly.

Record the S0f pin-record and data-manifest sha256s in the S0f RESULT and the S0z GO.

## On failure

Per protocol `execution_stops`, any S0 producer refusal, guard mismatch, pin mismatch,
structural-admission failure (wrong shape, order or count), RuntimeMaxSec kill, storage breach or
nonzero exit **ends v4**. This includes:

- a driver `refused`, `producer-failed` or `record-refused` status;
- `failure.json` in the output;
- a missing pin record;
- a unit that is not drained.

Later stages stay `not_started`. There is no retry, filtering, substitution or recollection. The
first fault and all partial outputs are retained, the charge stands (census, or 268 CPU-s without
a complete receipt), and any further work needs a new protocol version.

## Design note: S0z (no code yet)

**What the protocol requires.** S0z is "pin + independent compact audit (inside a census unit)".
It freezes the v4 data-manifest SHA and the source rosters (old, augmented, recorded-dev). S1 cannot
start before S0z passes review. The cost table gives S0z a 300 s kill target and a **305 CPU-s**
worst case at k = 1 (≈82 s expected). Reviewer audits run inside that unit. S0z must also check
that S0e-A recorded `passed` with no unwaived `not_covered` item, using
`run_male_navigation_v4_s0e.audit_passed`. The structural admission it applies is the protocol's:
- the old arm is 8 teacher sources (1000–1007) then 2 recovery sources (2100/2101);
- the augmented arm is that prefix plus 12 advice sources (3100…3103 × 10, 11, 12);
- there are 4 dev sources and 0 held-out rows;
- old rows use executed targets, and advice rows use `nav_advice_action`.

There is no filtering or substitution.

**What M4's trainer assumes** (`scripts/train_male_navigation_v4.py`, `read_corpus_pin`). A JSON
record with:
- `schema: m7-navigation-v4-corpus-pin-1`, `stage: S0z`, `status: passed`, the v4
  `protocol_sha256` and `qualification_claims: []`;
- `data_manifest` and `arrays`, each exactly `{path, sha256, bytes}`.

The schedule derivation reads only the data manifest (`male_matched_budget_v4.derive`, the shape
dry-run above). `load_arrays` expects one `.npz` with keys `<feature_target_sha256>/features` and
`<feature_target_sha256>/targets` for every rostered source.

**Match and gap.** The data-manifest side matches: S0f publishes exactly the shape `derive` admits,
which the post-run dry-load confirms. The arrays side is a gap S0z must close. S0f publishes
`historical-arrays.npz` for the old sources only, while the advice arrays are computed in-process
and not persisted. S0z must therefore:

1. Re-derive the 12 advice sources' features and targets read-only, using T-f's
   `advice_arrays`/`male_model.features` over the S0e recordings bound by the S0e records.
2. Take the old and dev sources from `historical-arrays.npz`.
3. Verify every array pair against the manifest's `feature_target_sha256`.
4. Write one keyed `.npz`.
5. Publish a corpus pin in M4's schema binding `data_manifest` (the S0f output) and `arrays`, plus
   chain fields: the S0f pin-record sha256, the S0e-A audit sha256 and the derivation sha256.

M4 ignores the extra chain fields. That record-format match should be pinned by a test
(`read_corpus_pin` on a synthetic S0z record) when S0z is implemented. This needs its own
reviewed change.

**Risks to resolve before any S0z GO (S0f review).**

1. **New data production.** Re-deriving the advice arrays is new data production. It is not
   a check, so it needs its own reviewed manifest and a scope statement: which code, which inputs
   bound by which records, and the read-only guarantee for S0e recordings.
2. **Byte drift ends v4.** If any re-derived array does not hash to the S0f manifest's
   `feature_target_sha256`, v4 ends: there is no repair or substitution. Mitigation:
   - import the T-f code at `88c1a0f6` (the S0f producer's own tree) in the same `.venv`
     interpreter (Python 3.11.15, NumPy 2.2.5);
   - before writing anything, verify that the feature and reader code hashes equal the S0f data
     manifest's `current_reader_sources` (and `feature_protocol_sha256`);
   - verify every array pair before the bundle is published.
3. **Pre-freeze round-trip test.** Before S0z is frozen, build a synthetic 26-key bundle: 22
   augmented-train sources (10 old + 12 advice) plus 4 dev, each `<fts>/features` float32 `(n, 388)`
   and `<fts>/targets` float32 `(n, 2)`, with `fts` the sha256 of the feature and target bytes. Run
   M4's `read_corpus_pin` on a synthetic S0z record, then `load_arrays` with the rosters from
   `derive`, and require exact admission. Also require refusal on a missing key, a wrong dtype or
   shape, and a hash mismatch.
4. **Cost against the 300 s kill.** S0z re-reads the same 26 sources and recomputes the 12
   advice sources' features: roughly S0f's own work plus hashing and writing the bundle. Estimate
   S0z's CPU from **S0f's measured charge** in its RESULT. If S0f measures above about 200 CPU-s
   (two thirds of S0z's 300 s kill), S0z's budget must be re-assessed before its GO. At S0f's
   expected 79.46 s, S0z would be about 80–110 s, consistent with the protocol's ≈82 s.
