# Memory prerequisites v3: fresh eight-cell scoped pass

8 October 2026, local date; native receipts are dated 7 October UTC. The approved
fresh campaign completed once. Its independent close reports
`native_prerequisites_passed=True`: all eight selected-profile cells were audited,
both restores preserved acquired invariants, their non-timing traces match, and
the frozen timer-aware candidate state matches. **Legacy raw state does not
match: 67 native bytes differ.** Raw SNPs and hashes remain unchanged.

This finishes the selected-profile prerequisites, not the memory benefit study.
`r2_complete=False`, `qualification_claims=[]`, pilot
`unattempted-by-scope` and `held_out_used=False` remain explicit. The failed
[v2 campaign](memory-prerequisites-v2.md) remains failed. No retry, corrective
study, pilot, held-out access or physical operation followed.

## Frozen entry and actual allocation

The [approved plan](../plans/memory-prerequisites-v3.md) preserves the eight
ordered seed-400/local-cue specs, native worker, observations, geometry, thresholds
and candidate contract. The [receipt repair](memory-campaign-receipt-size.md)
removes redundant driver audit copies; the independent close still performs
full raw/source/state/trace audits. The 1 MiB envelope limit is unchanged.

- Source/software implementation: `351eab266ed23d4707986091c57b6223e8cb7612`;
  committed registration and executed head:
  `61d0116bf1d3bbd8bb581ec532c4de6dc1d05698`.
- Registration: 333,044 bytes, SHA
  `8567bc446b265c36a3063dc5d3fcb2cf354bcd2a3684ec4a068e6c98007f12f9`.
- Profile: `7faba0a56d129ea051d5c28a019964034b546923dbe49cedb3a605af84437ec3`;
  prerequisite worker protocol:
  `ae7c4014868d5ade9928cfdda2729c3562df38404a32f7c4b7980d4cbb567a5d`.
- FlyGym checkout/gitlink: `8d964599119b420de67ee259434d273651a1a76d`.
  Registration pins assets, histories, executable and complete source dependencies.
- Runtime: Python 3.11.15, MuJoCo 3.3.6, NumPy 2.2.5, Torch 2.9.0 CPU;
  one numerical thread, EGL and CUDA disabled.
- Exactly one registration and invocation, eight owners, zero retries/corrective
  studies. Registration preparation took 4.556599984 seconds; its outer command
  took 4.665512165 seconds and returned 0. Its commit completed within the separate
  180-second preparation allocation. The preparation receipt transcribes that
  actual tool result after exit.
- Original-clock invocation caps: 4,300 seconds for admission/owners/inline audits,
  at most 600 for readout/cleanup/rechecks/publication, 4,900 total. Independent
  close occurred **898.369816433 seconds from the launcher origin**, with
  492.450830622 seconds left in the readout window. This is close timing, not an
  invented exact parent-exit duration. The parent subsequently returned 0;
  pipeline/native exit codes are 0 and `failures=[]`.
- Driver readout started 790.820647055 seconds after origin; its total was
  841.378004294 seconds, including 50.557357780 seconds of driver readout.
  The driver remains non-authoritative: `prerequisites-provisional-pass` with its
  own `native_prerequisites_passed=False`. The independently published close is
  the authoritative scoped pass.

The frozen plan and pre-entry software receipts retain their original
"not started" statements as historical snapshots. This report records execution;
neither the registered contract nor historical evidence was edited afterward.

## Independently audited cells

All eight have `raw_audit_pass=True`, acquired beliefs, completed supervision and
return code 0. Full runs/prefixes change memory, so `invariants_preserved=False`
there is expected. Only the two restore continuations require that flag.
Owner seconds below are supervisor elapsed time.

| Cell | Run ID | Result | Continuation controls | Owner seconds |
|---|---|---|---:|---:|
| south-no-event | `02d04b2c6d45454aafe78f2bd8785514` | acquired, goal | 196 | 101.30 |
| south-change | `c2acd119223b4cb68884baa13dbdedf8` | acquired, goal, blocked first commitment, retreat, one replan | 541 | 132.76 |
| north-no-event | `759b84578ddc4925b36763725a477daf` | acquired, goal | 195 | 105.83 |
| north-change | `0ffc6e231d7645ba8c2d2bda87bb184a` | acquired, goal, blocked first commitment, retreat, one replan | 565 | 141.85 |
| south-prefix | `e91cf0a8efbe4712b01a0a469991fcb8` | acquired and paused; goal not required | 0 | 94.56 |
| north-prefix | `9273115c0587491c8427087d09b723cb` | acquired and paused; goal not required | 0 | 91.34 |
| restore-1 | `e0277617fcd64bc0b1314f723b45b30f` | acquired invariant preserved | 5 | 23.32 |
| restore-2 | `4c41bdc2007940a9bbade1f65add77b9` | acquired invariant preserved | 5 | 23.22 |

All six fresh acquisition runs used 727 controls. The two repeats restore that
acquired state; they do not reacquire it. Total new recorded controls are 5,869,
not an independent statistical sample count. Evidence remains correlated,
development-only, on one profile/source/host.

The fresh south-prefix supplies both repeat owners. Its 1,559,948-byte source
SNP has SHA
`c426c119eb73028626d7fb5e393708dd476cf71b96d1397bc154ba62d528f4a3`,
invariant `3ff280e5c558af603a08a150af2c2cb916c2352e892dc92a14e600b5311405a9`.
The exact producing job/path and all 727 acquisition receipt IDs are retained in
[fresh-source.json](memory-prerequisites-v3-evidence/fresh-source.json).
Both independent source/control bindings passed; no historical source substitutes.

## Exact restore comparison

The legacy comparison differs only at `native_data` and `native_sha256`:
67 of 458,761 native bytes differ. Raw native SHA values remain
`ecdd68c7eba61d9972908e581052cade4fdacee6e648ef98518a9605322ad106` and
`e79b489db41e9d5418a789378beb78e16d533462868766542546a86361e74498`.

The candidate projects copies only: exactly 15 registered disjoint float64
profiling-duration intervals, 120 bytes per side. All other native bytes, timer
counts and typed state fields remain exact. Both projected native hashes are
`439012bbf14a87a2137107af12fb04e44e9548c76326fec0a58d164ca2427c87`;
both candidate digests are
`3a0d28f1107800abcad69775da6ad1357d7dce48994acec7de5d2ed1dbf7fdad`.
Both non-timing action/camera traces have digest
`f94b58687a84957a4034b9d5ee904ae465539b951696ccddc66dbd0fd93a7869`.
Candidate equality does not turn raw inequality into equality or broaden exclusions.

See the complete [authoritative close](memory-prerequisites-v3-evidence/scientific-close.json),
including the intervals, diagnostics, independent owner audits and final
`immutable_inputs_and_raw_evidence_unchanged=True` attestation. The independent
auditor's `new_native_owners=0` and `physics_steps=0` describe readout only;
the campaign itself ran eight native owners.

## Software verification and review

Before registration, focused tests passed 64 in 25.64 seconds; three preparation/
dependency tests passed in .32 seconds. The initial red check failed twice in
.27 seconds because v3 admission and launcher were absent. The required full
suite passed **1,082 tests**, with 24 skipped and 39 warnings, in 230.58 seconds,
shell exit 0. Native/model opt-ins were absent; skipped checks are not native
proof. Verbatim logs and invocation metadata are in
[software evidence](memory-prerequisites-v3-software-evidence/summary.json).

Independent whole-branch review found no Critical/Important issue. It checked
versioned schemas/paths, dependency pins, eight-cell/source binding, unchanged
gates, original-clock containment and cleanup/invalidation. Its minor limit:
the realistic envelope regression is representative, not a universal payload
size proof; larger legitimate reports still fail closed at 1 MiB. The actual
driver receipt is 590,733 bytes and independent close 532,583 bytes. No cap was
raised. Source/prose checks passed; original red logs retain original whitespace.
Account quota telemetry and a working-set binding were unavailable.

## Cleanup, retained bytes and review path

Original cleanup records all eight exact PID/starttime/PGID identities already
exited, `matching_owner_exited=True`, with no required kill. An independent
post-exit review observed all eight PID paths absent in the recorded namespace.
All 853 protected
prior files across 15 roots were preserved, including the original failed v2
output/control/publication. Invocation storage measured 1,335,786,375 bytes;
post-exit packaging measured 1,348,113,121 bytes across the same three phase
roots before its final publication receipt and subsequent prose/review files.
The 8 GiB aggregate limit, free-space floors and 64 MiB headroom were unchanged.

The [publication](memory-prerequisites-v3-evidence/publication.json) and
[288-file byte index](memory-prerequisites-v3-evidence/publication-index.json)
preserve exact closed bytes. The [97-member ZIP](memory-prerequisites-v3-evidence/retained-records.zip)
is 11,058,672 bytes, SHA
`760815786949d8d31f6685af253f1276e39687d6f8d22c8d7315e43c33165be9`.
Packaging read back every member. SNPs, events, worker/job/owner/supervision
receipts, registration, original marker, control/log bytes and publication
sources are included. Canonical copied receipts retain their original bytes.
Independent retention review matched all 97 members, all 288 indexed files and
all 853 unique protected originals by size/SHA, verified exact owner/source/cell
bindings and original-clock arithmetic, and found no defect. Its
[readback receipt](memory-prerequisites-v3-evidence/retention-review.json)
records byte/metadata checks only, not a new scientific grade. A separate final
documentation review found no Critical/Important issue; its two minor pilot
clock/timing-label clarifications were applied before publication.

The complete local raw root is
`runs/memory-prerequisites-v3-20261007T183709Z` in the
`research/memory-prerequisites-v3` worktree. **189 raw NPZ chunks and zero-byte
storage locks remain local and are excluded from the ZIP. It is not a
self-contained raw replay bundle.** A fresh checkout can inspect published
receipts and archive bytes; their hashes do not supply the omitted raw inputs.
Do not rerun the consumed preparer, launcher or auditor for archive review.
Post-close work is byte copying/hashing/ZIP readback and reporting only; no
scientific decode, state comparator or late grading occurred.

## Next decision

This pass permits preparation of the separate
[six-case/four-condition pilot proposal](../plans/memory-decision-pilot-v2.md).
Its admission bridge, new protocol, registration and 30-owner execution are
unapproved and unstarted. The current public pilot validator cannot directly
consume this v3 prerequisite close. Proposed allocation: 180 seconds preparation
plus one 6,600-second invocation (6,000 owner stage, 600 independent close),
8 GiB fail-closed aggregate, zero retries/corrective studies. This is requested
new time, not unused v3 time, and neither timing nor storage guarantees completion.

Memory/R2 benefit, full nine-condition study, held-out confirmation, learned
puck/navigation, adequate Afterimage, browser acceptance, human artwork/operator
acceptance and final delivery remain open. CI and physical rover remain deferred.
The simulation-first project remains incomplete.
