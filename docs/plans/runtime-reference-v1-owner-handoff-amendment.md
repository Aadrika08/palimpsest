# Task 2/3 runtime-requirements interface amendment

Status: **APPROVED source-only interface amendment; no actual runtime/profile adoption.** This supersedes only the affected interfaces in [runtime-reference-v1-implementation.md](runtime-reference-v1-implementation.md). It does not reopen Task 1's policy or accounting backend. Source inspected at the parent-supplied `00e9ae3` context; no independent Git/CI assertion, tests, imports or runtime/model/data reads/hashes were performed. Only this ignored amendment is written.

## Decision and source evidence

Adopt the root's explicit V3 `immutable.runtime_requirements` addition. It is smaller and safer than reading the manifest outside custody, deriving its expected pins from itself, adding parent-to-child IPC, or weakening `RuntimeHandle` validation. The child needs the same independent expectations in its job, not merely the parent's `freeze.runtime_roots`.

The concrete contract requires this: `RuntimeHandle.__init__` immediately validates required roots and the complete five-field pin object (`scripts/memory_source_runtime_closure_v1.py:582–586`); `_pins` requires Python alias/ELF, owner, `pyvenv_config` and `required_sources` (`:248–254`). Entry acquires/reads the manifest under custody and compares it against those already supplied pins (`:636–655`, manifest equality at `:324–327`). Its constructor is not a metadata-validation placeholder. The old owner validates only V2's inline closure (`scripts/memory_family_source_runtime_v2.py:98–156`).

## Exact V3 job addition and shared pure validator

V3 `immutable` keys become exactly:

```
python_alias, python_elf, owner_source, runtime_manifest, runtime_requirements
```

`runtime_requirements` has exactly `{roots, pyvenv_config, required_sources}`:

- `roots`: a list of 1–16 canonical absolute POSIX root strings, sorted, unique and pairwise nonoverlapping. Enforce Task 1's existing path/component/UTF-8 bounds, not just `Path.is_absolute`. These are independently frozen required full prefixes; they cannot be inferred from the manifest. They are converted to a tuple unchanged for the holder.
- `pyvenv_config`: exact `{path, size_bytes, sha256}`, with canonical path equal by lexical construction to `Path(python_alias).parent.parent / 'pyvenv.cfg'`. This equality performs no resolve/stat/open. Descriptor size is an integer 0–2 GiB, bool forbidden; SHA-256 follows the existing lowercase policy. It is independently frozen, not freshly hashed during metadata validation.
- `required_sources`: a sorted, path-distinct list of at most 64 exact absolute descriptors under the same zero-byte-eligible Task 1 file-record rules. No new source allowlist is derived from imported-module observations. Empty or incomplete lists may pass structural validation but must fail the private live-layout membership check described below.

To avoid duplicating Task 1's descriptor validation, add exactly this pure public helper in `scripts/memory_source_runtime_closure_v1.py`:

`validate_runtime_pin_requirements(value: dict) -> dict`

Its input is the **complete five-field pin object**, exactly `{python_alias, python_elf, owner_source, pyvenv_config, required_sources}`. It uses existing `_pins` validation and returns a deep independent copy; it creates no handle and performs no IO/clock/check callback. This is a public wrapper for existing semantics, not a new authority/profile. Retain zero-byte descriptor eligibility and existing caps. For roots the owner may use the same module's existing pure `_path` primitive in its local requirements parser; do not duplicate or relax its path grammar. This small private primitive dependency is confined to the source-owner integration, not a new public API.

Add owner-private `_runtime_requirements(job: dict) -> tuple[tuple[str, ...], dict]`. It checks the exact three-field object/root-list rules, composes the five pins from `immutable.python_alias/python_elf/owner_source` plus requirements.pyvenv_config/required_sources, calls the new public helper, checks the lexical config path, and returns `(roots, pins)`. Both V3 metadata validation and private custody use this same function. The helper reads only the provided job value. All returned collections are independent of caller mutations.

V3 metadata validation also rejects output overlap with any declared root, pin, alias, recipe/manifest/ledger descriptor or existing assets input. Preserve source-case, repo identity, pinned owner identity and unchanged limits. Repeated semantic pins at the same actual path are allowed only with identical descriptors; they are not multiple physical inputs. Do not reject owner/parent/helper pins merely because their paths lie inside a required source root. Preserve the 256 KiB job bound, including the already planned complete admitted V3 serialization check. V2 keys, pin size rules, inline closure, serialized bytes and failure behavior remain unchanged.

## Task 2 private owner contract

Replace the ambiguous private signature with:

```
_run_reference_admitted(job: dict, storage, *,
    check: Callable[[], None],
    runtime_handle_factory=closure.hold_runtime_manifest,
    engine_loader=_load_engine) -> dict
```

`storage` is the existing explicit storage object consumed by `_run_admitted`; authored tests may supply their existing fixture object. `engine_loader` is a zero-argument **factory returning the engine opener**: `_load_engine()` returns `Engine.open`. Call the factory only after private live-layout checks and successful handle entry, then pass its returned callable to `_run_admitted(job, storage, opener, check_identity)`. Do not pass `_load_engine` itself where `_run_admitted` expects the opener: the old core calls that opener with repo/assets/recording arguments (`scripts/memory_family_source_runtime_v2.py:290,324–327,396–407`). No public `run_source`/CLI loader argument or bypass is added.

The private body validates the V3 job, obtains `(roots, pins)` from `_runtime_requirements`, checks its own executing layout, and enters its own process-local handle with the exact job reference, returned requirements and output root. The parent independently enters its own handle. Both receive the unchanged `parent_admission.runtime_deadline_monotonic` absolute enclosing deadline (at most the original 900-second window); neither starts a new 900-second interval. The separate tighter source-work deadline remains unchanged. Child validation enforces finite non-bool deadlines, source<=runtime and future bounds, but never extends them. Every acquisition/recheck is separately charged.

The child checks full prefix coverage for its own `REPO_ROOT/src`, `REPO_ROOT/scripts`, `REPO_ROOT/paper/studies/change_audit_v1`, `sys.prefix/lib/pythonX.Y/site-packages`, and `sys.base_prefix/lib/pythonX.Y`; required nested paths are covered by an existing outer required root, never by dropping a required obligation. It checks `sys.executable`/alias and ELF using existing post-gate mechanisms. Required source descriptors must include the owner, parent, runtime-closure helper, numeric sealer, numeric-preservation helper and directory census helper at their actual checkout paths. The parent file contains the CPU compatibility helper and is therefore already required. Hash/pin equality is enforced against held manifest records; no current source is rehashed to invent an expected pin. These are private post-gate/live-layout checks, not template-time reads or proof of pre-import identity.

The current holder interprets required roots as complete-prefix coverage (`scripts/memory_source_runtime_closure_v1.py:310–315`), not equality to the manifest's selected root list. Preserve that Task 1 interpretation in this amendment: additional manifest-selected roots remain explicitly hash-bound, fully held and globally counted. Independently frozen required roots cannot be trimmed to get around executing-layout coverage. This amendment does not silently change the holder to an exact-root-list API.

Actual V3 `run_source` remains closed on retained-unqualified **before any handle acquisition, runtime/model read, loader invocation or output write**. Private fixture seams are not operator admission or a future actual backend.

### Outcome/failure schema selection inside the existing core

At the start of `_run_admitted`, select a finite schema pair solely from the already validated job schema: V2 -> existing `memory-family-source-owner-outcome-v2` / `memory-family-source-owner-failure-v2`; V3 -> corresponding `...-v3`. Reject unknown job schemas. Use that selection at each existing failure-file construction and returned outcome (`scripts/memory_family_source_runtime_v2.py:377–393`). Keep field values/order/canonical V2 bytes and the existing V4 source-owner/V3 worker-report formats unchanged. Do not rewrite an already written failure artifact or relabel its returned dict after the fact.

A V3 handle close failure after a tentative recorded core outcome must propagate as failed execution and cannot return recorded. If a core failure artifact already exists, preserve it unchanged; the parent may record the separate teardown failure in its own controls. Do not add a second overwriting writer merely to obtain a preferred schema. New failure emission, when applicable, uses the selected schema before its first exclusive write.

## Task 3 parent changes

V4 metadata verification requires exact list equality `job.immutable.runtime_requirements.roots == freeze.runtime_roots`, calls the owner's pure `_runtime_requirements`, and retains all ordinary structure/disjointness checks. It does not instantiate a `RuntimeHandle`, open the external manifest/recipe/ledger, read payloads or inspect the real installation to validate a template.

The private/post-gate `_bind_reference_inputs` uses precisely those roots and five pins. Independently check its own live `ROOT/src`, `ROOT/scripts`, paper subtree, executing venv site-packages and base stdlib coverage plus required source membership, just as the child checks its layout. Parent/child differing installations or frozen roots/config/source pins refuse, even if one process can hold its own manifest successfully. Existing `_bind_inputs` for V3 freeze/V2 job is unchanged. The actual V4 CLI remains closed before external payloads and output creation; no accounting/load backend is introduced.

No other V4 schema/accounting/deadline decision changes. All added requirements and their duplicated job/freeze/control copies consume the unchanged combined 1 MiB metadata envelope. A larger job cannot borrow from external manifest storage or controls/headroom allowances.

## Added authored tests and shared-file ownership

Task 2 now owns the following **small shared-helper amendment**, coordinated after the root accepts the pending Task 1 fix review: add `validate_runtime_pin_requirements` and its focused tests in `scripts/memory_source_runtime_closure_v1.py` / `tests/test_memory_source_runtime_closure_v1.py`. Do not modify Task 1 internals, profile, custody implementation or fixes under review. Task 3 consumes the helper and owner parser; it does not independently redefine pin validators. Root must serialize this ownership with any continuing Task 1 edits.

Add these Task 2 tests in the existing owner test file:

- `test_v3_requirements_are_exact_independent_metadata`: missing/extra keys, invalid/overlapping/unsorted/17 roots, wrong lexical config location, duplicate/65 sources and contradictory redundant pins refuse; valid zero-byte source/config descriptors pass metadata structure. Mutation of caller objects cannot alter returned requirements.
- `test_v3_template_never_constructs_holder_or_reads_pins`: fail-on-call holder factory, payload opener/hash and loader prove pure metadata validation uses no placeholder context or self-pinning read.
- `test_private_v3_owner_passes_complete_independent_requirements`: recording fake context sees exact tuple roots/five pins from the job, not manifest-derived expected values, with the original runtime deadline. A missing live-layout helper/config/prefix fails before engine-loader call.
- `test_private_v3_engine_loader_returns_opener`: factory called once after handle entry; returned opener receives the existing core's arguments. Real loader/native model imports are prohibited in this test.
- `test_owner_outcome_and_failure_versions_selected_before_write`: authored V2/V3 success/failure cases assert correct returned schema and first-written failure bytes; V2 golden canonical bytes remain identical, no file rewritten after return. Close failure cannot return recorded and preserves existing failure bytes.
- Shared-helper test `test_pin_requirements_validator_is_pure_copied_and_zero_byte_eligible`: exact five keys, existing path/descriptor bounds, independent deep copy; neither holder construction nor filesystem/hash call is reachable.

Add Task 3 tests `test_v4_frozen_roots_equal_job_requirements`, `test_v4_parent_and_child_check_their_own_layout`, and `test_v4_added_requirements_copies_count_in_combined_metadata`. Metadata/real-entry tests must assert no actual payload opens and continued closed V4 execution. Private tests use authored fake contexts/engines and, only where real file custody must be exercised, explicitly named authored files or selected named source copies in temporary roots. Never census/hash the installed interpreter/site-packages, actual model/raw/SNP/graph/checkpoint/data, or arbitrary tracked files to make a fixture pass.

No tests were run for this amendment. Root reviewed and adopted these finite source interfaces before Task 2. The amendment approves no actual input, backend or execution.
