# Memory directory census: prospective source revision

## Deliverable and boundary

Make the existing authored source-to-condition seal work on both the project
Btrfs filesystem and tmpfs without weakening exact namespace or held identity
checks. This closes the known implementation gap in simulation milestone1.
It does not qualify an actual model/runtime, launch an owner, collect a study,
prune raw evidence, close a whole case or satisfy any release gate.

The corrected stdlib diagnostic reproduces a first held-directory listing that
omits newly created entries on Btrfs. A fresh openat(fd, '.') listing sees them;
tmpfs agrees across methods. The first diagnostic's lseek metadata probe refreshed
state and confounded that result. Preserve both diagnostics. Upstream CPython and
Btrfs source explain a credible per-open-description mechanism; the exact host
kernel binary is not source-qualified by that analogy.

## Directory enumeration contract

New scripts/memory_directory_census_v1.py exposes
`directory_names(fd, *, max_entries, deadline=None)`. It takes a held directory FD,
opens '.' relative to it with directory/no-follow/close-on-exec flags and obtains a
fresh open file description. It never replaces the held FD, changes cwd, seeks,
uses a proc pathname, follows children or patches os globally.

Validate exact integer FD and entry bounds and any supplied finite unexpired
monotonic deadline. Enumerate the fresh description with bounded scandir; the
first excess entry rejects rather than materializing an unbounded listing.
Compare fresh and held directory identities and full metadata before/after the
scan and close only the owned description. Preserve primary failures and attach
cleanup diagnostics. This is bounded metadata work, not a hard latency guarantee.

Existing producer and condition namespaces remain exact. All their directory
censuses use this helper with a64-entry ceiling; the largest supported single
namespace has38 chunks. Per-role exact sets, recording/row/byte/file limits,
held leaves, named directory edges, no-replace publication and quarantine checks
remain enforced. Normal sites pass their existing deadline unchanged when
available. Private outer-checked metadata guards and failure/quarantine cleanup
remain bounded without restarting a budget or blocking cleanup on an expired
normal deadline. No study or resource ceiling changes.

## Explicit prospective protocol selection

The original memory-family-compact-evidence-v4-protocol.json remains byte-identical
at SHA256 cbdf034970963a847d42fabc879cc4596a99c8c1b58311561a6c678233e9c4fa. The qualification branch2514c47 and its original
amendment02 freeze remain preserved. The current source branch cannot invoke that
old capsule and must never rewrite or relabel its historical evidence.

Create the separately named active protocol
memory-family-compact-evidence-v4-directory-census-v1-protocol.json. Preserve every
scientific, schema, scheduling, storage, quota and all-false claim field. Change
only source-revision metadata and behavior-source descriptors for changed compact,
raw-audit and producer modules; add exact helper, this plan and original-protocol
references. There is no environment or caller-selected protocol override.

The compact module selects the new path explicitly. Raw auditing and replay
admission derive that active protocol descriptor consistently. Source hashes are
computed before protocol bytes; no module embeds the final active protocol SHA.
This avoids self-referential hashes while binding the actual implementation.

Preserve memory-condition-seal-v1-protocol.json unchanged too. A separately named
memory-condition-seal-v1-directory-census-v1-protocol.json retains its registration,
marker, schema, file/storage and false-authority contracts, binds the new active
base hash and refreshed helper/sealer/plan source pins, and records its parent.
Both sealer and admission helper select this exact extension path. Its repository
trust anchor remains empty and outside receipt self-custody; historical seed400
qualification still cannot serve generated family-case seeds without a separate
reviewed binding. No actual allocation decision follows from this source profile.

## Proof and stopping rule

Demonstrate fresh census after held enumeration and create/remove/create on both
filesystems; prove count limits, deadline/refusal, directory identity/metadata
mutation, ownership and error cleanup. The original six Btrfs condition checks
failed before this change. Rerun the same authored source/raw-audit/conversion/
pair/seal/reader route on Btrfs and tmpfs, including existing publication faults,
input/output mutation and quarantine cases. Positive numerical seams stay authored.

Verify original protocol/extension/freeze bytes, exact new source pins and no
scientific-field drift. Run affected legacy source checks and independent source
review; fix concrete findings in one bounded pass. Record every failure and the
exact evidence scope. No full-project, numerical or physical qualification claim.

Finish this unit when the directory implementation and unchanged scientific
contracts are reviewed and the required authored paths pass on both filesystems.
Then continue runtime configuration and the remaining family proof/order/case
work under the full seven-gate simulation goal. Pending study decisions and all
consumed allocations remain unchanged.
