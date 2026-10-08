# Memory family v3 allocation admission contract

**Date:** 8 October 2026
**Scope:** development block zero, deterministic zero-owner admission only
**Base:** `686e6e0` (`research/memory-family-analysis-v3`)

## Purpose and authority

This unit measures the storage, namespace, upstream, and runtime gates left by
the software-only producer registration. It may publish one immutable
capacity-and-identity admission only after every gate has a separately frozen
identity. It cannot start or authorize an Engine, model load, subprocess,
native owner, held-out read, retry, replacement, or protocol change. A later
reviewed launcher must bind the receipt path, byte count, and SHA-256 before it
can request native execution.

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

## Namespace coverage

Caller-chosen recursive roots cannot prove that every relevant historical or
training source was declared, and scanning arbitrary evidence roots cannot
enforce the held-out boundary. This contract therefore admits exactly two
logical sources: `pre-heldout-development-history` and `training-namespace`.
Each must be a direct, absolute, non-symlink external directory containing
exactly one canonical `namespace-export.json`; extra files, subdirectories,
links, and special files are rejected before metadata is read.

Each export has the exact `memory-family-namespace-export-v3` schema and binds
its logical source ID, kind, reviewed known-source enumeration, canonical UUIDs,
bounded authored IDs, and training seeds. The protocol must independently
freeze each export's byte count and SHA-256; root entry/file/byte counts and a
canonical inventory SHA-256; and the known-source, run-ID, authored-ID, and seed
counts/digests. These frozen identities exclude the machine-local root path.
The path manifest alone maps the two frozen logical sources to portable
absolute locations, while the searched-root receipt binds the actual paths. A
path manifest cannot add a source or assert an identity.
Name-based `held-out` rejection is defense in depth; the exact two source IDs,
one-file allowlist, schema, and frozen identities are the authority.

No reviewed pre-heldout exports are frozen in this revision. The canonical
protocol therefore records `coverage_status: unresolved` and
`allocation_authorized: false`, with null expected identities. Preflight must
refuse before opening either external directory. It must not inspect held-out
metadata to try to resolve global namespace completeness. A later protocol
revision may fill the expected identities only after independent review of the
two namespace-only exports and their known-source enumeration.

When coverage is resolved, admission rebuilds the producer-compatible namespace
from the two exact exports, requires equality with the producer-bound namespace
file, and rejects intersections with all 1,440 run UUIDs, the generated
authored-ID set, and the 48 development family seeds. It repeats both exact
export checks after exclusive publication. Hashes bind the reviewed export
bytes; they do not prove statistical independence or that an omitted real-world
source does not exist.

## Roots and capacity

Output and control roots must be absent. The publication root must contain only
the already frozen `registration.json`; `allocation-admission.json` must be
absent. All three roots must be absolute, pairwise non-overlapping, free of
symlink components, outside every immutable/search input, and backed by one
filesystem so the aggregate quota has one meaningful free-space measurement.

The preflight reuses `StorageBudget` for bounded recount and free-space
calculation. It creates no root and takes no writer lease. A possible success
writes one canonical payload to a synced temporary file, links it exclusively
to the final name, and removes the temporary name. It then revalidates every
mutable input and capacity check while the final name is visible, before syncing
the directory. Any failure after linking must unlink the target and sync the
directory again. Failure to prove either rollback step raises an explicit
indeterminate-publication error. Rollback verifies that the final name still
identifies the inode linked by this call before unlinking; a replacement is
preserved and surfaced as indeterminate. An existing target is never replaced.

## Source identities

Admission binds without constructing/loading a model, opening an Engine,
performing inference, or spawning a process:

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
- exact paths, byte counts, and SHA-256 values for the admission script,
  producer, family generator, artifact, asset, memory, family-world, and storage
  helpers. These are rehashed after exclusive linking and are part of the
  receipt that any future launcher must bind.

The submodule gitdir must be the exact `modules/upstream/fly-gym` directory
under the checkout's own resolved Git directory; an arbitrary external gitdir is
rejected before `HEAD` is read. Prepared graph metadata may name only a relative
edge and relative mapping files that remain below the verified graph root.
Behavior-source identities are captured while this module imports and current
source bytes must still equal that loaded-code baseline before a receipt is
constructed as well as after exclusive linking.

The upstream tree identity includes path, file/symlink kind, executable bit,
byte count, and content hash. Missing, changed, deleted, or untracked files alter
the digest. This is a clean-tree content check rather than a claim about remote
repository authenticity.

## Fail-closed result

Capacity, upstream, and frozen namespace-coverage checks are evaluated before
asset scans so the present host reports all known blockers without creating an
artifact. A refusal raises one ordered error and publishes nothing. Because the
two reviewed namespace exports are not yet frozen, this revision records
`allocation_authorized: false`, `storage_allocation_admitted: false`,
`namespace_coverage_complete: false`, `native_owner_launch_authorized: false`,
`native_allocation: false`, `held_out_used: false`, and an empty
`qualification_claims` list. Synthetic tests may exercise the success and
rollback machinery against an independently constructed resolved fixture, but
that does not change the production refusal or qualify any native allocation.
