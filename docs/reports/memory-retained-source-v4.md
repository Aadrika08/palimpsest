# Retained-only source reader evidence

The compact source reader now has a separate retained-only entry point. It binds
the canonical source commit, registration, controls, owner, independently
published raw audit, sealed compact inventory, retained worker bytes and sole
shared SNP through held descriptors. It recomputes the retained trace and source
application/oracle/world/terminal bindings without opening removed raw chunks.
Source raw must be absent; one explicitly named different condition raw owner
may exist. Known completed-condition directory names receive namespace checks
only, not condition-content admission. The old reader still requires exhaustive
raw revalidation. Both pruning and native execution remain disabled.

Observed RED `0d39dcc`: all 24 initial new cases failed at the missing reader.
Implementation checks first exposed the expected prospective producer-pin drift,
then a source terminal reference mismatch (the existing pair contract uses null
for a source's parent run) and noncanonical fixture UUIDs. Corrected those
bindings without changing the existing contracts. A separate invalid-case test
observed namespace access for null case IDs before validation; the wrapper now
validates case and deadline before opening the namespace. Fixture path precedence
errors were corrected before final runs.

Root verification: 270 compact/raw/source/pair/retained tests passed in 116.64 s;
the separate 19 staged-pair tests passed in 5.44 s, for **289 affected checks**.
Independent review reran 77 retained/old-producer tests and two behavior-pin/import
checks. Two additional temporary synthetic adversarial checks rejected a
self-consistently rebound worker/conversion/marker against the independent raw
attestation, and a final-case symlink alias. Import/compile and diff checks pass;
all 18 behavior pins match. Only the prospective producer hash/size changes in
the protocol; its SHA is
`a4e278ab7ec5513ac1d5f2b0dd896f681e984eacea9cbb938862fe7cdd8e7ad9`.

Reviewed producer SHA is
`2604bb0530e676d387991504c28a756e94566bd3fe8a74748f16381ef8807cf7`;
new test SHA is
`d1f806edb33351dc688c928a248af14fb912da0c55339ed0080e77b19677b2ee`.
Testing used pinned Python 3.11.15 / NumPy 2.2.5 and generated temporary evidence
only. The full repository/native suites were excluded from this bounded source
unit; no real model, retained recording, native owner or held-out block was read.

This establishes retained-source consistency. Removed raw recordings remain
pre-prune audit attestations; `raw_replay_performed` is false and every protocol
claim stays false. No actual evidence was pruned or collection admitted. Complete
condition/case close, recurrent-cell replay, reviewed raw-tree pruning,
allocation/namespace admission, native owner/control/cleanup qualification and
marker power-loss persistence remain open. No file or resource allowance grows.
