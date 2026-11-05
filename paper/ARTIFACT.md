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
summaries. Open/close costs are separate from steady-state tick time.

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
