# Actual CPU held qualification04: FAIL, consumed

The single frozen and freshly admitted04 invocation exits1 normally, without
timeout, in **43.401521891 s** (terminal `cb9b93`). The parent records FAIL after
43.300620780 s, descriptors5→5 and no children/non-main threads. The diagnostic
source change preserves the original cause and identifies the actual binding:

```
producer='torch._C'; phase='native_create'; export='torch._C._autograd'
attributes=['_autograd']; missing component '_autograd' at index0
```

Worker stdout is0B; stderr2,914B, SHA256
`e85945e341df69808e9b0d460eaf9cabdb516675567f21c1142e37ab6ed8391c`.
Native creation returned; native execution and all four imports did not complete.
This is the observed04 row. It does not recover03's unlogged row, qualify the
other35 native-create declarations or establish a replacement phase.

The8,835B configuration SHA6fa33667… and7,599B reviewed freeze SHAa34d83b1… were
committed at `de2d4ca49f4d784ea1128824a19ea6d8d912e853` before invocation. The
closed04 source proof independently passes246 affected checks in86.90s. Admission
at16:30:08UTC records3,096,526,848B available RAM,3,579,727,872B tmpfs free and
98,637,963,264B project free against unchanged2GiB/256MiB/4GiB floors. It verifies
44 current pins, six controls, four dated data-proof pins,95 historical archive
entries,83 immutable originals and54 capsule leaves. Ten changed historical live
script comparisons are excluded; their archived bytes remain verified. An
independent read-only preservation check confirms those counts and all old
baseline absences. The four staged roots retain their accepted device/inodes.

The frozen independent acceptance auditor exits1 normally in0.064069714s
(terminal `acfed5`), publishing FAIL on `Normal external transport exit required`.
Its617B publication SHA0c899f2f… matches stdout. It refuses **before** post-stage
byte checks; `baseline-after.json` is absent. This is neither a passing failure
audit nor held-runtime or post04 staged-byte acceptance. The separate pre04
data-only census at16:06:25UTC remains dated before the invocation and retains
only its own scope.

The supervisor reports sampled peak RSS386,580,480B,0.05s sampling and no matching
survivors. Independent host `/proc` observation at16:32:02UTC finds all three
tracked PID/start identities absent (terminal `dd005e`). Those observations and
FD closure establish reported operational cleanup, not hostile containment or
hard timing guarantees.

Static source inspection now explains why this particular declaration is too
early. The authenticated installed Torch version file declares source commit
`0fabc3ba44823f257e70ce397d989c8de5e362c1`. Its installed `torch/autograd/__init__.py`
matches that exact upstream file byte-for-byte (25,424B, SHA0439167a…). At line558
it calls `_autograd_init`, then imports the resulting module at line562. The exact
[upstream method table](https://github.com/pytorch/pytorch/blob/0fabc3ba44823f257e70ce397d989c8de5e362c1/torch/csrc/Module.cpp#L1564)
maps that callback to `THPAutograd_initExtension`; the
[implementation](https://github.com/pytorch/pytorch/blob/0fabc3ba44823f257e70ce397d989c8de5e362c1/torch/csrc/autograd/init.cpp#L102)
creates `_autograd` at line135 during that later Python initialization. This is a
source-supported explanation of the premature native-create check, not a trace
of the unexecuted later callback or proof of the linked binary's source build.
The exact upstream files, package source, licence and source index are retained.

Next: prove the lifecycle of this delayed export with authored fixtures, including
its appearance/import before the Python initializer finishes, raw producer-edge
identity, cache custody, completion and refusal on mutation. Inspect the other
declared exports individually before any profile correction. A producer/phase
change remains prospective; changing every row, skipping one or waiting until
parent completion without proving intermediate cache admission is unsupported.
Do not create or invoke05 from this failure report. Review any new source/profile
amendment separately before a future actual allocation.

[Exact evidence index](puck-cpu-held-qualification-04/evidence-index.json) preserves
all20 raw leaves, the ten-file fresh source capsule, streams/transport, admission,
custody, auditor CLI/publication, frozen controls, observer programs and source
inspection. Empty directories and absent baseline-after are explicit. The
[terminal ledger](puck-cpu-held-qualification-04/observation-ledger.json) separates
actual observations, static inference and dated data-only evidence. Historical
01–03 remain failed and consumed;04 is now also consumed. No05 exists. Passing
held qualification and the actual recorded/replayed/exported episode remain
unfinished. All seven release gates are open. No full suite, numerical study,
controller, operator/renderer, artwork, human or physical acceptance is claimed.
