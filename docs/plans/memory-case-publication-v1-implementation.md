# Retained Memory-Case Publication Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` to implement this plan
> task by task. Steps use checkboxes to distinguish work still required. Use a
> fresh independent reviewer before landing the complete source change.

**Goal:** Publish and read one retained nine-condition case with accepted order
attestation, continuous custody and durable no-replace publication.

**Architecture:** Reuse the retained semantic checks and existing bound-file,
exclusive-write and marker-guard helpers. Keep the filesystem transaction in a
private one-shot capability; default read-only custody remains strict. Both public
routes refuse until the existing qualification and new execution-audit anchors
admit the exact evidence.

**Tech Stack:** Existing Python standard library, Linux file descriptors and
`renameat2(RENAME_NOREPLACE)`, pytest; no new dependency, CLI, launcher or pruning.

**Spec:** [Retained memory-case publication v1](memory-case-publication-v1.md).
This plan is a prospective implementation handoff, not a claim of implemented or
tested publication. Task commits may stay local until the complete source change
passes review; finished work must reach remote main.

## Global constraints

- Ten distinct run IDs; source first, then all nine registered conditions. Reject
  oracle-before-own; do not redefine the study around compatible rows.
- Existing qualification pins and new execution-audit acceptance pins remain
  empty. Authored fixture seams never become accepted scientific evidence.
- At most 418 retained files, exactly 33 directories, three case files sharing
  at most 33,554,432 bytes, at most 454 accepted final entries.
- No `.raw` directory, published replacement, raw/model replay, owner launch or
  pruning. Keep all existing claims false and all historical profiles unchanged.
- Use one finite monotonic deadline; retain primary errors, close every fd and
  preserve partial evidence after any successful output creation.
- Retain the same case inode and file bytes across the sole same-filesystem
  no-replace move, then fsync both parents. No copy or path fallback.

## Review focus

1. A crash after rename but before fsync must not make a discovered marker an
   externally accepted result: Task 3 fault test plus Task 4 reader admission.
2. A successful leader exit with a live descendant must not establish no overlap:
   Task 1 accepted-observer binding and missing/invalid drain-evidence tests.
3. Final-mode support must not silently loosen a staged consumer: Task 2 paired
   staged/final alias, `.raw`, namespace and mutation regressions.
4. Caller dictionary mutation, PID reuse and mixed clock domains must not change
   an admitted result: Task 1 copy/type/identity tests and Task 3 held-input tests.
5. Failure in validation or teardown must not hide the original failure, leak fds
   or create a success descriptor: Task 3 fault matrix, repeated on tmpfs.

## Task 1: Accepted order-attestation validation

**Files:** Create `scripts/memory_family_case_publication_v1.py` and
`scripts/memory_case_execution_pins_v1.py`, with tests in
`tests/test_memory_family_case_publication_v1.py`. Extend the authored fixture
builders in `tests/test_memory_family_retained_case_v1.py` only where useful;
reuse their small ten-owner retained tree. Do not change the real producer or
launch a process to masquerade as scientific evidence.

**Interfaces:** Add `validate_execution_audit(audit, *, case_slot, source_commit,
condition_commits, contracts, control_payloads, publication_protocol_sha256)`.
`contracts` maps `source` and each condition to validated terminal exports;
`control_payloads` maps their control descriptor paths to already-held bytes.
Return a deep-copied validated audit. The function requires the acceptance pin
before interpreting protected control payloads; it does not read files or grant
custody. Add `ACCEPTED_EXECUTION_AUDIT_SHA256 = frozenset()` in the separate pin
module and import it for the private pin check. Keep the pin module outside the
audit's subject/source-profile closure to avoid self-reference, just as existing
qualification admission does. Existing qualification admission remains separate.

- [ ] Write `test_empty_execution_trust_refuses_before_control_access`: a mapping
  that fails on access is never touched and an empty anchor raises
  `PermissionError`. Add an authored accepted-seam test asserting source plus the
  nine conditions in registered order and unchanged all-false claims.
- [ ] Run `scripts/run_tests.sh -- tests/test_memory_family_case_publication_v1.py`
  and confirm the new behavior is absent before implementing it.
- [ ] Implement the spec's exact audit/supervisor/cleanup shapes, canonical
  descriptors, copy-on-entry, identity/clock conversion and all binding checks.
  Require accepted observer identity, not merely sorted timestamps.
- [ ] Add parameterized rejection tests for missing/duplicate/extra owners,
  changed run/job/registration/commit/observer, old supervisor/cleanup schemas,
  bool-as-int, reused PID/start identity, mixed boot/namespace, wrong tick rate,
  `pid != pgid`, time reversal/overlap, incomplete drain, nonzero return and own-after-oracle.
  Positive PID reuse uses a new starttime; adjacent intervals may share an endpoint.
- [ ] Run the module tests to zero failures; commit the bounded validator with
  its fixture evidence. No accepted audit is added to the anchor.

## Task 2: Shared staged/final semantics under explicit custody

**Files:** Modify `scripts/memory_family_retained_case_v1.py`,
`scripts/memory_family_retained_condition_v1.py` and private helpers in
`scripts/memory_family_producer_v4.py`, `scripts/memory_family_condition_seal_v4.py`
and `scripts/memory_family_oracle_admission_v4.py` that hardcode `.pending`.
Reuse `scripts/memory_family_compact_v4.py::bound_payload`'s existing explicit
`staged` argument. Test the retained source, condition and case modules and
`tests/test_memory_family_case_publication_v1.py`.

**Interfaces:** Keep all existing public staged signatures and return semantics.
Extract a private `_read_retained_case(..., location, case_files, deadline)` core
with the staged reader's input arguments; `location` is exactly `staged` or
`published`, and `case_files` is the expected root-file descriptor mapping (empty
for the current staged API, exactly the three files for published mode). Its
result is the existing retained result, with no mutation capability. Thread the
explicit location through the private source/condition/pair helpers. Never use
filesystem existence to choose the location.

- [ ] Write a paired fixture test: the same small retained evidence at a final
  location is read without staging copies or symlinks, and the staged API still
  rejects a final alias. Check equal derived cells/retained identity and all-false
  claims. Use explicit authored expected case-file descriptors for this private
  core; they do not test public marker admission yet.
- [ ] Run the targeted retained modules and confirm final-path behavior fails.
- [ ] Extract the semantic core and thread the private location through all
  source/condition binding, inventory, namespace and prior-own readers. Preserve
  check-exit behavior, primary exceptions, qualification admission before protected
  reads and exact staged/public signatures. Census accepts only the explicitly
  declared case files in final mode.
- [ ] Add paired staged/final tests for `.raw` (including empty), alias, extra
  root file, source/condition substitution, symlink/hardlink, history mutation,
  late failure and deadline expiry. No raw/model loader may run; fd count returns
  to baseline on success and exceptions.
- [ ] Run affected retained/source/seal/pair/custody tests to zero failures and
  commit the shared read-only core. Do not expose a public unbound final reader.

## Task 3: Case publication capability and public writer

**Files:** Create `scripts/memory_family_case_custody_v1.py` and
`tests/test_memory_family_case_custody_v1.py`; complete the writer in
`scripts/memory_family_case_publication_v1.py`. Reuse low-level helpers from
producer/condition-seal/custody modules; avoid weakening their default contracts.

**Interfaces:** A private `_CasePublication` context accepts `evidence_root`,
`case_id`, the complete expected file/dependency descriptors and `deadline`.
It exposes `recheck()`, `write_case_files(payloads)` and `publish()` only to the
writer. `payloads` has exactly manifest/close/commit canonical bytes; the
capability owns the temporary marker name. `publish()` performs the one allowed
edge move and both parent fsyncs. Expose the spec's `publish_retained_case(...)`
and `CasePublicationIndeterminate` from the public module. Return exactly
`case_commit`, `retained`, `order_evidence`; `retained` is the derived reader result
and `order_evidence` is `accepted-supervisor-attestation`.

- [ ] Write a real-filesystem test proving same case/file inodes and bytes at the
  final path, staged absence, exactly three new files, correct binding chain and
  no success before both parent fsyncs and teardown. Initially it must fail for
  missing publication behavior.
- [ ] Derive and hold the complete internal/external/source/profile/qualification
  dependency closure before running Task 2 semantics. Keep these independent
  holds through the entire write/move. Existing nested read-only contexts finish
  before mutation; the separate capability remains active. Do not reopen inputs
  after proof or transfer authority via a returned summary.
- [ ] Implement the exact marker-last sequence, bounded exclusive writes,
  readback/identity checks, Linux no-replace marker and case moves and same-device
  rejection. Expected directory metadata changes are limited to the authorized
  transitions; retained leaves and unrelated directories keep full checks.
- [ ] Test exact aggregate byte/entry boundaries (including short cases), missing
  parents, cross-device refusal, existing final collisions and a destination
  introduced just before the real syscall. The competing directory survives.
- [ ] Inject write, short-write, file-fsync, marker-rename, case-rename,
  parent-fsync, recheck, quarantine and close faults. Assert precreation refusal
  has no publisher writes; later failures preserve evidence, report indeterminate
  state with primary error, leak no descriptors and return no marker descriptor.
  Test hostile retained-file and directory mutation across every transition.
- [ ] Run new custody/publication tests and all unchanged read-only custody
  regressions on Btrfs and tmpfs in quiet windows. Commit only passing source.

## Task 4: Final reader, prospective profile and main delivery

**Files:** Complete `scripts/memory_family_case_publication_v1.py`; add the three
prospective protocol files named in the spec and
`tests/test_memory_case_publication_profile_v1.py`. Update current profile pointers
in `scripts/memory_family_compact_v4.py`,
`scripts/memory_family_condition_seal_v4.py` and
`scripts/memory_condition_replay_admission_v1.py`. Use
`tests/test_memory_retained_condition_profile_v1.py` as the preservation-test
pattern. Update `docs/progress.md`, the completion plan and a focused source
report. Existing pinned protocol files must stay byte-for-byte unchanged.

**Interfaces:** Expose the spec's `read_retained_published_case(...)` with the
same three result keys as the publisher. Use the expected `case_commit` input;
never derive it from the candidate marker. Both functions require an accepted
audit and all original qualification pins before accessing protected inputs.

- [ ] Write a public round-trip test through the real writer and final reader
  with explicit authored trust seams. It must fail until the final public reader
  is implemented. Test unregistered/discovered markers, revoked pins and a
  marker left by an indeterminate publisher: none is automatically accepted.
- [ ] Implement marker/close/manifest canonical comparison, independent semantic
  recomputation and complete final inventory/budget/order validation under custody.
  Add malformed/duplicate-key JSON, marker tampering, cross-case descriptors,
  leftover temp/quarantine/staging alias and input-mutation regressions.
- [ ] Create the prospective profiles, refreshing source closure only after the
  implementation is stable. Check old profile bytes/pins and all copied
  scientific/order/schema/storage/claim values. Keep both real acceptance anchors
  empty and the pruning stub refusing. Test that adding an audit acceptance entry
  never requires changing the audit subject's source digest; the separate pin
  module must not enter that digest closure. Do not create a qualification receipt.
- [ ] Run affected tests, historical-profile tests and documentation checks;
  perform an independent whole-diff review and resolve supported findings. Record
  exact commands, counts, failures, filesystem and candidate SHA.
- [ ] Push the source branch, require all complete hosted canonical/preflight/
  frontend checks, then merge without bypass or force. Verify remote main contains
  the candidate and its tested source tree; publish a truthful source report.
  Real observer qualification, order-policy resolution, pruning and scientific
  execution remain separate blockers. Do not mark the whole project complete.
