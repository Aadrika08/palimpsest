# Bounded guard accounting toward the real episode

The compatibility review retains the per-name whitelist union. Exact builtin
containers and strings do not freeze mutation: a callback can remove an allowance
between a cached snapshot and its use. A precheck or an additional traversal of
a custom module cache cannot establish the existing acceptance/refusal behavior.
PR169's two faster probes remain rejected. No stronger mutation policy is adopted.

Implement a bounded diagnostic extension in `scripts/puck_worker_bootstrap.py`
with authored tests in `tests/test_puck_guard_time_diagnostics.py`. Leave the
qualifier, registration, stdout receipt, guard predicates and their order intact.
This is a prerequisite for the real recorded/replayed/exported episode, not
installed-runtime acceptance. Preserve consumed 01–08; create no 09 controls,
admission or invocation. Keep the 180s deadline and 2GiB RAM floor unchanged.

## Diagnostic contract

- Activate only for the already validated CPU qualification-v3 selection.
  Legacy qualification-v1/v2 stays silent. The qualifier needs no new hook.
- Accumulate nanoseconds and section visits for binding reconciliation, module
  cache scanning, held custody/identity and native-image observation. Time only
  outermost checks; nested guards remain charged to their caller's section.
  Record outer full/light started/completed counts and nested-check count.
  Completion increments only after the original final deadline check succeeds;
  an end-of-section diagnostic may still show a pending completion.
- Emit separate `puck-worker-guard-cost-v1` stderr records at the eight exact
  import entry/return phase boundaries. Cooperatively emit at guard entry/section
  boundaries after ten seconds, resetting the next update without catch-up bursts.
  Include import context and active section/mode. Totals include completed
  sections; an in-progress section is labelled separately.
- Bound this component to 32 attempted writes / 32KiB, at most 1024B per row.
  Preserve phase-v1's independent 24-attempt / 16KiB budget and fields. Charge
  attempts/bytes before writes. Suppress nested cost emission, and permanently
  disable both channels after stderr I/O failure or short writes. A channel's
  budget exhaustion disables that channel only.
- Ordinary diagnostic clock/state/encoding failures disable cost diagnostics;
  they do not grant authority or replace the real operation. Cancellation closes
  owned holders and propagates. Emit nothing from failure cleanup. Keep terminal
  stdout after final close and deadline checks, and preserve first-failure poison.

These are sampled diagnostics, not a heartbeat, authenticated trace, exhaustive
cost breakdown or hard timing. A blocked call may prevent updates. Accounting
and writes consume the unchanged deadline; budgets do not bound blocking-write
latency or vendor stderr. Helper slots remain within the existing trusted-source
boundary. Future installed use needs a distinct reviewed source epoch and fresh
resource/byte/custody admission.

## Verification and exit

- [x] Preserve initial REDs for rows/counts/contexts, periodic updates, budgets,
  ordinary and reentrant I/O failures, malformed clocks, cancellation and cleanup.
- [x] Implement the extension without changing guard predicates or qualifier.
- [x] Run focused authored diagnostics, existing phase/refusal/legacy and nearest
  worker/consumer checks under their required storage conditions.
- [ ] Independently review source and evidence, retain raw outcomes and exact
  source identities, commit/push the source unit and update the active goal.

The seven simulation-release gates remain open; no fixture pass substitutes for
runtime/operator/renderer qualification, the episode or human acceptance.
