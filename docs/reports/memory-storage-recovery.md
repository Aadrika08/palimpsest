# Memory study storage and Git recovery

4 October 2026. Recovery follows the interrupted
[travel-handoff study](memory-travel-handoff.md), published in
[draft PR #68](https://github.com/Aadrika08/palimpsest/pull/68).
The research checkout's Git state is recovered, and a bounded storage-only probe
passed through the actual recording writer and reader. The historical native
attempt remains incomplete and unqualified. No new native owner was launched.

## Filesystem observation

The filesystem already had more headroom when this recovery started: approximately
47 GB available instead of the prior approximately 25 GB. Btrfs reported 2 GiB
unallocated and a 10 GiB metadata allocation, compared with approximately 1 MiB
unallocated and 9 GiB metadata allocation during the failure. Metadata usage was
84.72% on initial inspection and 85.47% in the later retained diagnostic.

That change occurred outside this recovery. No historical recordings, personal
files, caches, snapshots or build outputs were deleted, and no privileged filesystem
maintenance was performed. The exact cause of the historical ENOSPC remains
unproved; improved space statistics alone are not a write qualification.
The restricted process initially could not see the block-device path and Btrfs
also warned about unavailable detailed chunk information. No physical-device health
claim is made from those warnings.

[Filesystem diagnostics](memory-storage-recovery-evidence/filesystem-diagnostics.log)
retain current measurements. Concurrent filesystem activity is visible: free space
increased during the probe despite its output. Future workload capacity is not
assured by a single successful probe.

## Actual storage qualification

The [retained probe script](memory-storage-recovery-evidence/storage-probe.py)
uses the failed run's numeric array schema and synthetic deterministic payloads.
It uses the actual `RunWriter`, checksum-verifying `iter_ticks`, `StorageBudget`
and study atomic progress replacement. It does not execute policy, sensing,
simulation, acquisition, snapshots or any scientific task.

| Check | Measured result |
|---|---:|
| Synthetic control rows written and exactly read back | 2,100 |
| Payload bytes per row | 216,094 |
| Published NPZ chunks | 66 |
| Atomic progress replacements | 65 |
| Recording manifest | Terminal, completed |
| Retained payload and progress bytes | 454,296,181 |
| Elapsed time, including verification | 18.20 s |
| Native owners started | 0 |

Every reconstructed array matched exactly; published chunks passed the normal
reader's count/schema/checksum checks. The recording used a 512 MiB limit inside a
640 MiB probe bound, 64 MiB headroom and 2 GiB continuing free-space floor. Admission
required 10 GiB free and the probe/readback deadline was 240 s. Free space was
46,872,469,504 bytes before and 47,852,498,944 bytes after.
The interrupted native attempt's retained 23-file inventory remained unchanged.

[Qualification receipt](memory-storage-recovery-evidence/qualification.json),
[raw command output](memory-storage-recovery-evidence/storage-probe.log),
[terminal manifest](memory-storage-recovery-evidence/manifest.json) and
[per-chunk hashes](memory-storage-recovery-evidence/inventory.json) are committed.
The synthetic chunks remain local under
`runs/memory-storage-probe-20261004T131654Z/`. Compact metadata is not a self-contained
payload bundle. This result qualifies the measured write/readback operation at the
current filesystem state; it is not native feasibility, physical qualification,
a crash/power-loss trial or a future storage guarantee.

## Git recovery

Only the three known documentation files were pending in the research checkout.
Their contents matched the already-pushed publication commit `4dbcb0b` exactly.
The publication clone was fetched, and `git reset --mixed FETCH_HEAD` succeeded.
This updated branch/index metadata without overwriting worktree files. The checkout
was then clean at `4dbcb0b`; the original main stayed at
`ee6bf61ea8faec02d5522c7eee30ab7cf333f29d`.
[Git recovery receipt](memory-storage-recovery-evidence/git-recovery.json).
New recovery documentation is committed from the research checkout using its
repository-local Aadrika Maurya <aadrikamaurya@gmail.com> identity.

The scientific implementation and interrupted evidence were unchanged. The prior
full software suite was 915 passed / 24 skipped at the scientific frozen source;
that suite was not rerun for this documentation and filesystem/Git recovery.
The actual storage probe above is the new verification.

## CI and next action

The repository is private, owned by the personal account Aadrika08. Its Actions
permissions are enabled and allow all actions. No repository Actions setting or
workflow was changed. [Read-only settings receipt](memory-storage-recovery-evidence/actions-settings.json).
A fresh push of the recovery documentation checks whether the account-level block
persists; its observations are retained separately below.

The historical GitHub annotations report failed account payments or a spending
limit needing increase. That is an account billing issue, distinct from repository
workflow permissions. GitHub documents that private-repository Actions usage can
be blocked by missing payment information, exhausted allowance or configured
budgets: [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
If a payment is declined, the account owner must update billing information;
this may authorize a charge: [Unlocking a locked account](https://docs.github.com/en/billing/how-tos/troubleshooting/locked-account).
No payment method, subscription or spending limit was changed in this recovery.

The approved travel amendment forbids retries. Storage/Git recovery does not
retroactively authorize another native attempt. Any new study uses a separate
prospective execution contract, retains the aborted owner and all earlier failures,
and keeps the frozen geometry and limits unless explicitly amended. No profile
is selected, all eight native prerequisites remain unattempted, and R2/R3,
held-out, hardware/operator and exhibition gates remain open.

## Fresh remote result

At recovery head `f24420d`, both push and PR fixtures/frontend jobs again failed
without executing. [Exact new annotations](memory-storage-recovery-evidence/ci-annotations.json)
repeat the account failed-payments/spending-limit message. Actions permissions are
enabled; the annotation does not distinguish a declined payment from a budget cap.
No automatic CI rerun loop or payment/budget change was attempted. The next CI
step is for Aadrika08 to resolve that account-level restriction, followed by one
workflow rerun to observe real execution. New native work remains outside this
recovery-only execution.
