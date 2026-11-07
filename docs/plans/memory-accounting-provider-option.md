# Accounting provider option for prospective review

Status: UNADOPTED decision package. Source analysis only; no probe, research
execution, accounting exemption or permission follows from this document.
The existing accounting contract and all actual-stage gates remain active.

## Decision required

The current contract requires final CPU evidence for every project process,
including the administrator, watchdog and any bespoke acceptance reader. Its
pre-exit samples leave an unmeasured tail. Another bespoke wrapper moves that
tail rather than closing it. Actual whole-operation CPU and a justified whole-
operation upper bound therefore remain unknown.

A possible successor would treat a specifically admitted standard OS timing
provider as measurement infrastructure, while charging every bespoke research
process. This is an explicit boundary change requiring prospective approval;
it is not an interpretation of the existing authorization. Keeping the
existing boundary is a valid choice and keeps actual source admission blocked
until a complete final endpoint is supplied.

## Concrete candidate topology

1. A named GNU Time invocation inside the admitted service measures the closed
   research parent and its normally waited descendants. Service ownership,
   drain, no-escape, output and resource gates still apply independently.
2. A separate named GNU Time invocation measures the administrator, outer
   watchdog and their normally waited descendants outside that service. A
   service launched through the manager is disjoint from this child tree;
   that disjointness must be proved, not assumed from a unit name.
3. Each later bespoke preparation, reconciliation, publication or acceptance
   job must likewise be in a prospectively named timed, closed subtree. No
   bespoke final reader is excluded by calling it an observer. The finite
   roster must identify all jobs, close points and failure paths before GO.
4. The admitted timing-provider processes themselves would be excluded from
   the research-process charge under the proposed policy. Their CPU is not
   measured by their child totals. This limitation must remain visible;
   neither zero overhead nor whole-machine physical CPU is claimed.

This is a topology proposal, not a launcher implementation. GNU Time records
CPU; it does not enforce aggregate CPU limits, prove descendant closure,
authenticate a receipt, impose a namespace or make a receipt durable.

## Available source evidence and its limits

The installed `/usr/bin/time --version` reports GNU Time 1.10. Only version and
help were invoked; no timed workload ran. Upstream release source was fetched
from <https://ftp.gnu.org/gnu/time/time-1.10.tar.xz>, SHA256
`706bf7b8444ca9eb9037e9eda18e1d0eb7c2327ae7d8c2ce3a4823c5f80c7b11`.
The archive and bounded selected-source inspection are retained under
`runs/time-1.10-source-inspection-20261106/`. Version text does not establish
installed binary/source correspondence or exact live provenance.

In that upstream source, `time.c` waits for its child, then obtains
`getrusage(RUSAGE_CHILDREN)`, and formats user/system CPU separately at two
decimal places (`resuse.h` supplies the microsecond-to-millisecond truncation).
Under those semantics, for each completed fresh provider invocation, the
printed user-plus-system sum L encloses the OS-accounted waited-child CPU C:

`L <= C < L + 0.02 seconds`.

That interval covers formatting truncation, not kernel measurement error,
escaped/orphaned children, provider overhead or an execution-limit overshoot.
The implementation/platform correspondence and output format must be qualified
before this formula can support an actual receipt. Use exact decimal/rational
arithmetic; do not subtract the interval from the charge or clip an overrun.

Linux documents waited-child coverage, including descendants only when the
intervening processes wait for their children:
<https://man7.org/linux/man-pages/man2/getrusage.2.html>.
Upstream manual: <https://www.gnu.org/software/time/manual/time.html>.
No claim of sub-centisecond physical accuracy follows from this source review.

## Proposed field and acceptance contract

- Retain raw provider output, exact invocation identity, executable provenance,
  roster membership, child close status and independently authenticated scope.
- Each provider must start with no previously accumulated waited-child CPU;
  an exec prefix does not automatically reset inherited accounting. Qualify the
  exact `%U`/`%S` format and counter representation. All intermediate parents
  must wait on failure/signalling paths too. Nested timed subtrees cannot also
  be charged through a covering outer provider or service counter.
- Record covered-scope CPU as a rational interval for each disjoint closed job.
  Sum interval endpoints only across that frozen roster. A missing, truncated,
  ambiguous, nonfinal or unauthenticated term makes the aggregate unknown.
- A prospective conservative covered-scope charge could use the sum of upper
  endpoints. That choice must be approved and named explicitly; it is not an
  actual measurement of provider overhead or a retroactive policy debit.
- Keep `actual_whole_operation_cpu_seconds` and any physical whole-operation
  upper bound null. Name any successor covered-scope fields distinctly from
  the existing whole-operation fields; never relabel an incomplete old value.
- Preserve the project's 24-hour and memory lane's 12-hour caps, no borrowing,
  no retries and all failed-work charges. Reconcile prior accounting separately
  before any new actual source admission. This proposal supplies no missing
  historical final endpoints and does not change the historical ledger.
- Durable receipt publication requires a separate bounded close/readback
  contract. GNU Time's final output flush is not a filesystem durability proof.
  Descriptor inheritance, output authenticity and failure-prefix preservation
  must be reviewed in the actual launcher, not assumed from this topology.

## Remaining gates

Independent source review comes first. If sound, present the explicit provider
exclusion and interval-charge boundary for user choice. Only prospective
adoption could enable implementation of a new frozen launcher package; it
would not itself approve running that launcher. Exact platform/provenance,
finite roster, prior-cost reconciliation, capacity, closed resource lifetime,
storage preservation and separate source/held-out GO remain required.

The separately sealed source03 toy packet and its pending approval are
unchanged. Its execution cannot validate this new topology. No raw deletion,
native/model/SNP/protected read or research attempt is authorized here.

Independent bounded source review approved this package for prospective user
choice only. Report retained at
`runs/time-1.10-source-inspection-20261106/option-review.md`; the explicit
fresh-accounting, failure-wait and overlap conditions above preserve its
qualifications. No tests or probes ran for that review.
