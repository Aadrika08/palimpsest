# Navigation-v3 matched-budget execution amendment v2

**Status:** prospective amendment after consumed invocation 1. This document
authorizes no execution until its implementation, sealed manifest and exact head
receive independent review.

## Reason

Invocation 1 at source commit `148142b2086b93bdc1b3f0016ec070f99a20823f`
stopped before reservation with `ValueError: Runner argv differs from frozen
invocation`. Its manifest stored the interpreter followed by the script and
arguments, while Python's `sys.argv` begins with the script. The guard therefore
rejected the exact frozen launch. The output path was never created, and no
corpus, model, Torch, MuJoCo, training, simulator, development or held-out input
was opened. The retained report and journal remain immutable evidence; invocation
1 is consumed and is not retried.

## Single correction

Invocation 2 compares `[sys.executable, *sys.argv]` with the exact frozen runner
vector. A process-level regression must use the real Python `sys.argv` shape and
must reject a different interpreter. No training, scheduler, model, corpus,
optimizer, seed, limit, environment, source, cgroup property, selection rule,
development gate or held-out gate changes.

Invocation 2 uses:

- schema `m7-navigation-v3-matched-budget-execution-v2`;
- attempt number 2 and `retry_allowed: false`;
- manifest `docs/plans/m7-navigation-v3-matched-budget-execution-v2.json`;
- unit and output name `m7-navigation-v3-matched-budget-v2`;
- the unchanged three training seeds and six terminal models;
- the unchanged 2,150-second normal and 2,160-second hard outer bounds.

The v2 manifest binds the byte identities of the v1 manifest, retained failure
report, verification receipt and exact user-systemd journal. Preflight requires
both the old and new output paths to be absent. Any mismatch stops before the v2
reservation. The new output receives one durable attempt-2 receipt before any
trainer starts; failure consumes it, and there is no automatic third invocation.

## Gate

Before launch, pinned synthetic tests must reproduce the v1 failure and pass the
corrected exact-vector check, source and manifest admission, signal/process-group
containment and publication checks. A short process probe must execute the
runner only with `execute()` replaced, proving the interpreter/script/argument
shape without opening inputs or reserving output. Independent review must report
no Critical or Important finding on the exact sealed head and verify both output
paths absent. Only then may the exact `outer_argv` be invoked once.

Any v2 result remains training evidence only. Development scenes 3130-3133 and
held-out scenes 3120-3127 remain unopened and separately gated.
