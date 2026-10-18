# Bounded CPU worker phase diagnostics

The immediate product goal is one real CPU episode with recording, replay and
portable export. Qualification07 exhausted its normal-return deadline with empty
worker streams and no final outcome. These diagnostics narrow the next failure
location; they do not qualify that runtime or replace the episode deliverable.

## Source contract

- Change only the seeded bootstrap and fixed import qualifier. Select tracing
  from the already validated CPU qualification-v3 descriptor; add no environment,
  registration, argv, namespace, loader, provider or input option.
- Emit 18 nominal stderr checkpoints: validated bootstrap entry, source ready,
  dependency entry/return, bootstrap ready, entry invocation, before/after each
  fixed import, entry return/snapshot ready, and final close entry/return.
  The first checkpoint is after registration parsing, not Python/SEED entry.
- Keep terminal stdout after successful final context close. An import-return
  marker precedes version/guard acceptance. Even all 18 markers can precede a
  final deadline refusal; markers never establish acceptance or parent closure.
- Bound this trace component to 24 attempted writes / 16 KiB encoded bytes,
  with at most 512 characters in a phase name. Charge attempts before writing.
  Short writes and ordinary telemetry exceptions permanently disable tracing,
  including a failure nested inside an otherwise successful write.
- Preserve the real outcome when telemetry is unavailable. Cancellation closes
  owned holders and propagates. Do not add markers inside failure cleanup or
  change its first-exception, reverse-close, poison or terminal behavior.
- Keep legacy qualification-v1/v2 silent. A qualifier running under an older
  admitted bootstrap without the optional diagnostic hook retains its behavior.
  The qualifier captures an available bound hook before its four fixed probes.

The limits cover this component, not unrelated vendor stderr or blocking-write
latency. The existing whole-worker stream and operational deadlines still apply.
Bootstrap helper methods are not automatically class-slot-bound by the loaded
module guard. Missing, partial or modified traces cannot establish complete,
authentic or causally sufficient runtime evidence.

## Verification and next runtime boundary

Use tiny authored packages and existing worker fixtures to verify normal order,
legacy silence, import/version/admission failure, snapshot/close failure, actual
expired-deadline guards, post-marker refusal, both caps, short/error/reentrant IO
and cancellation cleanup. Preserve genuine REDs and every failed validation run.
Run nearest dependency, parent/auditor/observer and historical-publication
consumers under the storage conditions their fixtures require.

The unit is finished when those authored checks pass, independent source review
has no material findings, and exact source/test/log evidence is committed. No
installed import, operator, renderer, episode, model or study executes here.

Before any future runtime diagnostic, define and independently review a distinct
closed source epoch. The qualifier is a fifth preparation-relative changed path,
in addition to the parent, bootstrap, dependency bindings and dependency importer.
Existing epoch05–07 predicates must remain strict; do not widen them or reuse07.
Keep the source path roster, candidate D, remaining inputs, nineteen absences,
staged identities and resource limits explicit. Refresh full current byte/custody
and resource admission, then permit at most one separately frozen invocation and
independent outcome audit. No08 controls or invocation is created by this source
unit, and failed07 remains consumed with missing receipts preserved.

All seven simulation-release gates remain open. Full-repository tests, CI,
physical rover work and protected catalog access are outside this unit.
