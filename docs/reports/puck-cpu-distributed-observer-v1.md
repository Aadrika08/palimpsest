# Ordinary CPU observer: component verified, integration pending

Source commit `e2f3242` adds the fixed external observer and its authored tests.
The independent root rerun passes **57 checks in 1.49s**, with external test exit0
in 2.218849920s and unchanged source bytes. This verifies the observer component;
the new parent epoch and independent outcome/identity/full-byte auditor remain
unfinished. No real configuration, metadata observation or simulator episode ran.

## Implemented behavior

The observer accepts only the numbered03 configuration identity and fixed parent,
interpreter, output and installation paths. It authenticates the canonical
configuration and sorted distinct source pins, including the parent, worker and
observer, before launching the fixed isolated parent command. Complete source,
input and role closure remain the parent and independent auditor's obligations.

It reserves private exclusive raw stdout/stderr and transport receipt files,
records the command, environment, configuration pin, observed return code and
elapsed time, and hashes the retained streams. Normal and launch/nonzero/timeout
failures retain false-authority receipts. The bounds are 210s normal, 5s cleanup,
225s outer alarm, 16MiB per raw stream, 64KiB per receipt, 64 sampled identities,
40,000 descriptors and 8GiB per-process address space. Child file limits also
apply when authored tests call the observation function directly.

Process evidence consists of sampled PID/start identities. Cleanup rechecks those
identities before signaling and retains survivors. Sampling is not exhaustive,
and a PID/start check followed by a signal is not atomic lifetime proof. This
component does not replace the parent's process-group supervision or the final
independent closure audit, and makes no hostile-containment or timing guarantee.

## Checks and retained evidence

The [evidence index](puck-cpu-distributed-observer-v1/evidence-index.json) binds
the two implementation files to their source commit and retains 18 byte-identical
log/command/result artifacts totaling 97,229B, including two empty stderr files.
Earlier logs do not retain every intermediate source version. They document
observed test results; the final source and command are the reproducible component.

The initial system pytest launcher fails because `pygments` is absent. The valid
initial RED then has 48 missing-observer failures. The first implementation has
46 passes/two failures: the pinned interpreter lacks the proposed pidfd APIs.
The implementation uses the stated sampled PID/start limitation instead. Genuine
path, directory-token and API stream-flood regression failures are also retained,
followed by their fixes. The final agent run passes 57 checks in 1.70s; root
independently repeats all57 in 1.49s. The two additional CLI path regressions pass
against the already fixed production parser; no new RED is claimed for those.

The focused suite covers authored separately executed parents, exact CLI flags
and inherited limits, normal/nonzero/launch failures, timeout/child cleanup,
bounded output and receipts, stale sampled identities, source/configuration
tampering, canonical paths, symlinks, exclusive allocation and reentry refusal.
The earlier 55-case root run is retained as well.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  /home/utkarsh/Work/shraddha/brain/.venv/bin/python -m pytest -q \
  -p no:cacheprovider tests/test_puck_cpu_distributed_observer.py
```

## Remaining before actual execution

Connect the closed new parent epoch to the already verified request-v3 worker,
bind the historical observation02 evidence and source proposals, and implement
the separately pinned independent auditor. Prove the complete authored route,
including semantic tampering, historical-byte preservation and cleanup, before
freezing and reviewing an actual configuration. Current parent behavior remains
unchanged and still emits request-v2.

Then freshly admit exact pins, current installation bytes, absence conditions and
resources before one actual metadata observation. This source work accepts no
profile and grants no held-runtime, collection or study authority. Previous
consumed attempts remain preserved. Full repository tests and CI were not run;
all seven release gates and the real episode bundle remain open.
