# Task6a.1 fixed authored source holder — implementation report

Implementation covers the five root-authorized files after the concrete nested-close contract repair. **Settled five-file verification:208passed,2historical frozen-pin skips in37.95s,exit0,zero failures/warnings.** The earlier corrected holder-only result was92passed28.88s before primitive changes. Commit **9d2b88779e586328c76ddf76e105ff16e2256cec**. Final self-review/commit readback confirmed only the five authorized files are in this commit; their working-tree diff is empty. Root-authored docs remain outside the commit. Independent specification/code review remains root-owned and has not occurred. This does not complete6a, actual admission, integration or qualification.

## Binding scope and changes

Base HEAD verified44e08d1, branch research/memory-vnext-spec-v1. Initially scripts/memory_family_source_consumer_vnext.py and tests/test_memory_family_source_consumer_vnext.py were owned. Root subsequently authorized scripts/memory_family_compact_v4.py and scripts/memory_family_replay_custody_v4.py for FD-drain/error-preservation only, plus tests/test_memory_family_replay_custody_v4.py for its one conflicting error-precedence assertion. These five files are the entire implementer-owned tracked deliverable. Reports/diffs/logs here are ignored evidence. Root-authored plan/profile/output-contract edits in the shared worktree were neither edited nor staged by this implementer.

Binding tracked contract: docs/reports/memory-terminal-custody-preflight-2026-11-06/authored-source-contract-addendum-var-tmp.md, plus root's authored-profile-byte-rule.md, authored-output-topology-rule.md and authored-nested-fd-drain-rule.md (including the explicit single existing-test correction ruling). The initial /tmp quota refusal caused a root-reviewed docs-only amendment to /var/tmp, not a quota/stat/cap waiver. Original /tmp fixtures and logs remain retained.

The sole factory is private `_open_authored_source_vnext(root, admission, *, case_id, deadline)`. It yields exact HeldSourceVnext through a private identity sentinel. There is no public actual factory, summary factory, Engine integration, bind/rebind, caller checker/loader, arbitrary source class or positive authority flag.

The factory retains genuine compact.bound_payload metadata/bootstrap contexts while deriving the fixed record roster, then acquires exact HeldReplayFiles(exact_subtrees=('inputs',)) for all14+3P leaves. Admission is absent from its own13+3P inventory; it is independently bootstrap-held and also in the strong roster. Descriptor, schema, canonical authored metadata, cross-record identities, aliases, sole paths, counts, sizes, hashes, physical/logical aggregate ceilings and inventories are checked. Seven software-closure requirement subjects remain descriptor-only: the consumer never opens or qualifies them.

SNP preflight bounds physical/stored expansion bytes, metadata, archive entries and typed nodes; enforces duplicate/unknown/path/reference/ZIP rules and exact ZIP end framing before unchanged snapshots.read_snapshot. The authored decoded root and typed value bound are checked separately. Native bytes stay opaque. NPZ role caps are computed from fixed shapes/counts and ZIP/NPY framing before bounded guarded-FD reads. Unchanged 4a `_read_arrays` verifies exact headers/schema/canonical reencoding; every16 base +3 extra value and selected frame matches held raw bytes exactly. Raw audit hashes are independently recomputed.

Application/M/world/case and the immutable one-slot Context derive from the held SNP and records. Unchanged3a audit._source validates source rows/events/application and acquired boundary. configure_terminal_condition_vnext validates registered resources/schedule while terminal_source_view_vnext stays equal. Oracle pending provenance remains acyclic. Context.source_registration is the authored admission D, never an actual R.

Each property/recheck checks owner thread, active state, deadline, all strong file/absolute/input witnesses, retained bootstrap checks, fixed output witnesses and an immutable typed binding digest. Properties return deep detached copies, including arrays. Any failure poisons; close invalidates before resource release. Factory final recheck precedes invalidation; ExitStack wrappers preserve original body/decode errors and attach all visible exit failures as notes while draining every registered exit. Teardown-only failures raise infrastructure refusal.

Output-root acquisition occurs between strong rechecks. Owned root/outputs/condition directory FDs retain full custody._identity and named edges. Only work/atomic/quarantine branch edges use the specifically approved(dev,ino,mode,uid,gid) rule, allowing their descendant writes without weakening any input or absolute ancestor stat.

## Verification commands and custody of evidence

All pytest commands ran in this worktree with this exact common prefix:

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest
```

Each run used fresh unique retained basetemp and raw log; no pytest basetemp was reused. All raw logs below are under `.superpowers/sdd/memory-terminal-vnext-implementation/task-6a1-evidence/`. In the table, ID is the suffix used in both the log and basetemp.

| Log | Exact pytest arguments after prefix | Result |
| --- | --- | --- |
| red-20261106T110652184588371.log | tests/test_memory_family_source_consumer_vnext.py -q --basetemp=/tmp/task-6a1-red-20261106T110652184588371 |16failed1.07s:4 genuine missing-holder RED,12 real Errno122 fixture-write failures; no implementation then |
| red-20261106T110843596553089.log | tests/test_memory_family_source_consumer_vnext.py -q --basetemp=/var/tmp/task-6a1-red-20261106T110843596553089 |16 genuine missing-holder RED3.08s |
| green-20261106T111159720806711.log | tests/test_memory_family_source_consumer_vnext.py -q --basetemp=/var/tmp/task-6a1-green-20261106T111159720806711 |2failed14passed3.77s; positive/thread stopped at inherited profile canonical conflict; root clarification required |
| green-20261106T111305766674367.log | tests/test_memory_family_source_consumer_vnext.py -q --basetemp=/var/tmp/task-6a1-green-20261106T111305766674367 |2failed14passed4.60s; fixture scalar representation mismatch with prescribed NPZ decoding; fixed authored fixture to exact NumPy scalar types |
| green-20261106T111330026277158.log | tests/test_memory_family_source_consumer_vnext.py -q --basetemp=/var/tmp/task-6a1-green-20261106T111330026277158 |16passed6.06s; first real capability yield/closure |
| red-boundaries-20261106T111518580567306.log | tests/test_memory_family_source_consumer_vnext.py -q --basetemp=/var/tmp/task-6a1-red-boundaries-20261106T111518580567306 |1failed79passed27.08s,2 expected fixture ZIP-duplicate warnings; genuine SNP trailing-byte bug RED |
| green-boundaries-20261106T112559785157863.log | tests/test_memory_family_source_consumer_vnext.py -q --basetemp=/var/tmp/task-6a1-green-boundaries-20261106T112559785157863 |1failed79passed25.22s; no-event positive refused at real strong ancestor check; retained infrastructure failure, exact directory not identified in that older log |
| red-output-20261106T112635056612184.log | tests/test_memory_family_source_consumer_vnext.py -q -k output_ancestors --basetemp=/var/tmp/task-6a1-red-output-20261106T112635056612184 |4failed1passed80deselected2.90s; genuine missing output binding RED |
| green-output-20261106T112726197665838.log | tests/test_memory_family_source_consumer_vnext.py -q -k 'output_ancestors or real_authored_lease' --basetemp=/var/tmp/task-6a1-green-output-20261106T112726197665838 |8passed77deselected4.85s |
| final-20261106T113051810785239.log | tests/test_memory_family_source_consumer_vnext.py -q --basetemp=/var/tmp/task-6a1-final-20261106T113051810785239 |92passed29.84s,0skips/0warnings; prior full run, superseded by corrected final below |
| fd-precision-20261106T113425835966276.log | -q followed by the eight named nodes below, --basetemp=/var/tmp/task-6a1-fd-precision-20261106T113425835966276 |1failed21passed12.96s; absolute-parent node never yielded, underlying refusal swallowed by outer assertion then UnboundLocalError. Cause UNKNOWN; never classified passed or definitively infrastructure |
| corrected-final-20261106T113848234725187.log | tests/test_memory_family_source_consumer_vnext.py -q --basetemp=/var/tmp/task-6a1-corrected-final-20261106T113848234725187 |**92passed28.88s,0skips/0warnings,exit0**, after test assertion repair, no source changes |

The eight explicit FD precision nodes, each with `tests/test_memory_family_source_consumer_vnext.py::` prefix, were:

- test_real_authored_lease_derives_detached_context_and_closes_fds
- test_real_filesystem_mutation_permanently_poisons
- test_cross_thread_poison_and_original_body_error_survive
- test_real_deadline_expiry_is_permanent_and_closes_resources
- test_final_recheck_failure_refuses_and_closes_all_owned_fds
- test_multiple_teardown_faults_drain_every_real_context
- test_output_ancestors_and_precreated_branch_edges_remain_bound
- test_decode_error_remains_primary_through_multiple_real_context_exits

That run collected22 parameterized cases. `fd-precision-identity.json` retains AST identities for its eight changed and eleven unchanged test functions and confirms the production source stayed byte-identical to the prior92-test full run. The later corrected full92-test run executes the repaired assertions afresh and supersedes the partial proof; no non-covering test reuse is needed for final status. The holder source stayed unchanged through that correction. The later root-authorized shared primitive changes are validated by the settled run below; the earlier identity artifact does not attest to those later changes.

Root first narrowed final scope to the holder file, then authorized the holder plus existing replay-custody and compact pure suites because the concrete nested-close defect required shared primitive changes. No broad suite, qualification/source-launch tests, or transition/terminal audit/terminal numeric suites were rerun. No historical frozen-pin skip is counted as passing or newly executed evidence. `git diff --no-index --check /dev/null` on each owned file emitted no whitespace findings (difference exit1 is expected for new files). Source/test diff artifacts are retained here.

## Settled nested-drain verification

Raw log: `task-6a1-evidence/settled-close-20261106T114839014156420.log`. Exact arguments after the common environment/interpreter prefix:

```sh
-q -rs tests/test_memory_family_source_consumer_vnext.py tests/test_memory_family_replay_custody_v4.py tests/test_memory_family_compact_v4.py --basetemp=/var/tmp/task-6a1-settled-close-20261106T114839014156420
```

Result: **208passed,2skipped in37.95s,exit0**, zero failures/warnings. The new holder file contains112 cases (the previous92 plus20 internal-close cases); all execute in this run. The existing pure suites contribute96passes and2skips. The unchanged collection guard skipped exactly:

- tests/test_memory_family_compact_v4.py::test_protocol_is_canonical_and_freezes_exact_false_claim_contract
- tests/test_memory_family_compact_v4.py::test_protocol_binds_exact_present_sources_including_source_producer

The log reports historical `memory-family-compact-v4` source pin drift for compact_v4.py, oracle_admission_v4.py, producer_v4.py, retained_condition_v1.py and engine.py. The first file now also contains this authorized teardown-only correction; the other source files were untouched. These two skips are **lost historical coverage**, not passing qualification or evidence of source identity. No guard, pin, profile or original skipped assertion was edited/bypassed/repinned. The test import subprocess only verifies that the pure compact module does not import model/native/Engine modules; it does not launch an owner.

Self-review read the exact three tracked diffs and the new source/test files. Whitespace checks emitted no findings. Shared primitive changes are confined to drain/error precedence; the existing test change is confined to the single root-approved body-primary/drift assertion. Holder source hash remains501de64b6a91ffa421576904cda0efe5a06941ce077ff1a5c3709881c51ec471. No unresolved implementation concern was identified after the nested-close repair; independent review remains required.

## FD, lifetime and negative evidence

The final tests capture the baseline live `/proc/self/fd` set with real fstat filtering of transient listing FDs, compare the active set, union every exact strong `_files._fds` FD (including `/`, `/var`, `/var/tmp`) and every root-targeting FD, then demand actual OSError from fstat after teardown for every retained number. Strong FD sets are proved live and disjoint from baseline. `bound_payload` retains root and relative ancestors only, not extra absolute-ancestor FDs; those bootstrap FDs and fixed output FDs are included in the newly-live/root-targeting sets. No returned borrowed FD/fd_path is public.

All post-yield mutation, lifetime, tampering and body/teardown tests explicitly prove yield: fds starts None, outer rejection is retained, and a pre-yield refusal is rethrown with original traceback/notes. Semantic schema/value tests accept only ValueError. Initial missing-file and symlink-directory tests require FileNotFoundError and NotADirectoryError respectively; no generic RuntimeError/OSError absorbs unrelated setup/quota/stat failures. The lease test helper can read actual strong `_dirs` witnesses from an ancestor-error traceback and annotate changed paths/identities without patching any check.

Positive real files cover change/oracle, null/no-U and no-event/oracle, nonempty acquired source, original held SNP descriptor, exact Context derivation,16+3 equality, detached edits, allowed output descendant writes and stale refusal after closure. Real negatives cover bytes/replacement/parent/absolute-parent/input/output/branch changes, symlinks/hardlinks, wrong role/cap/namespace/aliases, unknown/missing schemas/keys/claims/actual-shaped flags, canonical UUID/case/resources/schedule/source mismatches, raw/base/extra/camera/frame differences, exact event/JSON/ZIP/NPY framing, combined metadata budget, SNP entry/metadata/typed-node bounds, empty source, thread/deadline, immutable binding tampering and final recheck failure.

Bounded deterministic fault injection wraps real compact contexts and the real strong exit: it raises only after each underlying real context has closed its FDs. Tests verify multiple exits still drain, teardown-only refusal, the identical original body error remains primary, and decode errors remain primary with teardown notes. No stat/recheck/guard patches, fake actual receipt, fake source authority, native/model/policy call, runtime owner or actual-shaped Q/L/R was used.

## Remaining concern and authority boundaries

The nested-close concern was confirmed and resolved through a root-authored scope amendment, not waived. `compact.bound_payload` now preserves the reached primary and attempts every owned descriptor close once, collecting all close failures. Strong custody cleanup does the same on entry/recheck/guard/read failures and at exit; incoming body errors remain primary while actual final recheck errors and close failures are attached. The one existing test which formerly required replacing an explicit body LookupError was updated by root instruction: it now asserts the same primary object, actual changed/differs recheck error/type in notes, unchanged FD count and stale refusal.

Twenty new internal fault cases use genuine bootstrap/strong contexts and real FDs. Injection performs the original os.close before raising on one or two close calls; tests prove each owned FD is attempted once, remaining closes proceed, fstat refuses all injected-real-closed descriptors, and entry/body/recheck/guard/read primary errors survive. Teardown-only faults refuse. Each post-yield case explicitly proves entry; entry-negative cases prove they never yielded. For a genuine kernel close failure the guarantee is complete attempted drain and explicit infrastructure reporting, not a fabricated closed-FD claim or blind retry. All path/hash/stat/cap/format/qualification semantics and frozen pins/guards/profiles remain unchanged.

Raw nested-close RED: close-red-20261106T114519521788567.log,19failed1passed4.25s. Command after common prefix: `-q tests/test_memory_family_source_consumer_vnext.py::test_internal_close_faults_attempt_all_real_fds_and_preserve_primary --basetemp=/var/tmp/task-6a1-close-red-20261106T114519521788567`.

Focused nested-close GREEN: close-green-20261106T114731774869986.log,21passed3.78s. Command after common prefix: `-q tests/test_memory_family_source_consumer_vnext.py::test_internal_close_faults_attempt_all_real_fds_and_preserve_primary tests/test_memory_family_replay_custody_v4.py::test_exit_drift_rechecked_without_replacing_body_error --basetemp=/var/tmp/task-6a1-close-green-20261106T114731774869986`. The20new cases plus the revised existing precedence test passed; the later settled run is authoritative for the final five-file state.


Strong absolute directory identity intentionally remains susceptible to real unrelated host ancestor mutations. A prior run did refuse this way; no stat fields, expected witnesses or caps were weakened and no test was skipped. Python sentinels and authored names are not hostile-process isolation, and current namespace agreement does not prove historical exclusive creation.

No actual factory/Engine opt-in/source owner/model/native restoration, actual producer authentication, source03/provider adoption, resource feasibility, whole-operation CPU accounting, full96-family study, paper completion, publication, allocation, GO or deletion authority follows. The full48development+48heldout x3kind x9condition objective remains incomplete. Whole-operation CPU and justified upper remain unknown; historical1222.455497s subtotal remains incomplete accounting. Memory12CPUh within project24CPUh, storage/census caps, source03 pending approval and separately explicit raw-deletion authorization remain unchanged. No cleanup, raw deletion, dependency, network, CI, service/probe or research run was performed.

## Commit/readback

Committed `9d2b88779e586328c76ddf76e105ff16e2256cec` (`feat(memory): hold fixed authored sources with complete custody drain`) on research/memory-vnext-spec-v1, parent44e08d1. Commit contains exactly the five authorized files,1386insertions/23deletions. Git cached whitespace check passed before commit; post-commit owned-file diff is empty. Only root-authored plan/contract files remain modified/untracked in the shared worktree. No push or independent review was performed.
