# Memory condition sealing: draft source evidence

The new condition route is implemented at `c1be67c347168e9574b33c34e5d3786fe3b750b7`, but the current
implementation milestone remains open: authored integration passes on tmpfs and
fails in the unchanged source producer on the project Btrfs filesystem. No actual
qualification, model inference, study, pruning or release gate is admitted.

The [machine-readable index](memory-condition-seal-v1-source.json) pins all seven
new source/test/extension files and preserves scoped results. The base is
`2514c47`; its tracked producer, compact, pair, cell, custody, qualification source,
compact protocol and amendment02 freeze remain unchanged. Original branches and
consumed attempts remain preserved.

## Working source behavior

[The sealer](../../scripts/memory_family_condition_seal_v4.py) binds the terminal
registration, source/SNP, raw audit, histories and controls; converts and compares
retained bytes; calls the production cell consumer through an internal default;
applies real staged pair admission; embeds replay in the existing commit marker;
and retains custody through no-replace publication. Indeterminate postcommit
validation/teardown retains the marker, quarantines and raises. Raw remains.
There is no additional replay file, condition snapshot, pruning or case grant.

[Admission](../../scripts/memory_condition_replay_admission_v1.py) owns held
receipt/source/runtime/model inputs and returns a checked session. Its separate
repository-reviewed [trust anchor](../../scripts/memory_condition_qualification_pins_v1.py)
is empty and explicitly outside the receipt's self-authenticated source closure,
avoiding a receipt/helper hash cycle. The public route refuses untrusted identity
before protected reads or numerical loading. Caller receipts do not grant trust.

The positive authored own-condition fixture uses the real independent raw auditor,
converter, exhaustive readback and staged pair. It replaces private qualification,
model-loading and cell-replay seams. These are orchestration checks, not evidence
that the full production model passed replay or that every condition works.

## Verification and review

| Check | Actual result |
| --- | --- |
| Root admission helper | 53 passed, 0.14s |
| Builder complete condition file on tmpfs | 33 passed, 50.04s |
| Root six condition spotchecks on Btrfs | 6 failed, 8.74s, before new sealer |
| Root same six condition checks on tmpfs | 6 passed, 9.60s |
| Directory replacement regression | RED 2 failed, 3.87s; GREEN 2 passed, 3.66s |
| Two independent-review findings | RED 2 failed, 3.54s; GREEN 2 passed, 3.38s |

The two review findings were primary replay error replacement during failing
cleanup and mutable registration identity copied after validation. The fixes drain
contexts while preserving the operation error with cleanup diagnostics, and copy
the descriptor before the first read. The builder also found and fixed detached
recording/chunks directory validation; retained named-directory edges now remain
bound. Root inspected these source fixes and independently exercised the relevant
regressions. No second independent post-fix source GO or combined full-suite pass
is claimed. Default Python could not import pytest because pygments was missing;
verification used existing test environments without installing anything.

## Concrete Btrfs gap

All six root Btrfs cases failed inside unchanged producer._disk_bundle while
preparing the authored source fixture. The new condition consumer was not reached.
A separate one-fixture diagnostic on Python3.11.15 recorded a held directory FD
listing only owner.json and snapshots after writing. Opening its /proc/self/fd path
for a fresh listing showed the expected recording and worker-report.json too.
After failure the on-disk namespace contained all four expected entries. `stat -f`
reported btrfs for runs/ and tmpfs for /tmp. The six scoped checks then passed on
tmpfs with the builder's interpreter. This measures a filesystem-dependent failure;
the underlying implementation/kernel cause is not yet qualified.

The failed tiny fixtures and diagnostic remain under the ignored runs/ roots in
the index. They are authored evidence, not actual scientific allocations. No
namespace guard, device/inode check or frozen source was weakened or rewritten.

**Next finite source task:** reproduce this directory-enumeration discrepancy in
a baseline authored regression, specify correct named-directory enumeration for
the supported filesystem, and implement/review the appropriate prospective source
extension. Preserve exact namespace and held identity checks. Revalidate both
filesystems before closing this implementation milestone.

## Remaining real execution requirements

No successful actual qualification is trusted. Historical qualification is fixed
to seed400, while generated family snapshots require their own case seed and exact
policy provenance. Current prospective receipt shape cannot serve those cases;
a separately reviewed historical-proof/per-case-model binding remains necessary.
Memory amendment02 is still uninvoked and alone would not solve this binding.
The numerical model-loading/checking path has not been exercised on the full model.

The oracle/own schedule conflict remains unresolved. Complete all-nine ordering,
source pruning, case/family admission, actual owner/terminal and stage resource/
clock/runtime qualification remain required. File/directory fsync is not measured
power-loss persistence. All seven simulation release gates remain open; the
[active simulation goal](https://github.com/Aadrika08/palimpsest/blob/research/simulation-completion-next/docs/plans/simulation-release-execution-goal.md)
continues to require research, capability, the lab, all six artworks, human
acceptance and one reproducible integrated delivery before a rover decision.
