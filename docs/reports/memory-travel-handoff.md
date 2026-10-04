# Memory travel-handoff amendment: implemented; native attempt stopped by storage

4 October 2026. The approved [prospective plan](../plans/memory-travel-handoff.md)
is implemented and software-verified. The single authorized native invocation
stopped on filesystem `ENOSPC` before acquisition completed. It selected no profile
and establishes neither successful travel nor a scientific route failure. R2,
paired memory benefit, R3, learned puck capability and physical/operator
qualification remain open. No retry, fitting, pilot, held-out use or merge followed.

Scientific source froze at `0f1f8ea601ad3f35472be7fb0eadcf67efc4d860`.
The earlier [acquisition failure](memory-v2-feasibility.md) and
[waypoint amendment failure](memory-waypoint-amendment.md) remain preserved.
The latter acquired both open observations and passed south/no-event, but its
south/change run lost the north exit at tick 1193, bearing −90.749°.
This travel amendment has not resolved that measured failure.

## Implemented change

Only the nonpreferred physical-side detour changes to `(.6, ±(1+d))`.
The selected 1.4 m acquisition loops, obstacles, start/goal, inspection, crossing
and exit markers remain fixed. Recomputed public route costs preserve the preferred
ordering. Legacy defaults, profiles, hashes and generated cases remain unchanged.

| Candidate, fixed order | d (m) | Preferred cost (m) | Nonpreferred cost (m) | Gap (m) |
|---|---:|---:|---:|---:|
| candidate-d25 | .25 | 5.054335509 | 5.154335509 | .100000000 |
| candidate-d20 | .20 | 5.054335509 | 5.119246573 | .064911064 |
| candidate-d15 | .15 | 5.054335509 | 5.091267197 | .036931688 |

The immutable [candidate ledger](memory-travel-evidence/candidates.json) binds all
coordinates, cases and hashes before any owner. New profile hashes, in order:

- `7faba0a56d129ea051d5c28a019964034b546923dbe49cedb3a605af84437ec3`
- `89a3f8610ddcaf12bba8e4f6bcfabaf731f37f230f91c31ba2f6d06c4b95ef91`
- `116d8be2ec7db3c04ae0d7fc699c86c609dedc98a2d4b74bb188858073527792`

All three pass the analytic geometry checks. Finite surveys now include acquisition,
travel and retreat chains: 25 transitions per candidate. They retain respectively
190,964 / 191,289 / 191,577 sampled position/heading combinations, of which
85,358 / 85,357 / 85,359 have an unsafe successor. These correlated, conditional
samples are neither probabilities nor continuous/native feasibility guarantees.
They use .05 m positions, 5° headings and legitimate visible departing arrivals;
colliding poses are excluded. Closed-gate and arbitrary continuous arrivals are
not qualified by these surveys.

The opt-in CLI is `--amendment travel-handoff`; its default still runs the previous
acquisition-loop study. Protocol/private job version 3 binds new stages, cases and
profile hashes. Packet 2, task 3, application snapshot 8 and SNP container 1 remain
unchanged. CPU FLYNN, unknown initial M, cameras/contact, 4 m/±90° sensing,
.75 m passage sampling, .35 m visible arrival and CueUnavailable remain unchanged.
No controller or sensor recovery behavior was added.

Development requires acquisition, blocked inspection, completed retreat, replanning
and goal completion. Only an independently audited declared task failure advances
to another candidate. Unknown exceptions, interrupted raw data, source/ownership
failures or resource refusal stop. Selection would freeze the profile for eight
fresh mandatory prerequisites; no development run or historical SNP substitutes.
The first mandatory failure stops, without returning to development. Even all eight
passing would not authorize a paired pilot.

## Actual one-shot attempt

Raw root in the research-phase checkout:
`runs/memory-travel-handoff-20261004T125507Z/`.

| Job | Disposition |
|---|---|
| candidate-d25 | Owner started; incomplete infrastructure failure |
| candidate-d20 | Unattempted after infrastructure stop |
| candidate-d15 | Unattempted after infrastructure stop |
| South/no-event, south/change, north/no-event, north/change | All unattempted; no selected profile |
| South/prefix, north/prefix, restore-1, restore-2 | All unattempted; no selected profile |
| Paired pilot | Unattempted by approved scope |

The first owner, `e168b54332b344028a34dc0e5c4557f3`, loaded the pinned full FLYNN
connectome on CPU. Its worker report declares 288 steps and an `OSError` at the
rename `recording/chunks/000008.tmp` → `000008.npz`, errno 28, "No space left on
device". Only **256 raw control rows are readable**. The recording manifest remains
`running`; the 288-step report is not a complete independently audited trajectory.
Acquisition did not complete, so there is no acquired SNP or travel result.

Atomic publication also failed for `supervisor.tmp` → `supervisor.json`,
`development/report.json.pending` → `report.json`, and finally
`execution.json.pending` → `execution.json`. The CLI exited 1. The canonical
execution receipt is the initial stale receipt, and the canonical supervisor still
says `running`. Their unpublished drafts retain later failure information.
No original receipt was overwritten or presented as successfully finalized.

Because owner dispatch raised before returning, the development draft contains an
empty scored-attempt list and lists all candidates as unattempted. That is incomplete
owner accounting, not evidence that no process ran. The separate
[recovery readout](memory-travel-evidence/readout-completion.json) explicitly records
candidate-d25 as **started and incomplete**, and the other two plus all eight
prerequisites as unattempted. Both the original files and drafts are retained.

The existing auditor refuses this interrupted recording with
`Unqualified acquisition infrastructure failure`. This is not an admitted task
failure and cannot justify advancing candidates. No native rerun occurred.

## Infrastructure evidence, audit and limits

Admission reported **25,511,452,672 bytes free**, above the required 10 GiB.
After the failure, `df` still reported about 25.4 GB free. The read-only
[Btrfs diagnostics](memory-travel-evidence/filesystem-diagnostics.log) show the
474.92 GiB device fully allocated, only 1 MiB unallocated and approximately
94.4% metadata usage. Allocation/metadata pressure is a plausible explanation,
but the precise cause of ENOSPC is **not established**. Reported free bytes alone
did not qualify the filesystem for sustained atomic recording. No balancing,
filesystem maintenance, evidence deletion or cache cleanup was attempted.

The unpublished terminal supervisor reports 183.77 s for its owner; the final
execution draft reports 196.48 s elapsed. A separate readout finished within the
original readout deadline: **282.41 s conservative readout, 473.14 s total**.
The fixed stage caps remain development 2300 s, prerequisites 4300 s and readout
600 s, without transfer; global cap 7200 s. One owner ran, and its exact
PID/starttime/PGID identity was confirmed exited. Source and asset identities
were freshly rechecked and unchanged.

The readout rehashed **21 original indexed files**, excluding the mutable pending
execution receipt whose final serialization changed its hash. It also retains a
fresh 23-file inventory before the readout receipt. Hash consistency preserves
partial files; it does not turn an incomplete recording into qualified raw evidence.
[Readout script](memory-travel-evidence/retained-readout.py) and
[readout log](memory-travel-evidence/retained-readout.log) record the checks.

Retained raw output is approximately **58.38 MB**, and initial publication copies
approximately **.84 MB**, below the aggregate 8 GiB allowance. A
[publication inventory](memory-travel-evidence/publication-inventory.json) records
exact copy hashes and byte accounting. Compact Git evidence includes cases/jobs,
original and pending receipts, owner/worker/manifest metadata, supervision logs,
validation and filesystem diagnostics. Camera chunks stay local. This is not a
self-contained raw replay bundle. No native restore was attempted. Full prefix
neural-state replay remains unsupported; partial raw bindings or symbolic replay
cannot substitute for it.

## Verification and review

The complete default software suite passed **915 tests, 24 skips, 39 warnings in
132.62 s**, without exclusions or partitions. The final focused suite passed
63 tests. [Exact validation command](memory-travel-evidence/validation.md),
[full regression log](memory-travel-evidence/regression-freeze.log).
Software fixtures are separate from this interrupted native study; skipped opt-in
checks remain unqualified.

A fresh independent review found a pre-acquisition terminal-proof gap and incomplete
qualification disposition on exceptional exits. Corrected regression fixtures
reproduced five failures: a missing runtime event and unrelated exception were
admitted, and three exceptional paths lost prerequisite accounting. Both valid
CueUnavailable and declared-supervisor fixtures passed. The fixes require the
matching actual terminal event/type/message/tick after packet/M replay, and retain
unattempted prerequisites or a published prerequisite report after an exception.
The one review fix pass and full suite preceded the scientific freeze. Actual
ENOSPC nevertheless prevented atomic receipt publication; the recovery readout
keeps that separate limitation visible.

## Next decision

Resolve and qualify the filesystem's atomic recording capacity before proposing
another native invocation. Preserve this partial owner, the original acquisition
failure and the prior changed-route failure. A new prospective bounded execution
contract should retain these frozen geometries unless a separately approved
scientific amendment changes them. This attempt supplies no reason to change
controller, sensing, candidate ordering or gates.

Native travel selection, eight prerequisites and deterministic restores remain
open. Paired memory benefit/R2, R3 navigation, learned puck capability, held-out,
physical hardware, operator and exhibition acceptance remain open. Main remains
`ee6bf61ea8faec02d5522c7eee30ab7cf333f29d`. This branch is for a stacked draft PR
on `research/memory-waypoint-amendment`; no merge is claimed. Repo-local author is
Aadrika Maurya <aadrikamaurya@gmail.com>; publication uses Aadrika08.
