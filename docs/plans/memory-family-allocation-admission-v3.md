# Memory family v3 allocation admission contract

**Date:** 8 October 2026  
**Scope:** development block zero, deterministic zero-owner admission only  
**Base:** `686e6e0` (`research/memory-family-analysis-v3`)

## Purpose and authority

This unit closes the storage, namespace, upstream, and runtime identity gap left
by the software-only producer registration. It may publish one immutable
capacity-and-identity admission, but it cannot start or authorize an Engine,
model load, subprocess, native owner, held-out read, retry, replacement, or
protocol change. A later reviewed launcher must bind this receipt before it can
request native execution.

The existing family generator, nine conditions, owner order, endpoints,
failure retention, stopping rules, and development/held-out boundary remain
unchanged. Hashes bind bytes and detect ordinary drift; they do not establish
family independence, model assumptions, source authenticity, or
generalization.

## Frozen capacity

The producer subtotal is copied exactly from
`memory_family_producer_v3.RESOURCE_PROJECTION`:

| Class | Formula | Bytes |
|---|---:|---:|
| Raw source and condition recordings | 144 x 512 MiB + 1,296 x 384 MiB | 599,147,937,792 |
| Initial snapshots | 1,440 x 16 MiB | 24,159,191,040 |
| Two logs and aggregate control | 1,440 x 3 MiB | 4,529,848,320 |
| **Producer subtotal** | | **627,836,977,152** |

The separate 8 GiB prerequisite allowance preserves the last reviewed fresh
prerequisite campaign ceiling. The 6,710,886,400-byte non-recording allowance
is the sum of these prospective hard bounds:

- 1,440 owner audits at 1 MiB: 1,509,949,440 bytes;
- 144 case closes at 32 MiB: 4,831,838,208 bytes;
- eight matrix/readout/analysis/final artifacts at 32 MiB: 268,435,456 bytes;
- one namespace inventory at 16 MiB: 16,777,216 bytes;
- four plan/registration/admission contract artifacts at 4 MiB: 16,777,216 bytes;
- one atomic publication staging reserve at 64 MiB: 67,108,864 bytes.

The allocation quota is therefore 643,137,798,144 bytes. The established 2 GiB
continuing free-space floor raises the minimum empty-filesystem capacity to
645,285,281,792 bytes (600.96875 GiB). Existing admitted files count against
the quota, so admission calculates `additional = quota - current_root_usage`
and requires `free - additional >= 2 GiB`.

At most 1,448 runs are admitted: 1,440 family owners plus eight prerequisite
owners. Each recording has at most 2,100 rows and therefore at most 66
32-row chunks. Including run, control, close, prerequisite, and final artifacts
can exceed the current 100,000-entry default. This contract freezes a 131,072
entry limit while leaving the storage helper's default unchanged.

## Namespace inventory

The caller supplies one canonical search manifest with at least one
`historical` root and one `training` root. Roots are absolute, pairwise
non-overlapping directories with no symlink component. The builder walks every
entry without following links, rejects symlinks and special files, and hashes
every regular file. It parses every `.json` and `.jsonl` file within the frozen
metadata and line bounds; malformed or oversized metadata fails rather than
being skipped.

The builder collects canonical UUIDs and every string of at most 128 characters
from metadata and path components. It also records all nonnegative integers
under keys containing `seed` in training roots. This deliberately broad set
may reject an innocuous repeated label, but it cannot silently omit a
prospective family/run identifier present in supported retained metadata. The
namespace JSON remains compatible with the PR #100 producer schema. A separate
search receipt binds absolute roots, kind, entry/file/byte counts, per-root
content digest, the combined searched-root digest, and training-seed digest.

Admission independently rebuilds the inventory, requires exact equality with
the producer-bound namespace file, and rejects intersections with all 1,440
run UUIDs, the generated authored-ID set, and the 48 development family seeds.
It scans the roots again before publication; any difference aborts.

Completeness is relative to the explicitly declared roots and supported JSON
metadata. The receipt never calls IDs or hashes evidence of statistical
independence.

## Roots and capacity

Output and control roots must be absent. The publication root must contain only
the already frozen `registration.json`; `allocation-admission.json` must be
absent. All three roots must be absolute, pairwise non-overlapping, free of
symlink components, outside every immutable/search input, and backed by one
filesystem so the aggregate quota has one meaningful free-space measurement.

The preflight reuses `StorageBudget` for bounded recount and free-space
calculation. It creates no root and takes no writer lease. Success writes one
canonical payload to a synced temporary file, links it exclusively to the final
name, syncs the directory, and removes the temporary. Any failure after linking
removes the target; an existing target is never replaced.

## Source identities

Admission binds, without importing simulation/model modules or spawning a
process:

- CPython 3.11 implementation, version, cache tag, resolved executable path and
  executable SHA-256;
- installed versions of the frozen simulation distributions plus the exact
  `pyproject.toml` and `uv.lock` bytes;
- the exact FLYNN asset manifest, archive, checkpoint, prepared graph, and seven
  mapping file identities;
- both family profile hashes and the family-design hash regenerated from source;
- the fly-gym detached HEAD `8d964599119b420de67ee259434d273651a1a76d`;
- a full clean upstream tree inventory of 122 files, 21,280,722 bytes, with
  canonical inventory SHA-256
  `ad06f7682f3c403f5b3b53d06e57594ffcb868997204796c6fba40b281b096bc`.

The upstream tree identity includes path, file/symlink kind, executable bit,
byte count, and content hash. Missing, changed, deleted, or untracked files alter
the digest. This is a clean-tree content check rather than a claim about remote
repository authenticity.

## Fail-closed result

Capacity and upstream checks are evaluated before the expensive namespace and
asset scans so the present host can report both known blockers without creating
an artifact. A refusal raises one ordered error and publishes nothing. Success
records `storage_allocation_admitted: true`, `native_owner_launch_authorized:
false`, `native_allocation: false`, `held_out_used: false`, and an empty
`qualification_claims` list.

