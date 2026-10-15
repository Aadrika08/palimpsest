# Next source goal: native identity on the actual filesystem

## Measured gap

The new missing-import source policy has an independent90-check pass, but it
cannot yet lead to a valid actual runtime configuration. Five existing native
positives fail on owned Btrfs test storage. Two tiny authored C configurations
returned47 while recording different identity behavior:

| Storage | Native fstat/pathstat | Native proc maps | Existing target guard |
| --- | --- | --- | --- |
| Btrfs | device57,inode26746125 | device29,same inode | Refuses |
| tmpfs | device55,inode1761200 | device55,same inode | Accepts |

Helpers show the same device difference/match. Both own map_files readlinks work;
following stat is EPERM on both. [Raw Btrfs](puck-v3-expected-missing-imports-diagnostic/btrfs-probe.stdout)
and [tmpfs](puck-v3-expected-missing-imports-diagnostic/tmpfs-probe.stdout) retain all rows/errors.
These authored libraries are not NumPy/Torch/MuJoCo or physics qualification.

## Primary-source explanation and its limit

UpstreamLinuxv7.2 proc maps uses the mapped inode's superblock device and inode
number. [proc source](https://github.com/torvalds/linux/blob/v7.2/fs/proc/task_mmu.c#L465-L480).
Btrfs getattr reports the subvolume root's anonymous device and includes its
subvolume ID. [Btrfs source](https://github.com/torvalds/linux/blob/v7.2/fs/btrfs/inode.c#L7695-L7727).
This plausibly explains the measured difference. Exact correspondence to this
host's7.2.5-3-omarchy binary/configuration has not been established.

Upstream following map_files links checks a capability gate separately from
reading their link text; EPERM is consistent with that behavior and supplies no
usable unprivileged mapped-file descriptor here.
[proc link source](https://github.com/torvalds/linux/blob/v7.2/fs/proc/base.c#L2142-L2163).
No privileges were changed. Source explanation is inference; measured identities
and errors are direct authored observations.

## Concrete next deliverable and exit

Produce a correct native mapped-object identity contract for the actual local
configuration, then implement and review it before proposing another actual run.
First assess descriptor-bound unprivileged interfaces, filesystem/subvolume
identity and persistent map observation. If the current platform cannot supply
the required proof, document that limit and prepare a concrete supported staging/
filesystem configuration with full resource/custody costs for review. Do not
silently ignore device identity or substitute pathname/inode equality for proof.

Authored acceptance must cover the measured Btrfs/tmpfs cases, exact target and
helper identity, different objects with ambiguous raw keys, cross-root/subvolume
distinctions, namespace/target swaps and permission failure. Existing default
native policy, fail-closed behavior and source/lease/first-error contracts stay
explicit. New semantics require their own versioned declaration.

Exit: an explicit implementable identity/observation contract, meaningful authored
regressions, independent source review and a reviewable actual configuration
proposal. Actual runtime remains a separate prospectively admitted numbered
allocation with exact source/capsule/interpreter/dependency/environment/bounds
and independent outcome audit. No automatic retry, new privileges, catalog/study
access, inference, collection, physics or rover work. Preparation01,
qualification01, observations01/02 and navigation attempts remain consumed.

All seven full simulation release gates stay open. This prerequisite does not
replace collection, valid studies/capability results, lab/six-artwork evidence,
user/operator acceptance or reproducible integrated delivery.
