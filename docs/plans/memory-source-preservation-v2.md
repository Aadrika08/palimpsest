# Single source preservation parent v2

Task 2 is INCOMPLETE at the actual namespace and external lifetime gates.
This is source implementation and authored software verification only. No actual
native owner, model, graph, checkpoint, retained SNP or protected catalog was
opened. No trusted qualification pin changes. Actual source qualification,
scientific acceptance, condition qualification, evidence pruning, and the full
48-development/48-held-out nine-condition study remain unqualified.

The parent is `scripts/qualify_memory_family_source_v2.py`; the source owner is
`scripts/memory_family_source_runtime_v2.py`. The owner and selected engineering
case are fixed to `development, 0, 0, change`; the generated case, seed and canonical
run UUID live in the externally pinned job template. There are no retries,
replacement cases, alternate policies/loaders, condition entry points, or arbitrary
commands in the real CLI. All partial and failed outputs remain in their original
locations. Historical attempts01/02, old workers, profiles and bytecode remain.

## Preparation and missing inputs

The real CLI accepts `--mode verify|execute --freeze PATH
--expected-freeze-sha256 SHA`. Verify opens the bounded, externally hashed freeze JSON and imports
public source/protocol metadata. It opens no selected runtime or protected input. It validates exact metadata through `validate_source_template`, whose
`parent_admission` must be null. It neither hashes selected model/runtime files nor
opens projections, GO, lifetime records or protected catalogs, creates output, or
starts a subprocess. `validate_source_job` still requires a matching live parent
assertion; verification never creates a successful-looking placeholder admission.

The freeze schema is `memory-family-source-freeze-v2`, with exact keys declared in
`FREEZE_FIELDS`. It binds the template, environment, source/runtime file roster,
clean selected installation roots, namespace-only projection descriptors, prior
CPU charges, maximum concurrent storage, output, established cgroup, external
prospective lifetime contract. GO is a separate operator-supplied document,
consumed by `--go PATH --expected-go-sha256 SHA`; the freeze excludes its hash to
avoid a circular binding. GO must bind this freeze SHA, the one job SHA, the
fixed source-only scope, `retry:false` and an approval reference. The program
never generates or approves GO. These are externally
supplied inputs, not artifacts that this implementation claims already exist.

Missing independently authorized namespace-only exports remain a concrete input
blocker for exactly `pre-heldout-development-history` and `training-namespace`.
The parent reuses the existing v3 coverage contract and exact
`memory-family-namespace-export-v3` schema; each external source directory may
contain only `namespace-export.json`. That existing gate requires independently
reviewed export/count/inventory/known-source/run-ID/authored-ID/seed identities.
The current canonical contract has `coverage_status: unresolved`,
`allocation_authorized: false` and null source identities. The real CLI therefore
refuses before opening any external namespace directory or runtime/model payload,
even if a prospective freeze supplies descriptors. No trusted pin/protocol is
updated to resolve that gate. Do not inspect a mixed held-out catalog to
manufacture the missing exports. A future reviewed contract is required before
actual execution. Descriptor labels, fixtures and a user-chosen path manifest
cannot establish the missing coverage.

The full clean runtime installation and native dependency closure are also not
prepared or qualified here. Execution holds the externally selected byte roster,
checks the pinned owner/runtime identity and enumerates the selected clean prefix
against that roster. The existing source owner caps closure at 4096 entries; a
larger real dependency tree is a blocker, not permission to raise the cap or omit
files. Verification of namespace metadata does not establish authorization,
namespace coverage or dependency completeness. Those require the real supplied
package and independent review. No actual execution freeze is delivered by these
software fixtures.

## Proposed maximum allocation

The fixed maximum is 900 seconds enclosing wall, 1800 aggregate research CPU
seconds, 8 GiB runtime memory, 640 MiB new retained/peak storage and a 6 GiB
filesystem free-space floor. The source work limit remains 360 seconds with a
10-second cleanup allocation. Existing `run_accounted` has a tighter three-second
owned-tree cleanup guard; it is reused unchanged inside that allocation.
Independent raw audit uses at most 180 seconds; public preservation/read deadlines
stay within their existing 300-second entry cap. No bound is silently raised.

The prospective simultaneous storage reservation is raw512 + SNP16 + compact32 +
controls8 + atomic8 + headroom64 MiB = 640 MiB. The SNP is one exclusive serialized
container; the public raw auditor's temporary receipt and sealer's small marker
are separately included in atomic space. Compact source itself retains its 32 MiB
protocol ceiling. Already-written control bytes count within the controls
allowance rather than being charged again as future allocation. Real raw/SNP,
control counts, atomic behavior, runtime cache/environment and filesystem reserve
still require review against this ceiling before any actual freeze/GO. This is a
proposed worst-case allocation, not a measurement of feasibility.

The prospective execution contract requires the caller to start the actual parent inside an already established dedicated
cgroup v2 whose `memory.max` is at most 8 GiB and `memory.swap.max` is zero. The prepared validation checks current membership and exclusive initial ownership.
The actual execution entry remains blocked while the external lifetime OS/receipt
interface and canonical namespace coverage are missing. A sampled
RSS monitor is never called a hard memory bound. The parent cannot establish a
real bound merely by carrying a true flag or by a successful fixture/CI run.
Actual systemd/scope command and the external complete lifetime accounting package
remain inputs to the execution review, not launch instructions supplied here.

All preparation, actual source, audit, supervisor, failed-attempt and accounting
tail CPU charges the 12-hour memory lane and 24-hour project allocation. Audit1h,
puck5h, navigation4h and final2h allocations cannot be borrowed. Ordinary authored
software tests are excluded. Unknown earlier charges stop actual admission.

## Runtime and preservation sequence

Execution refuses any existing output, uses a fresh
`ROOT/runs/memory-family-source-v2-*` root and retains external control files under
`controls/<run_id>`. Raw is
`.pending/<case>/.raw/<run_id>/`; the sole SNP is
`.pending/<case>/source/snapshots/initial.snp`; semantic owner metadata is
`.pending/<case>/source/owner.json`. Inputs are disjoint from outputs. File writes
are exclusive, fsynced and never replacements; the existing storage writer lease
is reused. Tests use a private temporary HOME so they do not take the user's
writer lease.

The actual interpreter argument is the frozen venv alias, never its resolved ELF
path. The parent separately checks `/proc/self/exe` and alias-to-ELF identity.
Its exact environment includes `-B`, `PYTHONDONTWRITEBYTECODE=1`, a fresh frozen
`PYTHONPYCACHEPREFIX`, CPU-only thread limits and source paths; old caches remain.
The public owner loader stays hardwired to `Engine.open`.

The source owner command executes only the fixed internal adapter. The parent
uses the unchanged pidfd/subreaper `run_accounted` for launch, exact reap, drain,
stdout/stderr caps and CPU controls. It records the actual command, environment,
limits and complete supervisor response. A failed owner outcome blocks audit even
when a late failure left the twelve-field raw report. Missing/nonzero exits,
unknown CPU, failed supervisors, undrained trees, closure drift and deadline
expiry block continuation. Whole-phase SELF plus reaped CHILDREN is charged once;
worker CPU is not added again to inclusive subtree CPU.

Only a genuinely successful closed owner reaches the separate raw-auditor child.
That child invokes the unchanged public `memory_family_raw_audit_v4` CLI against
the one acquired SNP. Before sealing, terminal export binds actual job,
supervisor, stdout, stderr, cleanup and independently published audit bytes from
this same attempt. The public `seal_compact_source` and `read_sealed_source` then
operate on the same closed raw tree, with immutable raw inventory comparison
before and after. No synthetic converter/private preparer, retained-only reader,
final publisher or raw pruning is an admission shortcut.

The preservation report separates compact stored-field preservation, matching
original-row commitments, and omissions (including cameras not fully retained and
latency fields). Original nonempty raw and the sole SNP remain authoritative and
retained. Natural early/zero-row conditions keep score900 semantics, but actual
condition stages require a separately versioned evidence-admission design. No
missing-cell or donor proof is inferred here.

## Accounting boundary and completion gate

As in the existing `pilot.py` contract, the terminal receipt reports CPU through
its preparation and explicitly excludes its own serialization/write/fsync,
lease release and process return. Held-input release is checked before that
terminal receipt while the writer lease remains held. A process cannot observe its own exact
post-exit accounting. Therefore a passing source path is reported as
`preserved-awaiting-lifetime-reconciliation`, with `actual_source_qualified=false`
and `parent_lifetime_reconciled=false`. The externally pinned lifetime supervisor
must cover the complete parent process, including this tail, and reconcile exact
limits, closed/drained outcome and all prior lane charges. A JSON contract alone
is not proof this supervisor ran or that the tail is known. No source pass or
study qualification is issued by this script before that external reconciliation.

Actual input projection bytes, clean install/complete native closure, live
whole-runtime enforcement, complete parent lifetime reconciliation, independent
Task 2/whole-feature review and exact-stage operator GO remain explicit gates.
CI and authored fixtures satisfy none of those execution authorities.

The real `execute` entry explicitly refuses while the external full-parent
supervision OS/receipt interface is unimplemented. The intended trusted outer
`run_accounted` must wrap the entire parent CLI, including terminal write, lease
exit and return. A source-level contract descriptor is not a live outer receipt.
This binding is deliberately left as an INCOMPLETE load-bearing interface for
the root's next concrete runtime amendment. Private authored integration may
exercise the prepared source/preservation core; it cannot authorize real data.

## Prepared-core review fixes

Parent phase CPU is measured only in the original coordinator. The callback in
`run_accounted`'s forked supervisor uses the prelaunch phase snapshot, that
supervisor's own SELF CPU since fork, and the helper's supplied live/reaped-worker
sample. It never subtracts a coordinator baseline from a forked child's counters
or adds an inclusive subtree to its worker a second time. This live estimate
omits coordinator CPU accrued while waiting and inherits sampling uncertainty;
it is containment, not proof of a hard aggregate bound. Closed parent/outer
accounting still gates acceptance. No cleanup/polling reserve arithmetic or
assumed administration upper charge is promoted to a proof.

Prepared runtime rechecks now retain the executable alias chain identity and
census all selected files and directories, including empty import namespaces.
Alias retarget/replacement and namespace additions refuse. These checks run
between phases and at held-input teardown. They do not prove which bytes were
already imported before a later disk hash or atomically close the interval
between checking an alias and executing it. The trusted external launcher must
establish the frozen load environment and immutable namespace before interpreter
startup and preserve that binding through exec. This remains an explicit,
unimplemented actual-execution blocker.

Created job, launch, supervisor, cleanup and terminal-export controls bind the
canonical bytes supplied by the validated parent state. Expected descriptors are
retained from that creation, then held and rechecked through finalization;
export cannot accept a rewritten control by freshly hashing it. Closed-owner
outcome/report, source owner metadata, sole snapshot and independent raw-audit
receipt are also bound to their validated values. Closed logs are pinned when
first observed after complete reap/drain. All source/control descriptor teardown
checks finish under the writer lease before the provisional terminal is written.
A teardown failure records `status:stopped` and `teardown_error` and quarantines
any retained source marker; the marker, raw, SNP and controls remain. Terminal
write, lease release and process return still require external lifetime closure.
