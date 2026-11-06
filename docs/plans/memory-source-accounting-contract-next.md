# Finite source-accounting contract: endpoint gap

**Status: UNADOPTED source proposal, not implementation or execution authority.**
Prepared against `caf919b` and the retained lifetime architecture. No numerical
cap, research-process exemption, policy debit, trusted pin or source03 packet
changes. No actual measurement or service probe was run for this document.

## Required accounting boundary

The project cap remains24 aggregate research-process CPU-hours, with12 hours
for memory and no borrowing. Real preparation, qualification, scientific
checking, orchestration, failed work, output publication and teardown count.
Standalone formal proof builds and ordinary software tests retain their
approved exclusion. An incomplete measurement is never zero.

For a finite, closed and disjoint roster, the desired quantity is:

`closed_research_CPU = closed_service_CPU + sum(final_outside_process_CPU)`

The shared trusted kernel/system-manager accounting implementation is the
measurement interface, not a project process hidden from this sum. Every
project-specific process remains included. A child already included in a
service or final waited-child total is not added twice.

The current design must accept no actual source until each outside term has a
named, available final-lifetime measurement. A pre-exit self sample, hard CPU
limit or planned reserve is insufficient. A receipt may refer to an OS record
produced after its writer exits; it need not contain its own future CPU. The
last bespoke reader/acceptance process still needs that measurement source.

## Available and missing endpoints

The pending source03 packet illustrates the gap concretely. It is an OS-only
toy, not the actual source launcher; the actual launcher needs its own frozen
roster. These are source observations, not executed measurements.

| Role | Existing measurement surface | Coverage and missing endpoint |
| --- | --- | --- |
| Service worker and its explicitly waited child | Same-invocation cached `CPUUsageNSec`; worker child `wait4` is an inner diagnostic | The cached counter is eligible only after independent drain-before-final-accounting, ownership/no-escape and counter-semantics proof. Inner values are not added again. No complete service result is asserted here. |
| Six fixed client invocations | Administrator's `RUSAGE_CHILDREN` after those children are reaped | `client.py` execs its fixed OS command in the same process. Under the fixed topology, the waited total can include client startup/exec/exit. On failure, prove which children closed; do not assume the planned six ran. |
| Python administrator | `admin_cpu_observed_before_final_receipt` | Partial: it precedes result persistence, return and final cleanup. Its final OS CPU endpoint is **not supplied**. |
| Outer timeout and its exec prefixes | Pre-interpreter hard limit and configured wall watchdog | These constrain attempted operation; they are not final CPU measurements. Its final OS CPU endpoint is **not supplied**. The administrator child must not be double-counted if a later endpoint includes waited descendants. |
| A later bespoke reconciliation/acceptance reader, if introduced | No implementation or endpoint presently supplied | Must be listed and measured too. Renaming it an observer does not exempt it. Adding another wrapper alone does not close the chain. |

Source references: pending packet `client.py:11–22`, `admin.py:107–126,214–241`,
and its README; trusted helper `paper/studies/change_audit_v1/process.py:461–525`.
The helper's final waited subtree and its caller's pre-return self interval are
different scopes. This table grants no additional role, client, unit or probe.

## Field semantics and acceptance

- `measured_closed_subtotal_cpu_seconds`: only complete, disjoint, identified
  terms with valid final OS evidence. Retain scope and source of every term.
- `partial_cpu_observations`: pre-exit samples or incomplete terms, with their
  exact boundaries. They cannot fill a missing final term.
- `actual_whole_operation_cpu_seconds`: null until every named research role
  is closed, accounted and reconciled without double counting.
- `administration_charge_seconds` and `charged_upper_cpu_seconds`: remain null
  under the current unsupported-upper-bound branch. A newly documented number
  is not an upper-bound proof.
- `planning_reserve_cpu_seconds`: prospective headroom only, never evidence of
  actual usage, a clipped overrun or an authorized budget debit.
- `budget_compliant`: false/unverified until the complete registered charge
  and prior ledger fit unchanged stage, lane and project caps.

The source-stage proposal remains1,800 CPU seconds,900 seconds including the
whole allocation/closure,8GiB memory and640MiB peak/new output with its existing
floor and component limits. All retained originals/candidates/partial outputs
and physical copies count. Actual feasibility remains unverified. Overrun or
unknown usage stops and preserves the failed/incomplete record; no retry,
replacement, borrowing, clipping or deletion follows.

Post-close acceptance under a declared trusted OS model is distinct from a
mathematical prelaunch never-exceed guarantee. Neither polling, source03, a
successful exit nor hard-limit values currently establish the latter. The
existing architecture already records that distinction; no stronger claim is
added here.

## OS trust, provenance and next decision

Exact live manager/library attestation and trusted OS CPU-accounting semantics
are separate assurance claims. The static package/source correspondence does
not verify live mappings or prove last-tail accounting. The current exact-
platform requirement remains unqualified; this document does not waive it.
A successor may propose an explicitly conditional trusted-OS accounting claim,
retaining unverified exact-live provenance honestly, for independent review and
the required prospective adoption decision.

**Next technical deliverable:** identify an available final OS measurement
endpoint for the administrator, timeout and any bespoke acceptance process,
then freeze the finite identity/coverage/close contract and verify it. None is
currently supplied by the retained source. Do not implement more closed
wrappers or launch another probe to make that endpoint appear.

If no such endpoint is available, changing the accounting boundary, exempting
an observer, adopting policy debits instead of actual overhead, or reducing the
assurance claim requires a concrete separately reviewed prospective decision.
No such change is inferred from the full-project authorization. Actual source
GO remains blocked; the independently pending source03 approval is unchanged.
