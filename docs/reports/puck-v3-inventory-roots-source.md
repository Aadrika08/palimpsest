# Puck inventory roots and historical occurrence assembly

This source wave continues PR #123 (`ef44ce8`). Independent source review gives
SOURCE GO to `dc65819dcaa31ceab37351092ac97453d8e7a546`; its exact affected
command passed **632 checks, six explicitly deselected, in 55.88 seconds**.
The diagnostic was subsequently reviewed at `c025aa95`; production source is
unchanged from `dc65819`, and SOURCE GO extends to that commit.
The catalog-only review separately gives SOURCE GO to `630c4fe`, with **84 checks
in 0.41 seconds**. These are authored-fixture source results, not actual inventory
or execution admission. No real project observer, catalog parser, registry,
reservation, model, native owner or study stage was invoked.

## Working behavior

`HeldSceneInventoryRoots` authenticates a strict externally hash-bound root
search contract and holds no-follow ancestor/discovered directory descriptors.
It enumerates directory-entry metadata only, discovers nested `.git` directory
and linked-worktree regular-file markers, and reports retained-root name and
manifest/registry/index/reservation filename hints. It neither reads leaf
payloads nor invokes Git. Repository markers and retained hints are candidates,
not validated repositories or supported scene schemas.

Search roots are canonical, existing, nonoverlapping directories. Every declared
opaque scope must be an existing, nonoverlapping proper subtree with a bounded
reason. Missing, aliased, symlinked or ambiguous declarations fail. Git control
storage is automatically reported opaque; caller roots cannot bypass it by
starting inside `.git`. No dependency directories are silently excluded.

Held edges and metadata namespace digests are checked during discovery, before
and after snapshot copying, during explicit recheck and before normal close.
Add/remove/rename/replace, leaf metadata edits, link-count changes, inode aliases,
special entries, clock expiry and lifecycle violations fail and poison the
context. All owned descriptors are closed on failure. A body exception remains
primary when final drift or descriptor cleanup also fails; notes retain both.
Read atime is excluded from the digest. Opaque directory contents deliberately
remain unobserved and unauthenticated, including content changes during custody.
The receipt states the last-held-check boundary explicitly: these are neither
atomic filesystem snapshots nor post-close or hostile-process guarantees.

Root source ceilings: 64 KiB contract, 32 search roots, 1024 declared opaque
subtrees, 1024 UTF-8 bytes per reason, depth 32, 8192 held directories, 65,536
observed entries and 64 MiB retained metadata. Discovery/snapshot/recheck/successful
close share an absolute deadline at most 600 seconds ahead. These are operational
failure ceilings inside the future registry stage, not extra grants or a measured
claim that the actual machine/project closure fits them.

`assemble_task_catalog_occurrences` validates supplied Git document descriptors,
framed SHA1/SHA256 blob OIDs and catalog bytes through the existing exact task
parser. It groups only identical scene-ID/canonical/scientific/payload identity
tuples and preserves every distinct repository/commit/tree/path/OID/pointer
occurrence. Same-ID variants and hash aliases remain explicit. Sorting is
independent of input order; caller inputs and later outputs are independent.
Conflicting repository formats, commit root trees, tree-path blobs/modes and
repeated commit-path declarations reject rather than become more provenance.

Blob binding does not authenticate caller-supplied commit/tree attachment,
repository coverage, fresh refs or filesystem custody. Unsupported documents
fail; this task-catalog-specific API never substitutes an empty result for
unknown Markdown, references, manifests or registries. Its
`legacy_scene_rows_compatible` concerns only the old global scene-row uniqueness.
The existing validator cannot represent same-ID variants or individual shared
hashes. No variant is dropped or hash fabricated to fit it; an actual conflict
requires a prospective schema/semantics decision before reservation.

Occurrence source ceilings: 4096 documents/variants, 65,536 scene occurrences,
32 MiB aggregate supplied input and 64 MiB retained metadata/output under the
same absolute deadline. No raw payload cache is retained in the receipt.
Whole-project/inventory/reservation/native/collection/executable grants remain
false and qualification claims remain empty. Authored mixed catalogs report
held-out catalog exposure; no actual held-out catalog/runtime path was opened.

## Verification and limits

Initial RED: **63 missing-root-feature failures** and **27 missing-occurrence-API
failures**. Subsequent adversarial REDs exposed opaque depth/race handling,
held-edge continuity, snapshot-copy drift/deadline, Git-storage bypass, lifecycle
poisoning, and contradictory tree entry declarations. Each was fixed before
source review. Final focused root check: **85 passed in 0.12 seconds**. Root
catalog/occurrence check: **84 passed in 0.44 seconds**; independent repetition
passed in 0.41 seconds. Tests operate on authored temporary forests and Git
repositories, including explicit Git-document reads into catalog assembly.

The first root combined command recorded **631 passed, one failed, six
deselected, 55.76 seconds**. The inherited
`test_actual_unchanged_cpu_model_and_interval_seam_on_authored_inputs[terminal]`
failed at its final verification assertion after its outer exception handler hid
the preceding failure. Independent exact source verification passed all 632
checks in 55.88 seconds; a root isolated reproduction passed in 1.50 seconds.
The original failure is retained here. Its underlying exception was not captured,
so its cause remains unestablished; no production fix is claimed. The test harness
now re-raises failures before scenario verification to preserve the next original
traceback. This diagnostic change does not weaken the success predicate or
change production execution, frozen studies or resource limits.
The subsequent serial combined command, with diagnostics enabled, passed
**632 checks, six deselected, 52.96 seconds**, exit 0. This passing rerun does
not establish the cause of the retained earlier failure.

The six explicit exclusions are inherited and documented with unchanged-base
reproduction in the [launcher report](puck-v3-collection-launcher-source.md):

- `first_supervisor_exception_retains_all_unstarted_rows`
- `historical_construction_pin_is_not_silently_promoted`
- `v5_mechanics_changes_only_identity_and_version_notes`
- `progress_timeout_forces_cleanup_and_never_passes`
- `receipt_before_next_ancestry_poll_waits_for_independent_identity`
- `startup_timeout_identifies_owner_before_any_receipt`

They are three immutable historical-profile mismatches and three missing-httpx
cases, not passing checks. The bounded default repository command again stops
at `tests/test_lab.py` collection, missing FastAPI: **exit 1, one error, 0.30 s**.
No full-suite or integrated-release pass is claimed.

The affected command is the sixteen named puck inventory/Git/custody/collection/
on-policy/qualification/mechanics test files, using the r0-reproduction Python
with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests`, and the same six exclusions
listed above. The source-only root and catalog components add 123 checks to the
predecessor's 509 affected checks. Heavy original one-shot qualifications were
not rerun; test inputs are authored fixtures.

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
  /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
  -m pytest -q --tb=short \
  tests/test_puck_scene_roots.py tests/test_puck_scene_occurrences.py \
  tests/test_puck_scene_catalog.py tests/test_puck_scene_git.py \
  tests/test_puck_custodied_native.py tests/test_puck_collection_ledger.py \
  tests/test_puck_execution.py tests/test_puck_execution_files.py \
  tests/test_puck_collection_admission.py tests/test_puck_bundle_provenance.py \
  tests/test_puck_on_policy.py tests/test_puck_on_policy_interval.py \
  tests/test_puck_on_policy_native_interval.py \
  tests/test_puck_original_bundle_qualification.py tests/test_bounded_qualification.py \
  tests/test_puck_mechanics.py \
  -k 'not (first_supervisor_exception or historical_construction_pin or progress_timeout or receipt_before_next or startup_timeout or v5_mechanics)'
```

## Remaining path

Complete declared project scope and repository matching, all reachable-history/
worktree and retained-root aggregation, strict Markdown/reference/raw-registry/
manifest dispatch and resolution, source/transport/runtime/dependency binding,
durable attempt/reservation, one-owner lease, process/resource supervision and
complete owner/collection close. Candidate discovery and catalog occurrence
normalization do not finish any of these compound admissions by themselves.

The [catalog access decision](../plans/puck-v3-scene-inventory-admission-amendment-01.md)
remains pending; so does memory qualification attempt-02. Preserve every consumed
attempt. Navigation attempt 3 remains unauthorized. Actual heavy stages remain
serialized, under unchanged protocols and budgets. All seven simulation release
gates remain open. CI and physical rover work remain outside this wave.
