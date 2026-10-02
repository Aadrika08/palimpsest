# Lab hardening verification

Run these commands from the qualified checkout with its cached simulation
environment and assets. Each output directory must be new. Preserve failed
reports alongside successful reruns; a short run never satisfies the hour gate.
Use one actual EGL/runtime measurement at a time, after the runtime is frozen.

## Recovery boundaries

```sh
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p test_recovery.py -v
```

The tests exercise a spawned owner exiting abruptly after 32 published ticks
and one buffered tick; a chunk rename followed by event publication failure;
and a real recorder disk fault propagated through an Engine with explicitly
labelled fixture physics. They assert that the readable prefix remains exactly
the 32 published ticks, failed requests settle, recording is not retried, and
the failed Engine stops advancing and closes its world. They do not substitute
fixture physics for MuJoCo continuation evidence.

Treat an incomplete run as recovery evidence. Read its verified published
prefix and failure events; do not infer that an unacknowledged command applied,
publish an orphan chunk, or resume the uncertain owner. Close the failed owner
and start a fresh session. Use a validated registered snapshot for a declared
branch. A new run ID and explicit provenance distinguish the branch from the
failed source. Keep `manifest.json`, `events.jsonl`, `supervisor.json`, recorder
chunks, and the failed verification report for diagnosis.

## Sustained active execution

```sh
PYTHONPATH=src .venv/bin/python scripts/verify_performance.py \
  --output runs/performance-600 --ticks 600
```

This uses actual spawned CPU manual and teacher owners in sparse-navigation
with checker texture and EGL. It requires at least 600 recorded ticks per
controller, validates contiguous episode ticks and the 20 ms simulated control
interval, and verifies that pause or termination freezes advancement. A teacher
that terminates early is reset into another explicitly recorded episode until
the total reaches the requested count. Loading and paused time are excluded
from the worker's active execution telemetry.

For an independently labelled natural-completion probe, add `--finish-episode`.
The final episode continues to termination or truncation after the minimum tick
count; the verifier does not issue an operator pause at that threshold. The JSON
records the completion protocol and minimum ticks. Its threshold, bounded
timeout and recorded continuity checks are unchanged. Retain earlier operator
pause reports rather than treating the protocols as interchangeable.

`worker_active.rtf` measures advanced simulation time divided by active owner
wall time, including owner-side logging and display work; it must be at least
one. `outer_rtf` additionally includes monitor polling and inter-episode reset
time. `kernel_rtf` uses recorded policy and physics/camera latencies and excludes
IPC, logging and display; it cannot qualify end-to-end execution by itself.
Copied transport sample counts do not measure browser frames. Browser paint,
input responsiveness and visual correctness require the separate UI gate.

## OS-level offline proof

```sh
PYTHONPATH=src .venv/bin/python scripts/verify_offline.py \
  --output runs/offline-cached --duration 55
```

The driver creates a mapped user plus network namespace with `unshare`. It
checks that both namespace identities differ before enabling only the child's
loopback interface. `network.json` records interfaces, all IPv4/IPv6 routes,
external connection failures with `ENETUNREACH`, and observed descendant
namespace identities. The nested actual API smoke exercises cached CPU manual
and teacher runs, authenticated WebSockets, preview/edit, masks, reset,
snapshots, branches, and exact action/policy replays without external routes.
The parent records unchanged namespace identities. It changes no host
interface, firewall, route or sysctl.

If this host forbids namespaces, the report is `blocked` with the exact
`unshare` error. Proxy variables, removed credentials, and an assumed cache are
not OS-level offline evidence. This script qualifies only the measured cached
CPU manual/teacher smoke, not full Flynn or a browser offline session.

## Mixed API smoke and hour gate

```sh
PYTHONPATH=src .venv/bin/python scripts/verify_endurance.py \
  --output runs/endurance-smoke --duration 55 --cycle-seconds 15 \
  --pause-seconds 0 --sample-seconds 2

# Run after the runtime/storage freeze.
PYTHONPATH=src .venv/bin/python scripts/verify_endurance.py \
  --output runs/endurance-hour

# First verify the four model loads and resource budgets in one CPU Flynn cycle.
PYTHONPATH=src .venv/bin/python scripts/verify_endurance.py \
  --output runs/endurance-flynn-smoke --controllers flynn --duration 240 \
  --cycle-seconds 120 --pause-seconds 0

# Run after the representative smoke and runtime freeze.
PYTHONPATH=src .venv/bin/python scripts/verify_endurance.py \
  --output runs/endurance-mixed-hour --controllers manual teacher flynn \
  --cycle-seconds 120
```

The default duration is 3600 seconds. This is a browser-independent mixed
HTTP/WebSocket workload with modest tick bursts and paused intervals. Every
cycle records its controller and operations. It measures HTTP receipt latency
separately from the observed applied-boundary latency, which includes polling.
It requires a complete cycle for every requested controller, the functional
operation set, completed duration, one owner,
configured resource budgets, and clean shutdown. The hour gate additionally
compares server RSS/FD/thread p95 in the 25–50% and 75–100% windows. These are
finite observed growth limits, not a mathematical guarantee about future runs.

Manual and teacher remain the defaults. Optional `--controllers flynn` selects
the actual full policy on CPU for the same mask/edit/step/reset/snapshot/branch
and exact action/policy replay flow. Each cycle loads a source, branch and two
replay owners sequentially. The 180-second per-owner wait remains bounded;
the proposed 240-second smoke must demonstrate that this host fits it and the
unchanged 8 GiB RSS / 2 GiB storage budgets. A 55-second manual/teacher smoke is
not full-policy evidence. Controller RTF and latency are measurements here;
this mixed gate imposes no RTF ≥ 1 threshold on CPU Flynn and qualifies neither
CUDA nor browser performance.

Periodic `resources.jsonl` samples cover the server and its descendants' RSS,
FDs, threads, run/export root bytes, and free disk. `commands.jsonl` retains
receipt/application timings. `server.stdout.log` and `server.stderr.log`
retain load or recorder failures. The script bounds samples, command timings,
ticks, duration and storage, and starts new runs well before the per-run command
ID limit. Its budgets supplement the application's enforced storage quotas;
they are not replacements for those quotas. The driver also passes its
`--max-bytes` and `--min-free-bytes` values to the application's aggregate byte
quota and free-space floor. The harness's whole-root sampler includes auxiliary
reports outside the managed run/export roots.

SIGINT/SIGTERM and deadlines trigger owner close and owned-process cleanup.
The drivers terminate only their own server/namespace process groups and
verified descendants; they never disconnect the host or kill unrelated jobs.
A startup failure still produces a failed report. Cleanup failures or owned
survivors make the report fail rather than hiding behind a successful workload.
Log-drain threads have bounded joins; a blocked drain or final `fsync` makes the
run fail even if its child exited zero. Python cannot cancel a thread blocked in
kernel I/O. Its file descriptors remain owned by that thread until the call
returns or the process exits; the parent does not close and reuse a descriptor
behind the blocked reader. This is a reporting bound, not a promise to cancel
an uninterruptible kernel storage operation.

## Release evidence boundaries

Keep recovery, sustained active execution, offline operation, hour API
endurance, browser accessibility/performance, and controller continuation as
separate results. Manual/teacher results do not qualify full Flynn. CPU
continuation does not qualify CUDA exactness; the recorded upstream CUDA CSR
nondeterminism finding remains a failed/inexact qualification. Report host,
software profile, source identity, command, artifact path, status and limits.
The browser sampler must separate WebSocket arrivals, DOM updates and browser
animation opportunities; none alone establishes presented camera FPS.
