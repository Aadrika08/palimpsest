# Actual CPU held qualification02: FAIL, consumed

The single reviewed qualification02 invocation returns external exit1 normally,
without timeout, in **38.75431559397839 s** (terminal `e24788`). The parent records
FAIL after38.6615098589682s and FD5→5 closure with no children/threads.
The fresh ten-file source capsule is retained; all original01 artifacts remain.
No03 configuration, invocation or policy change has been created.

The new bootstrap preserves the primary error:

```
ImportError: Unregistered local or external dependency import: torch._rocm_init
```

Torch line152 attempts this import. The later `torch._C` import at line427 raises
`ModuleNotFoundError` and is now explicitly chained to that first error. Worker
stdout is0B; stderr2285B. Static inspection authenticates Torch's102,969B initializer
SHA256 `3caf7f40140ede2465bde40b9003af10cbbc8f7bcf436fa1de026471daa1b288`.
Its lines145–157 describe the optional ROCm module and catch `ImportError`; the
retained CPU registration contains no `_rocm_init` leaf. This establishes02's
first guard denial. Original01's trace did not expose its primary error; preserve
that distinction. No claim that correcting this one denial completes qualification.

The exact8,816B configuration SHA253bf872… and5,838B sealed freeze SHA18180b07…
were committed at `44f1717e53aeefcf02a77949dc71d5c0c6360391` before execution.
Independent metadata review verifies44 source/input/acceptance pins, five controls
and34 historical capsule leaves. Fresh admission records MemAvailable3,486,789,632B,
/tmp free3,621,011,456B and project free99,123,531,776B against unchanged2GiB/
256MiB/4GiB floors. Seventy-nine original01 artifacts were rechecked exactly.
These are dated admission observations, not future resource guarantees.

The frozen independent acceptance auditor returns exit1 normally in0.053527704s
(terminal `a23d4b`) and publishes FAIL: `Normal external transport exit required`.
Its617B publication SHA884f63d0… matches stdout. It refuses **before** post-stage
byte checks. This is neither a passing failure audit nor post-qualification byte
acceptance; `baseline-after.json` remains absent. The earlier dated current-byte
audit02 is retained separately and does not establish bytes after this failed run.
The failure publication retains its existing v1 diagnostic schema; no successful
v2 qualification publication exists.

The supervisor reports three tracked PID/start identities, no matching survivors,
and sampled peak RSS284,901,376B. Independent `/proc` observation at14:42:33UTC
finds all three identities absent. Parent closure remains5→5. These establish the
reported operational cleanup, not hostile-process containment or hard timing.

[Exact evidence index](puck-cpu-held-qualification-02/evidence-index.json) retains
configuration/freeze, admission, raw invocation/descriptor/dependencies, fresh
source capsule, logs, transport, acceptance-audit CLI/publication, custody and
static diagnosis. [Terminal ledger](puck-cpu-held-qualification-02/observation-ledger.json)
distinguishes normal failure return from accepted qualification. The source
amendment's132 passing checks are [separate authored evidence](puck-cpu-held-qualification-amendment-02.md).

Next: prepare a prospective, separately numbered policy amendment for this observed
optional missing import, with narrow authored regression and independent review.
Keep all other source/data/limits guards, and retain01/02 as consumed. Do not rerun02
or infer permission for03 from this report. Passing held qualification and its
independent byte/cleanup audit still precede the recorded/replayed/exported episode.
All seven release gates remain open; no scientific, model, renderer, artwork,
physical or release authority follows from this failed allocation.
