# Compact memory evidence: independent source red team

**Overall: UNAPPROVED / INCONCLUSIVE for actual preservation. Raw deletion stays
DISABLED.** This is a read-only source assessment, not actual data verification,
qualification, pruning permission or GO. No converter, synthetic-data API, model,
native runtime, test, actual raw recording or protected catalog was opened/run.
No tracked source, paper, profile, HEAD or historical evidence was changed. The
only authored artifact is this ignored report; canonical verification is live.

Grades below distinguish representation from accepted production evidence.
`PASS-R` means the representation can retain the stated evidence, conditional on
correct qualified conversion and external provenance; it is not an actual pass.
`FAIL-R` means absent information prevents that claim from the compact bundle
alone. `INCONCLUSIVE-A` means actual correctness/authority has not been checked.
No claim is rewritten merely to make a preservation check pass.

## Exact current scope and source anchors

`paper/main.tex` currently reports an authority/continuation/replay/cost study,
not a completed48-family memory experiment. RQ2 retains paired raw values and
full executable action/policy replay; RQ3 reports measured wall/policy/physics/
camera costs, backpressure and paired operation costs. Those existing historical
artifacts must remain untouched. A future memory compact format is not evidence
that the current paper's full-source artifacts can be replaced or pruned.

Future memory plan: `docs/plans/project-completion-2026-11-05.md` and
`memory-family-analysis-v3.md`:48development families ×3kinds, separate48held-out
families, nine conditions, family as unit,90tick benefit/45harm and precision,
900 natural-failure score, original guards/model-based assumptions. Selection,
order, source/seed applicability, external acceptance and CPU/storage admission
remain separate. Compactness cannot establish independent families or discharge
Lean sampling premises.

Public compact contract: `docs/plans/memory-family-compact-evidence-v4.md`,
“Exact compact contract”, “Camera audit set”, “Replay and derivation proof”.
Executable checks: `scripts/memory_family_compact_v4.py::_project_rows/read_compact`,
`memory_family_producer_v4.py::_prove`, `memory_family_raw_audit_v4.py`,
`memory_family_oracle_admission_v4.py::_projection/_cross_bind`,
`memory_family_retained_case_v1.py::_cell/_read_retained_case`,
`memory_family_cell_replay_v4.py::_replay_rows`, and
`memory_family_case_publication_v1.py::read_retained_published_case`.

The representation keeps19,534bytes/tick: all encoded cell inputs, sensors,
action/control, pose pairs, reward, simulation time, raw cell output, eyes,
revision, four camera digests and a legacy row digest. It retains literal legacy
manifest/events, bounded selected raw images and one complete acquired source
SNP per case. It deliberately drops most image bytes, population summaries and
two timing channels. Raw chunk paths/hashes become provenance, not retained
chunks. Digests are commitments, not recoverable images or executable history.

## Claim-by-claim verdict

| Specific claim/evidence need | Representation verdict | Reason and actual boundary |
| --- | --- | --- |
| Recompute memory goal/non-goal, actual motor rows,900 cap and path length | **PASS-R; INCONCLUSIVE-A** | `_cell` derives row count/path from retained pose pairs; terminal legacy manifest and bound snapshot goal geometry are checked. Natural CueUnavailable versus infrastructure failure remains explicit. Actual mapping, provenance and all144cases still need acceptance. |
| Recompute complete48-family paired scores/precision/null harm guards | **PASS-R; INCONCLUSIVE-A** | All cells/IDs, outcomes and family design can feed unchanged analysis. Must retain full nine-condition case set, development gate, separate held-out selection and verification envelope. A missing family or audit failure cannot become a scored900 or independent extra case. Statistical assumptions remain assumptions. |
| Inspect exact retained numeric channels at every tick | **PASS-R; INCONCLUSIVE-A** | Arrays/dtypes/cursors are readable; producer `_prove` compares every retained value byte-for-byte against raw while raw exists. Direct numeric comparison is possible later, but publication authority/translation correctness are not established by a local chunk rehash. |
| Independently reconstruct every old full row or legacy full-trace digest from compact values alone | **FAIL-R** | Old row digest includes cameras AND `population_stats`; both are mostly/entirely absent. `_trace_digest` hashes stored opaque row-digest strings. Reproducing this string aggregation does not reproduce the original full-row digest inputs. |
| Current all-nine no-event/own-sham guard as retained historical attestation | **PASS-R in that explicit scope; INCONCLUSIVE-A** | Reader compares attested `trace_digest`, goal, ticks, path and outcome; scalar values are freshly derived. Immutable independently admitted raw-auditor/conversion receipts and externally expected commits are essential. This does not imply fresh full-row/model/vision replay. |
| Fresh independent all-nine equality of every original non-timing raw field | **FAIL-R from bundle alone** | Missing pixels/population values prevent original-field reconstruction. `_read_retained_case` compares scalar summaries plus opaque trace digest, not field-by-field every retained array. “Exact all-nine trace equality” needs its retained-attestation qualifier and accepted pre-prune chain, or additional evidence. |
| Re-execute encoded recurrent cell→raw output/action | **PASS-R; INCONCLUSIVE-A** | Cell replay feeds retained4813-wide inputs into the pinned CPU cell, uses zero hidden for source or acquired SNP hidden for conditions, checks raw/action bitwise and source final hidden. It omits retina/observation encoder/renderer/physics/Engine. Actual model/seed/runtime qualification remains unaccepted. |
| Re-audit full camera→retina→encoded-input computation or full policy replay as current RQ2 | **FAIL-R** | At most16raw frame ticks cannot reproduce every retinal update or observation. Acquired SNP supplies one boundary's hidden/retinal/RNG/native state, not missing prior/subsequent pixels. Encoded-input replay explicitly bypasses vision. Full Engine/action replay also has physics/state requirements beyond image bytes. |
| Verify selected visual panels/selected raw-to-effective eye derivation | **PASS-R only at selected ticks; INCONCLUSIVE-A** | Retained raw frames match typed digests; unmasked both-true eye invariant permits effective-eye regeneration there. This cannot support all-tick visual inspection, arbitrary post-hoc panels or universal absence of a transient visual event. |
| Neural population/display summaries or original population-value agreement | **FAIL-R directly; claim-dependent** | Engine records three populations ×count/mean/min/max from hidden activity; these values are omitted. Two raw output coordinates do not encode them. Pinned cell replay could compute model-implied hidden summaries, but that is new replay evidence, not rereading original recorded summaries; the current replay API does not emit these summaries. |
| Measured per-tick inference/physics latency, real-time speed, current RQ3 cost claims | **FAIL-R from compact rows alone; claim-dependent** | Simulation time is not wall/CPU time. Dropped `latency/step_latency` cannot be recovered from it. Existing independent benchmark/worker/supervisor timing reports may retain their scoped quantities; inspect their actual measurements rather than infer them from hashes or elapsed simulation. Compact conversion adds cost too. |
| Native/full-state boundary restore and full episode continuation | **PASS-R for retaining SNP bytes; INCONCLUSIVE-A for actual restore; FAIL-R as automatic full-episode re-audit** | SNP preserves declared native/controller/retina/RNG/observation/application boundary state and identities. It does not itself prove native restoration worked, independent source-start state existed, or every subsequent visual/physics transition can be rerun from compact data. |
| Actual source→own→remaining8 chronology, no overlap and genuine final publication | **PASS-R only with external authority; INCONCLUSIVE-A** | Literal events/mtimes/local manifests do not prove process order. Accepted observer/source/runtime identities, comparable clock/drain evidence and external registrations/expected `case_commit` are needed. Both real trust anchors are currently empty; no retained or discovered marker can populate them. |

## Critical distinction: what the code actually proves

`_project_rows` computes each old row digest over ALL original row fields except
`latency`/`step_latency`, including full four-eye arrays and population values.
It then stores that digest alongside the reduced row. `read_compact` validates
its compact chunk hash/schema/cursors, selected frame checks, camera and row
sequence hashes and the legacy event/chunk mapping. It cannot recompute that
full old row digest from values it no longer has.

The pre-prune `memory_family_producer_v4._prove` is stronger: with raw held, it
compares each retained field's dtype/shape/bytes, recomputes full old row and
camera digests, checks selected images and literal legacy bytes, and binds the
pose projection to the independently published raw-audit oracle result.
Condition sealing invokes this proof around candidate and final bytes. That is
the right point to prove representation fidelity BEFORE any raw removal. Merely
calling the low-level serializer (currently named `convert_synthetic` internally)
or `read_compact` is not an accepted production conversion. This review calls
neither API on any data.

Post-prune `_cross_bind` recomputes pose-projection hashes and policy-event
binding summaries from retained events, while original camera/row sequences are
attested commitments. Retained condition/case readers explicitly return
`raw_replay_performed=false`, `model_replay_performed=false`,
`replay_evidence='retained-attestation'`. Do not promote these into independent
vision/raw/model re-execution, even if their semantic reconstruction is useful.

For no-event cases, equality of a bound original digest is meaningful
cryptographic evidence under the authenticated raw-auditor/converter assumptions.
It is not worthless because pixels are omitted. Its limitation is inability to
independently reconstruct/inspect those original fields after removal, and the
need to trust the accepted pre-prune derivation. Scalar score recomputation and
retained numeric-array equality should be reported separately from that claim.

## Rehash laundering and authority

A self-consistent compact manifest, conversion receipt and case marker can be
rehash-rewritten together. Keeping an OLD opaque row digest while changing a
retained numeric channel is a particularly useful adversarial case: low-level
chunk/hash validity alone is not proof that the numeric channel was copied from
the old row. Pose projection and policy result events bind some channels; they
are not a substitute for the exhaustive raw-to-compact comparison of all fields.

This is not a demonstrated exploit against the fully externally admitted public
reader. Fixed expected source/condition/`case_commit` descriptors and genuinely
accepted execution-audit/qualification pins should reject a changed marker or
receipt, even when all local descendants are rehashed. But if an operator learns
expected hashes FROM the candidate, updates a trust pin to fit it, accepts a
caller `verified` flag or trusts a discovered marker, that protection disappears.
The pre-prune derivation and independently frozen authority must both be proved;
“all hashes match” is insufficient. Current empty anchors mean this actual chain
has not been accepted, not that content preservation has passed by default.

## Minimal additional evidence, conditional on actual paper requirements

No additional channel is automatically needed for the narrow frozen endpoint
estimands if their accepted raw→compact chain and retained-attestation limits
are sufficient for the real paper requirements. That sufficiency is precisely
what remains to decide; do not remove an intended paper claim to force a pass.

Payload ceilings below use public caps only:144sources ×1,200 +1,296conditions ×900
=1,339,200ticks per48-family block. They are deterministic maxima, not measured
storage or a new admitted allocation; container/schema/custody/control overhead
and a prospective format version still need exact accounting.

| Requirement if retained | Minimal candidate addition | Extra payload ceiling per block |
| --- | --- | ---: |
| Original three-population numeric summaries | all-tick3×4 `float64`,96bytes/tick, frozen names/index mapping |128,563,200bytes |
| Original two tick-latency channels | all-tick two `float64`,16bytes/tick, plus existing measured-window metadata |21,427,200bytes |
| Both small numeric additions |112bytes/tick |149,990,400bytes |
| Every raw camera tick, under independently checked all-row both-eyes-true/raw=effective invariant | lossless all-tick two raw eyes,98,304bytes/tick; effective eyes derivable |131,648,716,800bytes BEFORE archive overhead |
| All four eye arrays without relying on that invariant |196,608bytes/tick |263,297,433,600bytes BEFORE archive overhead |

Population plus timing payload would consume134,400bytes/source and100,800bytes/
condition. Existing source slack is only152,160bytes; claiming these fit existing
ceilings requires proving revised format/container overhead fits the remaining
17,760bytes, not merely noting payload slack. No cap change is assumed here.

For full old non-timing row reconstruction under the verified unmasked invariant,
two-eye lossless frames PLUS original population values address the two omitted
scientific components. This still does not reconstruct original ZIP-container
bytes, prove conversion/authority, or automatically qualify a vision/native
replay. Source full-vision replay may additionally need an explicitly retained
source-start native/controller/retina state or an independently qualified exact
reset contract; one acquired endpoint SNP is not that initial-state proof.
A new initial SNP at the existing16MiB bound would reserve up to2,415,919,104extra
bytes for144sources, subject to a new profile/count/budget review.

If the paper needs only a small named full-vision illustrative panel, retain the
WHOLE original raw recordings for an outcome-blind declared panel. A conservative
existing-cap formula is512MiB×number_of_sources +384MiB×number_of_conditions,
plus their separately inventoried support. That supports only that named panel,
not universal all-run vision audit. Do not pick only favorable completed runs or
pretend selected≤16tick images are a full panel trajectory. No panel size or
compression ratio is guessed; any lossless archive requires verified readback,
exact bounds and a separately frozen custody/reader profile. Historical raw
records remain unchanged under every option.

## Smallest falsifying checks to prepare, not execute now

1. While raw still retained, exhaustively compare one properly admitted actual
   case's raw→compact rows, literal events, SNP descriptor and all reported cells
   under held input/output custody; run every required actual qualification and
   source/seed/order gate first. This is a future supervised stage, not permission.
2. On ordinary authored fixtures in a later quiet window, change one retained
   numeric channel at a time (including control/reward/revision), a selected and
   unselected camera, population summary, and both latency channels. Verify what
   `_prove` rejects, what is intentionally omitted, and which post-prune claims
   become unrecomputable. Never run a synthetic API on actual research records.
3. For all-nine no-event fixtures, compare EVERY retained numeric field directly,
   not only scalar path/goal/ticks and stored trace strings. Separately verify
   bound original row-digest equality. Make a one-bit altered control/reward with
   preserved old digest and rehashed local containers fail at the correct
   derivation/authority boundary; document if a low-level reader alone accepts it.
4. Keep original externally expected markers/pins FIXED, rewrite every local
   manifest/receipt to match a tampered candidate, and require public refusal.
   Test missing/revoked/empty acceptance before protected reads. Also reject a
   marker left by indeterminate publication and an oracle-before-own order.
5. Require generic legacy/full-vision replay to reject compact input, rather than
   manufacture missing pixels, population values or latency zeros. Selected-frame
   inspection and recurrent-cell-only replay must retain their explicit scope.
6. For any claimed neural/timing/visual figure, trace its script to the exact
   retained channels/window/unit and regenerate only in separately authorized
   actual verification. A required omitted field is a preservation FAIL, not an
   opportunity to substitute a proxy or revise the claim for convenience.

**Decision:** compact is plausibly sufficient for narrowly scoped numeric memory
endpoints plus authenticated historical attestations; it is demonstrably
insufficient alone for full independent visual/retinal replay, original complete
row reconstruction, and omitted neural/timing evidence if the paper needs those.
Actual preservation remains INCONCLUSIVE until the no-deletion check maps every
intended paper claim to accepted retained evidence and passes the corresponding
qualified checks. Representation review is not production qualification. Raw
deletion, old-attempt replay, new studies and pruning authority remain disabled.
