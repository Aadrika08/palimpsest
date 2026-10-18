# Full-model cell qualification: attempt 01 failed at runtime admission

The one registered invocation on source `59270515f93a9c93820cb105fb5dec82e9744d4a`
failed before launching the numerical worker. The runtime descriptor incorrectly
registered the interpreter as an unknown-size file with a 1 MiB maximum. The
actual original interpreter is **21,662,864 bytes**, regular and single-link.
Its SHA256 still matches the campaign's original
`572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a`.
This attempted full-model qualification remains unproven and its allocation is
consumed. No corrective invocation occurred; unused cell/time capacity grants
no second attempt.

The [lossless evidence index](memory-full-cell-qualification-v4-attempt-01-evidence/index.json)
retains all seven original output files (2,517 bytes), both failure markers,
the original supervisor record and the byte-identical
[execution freeze](memory-full-cell-qualification-v4-attempt-01-evidence/execution-freeze.json).
Freeze SHA256 is
`9bba5a4a4fdd980ab2022d7ef0813aa4b2fa6a2c26c6ce86fead7110ad624c82`.
Copies contain no checkpoint, graph, raw camera/encoded rows or SNP bytes.

## Observed execution and independent audit

- External invocation exited **1**. The terminal handle was observed within a
  conservative **31.003-second wall observation upper bound**; this includes
  the delay before polling and is not measured process runtime.
- The original supervisor recorded **1.605572 seconds** from reservation through
  final workload observation, failed status, exit 1 and no matching survivors.
  Its sampled peak was **54,091,776 bytes**. This is sampled operational evidence,
  not a hard memory or execution-time bound.
- Parent custody stopped at the runtime leaf before `_run_worker`. There is no
  worker-started record, worker result, close or passing terminal marker. There
  were **zero model inference calls, native owners and physics steps**; no SNP
  decoding or family/held-out study occurred.
- The earlier source, asset, metadata and raw roles precede runtime admission;
  their files could already have been opened and hashed. Failure before numerical
  work must not be described as failure before protected-input access.
- Independent metadata checks of all **226 registered descriptors** found only
  the interpreter's size/cap mismatch. A separately bounded, read-only runtime
  hash (32 MiB / 60 seconds maximum) checked all 21,662,864 bytes in 0.026286
  seconds and matched the original SHA with stable file identities. This audit
  read no raw/model/SNP/ZIP content and ran no numerical qualification.
- Cleanup evidence comes from the recorded original execution namespace and
  terminal external handle. A later command's PID scan is not evidence about
  the former namespace.

## Source verification

The inherited compact/raw/source/pair/retained/staged/cell/Flynn slice passed
328 checks without skips. The current qualification/custody slice passed 89
checks in 1.92 seconds, independently repeated as 89 in 1.95 seconds: **417
affected source checks** covered across the runs. Upstream/Torch tests reported
44 existing tensor-copy, CSR-beta and TF32-deprecation warnings. The full
repository, native and browser suites were not run for this source unit.

Independent source/freeze review approved exact `5927051` and the freeze above
before invocation. It verified the process/output timing and directory custody,
bounded descriptors, pinned public timeout executable, source closure and cell
arithmetic. Numerical/metadata source review separately checked the three fixed
traces, seed 400, action/hidden comparisons and four prescribed negatives. Source
review did not measure the real model or establish the interpreter's file size.

## Prospective decision

Prepare a separately numbered amendment that registers the interpreter's exact
21,662,864-byte size and unchanged original SHA. Keep the 1 MiB unknown-metadata
cap, all original model/input identities, 737 positive cells, four fixed negatives,
1,470 maximum calls and 600/650/660-second limits. Preserve this attempt and its
freeze unchanged. The new source and freeze require independent review and
explicit approval before another qualification invocation.

Complete the condition/case and puck source paths where their prerequisites
permit. No pruning, collection, fitting, held-out opening or scientific/capability
gate is granted by this failure or its source tests. All seven simulation release
gates remain open; CI and physical rover work remain excluded.
