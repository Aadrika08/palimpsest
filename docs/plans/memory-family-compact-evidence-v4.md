# Memory family v4 compact evidence and storage plan

**Date:** 8 October 2026
**Scope:** prospective development-block-zero evidence format and allocation amendment
**Base:** `ed6c91955a2847298bb9fc146a72ebf305adab67` (reviewed PR #104 head)

## Decision and limits

Add one family-specific post-close converter and one strict compact reader before
any native owner is authorized. Keep the frozen 48-family, 144-case, 1,440-owner
nine-condition development block, owner order, endpoints, sample counts, scoring,
failure dispositions, zero retries, and no replacements unchanged. Every natural
continuation failure remains a scored cell; every source, owner, audit, storage,
or conversion failure remains retained evidence and stops the phase unscored, as
the analysis contract already requires (`docs/plans/memory-family-analysis-v3.md:120-131`).

This plan authorizes no allocation or execution. PR #104 still has unresolved
namespace coverage and `allocation_authorized: false`
(`docs/plans/memory-family-allocation-admission-v3.md:80-86`). No held-out path,
owner, Engine, model, simulator, asset, or upstream input was opened to prepare
this plan. A hash binds bytes and detects drift; it does not prove family
independence, causal provenance, or that omitted pixels were truthful.

The compact artifact preserves the complete exact numeric cell-input and motor
trace and every task/lifecycle event. It deliberately does not preserve every
camera pixel. Its intended scope is the frozen family oracle, endpoint
recomputation, converter-generated legacy-row-digest equality, and a bounded
recurrent-cell replay. Those claims remain false until the implementation proves
them. The artifact cannot support the existing full camera/Engine replay. These
limits are required fields in every compact receipt and result.

## Why the current projection is large

The Engine currently records four `128 x 128 x 3` `uint8` arrays at every tick:
effective `cam_left`, effective `cam_right`, `raw_cam_left`, and `raw_cam_right`
(`src/palimpsest/engine.py:903-906`, `src/palimpsest/engine.py:963-970`). Those
arrays cost `4 x 128 x 128 x 3 = 196,608` bytes per tick. The frozen CPU FLYNN
row is 216,094 numeric bytes per tick, including a `float32[4813]`
`encoded_input` (`scripts/verify_flynn_memory_transfer.py:51-54` and
`scripts/verify_flynn_memory_transfer.py:376-384`). Images therefore account for
196,608 of 216,094 bytes (90.98%). The existing allocation reserves 512 MiB for
each source and 384 MiB for each condition, or 599,147,937,792 recording bytes in
aggregate (`scripts/memory_family_oracle_admission_v3.py:23-26` and
`scripts/memory_family_producer_v3.py:44-57`).

Family sources have at most 1,200 recorded acquisition ticks. A continuation has
at most 900 recorded ticks and the total cursor is capped at 2,100
(`src/palimpsest/memory_decision_world.py:30-32` and
`src/palimpsest/engine.py:995-1004`). These are separate recording lengths; a
condition does not repeat the source prefix.

## Exact compact contract

The prospective `palimpsest-family-compact-v1` format is family-v3-specific. It
is not a generic recorder. A terminal recording contains a compact manifest, a
byte-identical legacy manifest and event stream, a separate compact chunk index,
fixed-schema 32-row numeric chunks, one audit-frame container, a conversion
receipt, and a separate raw-audit receipt. A source run also contains its one
acquired snapshot. Every payload file has a path, size, and SHA-256 entry in the
terminal receipt; the commit marker binds the receipt's path, size, and SHA-256.
The receipt also binds
the converter, reader, raw admission, family oracle, analysis,
snapshot, Engine, FLYNN bridge, family world, dependency/asset identities, and
the allocation protocol by exact source path, size, and SHA-256.
The closed owner's worker report and owner record remain byte-identical files
outside the compact recording and are included in that inventory.

The protocol freezes exact-key canonical JSON schemas named
`memory-family-compact-manifest-v1`, `memory-family-raw-audit-v4`,
`memory-family-compact-conversion-v1`,
`memory-family-compact-pair-admission-v1`, and
`memory-family-compact-case-v1`; the recording manifest's format is exactly
`palimpsest-family-compact-v1`. Unknown or missing keys, schema names, versions,
or unbound source identities fail before any array or snapshot is returned.

Every row retains these values bit for bit, with the listed fixed dtype and
shape. Episode zero and the contiguous tick interval are represented by the
chunk header and are not inferred from array length alone.

| Field | Dtype and shape | Bytes/tick | Reason retained |
|---|---|---:|---|
| `encoded_input` | `float32[4813]` | 19,252 | exact recurrent-cell model input |
| `sensors` | `float32[4]` | 16 | declared collision/bearing input |
| `action` | `float32[2]` | 8 | exact policy action |
| `control` | `float64[2]` | 16 | exact applied simulator control |
| `pose`, `next_pose` | two `float64[3]` | 48 | exact control and oracle geometry trace |
| `reward`, `simulation_time` | two `float64` scalars | 16 | endpoint and time trace |
| `raw_output` | `float32[2]` | 8 | exact cell output before action mapping |
| `eyes` | `bool[2]` | 2 | camera-mask state |
| `revision` | `int64` scalar | 8 | world/change cursor |
| four camera digests | four raw 32-byte typed-state SHA-256 values | 128 | commit to both effective and both raw eyes seen by the auditor |
| legacy row digest | one raw 32-byte SHA-256 value | 32 | preserve the frozen non-timing trace digest |
| **Total** | | **19,534** | |

The reader rejects missing or extra fields, a changed dtype/shape, nonfinite
numeric values, nonzero episode, a gap/duplicate tick, more than 1,200 source
rows, more than 900 condition rows, or a manifest/report/world cursor mismatch.
The existing family admission already requires `pose`, `next_pose`, `action`,
`encoded_input`, `raw_output`, cameras, and sensors before constructing its
pose-only oracle projection (`scripts/memory_family_oracle_admission_v3.py:35-36`,
`scripts/memory_family_oracle_admission_v3.py:105-146`, and
`scripts/memory_family_oracle_admission_v3.py:255-258`). Conversion therefore
runs only after a v4 pre-prune admission has applied those same exhaustive raw
row checks.

The raw `manifest.json` and `events.jsonl` bytes are retained unchanged as
`legacy-manifest.json` and `legacy-events.jsonl`. The latter includes every
original sequence number and raw `chunk` event. For a source snapshot with
`event_prefix.size_bytes = p`, the bytes `legacy-events.jsonl[0:p]`, their
SHA-256, newline count, and final newline must equal the three frozen prefix
fields exactly. Whitespace canonicalization is forbidden.

Legacy chunk paths become provenance only after pruning and the compact reader
never opens them. Compact numeric chunks are described only by canonical
`chunk-index.json`. Its ordered entry `i` has exactly `index`, `path`, `sha256`,
`episode`, `start`, `count`, `arrays`, `legacy_sequence`, `legacy_path`, and
`legacy_sha256`. `index == i`; compact paths are
`chunks/{i:06d}.npz`; `episode/start/count` and the 32-row-except-final partition
must equal raw chunk event `legacy_sequence`; and `legacy_path/legacy_sha256`
must equal that event. The compact SHA-256 is never substituted for the legacy
SHA-256. The compact manifest binds the exact byte size and SHA-256 of both
legacy files and the compact index, the parsed legacy event count, the snapshot
prefix identity, and SHA-256 over the ordered canonical lists of non-chunk
sequence numbers and raw chunk tuples
`[sequence,path,sha256,episode,start,count,arrays]`, calculated as
`hashlib.sha256(memory.canonical_bytes(list_value)).hexdigest()`. The reader
checks the map and
yields every non-chunk task/lifecycle event with its original sequence. Raw chunk
events remain historical records and are never exposed as live compact chunk
references.

The source legacy event file is capped at 7 MiB and a condition's at 5 MiB.
Exceeding either cap is a retained conversion failure, not permission to
canonicalize, discard, summarize, reorder, or change events or the case.

`latency` and `step_latency` are omitted: the trace digest already excludes them
because timing does not define neural, motor, or geometry equivalence
(`scripts/memory_decision_pilot.py:670-677`). `population_stats` is also omitted:
it is a derived display summary built after the step and is not an analysis,
oracle, action, or control input (`src/palimpsest/engine.py:958-970`). The exact
`raw_output` is retained instead. No endpoint may begin to depend on an omitted
field without a new prospective protocol version.

### Camera audit set

Every run retains both unmasked raw eye arrays at no more than 16 deterministic
ticks. Let `T` be the ordered, contiguous recorded tick values. The set is the
union of:

1. `T[floor(k * (n - 1) / 5)]` for `k = 0..5`;
2. each value in `{s - 1, s, s + 1}` that is present in `T`, for the case's one
   scheduled world-event tick when enabled and its one decision tick; and
3. the final two values of `T`, or its only value when `n == 1`. These are the
   pre-boundary pair for a source and the terminal/failure pair for a condition,
   including a sensor-only failure that emitted no row at the failing tick.

Duplicates are removed and output in `T` order. The rule has a structural upper
bound of `6 + 3 + 3 + 2 = 14`; more than 16 nevertheless fails conversion. A
planning-time pure enumeration of all 144 development-block-zero generated cases
and every source length 1..1,200 and condition length 1..900 found at most 7
source ticks and 11 condition ticks, because the final tick is already a quantile
and the two schedule neighborhoods overlap. Tick translation does not change the
cardinality. Before implementation, the enumeration was repeated with the
required `../lab-hardening/.venv/bin/python` Python 3.11.15 interpreter. Both
valid synthetic prerequisite IDs `gate-a` and `fixture-prefix` produced the same
case-list digest
`009135479864b4a1c83c611683ada7efce298d29e9a807a7740b07ee6d09112c`.
The earlier
`b5f603d175a4799864442055399656cb760c8d9ff82bfed354827b4d940a4bb5`
planning value came from unpinned `/usr/bin/python` 3.14.7 and is superseded
before any owner or evidence execution.
The implementation must repeat that generator-backed test and require that
digest. Empty recordings remain invalid. At every tick, the raw auditor and
converter check the existing policy-call observation/result hashes, require
`eyes == [true, true]` in every
row, reject any `eyes_changed` event, and check each raw eye equals its effective
eye. The boundary snapshot check remains necessary but is not treated as proof of
the all-row invariant (`scripts/memory_family_oracle_v3.py:151-158`). The four
stored digests are exactly `bytes.fromhex(state_digest(array))`, ordered
`cam_left`, `cam_right`, `raw_cam_left`, `raw_cam_right`. Effective hashes must
also equal those in that tick's policy-call event. Each selected
`uint8[128,128,3]` raw frame must match its raw digest; effective eyes are
regenerated by the exact mask rule. A selected frame costs
`2 x 128 x 128 x 3 = 98,304` bytes, so 16 cost 1,572,864 bytes.

This proves byte-exact raw-to-effective derivation only at selected ticks. At
other ticks the digests commit to bytes seen by the independent pre-prune auditor
and reject a later supplied mismatching frame, but cannot reconstruct or
independently inspect the omitted pixels.
The receipt must say `full_pixel_replay: false` and
`camera_to_encoded_input_independently_reauditable: false`. It may not turn a
digest match into an independence or causal claim.

### Replay and derivation proof

Before pruning any run, a separately invoked raw auditor whose exact executable
source path/size/SHA-256 is protocol-bound opens the closed v1 tree read-only,
exhausts every chunk, verifies stored hash/schema/counts and immutable inputs,
and runs `policy_bindings` so every full camera/sensor observation and exact
action/encoded-input/raw-output is bound to its policy-call event
(`scripts/verify_flynn_memory_transfer.py:366-392`). It publishes an immutable
pre-prune raw-audit receipt before the converter starts. The converter process
has no receipt-output argument: it can only open the already published receipt
read-only and must fail if it is missing, replaced, or changes.
The auditor publishes by exclusive link to an absent path, revalidates every raw
input after the link, and fsyncs the receipt and parent directory; rollback must
unlink and directory-fsync, otherwise the case is indeterminate and quarantined.
The receipt binds the exact raw manifest/event/chunk/support inventory by relative
path, size, and SHA-256; run/case/condition/source identities; row/event/chunk
counts; terminal state; oracle/policy results; camera-sequence SHA-256 over the
raw 32-byte digests in row-major order
`cam_left,cam_right,raw_cam_left,raw_cam_right`; and row-sequence SHA-256 over the
ordered raw 32-byte legacy row digests. The compact reader recomputes both
sequence hashes from its rows. This binds every stored per-row digest without
copying thousands of digest strings into the receipt.

The source passes the new v4 source-only raw admission and audit, is converted,
exhaustively reread, and is durably sealed with its acquired snapshot before its
complete `.raw/<run>` tree is removed. The
source-only receipt makes no source/condition-pair claim. Each condition then
passes its own v4 raw admission and audit. Only after its compact candidate is
reread may the
v4 compact-pair admission compare it with the durable compact source and the one
shared snapshot. That admission consumes both raw-audit receipts and reuses the
current manifest, lineage, policy-result, oracle, and immutable-input checks that
remain applicable (`scripts/memory_family_oracle_admission_v3.py:322-405`), while
explicitly replacing the condition-local snapshot check. It never claims that
the unchanged v3 source/own pair entry point passed; that entry point requires
both raw runs and a condition-local snapshot and hard-codes `own`. The v4 entry
therefore validates the registered condition plus its exact expected
selector/resource/U/history identities for each of the nine frozen conditions;
it cannot treat a non-`own` condition as if it passed the current pair code.

The converter reads the still-fingerprinted raw input once, writes the compact
candidate, exhausts the strict compact reader, and compares every retained value
and legacy event byte to the raw source. It regenerates the audit tick set,
raw/effective checks, four per-tick camera digests, world/task replay, endpoint
cell, and oracle projection. A pure cell replay is intended to use the frozen
model identity and starting policy state (reset state for a source; the shared
acquired source snapshot for a condition), feed every exact `encoded_input`, and
compare every `raw_output` and action. This is a recurrent-cell replay, not
retina, renderer, physics, or Engine replay. The protocol and every receipt carry
`cell_replay_verified: false`, `compact_oracle_equivalent: false`,
`storage_allocation_admitted: false`, `native_owner_launch_authorized: false`,
and `qualification_claims: []` until deliberate-wrong-input tests and independent
review prove the cell path and all other gates. Pruning authorization also
remains false until then. This plan does not flip those fields; a reviewed
implementation/protocol amendment must do so prospectively before any owner.

The legacy analysis `trace_digest` is computed before pruning exactly as today:
for each full row remove only `latency` and `step_latency`, calculate the lowercase
64-byte ASCII `state_digest` hex string, retain
`bytes.fromhex(row_digest)` in the compact row, and update the aggregate with
`stored_digest.hex().encode("ascii")`. Hashing concatenated raw digest bytes is
forbidden. This preserves the frozen aggregate and cross-condition equality
field, while the omitted row bytes remain unrecoverable and independently
unrehashable.

The compact proof binds the pre-prune raw tree digest and the independent raw
receipt, but those hashes only attest which bytes the auditor and converter saw.
Later reviewers can rerun compact event/task/oracle logic, endpoints, selected-
frame checks, numeric comparisons, and, only after its gate passes, cell replay.
They cannot rerun the omitted all-tick pixel checks.

## One source snapshot per case

Retain exactly 144 acquired source snapshots, one for each case, at the existing
16 MiB ceiling. Do not create 1,296 condition-local copies. Each condition
manifest instead binds the registered source run ID, source receipt SHA-256,
root-relative source snapshot path, exact byte count, and SHA-256. Absolute paths
and machine device/inode numbers are excluded from the portable artifact.
Against the current cap projection this removes
`1,296 x 16 MiB = 21,743,271,936` reserved bytes; it is a ceiling reduction, not
a claim about measured snapshot sizes or filesystem deduplication.

The snapshot is written once beneath the unpublished case tree and moved only by
the atomic case-directory publication; neither conversion nor a condition may
copy or hard-link it. Before restore, after owner close, before compact
publication, and during every later case close/read, code must open the
registration-derived path beneath the
same direct non-symlink output root, reject symlink components and non-regular
files, compare `fstat` identity to the open descriptor, hash through that
descriptor, and recheck path identity after hashing. Any replacement or mutation
stops the phase. The source snapshot remains immutable until its nine condition
receipts and the case-close receipt are durable, and then remains inside the
atomic case bundle for the complete evidence lifecycle. A condition cannot be
exported or read outside its committed case bundle, and no pruning may orphan its
relative snapshot reference. Cases run serially: one source, then its nine frozen
conditions in their already registered order, then case close. Maximum native-
owner concurrency is one.

The current v3 admission expects a condition-local registered snapshot
(`scripts/memory_family_oracle_admission_v3.py:177-190`), so v4 must replace
that check explicitly with this source reference. It must still prove that the
restored application equals the source application modulo destination recorder
identity, as v3 does (`scripts/memory_family_oracle_admission_v3.py:337-354`).
No hard link or path alias is treated as an independent copy.

## Publication, pruning, and failure

An owner writes the existing full v1 recording under an unpublished per-case
namespace. The source-only auditor publishes its raw receipt; the converter
writes and seals the compact source while the source snapshot stays at its sole
permanent relative path inside that case staging tree. Only after a second
exhaustive compact-source read, raw-receipt comparison, final input recheck,
file/directory fsync, and a source commit marker may the complete source
`.raw/<run>` tree be removed and the `.raw` parent directory fsynced. Each
condition repeats the raw receipt,
conversion, and re-read sequence. Its compact-pair admission against the
committed compact source and shared snapshot is published before its complete raw
run tree is removed. The byte-identical legacy manifest/events and raw chunk
ledger must already be sealed in the compact run. Removal is descriptor-anchored,
then verifies absence of every raw manifest, event, chunk, temporary, marker,
file, and directory before fsyncing the parent. After the ninth condition, case
close removes the empty `.raw` directory and fsyncs the case directory. Any
residual path is quarantine, not steady state. The existing v3 pair admission is
never placed before source removal or reported as this v4 admission.

The staged compact files are the final files, not copies to be rewritten later.
After all ten runs close, case close rechecks every receipt/reference, publishes
the case commit marker last, and moves the absent case directory into its final
name with no-replace same-filesystem semantics followed by parent fsync. Readers
ignore a source, condition, or case without the applicable marker. It never edits
or replaces a published run or case.

If raw auditing, conversion, pair admission, publication, recheck, pruning,
no-replace move, or rollback durability is uncertain, stop the phase and preserve
the case/raw/staged evidence as quarantined. Never retry the owner, replace its
run ID, omit a failed case, or continue by consuming the emergency reserve. The
next preflight must reject any quarantine or indeterminate marker.

Legacy `palimpsest-npz-v1` artifacts remain byte-for-byte untouched and readable
by their existing reader. Existing `iter_ticks`, artifact playback, sonification,
and `replay_run` must reject the compact format rather than synthesize absent
cameras or population summaries.
Only the new version-pinned family reader may open it. There is no in-place
migration and no claim that legacy and compact recording hashes are equal.

## Exact worst-case allocation

No compression ratio is credited. Numeric arrays, frames, and digest bytes are
counted uncompressed. ZIP/NPY headers, manifest, receipt, event index, and chunk
records have a separate 1 MiB hard ceiling per recording. A compressed encoding
may be added only if the reader retains these uncompressed limits and rejects an
expansion beyond them.

| Per-run component | Source | Condition |
|---|---:|---:|
| Dense rows | `1,200 x 19,534 = 23,440,800` | `900 x 19,534 = 17,580,600` |
| At most 16 two-eye raw frames | 1,572,864 | 1,572,864 |
| Byte-identical legacy events | 7,340,032 | 5,242,880 |
| Container/manifest/index/receipt overhead | 1,048,576 | 1,048,576 |
| Calculated maximum | 33,402,272 | 25,444,920 |
| Frozen recording ceiling | **33,554,432 (32 MiB)** | **26,214,400 (25 MiB)** |
| Slack inside ceiling | 152,160 | 769,480 |

The complete steady-state development allocation is:

| Class | Formula | Bytes |
|---|---:|---:|
| Compact source recordings | `144 x 32 MiB` | 4,831,838,208 |
| Compact condition recordings | `1,296 x 25 MiB` | 33,973,862,400 |
| Acquired source snapshots | `144 x 16 MiB` | 2,415,919,104 |
| Owner logs and control | `1,440 x 3 MiB` | 4,529,848,320 |
| **Compact producer steady subtotal** | | **45,751,468,032** |
| Existing prerequisite allowance | | 8,589,934,592 |
| Existing non-recording allowance | | 6,710,886,400 |
| Incremental single-owner raw/scratch/snapshot-temp overlap | `512 + 32 + 16 MiB` | 587,202,560 |
| **Allocation maximum** | | **61,639,491,584** |
| Continuing free-space floor | | 2,147,483,648 |
| **Minimum free bytes before launch** | | **63,786,975,232** |

The family-owner `3 MiB` row is a hard aggregate: at most 1 MiB for stdout, at
most 1 MiB for stderr, and at most 1 MiB combined across that owner's job,
supervisor, byte-identical worker report, owner record, cleanup receipt, terminal
export marker, run commit marker, and, for a condition, snapshot reference and
compact-pair admission. It is the sum of file sizes, not a separate 1 MiB grant
to each JSON file. Exceeding it stops before raw removal. The compact recording's
separate 1 MiB overhead row covers the compact and legacy manifests, chunk/index
container headers, audit-frame container overhead, raw-audit receipt, and
conversion receipt; legacy event bytes, dense arrays, and frame payloads have the
separate bounds shown above.

The inherited `6,710,886,400` non-recording bytes are also fully assigned:

| Non-recording class | Hard aggregate and files | Bytes |
|---|---:|---:|
| Independent owner audits | `1,440 x 1 MiB`, one immutable audit file each | 1,509,949,440 |
| Case closes | `144 x 32 MiB`, combined case manifest/close receipt/commit marker | 4,831,838,208 |
| Matrix/readout/analysis/final | `8 x 32 MiB`, one file each | 268,435,456 |
| Namespace inventory | one file at 16 MiB | 16,777,216 |
| Protocol/registration/admission contracts | `4 x 4 MiB`, one file each | 16,777,216 |
| Atomic non-recording publication staging | one shared 64 MiB reserve | 67,108,864 |
| **Total** | | **6,710,886,400** |

Prerequisite recordings, their worker/owner/support files, supervision logs,
snapshots, campaign controls, and close consume only the separate 8 GiB aggregate
prerequisite allowance. No family support file may also draw from that allowance,
and no file may be charged to two classes. These combined caps are rechecked at
owner close, compact admission, case close, and final close.

The steady subtotal already includes the unpublished case's final compact files
and sole source snapshot. The incremental overlap conservatively adds the larger
source raw tree, one 32 MiB converter scratch file, and one 16 MiB exclusive
snapshot-write temporary through durable publication; it does not assume a
second snapshot or copy of the compact tree. Capacity accounting keeps the final
snapshot reservation while that sole temporary is in flight, rather than
reclaiming reserved campaign capacity. A condition needs at most
`384 + 25 MiB` of raw-plus-scratch overlap and has no local snapshot. The 560 MiB
source bound is larger. The reserve is available to one owner only and is never
counted as recoverable campaign capacity after a quarantine.

Entry counts are also frozen. One final case has exactly 33 directories:
one `case/`; four source directories (`source/`, `source/recording/`,
`source/recording/chunks/`, `source/snapshots/`); one `conditions/`; and three
directories for each of nine conditions (`condition/`, `condition/recording/`,
`condition/recording/chunks/`).
Its source has
38 numeric chunks and 11 other files: compact and legacy manifests, legacy
events, compact index, audit frames, conversion receipt, raw-audit receipt,
worker report, owner record, source commit marker, and acquired snapshot (49
files). Each of nine conditions has 29 chunks and 12 other files: the same seven
recording/control files without a snapshot, plus worker report, owner record,
snapshot reference, compact-pair admission, and condition commit marker (41
files each). Three case files hold its manifest, close receipt, and final commit
marker. Thus one case is exactly `33 + 49 + 9 x 41 + 3 = 454` entries, and 144
cases plus the shared `cases` directory are 65,377 entries.

| Entry/count class | Frozen arithmetic | Maximum |
|---|---:|---:|
| Final family case trees | `144 x 454 + 1` | 65,377 entries |
| Owner control trees | `1,440 x 8 + 4` | 11,524 entries |
| Eight prerequisite trees and controls | exact aggregate below | 474 entries |
| Matrix/final, namespace, contract, and three lock files | `8 + 1 + 4 + 3` | 16 entries |
| **Steady entry projection** | | **77,391 entries** |
| One raw source tree, temp/quarantine markers, pending-case parent | `48 + 1` | 49 entries |
| **Peak projected entries** | | **77,440 entries** |
| **`StorageLimits.max_entries`** | frozen `76 x 1,024` cap | **77,824 entries** |

The eight per-owner control entries are exactly one job, one supervision
directory with supervisor/stdout/stderr, one audit, one cleanup receipt, and one
terminal export marker; four shared directories hold those classes. The raw
source is the larger transient budget: four directories at
`.pending/<case>/.raw/<run>/{recording,recording/chunks}`, raw manifest/events,
38 chunks, one converter scratch entry, one snapshot-write temporary, one compact
publication temporary, and one quarantine marker (48 entries). It contains no
second snapshot; the temporary is the sole snapshot while it is being written.
The shared `.pending` parent is the forty-ninth transient entry.
The staged case files are already charged as one of the 144 final case trees and
move without copying; source and condition writers cannot overlap. The cap has
384 entries of explicit headroom. A quarantined raw tree consumes the transient
49-entry allowance and stops the phase before another owner can add entries.

The prerequisite projection is aggregate rather than a per-run average. Each run
has four directories (`run`, `recording`, `chunks`, `snapshots`). Each of four
full runs has at most `ceil(2,100 / 32) = 66` chunks plus six files (`owner`,
worker report, manifest, events, snapshot index, initial snapshot), or 76 entries:
304 total. Each of two prefix runs has 38 chunks and the same six files, or 48
entries: 96 total. Each of two five-control repeat runs has one chunk, those six
files, and one post-repeat snapshot, or 12 entries: 24 total. The eight run trees
are therefore 424 entries. Four shared stage/jobs/runs/supervision directories,
eight job files, eight supervision directories with 24
supervisor/stdout/stderr files, five campaign files (registration, preflight,
execution, fresh-source, scientific-close), and one launcher control marker add
50, for the exact 474-entry prerequisite aggregate. Global contract files and
three storage locks remain in the separate 16-entry row.

The amended limits are `max_runs: 1,448`, `max_exports: 1,592`,
`max_snapshots_per_run: 2`, and `max_entries: 77,824`. Exports are exactly 1,440
owner audits, 144 case closes, and eight matrix/final artifacts. Family runs have
exactly one source snapshot or zero condition snapshots. The prerequisites have
one snapshot in each of four full and two prefix runs and two in each repeat, so
the aggregate snapshot ceiling is `144 + 4 + 2 + 2 x 2 = 154`. Admission checks
both that aggregate and the per-run limit.
An entry at the cap is accepted; one more is refused before write/publication.

On 8 October 2026, the final pre-review read-only `df -B1` on this worktree
reported 67,467,177,984 available bytes on `/dev/mapper/root`. The prospective
minimum therefore leaves 3,680,202,752 bytes. This is a point measurement, not
admission:
the future allocation check must measure again, subtract already-admitted root
usage exactly, include the overlap, and require the 2 GiB floor after the whole
prospective allocation. One byte short refuses. The earlier 643,137,798,144-byte
allocation and 1,440-snapshot projection must be replaced, not combined with
this one.

The amendment inherits every non-storage admission gate from PR #104: the exact
two reviewed development/training namespace exports and their coverage proof;
disjointness of all 1,440 run IDs, authored IDs, and development seeds; direct,
non-symlink, nonoverlapping output/control/publication roots; the exact clean
fly-gym pin and tree inventory; interpreter, dependency, project-file, asset,
model, family-profile, and behavior-source identities; and immutable rollback-
safe admission publication. A launcher must additionally bind the v4 admission
path, size, and SHA-256, enforce the registered owner order and concurrency one,
and refuse a quarantine, partial compact run, or stale capacity measurement.
The earlier execution-error probe establishes none of these gates and cannot be
relabelled as an admission.

Concretely, coverage remains unresolved for the namespace-only source IDs
`pre-heldout-development-history` and `training-namespace`; neither may be
replaced by an arbitrary recursive scan or by held-out metadata. Upstream must be
the clean exact fly-gym commit
`8d964599119b420de67ee259434d273651a1a76d` with 122 files, 21,280,722 bytes, and
inventory SHA-256
`ad06f7682f3c403f5b3b53d06e57594ffcb868997204796c6fba40b281b096bc`.
Python 3.11, every distribution and project-file identity in the v3 protocol,
the FLYNN asset manifest/model, both family profile hashes, and every old and new
behavior-bearing source must match. The future launcher must consume one
immutable successful v4 allocation admission, reject the existing inconclusive
execution-error evidence, and never infer authorization from a hash alone.

## Smallest implementation sequence

1. Freeze a canonical v4 protocol containing the exact schema, audit-tick rule,
   byte arithmetic, behavior-source identities, snapshot-reference contract,
   `full_pixel_replay: false`, and unchanged analysis/sample contract.
2. Test and implement the strict compact reader, the separately executable
   source/condition raw auditor, and one family-only post-close converter. Reuse
   the existing safe-path, fingerprint, digest, bounded JSON, raw reader, oracle,
   storage, and publication helpers; do not add a generic recording framework or
   alter `RunWriter` for other studies.
3. Adapt only family producer close and admission: source-only raw receipt,
   durable compact source and snapshot, complete source raw-tree removal, then one condition raw
   receipt and v4 compact-pair admission at a time. Replace the v3 local-snapshot
   check with the relative shared-snapshot contract; never label the v3 raw-pair
   entry point as passed.
4. Amend the allocation protocol and registration to 32/25 MiB recording caps,
   144 snapshots, a 560 MiB transient reserve, one-owner concurrency, new source
   identities, and a future launcher binding to the exact admission path, size,
   and SHA-256.

Required RED/GREEN tests are:

- exact field/dtype/shape, contiguous tick, source/condition row, event, frame,
  archive-expansion, entry-count, and total-byte limits, each with at-limit and
  one-over rejection;
- aggregate family support/control, independent-audit, case-close, and
  prerequisite byte tests that place every listed file in exactly one allowance,
  accept equality, and reject one byte over or double charging;
- conversion equality for every retained numeric value and exact legacy event
  byte, exact legacy-manifest bytes, snapshot-prefix bytes, compact-to-legacy
  chunk mapping, selected raw frames, raw/effective equality, all-tick four-camera
  digests, raw result hashes, trace/endpoints, every condition oracle, and
  recurrent-cell replay, with deliberately wrong values proving each check is
  live;
- the exact `bytes.fromhex(state_digest(row_without_timing))` stored row digest
  and ASCII-hex aggregate update, with a test proving raw-digest concatenation
  produces a rejected aggregate;
- all 144 generated development cases and all nine analysis cells, including
  natural failure and sensor-only failure fixtures, producing the same close
  cells and complete 1,296-cell analysis input as the raw projection; enumerate
  every legal recording length for the same 144 cases and assert the audit-tick
  union never exceeds 16;
- separate-process/exclusive raw-receipt tests that prevent the converter from
  authoring or replacing it; source-only audit, durable source publication and
  full raw-tree removal, then condition audit and compact-pair admission, with claims remaining
  false until the deliberate-wrong-input cell replay gate passes;
- exactly 144 source snapshots, zero condition-local SNP files, portable relative
  references, and rejection of mutation, replacement, symlink, alias, wrong
  source/case/run, wrong size/hash, or a missing source receipt;
- legacy-reader rejection of compact, compact-reader rejection of legacy or
  unknown versions, and no silent camera synthesis or full-replay claim;
- exclusive publication, commit-marker ordering, fsync and failure-injection
  rollback/quarantine checks; complete raw-tree removal only after durable
  re-read; deliberate residual raw manifest, event, chunk, temporary, marker,
  file, and directory tests; and no owner continuation after any indeterminate
  state;
- exact aggregate arithmetic, maximum concurrency one, free-space equality
  acceptance, one-byte-short refusal, exact four-full/two-prefix/two-repeat
  prerequisite entry/snapshot layouts with one-extra-entry refusal, and refusal while namespace coverage,
  upstream, assets, quarantine, or any PR #104 prerequisite is unresolved.

Before any native execution, a fresh independent reviewer must report no
Critical or Important finding on the schema, converter/reader trust boundary,
snapshot aliasing, raw-prune sequence, oracle/analysis equivalence, and arithmetic.
The reviewed allocation amendment must then resolve the exact two namespace
exports and all remaining PR #104 upstream/runtime/assets gates. Synthetic tests
and source review do not authorize an owner. Held-out remains unopened.

## Open risks

- The 7 MiB/5 MiB event ceilings are source-derived prospective bounds, not
  native measurements. A valid first owner may exceed one; that must stop the
  phase and retain its raw evidence. No compression experiment has been run.
- The 1 MiB compact-container overhead and combined per-owner support ceilings
  are also prospective hard bounds. If exact byte-identical reports or receipts
  exceed either, the case stops with its raw tree quarantined; the limits cannot
  be raised from observed results.
- Omitting unsampled pixels permanently prevents full retina, renderer, physics,
  and Engine replay and later independent camera-to-encoding audit at those
  ticks. The retained cell inputs and hashes do not cure that limitation.
- One shared snapshot creates a one-to-nine dependency. Rehashing detects drift
  but does not recover a corrupted source snapshot; storage/media reliability
  remains an operational prerequisite.
- Exact recurrent-cell replay from stored `encoded_input` still needs an
  implementation proof against the pinned upstream cell and reset/restored
  policy state. Until it passes, compact conversion and allocation stay false.
- The measured 3,680,202,752-byte margin is finite and will drift. PR #104 also
  remains blocked by unresolved development/training namespace coverage, and its
  prior real probe is inconclusive; this plan changes neither fact.
