# Memory Family V3 Allocation Admission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans
> to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for
> tracking.

**Goal:** Add one deterministic, zero-owner preflight that publishes a bounded
development allocation admission only when storage, namespace, upstream, and
runtime identities all satisfy the frozen contract.

**Architecture:** A new zero-owner script validates the existing PR #100
producer registration and accepts only two independently frozen namespace-only
exports, never caller-selected evidence trees. It derives source identities
without model loading or subprocesses, uses existing artifact and storage
primitives for bounded reads/recount/capacity, then exclusively links a
canonical receipt before the final full revalidation and durable commit.

**Tech Stack:** Python 3.11 standard library, existing `palimpsest.memory`,
`artifacts`, `assets`, and `storage` helpers, producer/family validators, pytest.

**Spec:** `docs/plans/memory-family-allocation-admission-v3.md` and
`docs/plans/memory-family-allocation-admission-v3-protocol.json`

## Global Constraints

- Development block zero only; 48 families, 144 cases, 1,440 family owners, and
  eight separately bounded prerequisite owners.
- Preserve the producer subtotal 627,836,977,152 bytes, 8 GiB prerequisite
  allowance, 6,710,886,400-byte non-recording allowance, and 2 GiB floor.
- Never invoke Engine, import/load a model, spawn a subprocess, start an owner,
  touch held-out inputs, change scientific protocols, or publish on refusal.
- Keep all outcomes and historical roots immutable. Never retry, replace,
  overwrite, prune, compress, or use hashes as independence evidence.
- Use repository-local `Aadrika Maurya <aadrikamaurya@gmail.com>` identity and
  commit the frozen contract before tests or implementation.

## Review Focus

- The exact `pre-heldout-development-history` and `training-namespace` exports
  must match protocol-frozen counts/digests and known-source enumeration; the
  separate path manifest supplies portable roots and the searched-root receipt
  binds the paths actually used. Unresolved coverage refuses before reading
  either external path.
- Each namespace root permits only one canonical `namespace-export.json`;
  directories, extra files, symlinks, special files, or drift must refuse.
- A UUID, authored string, or development seed already present in any declared
  historical/training root must be detected even when it appears only in a path
  component or nested metadata value.
- Capacity must be aggregated once for the shared filesystem and subtract
  already admitted root usage without double-counting or weakening the 2 GiB
  floor.
- Upstream pin plus full tree content must reject missing, dirty, untracked, or
  wrong-HEAD checkouts without calling Git, and its gitdir cannot escape the
  checkout's own resolved Git metadata directory.
- Prepared graph edge and mapping paths must remain under the verified graph
  root, and a namespace root rejects after reading at most two entries.
- Exclusive publication must link before final revalidation. Rollback must
  unlink and directory-fsync; inability to prove rollback is an explicit
  indeterminate state.
- Every behavior-bearing local source has exact path/size/SHA-256 in the
  receipt, equals the baseline captured while the module imports, is rechecked
  after linking, and is required future-launcher input.

---

### Task 1: Make the storage entry ceiling explicit

**Files:**
- Modify: `src/palimpsest/storage.py`
- Modify: `tests/test_storage.py`

**Interfaces:**
- `StorageLimits.max_entries: int = 100_000` preserves the existing default.
- `StorageBudget.usage()` applies the configured limit instead of the module
  constant.

- [ ] Write a test whose two-entry root fails with `max_entries=1`, while the
  same root passes with `max_entries=2` and the default remains 100,000.
- [ ] Run the focused test and confirm the old constructor rejects the new
  keyword.
- [ ] Add and validate the frozen field; change only the recount comparison.
- [ ] Run `tests/test_storage.py` and commit the passing helper change.

### Task 2: Pin inventory and admission behavior with failing tests

**Files:**
- Create: `tests/test_memory_family_allocation_v3.py`

**Interfaces:**
- `build_namespace_inventory(search_manifest_path)` returns a producer-compatible
  namespace plus a searched-root receipt and never writes.
- `admit(registration_path, search_manifest_path, repo_root, asset_root)` returns
  and exclusively publishes one allocation receipt.

- [ ] Assert unresolved production coverage refuses before opening an external
  root and leaves both allocation flags false.
- [ ] Build two synthetic namespace-only exports plus an independent resolved
  fixture contract; assert exact UUID/authored-ID/training-seed collection,
  known-source enumeration, counts, bytes, and combined digest.
- [ ] Add table tests for unknown/missing source IDs, unexpected files or
  directories, malformed/noncanonical/oversized export, symlink, special file,
  overlap, expected-identity drift, and held-out sentinel paths.
- [ ] Reuse the producer fixture to bind 1,440 UUIDs, then test namespace/run,
  namespace/authored, and training-seed collisions.
- [ ] Test direct roots, same-filesystem capacity arithmetic, frozen subtotal
  equality, missing/dirty upstream refusal, runtime/asset/profile/source
  binding, and the zero-owner flags. Sentinel Engine/model constructors,
  graph/checkpoint loaders, inference, and subprocess calls rather than imports.
- [ ] Test exclusive success, existing-target refusal, mutation after the hard
  link, and injected fsync/link/rollback failure handling. Patch only external
  capacity/upstream/assets identities in the success fixture; inventory,
  registration validation, and publication stay real.
- [ ] Guard `Engine.open`, FLYNN/male model loaders, prepared-graph/model APIs,
  subprocess calls, and held-out paths with sentinels. Commit corrected RED
  tests before changing the admission implementation.

### Task 3: Implement the deterministic admission module

**Files:**
- Create: `scripts/memory_family_allocation_v3.py`

**Interfaces:**
- Public functions exactly match Task 2.
- CLI arguments are `--registration`, `--search-manifest`, `--repo`, and
  `--assets`; the CLI calls `admit` and prints only its returned descriptor.

- [ ] Validate the exact two source IDs against the frozen contract. Open only
  the one allowlisted file in each direct root, with no recursive discovery;
  require canonical schema, counts, bytes, digests, and known-source identity.
- [ ] Collect canonical UUIDs, bounded authored IDs, and training seeds from
  those exact exports; generate the producer namespace and coverage receipt.
- [ ] Validate the producer registration, regenerate cases/authored IDs/seeds,
  compare the inventory exactly, and reject every collision.
- [ ] Validate fresh direct roots and use `StorageBudget` with 643,137,798,144
  max bytes, 2 GiB floor, 1,448 runs, two snapshots per run, 1,592 exports, and
  131,072 entries.
- [ ] Derive interpreter/dependency, asset/model/graph, family-profile,
  behavior-source, and detached upstream pin/full-tree identities without
  calling any load/constructor/inference path.
- [ ] Sync a temporary, link it exclusively, remove the temporary name, then
  rebuild every mutable identity and capacity. On any failure, unlink and
  directory-fsync; raise an indeterminate-publication error if rollback cannot
  be proven durable.
- [ ] Run the focused allocation and storage tests, compile the changed Python,
  and commit the implementation.

### Task 4: Verify the refusal and affected stack

**Files:**
- Create: `docs/reports/memory-family-allocation-admission-v3.md`
- Create: `docs/reports/memory-family-allocation-admission-v3-evidence/verification.json`

**Interfaces:**
- Evidence records exact commands, counts, hashes, free-space arithmetic,
  refusal blockers, and zero-publication observation.

- [ ] Build a software-only probe registration in `/tmp` from the frozen block,
  existing retained histories, deterministic UUIDs, and the unresolved
  production coverage contract. Do not open external namespace roots,
  initialize upstream, or allocate a native root.
- [ ] Run the real CLI once; require ordered capacity and/or upstream refusal and
  prove `allocation-admission.json` is absent.
- [ ] Run the focused tests, then the full affected PR #97-#101 family/oracle/
  producer/analysis/storage/artifact/replay slice with the four known optional
  `FlynnContinuation` tests deselected because upstream remains uninitialized.
- [ ] Run compile, `git diff --check`, contract arithmetic, forbidden-import AST,
  and clean-main/worktree checks.
- [ ] Request a fresh read-only source/diff review, fix Critical/Important
  findings through RED-GREEN tests, and commit the report/evidence.
- [ ] Push `research/memory-family-allocation-admission-v3` and open a draft PR
  based on `research/memory-family-analysis-v3`; do not merge or invoke CI.
