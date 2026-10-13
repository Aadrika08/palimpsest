# Puck-v3 native interval source boundary

This implements the bounded [source plan](m6-puck-v3-native-interval-source-plan.md),
stacked on `347a838389d7532b1727ad90bddd9b2bdca617cc`. Actual native capture,
filesystem namespace persistence, complete source collection and scientific
qualification remain unproved. No collection envelope is enabled.

`capture_query_state` reuses `snapshots.capture` and adds exact complete native
model bytes, puck identity/reset/binding caches and planner caches. Its result
contains the native snapshot/environment/profile/application state, retained
observation and independently retained Python, NumPy, CPU/CUDA Torch,
environment/seed and recursively collected Gym-space RNG states. Uninitialized
environment RNG and active callbacks are rejected. Native/model bytes are
bounded before snapshot copying; copied data payload bytes are bounded to
8 MiB. This is an in-memory payload bound, not a claim about serialized snapshot
size. The frozen initial-snapshot file limit needs its later owner admission.
There is no step, forward, reset, render, observation refresh, restore or RNG
draw in this function. Synthetic fake native and fake Torch boundaries prove
the selected capture mechanism; real native coverage remains unqualified.

`verify_puck_mechanics.on_policy_interval` requires matching actual native world,
data time and native/task/contact/own tick before any teacher query or student
inference. It stages one teacher label and one student action, prevalidates
both candidate cursors, and executes exactly the student action once. Probe
installation, begin/step/end have finally-close coverage. Existing contact,
control, world, packet and task arithmetic is reused. The new row's teacher
query mode names preserve historical reader rejection. The event retains exact
pre/post task, world and contact states; publication independently recomputes
the task/reward transition and pre-action sensor projection, and checks native
completed tick/time/control plus world, reward and normalized task digest arrays.
Any query/inference/probe/step/packet/task/cursor/publication failure poisons the
writer. A second invocation performs no teacher/inference/step. Physics has no
rollback. The returned own/teacher cursors are prevalidated and exposed only
after successful publication.

`PuckIntervalWriter` retains one fresh per-interval `RunWriter` transaction.
Its completed one-row recording and matching event are bound by exact bytes,
file identities and a predecessor chain. The admission marker is the last
no-replace hard link to an already fsynced commitment anchor, after all recording
and directory checks/fsyncs. Root/transaction/recording/chunk directory identities
and exact paths are checked through that boundary; no fallible work follows the
link. Both commitment names count toward the exact retained-byte allowance.
Before writing the commitment anchor, publication exhausts the candidate through
the unchanged strict numeric reader, checks the exact completed manifest and
chunk/event schema, and compares its decoded staged row, every numeric array and
event against immutable pre-write hashes/bytes. File hashes alone are not
admission: a self-consistent rewritten row/event also fails before commitment.
`read_committed_intervals` admits only the verified contiguous prefix and
rechecks files, marker and directory identities during reading. Failed raw
transactions are retained but cannot become rows. Missing first commitments
yield an empty prefix; malformed commitments or a committed row after a gap
reject the recording. A prefix is failed evidence, never a completed source.

The final marker link has no subsequent directory fsync: namespace durability
under sudden power loss remains unqualified. Recovery never synthesizes a
missing marker from its anchor. Earlier data/anchors remain conservatively
recoverable when their final links survive. This source boundary does not claim
atomic persistence of a RAM cursor or qualify a complete numerical owner.

The historical `RunWriter`, `snapshots`, `puck_profile`, mechanics/construction
protocols and v3 frozen protocol bytes are unchanged from the base. Every old
mechanics function has the same AST, except `owner` has one leading denial for
the named unqualified v3 envelope. That denial precedes old protocol routing
and protected imports. Existing historical profile-pin mismatch remains intact:
no frozen historical pin was changed or bypassed. The frozen v3 protocol remains
SHA-256 `fe8b2615f965a114274a13aeb2d49c26d3f79e0920eee72bce4eb671adff3d13`.

Verification with the existing Python 3.11.15 / NumPy 2.2.5 reproduction
environment, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests`:

```
python -m unittest tests.test_puck_on_policy_native_interval \
  tests.test_puck_on_policy_interval tests.test_puck_on_policy tests.test_records
```

77 tests passed. RED commits retained missing APIs, accepted native packet/event
disagreement, missing 8 MiB capture enforcement, omitted probe-install cleanup
and stale pre-action admission. GREEN coverage includes real temporary-file
RunWriter/storage accounting, complete successful two-interval prefix, file/
event/finish/fsync/anchor/link failures, root replacement, malformed/swapped/
gapped recording rejection, fake native/model/wrapper/observation/RNG mutation,
historical reader rejection and pre-import unqualified/held-out denial.
Independent review of `8e4c4cc` STOPped publication after a post-finish chunk
corruption was accepted and only later rejected by the reader. RED `34e7cf1`
reproduced that failure and three self-consistent replacement/manifest cases;
the candidate decode/compare gate rejects them all before an anchor or marker,
without advancing either writer cursor, while retaining the earlier prefix.
Compilation, fresh imports without Torch/MuJoCo, historical AST/byte identity
and whitespace checks passed. Full project/native/model tests were deliberately
excluded by this source-only authorization; no registry, retained input, model,
Torch/MuJoCo runtime, scene minting or numerical episode was accessed.

Remaining gates: complete native capture coverage and writer crash/power-loss
qualification; inventory scanner/reservation and scene admission; exact immutable
model/source/runtime admission; budgeted stage/owner manifests and attempt/
deadline/process/storage contracts; independent source/execution review. These
functions authorize no collection, fitting, development, held-out or hardware.
`qualification_claims` remains empty.
