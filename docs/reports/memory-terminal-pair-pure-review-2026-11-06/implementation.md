# Task5a implementation report

Implemented conditional pure pair proof only against clean base `aeb27496d6b397ee4019df74e0a9c288c82cfe5e` and the accepted 159-line tracked contract `docs/reports/memory-terminal-pair-contract-2026-11-06/contract.md`. Owned source/test files only; no existing source, helper, fixture, profile, pin, plan or ledger was edited. Root owns independent review.

## Implementation and self-review

`scripts/memory_family_terminal_condition_vnext.py` is 76 lines with one API, `prove_pair_vnext(source, condition, *, context, terminal_proof, deadline)`.

It validates exact outer dictionaries, Context, decoded representations and deadlines; validates both history E/U values; independently calls `memory.fit(e)` and compares canonical complete U; binds exact canonical history bytes via descriptors with the inherited 16 MiB bound; checks differing history paths and disjoint complete historical entity/evidence IDs. It constructs each exact registered nine-way selector/U mapping and checks complete bodies, including pending oracle syntax and acyclic provenance. It calls existing `audit.prove_terminal_vnext` directly with the original full source application/events/raw NumPy rows and original condition dictionary, compares every canonical byte of the fresh proof, copies the specified endpoint fields (only row_count renamed), bounds the detached result at 1 MiB and rechecks deadline. No second transition audit, score/path/goal formula, numeric projection, class, loader, CLI, family API, actual adapter or success/status authority flags were added.

Self-review checked direct raw-object forwarding, no input mutation, detached return references, exact serialization choice, no new resource/source backedges, both history refits even for conditions that use neither history, all nine mapping formulas, direct fresh whole-proof equality and no I/O/model/native/Engine operations inside the API. Staged whitespace check is recorded separately below. The source implementation did not need a correction after its first implementation; the intermediate failure below was a test's wrong choice of oracle for a source-application hash mutation.

## Authored source evidence and boundaries

Two genuine positives use unchanged 6a.1 `authored()` and `_open_authored_source_vnext` through its real lease helper, real authored source FDs/decoding, detached held Context/application/events/rows and `held.recheck()` before and after pair use. Both freeze the exact condition resources in the admission edit before opening. Own uses its refitted own history. Zero oracle uses proper empty-v1 U with its original pending selector provenance. New condition W/C are produced by real configure/arm/advance/inspect transition calls under the exact held Context and the existing Task3a worker/persistence event pattern; no old witness or receipt hash is relabeled. Each held test asserts exact Context equality, reaches the yielded holder and preserves all source/condition/history value digests.

For zero only, a test-local wrapper calls the unchanged source `_acquire` fixture and changes its returned final projected next_pose to finite within-arena `[6., 6., 0.]` before `authored()` constructs any raw row or serializes raw/numeric/events/SNP. Every downstream source representation/commitment is produced normally from that authored value. Root explicitly accepted this precise test-only transform. No source guard, stat witness, source auditor, production primitive, live held source, actual/native/physical source state or previously serialized evidence is patched. The actual pure worker naturally raises without a motor row; zero result retains null motor interval, path 0., goal false and capped 900.

Other mapping/refit/forgery tests use detached conditional source values from existing Task3a generic fixtures and newly generate condition evidence. They do not claim held-source admission or registration. Tests cover natural 1/2-row failures, post-trigger selection with a local raised cut and no commit for both nonempty change and empty null gold, pre-trigger/world-applied pending oracle, and no-event pending oracle. The no-event ordinary decision test permits decision_reached=true while proving no trigger/world application, no oracle stages/gold/selection and no selector/resolver invocation. All proof fields are forged independently; endpoint and reached-flag forgeries also span all nine slots. Mapping negatives rebind Context/config and manifest descriptors so stale hashes do not supply the mapping refusal; source/hash/retained/relabel negatives assert both fresh replay and its source checker entered. Exact outer fields, bad history bytes/refit/roles/alias/ID overlap, bool counters, opaque arrays without conversion hooks, deadline refusal, post-replay timeout, no I/O and output/input nonmutation are covered.

No actual record/payload/checkpoint/model/native restore/physics/replay/Engine owner, public actual source factory, admission/qualification/publication, real history acquisition/registration/donor independence or cross-condition equality was established. No research/probe/network/service/dependency/CI/push/deletion/all-tracked hashing occurred. Unchanged3a/6a.1 accepted suites were not rerun. Ordinary authored tests are excluded from research CPU; no new research debit, whole-CPU/upper-bound claim or feasibility claim. Raw deletion remains disabled; pending source03/provider approval, full 48 development + 48 held-out x 3 kinds x 9 conditions and separate GO remain unchanged. First-party account quota signal unavailable in this child: quota unknown.

## Exact commands and retained raw logs

Every pytest command ran serially from `/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite` with this exact prefix:

```text
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest
```

Each command's stdout/stderr was redirected with `> .superpowers/sdd/memory-terminal-vnext-implementation/task-5a-evidence/<log> 2>&1`.

1. RED suffix: `tests/test_memory_family_terminal_condition_vnext.py -q -x --basetemp=/var/tmp/palimpsest-task5a-red-20261106-01`; `red-01.log`; exit 1; 1 failed in 0.44s. Genuine missing required Task5a module/API before source implementation.
2. Initial mapping/cut suffix: `tests/test_memory_family_terminal_condition_vnext.py -q -x -k 'all_nine or natural_short' --basetemp=/var/tmp/palimpsest-task5a-focus-20261106-02`; `focus-02.log`; exit 0; 14 passed, 91 deselected in 7.31s.
3. Real FD suffix: `tests/test_memory_family_terminal_condition_vnext.py -q -x -k real_authored --basetemp=/var/tmp/palimpsest-task5a-fd-20261106-03`; `fd-03.log`; exit 0; 2 passed, 103 deselected in 2.10s. Initial zero authored pose [100,100,0] was subsequently replaced by within-arena [6,6,0]; subsequent negative wave and final both passed that final geometry.
4. Negative wave suffix: `tests/test_memory_family_terminal_condition_vnext.py -q -x -k 'not all_nine' --basetemp=/var/tmp/palimpsest-task5a-neg-20261106-04`; `neg-04.log`; exit 1; 1 failed, 85 passed, 9 deselected in 25.87s. Test incorrectly expected a mutated oracle source_application hash to enter3a although pending provenance correctly caused earlier mapping refusal. Test corrected to own, fully rebound manifest/Context and asserted actual replay/source entry; no source code change. No infrastructure/ancestor/quota exception was treated as a semantic negative.
5. Focused correction/edge suffix: `tests/test_memory_family_terminal_condition_vnext.py -q -x -k 'source_bindings or exact_outer or no_event_ordinary or deadline_rechecked or bool_selector or unused_histories or opaque_arrays or original_raw' --basetemp=/var/tmp/palimpsest-task5a-focus-20261106-05`; `focus-05.log`; exit 0; 42 passed, 99 deselected in 9.97s.
6. Settled FINAL, new pair file only, once: `tests/test_memory_family_terminal_condition_vnext.py -q --basetemp=/var/tmp/palimpsest-task5a-final-20261106-06`; `final-06.log`; exit 0; **159 passed in 48.56s**, no skips/deselections. No broader suite or retry for green.

All six /var/tmp basetemps and all logs retained; no remove/prune/cleanup. Newly authored physical fixture roots retained:

- FD03 own: `/var/tmp/palimpsest-AUTHORED-source-vnext-1000-af62c17c-b5fb-45ab-8239-1f672636c90f`
- FD03 zero: `/var/tmp/palimpsest-AUTHORED-source-vnext-1000-896376eb-83ba-483e-9665-8a732e3dfd2b`
- NEG04 own: `/var/tmp/palimpsest-AUTHORED-source-vnext-1000-80ecf081-cebc-4b8f-8c71-e51424e34dfe`
- NEG04 zero: `/var/tmp/palimpsest-AUTHORED-source-vnext-1000-cdf4aeaa-2e0f-4834-bfcf-cb3dc6412e4b`
- FINAL06 own: `/var/tmp/palimpsest-AUTHORED-source-vnext-1000-d70663c2-9bdf-4934-a6e7-5ca302c98648`
- FINAL06 zero: `/var/tmp/palimpsest-AUTHORED-source-vnext-1000-4a4890ec-1f93-4f7e-ada0-101636ec802f`

Condition values/W/C are authored in-memory fixtures, not published or fabricated actual recording containers. Source FD files above are authored-only and retain their original claims=false semantics. No infrastructure failure or skip occurred. Concern/remaining gate: independent root-owned spec/code review remains required; this proof cannot establish history origin/registration, cross-condition identity/equality, actual acquisition, job-body custody, physics/model equality or physical ledger completeness.

## Commit and postchecks

Authorized commit: `8b1ed1d` (`feat(memory): prove conditional terminal pair mappings`). `git diff --cached --check` passed before commit; staged names were exactly the two owned paths. Commit contains exactly those two new files, 585 inserted lines (76 source, 509 tests). `git diff HEAD^ HEAD --check` passed after commit, and `git status --short` was empty. Full commit ID recorded in the parent handoff. No push or CI invocation.
