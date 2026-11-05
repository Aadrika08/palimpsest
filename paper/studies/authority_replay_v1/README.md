# Authority-aware replay study v1

The frozen protocol defines a CPU-only, sequential study. It contains 111
accounting rows: 50 fault executions, 10 source/restored continuation pairs,
5 source replay trajectories, 40 execution-overhead conditions (10 matched sets
of four), 5 operation-cost units, and one same-host fresh-checkout run. Ticks and
replay modes are paired measurements within their declared units.

The protocol and executable implementation must be committed **before** the
first result-producing run. Freeze one clean campaign commit after all drivers
are implemented. Task 1's self-check validates contracts; it does not execute a
study, qualify a runtime, or provide paper results.

## Output ownership and failure retention

Raw campaign output belongs under the ignored `runs/paper-authority-replay-v1/`
root, with a fresh subdirectory for each driver. Drivers call
`prepare_output_root` before creating output; a non-empty destination, including
hidden files, is refused. Retained originals and the assets at
`/home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn` are read-only. Any fault
copies must live under the campaign root. Never overwrite a source recording,
snapshot, original asset, historical report, or failed repetition.

Before execution, drivers prepare/verify the full FLYNN runtime and call
`campaign_identity(repo, protocol, assets)`. It requires a clean Git checkout,
hashes runtime/study Python and configuration sources, hashes the pinned FLYNN
manifest, verifies its archive/checkpoint bytes, and verifies prepared graph
edge/mapping bytes when preparation metadata exists. Pinned CRLF archive bytes
must normalize exactly to their independently pinned upstream Git CSV bytes.
Raw mapping hashes are bound as assets and Git CSV hashes as runtime sources.
This read-only check does not prepare assets or infer that absent prepared
metadata is a working runtime. Drivers must
record their exact command and environment separately, recheck identity after
each unit, and preserve before/after hashes. An identity recheck that fails is a
retained failed unit, never permission to change a pin.

`declared_units(protocol)` is the canonical ordered expansion for drivers. Each
row contains its complete descriptor from that expansion, plus:

- `schema_version: 1`, `study_id: "authority_replay_v1"`;
- `identity`: the exact `campaign_identity` object;
- `status`: `completed`, `failed`, `refused`, `timeout`, or `incomplete`;
- `metrics`: a JSON object with finite numeric values; unavailable measurements
  use `null` and a reason, never NaN or infinity;
- command/environment/raw-output references and failure details as applicable.

The row's optional Boolean flags `silent_acceptance`, `explicit_detection`,
`correct_recovery`, and `benign_false_rejection` describe the semantic oracle.
They are independent of execution status: an explicit refusal may be correct
detection, and is never inferred to be successful recovery. A missing flag stays
unreported rather than being counted as a negative observation. The sole
declared benign control is C3; all other cases use `fault` and their same-trace
naive acceptance predicate. Numbered sibling/payload/queue variants preserve
the three distinct fixture units in the spec; driver implementation must fix
their concrete small payloads before the campaign commit.

`append_row` adds a single JSON line under an exclusive append lock, refuses a
duplicate ID, and refuses malformed/truncated existing rows. The sequential
campaign must retain one row for every declared unit, including failures,
refusals, timeouts, and units left incomplete by a stop rule. Record an explicit
reason for units stopped before starting. Do not retry or substitute a seed.
This append contract makes no power-loss/crash-consistency claim.

Stop new units at any 15-minute unit timeout, four-hour campaign limit, 512 MiB
ordinary-unit cap, 10 GiB checkout-unit cap, 16 GiB raw campaign cap, or crossing
the 6 GiB free-space reserve. Stopping never authorizes deletion or scope
reduction. These are frozen limits consumed by the drivers, not measurements of
acceptable overhead.

## Commands and analysis

Run from this worktree with the prepared main-checkout interpreter. `PYTHONPATH`
must include this worktree so imports do not use another checkout's sources:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q paper/studies/authority_replay_v1/tests
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B paper/studies/authority_replay_v1/analyze.py --protocol paper/studies/authority_replay_v1/protocol.json --self-check
```

After drivers have emitted all declared rows and saved the frozen identity:

```sh
/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B paper/studies/authority_replay_v1/analyze.py --protocol paper/studies/authority_replay_v1/protocol.json --identity runs/paper-authority-replay-v1/identity.json --rows runs/paper-authority-replay-v1/faults/rows.jsonl runs/paper-authority-replay-v1/continuation/rows.jsonl runs/paper-authority-replay-v1/replay/rows.jsonl runs/paper-authority-replay-v1/overhead/rows.jsonl runs/paper-authority-replay-v1/operations/rows.jsonl runs/paper-authority-replay-v1/offline/rows.jsonl --output runs/paper-authority-replay-v1/analysis
```

Analysis refuses missing/duplicate/undeclared units, descriptor or identity
drift, undeclared retries, duplicate JSON keys, incomplete appends, and non-finite
values. It writes deterministic `summary.json`, `rows.csv`, and `failures.json`.
Every denominator includes every declared row. The raw paired values and
failure details remain in the summary. Scalar statistics use completed eligible
rows, median, minimum/maximum, and inclusive quartiles/IQR, with sample counts.
Do not interpret the pooled execution-overhead statistics as a matched cost
estimate: the overhead driver must validate all four conditions' action/tick/
final-state agreement, set `timing_eligible: false` for unmatched sets, and
derive condition-specific paired comparisons from the retained rows.

Execution-overhead final-state matching excludes recorder source-run/event-prefix
identity and only MuJoCo `timer.duration` elapsed wall-clock telemetry. It decodes
a private native-data copy, zeros only those durations and recomputes the native
hash. All RNG, integration, controller, observation, application, physics, solver
and other serialized cache state remain included. The live engine and original
full snapshot are unchanged. Each condition retains `final-raw.snp`,
`final-normalized.snp`, raw/matched native and final-state hashes, component/RNG
digests and an explicit normalization descriptor. These files are written after
the measured tick window, within the same output budget. This comparison rule
is specific to execution overhead and does not alter snapshot/replay validation.
Open and close times are reported separately from steady-state wall/tick.

The operation-cost driver consumes only the full background-plus-storage replay
source, never a null-writer source. No significance test or cost pass threshold
is preregistered.

The planned operation-cost invocation uses `overhead.py --kind operations
--replay-root REPLAY_ROOT`; `--kind operation --sources REPLAY_ROOT` remains an
alias. Both read the completed replay descriptors at
`REPLAY_ROOT/seed-{seed}/row.json`, matching the repeatability driver's actual
unit directories.

Only compact summaries, sanitized fault traces, identities, commands, failures,
and raw-tree inventories are committed after source-bound verification.
Generated LaTeX consumes that compact evidence separately. A fresh checkout on
this host is **same-host clean-checkout evidence**. Independent machine/operator
reproduction remains an external submission gate.


### Pre-execution resource amendment (2026-11-05)

Before scientific execution, preparation measured the locked local Python
environment at about 7.2 GiB logical size (torch about 1.7 GiB and NVIDIA
dependencies about 4.3 GiB). The original 2 GiB offline cap could not contain
the required fresh-checkout environment. The authorized amendment raises only
the offline logical inventory cap to 10 GiB and aggregate logical inventory cap
to 16 GiB. All 111 descriptors, seeds, conditions, 512 MiB ordinary-unit cap,
900-second unit timeout, four-hour campaign deadline and 6 GiB physical free
reserve are unchanged. No scientific result preceded this amendment.

Cached installs may use hardlinks/reflinks, so logical inventory and physical
allocation differ. Offline admission records available space and the configured
cache/link policy, requires the 6 GiB actual free reserve plus 512 MiB headroom,
and actively monitors actual free space and the 10 GiB logical inventory cap.
It does not reserve 10 GiB of physical space up front. Installer/native uv/npm
output is polled, not protected by a strict prewrite filesystem quota. Crossing
the free-space, logical-output or time boundary stops coordinator-owned processes
and later phases; observed failures and partial rows remain retained. Actual
link mode is not assumed from the configured tool default.

## Recovery revision 2

The retained first attempt exposed a benchmark bug when seed 1 reached a goal at tick 199. Revision 2 measures sustained throughput across normal episode endings, explicitly resetting to the same declared seed before the next requested tick. Its 20 warmup and 200 measured ticks are unchanged; measured wall time includes resets and rows retain reset count, reason, and timing. Failed or stopped owners are never reset. Ordinary scientific failures remain ineligible and do not halt unrelated units; resource and identity boundaries still stop execution. `recovery-amendment.json` binds the original attempt, unchanged scientific variables, shared absolute deadline, and reduced recovery cap (13 GiB plus the retained first attempt under the original 16 GiB total). Revision 1 protocol files remain loadable for archival analysis.
