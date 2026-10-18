# CPU package payload acquisition v1

This is the first actual-payload preparation step toward the
[CPU runtime candidate](puck-cpu-runtime-candidate-v1.json). It verifies the
candidate's 70 wheels plus the locked python-louvain0.16 source archive.
It does not build, install, import numerical packages, qualify runtime/native
execution, inspect protected project catalogs, run a model or scene, collect
episodes, train or open held-out data. Existing preparation01, qualification01
and observations01/02 remain consumed. This is a different, package-only stage.

## Frozen scope and acceptance

The separately pinned configuration selects exactly the candidate's full
distribution set through its authenticated metadata assessment. Ordinary wheels
retain uv.lock URLs/size/SHA256; CPU Torch and torchvision retain their official
CPU-index identities. There are71 HTTP200 GETs at most, one per exact URL.
Only files.pythonhosted.org and download-r2.pytorch.org are supported; redirects,
proxies, compression encoding, changed lengths, wrong hashes and fallback
versions are refused. There is no network retry.

Each wheel's full archive hash is checked before payload examination. The offline
verifier streams every stored/deflated member, checking actual size and CRC,
METADATA identity/hash, WHEEL/filename tag consistency and complete RECORD
hashes/sizes. It refuses unsafe names, aliases, special members, unsupported
compression, signatures and inconsistent records. There is no extraction.
The full source archive is hashed and retained; its members and build backend
remain uninspected by this stage. Licence candidates are inventoried and their
bytes retained in archives; licence acceptance remains false.

An independently reviewed exact source/configuration precedes invocation.
Success requires the parent to exit0, a successful bounded worker and terminal
outcome, all71 archive identities,70 complete wheel manifests and the source
archive manifest, matching configuration/source pins and no owned group survivors.
An independent terminal audit checks these actual files and process outcome.
A retained failed stage is not a pass and is not automatically rerun.

## Bounds and retained output

Configuration01 uses600s normal return including parent configuration/preflight
and615s last operational process-group kill clock,20s per socket operation,
1GiB sampled combined parent/worker RSS threshold,2GiB worker address-space cap,
256 worker FDs and one worker process. Require4GiB disk free and2GiB MemAvailable
at admission. RAM readings are transient; there is no RAM reservation or hard
RSS/WCET guarantee. Kernel-blocked I/O and a trusted host/stdlib remain explicit
operating assumptions.

The exact archives total385,328,518B. The stage allows400MiB downloaded bytes,
256MiB per archive,512MiB aggregate retained output,2GiB decoded wheel bytes,
32,768 wheel entries,1GiB per decoded member,4MiB metadata/RECORD and16MiB per
manifest. The supervisor admits at most160 regular single-link output files and
three descendant directories. The legacy supervisor's32-file/two-directory
default remains unchanged; package acquisition declares its larger finite pair.
The ZIP central directory is parsed by stdlib before the entry-count check;
the authenticated fixed archive set and parent resource monitor bound this scope,
not a claim to sandbox arbitrary hostile archives.

One exclusive runs/puck-cpu-payload-acquisition-01 namespace contains archives,
manifests and outer logs. Allocated archive names stay fixed from the first byte through stage exit,
avoiding transient link counts and disappearing names in the concurrent monitor.
Partial bytes remain under those allocated names on failure. A filename never
means verified: acceptance requires its verified manifest plus a successful
audited parent outcome. Files and manifests use exclusive creation and never
replace retained evidence. No output directory is reused. Source/config/interpreter identities are held and
rechecked through worker execution; the terminal outcome is published after
successful custody teardown. Final acceptance also requires the independently
observed process exit and outcome audit, not a success JSON alone.

## Source and workflow

The fixed entry is scripts/acquire_puck_cpu_payloads.py, with
src/palimpsest/puck_package_payloads.py for offline wheel verification and the
existing descriptor/publication/process helpers. The exact configuration pins
all project source inputs and the resolved CPython3.11.15 executable. Acquisition
runs with -I -S -B, ordinary trusted CPython/stdlib/TLS/CA and host baseline,
no site startup, no numerical packages and no loader overrides. It does not
establish the later numerical runtime's complete stdlib/native/EGL closure.

1. Check authored success/refusal tests and preserved default namespace policy.
2. Review source and the exact canonical configuration independently.
3. Invoke configuration01 once using its SHA256; preserve success or failure.
4. Independently audit the terminal process and archive/manifest identities.
5. Inspect the authenticated python-louvain source and prepare its separately
   bounded exact build-toolchain configuration. Installation, actual installed
   namespace and licences, CPU/native/EGL staging, four-import qualification
   and the complete simulator episode remain subsequent work.

The [wheel format](https://packaging.python.org/en/latest/specifications/binary-distribution-format/)
defines mandatory archive RECORD verification and .data relocation.
The [installed RECORD specification](https://packaging.python.org/en/latest/specifications/recording-installed-packages/)
describes the separately changed installed namespace. This stage does not treat
archive paths as installed paths.
