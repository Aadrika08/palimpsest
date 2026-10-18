# Memory family v3 producer contract verification

**Date:** 8 October 2026  
**Implementation commit:** `c7c621f404edec36932b14e97570504d6215c2bf`  
**Base:** `a1801e62533d2aeaec164441a39037ef0da3ec09`
(`research/memory-family-oracle-raw-adapter`)  
**Handoff:** draft [PR #100](https://github.com/Aadrika08/palimpsest/pull/100);
goal tracker `fd6b2f8`
**Status:** verified software contract; native allocation remains inadmissible

## Result

The producer contract now regenerates and validates one complete development
block: 48 families, 144 cases, 144 source owners, 1,296 condition owners and
1,440 caller-supplied UUIDs. It materializes only non-executable source and
`own` descriptors. It contains no Engine, model, subprocess, signal or owner
launch path.

Registration binds the regenerated matrix plan, canonical protocol bytes,
bounded source identity, semantic E-to-U histories for both relation labels,
disjoint history and authored-ID namespaces, the caller's historical namespace
inventory, non-overlapping roots, the literal resource projection and the
behavior-bearing project sources used by registration and close admission.

The pair close requires both jobs to bind the outer registration; exact job,
owner, cleanup and supervisor paths and hashes; the current PID namespace;
normal integer-typed supervisor completion within the frozen timeout; per-file
and aggregate control limits; raw manifest producer bindings; a classified and
bounded run tree; and equal before/after ledgers. It then invokes the existing
raw oracle admission and publishes one canonical receipt through a synced
temporary file plus an exclusive hard link. Deadline or durability failure
after the link removes the target, so a failed call does not leave a poisoned
final receipt.

## Verification

The focused producer and raw-admission command passed **47 tests in 69.46
seconds**:

```text
../memory-family-oracle-raw-adapter/.venv/bin/python -m pytest -q \
  tests/test_memory_family_producer_v3.py \
  tests/test_memory_family_oracle_admission_v3.py
```

The affected oracle/family/snapshot/artifact/replay slice passed **172 tests,
with 7 skipped and 4 `FlynnContinuation` tests deselected, in 151.39 seconds**:

```text
../memory-family-oracle-raw-adapter/.venv/bin/python -m pytest -q \
  tests/test_memory_family_producer_v3.py \
  tests/test_memory_family_oracle_admission_v3.py \
  tests/test_memory_family_oracle_v3.py \
  tests/test_memory_family_world.py \
  tests/test_memory_family_runtime.py \
  tests/test_memory_family_slots.py \
  tests/test_memory_decision.py tests/test_memory_task.py \
  tests/test_memory_experiment.py tests/test_snapshots.py \
  tests/test_artifacts.py tests/test_replay.py \
  -k 'not FlynnContinuation'
```

Compilation of the producer and both changed test files passed in 0.03 seconds.
`git diff --check a1801e6..c7c621f` passed. The affected run emitted 15
non-failing Torch/Matplotlib deprecation warnings. CI was excluded by instruction.

Tests explicitly reject duplicate or historical UUIDs, malformed nested input,
noncanonical protocol bytes, history relabeling, stale or hand-authored U,
cross-history and history/authored namespace reuse, source snapshots above 16
MiB, cross-registration job splicing, boolean/float substitutions in supervisor
proof fields, timeout overrun, alternate or extra supervisor evidence, aggregate
pair control bytes above 2 MiB, unregistered run files, changed manifests,
active owners, input drift, deadline expiry during finalization and failures
before or after the exclusive publication link. A sentinel test makes
`bounded_process`, `subprocess.Popen`, `Engine.open` and `os.killpg` fail if any
contract path attempts native execution.

Three independent read-only reviews found material issues in the initial
implementation. The fixes added canonical protocol identity; semantic history
validation and namespace disjointness; outer-registration binding; snapshot,
control and run-tree ceilings; deadline-aware hashing; direct and transitive
source provenance; exact supervisor scalar types; zero-launch coverage; and
rollback-safe atomic publication. Two final reviewers reported no remaining
Critical or Important findings on `c7c621f`; one reran 32 producer tests and the
other also reran all 15 raw-admission tests, compilation and whitespace checks.

## Resource decision

The frozen known subtotal remains:

| Class | Bytes |
|---|---:|
| Raw recordings | 599,147,937,792 |
| Initial snapshots | 24,159,191,040 |
| Two logs plus aggregate control per owner | 4,529,848,320 |
| **Known subtotal** | **627,836,977,152** |

The plan-time free-space measurement was 68,881,358,848 bytes, leaving the
required **558,955,618,304-byte shortfall**. A fresh check after verification
found 68,848,934,912 bytes free, a 558,988,042,240-byte shortfall. Report,
audit, prerequisite and close-headroom bytes remain outside the subtotal, so
meeting the known subtotal alone would still be insufficient. The frozen
external-owner allowance is 221,760 seconds plus 14,400 seconds of cleanup,
236,160 seconds total (65 hours 36 minutes).

No native phase is admissible on this filesystem. The module deliberately does
not create an allocation registration or turn its job descriptors into grants.

## Evidence boundary and next decision

All positive close tests use synthetic temporary recordings. They hand-write
owner and supervisor records and patch the live PID-namespace/owner-exit
observation. They prove validation and readout composition; they do not prove
that `bounded_process` launched a registered command, environment or child PID.
A future native launcher must bind and emit those facts before its receipts can
support runtime qualification.

No development block was selected for collection, registered on disk, allocated
or run. No trained-model inference, native study owner, held-out input or
physical rover was used. The affected snapshot regression tests did execute
small local MuJoCo fixture steps; those were test mechanics, not study
collection. The receipt carries `study_complete:false`, `native_allocation:false`,
`held_out_used:false` and no qualification claims. Historical namespace
inventory completeness remains an external prerequisite. The hash-sealed close
detects ordinary drift; it does not defend against a hostile same-user rename
race.

The next allocation decision is **do not allocate**. Before native memory
collection, resolve storage plus unbounded overhead, supply and independently
check the complete historical namespace inventory, freeze effect and null-harm
margins/intervals/stopping rules, and implement a separately hash-bound launcher
and allocation registration with command/environment/child-PID provenance.
