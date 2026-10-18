# Registered dependency custody and fresh-worker imports

The source unit continues PR #129 (`72758c6`) toward the complete durable puck
launcher. Corrected source is `7db611bb142d35cc2a5683001647a0a36057cf5c`.
All seven simulation release gates remain open. This is source/fixture evidence,
not actual numerical dependency qualification, native closure, a collection grant,
a capability result or an independently reviewed exact final execution freeze.

## Implemented behavior

`puck_execution_files.py` now shares a private file-holder core while its public
collection wrapper retains the original fixed 512-file / 32 MiB-per-file /
64 MiB-total bounds. The source-plus-original-interpreter 80 MiB ceiling remains.
The worker's v1 registration stays supported and denies external dependencies.

`puck_dependency_files.py` provides a distinct, externally SHA-pinned canonical
registration: explicit package/system-image roots, files, Python/extension/namespace
mappings and distribution Name/Version metadata. Package roots require exact
recursive census, including inert installed cache bytes and empty directories,
and Linux read leases before initial streamed file hashes. Existing writers,
unsupported leases, namespace drift, altered notification ownership and requested
lease breaks refuse; there is no writable-file metadata-only fallback. External
hardlink names are unknown, while the same held inode's write aliases trigger its
lease. Duplicate selected inodes remain unsupported. System-image inputs instead
require trusted root ownership and effective unwritability to the current non-root
user; this explicitly assumes trusted root/Linux.

Separate dependency bounds: 32 nonoverlapping roots, 32,768 aggregate files,
60,000 entries per complete forest census, 2 GiB/file, 16 GiB read-only input,
16 MiB registration, 64 MiB serialized retained metadata, 4 MiB copied reads and
one absolute <=180-second worker deadline. Enumeration enforces the remaining
aggregate census budget before accumulating another root. These are admitted
input/metadata limits, not measured RSS, output allocation or hard timing bounds.

`puck_dependency_imports.py` connects held Python bytes, explicit namespaces,
package/namespace resources and distribution metadata to the single worker finder.
Unregistered imports have no ambient site/bytecode fallback. Native extension
initialization uses `/proc/self/fd/<held-fd>` as CPython's actual spec origin;
there is no physical-path fallback. Full checks bracket native initialization,
and persistent file-backed map observations must identify registered held objects
or the explicitly trusted baseline/stdlib images. Module object/spec/loader/origin
bindings are retained; mutable external package functions/data are not sandboxed.

Worker v2 adds only the dependency registration's exact path/size/SHA reference.
Its all-false runtime/dependency/native/collection/executable fields and empty
qualification claims remain authoritative. A terminal JSON receipt is transport,
not durable owner publication or evidence of descendant drain.

The APIs were checked against the official [CPython importlib reference](https://docs.python.org/3.11/library/importlib.html),
[Linux read-lease reference](https://man7.org/linux/man-pages/man2/F_SETLEASE.2const.html)
and [proc maps reference](https://man7.org/linux/man-pages/man5/proc_pid_maps.5.html),
then exercised on the target CPython 3.11.15 in real isolated fresh children.

## Scope observations and verification

A separate metadata-only census of the existing lab environment observed 33,694
entries, 31,000 regular files and 7,633,845,149 logical bytes in 1.038 seconds;
27,529 files had external hardlink counts, no selected inode repeated, and no
symlinks/special files were observed. Largest file was 1,022,772,113 bytes.
Installed metadata identified NumPy 2.2.5, Torch 2.9.0 and MuJoCo 3.3.6. These
were stat/directory and bounded distribution-metadata observations, not payload
hashes or imports. The MuJoCo dependency uses etils[epath]: bare etils lock rows
omit its extra-qualified fsspec/typing_extensions/zipp/epy requirements. Complete
resolved extras and native/system image closure still need admission.

Observed implementation sequence:

- `a39db1f`: core extraction; 59 original checks before, 85 original/bootstrap
  checks after, 4.82 seconds.
- `469a66d`: seven missing-importer integration REDs. Dependency holder API RED
  preceded its implementation; the initial holder lane passed 53 authored checks.
- Initial integration exposed invalid descriptor ordering in the new fixture;
  sorting canonical relative strings and explicit negative refusal reasons fixed
  the test input. No early-refusal negative was credited as its intended path.
- A caught-active-reentry RED showed custody remained usable. One-shot entry
  now poisons invalid reentry. Attachment path sets are computed once per root.
- `43a861d`: 146 focused passed, 11.87 seconds.
- An intermittent seed refusal was preserved and reproduced deterministically
  using an aged access time. The original seed compared all stat fields, so its
  own read could look like changed source. The fix excludes access time while
  preserving SHA/bytes/inode/mode/size/mtime/ctime/nlink checks. This reproduction
  establishes this seed defect; it does not explain earlier unrelated anomalies.
- `42859cd`: 150 focused passed, 16.37 seconds; 1367 affected passed, six inherited
  exclusions, 77.64 seconds. Added actual native boundary characterization:
  a registered origin-relative shared dependency refuses to load through an FD,
  an unregistered persistent shared image refuses terminal success, and external
  module-cache replacement refuses. No native closure claim follows.
- One whole-branch review found three Important defects: census aggregation after
  traversal, missing namespace resources and full signal-mask restoration.
  Each reproduced RED and was fixed in one pass. The precise census regression
  observed five second-root entries where the remaining budget plus one overflow
  observation allowed three. Namespace resource reads now work, and cleanup
  restores only SIGIO membership while preserving unrelated masks.

Final source `7db611b`, serialized root/independent results:

| Scope | Root | Independent |
| --- | --- | --- |
| Four focused files | 153 passed, 16.53s | 153 passed, 16.38s |
| 28 affected files | 1370 passed, six deselected, 77.01s | 1370 passed, six deselected, 78.32s |

All four commands exited 0. Independent repetition is verification, not a second
source review or final runtime GO. Root's earlier suite logs remain locally under
`runs/source-validation/puck-v3-dependency-custody/` (ignored test artifacts).
`git diff --check` passes.

Interpreter and environment for all these commands:

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
  /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
  -m pytest -q --tb=short \
  tests/test_puck_execution_files.py tests/test_puck_worker_bootstrap.py \
  tests/test_puck_dependency_files.py tests/test_puck_worker_dependencies.py
```

The affected command is [PR #128's exact 25-file command](puck-v3-inventory-scope-source.md)
plus `test_puck_worker_bootstrap.py`, `test_puck_dependency_files.py` and
`test_puck_worker_dependencies.py`, with the same six inherited mechanics
construction-pin/missing-httpx exclusions. Default `-m pytest -q -x --tb=short`
still stops on missing FastAPI at `tests/test_lab.py`: one collection error,
0.31 seconds. No repository-wide suite pass is claimed.

## Ruling, limits and next deliverable

V2 external Python/resource consumption checks bound local dispatch and source
metadata plus selected dependency bytes/ancestors/lease notifications. Full source
hashes, full dependency census/all leases and image observations remain admission,
public full checks, native initializer and terminal boundaries. This avoids a full
31,000-file sweep/interpreter hash per import. Mutation elsewhere can be observed
at the next full boundary; this is trusted-source custody, not atomic filesystem
observation or a sandbox against admitted Python. V1 full checks stay unchanged.

The deferred review minor is resource enumeration of authenticated empty
directories: resource traversal currently derives directory names from files.

Actual installed dependency payloads were not hashed/imported/qualified. The
origin-relative ELF fixture is explicitly unsupported; real numerical runtime
compatibility and transitive native resolution remain open. Map snapshots observe
persistent file-backed images only, after initialization may already have run;
they do not prevent arbitrary trusted C execution, observe transient dlopen/dlclose
history or qualify anonymous/JIT code. Stdlib/ELF baseline remains trusted and
unqualified. Read leases assume supported Linux/filesystem behavior and a trusted
host. Deadline polling is not a hard process kill or resource envelope.

Next freeze and qualify an exact supported dependency/runtime configuration, then
connect worker v2 to the held declared inventory, envelope, reservation, scene/model
custody, native recorder, interval/clock ledger, exact-environment parent supervisor,
leases/escaped-descendant/resource handling and durable terminal close. Authored
fixtures permit source progress while real catalog access is pending. Review the
complete executable route before any actual collection. Memory replay-to-case-close
source work remains part of the same full simulation goal.

Memory amendment02 approval, catalog-access policy and prospective navigation
study decision remain pending. No actual inventory scan, original qualification
CLI, model/native owner, memory replay or study was invoked. No consumed attempt
was retried. All seven release gates stay open; CI and the physical rover stay
excluded, with all six artworks completed in simulation first.
