# Fresh restores recorded; independent readout stopped

4 October 2026. **Both registered five-tick restores completed, but the final
independent readout stopped before pair comparison.** No native retry or fresh
qualification was run. A post-stop readout-validator repair is software evidence;
it cannot retroactively qualify this failed invocation.

[Contract](../plans/memory-restore-study-v2.md),
[prospective registration](memory-restore-study-v2-evidence/registration.json),
[exclusive invocation](memory-restore-study-v2-evidence/native-launch.json),
[original close receipt](memory-restore-study-v2-evidence/scientific-close.json),
[phase dispositions](memory-restore-study-v2-evidence/disposition.json).

## Preparation and software admission

Parent `38093ad`, draft PR #70; branch `research/memory-restore-study-v2`. Contract
commit `9bebb5c` precedes implementation `a61a85f`; registration commit `10190ec`
precedes the single invocation. The existing scientific driver, schema, profile
and normalization were reused unchanged. Each phase has a new output, ignored
log workspace and exclusive marker; the previous consumed marker is preserved.

Temporary-Git tests ran the new launchers and the production child driver's clean
admission checks. Source/native preparation was substituted and exited before
any output allocation. Both tests also committed documentary logs and verified a
second invocation was refused by the exclusive marker, independently of Git
cleanliness or existing output. The copied old wrappers failed these tests, then
the study-specific wrappers passed. [RED](memory-restore-study-v2-evidence/launcher-red.log),
[GREEN](memory-restore-study-v2-evidence/launcher-green.log).

Before registration, 20 focused tests passed. The full local suite passed
**935 /skipped24**, with39 warnings, in102.01 s.
[Full log](memory-restore-study-v2-evidence/full-suite.log). These fixtures started
no native owner and are not scientific qualification evidence. CI was excluded.

## The bounded native attempt

The fixed .25 m profile and audited prior south-prefix SNP were prospectively
bound, with all339 previous recovery-study files,24 historical abort files and25
previous diagnostic evidence files checked unchanged. The source SNP SHA256
remained `c839fae1fe3d981cf4b7073970f7eb06d5738f009d6cb23f249408fd227cf6bf`;
it was copied byte-for-byte into this study's stage. Registration measured
41,036,386,304 free bytes, above the inherited10 GiB admission requirement.

Two owners ran sequentially, each with exactly five continuation ticks. Their
per-owner raw audits passed during execution; initial invariants were preserved.
The execution receipt records both exact owner identities as already exited
during same-namespace cleanup. The child exited1 with
`independent-readout-stop` after58.9827 s total, including0.00189 s readout.
The unchanged900 s allocation was not exhausted or extended.
[Invocation log](memory-restore-study-v2-evidence/native-invocation.log).

| Restore | Run ID | Owner supervision | Recorded post-state digest |
|---|---|---:|---|
| 1 | `a622e7d821954286a7595b846baae849` | 30.253 s | `4645bee796915201c043098f6e00fb17f68fa805e4fa74ab597b23e979f2947e` |
| 2 | `b14d9fc28bef43cbae0a5a417f898ebc` | 25.773 s | `37b47825b374b8dfc2992ac947391e04737a78e63066dfb4b5f25c727719c1e9` |

The two per-owner trace digests match:
`794593e481fe2cca88fa49f59a491e33597f0bf2f9713b3496a68ad3d99f3249`.
Worker receipts report matching component hashes for application, environment,
identity, integration, integration_enum, observation, policy, RNG, schema_version
and teacher. Their `native_data` and `native_sha256` component hashes differ.
These are recorded receipt comparisons, not a completed independent audit of the
retained post-state payloads. The final pair equality field was never computed;
no named native-field comparison exists and no causal explanation is established.

## Exact readout failure and delivery repair

The final auditor called `validate_job` on an allocated job whose output already
existed. That function was a worker-launch validator: its `safe_output` guard
correctly requires an absent output before starting a worker. The final auditor
therefore raised:

```text
ValueError: Output must be absent; existing evidence is immutable
```

This is a readout tooling defect, separate from the restore state discrepancy.
It occurred before final owner/raw/post-state re-audit, source/history rechecks,
artifact indexing or state/native-field comparison. No later analysis is
substituted for the failed scientific readout or presented as an extended clock.

The post-stop fix adds an explicit private `read_only=True` job-validation mode
for the auditor. It permits inspection of existing output while preserving path,
source-overlap, spec, geometry and lineage checks. Default worker admission still
refuses existing output. No job fields, CLI or scientific normalization changed.
A realistic allocated-job fixture reproduced the same exception without mocking
the validator. After the fix, focused tests passed78, including refusal of worker
retry and malformed audit jobs. The final local suite passed **939 tests, with24
skipped and39 warnings**, in84.92 s. [Regression RED](memory-restore-study-v2-evidence/readout-red.log),
[GREEN](memory-restore-study-v2-evidence/readout-green.log),
[delivery full suite](memory-restore-study-v2-evidence/delivery-full-suite.log).
The repaired implementation has not run this study again.

Exact executed bytes are retained separately:
[driver](memory-restore-study-v2-evidence/executed-driver.py),
[pilot helper](memory-restore-study-v2-evidence/executed-pilot-driver.py),
[launcher](memory-restore-study-v2-evidence/executed-launcher.py).
Delivery changes cannot change the meaning of the original failed receipt.

## Preservation, limits and next boundary

[Publication integrity](memory-restore-study-v2-evidence/publication-integrity.json)
rechecked all339 prior recovery files,24 historical abort files,25 previous
diagnostic evidence files, the original consumed marker and original source SNP
unchanged. The previous refused output remains absent. Exact compact receipt
copies are checked by checksum. The final scientific artifact index is absent
because readout stopped; the separate
[retained-output inventory](memory-restore-study-v2-evidence/retained-output-inventory.json)
is a post-close documentary manifest, not an independent raw audit or qualification.

Raw SNP/NPZ payloads remain local under the registered
`runs/memory-restore-study-v2-diagnose-20261004T155817Z` directory. Git metadata
are not a self-contained replay bundle. No evidence was deleted or rewritten.

The original six-of-eight prerequisite result remains unchanged. No demonstrated
same-contract state repair exists; qualification and pilot remain unattempted.
The next useful scope is a separately registered **offline exploratory readout of
the retained post-states**, without another native pair, to localize the native
payload difference. That later study must not relabel this failed close or the
prior prerequisite gate. Navigation, puck, held-out and physical gates remain open.

Repository-local author Aadrika Maurya <aadrikamaurya@gmail.com>, publication as
Aadrika08. Draft PR stacked on #70 against `research/memory-restore-diagnostic`.
Main unchanged; no merge or CI.
