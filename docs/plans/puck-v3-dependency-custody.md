# Connect held dependencies to the fresh worker

Continue the approved simulation goal from PR #129 (`72758c6`). Complete the
missing registered dependency import path using a separate profile. Do not change
the original seven-role 80 MiB input ceiling or grant numerical collection.

Metadata-only census of the existing lab environment found 31,000 regular files,
7,633,845,149 logical bytes and many external hardlink aliases; the largest file
is 1,022,772,113 bytes. These observations are not payload/runtime qualification.
Use at most 32 roots, 32,768 aggregate files, 60,000 census entries, 2 GiB/file,
16 GiB aggregate read-only payload, 16 MiB registration, 64 MiB serialized held
metadata, 4 MiB copied reads and one absolute <=180-second worker deadline.
Read-only payload size is distinct from retained output/RSS/resource admission.

Reuse the private file-holder core behind an unchanged fixed collection wrapper.
For package roots, require exact full recursive census and per-inode Linux read
leases before initial streamed hashes, including inert installed cache bytes.
Hardlinks may exist outside the roots; their names remain unauthenticated, while
lease breaks poison the held inode. Refuse an existing writer, unsupported leases,
changed signal ownership/mask/handler or a requested break. No metadata-only
fallback for writable package files. Selected system images instead require an
explicit trusted-root-owned, unwritable-to-current-user mode; this assumes trusted
root/Linux and never claims protection from a hostile root.

Full namespace/lease rechecks apply at admission, explicit full checks, native
initializer and terminal boundaries. A Python/resource read checks its selected
leaf, held ancestor chain and global signal/lease state before/after hashing;
do not rescan 31,000 files for every Python module. This is a declared granularity
decision, not an atomic filesystem or hard timing guarantee.

Add an explicit worker v2 registration with an external dependency-manifest
path/size/SHA reference; v1 stays compatible and denies dependencies. Extend the
single held finder with registered Python/namespace/extension imports, bounded
resource and distribution metadata reads, and no ambient site/bytecode fallback.
Use held descriptors for native extension loading, with observed file-backed
image identity checks before/after initialization. Unregistered new mapped files
reject; pre-existing/stdlib image trust and unobserved transient/anonymous code
remain explicit unqualified boundaries. Map snapshots alone cannot prove an
entire native execution history. All runtime/native/collection grants stay false.

- [x] Preserve the original file holder behavior around core extraction:
  59 original checks before; 85 original/bootstrap checks after, 4.82 seconds.
- [ ] Observe dependency holder and real fresh-worker Python/native REDs on
  authored tiny temporary namespaces, without importing installed simulation deps.
- [ ] Implement dependency custody, importer/resources/metadata and worker v2
  integration; preserve terminal refusal and source/model limits.
- [ ] Review complete source, fix concrete findings with regression proof and
  serialize meaningful focused/affected verification; retain suite limitations.
- [ ] Commit/push a stacked draft PR and update goal/matrix. Then finish actual
  runtime qualification and the complete inventory-to-durable-collection route.

Memory amendment02, catalog access and navigation decisions remain pending.
No actual dependency qualification, inventory/model/native owner/study invocation.
CI and physical rover remain excluded. All seven simulation gates stay open.
