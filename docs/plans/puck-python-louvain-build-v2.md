# python-louvain build 02: prospective namespace correction

This separately numbered ordinary build preparation stage continues the
[unchanged v1 build specification](puck-python-louvain-build-v1.md), with only the
explicit changes below. It is not a retry of configuration01. That invocation
remains failed and consumed; its [raw evidence and audit limitations](../reports/puck-python-louvain-build-01.md)
remain unchanged. Original source commit8895441e3d1be8492378606a10d6391b5fdc1f86
and evidence commitc729159 preserve its complete source/configuration/outcome.

## Changes and source-supported reason

- Require explicit bubblewrap unshare-user as well as unshare-all before
  disable-userns. Version0.12's [argument parser](https://raw.githubusercontent.com/containers/bubblewrap/v0.12.0/bubblewrap.c)
  sets unshare-all's user option to try, then checks disable-userns before implied
  user-namespace setup. Configuration01 stopped at that check; no worker ran.
- Accept exactly bubblewrap's documented PWD=/source addition to the seven
  explicitly set environment variables. Check both PWD and actual cwd equal
  /source; all other inherited environment remains refused. The same source's
  xsetenv(PWD,new_cwd) explains the authored probe's first post-parser refusal.
- Require kernel ST_RDONLY mount flags for every declared read-only mount.
  Continue file-creation refusal checks except on procfs, whose root refuses
  arbitrary files with ENOENT even on a writable mount. ST_RDONLY is the proc
  check. An authored negative refuses a writable proc mount before file creation.
- Exclusively reserve runs/puck-python-louvain-build-02. The parent now accepts
  only configuration02's output. Configuration01 cannot be relaunched under this
  source. The JSON schema remains v1; this is a source and invocation amendment.
- Add this amendment to the source capsule. Retain original v1 specification,
  source archive, backend pin, host baseline, all limits, import restrictions,
  subprocess/exec/session seccomp denials and false authority claims unchanged.

## Verification and one actual exit

An explicitly opted-in authored namespace test reproduced the parser defect,
then the PWD and procfs-probe mismatches, before the above fixes. It uses only
fresh authored source/backend directories and the stdlib worker; no acquired
backend or target code executes. Final namespace/proc slice:3 passed in0.19s,
including a real namespace probe with private network/no external route,
read-only mounts, empty HOME, exact256MiB scratch and all eleven denied syscalls.
The intermediate diagnostic logs and original actual failure are retained.

Use the new exact source-pinned puck-python-louvain-build-02.json only after
independent source/configuration review. All v1 allocation boundaries remain:
120s normal/135s hard;768MiB sampled combined RSS; at most3 group processes;
worker512MiB AS/60s CPU/8MiB file/128FD;256MiB private scratch;128MiB retained
output;256KiB wheel transfer;1MiB logs/stream;2GiB free disk/1GiB available RAM.
One new exact backend request is allowed by this separately numbered stage.
There is no dependency resolution, repeated target build or automatic rescue.

The namespace preflight must pass before the actual verified backend fixture
executes, and the fixture must pass before the sole target build. Require unchanged
staged trees and host baseline, full wheel payload/METADATA/WHEEL/RECORD evidence,
normal cleanup, externally observed exit0 and an independent terminal audit.
A late/nonzero return overrides a prior artifact result. Preserve every failure.

No numerical-runtime installation/qualification, model, native collection,
renderer, physics, protected catalog, development/held-out study or scientific
attempt is authorized. This output closes only the missing package-artifact gap;
the complete CPU runtime and simulator episode remain subsequent milestones.
