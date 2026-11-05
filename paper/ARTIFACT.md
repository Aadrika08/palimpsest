# Authority-aware replay artifact

The artifact tests a domain-semantic contract, not controller quality. Its
predeclared, committed-then-frozen protocol lives at
`studies/authority_replay_v1/protocol.json`; drivers and pure analysis live next
to it. See the study README for commands and output schemas.

## What the units mean

| Evidence | Declared units | Scope |
| --- | ---: | --- |
| Fault/challenge matrix | 50 | Actual CPU FLYNN/lab faults plus production-interface custody/publication/resource fixtures |
| Continuation | 10 | Seeded source/restored pairs, 8-prefix + 100 continuation ticks |
| Replay | 5 | Seeded trajectories with branch/playback/action/policy conditions |
| Execution overhead | 40 invocations / 10 sets | Null/synchronous/background/background+storage, fresh process per condition |
| Operation cost | 5 | Full retained RQ2 sources; capture/save/read/restore and replay costs |
| Offline workflow | 1 | Full FLYNN, same-host clean checkout; no second-machine claim |

Ticks are repeated observations within a unit. Fixed seeds are engineering
repetitions; seed 0 appeared in disclosed development checks. No held-out or
population inference follows. All failed/refused/timed-out/incomplete units stay
in declared denominators; the protocol does not allow replacing them.

## Evidence custody and analysis

### Retained initial attempt and recovery amendment

The initial frozen campaign at `d8658dda3fca37bb43b6dafc909114279f706f11`
accounted for 111 descriptors: 69 completed, one failed, and 41 incomplete.
Overhead seed 1 reached its navigation goal at tick 199; the benchmark then
requested another step without resetting the terminal episode. The driver also
misclassified the ordinary `ValueError` as a resource boundary. This is a
benchmark failure, not evidence that recording or continuation failed.

`evidence/authority-replay-v1/initial-attempt/` retains the exact summary,
manifest, inventory, fault traces, failure report, original protocol and stderr.
Its `retention.json` binds their hashes and the original raw-output location.
The summary SHA-256 is
`b9f7c43b1c5ba9015a2f45361671eaec7a31065220d004871b83a8bc3b8679e9`.
The complete original raw tree remains retained locally.

The recovery amendment explicitly resets normally ended episodes using the same
declared seed while retaining the fixed 20 warm-up and 200 measured ticks.
Measured reset work is included in throughput cost. It also preserves typed
worker failures so ordinary scientific failures can remain ineligible without
silently cancelling later units. This measures sustained engineering throughput
across episode boundaries. Production engine, controller, seeds, tolerances,
fault oracles and declared scope stay fixed. The new campaign has a separate
execution/protocol identity and fresh output root; it does not replace initial
rows.

The first recovery launch at `6c129516742d240075a95565bcd308ef1d313bb0`
stopped when a late worker fix changed source identity during execution. Its
manifest, emitted rows, unexecuted descriptors and supervisor records are retained
under `evidence/authority-replay-v1/interrupted-recovery/`; it is excluded from
scientific aggregation. This was an orchestration failure. Final execution uses
an isolated checkout at `cc57edf9f70323926237d887d766627d8c9cdd42`, protocol
revision 3, SHA-256
`570a4afe8179425bb2b25b86364470af34052ecc4929b74f207c279076728860`.
Revision 3 preserves the amended execution semantics and tightens the final
output cap to 12 GiB. Original (3,076,227,528 bytes), interrupted recovery
(461,457,713 bytes), and final cap total 16,422,587,129 bytes, below the original
16 GiB budget (17,179,869,184 bytes). All launches share the original absolute
deadline, Unix `1793860506.2223496`. Raw outputs from every attempt remain local.

Retain the frozen execution commit, protocol hash, effective configuration,
commands, source/asset identities, raw-tree inventories and hashes, compact
rows, sanitized fault traces, and analysis output. The report commit may differ
from the execution commit and must not replace it in provenance.

A weak predicate accepting a trace is not automatically a false claim. Inspect
the named claim, observed true/false/unknown truth, evidence and temporal scope.
B1 and E2 can be successful valid challenges. R1/R2 are study-level replay-label
guards; they are not production mislabel-refusal measurements.

Scientific-array comparisons require finite values and the protocol's frozen
exact/tolerance rules. Execution-overhead matching alone excludes recorder
source/event-prefix identity and canonicalizes MuJoCo `timer.duration` on
private decoded copies. Original snapshots and raw hashes remain retained, all
RNG/scientific state remains in the match, and replay validation is unchanged.
An unmatched seed retains all four rows and is excluded as a whole from timing
summaries. Open/close costs are separate from measured execution tick time.

The separate post-run `scripts/audit_authority_state.py` checks retained raw and
normalized cost snapshots against the raw inventory and reported state digests.
It scans numeric container arrays/scalars and exposed native MuJoCo/model views
for finite values, then independently reproduces the recorder-field removal
and timer-only normalization. This establishes evidence about retained states;
it does not add a benchmark-time guard. Run after the campaign finishes:

```sh
python -B paper/scripts/audit_authority_state.py \
  --summary RAW_ROOT/analysis/summary.json --raw-root RAW_ROOT \
  --output paper/evidence/authority-replay-v1/cost-state-audit.json
```

The output is exclusive: an existing audit is retained. Its summary and inventory
hashes distinguish the exact inputs. The S1 table separately reports absolute
velocity-command and heading-angle errors, preserving their coordinates rather
than treating a combined numerical discrepancy as a physical distance.

## Observed completion and checkout gap

### Worked source trace and recorded configuration

`execution-configuration.json` records the observed CPU/governor, package,
thread, renderer, controller and scenario settings used in the manuscript.
`worked-chain/chain.json` joins `replay/0` and `operation_cost/0` to their actual
source run. The directory retains that source's manifest and complete event
stream plus the two relevant snapshots, with exact SHA-256 values.

The tick-8 snapshot contains the applied `edit` receipt (tick 0, revision 1) and
the digest of the first 30 source events; that prefix digest was recomputed from
the retained stream. Its branch compares 92 remaining ticks. Action and policy
replays use the separate initial snapshot and compare 100 source ticks, with
their policy-execution flags false and true respectively. The completed source
has 100 published ticks, independently decoded by its operation-cost unit.
This is one successful evidence join, not a combined-fault campaign or proof.

The final campaign accounted for all 111 descriptors: 110 completed, with the
declared offline checkout unit incomplete. Its conservative aggregate admission
required the full 10 GiB unit allowance in addition to existing output, exceeding
the final campaign cap. No checkout worker was launched for that unit. All 40
cost conditions matched; the separate retained-state audit passed all 40 pairs.

`offline-followup/` preserves a separately supervised operational check using the
same frozen runtime, original deadline, actual cumulative inventory monitoring
and original 16 GiB total cap. It does not replace the incomplete scientific
row. Fresh Git and pinned upstream checkouts succeeded. `uv sync --locked
--offline` then failed because the exact `torch==2.9.0` PyPI wheel was not cached.
The isolated network remained unavailable, and no new-environment FLYNN run
occurred. Runtime identity and earlier campaign metadata stayed unchanged.
This establishes the cache-dependent packaging gap, not a controller failure.
The exact wheel URL is in the retained stderr and locked requirements.

The next reproduction attempt needs the permitted locked dependency cache
prepared first and a separately bounded fresh output directory. Do not relabel
this failed follow-up or the incomplete original unit as successful. Independent
machine/operator reproduction also remains open.

Raw campaign outputs are local ignored artifacts. Compact evidence and the
frozen protocol support review without silently redistributing third-party
assets. Check `THIRD_PARTY_NOTICES.md` and source terms before public deposit of
checkpoints, graphs, snapshots, or derived arrays. No public archive or permissive
redistribution status is implied by local availability.

## Verification and remaining gates

The integrated generator must reject identity/hash drift, missing/duplicate
rows and non-finite results rather than supplying expected values. Rebuild the
paper, check generated-file freshness and citations, inspect all PDF pages, and
check claim wording against the actual compact summary. A successful source
build is not a rendered-output or scientific-evidence review.

Second-machine/operator reproduction, public archive/checksum readback,
licensing, final authorship/disclosures, venue formatting and submission remain
separate gates. Controlled subprocess interruption and writer failures do not
establish power-loss recovery or hostile-host security.
