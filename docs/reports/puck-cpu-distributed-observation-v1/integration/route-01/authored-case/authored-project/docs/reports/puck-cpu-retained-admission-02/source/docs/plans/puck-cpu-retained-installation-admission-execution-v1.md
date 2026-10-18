# Retained CPU installation admission: executable preparation contract

This implements the [reviewed proposal](puck-cpu-retained-installation-admission-v1.md)
and the active simulation goal's package-preparation exit. Keep installation01's
FAIL, consumed allocation and missing original finalizer artifacts unchanged.
There is no installer rerun, dependency expansion, numerical import, model/scene/
catalog read, native execution, network access or scientific allocation.

One fixed script/configuration admits exactly the27,225 retained files and2,074
directories in `runs/puck-cpu-install-01/site`, including the authenticated empty
`mujoco.libs` and `pandas.libs`. Input pins include the original failed result,
independent failure-audit report/census/layout and96 licence-copy identities.
The unchanged full payload/RECORD/launcher audit plus equality of every current
file hash binds this admission to the71 exact wheel artifacts without installing
or reexecuting them. This is point-in-time read-only custody on a trusted host,
not continuous writer exclusion or a hostile-process defense.

Reuse the internal held-file core under a stage-specific profile. A preindexed
exact direct-child census preserves named empty directories and avoids rescanning
all path prefixes per directory. Each enumeration gets a fresh bounded directory
cursor. No existing collection/dependency cap or immutable-output guard changes.
A private input reader admits at most8MiB per JSON under held descriptor/ancestor
checks; the original4MiB public read cap remains unchanged. Reject duplicate/
nonfinite JSON, depth>32 and more than300,000 structural nodes.

The sole new data-only exception is exactly
`numpy/distutils/__pycache__/conv_template.cpython-311.pyc`,14,203B,SHA256
6bfa3ef61560b422e0ef918673b642803b958f21edcd27c882ba4857e63d5177.
The original blanket refusal remains historical. Refuse every other pyc and all
pth files. This stage grants no execution authority. Static source review finds
that registered modules allow only `.py` or native extensions
(`puck_runtime_registration.py:287`, `puck_dependency_files.py:273`), with source
compiled directly by the held loader (`puck_dependency_imports.py:133`). Inert
bytecode data is not a registered module. This is not a prohibition against
arbitrary admitted source interpreting its own data. Dependency-v3 still requires
every leaf, including inert bytes, on tmpfs for subsequent numerical use.

Allocation01:180s normal/195s hard;1GiB AS and40,000FD kernel ceilings;512MiB sampled
RSS stop;32MiB output;4GiB free disk/2GiB MemAvailable admission;40,000 installed
files,5,000 installed directories,3GiB admitted aggregate/1GiB individual file.
Metadata uses a separate512-file/64MiB holder and is included in aggregate bytes
and process FD accounting. Require the current host to support40,000FD before
opening the measured tree. Cooperative clock/RSS/disk/output checks occur during
bounded hashing/enumeration with a50ms minimum interval between resource samples;
this is operational sampling, not hard aggregate RSS/storage proof. A kernel
SIGALRM with its default termination action bounds the complete parent at195s.
The parent creates no child or background/log-drain thread.

Reserve only fresh `runs/puck-cpu-retained-admission-01`. Publish configuration,
invocation, full inventory, and current trusted-prefix/bubblewrap/native/tool
baseline pre/post receipts. Write `snapshot.json` synchronously/fsynced while all
source/metadata and installed-file descriptors and namespace edges are held; then
recheck them through close. Write the distinct `result.json` after normal handle
closure, with the snapshot digest, accepted package-data claim, false runtime/
study/collection claims, unchanged original FAIL and closure/FD counts.
A passing artifact is provisional until the externally observed process returns0
within180s and the independent terminal audit passes. A failed/late return wins;
never replace missing original receipts or promote an early snapshot alone.

Source checks cover byte changes, extra/missing files, renamed empty directories,
symlinks/hardlinks, unknown/changed inert pyc, hook files, bounded/deep/nonfinite/
duplicate controls, real low-FD refusal, live-thread/leaked-FD refusal and inherited
synchronous publication checks. Freeze source/configuration before the sole
actual invocation, independently audit the current complete namespace/receipts,
and retain every outcome. Package acceptance alone closes no release gate;
fixed four-import runtime qualification and the real recorded/replayed/exported
episode remain subsequent exits.
