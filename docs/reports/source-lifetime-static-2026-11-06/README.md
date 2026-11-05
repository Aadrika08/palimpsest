# Source investigation of the lifetime platform

This is ordinary source/infrastructure inspection, not a new research owner,
service probe, runtime qualification or actual source attempt. No service was
created, changed or stopped. Earlier source-01/source-02 outcomes remain intact.
No model, graph, checkpoint, raw recording, SNP or protected catalog payload was
opened for this investigation. Hashing was restricted to the three named OS
infrastructure files and public package/source artifacts.

## Package/source correspondence

The installed package metadata names systemd262.1-1. The cached package signature
verifies against the installed Arch public keyring after conversion to task-local
binary keyring format; the initial format failure and corrected exit0 remain
separate records. No user/system keyring was changed. Gpgv verification is not a
reproduction of every pacman trust-policy decision.

The cached package BUILDINFO pins the same PKGBUILD SHA256 as the official
[Arch recipe at commit83e49870](https://gitlab.archlinux.org/archlinux/packaging/packages/systemd/-/raw/83e49870f69d70cce91321b165a69ef788c869be/PKGBUILD).
Its upstream source is v262.1, and its backport/revert lists are empty. Its sole
listed patch matches the recipe SHA512; the patch touches build/group settings,
udev rules and base users, rather than core accounting files. Tag objects and
peeled commits are preserved in source-tag-bindings.json. These checks establish
source/package correspondence, not a locally reproduced build.

The installed manager executable and named core/shared libraries match their
package MTREE sizes and hashes under held-file before/after checks. The live
manager reports262.1-1-arch. Reading /proc/1161/maps was denied, so this record
**does not verify the running manager's mapped binary/library identities**.
No escalation or alternative memory-access technique was attempted.

## Source-backed mechanism and limits

In [v262.1 cgroup.c](https://raw.githubusercontent.com/systemd/systemd/v262.1/src/core/cgroup.c),
unit_prune_cgroup caches CPU before attempting removal. unit_maybe_release_cgroup
then releases tracking only when the hierarchy is empty. unit_get_cpu_usage
returns its cached value when the tracked path is absent. This explains retained
CPU after removal; it does not by itself prove a complete last-tail measurement.
Because caching precedes trimming, acceptance must establish that the entire
registered service was already drained before that cache, rather than assume
that two equal reads or a missing path prove completeness. Unexpected release,
migration, failed drainage or unknown tails stay unqualified.

The [service state path](https://raw.githubusercontent.com/systemd/systemd/v262.1/src/core/service.c)
prunes on SERVICE_EXITED. The [D-Bus property implementation](https://raw.githubusercontent.com/systemd/systemd/v262.1/src/core/dbus-unit.c)
uses the unit CPU getter, exposes unknown CPU with its infinity sentinel, and
reports an empty ControlGroup when no tracked path remains. The
[low-level empty check](https://raw.githubusercontent.com/systemd/systemd/v262.1/src/basic/cgroup-util.c)
uses recursive cgroup.events populated and also treats ENOENT as empty. Therefore
arbitrary ENOENT, MainPID0 or empty ControlGroup alone is not closure evidence.
Stable same-invocation readback, authenticated ownership, independent subtree
drainage and live enforcement remain required actual-stage evidence.

## Startup reuse investigation

The installed bubblewrap help documents --ro-bind-fd and --args. Existing
puck_cpu_namespace.py demonstrates fixed private paths, explicit source/native
bindings and dropped capabilities, but grants no qualification. Its9-path
baseline,512-source-file and staged-input policies are not a drop-in32k runtime
contract. A descriptor-bound namespace may avoid copying7.6GB into RAM; no such
startup backend is implemented or tested here. Descriptor/lease ownership across
exec, protected bootstrap, bounded command metadata, cgroup/PID namespace
identity and the unchanged memory/CPU/retained limits still need a reviewed
concrete implementation. A read-only directory bind alone does not establish
immutable backing bytes or topology.

Whole-operation administrative/finalizer costs, complete prior reconciliation,
actual namespace/input authority, real kernel enforcement and exact-stage GO
remain open. No administration allowance, measured whole-operation CPU or
source/runtime/scientific/pruning qualification is issued. All original local
source responses, package metadata, signature failures and verification artifacts
remain under runs/source-lifetime-static-20261106; their selected copies are
listed in manifest.json. Cached package and installed binaries were not copied
into this report or deleted.
