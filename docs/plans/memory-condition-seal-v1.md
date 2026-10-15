# Durable single-condition compact sealing: source extension

## Purpose and boundary

Implement the missing post-close condition route for the complete simulation
release: authenticate one raw condition and its retained source, convert and
exhaustively compare it, invoke the production full-model encoded-cell consumer
internally, admit the staged pair, then publish the condition marker last.
The original v4 compact protocol, conversion-v1, pair-admission-v1 and source
marker-v1 remain byte-identical. This separately versioned extension adds no
scientific allocation, model capability, raw pruning or case-close authority.

The qualification branch at2514c47 and its pending amendment02 remain preserved.
No actual passing full-model qualification descriptor exists. The new public
route must refuse a missing, failed, unknown or caller-asserted qualification
before opening model inputs or loading the numerical runtime. Empty fixed trusted
qualification pins implement that current state. The separately reviewed repository
trust anchor, scripts/memory_condition_qualification_pins_v1.py, is explicitly
outside the receipt source closure and extension source pins. It accepts no caller,
path or environment override. This avoids a receipt/helper hash cycle; adding a
real pin later changes only the trust anchor and requires separate reviewed exact
admission of successful execution plus independent outcome evidence. A terminal JSON saying passed is insufficient by itself.

The prospective receipt retains the historical qualification seed400. Generated
family cases use different seeds, and the real cell consumer requires exact
application/policy seed and provenance equality. Therefore this receipt shape
cannot currently admit a generated-family condition. A separately reviewed
historical-proof/per-case-model binding is still required; amendment02 alone
would not make this route ready. Source orchestration must not widen that scope.

## Interfaces and data

New modules are scripts/memory_family_condition_seal_v4.py and
scripts/memory_condition_replay_admission_v1.py. New public functions are
seal_compact_condition(evidence_root, registration, *, case_id, condition, deadline)
and read_sealed_condition with the same arguments. Registration is an immutable
root-relative path/size_bytes/SHA256 descriptor; there is no public policy,
callback, or replay-passed dictionary argument.

The canonical registration has exactly the keys in
[memory-condition-seal-v1-protocol.json](memory-condition-seal-v1-protocol.json).
It binds the case/run/condition/source identities, owner/control and independent
raw-audit slots, source registration/commit/sole snapshot, own/swapped histories,
prior-own evidence when required, and the exact qualification-admission descriptor.
The qualification descriptor occupies a shared contract/evidence reference; the
sealer creates no additional qualification file or duplicate snapshot per condition.
All claims remain the base protocol's all-false values.

The internal qualified_replay context loads a policy only from authenticated
held sources/runtime/asset inputs in an accepted admission. Assets must cover the
checkpoint, edge and seven sibling neuron mapping CSVs used by load_policy.
It checks actual Python/NumPy/Torch identity, Torch profile, full pinned policy,
model provenance and immutable controller tensors. Its returned session owns
.policy, .descriptor and .recheck(); that session remains open through replay,
publication and final validation. A returned dictionary or guarded path alone
would not preserve custody.

The new condition commit embeds the internally generated cell replay result
and qualification reference, alongside exact conversion-v1, pair-admission-v1
and portable snapshot-reference identities. Its new schema is
memory-family-compact-condition-commit-v1. Replay is embedded in the already
budgeted commit.json, with no replay.json, extra receipt file or condition SNP.
The extension authenticates its own source pins separately from the unchanged
base protocol, avoiding a self-referential protocol hash.

## Composition and publication

Validate the registration, condition/run identity, source marker and immutable
qualification before model access. Bind source/SNP/raw/control/history inputs;
recompute the independently published raw audit and bind the complete raw tree.
Convert and independently compare every retained value and legacy/camera digest.
Precreate owned publication directories before strict model-source custody, then
load the model internally, call replay_compact_cell, validate its exact case/run/
operation/trace/count/source-reference identity, and preserve caller state rules.
Write candidate files exclusively; reread their exact descriptor-held inventory;
write the unchanged conversion receipt and snapshot reference; apply staged pair
admission; write its exact receipt; and recheck all inputs, outputs and budgets.
Prepare and fsync the existing temporary marker, then publish via no-replace rename.

One lifetime remains open through marker publication. Any precommit failure
retains all raw evidence and quarantines an output attempt once writing starts.
A postcommit validation failure cannot return valid admission: retain the marker,
quarantine the case, and raise SealIndeterminate. Readers refuse a quarantine or
indeterminate state. No marker is silently overwritten or rolled back. Descriptor
close diagnostics must not conceal the primary validation error. Namespace power-
loss durability remains unqualified; file/directory fsync and no-replace rename
are source mechanisms, not a physical power-cut test.

A sealed reader rederives registration/commit/conversion/pair/replay bindings,
revalidates exact retained bytes and claims and refuses extra/missing entries.
This is not case publication and does not permit removing the raw owner tree.
The actual source-pruning/public campaign route remains a separate prerequisite.

## Bounds and unchanged scientific contract

Enforce the condition's900 rows,29 chunks,25MiB recording,5MiB events and1MiB
recording overhead. Support/control, including owner/worker/snapshot reference,
pair receipt and commit, stays within the existing combined1MiB allowance except
the separately budgeted log/audit streams. At most41 condition files exist at
maximum29 chunks: no new permanent entry. Exact files, directories and aggregate
bytes are checked; no compression credit or emergency reserve is invented.

The frozen nine-condition owner schedule and oracle donor proof are unchanged.
Oracle-before-own affects42/48 families (126/144 cases), while current oracle
admission requires prior-own. That conflict still needs a prospectively reviewed
resolution before all-nine/case close. The single-condition API must retain both
existing constraints; it must not reorder, add donors or fabricate prior evidence.

## Verification and actual prerequisites

Authored tests exercise real RunWriter/raw-auditor/converter/pair code and durable
publication/refusal behavior. Positive orchestration fixtures may replace private
qualification/loading and production-replay seams; those are explicitly not
full-model qualification evidence. Tests must prove the default public route
refuses unregistered qualification before any protected read; no passing actual
receipt may be fabricated for a source test.

Meaningful checks cover exact namespace and raw retention, wrong/cross-bound
identities, replay failure/wrong identity, input/model/output mutation, unsupported
prior-own, deadline and every quota boundary, file/fsync/no-replace publication
faults, quarantine failure, immutable repeated calls and final lifetime checks.
Independent source review and unchanged base-source regression accompany the unit.

Before any real invocation: approved numerical qualification and independent
accepted outcome; exact source/runtime/asset/input configuration and process/
clock/storage admission; native owner/terminal integration; and separately
reviewed pruning/complete case/order resolution as applicable. All seven full
simulation release gates stay open until their actual acceptance evidence exists.
