# All-nine development: recorded selector comparison

Frozen source `0a05233eefb3c1e55323224f2600120bda251fe4` completed all 22
planned stages: two 300-tick acquisition sources, two zero-step anchors and 18
126-tick continuations, totaling 2,868 recorded numeric ticks. The outer supervisor
completed with exit 0 in 367.611026407 seconds. All owners closed normally, all
source/test/lock/upstream/asset before-and-after identities matched, and the final
plan-bound process scan found no owned survivors. No retries or replacement cases
ran. This is a **manual-controller development mechanism check**, with no neural
motor inference, held-out execution or R2 completion.

The two blocks are fresh development-test seed 8/local and seed 9/paired. Every
continuation starts from its block's identical acquired source/anchor. The permitted
initial differences are U and declared selector configuration/resources, with task
version normalization. This full nine-condition comparison is not U-only. Within
both blocks, every other native component and the complete M/E/initial_M/detector/
cursor/requests/active/last_decisions state matched exactly.

Both blocks have one evaluator gold fact: lower `fact-a`. IDs are prefixed
`live-development-test-00000008-` or `live-development-test-00000009-`. Every row
below reached the goal and committed the changed lower fact at the same boundary.
Inspection columns are requested / started / resolved control ticks; correction
columns are first actual correct observation / first committed correction.

| Block | Condition | Selected target | Exact gold set | Inspection ticks | Lower correction ticks | Goal boundary (continuation ticks) | Evaluator task |
| --- | --- | --- | --- | --- | --- | --- | --- |
| local-8 | own | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |
| local-8 | swapped | upper (`fact-z`) | false | none | 354 / 354 | 426 (126) | true |
| local-8 | sham | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |
| local-8 | no-U | [] | false | none | 354 / 354 | 426 (126) | true |
| local-8 | hand-authored | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |
| local-8 | history-independent | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |
| local-8 | traversal | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |
| local-8 | retrieval | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |
| local-8 | oracle | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |
| paired-9 | own | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |
| paired-9 | swapped | upper (`fact-z`) | false | none | 354 / 354 | 426 (126) | true |
| paired-9 | sham | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |
| paired-9 | no-U | [] | false | none | 354 / 354 | 426 (126) | true |
| paired-9 | hand-authored | upper (`fact-z`) | false | none | 354 / 354 | 426 (126) | true |
| paired-9 | history-independent | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |
| paired-9 | traversal | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |
| paired-9 | retrieval | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |
| paired-9 | oracle | lower (`fact-a`) | true | 300 / 300 / 354 | 354 / 354 | 426 (126) | true |

All 18 evaluator navigation/revision/task scores are true, with no timeout or
unresolved request. Every worker's conservative `task_pass=false` placeholder is
retained; it is distinct from the independently recomputed evaluator score. Own U
and sham match bitwise across all 126 recorded numeric/camera fields excluding wall
latency fields in each block. Wrong upper targets are refreshed directly at 300
without an inspection route; no-U abstains. Both still observe and commit the lower
blockage at 354 on the ordinary common-goal path. Correct lower targets remain
uncertain from 300 to 354 (54 ticks); wrong upper targets resolve at 300 (zero ticks).
No-U has no uncertainty interval. Absence of an uncertainty interval does not imply
that the lower stale expectation was correct before 354.

Own U transfers the learned local/paired relation; swapped U chooses the wrong
upper fact in both blocks, and the fixed local hand-authored rule fails targeting
in the paired block. History-independent and traversal happen to select lower
`fact-a` in both. These two cases therefore retain physical-side, lexical-order and
goal-route confounds. They show **no own-U advantage in task success, correction
timing or completion ticks**. Goal attainment does not establish crossing the
blocked aperture. Frames are correlated; the sampling units are these two cases.

U is exactly refitted from each immutable recorded historical E bundle, with four
changed supports for the relevant relation and four unchanged supports for its
foil. Live M begins unknown and is populated only by actual declared packets; live
E stays empty. Only retrieval receives historical E as a selector behavior input;
only oracle receives evaluator gold IDs. All workers may read the history bundles
for pinned-artifact/refit validation. Access and validation/behavior input bytes,
U payload/envelope bytes and history bytes are recorded separately in the index.
The supervisor and fixed manual continuation use only published declared bearing;
manual source preparation uses explicitly privileged pose supervision. Operator
blindness is unverified. This controller does not satisfy the PRD's first R2 fixed
pretrained FLYNN motor-path requirement.

Both source public goal commands apply at boundary 300/revision 301, to effective
float32 `[-0.5,-2.700000047683716]`. The exact authoritative pre/post physics and
M/E/U/cursor hashes match; post-integration digests bind to registered native
snapshots. Cached-to-refreshed pose differences are labeled as derived-cache
refresh, not physical movement. The separate post-command visibility probe does
not advance memory or fabricate a sensor tick. Actual packet 299 and branch packet
300 pass the declared visibility/evidence admission. Old v1-v4 failures/results and
raw recordings are unchanged.

The independent audit reran existing recording terminal/chunk/count/hash/lineage
readers, native U/config/provenance and normalized-state checks, exact source and
continuation action bindings, evaluator-only pre/post geometry and consecutive cue
proof, all nine targeting scores and revision timings, and own/sham numeric parity.
It performed no simulator run, replay or raw-data mutation. Source focused checks
passed 63 tests in 4.983 seconds in this retained-data worktree. A later integration
fixture exposed a mocked-history context omission; test-only `d906d2c` (feature
cherry-pick `a1cb6b0`) fixes portability. Integrated 63 checks then passed in 3.548
seconds with no skips; actual source/data remain frozen at `0a05233`.

Artifact counts have explicit scope: 136 manifest/event/chunk recording files total
590,817,762 bytes. A further 132 worker/snapshot/index/per-child-supervisor/stdout/
stderr files total 20,717,378 bytes, giving 268 stage files and 611,535,140 bytes.
Top-level plan/report and all outer launch/control/audit files are excluded from
both recording-only and stage-file totals. Process identities were sampled during
the latter part of the run; the final scan covered every plan-bound worker and
found none. Normal child cleanup did not require an additional kill.

The [evidence index](m5-all-nine-development.json) retains all 22 run identities,
primary and secondary file hashes, native/selector/resource/provenance hashes,
source handoff proofs, every target/access score and timing, and the parity audit.
Primary immutable artifacts:

- `runs/m5-all-nine-development-20261002/transfer-plan.json`:
  `6ab48e1e0fd447cd436888e7b04cedbc56be9f5c9b16bf61de4875db2563d33c`.
- `runs/m5-all-nine-development-20261002/transfer-report.json`:
  `2a5fd2fc90454ad872be0b400c0a322cd687cefcb03ea9b497d50b63ce19ca96`.
- `runs/m5-all-nine-launch-0a05233/independent-audit.json`:
  `e872799ce787b7ae0697646cb00ac1d2c85a2eb0f40ae5e7a32245dee5b3720e`.

No useful-memory performance effect, biological interpretation or held-out
inference is claimed. Counterbalanced/null/no-event development and the fixed
pretrained neural-controller continuation remain prospective work.
