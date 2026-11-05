# Task 1 report: prospective source-runtime reference primitives

Implemented only `scripts/memory_source_runtime_closure_v1.py` and `tests/test_memory_source_runtime_closure_v1.py`. No Task 2/3 dispatch, loader, generator, registration, instrumentation framework, installation preparation or operational probe was implemented. This report is ignored supporting evidence; it is not in the owned-code commit.

Base: `9edfd5b38f14f0f8137404f0cedd80a7e5d78d18`, branch `research/source-cpu-compat-v1`, worktree `/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite`.

`PROFILE` is an immutable flat `MappingProxyType`; use `dict(PROFILE)` for JSON serialization. Its identifier is `memory-source-runtime-profile-v1-proposed`; canonical SHA-256 is `24b40536c06d44a748a3a948158ea2a0c24c75892c763317084052f0a2902bc1`. This policy is prospective and unqualified.

## Mechanism and authority boundary

The pure validators enforce closed canonical UTF-8 JSON schemas, actual supplied byte hashes, duplicate/noncanonical/unknown-field refusals, bounded structure, path/type/size/count coverage, exact repeated semantic pins, and the recipe → manifest → declared completed external ledger DAG. Supplied manifest dicts are schema-validated again when used by recipe/ledger validators; streaming bounded canonical encoding avoids creating an unlimited reconstruction first. Byte preflight limits nesting/nodes before parsed-container allocation. Pure validators use no filesystem IO and return independent normalized copies/results.

Runtime regular-file and census totals are global: 32768 files, 60000 census entries including each selected root, 16 GiB runtime input bytes, 2 GiB per regular file and 16 MiB manifest. Repeated identical semantic pins do not create charges. Different evidence paths represent additional physical copies, including equal-content files. Metadata and evidence storage enter external described input accounting in addition to runtime bytes; the ledger's own final size comes only from its outer descriptor.

The local `_SourceNamespaceFiles` adapter supplies new explicit limits to unchanged `_HeldFileCore`. It does not call the old 3 GiB `HeldInstalledFiles` constructor. One aggregate runtime/evidence holder plus the already-open metadata holder preserve complete selected directories, exact names/types, full identity at/below selected roots, edge-only ancestor identity, aliases, and current bytes. Empty selected roots stay held/censused. Metadata is held and hashed before parsing. Partial acquisition and parse/custody/close failures poison the public handle and release all tracked FDs. Recheck retains the original absolute deadline and callback. Final recheck precedes release. Python alias handling locally preserves the existing explicit alias-chain semantics; it grants no selected-tree symlink allowance.

Accounting validates baseline plus unique completed/failed operation charges, exact cumulative evidence identity/totals, physical described byte sums, exact least-upward binary64 prior seconds using integer ratios, positive zero, and fixed 1800-second integer lane admission. Summaries and accounting outputs have fixed fields and stay below 2048 canonical bytes; no roster or FD map is emitted. Every accounting result has `accounting_authority_qualified: false`; current-byte summaries always have `runtime_qualified`, `source_qualified`, and `execution_authorized` false.

## Genuine red/green evidence

All retained logs are below `runs/runtime-reference-task1/`. Fixture trees in runs using `--basetemp` are preserved. No cleanup occurred.

The first run preceded the new helper and genuinely failed on `new source-runtime helper is absent`, 18 failures. Its command was:

```bash
env PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q \
  tests/test_memory_source_runtime_closure_v1.py
```

Output: `runs/runtime-reference-task1/red-5WGx68/pytest.log` (`18 failed in 0.35s`). Initial helper absence meant that default pytest temp paths contained no authored runtime fixture payload from these tests.

Intermediate commands used the same first environment and test file, plus the indicated unique `--basetemp=.../fixtures`:

| Run directory | Selection | Actual result |
| --- | --- | --- |
| `green-attempt-6Kz88c` | all | 3 failed, 15 passed in 2.54s |
| `edge-red-sKSKt9` | all | 3 failed, 30 passed in 2.65s |
| `evidence-red-Wg6EN1` | `-k 'ancestor_metadata or never_schema or zero_byte_evidence or global_inode'` | 3 failed, 2 passed, 29 deselected in 0.17s |
| `green-SJXXMe` | all | 34 passed in 4.58s |

The first intermediate failures exposed authored expectation mistakes: both 11 ns and 7 ns nearest floats are below their exact rationals, and a caught custody failure must still refuse normal context exit. Tests were corrected to independently checked next-binary64 hex literals and failing teardown, rather than changing correct production behavior. A later cross-alias fixture mistakenly assigned into a tuple; that fixture error was corrected and its targeted case then passed. The preserved red logs include these mistakes rather than representing them as production failures.

The remaining runs used this fully clean environment prefix:

```bash
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 \
  VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 \
  /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q
```

| Run directory | Arguments after clean environment prefix | Actual result |
| --- | --- | --- |
| `bounds-red-orpFoa` | `tests/test_memory_source_runtime_closure_v1.py -k 'actual_manifest or standalone_file_ancestor' --basetemp=runs/runtime-reference-task1/bounds-red-orpFoa/fixtures` | 1 failed, 1 passed, 34 deselected in 9.30s |
| `focused-green-ZRi0Vb` | `tests/test_memory_source_runtime_closure_v1.py --basetemp=runs/runtime-reference-task1/focused-green-ZRi0Vb/fixtures` | 36 passed in 13.64s |
| `review-red-6Tq0H4` | `tests/test_memory_source_runtime_closure_v1.py -k 'lexically_interposed or combined_absolute' --basetemp=runs/runtime-reference-task1/review-red-6Tq0H4/fixtures` | 2 failed, 36 deselected in 0.11s |
| `final-green-bEb4mC` | `tests/test_memory_source_runtime_closure_v1.py --basetemp=runs/runtime-reference-task1/final-green-bEb4mC/fixtures` | 38 passed in 17.21s |
| `reused-custody-green-6EFr3g` | `tests/test_puck_retained_installation.py -k 'exact_empty_directory or current_namespace_changes or file_and_time_limits or unrelated_sibling_membership or redirected_ancestor or public_collection_ancestor' --basetemp=runs/runtime-reference-task1/reused-custody-green-6EFr3g/fixtures` | 11 passed, 10 deselected in 0.07s |

Each run's full output is its `pytest.log`. `stat -f -c '%T' scripts/memory_source_runtime_closure_v1.py runs/runtime-reference-task1` reported `btrfs` for source and retained fixture/log storage. No bwrap override was necessary; these runs encountered no EDQUOT.

Boundary fixtures include 32768 regular-file records / 60000 census entries and one-over rejection, a genuine exact 16 MiB canonical manifest with one-over rejection, 16 GiB global runtime metadata eligibility, zero-byte files/evidence, >3 GiB aggregate constructor metadata eligibility without hold/read, positive-zero and exact integer lane limits. Large fixtures are authored metadata only, not huge file payloads. Held filesystem fixtures contain authored tiny bytes. Tests never read/hash actual runtime/model/graph/raw/SNP/checkpoint/catalog payloads or import a native owner. `/proc/self/fd` use is limited to test-local FD-leak assertions.

## Separate self-review and unchanged-source evidence

The API/accounting/custody self-review was a separate pass after initial green. It identified and reproduced genuine additional failures before their narrow fixes: nested metadata paths; ledger acceptance of a manifest that had not passed schema validation; an unjustified nonzero-evidence restriction; standalone regular-file ancestor paths; an intervening lexical sibling hiding an ancestor; and combined root-relative absolute paths exceeding the total path byte limit. All regression cases pass in the final focused run.

Explicit byte hashes were taken only for the two owned files and these three named reused/derived source helpers. No tracked-file traversal or payload hashing was used.

| File | SHA-256 |
| --- | --- |
| `scripts/memory_source_runtime_closure_v1.py` | `761276c928b6864b6ec760a99fb0b5d0889dc8198db90bbfdb8e32476466105f` |
| `tests/test_memory_source_runtime_closure_v1.py` | `d2ebc67d7fab657f183489c26a1b826109972e3af35191ea268012156a3a455e` |
| `src/palimpsest/puck_execution_files.py` | `ac059455bc45437c45330d01aaca761fd571d6de1637a4a8d7ebfbd796622062` |
| `src/palimpsest/puck_retained_installation.py` | `b5e202d37cf8e8155295b607d5daa4dcaa3869cbeda3871cefdf00d2b159fdcc` |
| `scripts/qualify_memory_family_source_v2.py` | `1117434d577fa3bcacdaef6c985850fd7c4798dab56e031b3f661b6fd3b2cc50` |

Each reused-source hash equals the hash of `git show 9edfd5b:<that exact path>`. `git diff --exit-code 9edfd5b -- src/palimpsest/puck_execution_files.py src/palimpsest/puck_retained_installation.py scripts/qualify_memory_family_source_v2.py` passed. The old constructor's 4 GiB refusal is also tested behaviorally. No existing Puck source/pin/profile, owner/parent/numeric format or CPU-compat code is modified. The final staged `git diff --cached --check` initially found one trailing space in a test; that whitespace-only issue was removed, and the staged check then passed. The owned hashes above describe the final staged files; final green test behavior is unchanged by that trailing-space removal. Root-owned untracked `docs/reports/source-lifetime-static-2026-11-06/` remains untouched.

## Limits and uncertainty

This is authored software evidence only. No actual runtime closure, large-input hold feasibility, FD/time/RSS fit, 1 MiB attempt-metadata fit, 640 MiB attempt-output fit, preparation completion/authenticity, lifetime CPU reconciliation, physical immutability, native/source qualification, exact-stage GO, research/study acceptance or pruning authority follows from these results. The external collector, loader/startup safety and nonoverlapping accounting cut remain UNQUALIFIED/unresolved. No ledger publication-tail or recursive supplement was manufactured. A retained completed label and true current-byte check do not authenticate history or authorize loading.

The code does not establish when input metadata was prepared; it supplies no stage-created metadata exemption or prospective B adoption. Actual B classification would still require separately completed immutable input artifacts predating source freeze, externally charged full bytes/copies and CPU/tails, and actual adoption approval. Existing old inline/reference pairing and execution routing are outside Task 1 and unchanged. Full-suite execution was deliberately excluded by the assigned Task 1 scope; only the focused file and justified nearest authored custody selection were run. No push, checkout, merge, PR186 mutation or protected operational action occurred.

Commit: `a2b8c4451d3aced2e6f980ebe55d4f098a876d77` (`feat(memory): add unqualified runtime reference custody`). Post-commit `git show --stat` confirms exactly the two owned new files; `git diff --exit-code HEAD -- <the two owned files>` passed. The three named reused-source diffs against base passed again. `git status --short` contains only root-owned untracked `docs/reports/source-lifetime-static-2026-11-06/`. No push occurred.

## Review fix round 1 — base a2b8c44

Read the complete independent `task-1-review.md` before changing code. Its two Important findings were confirmed against the implementation. This fix round addresses only those two findings; independent scoped rereview is still pending.

1. Removed `_bounded_encoding(result, 'charge_reference')` from `validate_runtime_reference`. RuntimeReference is bounded by its exact schema, fixed IDs/enums, three canonical 4096-byte paths, bounded descriptor integers and fixed digests. It receives no new arbitrary serialization ceiling and the profile/hash does not change. `_charge` retains the specified 8192-byte cumulative-charge bound. New pure regressions use three disjoint paths of exactly 4096 UTF-8 bytes each, including a quote-rich legal path variant whose canonical JSON exceeds 16384 bytes. Both variants retain 4097-byte path refusal and normalized-copy independence.
2. Added an exact dictionary-type guard for supplied prior reference/CPU arguments inside `RuntimeHandle.accounting`'s poisoning `try`, before delegation/recheck. `(None, None)`, one absent value and list-valued arguments refuse, poison further operations, refuse successful context exit and close all held FDs. The pure ledger validator's explicit `(None, None)` child mode is unchanged and has a separate regression. Existing valid supplied-pair tests still run.

Production diff against `a2b8c44`: one removed reference encoding call and two added handle guard lines. No profile, source policy, backend, protocol, old holder or authority flag changed. The test diff adds eight cases, retaining all prior 38 cases. No real payloads were used.

Genuine full-file red, before these production edits:

```bash
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_source_runtime_closure_v1.py --basetemp=runs/runtime-reference-task1/fix1-red-qsLU7V/fixtures
```

Retained `runs/runtime-reference-task1/fix1-red-qsLU7V/pytest.log`: **3 failed, 43 passed in 17.02s**. Both legal long-path variants failed on the incorrect charge-reference byte guard; `(None, None)` failed to raise from handle accounting. The remaining old/new cases passed. These are genuine implementation regression failures, with no fixture/expectation errors in this round.

Full-file green after the minimal fix:

```bash
env -i HOME=/home/utkarsh PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 BLIS_NUM_THREADS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_source_runtime_closure_v1.py --basetemp=runs/runtime-reference-task1/fix1-green-hN8UWw/fixtures
```

Retained `runs/runtime-reference-task1/fix1-green-hN8UWw/pytest.log`: **46 passed in 18.37s**. Source/test and authored fixture/log storage remain Btrfs; fixtures and logs were preserved without cleanup. The shared venv alias and `-B` were used with a clean environment and every named thread limit set to one. No bwrap or operational probe was needed. The unchanged old 11-test custody result was not rerun, per this round's scope. No full suite was run.

Separate self-review inspected the exact three-line production diff and all added regression cases. The guard is inside the existing poisoning path, pure child mode is untouched, there is no replacement reference cap, `_charge` still owns its 8192-byte bound and all original profile literals remain unchanged. `git diff --check` passed. Read-only `git diff --exit-code 9edfd5b -- src/palimpsest/puck_execution_files.py src/palimpsest/puck_retained_installation.py scripts/qualify_memory_family_source_v2.py` passed again; the earlier named reused-source hashes remain applicable. Only these two owned source/test files were hashed in this round:

| File | Fix round 1 SHA-256 |
| --- | --- |
| `scripts/memory_source_runtime_closure_v1.py` | `0f3a5b31df75c5cdf2a95f287ebb9ea567126c34530e5d172c5b8c61ce04fd20` |
| `tests/test_memory_source_runtime_closure_v1.py` | `e62d77051f1c785f72fc6539cf2bee51c1ab8ec2a2712608789e3999c0c2d3aa` |

All earlier unqualified-backend, execution, chronology, actual B adoption, large-input feasibility, metadata fit and scientific limitations still apply. No new authority or actual source prototype completion is claimed. Root-owned lifetime documentation remains untouched and untracked. No push, native/source payload access, broad hashing, subagent, cleanup or protected operational action occurred.

Fix round 1 commit: `00e9ae33b10db8ca603abeeb758b20a2d9ac5e2c` (`fix(memory): enforce runtime reference accounting contract`). Post-commit readback confirms exactly the two owned files and no owned working-tree modifications. The three named reused-source diffs against base still pass. `git status --short` lists only root-owned untracked lifetime documentation. Scoped independent rereview remains next; no push occurred.
