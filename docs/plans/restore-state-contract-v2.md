# Prospective restore reproducibility contract v2 candidate

7 October 2026. Prepared under user `doit` following the state-contract proposal
handoff in PR #73. Parent `f539d40`; branch `research/restore-state-contract-v2`.
This is a reviewable software candidate, not an activated native qualification
gate. No retained-pair rerun or fresh native qualification is part of this scope.

## Why distinguish storage integrity from reproducibility

The separate registered attribution study established that all 72 differing bytes
in one retained pair are timer durations, with exact decoded-copy substitution
reproducing the right original payload. The legacy full-state comparison properly
reports unequal raw native bytes; its results stay unchanged.
[Evidence](../reports/memory-native-byte-attribution.md).

MuJoCo describes timer durations as accumulated profiling statistics supplied by
the user-installed timing callback. The candidate treats those statistics as
observational metadata for this declared comparison. It does not claim they are
irrelevant to every possible custom controller.
[MuJoCo 3.3.6 diagnostics](https://mujoco.readthedocs.io/en/3.3.6/programming/simulation.html#diagnostics).
Current repository search found no duration consumer in the simulator/controller
path; uses are offline analysis and the separate fixed-layout puck comparator.
That comparator also excludes other regions and is not reused for this contract.

## Exact candidate rule

Contract identifier: `restore-reproducibility-v2-candidate`.

1. Keep snapshot schema, complete native bytes, raw SHA256, SNP checksum, source
   identities and exact legacy post-state digests unchanged. Verify the raw native
   checksum before constructing any comparison projection.
2. Reuse existing application/destination-receipt normalization unchanged.
3. Use the already tested MuJoCo 3.3.6 round-trip and reversible finite probes to
   map all 15 `timer.duration` float64 fields. Require the same 15 disjoint eight-
   byte intervals on both sides. Unsupported version/layout/probe fails closed.
4. On comparison copies only, zero exactly those 120 mapped bytes. Derive that
   projection's native SHA256 from its projected bytes. Raw checksum verification
   remains mandatory and raw hashes are reported separately; changing this
   derived comparison field never alters a stored raw checksum.
5. Compare every other normalized typed field and every other native byte exactly.
   Timer call counts, warning/solver statistics, caches, native model bytes,
   padding and opaque residual bytes remain included. No numeric tolerance.
6. Report raw full-state comparison and candidate comparison under separate names,
   with contract ID, raw/projected native hashes, mapped intervals and profiling
   durations. Candidate equality is neither qualification nor a raw-byte match.

Only an explicitly registered candidate readout kind may request this projection.
Old registrations, worker receipts, scientific protocols and release gates use
the legacy exact rule. Candidate code neither writes snapshots nor invokes an
Engine, policy inference, reset, forward, step, current-PID check or cleanup.

## Software acceptance and independent review

Use a small synthetic regression covering duration-only equality while raw state
differs, and refusals for timer count, native qpos, application, checksum and
destination-receipt differences. Exercise the candidate through the existing
audited-pair path on synthetic SNP fixtures. Preserve original inputs/digests and
empty qualification claims. Run relevant existing tests and the full local suite;
full-suite isolated simulator tests are software evidence, not study physics.

One final independent read-only branch review, then incremental commits and draft
PR stacked on #73, as Aadrika08 with repo-local author Aadrika Maurya
<aadrikamaurya@gmail.com>. Main unchanged; CI excluded. Preserve old studies,
markers and raw evidence. Account quota telemetry unavailable.

## Activation boundary

Before any scientific activation, freeze a new qualification protocol that names
this version and projection, exact host/runtime/model/profile/source identities,
positive and negative controls, owner count, deadlines, storage bounds and stop
rule. It must require both exact non-timing traces and candidate state equality,
retain/report raw inequality and timings, independently re-audit fresh retained
post-states, and keep historical results unpromoted. No inherited gate success.

Fresh same-source five-control restore attempts can establish a narrow prerequisite
only; broader seeds/longer trajectories, the memory benefit pilot, navigation R3,
held-out and hardware/operator claims remain separate. This candidate PR stops at
software verification and leaves that prospective measured study unattempted.
