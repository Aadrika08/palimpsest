# Corrected authored lifetime probe: partial mechanism success

One corrected software probe was explicitly authorized after source-01's
capability-preflight refusal. Source-01 is unchanged. Source-02 launched one
authored service, with no model, simulator, raw/SNP/catalog or other research
inputs. It is not actual source qualification and is not a scientific retry.

## Observed

The pre-interpreter chain used `setpriv --inh-caps=-all --ambient-caps=-all
--no-new-privs -- prlimit --cpu=2:2 --core=0:0 -- python -I -B -S admin.py`.
Local `setpriv --help` confirmed those flags before launch. The admin, client
pre-exec receipts and worker record show UID1000, effective/permitted/inheritable/
ambient capabilities0 and NoNewPrivs1; the normal bounding set remains nonzero.
Admin/client CPU limits are2:2; manager-created worker limits are6:6, core0:0.

The source-02 parent consumed2.225748 CPU seconds before terminal publication,
exceeding the launching admin's hard2 limit, and reaped its authored child with
0.050420 CPU seconds. Its terminal fsync and interpreter return follow those
observations. The retained systemd unit reports success/exit0 and
CPUUsageNSec2281239000 (2.281239 seconds). The5.071ms difference from the sum
2.276168 is not an isolated measurement of terminal overhead: it also includes
other unit startup/exit accounting differences.

Unit: `palimpsest-memory-lifetime-probe-20261105-source-02.service`.
InvocationID: `d51cbb4a162049829394c37ed5fb09c7`.
Post-exit properties: active/exited, MainPID0, ControlPID0, empty ControlGroup,
Type=exec, RemainAfterExit=yes, KillMode=control-group, NoNewPrivileges=yes,
MemoryMax67108864, MemorySwapMax0, TasksMax8, RuntimeMax8s, stop timeout1s,
LimitCPU/LimitCPUSoft6, LimitCORE0. These establish configured unit properties;
the probe did not preserve live kernel memory/pids controller readbacks.

The original admin result is **failed**, retained unchanged: after worker exit,
opening the dedicated `cgroup.events` raised FileNotFoundError. RemainAfterExit
retains the unit, **not its empty cgroup directory** on this manager. The original
admin ran clients1/2, recorded observed self CPU0.045656844 and reaped-client
CPU0.051095, and exited1. Those values exclude later observation and are not a
complete operation total. The already-planned third client subsequently read
the retained properties under the same capability/CPU restrictions; this was
same-attempt observation, not another service launch. Separate follow-up JSON
confirms the original worker cgroup path is absent.

## What the primary source supports

Systemd v262 `src/core/cgroup.c::unit_prune_cgroup` caches CPU before removing
an empty cgroup. `unit_get_cpu_usage_raw` reads `cpu.stat`'s `usage_usec`;
`unit_get_cpu_usage` supplies the cached value when the cgroup is gone. This
explains the measured retained property without inventing a raw-counter receipt.
[Primary source](https://raw.githubusercontent.com/systemd/systemd/v262/src/core/cgroup.c).

The source is the upstream262 tag; the installed manager reports262.1-1-arch.
Exact distro build/source identity was not established. One retained read is
evidence of availability, not a repeated counter-stability experiment. No
`populated 0` snapshot was captured, and no raw `cpu.stat` file was retained.

## Prerequisite verdict and next implementation interface

Confirmed: capability-drop correction; per-process hard limits before Python;
manager-created worker independent of the client's lower hard limit; authored
parent/descendant completion; retained post-exit CPU usage and terminal identity;
fixed small client topology; requested unit properties.

Not confirmed: repeated terminal counter stability, live kernel memory/task/swap
readbacks, a recorded populated0 state, deployed manager exact source identity,
or a source-backed numeric kernel CPU-limit enforcement/exit allowance. Therefore
not all source-02 prerequisites passed. `actual_whole_operation_cpu_seconds`
and `charged_upper_cpu_seconds` remain null. No native research source is qualified.

Choose the existing manager's **cached closed-unit accounting** interface for
the minimal project finalizer; do not require a raw cgroup file to survive exit.
Bind InvocationID, unique unit name, exact ExecStart/limits, worker cgroup identity
captured while live, MainPID0/ControlPID0, successful terminal status, and its
parent receipt hash. Validate either a retained empty cgroup or source-backed
manager removal/empty state without interpreting arbitrary ENOENT as closure.
Keep actual ancestry/drain obligations from the trusted process helper. Record
missing counters as unknown, not zero. Capture live enforcement before releasing
the research admission gate in any eventual implementation.

This existing-manager finalizer is project-specific and requires no new daemon.
It closes the service's measurement tail in principle; independently bounded
outside administration remains necessary. Hard2 is a kill threshold, not proof
of exactly2 final CPU seconds per process. Neither this successful child nor
SC_CLK_TCK100 establishes kernel HZ, bounded signal handling, or exit CPU.
Do not approve an upper charge by multiplying2 by the client count without a
justified enforcement allowance. The earlier1800-second absolute-cap concern
therefore remains; a passing after-the-fact charge is not a strict prelaunch cap.

All source/logs/receipts remain in this directory. The original failure result
is not rewritten to green. No automatic third probe is authorized or performed.
Same-attempt empty-unit disposition is recorded separately after root review.
