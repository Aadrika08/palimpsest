# One-shot lifetime probe: refused before service launch

The single permitted probe invocation exited1 at `admin.py:11`, before its
first systemd client. UID1000, CPU soft/hard2:2 and core0:0 assertions preceding
that line passed. The zero-capability assertion failed. No systemd service was
launched, no worker ran, and no service stop or retry was attempted.

Retained artifacts: `admin.py`, `client.py`, `worker.py`, `admin.stdout`,
`admin.stderr`, and `refusal-capability-inspection.json`. There are no actual
service property or CPU receipts; generating those would misrepresent the
refusal. No research-data reads or production-source changes occurred.

Read-only inspection immediately afterward found UID/EUID1000; effective,
permitted and ambient capability sets0; inheritable set`0x0000000800000000`
(`CAP_WAKE_ALARM`, bit35); bounding set`0x000001ffffffffff`; NoNewPrivs0.
This inspection ran outside the refused limited process and is explicitly
labeled that way. The inherited capability caused the stricter zero-inheritable
guard to refuse, even though it was not an effective capability.

The available user manager reports systemd262.1-1-arch; running kernel is
7.2.8-9-omarchy. Availability does not establish resource accounting behavior.
First-party account quota telemetry was unavailable, hence quota is unknown.
This is an ordinary authored software refusal, not research execution.

## Architecture answer

Yes, a fixed project-specific finalizer using an already-running systemd user
manager is a minimal way to separate a hard-limited administrative client from
the service's independently configured limits. It is not a new generic cgroup
service or daemon. This probe did **not** verify that mechanism: retained cgroup
counter stability, MainPID0/populated0, memory/swap/task enforcement and a worker
exceeding the administrative2-second limit all remain untested.

The prepared single attempt would use four exact clients (occupancy check,
launch, properties, stop-empty), each under inherited CPU2:2/core0:0. The service
would use Type=exec, RemainAfterExit=yes, LimitCPU6:6, RuntimeMax8s/stop1s,
MemoryMax64MiB/swap0/TasksMax8. The authored parent would spin2.2 CPU seconds,
reap a0.05-second child, write its terminal and exit. Three empty-cgroup reads
would compare `cpu.stat` after service MainPID0. These are intended checks,
not results.

An eventual success would establish a measured service lifetime and bounded
administrative process topology. It would not by itself prove a numeric upper
charge for unmeasured finalizer exit or kernel CPU-limit overshoot. A2-second
RLIMIT_CPU is a kernel kill threshold, not an evidence-backed assertion of
exactly2 seconds final usage. `SC_CLK_TCK=100` is not proof that kernel HZ is100,
nor a bound on signal/exit CPU. Upstream kernel source compares sampled process
CPU against the hard limit and can process CPU timers via deferred task work;
it supplies no general constant here for all time through final exit. No
deployed-kernel tolerance proof was established. Therefore exact whole CPU and
charged upper CPU remain null, and the whole-operation CPU-cap gate stays open.

Source basis: [Linux CPU timer implementation](https://raw.githubusercontent.com/torvalds/linux/master/kernel/time/posix-cpu-timers.c),
especially `check_process_timers` and `handle_posix_cpu_timers`, plus
[getrlimit(2)](https://man7.org/linux/man-pages/man2/getrlimit.2.html).
Upstream master is explanatory source, not a verified match for this deployed
Omarchy kernel.

## Concrete next interface, without retrying

For a separately authorized future check, prepare a capability-dropping launcher
before the administrative interpreter (for example reviewed `setpriv` arguments
to clear inheritable/ambient capabilities and set no-new-privileges, then
`prlimit --cpu=2:2 --core=0:0 -- python -I -B -S`). Preserve the current failed
attempt unchanged and use a new nonce. Do not silently relax the guard or retry
this attempt. Pin binaries and fixed client count; disabled pager, prompting and
remote execution remain required. Confirm the manager's unit limits independently
of inherited client limits.

Production interface should publish distinct service measurement and external
administration-bound records. The former binds unit InvocationID/cgroup identity,
parent terminal digest, empty-state evidence, final counter and timestamps; the
latter must identify every outside process, its pre-exec hard limit and a justified
kernel enforcement allowance. The validator accepts only their finite sum within
the fixed1800-second allocation and remaining memory lane. Missing either record
leaves provisional preservation only. Even a valid terminal upper charge is not
a prelaunch proof that sampled resource stopping cannot overshoot1800.

No service exists from this attempt to clean up. No artifact was deleted.
