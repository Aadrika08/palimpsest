# Independent Task 1 review

Spec: **FAIL**. Code/architecture: **CHANGES REQUESTED**.

Reviewed local HEAD `a2b8c4451d3aced2e6f980ebe55d4f098a876d77`, base `9edfd5b38f14f0f8137404f0cedd80a7e5d78d18`. The binding input was `task-1-brief.md`, read first and completely. Review scope is the two new Task 1 files, the supplied Task 1 report, and the named unchanged custody/alias helpers necessary to assess their reuse. The changes requested below concern the prototype's own contract; neither requests a real backend, actual adoption, execution, or scientific qualification.

## Findings

### Important 1: RuntimeReference inherits the wrong serialized byte ceiling

Location: `scripts/memory_source_runtime_closure_v1.py:226` (`_bounded_encoding(result, 'charge_reference')`; function begins at line 215).

Trigger: provide the exact RuntimeReference schema with three disjoint metadata paths of 3024, 3026, and 3024 UTF-8 bytes. Each is canonical, below 4096 bytes, and composed of components below 255 bytes. The resulting canonical reference is 9648 bytes. All three descriptors retain positive sizes within their respective recipe/manifest/ledger limits and valid lowercase hashes.

Observed impact: `validate_runtime_reference` raises `ValueError: JSON byte bound exceeded`. Consequently every public validator and holder rejects this otherwise permitted reference. The binding profile assigns the 8192-byte ceiling to **Inline cumulative charge reference**, not RuntimeReference. This adds an undocumented restriction to valid metadata path combinations; it is a false refusal, not an authority escape.

Minimal fix: stop applying the cumulative-charge serialization budget to RuntimeReference. Its exact schema, bounded paths, bounded descriptor integers and fixed strings already provide a finite derived bound. If an explicit reference serialization guard is desired, derive it from those existing bounds rather than introduce a new policy ceiling. Keep the 8192-byte guard for `_charge`. Add a pure reference regression using multiple long valid paths and retain path one-over refusals.

### Important 2: Public handle accounting accepts absent required prior bindings

Location: `scripts/memory_source_runtime_closure_v1.py:705-710`, delegating to the optional-prior branch at lines 392-395.

Trigger: enter an otherwise valid authored holder, then call `held.accounting(prior_charge_reference=None, prior_cpu=None)`.

Observed impact: the method returns the normal five-field accounting result and the handle remains usable. This bypasses both required supplied-prior identity/float matching and fixed-allocation checking in this public API. The brief expressly permits both absent only for child-side pure ledger validation; `RuntimeHandle.accounting` takes required dictionaries and promises to check the supplied cumulative reference/prior float match. The result still correctly reports `accounting_authority_qualified: false`, so this is not evidence of an actual execution-admission bypass.

Minimal fix: reject absent/non-dictionary arguments inside the method's poisoning `try` before delegating. Keep the pure ledger validator's documented both-absent child behavior. Add an authored holder regression asserting refusal and poison after `(None, None)`; retain valid supplied-pair coverage.

No Critical findings. No additional Minor findings are requested.

## Evidence and checks

One new, narrowly targeted probe was authored and run in the ignored `task-1-review-fixtures/` directory next to this report. `probe.py` uses the existing authored fixture helpers and the new helper only; it creates tiny review-owned bytes. The retained `probe.log` records:

```text
reference path byte lengths: [3024, 3026, 3024]
canonical reference bytes: 9648
valid-path reference refused: JSON byte bound exceeded
accounting with absent required bindings: {'runtime_input_bytes': 1, 'external_input_bytes': 5330, 'project_cpu_ns': 11, 'memory_cpu_ns': 7, 'accounting_authority_qualified': False}
handle remains active: True
```

Command (exit 0; this is a successful reproduction, not a passing regression test):

```bash
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B .superpowers/sdd/runtime-reference-v1-implementation/task-1-review-fixtures/probe.py
```

Read the retained final focused log (`38 passed in 17.21s`) and reused-custody log (`11 passed, 10 deselected in 0.07s`). These are existing implementation evidence, not independent reruns. The report retains genuine missing-helper and subsequent regression reds, and distinguishes the corrected upward-float and teardown test expectations from implementation failures. No old or full suite was rerun.

`git diff --stat 9edfd5b..a2b8c44` shows only the new helper and new test file. Read-only `git diff --exit-code` checks confirmed the two owned files match HEAD and the three named reused sources (`puck_execution_files.py`, `puck_retained_installation.py`, `qualify_memory_family_source_v2.py`) match the base. No source, index, HEAD, or remote state was changed by this review.

## Satisfied parts and architecture assessment

- The literal profile is immutable and explicitly proposed. Existing per-holder policy and constructors remain unchanged; the new adapter passes explicit aggregate limits directly to `_HeldFileCore`.
- Actual bytes are length/hash checked, preflight bounds nesting/node tokens before parsed-container allocation, and canonical encoding, duplicate keys, Unicode, finite numeric values, exact fields and integer/bool distinctions are checked. Metadata file copying is capped by validated descriptors before reading.
- File, root, census and regular-input byte sums are global and include selected root directories. Empty complete roots remain held. Semantic pins must equal runtime records and do not add physical charges. Root/standalone/metadata/evidence overlap checks and directory topology are explicit.
- The declared recipe/manifest/ledger graph is noncircular. Ledger own size is charged only through its outer descriptor; distinct described paths contribute physical copies. Baseline/operation sums, operation IDs, reused evidence paths, integer limits, exact upward binary64 conversion and positive zero have substantive checks. All accounting results remain unqualified.
- Full directory identity is used at/below selected roots; only ancestor edge identity is used above them. Complete namespaces reject unexpected entries/types. File custody rejects hardlinks and inode aliases across metadata and runtime/evidence holders. The existing explicit Python alias-chain exception is preserved without allowing selected-tree symlinks.
- Acquisition/read/hash/census/recheck paths retain the absolute deadline and callback; failure releases tracked FDs and poisons the handle. Final recheck precedes release; close failures remain failures. Public descriptor/results are copies, and fixed summary/accounting fields do not export an FD map or runtime roster. Qualification/execution flags remain false.

## Verification limits and declined scope

This is a source/API review plus one tiny authored reproduction. It does not verify real large-input hold feasibility, FD/RSS/time fit, actual 1 MiB attempt metadata fit, full 640 MiB output fit, artifact preparation chronology, accounting authenticity/completeness or publication tails, loader/native safety, source/runtime/scientific qualification, or actual B adoption. Those limitations are explicitly acknowledged in the implementation report and are not additional Task 1 defects. Required actual executing layout/pins are caller integration obligations for later tasks; no owner/parent dispatch is implemented here.

No actual runtime/model/graph/raw/SNP/checkpoint/catalog payload was read, hashed, or imported; no native owner, service, network, operational probe, broad tracked-file hashing, cleanup, subagent, source edit, or GitHub action was performed. Only this ignored review report and its ignored authored reproduction files were written. No working-set binding/tool was available in this reviewer context.
