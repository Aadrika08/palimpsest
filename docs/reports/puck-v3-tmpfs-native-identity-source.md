# Tmpfs native identity: source result and next configuration

## Outcome and scope

Source commit `2f14c3f` adds explicit dependency-registration v3 with
`native_identity: "tmpfs-raw-dev-inode-v1"`. A new registration must use fully
censused, Linux-read-leased package roots. Every admitted dependency leaf FD,
including inert files and external-image copies, must be a linked regular file
on tmpfs. Descriptor-bound `fstatfs` checks the filesystem after custody/hash
admission and before dependency code executes; raw device/inode equality stays
unchanged. Unsupported filesystems, ABI, permission and lifetime changes refuse
admission and preserve cleanup/poisoning. No path/device normalization is added.

The helper supports the inspected Linux x86-64 LP64 ABI. Host headers
`bits/statfs.h`, `bits/types.h`, `bits/typesizes.h`, `asm-generic/statfs.h` and
`linux/magic.h` establish the layout/magic used here. The 256-byte aligned buffer
covers the inspected 120-byte libc structure. Other ABIs are refused, rather
than extrapolated. The caller must retain descriptor lifetime custody.

Registration v1/v2 keep their old schemas and receipt fields. V3 records its
policy in the custody receipt and refuses the trusted-root `system_images`
shortcut. Worker capsules now authenticate the new helper (10 worker files,
14 complete parent source files). Historical consumed capsules/freezes are not
rewritten; their old source hashes do not admit this new source.

V3 preloads trusted stdlib `ctypes` during validated construction, before the
holder is attached as an entering child. The first integration test caught
reentrant import-hook rechecking of an inactive child; moving the preload fixes
that ordering without relaxing rechecks. V1/v2 do not preload ctypes.

## Why direct Btrfs normalization was rejected

Upstream Linux v7.2 reports the mapped inode's superblock device in
[proc map queries](https://github.com/torvalds/linux/blob/v7.2/fs/proc/task_mmu.c#L702-L707),
while [Btrfs getattr](https://github.com/torvalds/linux/blob/v7.2/fs/btrfs/inode.c#L7695-L7727)
reports a subvolume anonymous device. The
[query ABI](https://github.com/torvalds/linux/blob/v7.2/include/uapi/linux/fs.h#L543-L635)
does not expose a mapped-file descriptor, mount identity or subvolume identity.
This supports the measured mismatch explanation; correspondence to the running
7.2.5-3-omarchy binary/configuration remains unverified. A numeric FD/mountinfo
bridge would not establish which Btrfs subvolume a mapped VMA belongs to.

Source review identified a possible ambiguity: one file can remain mapped while
a different mount hides its pathname. Matching the current pathname/inode and
normalizing its device would then not prove the mapped object. This is a source
inference, not an executed mount attack. No privileges, mounts or host security
settings were changed. Previous authored Btrfs/tmpfs measurements and EPERM from
following map_files remain in the
[previous report](puck-v3-native-filesystem-identity-next.md).

## Verification and independent review

Only authored files/tiny C libraries and authored parent fixtures were executed:

| Check | Result |
| --- | --- |
| Helper RED, module absent | 20 failed in 0.16s |
| Helper GREEN | 20 passed in 0.06s |
| Root v3 integration RED, schema absent | 5 failed / 8 passed in 2.40s |
| Initial source integration, lazy-import ordering exposed | 32 passed / 1 failed in 3.43s |
| After ordering fix, /tmp ancestor changed | 32 passed / 1 failed in 1.85s |
| Isolated native positive, same intact guards | 1 passed in 1.80s |
| Broader affected slice | 191 passed / 1 failed in 36.90s |
| Independent whole-branch focused verification | 40 passed in 14.22s |

The broader failure is the same v3 native positive refusing changed ancestor
metadata under `/tmp`, this time while importing `email.quoprimime` before
provider admission. The external actor is unknown. It is retained as a failed
run; neither a skip nor a relaxed ancestor check was introduced. A stable
staging location remains a configuration requirement. No full-suite pass is
claimed. The previously reported default-suite missing FastAPI/httpx collection
errors were not rerun in this unit.

Independent review covered helper ABI, every-leaf admission, schema versions,
lease cleanup/poisoning, worker sequencing, authenticated source closure and
unchanged native map/origin checks. It found no concrete Critical, Important or
Minor defect. Its 40 checks include all 33 new cases and seven legacy worker
controls. Exact independent command (R0 Python is the existing reproduction venv):

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
-B -m pytest -q -p no:cacheprovider \
tests/test_puck_native_identity.py tests/test_puck_tmpfs_dependencies.py \
tests/test_puck_worker_dependencies.py::test_python_dependency_resources_and_distribution_metadata_are_held \
tests/test_puck_worker_dependencies.py::test_bad_dependency_admission_never_executes_entry \
tests/test_puck_worker_dependencies.py::test_held_descriptor_origin_relative_native_dependency_is_explicitly_unsupported \
tests/test_puck_worker_dependencies.py::test_unregistered_persistent_native_image_refuses_terminal_success
```

The bad-admission node expands to four cases; the three other legacy nodes add
three cases. This is source/fixture evidence, not installed-stack qualification.

## Feasibility proposal and exact next exit

The [metadata-only proposal](../plans/puck-v3-tmpfs-native-staging-proposal.json)
retains input hashes and the live filesystem/RAM snapshot. Disk cleanup is
confirmed, but the original dependency namespace is 8,172,376,285 logical bytes,
larger than each 8,011,890,688-byte tmpfs before any reserve. The 93 selected
native images alone are 5,010,115,161 bytes; staging only them would not prove
the full namespace. Current free/RAM snapshots are observations, not reservations.
Swap is not counted as available staging RAM. Mount writability/execution policy
also requires admission; statvfs capacity alone does not prove either.

The original CUDA configuration is **not admitted and infeasible for this tmpfs
proposal**. The next candidate is an exact CPU-only runtime footprint assessment;
its proposed wheel versions, availability, hashes, licences and expanded sizes
remain unverified. No download, installation, payload census or new observation
occurred. It is a prospective alternative, not a silent change to the frozen
CUDA runtime.

Before an actual proposal can be ready, resolve all of:

1. Exact package/interpreter/stdlib layout and all selected external native-image
   lookup paths; packages-only tmpfs copies are not complete proof.
2. Stable writable/executable tmpfs location with the existing full ancestor
   custody contract, plus all-file hashes/census/read leases and exact origins.
3. Whole-stage storage, available RAM, descriptors, metadata, process identity,
   descendants and clock admission. Proposed reserves are not hard resource bounds.
4. Explicit trusted stdlib/interpreter baseline: ctypes preload expands that
   baseline for v3, and neither the baseline nor later Btrfs stdlib image loading
   is qualified by the new dependency policy. Existing global raw-key baseline
   exemptions and snapshot-only native observation are unchanged limitations.
5. A separately numbered prospective decision, exact source/capsule/runtime/
   dependency/environment/bounds review and independent terminal outcome audit.

Preparation01, qualification01 and observations01/02 remain consumed. No actual
NumPy/Torch/MuJoCo allocation, collection, inference, physics, fitting, catalog or
study access, navigation retry, browser/human session or rover work ran. Every
qualification/collection/study/execution authority in the proposal remains false.
All seven full simulation release gates remain open.
