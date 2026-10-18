# Fresh narrow restore validation

7 October 2026. The approved single-source `restore-v2` allocation passed its
independently checked terminal close. This qualifies one CPU FLYNN profile on
this runtime for two five-control continuations under the reviewed
`restore-reproducibility-v2-candidate` comparison. It does not qualify the full
memory prerequisite campaign, paired pilot, population reproducibility, memory benefit,
learned capabilities, artwork or physical hardware.

## Measured outcome

| Check | Retained result |
|---|---|
| New owners and controls | Exactly two sequential owners, five audited controls each; no retry |
| Initial source | Both restored the frozen source SHA `c839fae1fe3d981cf4b7073970f7eb06d5738f009d6cb23f249408fd227cf6bf`; invariant and receipt bindings checked |
| Non-timing traces | Exact match: `bf05e4fe707954ab3ed9e28cbf39137c778918279228cbabef2ed4272f76c9cf` |
| Legacy complete state equality | False: only `native_data` and `native_sha256` differ; 74 of 458,761 native bytes differ |
| Candidate complete state equality | True; all other normalized typed fields/native bytes and timer counts stay exact |
| Projection | Exactly 15 proven disjoint eight-byte duration intervals, 120 bytes per copied payload; stored bytes untouched |
| Candidate complete digest | `70223db34c3e397e61d8dd5fbe26806170eed9244f60fed16f4a22a1a5d1ae46` on both sides |
| Native prerequisites / pilot / held-out | False / unattempted / unopened; `qualification_claims: []` |
| Driver / independent close | 60.080 s / 66.574 s from driver start, within the original readout deadline |
| Invocation | Pipeline and launcher exit 0; no failure flags |
| Storage at invocation end | 11,458,574 bytes across the exact three roots, below 8 GiB |

Raw native hashes remain
`3283d9e5f5a4125f0869459580c09819c40f725449aa2242b701a934b0642c18` and
`5b08d7472891e8f573ffdcba7a04993585e203185d6f5b863c3b228b9c133d75`.
The projected native hash is
`5b2158f6533c5b81045701c7a16e3c52e20da9a06a74531e0b9ff5a12a8c1a5e`.
Both post-SNP/raw/component hashes and full duration values are retained, rather
than replacing the raw result with the candidate boolean.

The driver remained provisional with `narrow_restore_passed: false`. The separate
[scientific close](restore-qualification-v2-evidence/scientific-close.json) alone
reported true after independently reconstructing sensors/controls and comparing
fresh raw traces/states. The same original readout allocation covered that audit;
no deadline was restarted. The one GNU TERM890/KILL5 watchdog covered the pipeline,
cleanup, rechecks and final publication. Both exact PID/starttime/PGID identities
were observed exited inside fresh invocation namespace `pid:[4026533098]` before
return; those are retained namespace observations, not probes in a later tool
namespace. No owner was terminated or replaced to obtain success.

## Implementation and checks

The explicit mode/schema leaves legacy diagnostic/qualification paths intact.
New admission binds the comparator, auditor, launcher, Python binary/runtime,
contract, source/assets, expected jobs and protected historical roots. It counts
run output, exact controls/logs and publication together, reserving each unchanged
native worker's complete bounded output before admission. This is a reservation
and recount, not an atomic filesystem quota against unrelated writers.

Completed-owner software fixtures exercised schema/pin/root refusal, invariants,
traces, source/post corruption, active/reused owner identity, original deadlines,
interruption, log overflow and failed publication. Independent source review found
watchdog/interruption and native sibling-budget issues; one red-to-green fix pass
addressed them. Final checks: 100 focused passed; full suite 1,015 passed,
24 opt-in checks skipped, 39 existing warnings. Those software checks are separate
from this actual asset-backed pair; skipped checks contribute no qualification.

Registration input verification took 3.431 s; registration and commit completed in
156.569 s of the fixed 180 s preparation allocation. All 479 preserved files,
including original consumed controls, were checked. The frozen
[protocol](../plans/restore-qualification-v2.md) and
[registration](restore-qualification-v2-evidence/registration.json) remain unchanged.
Original failed closes, raw comparisons and consumed markers remain intact.

## Retained evidence and reproduction

[Publication index](restore-qualification-v2-evidence/publication-index.json)
records byte-identical receipt copies and the complete fresh
[raw archive](restore-qualification-v2-evidence/fresh-records.zip): 34 files,
11,058,179 uncompressed bytes, 3,476,107 ZIP bytes, SHA256
`4eabafe50ab23c54efa1c01ae049d14d65a268f3aaf331af30be1f9d2b9cdb92`.
Packaging happened after the successful close, using its unchanged raw files;
it adds no readout, owner or qualification. Every archived member was read back
against the original file hash. Software logs, original fresh driver/candidate
comparisons, independent close, bounded stdout/stderr and consumed marker are
published alongside it. Retain the original allocated output; do not relaunch it.

For a fresh checkout with the pinned Python 3.11/MuJoCo 3.3.6/NumPy 2.2.5
software environment, verify the archive SHA above before extracting its trusted
`phase/` members into a new temporary directory. Verify every member against the
publication index. Existing `p.read_raw` and `p.trace_digest` can recompute each
five-control trace; `read_snapshot` on each initial/post SNP and
`compare_reproducibility_states` can recompute raw integrity and the candidate
comparison using source receipt IDs derived from the initial SNP. This is an
offline check of published evidence, with no physics; it does not reopen the
original expired scientific close or reproduce its current-namespace cleanup.
Actual fresh owners require a separately frozen allocation and the original
verified asset/history setup, not reusing this registration or consumed marker.

## Next gate

Prepare and review the separate eight-cell fresh prerequisite campaign for the
one selected profile (four full runs, two prefixes and two restores from the new
south prefix). The frozen narrow protocol used the shorthand "eight fresh profile
prerequisites"; it does not define eight distinct profile identities.
The narrow pair substitutes for none of those future owners and unlocks no paired
pilot. Only after all eight pass may the four-condition/six-case development pilot
begin; full matched-control development/held-out research remains later. Existing
learned puck/navigation failures and human artwork/operator gates remain open.
