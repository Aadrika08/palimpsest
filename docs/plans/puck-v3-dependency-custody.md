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
- [x] Observe dependency holder and real fresh-worker Python/native REDs on
  authored tiny temporary namespaces, without importing installed simulation deps.
- [x] Implement dependency custody, importer/resources/metadata and worker v2
  integration; preserve terminal refusal and source/model limits.
- [x] Review complete source, fix concrete findings with regression proof and
  serialize meaningful focused/affected verification; retain suite limitations.
- [x] Commit/push a stacked draft PR and update goal/matrix. Then finish actual
  runtime qualification and the complete inventory-to-durable-collection route.

Memory amendment02, catalog access and navigation decisions remain pending.
No actual dependency qualification, inventory/model/native owner/study invocation.
CI and physical rover remain excluded. All seven simulation gates stay open.

## Implementation ledger

- Core extraction `a39db1f`; plan/integration API REDs `469a66d`.
- Dependency/import integration `43a861d`: 146 focused passed, 11.87s.
- Seed atime regression reproduced before correction; content/identity comparison
  excludes access time, preserving byte/hash/inode/mode/size/mtime/ctime/nlink pins.
  Native boundary characterization `42859cd`: 150 focused passed, 16.37s;
  1367 affected passed, six inherited excluded, 77.64s.
- Whole-branch review found aggregate census enforcement after traversal, missing
  namespace resource readers and unrelated signal-mask restoration. Each was
  reproduced RED and fixed in one pass; precise second-root census RED observed
  five entries where the remaining budget plus one allows three. Corrected source:
  153 focused passed, 16.53s; 1370 affected passed, six inherited excluded, 77.01s.
- Default test command stops at missing FastAPI in R0 interpreter: one collection
  error, 0.31s. No whole-repository pass or numerical qualification claimed.
- Ruling: v2 external Python/resource imports use bound local dispatch and source
  metadata plus targeted dependency byte/ancestor/lease checks; full source hashes,
  dependency census and image observations remain public/native/terminal boundaries.
  This avoids repeatedly hashing the interpreter and whole dependency forest for
  every import. Cost if wrong: mutations outside the consumed path can be observed
  only at the next full boundary; this is trusted-source custody, not a sandbox or
  atomic forest proof. V1 full checks remain unchanged.
- Deferred minor: resource listing derives directory names from registered files;
  authenticated empty directories are not exposed through resource traversal.
- Actual origin-relative ELF fixture refuses because held-FD loading changes its
  lookup origin. No pathname fallback or native transitive compatibility claimed.

Independent final-source repetition: 153 focused/16.38s and 1370 affected/78.32s,
same six exclusions, exit0. All test processes stopped. See the source report.

Published draft PR #130; goal PR #94 and matrix PR #102 updated.
All seven release gates remain open; next runtime/owner integration is unfinished.
