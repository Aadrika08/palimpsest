# CPU runtime installation: one bounded package-preparation unit

Goal: produce a real flat SITE from the 71 retained verified wheels, with an
installed census, exact relocations, licence bytes and an independently audited
preparation receipt. This implements the active simulation-release goal's first
exit. It grants no numerical imports, model/scene/catalog reads, physics,
collection or scientific allocation. Existing studies and consumed failures are
unchanged. This is routine trusted-tool preparation, not a new package framework.

Use the existing isolated CPU worktree on research/puck-cpu-install-v1, based on
bef485353fb122333b7921e836dde456a12cf0b5. Source files: the new
scripts/install_puck_cpu.py and tests/test_puck_cpu_install.py. Reuse existing
wheel verification, held input custody, host baseline, process supervision and
bounded report publication. Preserve their strict immutable-output limits;
monitor only stable logs with that helper. An additional sampled mutable-tree
limit covers installer output and scratch; it is an operational stop threshold,
not a hard aggregate filesystem quota or hostile-tool guarantee. UV temporary
cache symlinks in scratch are counted without following them; final SITE still
refuses every symlink and special file.

One configuration pins source, candidate/metadata/host baseline, exact 71 wheel
paths/hashes, UV 0.9.25 and CPython 3.11.15. Exclusively reserve
runs/puck-cpu-install-01 before holding inputs. Keep archives, SITE and scratch
on project disk. Recheck full wheel payloads and host/tool hashes before running,
and retained input hashes plus host prefix after normal installer return.

The exact UV call uses pip install --target SITE --python PIN --no-deps
--no-index --offline --no-build --link-mode copy --no-cache --no-config
--no-python-downloads --no-compile-bytecode -- WHEEL1 ... WHEEL71. UV still
resolves the explicit wheel requirements for metadata/compatibility; it does not
expand dependencies. Temporary cache files are allowed only in private scratch.

Bubblewrap 0.12.0 provides a private network/user/PID/mount namespace. Bind the
exact interpreter prefix, UV, its reviewed ELF closure, driver and wheel leaves
read-only; only fresh SITE and scratch are writable. Clear the environment and
set deliberate HOME/TMPDIR/locale/PATH plus SETUPTOOLS_USE_DISTUTILS=stdlib.
The selected interpreter contains one observed distutils-precedence.pth; this
value makes its shim import a no-op. UV's -I -B interpreter probe still processes
trusted global site and imports UV's bundled helpers; no zero-global-import
claim is made. The fresh target is not a probe search path. Compilation remains
disabled. No target package, console script or installed hook is executed.

Before target installation, run one authored wheel in the same namespace with
poison package code, a marker-writing .pth and an unsatisfied dependency. Require
normal exit, unchanged inert payload and no execution marker. A namespace/fixture
failure stops this unit before the 71 target wheels. No automatic rerun.

Allocation: 300 seconds normal/315 hard for the complete parent; combined sampled
RSS at most 1536 MiB; at most 3 child-group processes; worker 2 GiB address space,
120 CPU seconds, 1 GiB individual file and 256 file descriptors; 1 MiB per log
stream. Operational mutable SITE+scratch threshold 6 GiB, at most 100,000 entries;
final installed namespace at most 3 GiB, 40,000 files, 5,000 directories, 1 GiB
per file; report at most 16 MiB. Require 4 GiB free disk and 2 GiB MemAvailable
before invocation and a sampled 4 GiB free-space floor during installation.

Accept only a normal zero return with empty owned process groups, all immutable
payloads preserved except declared RECORD/script rewriting, 71 exact distribution
identities, complete actual file census and copied licence contents. Retain exact
commands, namespace probe, baseline checks, logs and supervisor result. Generate
no bytecode or target .pth. An independent terminal audit rehashes the entire
installed tree and checks raw wheels/RECORDs, scripts, metadata and licence copies.
A late/nonzero return overrides an artifact PASS. Preserve partial output on
failure, then decide the next separately numbered change prospectively.

Sequence: focused regression checks; authored fixture and source/configuration
review; commit frozen source/configuration; invoke exactly once; independent audit;
commit/push evidence on a draft stack based on PR142. Do not merge. Passing this
unit closes installation preparation only; numerical qualification and all seven
release gates remain open.

Pinned UV source behavior was reviewed at upstream tag 0.9.25 / commit
38fcac0f3668986727aa7ba6290e8cb94c1dbe5f: uv-python interpreter.rs (probe),
target.rs (flat installation scheme), uv-install-wheel install.rs/wheel.rs
(relocations/launchers/RECORD), uv-cache cli.rs/lib.rs (temporary cache), and
uv lib.rs (configuration precedence). This is source inspection of the pinned
version, not binary/source reproducibility proof.
