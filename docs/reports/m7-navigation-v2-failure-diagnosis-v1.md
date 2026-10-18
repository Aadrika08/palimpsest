# M7 navigation-v2 failure diagnosis v1

8 October 2026. The one retained-data invocation allowed by the frozen
[protocol](../plans/m7-navigation-v2-failure-diagnosis-v1.md) failed closed.
It produced no trajectory report and supports no navigation conclusion. The
byte-identical [failure receipt](m7-navigation-v2-failure-diagnosis-v1.json)
records `AttributeError: 'str' object has no attribute 'get'`, with no
qualification claim and `r3_complete: false`.

## Retained execution evidence

The [execution receipt](m7-navigation-v2-failure-diagnosis-v1-execution.json)
records the exact command, exit code and hashes. The invocation used analyzer
commit `2f0a425b7c541b9d972b7a5d8263b2a85f072340` (source SHA-256
`ce0f9e0126ce31a0c356678386f44097cebe0115332e1967e87d4053737e92c9`),
protocol SHA-256
`242fad46433241697bb7d7731e692cd1b42918b3788a8f816c6c8a9e9271b5e3`
and development-index SHA-256
`850c6337e1fa4e2916751a8f02c20dae4a9ba347eb88eb3f17d17cedb065dc71`.
It exited 1 after 2.337815377 seconds. The fresh output contains only the
6,964-byte protocol and 293-byte failure receipt; `report.json` is absent.

Source tracing places the exception after the complete initial ledger hash and
after the first enumerated case's six selected numeric fields were decoded.
That boundary is an inference from the committed call order, rather than a
separately instrumented runtime measurement. No computed values were
published. The path imported neither Torch nor MuJoCo, ran no model or physics,
accessed no held-out scene, and decoded no camera or snapshot payload.

## Root cause and correction

The producer stores `result["outcome"]` as the string returned by
`run_episode`. The analyzer instead called `.get("reason")` on that string.
Its authored fixture had modeled the value as an object, so all pre-run tests
repeated the same incorrect assumption. Commit
`d582eca99a8526c97e7c8d7ac33d44636c32d070` changes the fixture to the producer
schema and reads the string directly. The focused 15-test diagnosis suite and
the existing nine-test development-v2 suite pass after the correction. Those
are synthetic/source-level checks only: the corrected analyzer has not been
run on retained data.

## Decision boundary

The protocol's at-most-once retained invocation is exhausted. This failed run
does not classify the 24 cases, compare the two training arms, explain the
augmented arm's 0/4 results, complete R3, or support capability, topology,
biological, simulator, hardware or release claims. A new attempt requires a
separate prospective amendment with a fresh output, explicit authorization to
consume the retained batch again, and a producer-schema contract test before
execution.
