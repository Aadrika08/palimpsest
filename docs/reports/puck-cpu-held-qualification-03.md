# Actual CPU held qualification03: FAIL, consumed

The single reviewed qualification03 invocation returns external exit1 normally,
without timeout, in **45.51643660804257 s** (terminal `82ce07`). The parent records
FAIL after45.43247786100255s, with FD5→5 and no children/threads. Its ten-file fresh
source capsule is retained. Original01/02 outcomes remain failed and consumed.
No04 configuration or invocation has been created.

The exact optional-missing-import correction gets execution beyond02's
`torch._rocm_init` guard denial. Actual03 reaches Torch's `from torch._C import *`
at line427 and native `create_module`, then fails inside
`ExportBindings.complete(torch._C, native_create)` → `_resolve`:

```
RuntimeError: Dependency producer attribute binding is missing
```

Worker stdout is0B; stderr2582B, SHA256
`168769c9867a5dc516daada884738aecef8944cb5f6f372b9fc6428c162bef70`.
Native creation returned before this check, but native `exec_module` and all four
imports did not complete. Static inspection of the authenticated profile finds
36 declared `torch._C/native_create` rows with null class bindings. The generic
error identifies neither the failing row nor attribute component. `_aoti` is
first in the roster, not proven responsible. No replacement phase or producer is
established. Bootstrap, provider, namespace and profile were not changed by03.

The8,835B configuration SHAc6f5807c… and7,403B sealed freeze SHA2470b8fe… were
committed at `8111299d2abfcb0ba6b2c075a8bde5bc90adb086` before invocation.
Independent review verifies44 current pins, five controls,34 historical capsule
leaves and four separate current-data-proof pins. Fresh admission records
MemAvailable3,729,133,568B, /tmp free3,657,646,080B and project free99,105,910,784B
against unchanged2GiB/256MiB/4GiB floors. All111 prior original evidence artifacts
were checked. These are dated observations, not future admission.

The separately reviewed data-only census passes at15:06:59UTC: external normal
exit0 in13.446514741s,27,255 files/1,318,494,346B across four roots and FD4→4.
Publication SHA373215b8… is dated **before03**. It is not preparation reacceptance,
a passing failure audit, held qualification or post03 byte acceptance. The four
historical preparation-acceptance pins remain unchanged.

The frozen independent acceptance auditor returns exit1 normally in
0.051284271s (terminal `2b1134`) and publishes FAIL:
`Normal external transport exit required`. Its617B publication SHAec469ff4…
matches stdout. It refuses **before** post-stage byte checks; `baseline-after.json`
is absent. This is not a passing failure-preservation audit or post03 byte
acceptance. The failure diagnostic keeps its existing v1 schema; no passing v3
qualification audit exists.

The supervisor reports three tracked PID/start identities, no matching survivors
and sampled peak RSS389,070,848B. Independent `/proc` observation at15:17:38UTC
finds all three identities absent. These observations and FD5→5 establish reported
operational cleanup, not hostile-process containment or hard timing guarantees.

[Exact evidence index](puck-cpu-held-qualification-03/evidence-index.json) retains
configuration/freeze, admission, raw invocation/dependencies/descriptor, fresh
source capsule, logs, observer transport, acceptance-audit publication/CLI and
custody. Empty directories and absent baseline-after are explicit in the index.
[Terminal ledger](puck-cpu-held-qualification-03/observation-ledger.json) separates
actual failure from static interpretation and dated pre03 data evidence. The
[source amendment report](puck-cpu-held-qualification-amendment-03.md) retains the
separate **185 passing affected checks in53.58s** and source-only review. No full
repository suite is claimed.

Next: expose bounded producer/phase/export/attribute-component context at the
shared resolution failure and prove it with authored exports while preserving
the exception cause and refusal behavior. Source fixtures cannot recover03's
unlogged row. Review the diagnostic source/data transition before any separately
numbered actual invocation; its retained context may identify the binding. Any
later producer/phase correction must follow that observed evidence. Do not guess
a producer, skip rows or start04 from this report.
Passing held qualification and its independent staged-byte/cleanup audit still
precede the recorded/replayed/exported episode. All seven release gates remain
open; no scientific, model, renderer, artwork, physical or release acceptance
follows from this failed allocation.
