# Lifetime architecture amendment after authored source-02

Use the existing systemd user manager's **cached closed-unit CPU accounting**
as the external lifetime measurement interface. Do not require a dedicated raw
cgroup directory to survive exit. Source-02 observed MainPID0/ControlPID0,
success/exit0, empty ControlGroup and absent original cgroup, while the retained
unit supplied CPUUsageNSec2281239000. A worker with manager-configured CPU6:6
consumed more than the launching client's hard2 seconds, demonstrating independent
limits for this authored case. The fourth planned bounded client subsequently
stopped only that completed unit successfully (return0); all artifacts remain.

Systemd v262 `unit_prune_cgroup` caches resource accounting before removing an
empty cgroup; `unit_get_cpu_usage` reads `cpu.stat` and returns its cached value
when the cgroup is gone. This source explains the observed receipt.
[Primary source](https://raw.githubusercontent.com/systemd/systemd/v262/src/core/cgroup.c).

The project-specific finalizer should bind unique unit/InvocationID, pinned
ExecStart and runtime, live cgroup identity and enforcement, exact parent terminal
hash, final process status and cached CPU measurement. Keep the existing trusted
`run_accounted` closure/drain evidence inside the measured service. The external
finalizer adds no new daemon or generic accounting framework. Cached unit CPU
includes the service's closing tail; it excludes outside clients/finalizer and
does not establish their total charge.

Acceptance requirements still **unproved**:

1. Exact deployed systemd262.1-1-arch build/source binding and its complete cached
   accounting/closure path; upstream262 is explanatory, not a verified build pin.
2. Stable post-exit CPU readback bound to the same InvocationID. Source-02 retained
   one final read, not repeated stability samples or a final raw cpu.stat receipt.
3. Robust closure evidence accepting either verified populated0 or authenticated
   manager removal of the owned cgroup. Arbitrary ENOENT, MainPID0 alone, or a
   parent-generated success flag cannot establish complete descendant closure.
4. Live kernel memory.max/swap/pids readbacks before admission, owned ancestry,
   no unrelated processes, and no migration/escape. The probe verified configured
   unit properties, not retained live controller values.
5. Independently bounded outside administration: exact process/client topology,
   pre-interpreter limits and privilege state, plus a source-backed allowance for
   kernel limit enforcement and exit CPU. Hard2 per process is not proof of
   exactly2 final CPU seconds. This probe establishes no such numeric allowance.
6. Complete prior lane reconciliation, all finalizer/client/setup charges and
   output/control peaks, and an actual admission package with separate exact-stage
   GO. The1800 CPU/900 wall/8GiB/640MiB proposal remains unchanged.

Consequently actual whole-operation CPU and charged upper CPU remain null.
Even an eventual valid closed-measurement-plus-administration charge does not
convert sampled stopping into a strict prelaunch never-exceed1800 guarantee.
Preserve provisional-parent semantics and all scientific flags=false. Source-02's
original failed probe result remains unchanged; the mechanism findings and
authorized unit disposition are separate records. No broader implementation,
third probe, actual research launch or evidence deletion follows this amendment.
