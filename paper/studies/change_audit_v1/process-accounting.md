# Trusted process accounting helper

`process.py` prepares ordinary software execution. It does not select a research
budget, launch a study by itself, import a model, establish sampling eligibility,
or certify scientific conclusions.

## API and caller contract

```python
result = run_accounted(
    command, cwd=directory, env=environment,
    stdout_path=stdout_path, stderr_path=stderr_path,
    wall_seconds=wall_limit, cpu_seconds=cpu_limit,
    max_log_bytes=1024 * 1024, monitor=check_storage,
)
```

The caller must be a single-threaded Linux process with no preexisting direct
children. Concurrent calls, ignored SIGCHLD, invalid limits, and existing log
paths refuse admission. The helper uses only the standard library and glibc;
`pidfd_open`, `pidfd_send_signal`, `/proc`, `fork`, `waitid`, and `wait4` must be
available. It creates a private forked supervisor, not a caller-wide subreaper.
The supervisor alone enables `PR_SET_CHILD_SUBREAPER`.

This is a trusted-job helper. The worker and its descendants must preserve normal
Linux child resource accounting: wait for exited children or leave them to be
adopted, and do not install SIGCHLD=SIG_IGN/SA_NOCLDWAIT, evade ownership, interfere
with the supervisor, or hand descriptors to unrelated processes. It is not a
sandbox for hostile programs. A worker should import threaded libraries only
after exec. The monitor callback runs in the supervisor's forked memory, so its
ordinary Python state changes are not reflected in the parent. It must be trusted,
short, and nonblocking. A separate parent wall guard sends pidfd SIGTERM after
the wall deadline plus a quarter-second allowance. SIGTERM interrupts an active
callback, while critical launch and accounting sections defer it until their
next safe stop check. Callbacks must not catch or suppress BaseException or
change signal handling. Kernel scheduling and uninterruptible system calls can
still delay enforcement; this helper is not a hard realtime containment system.
A truthy return value requests `monitor_stop`; exceptions request `monitor_error`. Its
snapshot includes elapsed time, sampled worker CPU, and observed/retained log
sizes. The monitor applies storage policy owned by its caller.

## Ownership and drain

Both supervisor and worker wait at admission gates until their parent has pinned
their direct-child identity using a pidfd and verified start ticks before and
after pinning. No process groups are signalled. A private supervisor can safely
infer that a newly adopted direct child belongs to its single job; it pins that
child before signalling. No discovered PID is ever signalled by a raw `kill`.
When the leader exits or any limit requests stop, direct children receive SIGKILL
through retained pidfds; their remaining descendants become direct adopted
children and undergo the same procedure. Detached sessions are included.

`waitid(WNOWAIT)` observes exit without releasing identity; `wait4` then reaps that
exact child and retains its usage. Only `ECHILD` proves the process tree drained.
A three-second cleanup deadline bounds repeated cleanup attempts. Unknown pidfd,
wait, discovery, or cleanup failures preserve error details and force
`accounting_complete=False`. An unresolved tree also has `tree_drained=False`.
The caller must refuse further work in either case; missing accounting is `None`,
never an invented zero. Do not assume that a failed drain has removed every
process. No retries or evidence deletion are performed.

The parent reads the result pipe without blocking and retains its supervisor
pidfd through exact wait4. A transport read/allocation error sends cooperative
SIGTERM, closes the failed result reader so a drained supervisor cannot block
writing its report, and reaps the supervisor before returning unknown accounting.
Other post-fork exceptions run the same containment in finally before propagating.
Loss of the supervisor report leaves both completion flags false even if parent
wait4 supplies an observed aggregate; that number alone cannot prove drain.

## CPU and memory fields

Each reaped record contains `user_seconds`, `system_seconds`, their sum, exit
code, and `maximum_child_rss_kib`. Linux wait4 usage includes descendants already
waited by that child. Summing the records therefore includes waited descendants
and separately adopted descendants exactly once under the trusted-job contract.
`maximum_child_rss_kib` is Linux's largest individual child RSS, not simultaneous
whole-tree memory and not a sum of RSS values.

When accounting is complete:

- `worker_cpu_seconds` sums worker-tree wait4 records.
- `subtree_cpu_seconds` is the parent's authoritative wait4 usage for the
  supervisor, including its waited worker descendants.
- `supervisor_cpu_seconds` is `subtree_cpu_seconds - worker_cpu_seconds`.
- `parent_cpu_seconds` measures parent RUSAGE_SELF from API preflight through
  receipt/reaping, before final result assembly and descriptor cleanup. A caller
  that needs complete coordinator charging should meter the entire caller phase.

Charge `subtree_cpu_seconds + parent_cpu_seconds` for that measured interval.
Adding worker CPU again would double count it. The `*_observed` fields preserve
partial measurements if accounting is incomplete; they are not complete totals.

The kernel enforces per-process RLIMIT_CPU at `ceil(cpu_seconds)` soft seconds
and one second higher hard limit. The supervisor also samples aggregate worker
CPU with `/proc` plus reaped usage and stops when the sampled threshold is reached.
Sampling is racy, rounded to clock ticks, and can both miss concurrent exits and
briefly double count a wait transition. It is a stop mechanism, not an exact
aggregate ceiling. Wall checks run every loop (nominally ten milliseconds),
subject to kernel scheduling, proc scanning, and monitor latency. Reserve budget
headroom for polling, supervisor CPU, and cleanup; use final complete accounting
for the aggregate ledger. Limits do not promise zero overshoot.

## Bounded logs

Worker stdout and stderr go to native pipes. The supervisor drains each stream
in bounded chunks and exclusively creates mode-0600 output files. It retains
only the first `max_log_bytes` bytes of each stream, marks `clipped=True`, and
requests `log_limit` on overflow. Remaining pipe bytes are drained/discarded
while the owned tree stops; no unbounded output string is accumulated. These
limits bound each retained log prefix even between monitor checks. They do not
restrict files the worker writes directly; the caller's monitor must check those
against its own policy. Partial output is preserved on every failure.

## Primary contracts

- [PR_SET_CHILD_SUBREAPER](https://man7.org/linux/man-pages/man2/PR_SET_CHILD_SUBREAPER.2const.html)
  defines orphan adoption and subsequent waiting by the subreaper.
- [wait4](https://man7.org/linux/man-pages/man2/wait4.2.html) supplies resource usage
  with exact child reaping;
  [waitid WNOWAIT](https://man7.org/linux/man-pages/man2/waitpid.2.html) retains status
  for that later reap.
- [getrusage](https://man7.org/linux/man-pages/man2/getrusage.2.html) defines CPU,
  waited descendant propagation, and maximum-child RSS semantics.
- [pidfd_open](https://man7.org/linux/man-pages/man2/pidfd_open.2.html) and
  [pidfd_send_signal](https://man7.org/linux/man-pages/man2/pidfd_send_signal.2.html)
  define stable process references and signalling.
