# Source lifetime architecture decision

Source-only review of `12873f1eeba0149cd98b194a5a477889f7809969`.
No implementation, tests, native execution, or research-data inspection occurred.

## Decision

Implement one fixed external lifetime entrypoint around the **entire** current
qualification CLI, using the unchanged `run_accounted`. Publish a separate
external closure receipt after that CLI has exited and been reaped. Keep the
parent's existing terminal provisional. Do not make the parent certify its own
future exit, and do not repeatedly wrap meters to pretend an exact whole-operation
number exists.

**Reject the proposed `1500 + 64*(3+.1) + 25 + 25` pre-execution proof.**
The existing helper explicitly documents racy `/proc` sampling, scheduling/probe
latency, and possible unresolved descendants. Its three seconds limit cleanup
attempts, not descendant lifetime. Its nominal poll sleep is `.01`, not a proved
maximum sample interval. `TasksMax=64` limits simultaneous tasks, not CPU between
observations or total process births. Therefore 198.4 is a planning reserve, not
a defensible worst-case CPU bound. Reducing the work threshold to1500 is useful
headroom but cannot make that arithmetic a hard aggregate guarantee.

**A measured closed subtree plus separately justified administration bounds is
the right terminal accounting interface.** It may accept only after measuring
the actual subtree and testing the resulting charge against1800. It cannot promise
before launch that1800 will never be exceeded. Do not advertise it as such.
If strict never-exceed admission is required, retain the actual GO blocker until
a separately reviewed enforcement contract proves it; current source and Linux
polling do not provide that proof.

## Minimal source interface

Add a project-specific `scripts/run_memory_family_source_lifetime_v2.py` with
fixed verify/execute roles and no arbitrary command or retry argument:

1. Verify externally pinned freeze, separate GO, exact source/helper identities,
   resource contract and prior memory/project charges. A descriptor supplies
   prospective policy only; it is never proof of a completed run.
2. Invoke unchanged `run_accounted` with the exact Python alias, `-B`, fixed
   environment, and complete `qualify_memory_family_source_v2.py --mode execute`
   command. Start measurement before parent interpreter startup. The parent's
   stdout/terminal/lease exit/return are inside the worker lifetime. Existing
   source/audit child accounting remains diagnostic; do not sum it into the
   outer subtree a second time.
3. Supply an actual launch binding: fresh attempt nonce, external freeze/GO hashes,
   wrapper/supervisor/parent PID plus start identity, exact cgroup identity,
   executable and argv. Parent verifies its live ancestry and membership before
   opening runtime/model inputs. A JSON `admitted:true` or a parent-generated
   descriptor is insufficient. Use existing pinned PID ownership; no `killpg`.
4. After exact outer reap, require complete accounting, drained tree, expected
   return code, immutable parent terminal and matching attempt identities.
   Export a new exclusive, durable external closure record; never overwrite the
   provisional terminal or existing V4 controls. Closure includes parent terminal
   hash, complete outer result/hash, launch binding, measured scope, reserve
   basis, charge, limits and explicit scientific flags=false.
5. A small independent validator combines these records. Only it may mark the
   parent lifetime reconciled. Missing/failed external closure leaves preserved
   bytes provisional; the existence of a compact source marker is insufficient.

`run_accounted.subtree_cpu_seconds` includes its private supervisor's full life
and waited worker descendants (`process.py:480–496`). This closes the research
parent's tail. Its `parent_cpu_seconds` ends before its own result construction
and cleanup: it does **not** close the external caller's life.

## Unknown versus charged bound

Use explicit fields, never overload `actual_cpu_seconds`:

```
measured_subtree_cpu_seconds: finite number from the closed outer receipt
actual_whole_operation_cpu_seconds: null
administration_charge_seconds: justified fixed upper charge, otherwise null
charged_upper_cpu_seconds: measured subtree + administration charge, or null
budget_compliant: true only with valid bound and charge <= allocation/lane remainder
```

The private supervisor is already included in measured subtree CPU. Do **not**
charge a separate guardian reserve for it. Charge every distinct outside process
once, including any systemd client, startup before Python accounting, and final
receipt write. Retain sampled/partial values on failure but never promote them
to a complete number. No automatic retry or borrowing from another lane.

Soft20/hard1800 with default SIGXCPU is useful trusted-code containment, but is
not by itself proof of a25-second upper charge: the process can raise its soft
limit, block/change SIGXCPU, fork additional processes, and the proposed5-second
enforcement allowance has no source-backed worst-case justification. In
particular, the intended research parent raising its limit must not accidentally
authorize an outside administrative process to do the same.

Concrete alternative if fixed administration charging is selected: launch the
small non-spawning outside finalizer under an independently applied **hard** CPU
limit before interpreter startup, with exact source, no capabilities, and explicit
signal/mask policy. Start the research unit through the system manager with its
own independently configured limits; do not inherit the administrative hard limit
and then attempt to raise it. Account any separate client under its own bound.
Pin and review the actual OS enforcement/tolerance contract before calling25 an
upper bound; until then expose `administration_charge_seconds:null` and refuse
budget acceptance. A successful exit does not prove that an assumed bound was
valid. This is a concrete remaining admission dependency, not permission to
invent a number. It needs no additional recursive research meter.

For a stronger eventual measurement, a retained dedicated cgroup CPU counter
after verified emptiness can include the entire wrapper, its terminal write and
all descendants. It still excludes the outside reader/finalizer and therefore
does not eliminate that final bounded-administration contract. Do not implement
a new generic cgroup service for this source task merely to relocate the tail.

## Resource and failure requirements

Keep8GiB `memory.max`, swap0,900-second allocation,640MiB peak/new output and6GiB
reserve. Include outer logs/closure/atomic write peaks in the existing controls
allowance. The900-second allocation includes startup, parent lifetime, drain and
finalization; do not pass900 to a worker and silently add cleanup afterward.
None of these values proves feasibility or runtime readiness.

If the outer wrapper and private supervisor share the parent's cgroup, current
`_enforcement`'s sole-PID admission check must be replaced by the exact pinned
initial roster plus descendant containment. Alternatively use a dedicated child
cgroup for the research parent under a common bounded ancestor. A fabricated
sole-PID check or an unrelated shared cgroup is not acceptable. Preserve the
existing checks against memory enforcement and changing runtime inputs.

Any bad ancestry, malformed/missing receipt, unknown CPU, non-drained tree, changed
input/control, overrun, OOM, wrong GO or unmatched attempt refuses acceptance.
Retain all raw/SNP/compact/control/failure evidence. An overrun is recorded as an
overrun with its real charge, never clipped to1800. No resumption follows unknown
accounting without independent reconciliation.

## Namespace decision

**Yes: use a separately versioned source-engineering namespace contract.** Keep
the immutable canonical V3 coverage and full-block admission unresolved. The new
contract is externally pinned by freeze and GO, applies only to the fixed
development source tuple, and explicitly grants no full-block/study admission.

Reuse exactly the existing `memory-family-namespace-export-v3` bodies for
`pre-heldout-development-history` (historical) and `training-namespace` (training).
Reuse `_read_export`'s strict identity checks and one-file namespace directory
allowlist; do not mutate `NAMESPACE_COVERAGE` or monkeypatch `_coverage_contract`.
The new contract must pin **all** existing expected counts, list hashes, export
hash/size and inventory identity fields, not expected counts alone. Preserve
duplicate and selected run/authored-ID/training-seed collision refusals.

The reviewed external contract must attest which complete permitted namespaces
the exports cover. Matching hashes/counts establish identity, not completeness.
No export exists in this review; code must continue refusing actual execution
until independently supplied reviewed projections arrive. No mixed/protected/
held-out catalog reads to manufacture them. Parent verify mode should report
engineering-contract absence separately from unchanged canonical V3 nonadmission.

## Next changes and acceptance

Implement the fixed external wrapper, live binding, closure schema/validator,
and separate source-engineering namespace contract. Adjust parent admission to
consume them and preserve provisional semantics. Author source-only tests for
forged ancestry, stale/replayed receipts, full parent tail inclusion, double
counting, unknown/overbudget CPU, missing bound, immutable canonical nonadmission,
namespace identity/completeness provenance and absent GO. These tests are proposed,
not run. They can close the **implemented source interface** gate; actual resource,
input, administration-bound and GO gates remain separately visible. No actual
package or research launch is authorized by this decision.

Primary basis: local `paper/studies/change_audit_v1/process-accounting.md`,
`process.py`, `pilot.py::_terminal_accounting`, current parent and allocation
source. Linux documents per-process CPU signals/limits and inheritance at
[getrlimit(2)](https://man7.org/linux/man-pages/man2/getrlimit.2.html), and cgroup
hierarchy/accounting interfaces at
[cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html).
