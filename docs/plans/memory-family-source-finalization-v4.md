# Prospective source finalization amendment

Scope: the source-only post-close converter and staging seal in
`scripts/memory_family_producer_v4.py`. This implements the approved compact
plan's next source lifecycle slice; it does not allocate, launch, prune, publish
a case, qualify a model, or change any analysis threshold or resource allowance.
All protocol claims remain false and qualification claims remain empty.

## APIs and identities

`seal_compact_source(evidence_root, registration, *, case_id, deadline)` consumes an
immutable root-relative registration descriptor (`path`, `size_bytes`, `sha256`).
The canonical post-close export has exactly `schema`, `protocol_sha256`, `case`,
`run_id`, `owner_source_sha256`, `snapshot`, `raw_audit`, `owner_record`,
`controls`, and `claims`. Its schema is
`memory-family-source-finalization-registration-v4`. This consumes the EXISTING
per-owner terminal-export control slot, whose closed hashes become known only
after source audit/cleanup. It is not a native registration or launch gate. The
shared prospective campaign registration remains separate and unchanged.
`controls` contains exactly the other job, supervisor, stdout, stderr, cleanup
and audit descriptors; audit is exactly the independently published raw-audit
receipt in the existing independent owner-audit slot. The converter retains its
byte-identical copy inside the recording, charged to compact overhead. The
external audit is charged to its separate existing 1 MiB audit allowance, not
again to combined owner control. Controls exclude the terminal export itself, avoiding digest
recursion. The nine unchanged conditions and development case are validated from
the frozen family contract. The source raw tree is derived as
`.pending/<case>/.raw/<run>`, its permanent staging source as
`.pending/<case>/source`. Registration/export and controls live outside that case
and are rechecked through held descriptors. The owner record already occupies
source/owner.json; the sealer does not create a second owner-record path. No new
campaign/control file is created by sealing. Native owner
job/cleanup admission remains a separate future integration requirement.

The separately executed raw auditor receives `--evidence-root` and
`--source-snapshot` (canonical descriptor JSON) for a source. No converter API
authors or replaces the raw receipt. The source snapshot is written once at
`.pending/<case>/source/snapshots/initial.snp` before the raw auditor is invoked.
It is never moved, copied, hardlinked, or rewritten by conversion. A source raw
tree contains only recording files and its byte-identical worker report: it has
no local snapshot, owner file, snapshot index, or undeclared temporary.
The raw receipt adds `snapshot_reference` (the canonical descriptor for a source,
null for a condition); its `raw_inventory` describes only the complete deletable
raw tree. Existing receipts are not rewritten or relabelled under the amended
protocol. Pair admission cross-binds this separate snapshot descriptor.

`source_snapshot_path(evidence_root, case_id, *, staged)` derives only the exact
registered case path, resolving canonical
`cases/<case>/source/snapshots/initial.snp` through `.pending/<case>` while staged
and `cases/<case>` after case publication. Every component is opened without
following symlinks; held descriptors, edge identities and bytes are rechecked.
No `.pending/cases` directory or other unbudgeted directory is introduced.

## Receipt and marker

The conversion schema adds exactly `inventory`, `support`, and `registration`.
`inventory` is the sorted path/size/SHA list of every compact recording payload
and the raw receipt, plus the separately inventoried canonical source snapshot
descriptor without copying its bytes. `support` is the sorted descriptor list for byte-identical
`worker-report.json` and `owner.json`; `registration` binds the input contract.
No additional receipt file is introduced. Conversion receipt and raw receipt
live inside `source/recording`; source marker and support files live in `source`.
The marker schema is `memory-family-compact-source-commit-v1` with exactly
`schema`, `protocol_sha256`, `case_id`, `run_id`, `conversion`, and `claims`.
It binds the root-relative conversion receipt path, size and SHA. The marker is
first written and file-fsynced as `.commit.tmp`, using the existing single compact
publication temporary entry. Every directory fsync, input/context-exit recheck,
raw namespace check, support check and descriptor-edge check completes before
Linux `renameat2(RENAME_NOREPLACE)` renames that temporary to `commit.json`.
That syscall is the last publication operation, with no fallible validation or
fsync afterward. Unsupported libc/kernel/filesystem support refuses without a
final marker; no overwriting fallback is permitted. Marker-data fsync failure
combined with quarantine-publication failure therefore cannot admit a source. Readers require that marker and exhaust its
inventory before admitting a source. This is a staged source seal, not atomic
case publication or native-owner qualification.

## Ordering, limits and failure

The producer holds registration, raw-receipt, control and snapshot identities;
recomputes the published raw audit; reads the full closed raw rows; builds the
compact candidate; compares every retained numeric bit, camera and legacy row
digest, exact legacy metadata byte, selected frame and oracle projection; writes
the final staged files exclusively; exhausts a disk reread; rechecks all inputs;
and fsyncs files/directories before exclusive receipt and prepared-marker
publication. Input context exits happen before the final no-replace rename.
It retains raw evidence on success and failure. Once output writing starts, any
exception leaves that attempt immutable and writes one exclusive quarantine
marker when possible; inability to make quarantine durable is indeterminate.
An existing marker, candidate, or quarantine refuses a second attempt.

All current 32/25 MiB recording caps, 1 MiB compact overhead, 16 MiB snapshot,
3 MiB aggregate owner support/control, 77,824 entries and frozen allocation
arithmetic remain unchanged. Raw receipt and conversion receipt count against
compact overhead; source support/marker and input control files count against the
single combined owner-control MiB, except each stdout/stderr stream's own MiB.
The converter uses no on-disk numeric scratch. While worker-report.json exists
both in the raw run and final source, its raw path occupies the existing single
converter-scratch entry: its at most 1 MiB fits that entry's 32 MiB allowance.
The final report is charged once to owner support/control; the transient raw
report is charged once to scratch, never to that support allowance again. The
scratch allowance cannot simultaneously contain another file. The one quarantine
marker uses the existing transient allowance. Pruning refuses
before all mutation while the protocol's replay/pruning flags are false.
No code in this slice removes raw files or publishes the final case directory.

Synthetic tests must prove separate-process receipt provenance, shared snapshot
placement/alias rejection, exact raw-to-compact derivation, retained support,
commit-last durability and failure quarantine, immutable one-shot attempts,
resource boundaries, import purity, and mutation-free pruning refusal. Pinned
cell replay, native owner writer/cleanup wiring, all nine condition closes,
case/final close, namespace coverage and allocation admission remain prerequisites.

## Namespace durability boundary

Data files, conversion receipt, marker temporary, and their preparation directory
entries are fsynced before final rename. The final marker rename is atomic and
exclusive while the host is running; its namespace persistence across power loss
is explicitly unqualified because no directory fsync follows that final operation.
The later case publication is a separate prerequisite. A missing final marker,
leftover marker temporary, quarantine or indeterminate candidate refuses every
reader/next attempt. This amendment does not claim a power-loss-qualified native
source publication or change release gates.

The syscall contract was checked against the upstream Linux man-pages project's
[rename(2)](https://man7.org/linux/man-pages/man2/rename.2.html) and
[fsync(2)](https://man7.org/linux/man-pages/man2/fsync.2.html). No local man2 page
was available. The implementation uses directory-relative descriptors and
RENAME_NOREPLACE, refuses unsupported operation, and introduces no generic writer
changes or additional permanent anchor.

Read-only descriptor teardown after a successful final rename is best-effort and
reported in the returned `descriptor_teardown_errors` list; it cannot reclassify
an already published source as a failed publication. Before publication, teardown
errors still stop preparation. A future native caller must stop the phase on a
nonempty teardown warning rather than launch another owner. No post-publication
filesystem writes, checks or fsyncs are used to record that return metadata.
