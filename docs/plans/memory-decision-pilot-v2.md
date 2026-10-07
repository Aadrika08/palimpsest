# Proposed six-case memory decision development pilot

8 October 2026. **Proposed, unapproved and unstarted.** This document requests a
separate implementation and finite execution allocation. The approval for
[memory-prerequisites-v3](memory-prerequisites-v3.md) authorized eight fresh
prerequisite cells on one profile; it did not authorize this bridge or pilot.
No implementation, registration, owner, decoder, new readout or pilot follows
from writing this proposal.

## Evidence that permits this proposal

The authoritative receipt at
`runs/memory-prerequisites-v3-20261007T183709Z/scientific-close.json` reports
`native_prerequisites_passed=True`, `candidate_restore_pair_matches=True` and
`trace_equal=True`, with all eight cells complete. Its legacy
`restore_pair_matches=False` remains visible: the legacy comparison found 67
different native bytes. The candidate contract excludes exactly the registered
15 float64 duration intervals, 120 bytes per side; its equality does not replace
legacy equality or permit new exclusions. The close reports immutable inputs and
raw evidence unchanged; the completed campaign preserved 853 prior files.
The admitted receipt SHA-256 is
`6e33c0c5fd0ec6a407588e6d7f7240f79964706e5cdd638a351bbe5a0b433b76`;
its registration SHA-256 is
`8567bc446b265c36a3063dc5d3fcb2cf354bcd2a3684ec4a068e6c98007f12f9`.
That registration pins implementation commit
`351eab266ed23d4707986091c57b6223e8cb7612`; the executed checkout head was
`61d0116bf1d3bbd8bb581ec532c4de6dc1d05698`. Its complete `source_identity`,
assets/history inventories and runtime are the reference for the future source
bridge; a new pilot driver hash must be recorded as an explicit derivation.

This is one selected profile, source and host, with correlated development
evidence. Keep `r2_complete=False`, `qualification_claims=[]` and held-out unused.
The old contract, consumed registration, SNPs, native bytes, raw records, receipts
and failed studies remain immutable. This proposal neither re-scores them nor
reinterprets the failed legacy hypothesis.

## Fixed experiment

Reuse the selected .25 m travel profile
`7faba0a56d129ea051d5c28a019964034b546923dbe49cedb3a605af84437ec3`.
The prerequisite worker protocol is
`ae7c4014868d5ade9928cfdda2729c3562df38404a32f7c4b7980d4cbb567a5d`.
Its scope is prerequisites only; a future pilot must have a distinct registered
opt-in protocol, rather than claiming this hash already admits condition owners.
Preserve the selected 1.4 m acquisition/retreat loops and (.6, ±1.25) m
nonpreferred detour. No profile selection, geometry adjustment or extra families.

Use exactly the existing `scripts/memory_decision_pilot.py::pilot_specs` cases,
in their existing order, with only the selected profile attached:

| Spec ID | Seed | Regime | Kind / preferred side | Exact world case ID |
|---|---:|---|---|---|
| `local_cue-south` | 401 | `local_cue` | change / south | `memory-v2-00000191-local_cue-change-0` |
| `local_cue-north` | 401 | `local_cue` | change / north | `memory-v2-00000191-local_cue-change-1` |
| `paired_cue-south` | 401 | `paired_cue` | change / south | `memory-v2-00000191-paired_cue-change-0` |
| `paired_cue-north` | 401 | `paired_cue` | change / north | `memory-v2-00000191-paired_cue-change-1` |
| `local-null` | 402 | `local_cue` | null / south | `memory-v2-00000192-local_cue-null-0` |
| `paired-no-event` | 403 | `paired_cue` | no-event / north | `memory-v2-00000193-paired_cue-no-event-1` |

Each change case moves the preferred-side gate after acquisition. The null
changes the cue with no closure; no-event changes neither cue nor gate. Preserve
`make_case`'s IDs, full case/graph hashes and public cost ordering; register all
six resolved cases before any owner. These six variants are not six independent
samples, and prerequisite seed-400 recordings are not pilot observations.

For each case, acquire once from unknown M with CPU FLYNN, no U, real cameras
and contact sensing. Both open observations and return to `await_decision` are
mandatory. Retain one fresh pre-event SNP and its invariant; fork all four
continuations from those exact bytes, in order `own`, `swapped`, `no-U`, `sham`.
Maximum six fresh acquisition owners plus 24 continuation owners: 30 total.
No historical SNP, synthetic prefix, cross-case source or extra restore owner.

Keep the frozen v1 historical rule resources and provenance:

| Resource | History file under the registered history root | SHA-256 |
|---|---|---|
| local | `runs/m5-acquisition-batch-20261002/local_cue-history.json` | `016c5b5e9472b116d065fb922b32d64089db6e27839aec09d751238f8ce7ffc1` |
| paired | `runs/m5-acquisition-batch-20261002/paired_cue-history.json` | `64628e37cc6e861194f810baa92926eba8f57260047cdd8ad320a4601023d213` |

`mapped_histories` makes own/sham use local U in local-cue cases and paired U in
paired-cue cases; swapped uses the other artifact. No-U uses the existing empty
U. Reuse `selector_for`/`u_for` and the fixed limit-one selectors. Do not relabel
v1 histories as fresh v2 acquisition, refit U or use pilot outcomes for selection.

Preserve native/model/RNG/observation/world/M/E/supervisor/command state across
restore and selector substitution, apart from the existing declared recorder
and selector/U substitutions. Do not broaden `condition_state` normalization.
Arm event at boundary+1 and decision at boundary+2; no-event has no event tick.
Packet 2, task 3, application 8 and SNP container 1 remain fixed. All conditions
use one unchanged categorical policy: exclude observed-blocked routes, prefer
observed-open to uncertain, then public route cost and lexical ID; inspect before
crossing, retreat and replan after blocked evidence.

Keep range 4 m, ±90-degree FOV, .75 m passage sampling and .35 m visible arrival;
missing selected bearings are `CueUnavailable`. CPU FLYNN alone issues scored
actions through the existing bearing bridge. No private pose, ground-truth bearing,
manual rescue or planner input. Retain 1,200 acquisition / 900 continuation /
2,100 total ticks, .02 s control, two attempts, 150 inspection ticks and 300
waypoint ticks. No tolerance, task threshold, policy or sensor change.

## Prospective admission bridge and source freeze

The current `validate_feasibility` accepts only a version-1 `feasibility` report
with the legacy protocol and same global byte phase. Current travel worker
allocation rejects pilot/condition jobs. The public pilot CLI therefore cannot
consume the v3 close or run this profile as proposed.

If separately approved, add the smallest explicit v3-prerequisite admission and
selected-profile pilot seam to the existing driver/worker/auditor; reuse the
existing Engine, supervisor, recorder, snapshot, StorageBudget and containment.
Preserve default/legacy v1 validation and rejection behavior. Do not fabricate a
legacy feasibility report, change the old protocol scope or bypass admission.
The new bridge must fail closed before model import, output allocation or any
native owner unless all of the following hold:

- The exact authoritative v3 close and registration hashes, eight ordered
  jobs/cases, selected profile, prerequisite protocol and candidate state contract
  match. All mandatory/raw/trace/candidate/cleanup/input-integrity checks pass,
  no owner or cell is missing, and the failed legacy result remains explicit.
- Rehash the retained prerequisite receipt, inventories and indexed evidence;
  admit this separate immutable evidence root only through the new opt-in bridge.
  A driver result alone, copied success flags or a consumed marker cannot qualify.
- The future source derivation identifies the admitted prerequisite bytes and
  every deliberate pilot/admission/auditor change. Preserve native scientific
  source, geometry, controller, task/sensor contracts, assets and histories.
  Any unregistered difference refuses admission; a scientific change requires a
  separate decision, not automatic reuse of the prerequisite result.
- Freeze implementation commit, exact bridge/driver/launcher/worker/auditor/
  comparator hashes, protocol, six cases, histories, assets, runtime and complete
  protected-evidence inventory in a new committed machine registration. Bind
  the 30 owner slots, resource reservation, output/control/publication roots and
  distinct exclusive marker. All new output roots must be absent.

Before registration, run local software checks for the bridge's positive and
negative admission, default compatibility, exact case/profile/source binding,
paired invariants, finite owner accounting and independent publication; obtain
independent branch review. Prepare independent close before native launch. These
are future implementation requirements, not software checks run by this proposal.

Pin the admitted runtime: Python 3.11.15 executable identity, MuJoCo 3.3.6, NumPy
2.2.5 and Torch 2.9.0 CPU; one numerical thread, EGL, CUDA disabled. Recheck the
actual executable, versions, source/assets/history and real-user exclusive lease
at launch. Fresh profile-specific geometry checks may refuse admission; they
cannot edit geometry or establish native feasibility of the six new cases.

## Requested single finite allocation

| Allocation | Seconds | Scope |
|---|---:|---|
| Separate nonnative registration preparation | 180 | integrity/resource checks, registration and its commit |
| One pilot owner stage | 6,000 | admission, six acquisitions, 24 continuations, inline audits and owner cleanup |
| Independent close | 600 | final readback, exact cleanup, input rechecks and authoritative publication |
| Total additional nonsoftware allocation | 6,780 | one preparation and one 6,600-second original-clock invocation |

This explicitly requests new time; no unused v3 time transfers. Software
implementation/checks precede the finite preparation allocation and cannot start
native work. Within the invocation, the owner deadline is origin+6,000 s and the
global deadline is origin+6,600 s. The independent close deadline is
`min(origin + 6600, close_started + 600)`. Starting close early does not extend
its 600-second allowance or rebase either deadline. No stage transfer or retry.

Reuse documented 360/370 s internal/external bounds for each fresh acquisition
and 120/130 s for each scored continuation. Their external sum is
`6 × 370 + 24 × 130 = 5,340 s`; reserve 10 s per owner admission for cleanup,
`30 × 10 = 300 s`, leaving 360 s of the 6,000 s for admission/inline audits.
The old 4,200-second pilot stage cannot cover that bound. Each owner is admitted
only when its complete external bound plus cleanup fits the remaining original
stage time; auditing overhead can still leave later cells unattempted.

The completed v3 execution recorded worker `wall_seconds` of approximately
90.60–93.66 s for its two prefixes and 100.70–140.54 s for its four full runs;
the authoritative close was about 898.37 s after launcher origin. Supervisor
elapsed seconds are separately reported in the campaign report. These measurements are a reference on this
profile/host, not observed pilot timing or a guarantee for seeds 401–403, paired
cues or 900-tick branches. The proposed allocation is based on documented caps,
not an extrapolated success threshold. An owner reaching its wall cap is incomplete
infrastructure evidence, never a scored task failure.

One CPU native owner at a time, maximum 30, one registration/invocation, zero
retries, zero corrective studies and zero fallback profiles. Retain exact
PID/starttime/PGID ownership and ancestor process-group containment. Apply
whole-pipeline TERM at 6,590 s, KILL after five seconds and ancestor hard KILL at
6,600 s; a forced kill fails the close. Scientific publication must finish inside
the original clock. Later prose/Git work cannot add scientific analysis.

Keep the inherited **8 GiB aggregate hard cap**, 10 GiB initial free-space floor,
2 GiB continuing floor and 64 MiB headroom across every new output, control,
publication and documentary-copy root. Retain 512 MiB acquisition recording /
384 MiB continuation recording / 16 MiB SNP / 1 MiB per stdout, stderr and control
envelope. Do not raise an envelope cap to conceal duplication. Reserve/check the
next owner's complete recording+SNP/log/control bound within the aggregate budget
before admission; preserve partial output on refusal.

At the recorded v3 close, free space was 14,579,466,240 bytes and its phase used
1,335,252,990 bytes. This historical observation does not establish future
headroom. Before registration, measure existing retained recording/metadata sizes
without generating new native data and freeze a finite projected byte ledger for
six acquisitions, 24 continuations, SNPs, logs, close and copies. Treat any
projection as an estimate. Verify a bounded 8 GiB reservation plus the 2 GiB floor
and 64 MiB headroom is available under the shared lease; recheck actual free space
and bytes before every owner and close. Failure refuses/stops this allocation,
without deletion or filesystem maintenance.

The per-recording theoretical maximum alone is
`6 × 512 + 24 × 384 = 12,288 MiB`, above 8 GiB. Retaining those individual ceilings
and the 8 GiB aggregate deliberately does not guarantee all 30 owners fit; actual
bytes govern admission. Do not lower recording/tick/evidence requirements, drop
cameras, discard failures or duplicate raw into Git to force completion. If the
finite preflight ledger cannot support a credible bounded reservation, stop and
request a separately reviewed resource decision; do not silently increase caps.
Account quota is unknown when first-party telemetry is unavailable.

## Audits, result and stops

Reuse independent raw checksum/count, source/controller/native-owner, snapshot,
packet/visible-arrival, policy-binding, M/selector, commitment and terminal audits.
Retain exact terminal `CueUnavailable` replay and declared supervisor failure
proof for the new protocol; unknown exceptions or missing proof are infrastructure
failures. The common source SNP must match all four registered source hashes and
preserved invariants. Full tick-zero native neural prefix replay remains
unsupported; acquired-snapshot continuation replay is the supported scope.

For each complete pair require own/sham exact non-timing action/camera/raw trace
identity and equal goal, tick, path, commitment and post-event-sample fields.
Require first commitment before fresh post-event passage evidence. Reconstruct
public costs and categorical decisions independently, and prohibit separator
bypass. Report the existing mechanism predicates without guaranteeing them:

- M-caused route difference: own/no-U first routes differ, retained commitment
  inputs differ and the preserved starting invariants agree.
- Closed-route cost: in a change case no-U first commits to the blocked route,
  completes retreat/replan and has a longer scored path than own.
- False-targeting cost: in the null case own has a longer scored path than no-U.

Keep `mandatory_pass` separate from `mechanism_observed`; the latter requires at
least one admitted change-case M difference, one closed-route cost and the null
false-targeting cost, as in the existing pilot. An absent mechanism is a result,
not permission to tune, rerun or replace a case. Publish per-case/per-condition
success, capped ticks, scored path length, inspections, replans, unavailable cues,
commitments, bypasses and every failure/incomplete/unattempted disposition.
Every independently audited failed continuation receives the full 900-tick
score; infrastructure interruptions receive no manufactured task score. Preserve
all cases and failures, with no successful-only or independence analysis.

Stop later owners after the first acquisition failure, invariant/identity/raw
failure, own/sham or opportunity failure, unknown exception, unproven terminal,
resource refusal, deadline exhaustion or cleanup failure. A completely audited
task failure may remain in its pair with the fixed score; it is never replaced.
An incomplete pair stays incomplete. Independent close alone may publish the
pilot result after final inventories, registered-slot accounting, same-namespace
owner-exit proof and input rechecks. Preserve every available partial artifact
when close fails; no late authoritative success rescue.

Even a complete mechanism-positive pilot establishes only correlated exploratory
behavior under this one selected simulation profile and frozen historical U.
It does not establish R2 benefit, generalization, biological learning or physical
qualification. No full nine-condition study, held-out data, fitting, puck/navigation
repair, hardware/operator/exhibition run, CI, merge, cloud or purchase is proposed.
Any follow-on requires its own evidence review and approval.
