# Memory source lifetime: authored mechanism probes

Actual source qualification remains **incomplete**. These two probes used only
tiny authored standard-library programs. They opened no research model, raw
recording, snapshot or protected namespace. Ordinary software verification is
excluded from the research CPU ledger; no new research charge is asserted.

The first probe refused in preflight because its inherited capability set was
nonzero; no service launched. The second explicitly dropped inherited and
ambient capabilities and set no-new-privileges before its bounded administrator
started. A manager-created worker used CPU limits 6:6 independently of the
administrator's 2:2 limit. Its parent consumed 2.225748 CPU seconds and its reaped
child 0.050420 seconds. The retained service reported CPUUsageNSec=2281239000.

The second probe still failed its original acceptance test: the service manager
removed the cgroup after exit, so the expected surviving raw cgroup counter was
unavailable. A same-attempt property read found the completed unit active/exited,
MainPID=0, ControlPID=0 and an empty ControlGroup. The fourth fixed client stopped
only that completed unit successfully. There was one service launch in this
probe and no third probe. Both failed results and all original receipts remain.

The [architecture amendment](lifetime-architecture-amendment.md) explains the
cached service counter and six remaining acceptance requirements. This is a
partly verified accounting mechanism, **not** a verified whole-operation CPU
bound, native runtime qualification, preservation result or execution approval.
Whole-operation actual CPU and its justified upper charge remain unknown.

[Custody manifest](custody-manifest.json) records the 39 copied source artifacts;
all copied bytes were compared with their retained originals. The manifest does
not include itself or this explanatory README. Internal paths in the probe
receipts identify the original working location; copying them does not create a
new run or alter their claims. No raw deletion or pruning is authorized.
