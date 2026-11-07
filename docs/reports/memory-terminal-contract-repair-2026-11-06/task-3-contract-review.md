# Task 3 contract planfix review

**Verdict: FAIL — one bounded contract freeze is required before Task3a fixture/test implementation.**

Scope: the uncommitted changes to `docs/plans/memory-terminal-vnext-implementation.md` against `be2fbf4`, limited to Task3a/3b, their input contract, and dependency order. Existing Task1/2a acceptance was not reopened. This was source/document inspection only; no tests, imports, native/model/raw/SNP/protected reads, dependency changes, CI, or code edits were performed.

## Required fix

**Freeze the minimal manifest semantic projection before implementing Task3a tests.** Plan lines182–193 currently require categories (“run/case/condition/source lineage”, “configured CPU FLYNN/device/eye state”, “counters/final state”) rather than an exact set of required field paths, types, allowed values, and cross-input equalities. Binding the whole extensible manifest to a descriptor does not establish which of its claims must be independently checked. Two implementations could satisfy this paragraph while disagreeing on whether a missing or contradictory admission-relevant field is acceptable.

Add a bounded table or equivalent explicit contract for the required projection, while retaining an extensible whole manifest. It must state the concrete keys and checks for owner/case/condition/source lineage, closed status and format, configured controller/device/eyes, original scenario/case configuration, recording ceiling, all three recording counters, terminal world/phase/tick/outcome, and the existing Task2a mode/hash plus new Context descriptor. Explicitly identify which old semantic checks are retained and how condition identity is established without the old admission envelope; do not require or synthesize that envelope.

The relevant existing checks are concrete: `memory_family_oracle_admission_v3.py:160–171` checks `controller`, `requested_device`, `teacher_privileged`, `texture`, `scenario`, `seed`, `memory_case`, `memory_case_sha256`, `acquisition_protocol_sha256`, and `recording_max_bytes`; its old envelope requirement must not be carried over as authority. `memory_family_raw_audit_v4.py:405–456` binds report/manifest terminal state and source lineage. `records.py:331` and `443–446` establish the exact `recorded_ticks`, `recorded_chunks`, and `recorded_events` counts. The successor projection must make the zero/positive/full relationships explicit without relaxing the preserved normal/full obligations. Derive missing-field, contradictory-field, and bool-as-integer fixture refusals from this frozen projection rather than letting fixtures define it.

## Accepted aspects of this repair

- The proposed implementation order `1→2a→3a→4→5→6→3b→2b→7` removes the immediate public producer cycle. Task3a produces only a conditional pure `TerminalProof`; Task3b waits for the real Task6 holder and explicitly requires a separately frozen pre-audit registration without output/self edges. Deferring that public contract is acceptable because this repair does not authorize Task3b implementation.
- Raw has six exact keys, with five exact descriptor roles. `raw.job` is a descriptor equal to `descriptors.job`; actual job-body/Context correspondence remains a Task3b held-byte obligation. This does not introduce a fake partial owner job or claim that a job digest proves its absent body.
- The specified RunWriter manifest/event serialization matches `records.py:22–23,198–199,218`. Context/report canonical serialization is distinct. The plan correctly limits those comparisons to deterministic representations and requires Task3b to compare physical originals. Supplied source application/events/nonempty rows remain conditional premises; their hash/prefix checks are not SNP custody or native-placement qualification.
- The top-level gate and Task3b’s explicit restriction on Tasks4/5/6 prevent authored proofs/private fixture receipts from granting actual publication acceptance. No downstream bypass is authorized by this diff. Task5 already keeps public actual entry refused; Task6 actual acceptance sets remain empty.
- The diff leaves the original normal/full terminal requirements, zero-row restrictions, nonempty source requirement, scientific constants, and existing byte/resource caps intact. Public APIs are absent in3a, not stubbed or represented as successful receipt flags.

## Local wording repair

Make the Task3a checklist agree with the split: lines197 and199 still say to reuse raw custody/inventory helpers and run “exact inventory/custody” negatives, whereas lines211–212 assign those properties to3b. Specify pure byte/shape/count/cap refusal tests in3a and held-inventory/custody/publication tests in3b. Likewise, use conditional supplied-source wording for3a’s “authenticated acquired state”/“source SNP ... bound” assertions. The surrounding text already denies physical authority, so this is not a separate discovered bypass, but the actor should not be directed to implement unavailable custody APIs or claim those tests passed.

After the manifest projection is frozen and the checklist is aligned, this bounded planfix can be rereviewed for Task3a implementation readiness. No broader plan, actual qualification, or adoption approval follows from this review.
