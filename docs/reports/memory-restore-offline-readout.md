# Retained restores audited offline; full native mismatch remains

4 October 2026. The single prospectively registered offline readout completed in
**3.423631 s**, independently auditing both retained raw recordings and post-state
payloads. Their control traces match; their full normalized states do not.
Each native payload contains 458,761 bytes, with **72 differing bytes**. No new
native owner or physics step was started. Qualification claims remain empty.

[Contract](../plans/memory-restore-offline-readout.md),
[registration](memory-restore-offline-readout-evidence/registration.json),
[exclusive marker](memory-restore-offline-readout-evidence/offline-launched.json),
[original offline close](memory-restore-offline-readout-evidence/execution.json),
[complete analysis](memory-restore-offline-readout-evidence/analysis.json),
[invocation result](memory-restore-offline-readout-evidence/invocation-result.json).

## What was implemented and executed

Parent `49f755e`, draft PR #71; branch `research/memory-restore-offline-readout`.
Contract commit `2bca4e7` precedes implementation `971567c`; registration commit
`0259763` precedes the invocation. Python 3.11.15, NumPy 2.2.5 and MuJoCo 3.3.6
were frozen separately for the offline auditor. The raw workers retain their
original source identities. Registration measured 40,824,131,584 free bytes,
above the 10 GiB admission requirement.

The study-specific driver reused read-only allocated-job validation, raw packet
reconstruction, retained post-state checksum/component audits, and the unchanged
trace and full-state comparison rules. It checked exactly two allocated owners,
their original completed supervision receipts, five controls each, and historical
same-namespace cleanup linkage. It made no current PID probe and performed no
neural inference, native launch, reset, forward or physics step. Offline native
deserialization was allowed within the single registered invocation.

The fixed 300 s phase included admission, both audits, comparison, input rechecks,
artifact indexing and close; an external 290 s timeout provided TERM/KILL bounds.
No second invocation occurred. The consumed marker remains in place.
[Invocation log](memory-restore-offline-readout-evidence/readout.log).

## Measured results from the completed readout

| Restore | Historical run ID | Raw controls | Raw and retained post-state audit |
|---|---|---:|---|
| 1 | `a622e7d821954286a7595b846baae849` | 5 | Passed |
| 2 | `b14d9fc28bef43cbae0a5a417f898ebc` | 5 | Passed |

Both initial invariants were preserved. The two trace digests match:
`794593e481fe2cca88fa49f59a491e33597f0bf2f9713b3496a68ad3d99f3249`.
Every recorded non-timing control field was compared under the existing rule.
This is two independent restore attempts with the same source, profile and seed;
their ten correlated control rows are not ten independent experimental samples.
Owner exit information is historical cleanup evidence, not a current liveness
claim.

Full normalized state digests remain different:

| Restore | Full post-state digest |
|---|---|
| 1 | `4645bee796915201c043098f6e00fb17f68fa805e4fa74ab597b23e979f2947e` |
| 2 | `37b47825b374b8dfc2992ac947391e04737a78e63066dfb4b5f25c727719c1e9` |

The only differing complete-state components are `native_data` and
`native_sha256`. Application, environment, identity, integration,
integration_enum, observation, policy, RNG, schema_version and teacher component
hashes match. No field was dropped from this full-state comparison.

The native payload SHA256 values are
`e4b7499d44b990c16a8b606d64e29ea21907e0efce9bc8bbc0e2987828ab5ae8`
and `c6a2fa9f6c67023ce27ed21df46cce37352556981c91c75c7792292f585faca8`.
The first differing byte offsets are 279971–279976, 279987–279992 and
280020–280023. These are a bounded preview, not all 72 offsets.

The **executed, unfiltered decoder** inventoried 207 named fields per side and
reported no omissions. Its original result is retained unchanged:

| Decoder path | Different elements | Maximum absolute difference | Interpretation limit |
|---|---:|---:|---|
| `timer.duration` | 14 / 15 | 0.000491245999988621 | Timing-statistic difference; byte attribution remains unproved |
| `efc_AR_rowadr` | 242 / 284 | 2,606,379,383 | Unfiltered exposed-view difference; not established captured-state evidence |
| `efc_AR_rownnz` | 263 / 284 | 2,867,062,592 | Unfiltered exposed-view difference; not established captured-state evidence |

The other inventoried named-field hashes match under that executed decoder.
Named-field equality is not a complete interpretation of the serialized payload.
There was no serialized-byte-to-field mapping, and no causal claim that timers
alone account for all 72 differing bytes.

## Post-close source interpretation and decoder repair

After the offline close, source inspection showed that MuJoCo 3.3.6 serializes
timer statistics and conditionally serializes dual-solver arena arrays. Its
decoder sets absent arena pointers to null, while the Python arena getter builds
an array view from the field pointer and shape. This makes array population
eligibility relevant to interpreting named fields.
[Serializer and deserializer](https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.6/python/mujoco/structs_wrappers.cc),
[arena getter](https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.6/python/mujoco/structs.cc),
[array construction](https://raw.githubusercontent.com/google-deepmind/mujoco/3.3.6/python/mujoco/structs.h).

The already recorded scalar hashes for both sides match `state_digest(0)` for
`nA` and `state_digest(284)` for `nefc`. This is a post-close interpretation of
existing result hashes, not a new state measurement. The actual model's solver
population conditions were not independently collected in this study, so these
hashes alone do not prove the status of every arena field.

A separate synthetic software fixture created an empty MuJoCo model and set
artificial `nefc=1` metadata on an unpopulated arena. It took zero physics steps
and used no retained study snapshot. The binding exposed NumPy-owned arrays;
the old decoder incorrectly included them as native-state evidence. The
regression failed before the fix, then passed when the decoder omitted owned
NumPy arrays and reported their field, shape, dtype and omission reason.
[RED](memory-restore-offline-readout-evidence/decoder-red.log),
[GREEN](memory-restore-offline-readout-evidence/decoder-green.log).

This repair changes future named-field inspection only. Full-state bytes,
digests, scientific normalization and qualification gates are unchanged. The
fixed decoder **has not decoded the retained pair again**. The original 207-field
analysis is not retroactively filtered or replaced. The AR array differences
therefore remain suspect decoder-view observations, rather than proven native
state differences. Timers are a source-supported candidate for the serialized
mismatch; identifying all 72 bytes still requires a separately scoped study.

Exact executed code is preserved separately from delivery code:
[offline driver](memory-restore-offline-readout-evidence/executed-offline-driver.py),
[original diagnostic helper](memory-restore-offline-readout-evidence/executed-diagnostic-driver.py),
[pilot helper](memory-restore-offline-readout-evidence/executed-pilot-driver.py),
[launcher](memory-restore-offline-readout-evidence/execute-readout.py).

## Validation and evidence preservation

Before invocation, focused software tests passed 34 and the full local suite
passed **949**, with **24 skipped** and 39 warnings, in 86.19 s. Tests cover
historical cleanup linkage, exactly-two/five-row requirements, corrupt or missing
post-states, changed inventories, failed close/deadline invalidation, and clean
launcher admission with an exclusive marker. The real child admission fixture
substitutes the analysis and exits before reading study inputs.
[Focused log](memory-restore-offline-readout-evidence/focused-green.log),
[pre-invocation full suite](memory-restore-offline-readout-evidence/full-suite.log).

After the decoder repair, 35 focused software tests passed in 0.65 s. The final
full local suite passed **950**, with **24 skipped** and 39 warnings, in 87.19 s.
[Delivery full suite](memory-restore-offline-readout-evidence/delivery-full-suite.log).
These tests start no native worker and are software evidence only. CI is excluded.

The registered inventories remain unchanged: 339 original recovery files,
24 historical abort files, 25 previous diagnostic evidence files, 30 retained v2
native files and 26 published v2 evidence files. All 13 bound execution inputs
were checked again during documentary publication; the executed diagnostic
helper was verified using its separately preserved pre-repair bytes.
[Publication integrity](memory-restore-offline-readout-evidence/publication-integrity.json).

The original v2 `independent-readout-stop`, the earlier refused diagnostic,
exclusive markers and source SNP are unchanged. This successful separate offline
audit does not promote either failed close or change the original six-of-eight
prerequisite disposition. Raw SNP/NPZ payloads stay local at the registered paths;
the Git evidence is not a self-contained replay bundle.

## What remains and where to stop

Completed here: registered offline tooling, one retained-pair audit, full-state
localization, bounded original named-field results, a post-close decoder
regression/fix and documentary publication. No state repair, normalization
amendment, native retry, fresh qualification or paired pilot occurred.

The next useful bounded scope is byte-to-field attribution together with
verification of native field population eligibility. Only after that evidence
could a separate prospective scientific contract proposal distinguish behavioral
restore state from nonbehavioral statistics. This report does not authorize or
perform that amendment. Fresh qualification, memory benefit/pilot, navigation R3,
puck, held-out and physical/operator gates remain open.

Repo-local author Aadrika Maurya <aadrikamaurya@gmail.com>; publication as Aadrika08.
Draft PR stacked on #71 against `research/memory-restore-study-v2`. Main unchanged;
no merge or CI. Account quota telemetry was unavailable.
