# Bounded pilot parent contract

`pilot.py` is an engineering supervisor. Importing it loads only standard-library
modules and the stdlib-only worker/process helper definitions. No actual pilot
has been run by its software tests. A successful parent report cannot establish
sampling eligibility, scientific improvement, native qualification, or a Lean
certificate. It does not read snapshot contents, geometry, protected catalogs or
held-out metadata; it verifies external file descriptors and hashes.

## CLI and externally prepared inputs

Use the repository's intended Python interpreter with `-B`. The two modes are
`--mode plan-only` and `--mode execute`. Both require:

- `--input-roster PATH --expected-input-roster-sha256 SHA`;
- `--namespace-projection PATH --expected-namespace-projection-sha256 SHA`;
- `--source-commit FULL_COMMIT --output FRESH_ABSOLUTE_DIRECTORY`.

Execution additionally requires explicit finite nonnegative
`--project-cpu-used-seconds` and `--audit-cpu-used-seconds`. These are the
operator's externally reconciled cumulative charges, including failed prior
research preparation. Unknown prior usage is not zero. The audit prior charge
must not exceed the aggregate project prior charge. There is no lane borrowing.
The CLI exposes no injected source state, runner, fixture runtime or alternate
model. Private Python parameters exist solely for authored software tests.

The input roster has exactly `schema`, `repo_root`, `asset_root`,
`prepared_graph_directory`, `source_commit`, `files`, `runtime_metadata`.
`schema` is `change-audit-input-roster-v1`; `files` is a bounded nonempty list of
unique absolute `{path,size_bytes,sha256}` rows. `runtime_metadata` is a nonempty
object retaining the independently reviewed dependency/model/configuration
identity. Its completeness remains the external preparer's responsibility.
The parent neither discovers inputs nor manufactures this roster.

The namespace projection has exactly `schema`, `roots`, `reserved_seed_ids`,
`source`, `scope`, `protected_catalogs_read`. Its schema is
`change-audit-pilot-namespace-projection-v1`. `roots` contains exactly four
`{root_id,scenario,texture,seed}` objects with distinct root IDs and seeds.
`reserved_seed_ids` contains unique bounded integer IDs, with no intersection
with the four selected seeds. `source` is an independently pinned file descriptor
also present in the input roster. Scope must be `approved-public-cohort-ids-only`
and `protected_catalogs_read` must be false. These are public ID checks only;
they establish no geometry, pretraining, or probabilistic sampling disjointness.
All four roots may use reproduction/checker with four distinct seeds.

JSON is bounded, duplicate-key rejecting, and finite even for numeric overflow
such as `1e999`. All readonly input files are regular files without symlink
traversal. Their sizes and hashes, both external JSON pins, the public source,
actual clean tracked HEAD, and generated configuration hashes are checked again
between jobs and after close. The production source root must be the executing
parent's own repository. Untracked output does not make tracked source dirty;
any tracked edit or HEAD change refuses execution. Plan-only performs these
readonly checks and returns a plan without creating output, a lease, or workers.

## Phase ordering and acceptance

Execution creates one fresh namespace; existing output is never resumed. The
parent owns one StorageBudget lease across worker execution, frozen manifest
publication, and terminal report publication. Each worker receives the shared
root and policy instead of acquiring another lease. Log directories are created
by the parent; each worker's artifact directory must remain absent until that
worker creates it. All controls and attempts are exclusively created.

Four preparation jobs each capture one gain-one original anchor with no forward
attempt and no tick. The parent accepts each only after both successful,
complete/drained process accounting and a successful, production-scope worker
stage report. It checks descriptor shape, path containment, ZIP size and checksum
without decoding state. After all four pass, the parent checks readonly pins and
all originals, admits the complete fixed future condition block, writes all four
anchor descriptor files, and exclusively publishes the full sixteen-condition
manifest. That manifest pins config SHA values, anchor descriptors and their
JSON file SHA values, source/model/namespace identities, limits, roots and gain
order. Conditions cannot begin before this publication.

Sixteen sequential fresh workers then run four gains per root in exact order
`1, .5, .75, 1.25`; every worker uses CPU FLYNN, parity false and 64 requested
ticks. The command preserves the original absolute `sys.executable` alias,
including its virtualenv path; resolving that symlink would lose virtualenv
`sys.prefix` and dependency access. The canonical interpreter ELF remains a
separately pinned input-roster identity. The command uses `-B`, the absolute worker
script, and pinned config/anchor descriptor SHA values. The production worker
accepts no test seam. CPU thread variables are one, CUDA is hidden and rendering
uses EGL. A fresh unused `PYTHONPYCACHEPREFIX` plus `-B` avoids stale ignored
bytecode; Matplotlib uses Agg and a job-local cache inside the budget root.
Source/model/runtime compatibility remains a separate execution gate.

A successful condition requires all process flags, zero exit, exact stage-report
root/mode/gain/scope, no retained errors including close failures, the original
anchor descriptor, equal finite before-first-tick hashes, and exactly one actual
forward per completed tick. Tick-limit means exactly 64 completed ticks. Natural
termination retains a positive actual prefix and terminal outcome, without reset
or padding. Baseline uses the exact original descriptor; candidates must retain
their own capped derived snapshot and derivation receipt. Every scientific and
certification flag remains false. Any failed job, resource/pin/artifact gate or
close error stops the entire pilot. There are no retries, replacement roots,
subsets, tuning, deletions or automatic continuation after outcomes.

## CPU, wall and crash accounting

The parent measures the entire preparation/execution phase using delta
`RUSAGE_SELF + RUSAGE_CHILDREN`, including readonly hashing, source subprocesses,
failed prerequisites and bookkeeping. Process helper fields are independently
validated; `subtree_cpu_seconds` already includes supervisor and worker, so the
parent does not add either worker CPU or the helper charge onto this phase
meter. The preliminary parent report samples through its preparation. An exclusive
`terminal-accounting.json` extends the measured charge through parent-report
publication, and controls final returned status if those operations cross a
resource ceiling. Its 64KiB cap is pre-admitted and the lease remains held through
terminal publication. Terminal receipt serialization/write/fsync, lease release
and process return remain unmetered, explicitly named in that receipt. The actual
CLI invocation requires an independent outer trusted lifetime supervisor to
wait4-meter and reconcile all parent/descendant CPU through process exit. No exact
process-lifetime total is claimed by the parent's point-in-time receipt.

Before each job, admission requires a full 120-second CPU allowance plus 15
seconds administration within both the one-hour audit and 24-hour project
remaining allocations, and a full 120-second wall allowance plus five seconds
cleanup within the 30-minute pilot wall budget. The CPU and wall meters start
before external input validation. The helper receives 120-second per-job CPU
and wall thresholds. Polling and cleanup are bounded operational controls, not
hard zero-overshoot or realtime promises; complete final charges are retained
and a ceiling overrun stops further admission. No promise is made that twenty
worst-case 120-second jobs fit the global 30-minute wall bound.

A running ledger record is fsynced before each invocation. Complete/drained
accounting and job acceptance have separate exclusive durable events. Missing,
malformed, nonfinite, incomplete, or undrained accounting produces a stopped
parent report with `phase_cpu_seconds=null`; the observed SELF+reaped CHILDREN
lower bound is separately retained. Unknown is never zero. No more worker may
be admitted. An interrupted parent leaves its running ledger as incomplete;
the fresh-output rule refuses automatic resumption. Execute preflight failures
also retain a fresh admission-failure record when storage permits. If even
terminal control publication fails, the exception and earlier durable records
remain; no success is reported.

## Storage arithmetic and limitations

The root cap is 512MiB with a 6GiB free-space floor. Native stdout/stderr retain
at most 256KiB each for twenty jobs, a total 10MiB prefix cap. A preparation or
candidate snapshot is at most 16MiB, each recording at most 15MiB. Four originals
plus twelve candidates give at most 256MiB SNPs. The parent never assumes
preparation recordings are small: before the first worker it admits the
entire zero-forward preparation block,
`4*(15MiB recordings + 16MiB SNPs) + 8*256KiB logs + 12MiB controls + 16MiB unused headroom = 154MiB`.
After four preparations it measures retained bytes and checks the whole future allocation before any condition inference:

`16*15MiB recordings + 12*16MiB derived SNPs + 32*256KiB future logs + 12MiB controls + 16MiB unused worker headroom = 468MiB`.

This is added to actual retained preparation bytes. A preparation-heavy run is
therefore refused even though each individual preparation was legal. Existing
control files are conservatively counted in actual usage and again in the full
future control envelope; this can refuse early and never relaxes the cap. The
16MiB headroom is unused reserve required by worker CLI checks, independently of
retained log/control bytes; it is not counted as another written file.

The 12MiB control envelope admits at most 4MiB serialized initial controls,
36 worker reports/receipts of at most 128KiB, four anchor descriptor files,
256KiB condition/parent manifests, a 64KiB terminal accounting receipt, and at
most 64 ledger files of 8KiB.
Any individual parent record that exceeds its bound stops the run. Worker
recordings and snapshot saves use the cooperative shared budget; the supervisor
monitor recounts only this bounded output root and checks the unused reserve.
Its short callback executes in forked supervisor memory and never mutates parent
state. Native direct writes can overshoot between scans: this is not a kernel
filesystem quota or a sandbox for hostile workers. No partial file is deleted.

Software tests use authored bytes, JSON and an injected runner only. They prove
supervisor ordering and refusal behavior; they provide no inference, performance,
physical, sampling or model-restoration evidence.
