# Dedicated CPU preparation and held-import supervisor

This implements the next source dependency in
[checkpoint A](https://github.com/Aadrika08/palimpsest/blob/research/simulation-completion-next/docs/plans/simulation-release-execution-goal.md).
The exit of checkpoint A remains one actual recorded, replayed and exported
simulator episode. Authored packages establish the supervisor route only.

The dedicated entry is `scripts/qualify_puck_cpu_held_runtime.py`, with an externally
hashed, canonical configuration selecting exactly one phase. Preparation uses
`runs/puck-cpu-held-preparation-01`; qualification uses the distinct
`runs/puck-cpu-held-qualification-01`. Existing allocations and historical parents
are preserved. No installed-stack configuration or invocation is implied by this
source contract.

The preparation parent authenticates its complete source roster and sixteen input
roles: accepted inventory/layout/result/snapshot/configuration/audit/index;
ordinary observation configuration/report/result/audit/index; original host
baseline; native metadata05; CPU candidate; and the generated helper. Current pins
must equal the successful observation's selected inputs and the archived evidence
rows. The accepted configuration's original frozen bytes and its writer's compact
JSON+LF retained representation remain separate identities.

The byte-only planner constructs four source roots: SITE, selected `/usr` leaves,
selected `/etc` leaves and the generated helper. It emits a copy-only dependency-v2
registration with no import mappings. A private data worker holds the exact SITE
file/directory namespace, streams all declared bytes to tmpfs, then attaches the
candidate under dependency-v3. Alias paths remain outside regular-file forests.
The generated helper is prospective source; no historical scratch-byte identity
is claimed. The accepted inert bytecode stays data.

Preparation owns a 0700 host tmpfs directory at its frozen `/tmp` path and binds it
at `/puck/staged`; the copier creates `inputs/root-0000` through `root-0003` there.
Qualification binds only that persisted input tree read-only at the same private
paths. It checks the prepared root device/inode identities before and after use,
rebuilds the accepted byte plan, compares its files/distributions/profile, and
lets the new held worker independently rehash, census and lease every input.
This is fresh custody in each consuming process, not a continuous lease across
separate parent invocations.

Qualification preserves source-bootstrap-v3 and qualification-v3. It imports
NumPy2.2.5, Torch2.9.0+cpu, torchvision0.24.0+cpu and MuJoCo3.3.6 in that order.
The actual receipt must contain every declared native-cache binding, exact
versions and counts, expected missing-import declarations, intact interpreter
identity and false broader authority fields.

Preparation uses the observed PID1 data-worker layout. Qualification keeps the
namespace's PID1 reaper and uses a trusted original-Python `setsid`/`execv` launcher
for the PID2 worker. This preserves the worker's existing real-parent, dedicated
session and exact argv checks. Its supervisor explicitly tracks recursive
process descendants and observed PID/start-time identities, including the new
session, for RSS, counts, termination and survivor checks. Legacy callers retain
process-group supervision. These are operational observations; they do not prove
hostile fork containment or hard timing bounds. The isolated namespace and
`--die-with-parent` remain in force.

Both phases have a 180-second normal return limit, 190-second child kill limit
and 200-second outer kernel alarm, retained through closure, publication and
terminal output. Limits include 2GiB sampled parent-plus-owned RSS, 8GiB address
space, 64MiB output and private scratch, 16MiB per written file, 40,000 descriptors
and at most three owned processes. Preparation requires 4GiB available RAM and
2GiB free tmpfs; qualification requires 2GiB available RAM and 256MiB free tmpfs.
Both require 4GiB free project storage. A fresh named regular-file probe verifies
tmpfs admission without weakening the regular-file native identity API.
The planned 1,318,494,346 content bytes are not full-stage RAM admission.

The next actual-stage exit requires a separately frozen and independently
reviewed configuration, fresh resource admission, normal zero parent/worker
returns, exact custody/version/cache receipts, no surviving processes or leaked
handles, and an independent terminal/byte audit. Failure retains its allocation
and evidence; it does not authorize an implicit retry. No actual model, scene,
physics step, inference, study, protected catalog read, renderer/operator session,
CI, merge, purchase, cloud or physical rover is part of this source unit. All seven
release gates remain open.
