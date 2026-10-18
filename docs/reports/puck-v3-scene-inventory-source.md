# Puck scene inventory: authentic Git discovery and catalog normalization

Independent SOURCE GO applies to
`5e93cc31a3f26600fdebd199a7f9efc456f0e2e1`, based on PR #122 `fc04598`.
This implements two parts of authentic inventory admission: descriptor-first
Git discovery for one declared repository and pure historical task-catalog
collision identities. Complete project/root discovery, semantic inventory assembly
and the real registry/scene/collection execution path remain incomplete.

Root affected verification: **509 passed, six explicitly deselected, 51.84 s**.
Independent exact repetition: **509 passed, six deselected, 51.90 s**, exit 0.
The reviewer verified unchanged HEAD/source and no remaining component-scope
blocker. No actual project observer/parser invocation or inventory stage ran.

## Implemented behavior

`HeldGitSceneSources` observes local heads/tags/remote-tracking refs, fresh remote
head/tag/pull advertisements, registered worktrees including detached heads,
every reachable commit/root tree, and unique tracked JSON/Markdown document
objects. Missing advertised objects fail without fetch. It holds canonical
ancestor/common Git metadata, rejects ambiguity and observes the same closure
before and after use. Discovery and snapshot never read document payloads;
only explicit `read_blob(oid)` returns registered document bytes, verifying size,
Git OID and SHA256. Read hashes remain separate from descriptor observations.

Worktree registration binds unique admin targets, reciprocal `gitdir` pointers,
HEAD/branch commit identities and held namespace edges. Config includes, BOM/NUL
ambiguity, shallow/grafted/replaced/alternate sources, symlinked documents and
changing/missing/unreadable registrations fail. Snapshot copying and descriptor
close remain inside source/clock checks. A body failure remains primary if final
checks also fail; notes retain the final drift and cleanup failures.

Commands read bounded pipes incrementally. Failure attempts TERM/KILL, reaps the
direct leader and observes owned process-group absence within the existing cleanup
allowance; remaining groups and signal/cleanup failures cannot yield successful
source close. This is trusted-Git operational custody, not a hostile-descendant
sandbox or a claim that the parent reaps grandchildren. External Git/transport/
SSH/environment/dependency qualification remains an execution-freeze obligation.

Finite component ceilings: 4096 refs/commits/blobs/worktrees, 65,536 trees and
entries per tree, 16,384 Git namespace entries, 4 MiB per explicit document read,
64 MiB descriptor/read metadata, 8 MiB command stdout and 64 KiB stderr. The
constructor accepts an absolute deadline no more than 600 seconds ahead. These
are source failure ceilings, not extra stage time/storage grants or measurements
of the actual project's closure. Document input sums are not retained in memory;
the component retains descriptors and observed read hashes, not payload caches.

`parse_task_catalog` supports the five exact historical task version identities,
strict bounded JSON and both genuine mechanics shapes: fixed action and exact
`puck-teacher` controller. It rejects duplicate keys, unknown nested scene fields,
reserved IDs, type aliases, split mismatches, nonfinite/oversized geometry and
structure bounds. Canonical geometry and scientific-initial domains match v3;
legacy reset payload hashes retain the genuine canonical historical reset object,
without fabricated v3 slots. Model seeds and unrelated byte/hash fields are not
scene IDs. Results are extraction evidence, not whole-inventory admission.

All whole-project/inventory/reservation/scene/native/bootstrap/collection grants
remain false or unissued, and qualification claims remain empty.

## Verification and retained failures

Tests use actual temporary local Git repositories/bare file remotes, branches,
annotated tags, packed objects, SHA1/SHA256 stores and detached worktrees; no
project refs, real remote advertisements or retained registries are scanned.
Catalogs are authored fixtures; the new parser did not parse actual public task
catalogs or protected held-out data. Final new coverage is **98 checks**:
46 catalog and 52 Git checks, plus the inherited 411 passing affected checks.

Meaningful REDs preceded the implementations and review fixes: missing APIs;
genuine teacher row rejection; silent nested geometry omission; integer overflow/
root type errors; eager document reads; config include/BOM escape; double-leading
roots; late/failing/drifting snapshot copies; reciprocal worktree aliasing;
missing final PG observation and cleanup notes; signal failure masking; and
active-body/final-drift exception continuity. The BOM test first proves actual
Git accepts the temporary external include, then proves this component rejects
it before its first Git command. Authored source tests are repeatable; no frozen
real attempt was consumed or retried.

The exact affected command is the predecessor's twelve test files plus
`tests/test_puck_scene_catalog.py` and `tests/test_puck_scene_git.py`, using
`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests` and the r0-reproduction Python.
It keeps the same six explicit mechanics exclusions, named and independently
reproduced on unchanged base in the
[predecessor report](puck-v3-collection-launcher-source.md): three historical
profile-pin mismatches and three missing-httpx failures. These are not passing
checks. The preliminary combined run passed 508 checks in 53.52 s before the
last exception-continuity regression/fix; the final source was then verified
with 509 checks as recorded above.

The bounded default repository command (`pytest -q --maxfail=1 --tb=short`,
20-second outer limit) again stopped at `tests/test_lab.py` collection, missing
`fastapi`: exit 1, one error, 0.34 s. No default full-suite pass is claimed.

Browser availability was refreshed on 15 October 2026 locally: native
inventory returned **zero apps and zero browsers**. No real
browser/artwork workflow ran; this is availability evidence only.

## Catalog decision and remaining full path

[Prospective admission amendment 01](../plans/puck-v3-scene-inventory-admission-amendment-01.md)
identifies the frozen protocol conflict: its public task catalogs embed held-out
coordinates, while the literal lock says held-out rows stay unopened. The
separately requested choice remains pending: permit collision-only public-catalog
parsing and record exposure, or require independently prepared identity-only
projections. No approval or real scan follows from this source result.

A successful parse reports `held_out_catalog_read:true` for such authored rows;
it never labels whole-file parsing as unopened coordinates. Actual held-out
registries, recordings, runtime scenes, training inputs and evaluation remain
locked. The original protocol SHA, splits, models, limits and capability thresholds
remain unchanged.

Next implement all matching repository/retained-root discovery, exact typed
JSON/report/Markdown/reference parsing, duplicate-occurrence provenance and
variant-preserving semantic assembly. Preserve every historical variant; do not
fabricate hashes or discard evidence to fit the old uniqueness checker. Then
bind runtime/transport/source/input identities, durable attempt/lease/process/
resource supervision and exact registry-stage allocation before execution.
Scene minting and collection require their separate complete admissions.

Memory amendment 02 still awaits its own approval; navigation attempt 3 remains
unauthorized. All seven simulation release gates stay open. No actual registry,
reservation, minter, original model inference, native owner, collection, fitting,
development, held-out evaluation, CI or physical rover work ran in this wave.
