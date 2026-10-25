# Retained memory-case publication v1

Status: prospective engineering contract, 25 October 2026. This specifies the
next step in the [completion plan](project-completion-2026-10-23.md); it does not
implement a publisher, accept an execution audit, authorize pruning or launch a
study. The names and interfaces below are new engineering decisions. Historical
protocols, allocations, recordings and consumed attempts remain unchanged.

## Scope and existing mechanisms

Publish one already sealed source and all nine already sealed conditions by
moving their existing directory from `.pending/<case_id>` to `cases/<case_id>`.
Use the [staged reader](memory-retained-case-v1.md) for the existing semantic
checks and derive all analysis cells again. Never accept cells supplied by a
caller. Publication performs no raw/model replay, owner launch or raw deletion.

Reuse `memory_family_producer_v4`'s exclusive file write/fsync pattern,
`memory_family_condition_seal_v4`'s marker guard and validating stack, and the
strict inventories in `memory_family_replay_custody_v4`. The existing
`_rename_noreplace` only renames a source marker in one directory; the case move
needs both held parent descriptors. `HeldReplayFiles` is deliberately read-only:
do not weaken its default checks or treat a returned reader dictionary as a
mutation capability.

All nine conditions must match one externally expected v3 slot: exactly
`case_id`, `case_sha256`, `source_run_id`, `condition_run_ids`, with ten distinct
canonical run IDs. Derive condition order from the registered row using
`memory_family_analysis_v3.condition_order`. Preserve the rejection of
oracle-before-own rows. Only rows 0, 9, 18, 27, 36 and 45 currently satisfy that
dependency; this does not authorize using those six as a replacement study.
Seed-400/family-case applicability remains unresolved.

## Inputs and trust boundary

The proposed public interfaces are:

```python
publish_retained_case(evidence_root, registrations, *, case_slot,
                      condition_commits, execution_audit, deadline)
read_retained_published_case(evidence_root, registrations, *, case_slot,
                             condition_commits, execution_audit,
                             case_commit, deadline)
```

`registrations`, `case_slot` and `condition_commits` retain the staged reader's
meaning. The common source terminal export provides the independently registered
source commit. `case_commit` is an externally expected descriptor of the final
case marker, never derived from the file being admitted. A descriptor has exactly
`path`, `size_bytes`, `sha256`; paths are canonical relative POSIX paths, sizes
are nonnegative integers (never booleans), and hashes are lowercase SHA-256.

`execution_audit` is a canonical-JSON-compatible object supplied by an independent
execution auditor. Its canonical bytes must hash to an explicitly accepted entry
in a new, initially empty `ACCEPTED_EXECUTION_AUDIT_SHA256` trust anchor. There is
no CLI or environment bypass, TOFU, acceptance of a caller's `verified: true`, or
automatic trust-anchor update. A self-consistent receipt is not authority. Actual
acceptance requires independent review of the observer, runtime, allocation and
the ten real owner lifetimes; authored fixtures cannot populate this anchor.
Keep the anchor in a separate `scripts/memory_case_execution_pins_v1.py`, following
`memory_condition_qualification_pins_v1.py`. Exclude that acceptance file from
the audit's subject/source-profile digest closure, and test the exclusion: putting
an accepted audit hash inside a file hashed by that same audit creates an
impossible hash cycle. The validator and all behavior sources remain pinned.
Read the selected acceptance policy independently and recheck it at admission
boundaries; this exception does not allow mutable behavior code.

Check both the existing qualification pins for every terminal export and the
execution-audit acceptance pin before opening protected source, condition,
snapshot or history files, creating case files, or mutating any directory. The
empty anchors therefore keep both public routes closed. A final reader must also
require current acceptance; a valid marker alone never bypasses a revoked pin.

Copy caller-owned inputs at entry. Require a finite monotonic deadline; all
bounded reads, hashes, census, checks and writes share it. Recheck every trust pin
and held dependency before committing and before returning. Returned values
contain no live custody or authority for another operation.

## Execution evidence

The existing v3 supervisor receipt records `started_utc`, duration and exit
status. Owner and cleanup records bind PID/starttime/PGID/PID namespace. They do
not establish a comparable completion clock or absence of overlapping owners.
Do not infer chronology from those records, file mtimes, condition display order
or the fact that all ten owners are terminal now.

Use a prospective supervisor schema in the existing ten `controls.supervisor`
files. Old supervisor objects are rejected for order admission. Keep their
existing per-file and aggregate control byte/entry limits; no new per-owner log
file, external ledger or second copy of the case is added. The accepted audit is
embedded in the case close receipt and charged to its combined 32 MiB allowance.

The execution audit's exact keys are `schema`, `publication_protocol_sha256`,
`case_slot`, `source_commit`, `condition_commits`, `observer`, `owners`, `claims`.
Its schema is `memory-family-case-execution-audit-v1`; slot and commits must equal
the independently expected values. Claims equal the base protocol's all-false
claims object. `observer` has exactly `source_sha256`, `qualification_sha256`,
`boot_id`, `pid_namespace`, `clock`, `ticks_per_second`. It identifies the
independently qualified supervisor implementation and runtime, not the worker.
The clock is `CLOCK_BOOTTIME`; durations are integer nanoseconds. `boot_id` is a
canonical UUID, `pid_namespace` has the canonical `pid:[<positive integer>]`
form, and `ticks_per_second` is a positive integer. One audit has one observer
and one clock domain; cross-boot/namespace records cannot be compared.
The observer source/qualification hashes are historical provenance covered by the
independently accepted audit, not reopenable file descriptors. Readers validate
that attestation; they cannot requalify the historical observer from these hashes.

`owners` is an ordered list of exactly ten objects, source first followed by the
registered nine-condition order. Each object has exactly:

| Field | Required meaning |
| --- | --- |
| `operation`, `condition`, `run_id` | `source`/null or `condition`/exact condition, and the slot's run ID |
| `registration`, `job`, `owner`, `supervisor`, `cleanup`, `commit` | Descriptors of that owner's existing terminal export, job, owner, prospective supervisor, cleanup and sealed commit |
| `pid`, `starttime`, `pgid` | Positive integer process identity; the same identity must occur in prospective supervisor and bound cleanup evidence |
| `launch_ns`, `reaped_ns`, `drained_ns` | Nonnegative integer observer-clock readings bracketing launch, leader exit and verified absence of all that owner's descendants |
| `returncode`, `status` | Exact integer zero and `completed`; an infrastructure failure is not a completed owner |

The prospective supervisor has exactly `schema`, `case_id`, `run_id`,
`operation`, `condition`, `observer`, `job`, `pid`, `starttime`, `pgid`,
`launch_ns`, `reaped_ns`, `drained_ns`, `returncode`, `status`. Its schema is
`memory-family-order-supervisor-v1`. The audit's observer and corresponding
owner fields must match these retained bytes exactly. The other descriptors
must match the terminal export's controls, owner record and expected commit;
the supervisor cannot bind its own future descriptor or a future commit.
The compact v4 owner record contains run/case/source identity, not PID fields;
keep that exact schema and compare those identities. Do not retrofit PID fields
into it. The prospective cleanup record must carry the same process identity,
observer and drain facts as the supervisor; old cleanup records cannot substitute
for that evidence.
Its exact keys are `schema`, `case_id`, `run_id`, `operation`, `condition`,
`observer`, `job`, `pid`, `starttime`, `pgid`, `drained_ns`, `status`; its schema
is `memory-family-order-cleanup-v1` and status is exactly `drained`. It occupies
the existing `controls.cleanup` descriptor slot. Neither this record nor the
supervisor embeds a digest of the terminal export that will later reference it.

Require `launch_ns <= reaped_ns <= drained_ns` for every owner and
`previous.drained_ns <= next.launch_ns` for every adjacent pair. Distinct run IDs
must have distinct `(pid, starttime)` identities; PID reuse with a different start
is representable, while reuse of the same identity is rejected. Preserve the
current owner contract's `pid == pgid` rule. `/proc` starttime
is a boot-relative tick count: compare it to the launch/reap bracket using the
recorded tick frequency with one-tick quantization tolerance. Do not compare its
integer directly to nanoseconds. `launch_ns` is sampled immediately before the
supervisor creates the owner process, not after a prestarted process is released
and not supplied by the worker.

`drained_ns` is sampled only after the observer verifies the entire owned process
scope is empty and prevents any later descendants from appearing. A successful
leader exit or an empty process group at one instant is insufficient. The
independently accepted observer qualification must demonstrate this containment,
serialization, identity continuity and fail-stop behavior. Its implementation and
real evidence are separate gates, not facts this publisher can reconstruct.
Invalid time order, incomplete drain, timeout, uncertain cleanup, missing owner,
extra owner, changed observer or mixed clock domain refuses the whole case.

Passing this validator means **accepted supervisor attestation**, not fresh
process observation. The old staged reader keeps `execution_order_verified=False`.
New publication results use `order_evidence="accepted-supervisor-attestation"`
and retain `raw_replay_performed=False`, `model_replay_performed=False` and
`replay_evidence="retained-attestation"`. No scientific claim changes.

## Three files and binding chain

All files use `memory.canonical_bytes`; reject unknown fields, noncanonical JSON,
duplicate object keys, type coercion, malformed descriptors or trailing data.
Descriptors embedded in files always use final `cases/<case_id>/...` paths.
Location mapping is a reader/transaction concern, not a rewrite of sealed bytes.

| File at the case root | Schema and exact keys |
| --- | --- |
| `manifest.json` | Existing `memory-family-compact-case-v1`: `analysis_cells`, `case_id`, `claims`, `condition_run_ids`, `protocol_sha256`, `run_receipts`, `schema`, `snapshot`, `source_run_id` |
| `close.json` | New `memory-family-case-close-v1`: `schema`, `protocol_sha256`, `publication_protocol_sha256`, `case_id`, `manifest`, `execution_audit`, `retained_inventory`, `retained_directories`, `retained_bytes`, `claims` |
| `commit.json` | New `memory-family-case-commit-v1`: `schema`, `protocol_sha256`, `publication_protocol_sha256`, `case_id`, `manifest`, `close`, `claims` |

`protocol_sha256` always names the selected prospective compact profile;
`publication_protocol_sha256` names the new publication extension. `claims`
always equals the unchanged base claims object. Manifest `analysis_cells` is the
staged reader's derived `retained_cells` in canonical condition order, not launch
order. `run_receipts` has exactly `source` and `conditions`: the expected source
commit descriptor and the complete nine-condition commit mapping. All remaining
manifest identities/snapshot are derived and compared with the registered slot.

Close `manifest` is the manifest descriptor. `retained_inventory` is the sorted,
unique descriptor list of all sealed source/condition leaves, excluding the
three case files. `retained_directories` is the sorted exact directory list,
including the case root. `retained_bytes` equals the sum of inventory sizes.
The final marker binds both manifest and close descriptors. Nothing hashes itself;
no in-file field claims that a future rename or fsync has already succeeded.
Only successful publisher return records durable completion to its caller.

The source/condition inventory has at most 418 files and exactly 33 directories.
The three new files together consume at most 33,554,432 bytes (32 MiB), and the
final tree has at most 454 entries. Enforce both limits independently before any
write and on the final read. Short natural failures may have fewer chunks;
do not pad them to reach 418. Existing source/condition/snapshot/control and
campaign aggregate bounds still apply. The exact final root contains only
`source`, `conditions`, `manifest.json`, `close.json`, `commit.json`.

## Publication transaction

Use a private, one-shot case publication custody object. It holds the evidence
root, both already-existing `.pending` and `cases` parents, case inode, every
registered file and directory, and every external/source/protocol/qualification
dependency through validation, writes, move, fsync and teardown. The publisher
does not create either parent; prospective preparation must do that durably.
No symlinks, hardlinked leaves, repeated inode aliases, unexpected entries,
quarantine, existing case files, final aliases or raw residues are admitted.
The entire `.raw` directory must already be absent, even if empty.

1. Admit public inputs and both trust anchors. Open parents without following
   links; require the same filesystem. Hold the exact source/condition inventory
   and dependency closure **before** semantic validation. Run the existing staged
   semantics while these holds remain active. Validate accepted order evidence
   against the held controls and freshly derived commits/slot.
2. Construct the three canonical payloads in bounded memory. Derive inventory and
   sizes; check the combined 32 MiB and 454-entry limits, all existing ceilings,
   and the exact prepublication namespace. Recheck every held identity/hash.
3. Write `manifest.json`, then `close.json`, using exclusive no-follow opens,
   complete writes and file fsync. Hold each new file's descriptor and verify its
   exact bytes after writing. Fsync the case directory. No retained leaf changes.
4. Write the final marker as `.commit.tmp`, exclusively, fsync it, and verify its
   bytes under custody. At this point the temporary occupies the third case-file
   slot; it is not a fourth file. Recheck all inputs, pins, identities and bounds.
   Rename only `.commit.tmp` to `commit.json` with `RENAME_NOREPLACE`, retaining
   its inode under the existing marker-guard pattern. Fsync the case directory.
5. Recheck again, then call Linux `renameat2` with held `.pending`/`cases` parent
   descriptors and `RENAME_NOREPLACE`. There is no check-then-replace fallback,
   copying fallback or cross-filesystem move. A destination that appears during
   the race must survive byte-for-byte.
6. Verify the same held case inode is now named under `cases`, the staged edge is
   absent, and all retained/new file identities, hashes and the exact final census
   still agree. Fsync both the source parent and destination parent, then recheck
   the final namespace, external dependencies and acceptance pins. Drain every
   validating context and descriptor before returning the externally registerable
   final marker descriptor and retained result.

Authorized mutations are only the three new files, the temporary-marker name
transition, and the single case-directory edge move. Exact file metadata/hash
checks remain unchanged for retained leaves. The private capability may update
expected case/parent directory metadata only for those transitions, after
checking stable device/inode/type and exact before/after entries. It must not
reset all identity baselines after an arbitrary mutation. Ancestors and all
unrelated directories remain held; unexpected sibling activity fails closed.
Default read-only custody tests must continue to reject every mutation.

## Failure and recovery

Before the first successful exclusive output-file creation, an ordinary admission
failure makes no publisher mutation. Once creation succeeds (even if the first
write or fsync fails), preserve the partial files and return `CasePublicationIndeterminate`.
Any failure after marker publication, case rename, parent fsync or teardown is
also indeterminate; never return success because a marker merely exists.

Use the existing `quarantine.json` case marker convention on failure where the
held case descriptor remains valid. Write it exclusively and fsync the held case
directory, plus affected parent directories when applicable. Do not overwrite an
existing quarantine marker. It belongs to the existing failure/temporary reserve,
not the 454-entry accepted steady tree. A quarantined case is never an accepted
tree, and its reservation is never reclaimed to continue the campaign. If marker
creation or durability also fails, preserve the primary failure with cleanup
notes and report quarantine durability as indeterminate. Do not delete, rename
back, reuse a run ID, retry an owner or overwrite a colliding final case.

A crash can leave a complete-looking directory before parent fsync or before a
quarantine marker becomes durable. Final readers therefore require an externally
registered expected case commit obtained only after a successful publisher return;
they never self-register the discovered marker. Explicit recovery must revalidate
custody and durability before issuing any new acceptance. Automatic retry or
recovery is outside this version. No success descriptor is exposed on an exception.

## Final-path reading

Share a private retained semantic core between staged and published readers.
Keep existing staged APIs and their strict namespace behavior unchanged. Select
location explicitly; never probe staging then fall back to final, create aliases,
or rewrite a copy for an existing reader. Final mode maps portable descriptors
directly to `cases/<case_id>`, requires the expected case marker and rejects any
staged alias, temporary marker, quarantine, raw residue or extra entry.

Under continuous read-only custody, validate the marker -> close -> manifest
binding chain, rederive all ten sealed run semantics, the nine cells, equality,
source/snapshot/history relations, complete inventory, accounting and accepted
order attestation. Compare canonical expected bytes to each of the three files.
Require the externally expected commit/slot/registration descriptors and both
trust anchors again. Reading a final path cannot bless indeterminate publication;
the expected marker is a separate caller trust boundary.

## Prospective profiles and acceptance

Source changes need new compact and condition-seal profiles plus a publication
extension. Preserve every existing protocol file and historical pin. New profiles
copy scientific/schema/order/storage/claim values exactly and refresh only their
declared behavior source closure and prospective source identity. Include the
case reader, order validator, transaction, tests and affected dependencies in the
new closure, excluding only the separate trust-anchor files as above; do not make
historical evidence match current source by rebinding it.
Changing this design's scientific or storage values needs a separate prospective
decision, not an implementation convenience.
The planned paths are
`docs/plans/memory-family-compact-evidence-v4-case-publication-v1-protocol.json`,
`docs/plans/memory-condition-seal-v1-case-publication-v1-protocol.json`, and
`docs/plans/memory-case-publication-v1-protocol.json`. These files do not exist
yet. The publication extension must pin the selected base and condition extension,
all three new schemas, the observer/control schemas, all bounds and its complete
behavior closure; it is not a new accepted qualification receipt.

Acceptance tests must cover the real no-replace syscall, marker and directory
rename races, post-rename fsync/teardown faults, ancestor/file substitution, links,
unexpected entries, deadline expiry, descriptor leaks, limits and every ordering
binding. Use small authored fixtures on Btrfs and tmpfs with explicit private trust
seams. Public empty-pin tests must refuse before protected reads and writes.
Neither fixture success nor hosted CI creates an accepted execution audit or
closes R2. See the [implementation plan](memory-case-publication-v1-implementation.md).
