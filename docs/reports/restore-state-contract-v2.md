# Restore comparison v2 candidate prepared; qualification remains open

7 October 2026. The [prospective contract proposal](../plans/restore-state-contract-v2.md)
and opt-in software comparison are implemented on `research/restore-state-contract-v2`,
stacked on PR #73. This delivery contains synthetic software validation only;
no retained-pair readout, native qualification or physical work was invoked.

The candidate verifies raw native SHA256 first, preserves the existing application
and destination-receipt normalization, and reuses the exact round-trip/reversible
timer mapping from the attribution helper. It zeros precisely 15 mapped duration
fields, **120 bytes per side**, on comparison copies only. Its derived native
checksum matches those comparison bytes; raw hashes and durations remain separately
reported. Stored snapshots and their raw/native/full-state integrity hashes never
change. Call counts and every byte outside those intervals remain exact.

The existing [72-byte attribution](memory-native-byte-attribution.md) motivates
this proposal; it is not re-scored or promoted as qualification under v2. MuJoCo
documents durations as accumulated profiling information supplied by a timing
callback. This classification is the candidate contract's declared assumption,
not a guarantee for arbitrary custom controllers that might read those statistics.
[MuJoCo 3.3.6 diagnostics](https://mujoco.readthedocs.io/en/3.3.6/programming/simulation.html#diagnostics).

The existing offline auditor selects the candidate only when registration names
`restore-reproducibility-v2-candidate`. It keeps `comparison` as the legacy exact
result and adds `candidate_comparison`. The receipt reports candidate equality
and contract ID separately; `native_prerequisites_passed` remains false and
qualification claims remain empty. Old no-kind and attribution registrations
retain their previous paths. Workers, scientific protocol hashes and release
gates are unchanged. No new launcher or generic study framework was added.

Seven new synthetic cases failed before implementation and passed afterward:
duration-only equality; included timer-count, native-qpos and application
differences; refusal of raw-checksum and destination-receipt violations; and
the audited synthetic SNP pair exposing raw inequality alongside candidate
equality without changing the old close receipt. Original input digests remain
unchanged. The relevant combined suite passed **45 in 2.53 s**.
[RED](restore-state-contract-v2-evidence/red.log),
[GREEN](restore-state-contract-v2-evidence/green.log).

The full local suite passed **960**, with **24 skipped** and 39 warnings, in
97.28 s. Full-suite isolated MuJoCo step/forward tests are software validation,
not a new native study or hardware evidence. CI is excluded.
[Full software log](restore-state-contract-v2-evidence/full-suite.log).

[Documentary preservation check](restore-state-contract-v2-evidence/preservation-check.json)
rehashes all 473 previously registered evidence files, 17 unchanged bound inputs
and seven attribution publication copies. The existing offline auditor is the
declared delivery-code change; its previous executed bytes remain archived.
The old invocation marker remains intact. This is checksum verification only,
not a new scientific readout or retained-state decode.

The proposed activation boundary requires a separately frozen, prospectively
registered qualification study naming this contract, host/runtime/model/profile,
source snapshots, controls, owners, deadlines and storage limits. Fresh raw and
post-state audits must establish exact non-timing traces and candidate equality,
while reporting original raw inequality and profiling diagnostics. Historical
failed gates cannot inherit success. This study has not run here.

The candidate is intentionally version-specific to MuJoCo 3.3.6 and fails closed
on unsupported native bytes, checksum, round trip, field layout or probes. It
does not relax warning/solver statistics, padding, opaque tails or numeric values
outside timer durations, and does not establish broader restore reproducibility.
Memory benefit/pilot, navigation R3, puck, held-out and hardware/operator claims
remain separate.

Repo-local author Aadrika Maurya <aadrikamaurya@gmail.com>; publication as Aadrika08.
Main unchanged; all prior reports, native evidence and consumed markers preserved.

[Independent final review](restore-state-contract-v2-evidence/final-review.md)
found no Critical, Important or Minor issues and independently passed 14 selected
synthetic tests in 2.33 s. The review accepts publication within this prospective
software scope; its declined judgments and executor rulings are recorded. Fresh
qualification remains unattempted.
