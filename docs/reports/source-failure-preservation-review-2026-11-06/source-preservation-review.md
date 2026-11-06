# Bounded source failure-preservation review

Spec: **FAIL pending the narrow test correction below**.
Production quality: **APPROVED**. No preservation implementation findings.
Test quality: **CHANGES REQUESTED**, one P2 finding accepted by root.

Reviewed the uncommitted three-source-file diff and new dedicated test against
HEAD `b7a967026d1261b20450024e271f7cfc790dfd17`, the bounded brief, implementation
report, retained RED/GREEN/covering logs, and relevant existing bootstrap fixture.
HEAD readback matches that base. The owned source diff is 31 insertions and
13 deletions; the dedicated test is untracked. No tests were rerun.

## Spec and mechanism

- `snapshots.py:610-620`: keyword-only `preserve_failed=False` rejects non-exact
  bools before imports, encoding, budget checks or output. The existing encoder
  and exclusive container creation remain unchanged.
- `snapshots.py:661-670`: creation remains outside the failure cleanup handler;
  preexisting targets therefore cannot be unlinked. True retains actual target
  bytes after partial-write, flush or fsync errors and propagates the error.
- `records.py:26-36,48-58,302-314`: all manifest/background-chunk/synchronous-chunk
  pending writers retain their existing exclusive creation and publication.
  True skips cleanup; successful replace consumes the pending name normally.
  Existing pending files fail exclusive creation without truncation or unlink
  in preservation mode. Ordinary running-manifest replacement is unchanged.
- `records.py:139-142,182,214,103`: public exact-bool validation and flag threading
  cover constructor, manifest, background worker and existing synchronous path.
  The private helpers receive the already validated flag. No serializer,
  publication block, retry or custom writer was added.
- `records.py:187-217,309-316,327-367`: existing broken-state and background error
  propagation/drain/close behavior remains in place. Disk failure cannot finish
  a run successfully, reuse the failed pending leaf or resume through public
  writer operations. Retention does not bypass existing quota checks.
- `engine.py:359-362,476-478`: only the accepted canonical bootstrap mode selects
  preservation. The default invocation omits the new keyword entirely.
- Source docstrings explicitly leave failed bytes chargeable and atomic-space
  reservation to future source admission. This patch does not add that owner.

## Evidence assessed

- Corrected `source-preservation-red.log`: **42 failed, 21 passed in 0.70s**;
  failures include unsupported new keyword/validation and the previous deletion
  of canonical Engine's failed manifest pending file.
- `source-preservation-green.log`: **63 passed in 0.65s**.
- `source-preservation-covering.log`: **119 passed in 3.37s**; the implementation
  report identifies bootstrap, recorder and background-recorder test modules.
- `source-preservation-diff-check.log` records `git diff --check exit=0`.
  I inspected these existing results rather than performing another execution.
- Dedicated tests inject real partial writes and flush/fsync/replace errors into
  the existing writer paths, inspect retained bytes and published manifests,
  check no completed result or readable tick after failure, and verify retry
  refusal (`test_source_failure_preservation_vnext.py:83-105,141-222`).
- Success-byte equivalence uses the real container/recorder encoders, with SNP
  ZIP clock control, real decode and synchronous/background completion
  (`:108-138`). Failure tests join/close actual writer threads (`:172-179`).
- Quota refusal and physical StorageBudget recount use authored small arrays
  and retained bytes (`:225-247`). No retention-only budget bypass appears in
  the production diff; broader reservation semantics are not implemented.
- Canonical Engine failure test uses the imported authored bootstrap fixture
  and real RunWriter (`:250-259`), retaining the actual readonly resolver and
  held/world validation. It observes failed manifest retention and resource
  closure with the published manifest still running.

## Finding

**P2 — remove unnecessary guard-to-success patches from the active default
compatibility test**, `tests/test_source_failure_preservation_vnext.py:266-267`.
The test substitutes `verify_assets` with unconditional success and substitutes
`prepare_graph` to reach a complete legacy Engine invocation. Although this
controlled boundary avoids ambient acquisition and does not affect the real
canonical preservation test, the brief prohibits patching guards to success.
The required keyword-omission assertion needs only the writer entry boundary:
use a legacy-signature callable that raises a dedicated sentinel immediately,
then require that sentinel from default `Engine.open`. An accidentally passed
`preserve_failed` keyword instead raises TypeError before entering the callable.
Keep the fixture's denied acquisition functions intact. Root accepted this
narrow correction after initially allowing the controlled legacy boundary.

The existing full-path result remains historical controlled-boundary evidence;
it must not be cited as proving real asset verification, graph preparation,
source admission or qualification. The canonical test (`:250-259`) keeps its
actual readonly resolver and held/world guards intact and needs no change.

## Scope and limits

The initial RED test-location correction is disclosed in the implementation
report; the corrected RED log is the evidence assessed here. Test invocation
environment and retained basetemp paths are recorded by the implementer; I did
not execute commands to revalidate those retained fixture directories.

This is review of the preservation prerequisite only. Atomic-space admission,
source ownership of SNP saving, wider source lifecycle contracts, and historical
Engine error aggregation are outside this patch. The future source caller's
synchronous-only policy is not established by exercising recorder background
compatibility. Injected unit failures do not prove filesystem crash durability,
native/model behavior, actual source success, experiment readiness, CPU-provider
qualification, or research conclusions.

Review performed with read-only source/log inspection and this report as the
only write. No test/import/runtime/native/model execution, actual source or
protected data inspection, network/service/CI/dependency operation, cleanup,
git mutation, or delegation was performed.
