# Puck-v3 native interval source plan

This source-only slice is stacked on `347a838389d7532b1727ad90bddd9b2bdca617cc`.
The frozen v3 protocol bytes and all historical owner, packet, recording and
protocol call paths remain unchanged. Actual capture/writer qualification,
collection admission and numerical execution remain false.

## API and ownership

`puck_on_policy.capture_query_state(env, observation, *, application)` reuses
`snapshots.capture`; retains full native model bytes (including the mutable
arrays excluded from canonical model identity), native data/integration,
environment/profile fields, fixed native binding and puck identity/reset
caches, planner caches, existing observation and Python/NumPy/Torch/environment/
space RNG. Capture is paused, callback-free, headless and observation-only;
uninitialized environment RNG is rejected before capture. It performs no
step/forward/render/reset/restore/observation refresh/RNG draw.

`PuckIntervalWriter(path, *, max_bytes, storage_budget=None)` owns one fresh
v3 recording root and at most 600 interval transactions. Each interval directory
has one unchanged `RunWriter` recording containing one numeric row, its chunk
event and one exact v3 interval event. This deliberately avoids claiming the
historical buffered recording format provides an atomic row/event transaction.

`publish(staged, arrays, event, *, completed_tick)` validates exact staged fields,
the row projection and predecessor before writing. It publishes only a strict
contiguous prefix and returns the existing pure adapter row receipt. A failed
writer remains poisoned and cannot publish any later interval.

`read_committed_intervals(path)` reads only transaction directories with exact
commit markers, verifies the predecessor chain, recording files/identities,
numeric row/event and schema, and yields the admitted interval prefix. Failed
uncommitted directories are retained but do not admit rows. Any malformed
committed directory or later committed directory after a gap fails closed.

`verify_puck_mechanics.on_policy_interval(...)` is a named source seam using
the actual paused environment, contact probe, task state and v3 writer. It calls
one teacher, one student and one student-only step, reuses task/contact/world
arithmetic, and installs both prevalidated cursors only after publication.
It is not a collection envelope: `owner` rejects a v3 envelope before protected
imports until a later reviewed route binds scene/model/registry/manifest sources.

## Commitment

Each interval `000001` through `000600` has `recording/manifest.json`,
`recording/events.jsonl`, `recording/chunks/000000.npz`, plus a durable
`commit.anchor.json` and its final no-replace hard link `commit.json`.
Commit JSON has exactly:

```
version, kind, protocol_sha256, completed_tick, previous_commit_sha256,
row_sha256, staged_sha256, arrays_sha256, event_sha256, files
```

`files` binds each of the three exact recording paths to SHA-256, bytes and full
regular-file identity. The two commitment names must point to the same inode
with exactly two links and contain canonical identical bytes. The first
predecessor is null; subsequent predecessors hash exact prior commitment bytes.
The marker is a new v3-only identity and never a historical record schema.

## Failure order and durability

Before native step: stage decision, validate candidate cursor/row receipt and
immutable packet inputs. After one completed native step: validate native
control/contact/task and bounded v3 packet/event; no live cursor change yet.
Create fresh interval directory and write/finish the one-row `RunWriter`.
Fsync recording files and chunk/recording/transaction/root directories. Read
the exact durable files and bind identities, row/event and predecessor. Write
and fsync commitment anchor; fsync its directory; revalidate files and anchor;
then create the no-replace final link as the sole admission point. No fallible
operation or namespace mutation follows that link. Caller installs already
validated cursors with assignment. A step/write/event/fsync/publication failure
stops this writer/owner forever, keeps previous admitted intervals recoverable
and never promotes raw leftover bytes. Physics is not rolled back.

The final link may be absent after abrupt power loss; its durable anchor and
data remain, but absence cannot be promoted by recovery. This is conservative
admission, not a claim of atomic persistence of a RAM cursor across power loss.

## Accounting and verification

Limits remain 600 intervals, 128 KiB numeric row, 16 KiB interval event, 8 MiB
query capture and 160 MiB owner evidence. Every write is budgeted; all per-row
NPZ headers, both commitment names (one inode, one payload), event/manifest
bytes and directories count in measured retained storage. No fixed-size
estimate substitutes for exact byte accounting. Per-interval buffering is one
row. The parent must leave allowance for initial snapshot/log/result files.

RED/GREEN synthetic fixtures use fake native/model/module boundaries and real
temporary-directory `RunWriter`. They cover isolated capture components,
single student step, exact successful prefix roundtrip, every step/probe/write/
event/fsync/publication failure, replayed/swapped/torn/reordered commitments,
historical reader rejection and v3/held-out envelope rejection before protected
imports. No retained asset, registry, model, native runtime or numerical episode
is accessed. Full native coverage and collection route admission remain open.

Existing mechanics/construction profile hashes differ from the new explicit
layout seam. Historical protocol bytes are not repinned or bypassed; a later
v3 execution manifest must bind the complete current behavior-source closure.
