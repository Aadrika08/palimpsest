# Bounded guard diagnostics; original checks retained

The compatibility review retains the original per-name whitelist union. Even
exact builtin containers and strings do not freeze asynchronous mutation between
a cached allowance snapshot and its use. No small equivalent fastpath is
supported by the current mutation contract. PR169's faster but incompatible
experimental copies remain rejected; no stronger mutation policy is adopted.

The implementation at `57e2e793edddc8fddc20b4af77e8a8a0035463a0` adds bounded
guard-time accounting in `scripts/puck_worker_bootstrap.py`. This is the only
production file changed from `3975f8a158c0899e9c640b323488de9a0f0a40df`.
Independent source review strips the accounting calls/local bookkeeping and
finds the original `_check` predicates and order unchanged. The qualifier,
parent, observer, auditor, stdout receipt and registration schema are unchanged.

## Contract and corrections

Only already validated CPU qualification-v3 enables the new
`puck-worker-guard-cost-v1` stderr records. Qualification-v1/v2 stays silent.
Records report outer full/light checks started/completed, nested checks and
completed-section nanoseconds/visits for bindings, cache, custody and images.
Nested work remains charged to its caller's section. Completion increments only
after the original final deadline check succeeds; an end-of-section record can
show no active section while a completion is still pending.

Eight import enter/returned boundaries force cost records. Guard entry/section/end
checkpoints also cooperatively emit after ten seconds, without catch-up bursts.
There are at most 32 attempted writes/32KiB and 1024B per cost row. Phase-v1 keeps
its existing fields and independent 24-attempt/16KiB cap. Exhausting a channel's
budget affects that channel; a short or failed stderr write disables both.

The retained REDs exposed final-deadline bypass, reentrant clock/encoder I/O,
output after caught refusal/poison and a failed guard counted as completed.
Corrections put accounting finalization before the original final clock and
completion after it, cover clock/encoding/write with the cost reentry latch,
recheck eligibility immediately before output and reject backwards nanoseconds.
Ordinary diagnostic errors disable diagnostics; cancellation closes and
propagates. First failure and terminal-stdout-after-close behavior remain.
The initial cancellation assertion matched a marker embedded in a traceback;
the stronger actual-exception assertion and its separate RED are preserved.

The existing authored08 consumer initially failed with `KeyError: phase` because
it treated every stderr JSON record as a phase. Its test now splits by record
kind and verifies cost caps while retaining the exact eighteen-phase sequence,
source/dependency bindings, API/CLI audits, closure and reentry checks. Historical
actual08 controls and raw evidence were not rewritten.

## Validation and independent review

Final validation passes **304 disjoint authored cases**:

- Thirteen private-storage worker, diagnostic, dependency, parent, observer and
  auditor files: 302 passed in 242.70s; external normal exit 0 in 242.980s.
- Both persistent historical-publication integrations: 2 passed in 24.43s;
  external normal exit 0 in 24.653s. These cover the old four-path/optional-hook
  route and current five-path CPU-v3 parent/API/CLI route.

All twelve command/log/terminal/source-snapshot batches are retained. Earlier
RED/green selections overlap and are not added to the final 304. Tests use
CPython3.11.15, disabled pytest plugin autoload/bytecode/cache and their required
private or persistent storage under bwrap. Private temporary worker trees are
not retained; their aggregate logs/source identities are preserved.

Source review02 found no material findings at the final source/test pins; its
reviewed plan is retained separately because completion checkboxes changed.
The earlier source review is superseded and retained. A separate final evidence
review checks command/terminal/source pins, disjoint selections, preserved REDs
and the positive authored08 logs without rerunning tests or installed payloads.
Its conclusion is GO for scoped source/authored evidence, with no material
findings. The 44,094B review SHA256 is
`04a4b1e3afa4fb11e6cf7878f63676a599d66155c3ceecd634268455fcbc4c32`.

The positive authored08 fixture retains eighteen phase and eight cost records.
At its last import checkpoint full checks are 94/94 and light checks 49/49. Its
CLI audit is PASS; parent/auditor report balanced 5→5/4→4 descriptors and no active
children/non-main threads. These are synthetic fixture receipts, not independent
installed process-lifetime or FD proof. The unchanged auditor binds stderr bytes
but does not authenticate or semantically validate cost records. The API return
object and a separate CLI-process terminal are not individually archived; their
assertions are retained in the passing integration test and aggregate log.

The finite [evidence index](puck-cpu-guard-accounting-v1/evidence-index.json)
binds source Git, all raw batches, selected positive-fixture receipts, reviews,
reviewed plan and the reused byte verifier: **136 artifacts / 1,560,197B / 13 empty
files**. Its index SHA256 is
`8bfe3981a960abc351ef95747197379ed19c55d923da6418c162de95a8be9f87`.
Original/archive/source-Git verification passes. Verify the committed packet with:

```sh
python docs/reports/puck-cpu-guard-accounting-v1/verify_evidence.py --originals --git-revision <evidence-commit>
```

## Limits and next exit

Cost elapsed nanoseconds begin at the first guard, independently of phase elapsed
seconds. Do not subtract these origins. Section totals include instrumentation
and nested work; images cover only images calls inside `_check`. Native work
elsewhere, initializer work and preparation are outside this accounting. A
blocked call can prevent updates, so this is not a heartbeat, exhaustive profile,
authenticated trace or hard timing. Trusted Python helper state remains mutable.
Budgets bound this component's attempted output bytes, not blocking-write latency
or vendor stderr; instrumentation consumes the unchanged 180s deadline.

Next implement and independently review **closed09 source support** for this
bootstrap, preserving existing acceptance/refusal semantics, frozen inputs and
limits. Finish authored metadata, observer and parent/API/CLI evidence first;
actual09 controls and fresh byte/custody/resource admission are a separate unit.
No 09 controls, admission or installed runtime invocation exist in this change.

Attempts 01–08 remain consumed; the installed 08 timeout's cause remains unknown.
The 180s deadline, 2GiB qualification RAM floor and all seven release gates stay
unchanged. This source pass does not qualify the runtime, episode, renderer,
operator, models, studies or release. Full-repository tests, CI, installed vendor
qualification, actual renderer/artwork sessions and physical checks were not run.
