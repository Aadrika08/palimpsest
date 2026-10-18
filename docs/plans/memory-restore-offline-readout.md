# Registered offline restore readout

Approved by `doit` on 4 October 2026 after the proposed registered offline
analysis of retained post-states. Parent `49f755e`, draft PR #71; branch
`research/memory-restore-offline-readout`. Reuse existing raw and post-state
auditors and offline native-field decoder. Inline implementation, incremental
commits, one final independent review and draft PR stacked on #71. Repo-local
author Aadrika Maurya <aadrikamaurya@gmail.com>; publish as Aadrika08.
Main unchanged; CI excluded. Account quota telemetry unavailable.

## Question and evidence boundary

Can the two retained five-tick v2 restores be independently audited offline, and
which exact state/native fields differ? One pair, same source/profile/seed; the
ten correlated control rows are not ten independent experimental samples.

Preserve v2's `independent-readout-stop` and empty qualification claims. This
readout is a separate exploratory study, not a replacement or extension of the
failed scientific close. No new native owner, policy inference, physics/reset/
forward call, source migration, normalization amendment, state repair, native
retry, qualification, pilot, held-out or physical claim.

## Implementation and registration

Add a study-specific offline driver with a registration-file CLI. Reuse private
`validate_job(read_only=True)`, `audit_run`, `audit_post_state`, `compare_states`
and `compare_native_states`. Do not call native launchers, `audit_owners`,
`owner_exited` or cleanup: their current-process namespace is unrelated to the
recorded owners. Validate prior owner JSON against the original same-namespace
cleanup receipts and report this as historical evidence, not current liveness.

Prospectively commit the contract, implementation and machine registration before
one offline invocation. Bind implementation commit, auditor/dependency hashes,
Python/NumPy/MuJoCo versions, assets/history identities, failed close, exact
source SNP, immutable retained/native and prior evidence inventories, output and
exclusive invocation marker. Source cases and worker provenance retain their
original identities; the offline auditor has its own separately frozen identity.

Use a fresh output and ignored live-log workspace. Keep logs ignored until the
child exits. Refuse dirty checkout, changed inputs, existing output or consumed
marker. Registration and raw snapshots remain immutable. Admission rehearsal
uses a temporary Git/production-child fixture and stops before input analysis.

## One bounded offline analysis

300 s from admission through independent raw/post-state audits, native-field
decoding, input rechecks, indexing and close. External wrapper 290 s, TERM then
KILL after 5 s. No repeated invocation on failure. Use pinned Python and single
CPU thread settings; no rendering or GPU. Maximum new phase output 64 MiB,
individual control/log 1 MiB; snapshots up to the existing 16 MiB input bound.
Require at least 10 GiB free at admission and retain the existing 2 GiB floor and
64 MiB headroom. No evidence deletion or model preparation/download.

Require exactly the two allocated restore jobs, their matching recorded owner
identities/cleanup, original completed supervision receipts, five raw controls
each, preserved initial invariants and audited retained digest-input post-states.
Reject extra/missing allocations, unknown owners, malformed/corrupt input or
source/profile/protocol mismatch. Compare every non-timing control field using
the unchanged trace rule and full normalized state using the unchanged rule.

Publish bounded differing paths, component hashes, byte offsets/counts, named
native-field differences and decoder omissions. Native decoding deserializes
trusted same-version bytes but takes zero physics steps. Named-field equality
or differences are not a complete interpretation of opaque serialized bytes or
a causal proof. Do not discard native bytes or checksum fields to force equality.

## Validation, close and publication

Software fixtures exercise malformed owner/cleanup linkage, exactly-two/five-row
requirements, missing/corrupt post-states, changed input inventories, clean
admission, exclusive invocation marker and deadline/failed-close invalidation.
Use tests that fail then pass for new behavior; run focused and full local suite.
Tests start no native owners. A completed offline readout requires all integrity,
artifact indexing and deadline checks; failed close must clear completion and
qualification claims. Any repair after close cannot change the original result.

After close, copy exact compact receipts, registration, executed code and final
findings into docs; keep SNP/NPZ local. Preserve all prior studies, their logs and
exclusive markers. Documentary publication checks do not add scientific
measurements. One independent whole-branch review, address Important/Critical
issues with software regressions, then push a draft PR against
`research/memory-restore-study-v2`, no merge or CI. Stop after reporting findings;
any scientific-contract amendment or new qualification requires its own scope.
