# Memory family v3 producer contract implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` or `superpowers:executing-plans` to
> implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for
> tracking.

**Goal:** Freeze and verify the smallest version-3 registration, job, owner,
cleanup, and source/`own` close contract without granting or starting native
collection.

**Architecture:** A pure contract module regenerates one complete development
block, binds 1,440 caller-allocated UUIDs and every immutable input, and derives
the exact raw-admission envelope added in PR #99. A read-only close validates two
retained non-executable descriptors, manifest-bound producer identities, normal
supervisor exits and independently recorded owner cleanup, invokes the existing
oracle admission, rechecks a complete input ledger, then writes one exclusive
hash-sealed receipt. The module contains no Engine, model, subprocess, signal, or
owner-launch path.

**Tech stack:** Python standard library, existing `palimpsest.memory`, artifact
readers, family generator/slot builder, PR #99 oracle admission, and pytest.

**Spec:** [`memory-confirmatory-v3-design.md`](memory-confirmatory-v3-design.md)
and [`memory-family-oracle-admission-v3.md`](memory-family-oracle-admission-v3.md).

## Global constraints

- Development split only; exactly one complete block, 48 families, 144 cases,
  144 source slots, and 1,296 nine-condition slots.
- Registration mode is `software-contract-only`; `native_allocation` and
  `held_out_used` remain false and `qualification_claims` remains empty.
- The caller supplies exactly 1,440 canonical, unique UUID hex strings. The
  contract never allocates IDs, discovers donors, launches owners, or chooses a
  block.
- Zero retries, replacement families, fallback profiles, corrective studies,
  or post-result extension.
- Bind the canonical matrix plan, protocol object/hash, source identity/hash,
  both history bundle paths/hashes, namespace inventory,
  output/control/publication roots,
  and the exact producer/family/oracle dependency hashes.
- Validate the selected block's enumerated authored IDs against the supplied
  historical inventory. Inventory completeness is an external prerequisite and
  is not established by this module.
- Freeze the known ceiling: 599,147,937,792 raw bytes, 24,159,191,040 snapshot
  bytes, 4,529,848,320 log/control bytes, 627,836,977,152 bytes total, and
  236,160 external-owner-plus-cleanup seconds. Audit/report/prerequisite overhead
  remains unallocated.
- Current free space is 68,881,358,848 bytes. No native phase is resource
  admissible on this filesystem.
- Source/`own` descriptors are `non-executable-contract` records. Validation is
  never an allocation grant; a later writer must require a separate hash-bound
  allocation registration after capacity and protocol gates pass.
- Each retained manifest must bind the exact registration, job, and owner hashes.
  Each owner binds the current PID namespace, registration and job, and each
  bounded-process supervisor receipt must show normal exit within the exact cap.
- A close is hash-sealed against ordinary drift and written once. It is not a
  hostile same-user immutability guarantee and makes no scientific or runtime
  qualification claim.
- CI, physical rover work, held-out access, actual model/runtime execution, and
  effect-threshold inference are outside this unit.

## File structure

- Create `scripts/memory_family_producer_v3.py`: strict registration/source-own
  descriptor/owner/supervisor validation, raw-admission envelope derivation, and
  read-only pair close.
- Create `tests/test_memory_family_producer_v3.py`: one complete registration,
  boundary tampering, exact jobs/envelopes, owner cleanup, real synthetic PR #99
  close, exclusive publication, and drift rejection.
- Modify `tests/test_memory_family_oracle_admission_v3.py`: allow its existing
  synthetic pair fixture to receive protocol and source-identity hashes while
  preserving the current defaults and every existing test.
- Create `docs/reports/memory-family-producer-v3.md`: exact test/review evidence
  and the remaining native-allocation boundary.
- Create `docs/reports/memory-family-producer-v3-evidence/verification.json`:
  machine-readable commands, counts, hashes, and measured results.

## Review focus

- A duplicate, malformed, or historically reused run UUID must fail before a job
  or envelope is admitted; registration tests corrupt each class.
- A regenerated case, plan, protocol, history, source identity, dependency, or
  namespace binding must differ from the registration and fail; tamper tests
  cover both values and files.
- An `own` post descriptor must bind the exact registered source run and its
  actual initial snapshot path/hash; job tests substitute each field.
- Owner cleanup must be exact for both run IDs and freshly exited in the same PID
  namespace, while the matching bounded-process receipts prove normal return-zero
  completion within their caps; tests reject malformed identity, reused rows,
  active owners, failed supervision, and unsupported dispositions.
- Any change during oracle admission must prevent publication; the close test
  mutates retained evidence inside a wrapped admission call and verifies that no
  receipt exists.

---

### Task 1: Freeze the contract and failing tests

**Files:**
- Create: `tests/test_memory_family_producer_v3.py`
- Modify: `tests/test_memory_family_oracle_admission_v3.py`

**Interfaces:**
- Consumes: `memory_family_v3.build_slots`,
  `memory_family_oracle_admission_v3.admit_oracle_pair`, and the existing
  `_pair`/`_tree_hashes` synthetic test helpers.
- Produces: executable expectations for `build_registration`,
  `validate_registration`, `make_job`, `validate_job`, and
  `close_oracle_pair`; envelope and owner/supervisor checks remain private.

- [x] **Step 1: Extend only the reusable fixture inputs**

  Add keyword-only `protocol_sha256` and `source_identity_sha256` parameters to
  `_pair`, retaining the existing `'4' * 64` and `'6' * 64` defaults. Use those
  values when writing each admission envelope and in the returned descriptor.

- [x] **Step 2: Write the exact registration test**

  Build one canonical development plan for block zero, a two-relation history
  map, an empty strict namespace inventory, and 1,440 deterministic UUIDs. Assert
  the exact family/case/source/condition counts, resource totals, dependency
  bindings, authored-ID inventory digest, zero-allocation flags, and absence of
  output/control directory creation.

- [x] **Step 3: Write strict tamper tests**

  Parametrize duplicate and historical UUIDs, a changed case hash, held-out or
  multi-block plan, unknown condition, changed input bytes, overlapping roots,
  malformed namespace entries, and altered fixed resource totals. Each must
  raise `ValueError` without creating evidence.

- [x] **Step 4: Write job and envelope tests**

  Assert that source and `own` descriptors use their registered UUID/path, exact
  regenerated case, correct relation history, source snapshot binding, and exact
  PR #99 envelope. Reject unregistered cases, source substitution, wrong snapshot
  path/hash, stale registration bytes, any other condition, and any attempt to
  treat the descriptor as an allocation grant.

- [x] **Step 5: Write owner and close tests**

  Reuse `_pair` for one block-zero row-four change pair. Write exact job and owner
  and normal supervision files plus one two-row cleanup receipt, patch only the
  live PID observation, add the exact registration/job/owner binding to each
  synthetic raw manifest, invoke the real PR #99 admission, and assert one close
  receipt with unchanged raw inputs. Reject a PID-namespace mismatch, active
  owner, failed supervisor, missing manifest binding, second close, and an input
  mutation during admission; no rejected close may publish a receipt.

- [x] **Step 6: Run the focused tests and confirm the expected import failure**

  Run `python -m pytest -q tests/test_memory_family_producer_v3.py` and confirm it
  fails because `scripts.memory_family_producer_v3` does not exist. Commit the
  contract tests separately.

### Task 2: Implement the zero-allocation producer contract

**Files:**
- Create: `scripts/memory_family_producer_v3.py`

**Interfaces:**
- `build_registration(block, *, plan_path, protocol_path, source_identity,
  history_bundles, namespace_inventory_path, output_root, control_root,
  publication_root, run_ids)` returns a fully validated plain-JSON registration
  and never writes.
- `validate_registration(registration)` returns a defensive copy after exact
  structural, identity, hash, namespace, root, count, and resource checks.
- `make_job(registration_path, case_id, condition, source=None)` returns one
  registered, non-executable plain-JSON source or `own` descriptor and never
  writes. Other registered conditions remain IDs only in this unit.
- `validate_job(job)` verifies all registration/input bindings and returns a
  defensive copy; it does not grant permission to create an output or owner.
- `close_oracle_pair(registration_path, source_job_path, post_job_path,
  cleanup_path, *, deadline=None)` validates an exact source/`own` pair, calls
  the real oracle admission, rechecks its full ledger, and exclusively writes and
  returns the derived close descriptor.

- [x] **Step 1: Add strict bounded primitives**

  Reuse `artifacts._safe_path`, `_read`, and `_json`; use canonical SHA-256,
  canonical UUID hex, finite monotonic deadlines, fixed field sets, fixed-size
  JSON reads, and `open('xb')`. Do not add a dependency or a CLI.

- [x] **Step 2: Regenerate and validate the complete matrix**

  Call `build_slots('development', [block], plan['prerequisites'])`, regenerate
  all cases, prove only the intentional family ID is shared among twins, derive
  the authored-ID set from cases plus public graphs, bind the 1,440 UUIDs in
  source-then-nine-condition order, and reject intersections with the supplied
  historical inventory.

- [x] **Step 3: Bind fixed inputs and resources**

  Require the plan file to equal the regenerated canonical plan. Bind the
  protocol and source identity by canonical digest, both relation histories by
  safe path and file digest, the strict namespace inventory, non-overlapping
  roots, critical dependency file digests, and the literal resource projection.

- [x] **Step 4: Derive exact jobs and admission envelopes**

  Recover a case and slot only from the registration. A source has null source
  fields; the `own` descriptor has the exact registered source run plus
  `<source-run>/snapshots/initial.snp` and its supplied digest. Validate the
  registration hash on every descriptor read and derive the exact PR #99 manifest
  envelope privately rather than accepting an inline copy. Mark every descriptor
  `non-executable-contract` and reject every condition except `own` in this unit.

- [x] **Step 5: Validate independent owner cleanup**

  Require exact owner fields for schema, run ID, PID/start time/PGID, PID namespace,
  registration hash and job hash; positive integers; `pid == pgid`; exact cleanup
  path/hash/status; and a fresh `memory_restore_diagnostic.owner_exited` check in
  the same PID namespace. Require the exact bounded-process supervisor file,
  `completed`, return code zero, its registered timeout, finite elapsed time within
  the cap, and stdout/stderr files within 1 MiB. Never signal or clean a process.

- [x] **Step 6: Publish one hash-sealed close**

  Require exact job file locations and one ordered two-row cleanup receipt.
  Require each raw manifest's producer binding to equal the registration, job and
  owner hashes. Capture registration/job/cleanup/supervisor/dependency/input
  hashes and full source/post tree ledgers, run the existing raw oracle admission,
  then recompute the same ledger and owner checks. On equality, write one canonical
  close containing the complete oracle result, ledgers, owner/supervisor evidence,
  `contract-pair-validated`, `study_complete:false`, empty claims, and the
  software-only scope. Return its path and SHA-256.

- [x] **Step 7: Run focused tests and commit**

  Run `python -m pytest -q tests/test_memory_family_producer_v3.py
  tests/test_memory_family_oracle_admission_v3.py` and commit only after all
  focused checks pass.

### Task 3: Verify, review, and record the evidence boundary

**Files:**
- Create: `docs/reports/memory-family-producer-v3.md`
- Create: `docs/reports/memory-family-producer-v3-evidence/verification.json`

**Interfaces:**
- Consumes: the final implementation commit and focused/affected test results.
- Produces: a human report and machine-readable verification record; neither is
  a native registration, allocation, or scientific result.

- [x] **Step 1: Run focused and affected verification**

  Run the producer/admission/oracle/family/slot/snapshot tests, compile the
  changed Python files, and run `git diff --check`. Record exact commands,
  pass/skip/failure counts, durations, commit, and file hashes.

- [x] **Step 2: Review the trust boundaries**

  Independently inspect registration regeneration, namespace collision checks,
  source/post linkage, manifest provenance, PID namespace, supervision, read-time
  drift, exclusive close, and any route by which model/runtime work could start.
  Fix material findings and rerun only the affected checks.

- [x] **Step 3: Write and commit the report**

  State that tests use synthetic recordings; no block was selected, registered,
  allocated, or run. Record the 558,955,618,304-byte current capacity shortfall
  against the known subtotal, plus the still-unbounded report/audit/prerequisite
  overhead and historical-inventory completeness gate.

- [ ] **Step 4: Publish a stacked draft PR and update the goal tracker**

  Push this branch through the `Aadrika08` account, open a draft PR against
  `research/memory-family-oracle-raw-adapter`, verify base/head/account, then add
  the PR, commit, verification result, and next allocation decision to the goal
  tracker branch without changing `main`.
