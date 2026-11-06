# Task 1 pure transition implementation report

Status: Task1 pure source implementation and final approved six-file checks complete; independent root spec/code review remains. Local commit `7f3c783868f8c878426e9ee02b44c86a125353c6` (`feat(memory): add proposed detached terminal transitions`). Worktree `/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite`, branch `research/memory-vnext-spec-v1`, base `0de8cc1e7e47bb29c86a859080433fb371cf929f`. Root owns the separate unstaged plan clarification; it is excluded from the four-file commit.

## Source scope

Only owned deliverables are changed: `src/palimpsest/memory_decision.py`, new `src/palimpsest/memory_transition_vnext.py`, new `tests/test_memory_transition_vnext.py`, new `docs/plans/memory-terminal-vnext-v1-protocol.json`. This ignored report and retained `task-1-evidence/` are the only authored supporting artifacts. No Engine, old protocol/pin, model/runtime, actual source/raw/SNP/catalog/interpreter payload, native service/probe/CI, dependency, publication or cleanup operation. No nested agents. Legacy test source imports read their existing named pure source identities; the proposed profile hashes only three explicitly named inherited JSON protocol files as immutable metadata. No new profile/source-closure self-pinning edge.

The legacy strict3 signatures/default path remain fixed. Factoring adds fixed private common field validation, acquired/arm/goal predicates and one worker; its only new branch accepts the exact private terminal builder class. No external sink/callback/policy/loader registry. All old public helpers reject4. New wrappers preserve the exact declared source projection before arm and only the existing supervisor schedule change during arm. The worker selects once at the original cut and captures actual local state/audit even when a later CueUnavailable prevents any returned-state assignment.

The proposed module supplies Context/Reach/record validation, strict4 lifecycle wrappers, immutable detached source data, fixed source-M resolver, stage hashes, detached result variants, opaque same-exception rethrow token, and exact bounded complete event encoding. It writes no journal, makes no commit, and authenticates no actual source/event authority. Unknown future owner state cannot be resumed through this pure record API; the later owner must stop after E/rejection.

## Root rulings carried into code/profile

- Source world is the existing validated state2, matching case, unarmed/applied-false, with last_tick=boundary-1. Before occupancy uses its fixed audit geometry **conditional on later held-source proof that actual acquired source placement equals the registered geometry**. State2 and binding constructors alone are not source authentication. Actual after circles must equal the one allowed realized edit; Task3 must independently authenticate event roles/bodies/placement.
- Reach contains only Ref sequence/hash, not event bodies. Task1 checks bounded shape, prior/distinct references, required roles, actual packet/trigger/schedule and circles; Task3 authenticates the complete actual raw/source events. No artificial trigger_tick==event_tick rule; delayed detection at decision is tested, late installation after decision refuses.
- Occupancy maps are nonnull only for oracle resolution in this transition. Nonoracle local trigger/selection, pretrigger/no-event, later terminal without new oracle resolution have both maps null; nonoracle receives no OracleBinding/evaluator lookup. Task3 independently reconstructs actual occupancy.
- Error is a fixed private frozen token containing the SAME original exception object, exact captured type identity and independent canonical projection bytes. Rethrow compares those bytes and any mutable Witness projection immediately before raising the original object; aligned witness/error mutation cannot bypass capture. No global registry or exception reconstruction.
- Review found legacy `_numbers` admitted `10**308` integer coordinates (309 JSON characters), contradicting the float64 coordinate bound, and tuple circles escaped ordinary no-witness admission. This was an implementation defect against the existing finite-float-triple spec, not a cap/policy failure. RED was retained; successor-only circles now require exact plain lists of three finite built-in floats and positive radius. Legacy `_numbers` is unchanged.
- Final cross-check found the initial serializer tests used a case_id envelope instead of Task2a's exact existing Engine envelope. That earlier writer equality was real but insufficient for the intended Engine contract; red-08 retains the missing episode-field failure. Root confirmed exact envelope `run_id,episode,tick,episode_step,sequence,kind,witness|commit`; episode is exact int0, tick and episode_step are exact ints0..2100 and both equal body.tick at the pre-motor cut. Corrected encoding rejects bool/range/mismatched counters and unknown extra keyword arguments. No case_id envelope field.
- Context metadata D<=1MiB (snapshot<=16MiB) is explicitly a **proposed wire maximum**, not a claim that every inherited role permits1MiB or six free metadata MiB. Later authentic source consumption must additionally preserve stricter existing per-role caps (e.g. numericV2 commit16KiB, conversion64KiB), shared overhead1MiB, and actual-role/epoch validation. Descriptor-only software closure is distinct from separately versioned runtime-reference manifests; Task6 is not inferred ready.

## TDD and retained commands/results

All pytest invocations used `/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B`, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH=src:scripts:tests`, `LC_ALL=C.UTF-8`, numerical thread vars1, `MUJOCO_GL=egl`, `CUDA_VISIBLE_DEVICES=''`. Beginning with red-03, `env -i PATH=/usr/bin:/bin` explicitly removes every inherited research opt-in. Earlier commands set the same listed environment without env-i; no research execution occurred. A single green-01 source-only diagnostic printed `rejected ValueError Fact estimate requires retained observed evidence`; it explained why the authored changed-live-M fixture needed valid uncertain status instead of invalid unknown/origin fields. This diagnostic touched no actual payload.

Every pytest call uses a fresh explicitly named `--basetemp=.superpowers/sdd/memory-terminal-vnext-implementation/task-1-evidence/<name>-temp`, retained log `<name>.log`, and stdout/stderr redirection. No occupied basetemp reused or old workspace removed. Existing test-internal transient actions are not claimed retained individually.

Command prefixes below are exact shell forms:

```
E1: PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest
E2: env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest
NEW: tests/test_memory_transition_vnext.py
LEGACY: tests/test_memory_decision.py tests/test_memory_task.py tests/test_memory_experiment.py tests/test_memory_decision_world.py tests/test_memory_world.py
```

Each row appends `--basetemp=.superpowers/sdd/memory-terminal-vnext-implementation/task-1-evidence/<name>-temp > .superpowers/sdd/memory-terminal-vnext-implementation/task-1-evidence/<name>.log 2>&1`; shell saved and returned pytest's exit status. Every available log is retained.

| Name | Exact arguments after prefix | Exit | Result / why |
|---|---|---:|---|
| red-01 | E1 `-q NEW` |1|23 failed,0.47s; intended missing-module failures before source implementation |
| green-01 | E1 `-q NEW` |1|3 failed/20 passed,4.40s; fixture U mismatch, invalid changed-live-M status/origin, oversized authored descriptor outside role cap; fixture corrections retained in source |
| green-02 | E1 `-q NEW LEGACY` |0|57 passed,7.44s |
| red-02 | E1 `-q NEW` |1|12 failed/26 passed,9.06s;11 real missing nested-record validation failures plus one authored deadline-loop end too early, corrected without changing worker policy |
| green-03 | E1 `-q NEW` |0|38 passed,9.04s |
| red-03 | E2 `-q NEW -k mutated_error` |1|1 failed/38 deselected,0.29s; intended missing fixed error-token capture |
| green-04 | E2 `-q NEW` |0|39 passed,9.03s |
| red-04 | E2 `-q NEW -k 'delayed_trigger or source_binding_refuses'` |1|5 failed/39 deselected,0.96s; missing late-install and acquired-source identity guards |
| green-05 | E2 `-q NEW LEGACY` |0|78 passed,12.86s |
| red-05 | E2 `-q NEW -k 'event_references or every_arm or terminal_sensed'` |1|1 failed/2 passed/44 deselected,2.11s; missing Ref-before-writer check; all-nine no-event and terminal fresh-sample checks already passed |
| red-06 | E2 `-q NEW -k malformed_nested` |1|2 failed/12 passed/35 deselected,2.51s; missing reconstructable selection-output/provenance commitment checks |
| green-06 | E2 `-q -s NEW` |0|49 passed,12.20s; earlier envelope size proof retained but superseded by exact Engine envelope correction |
| red-07 | E2 `-q NEW -k circles_require` |1|3 failed/2 passed/49 deselected,0.99s; integer/tuple circle counterexamples above |
| green-final-01 | E2 `-q -s NEW LEGACY` |0|88 passed,15.83s; earlier envelope-size assurance subsequently found incomplete; not the final intended-envelope gate |
| red-08 | E2 `-q NEW -k exact_engine_envelope` |1|1 failed/54 deselected,0.31s; intended missing exact Engine envelope interface |
| green-final-02 | E2 `-q -s NEW LEGACY` |0|95 passed,17.06s; exact Engine envelope correction and counter negatives |
| green-final-03 | E2 `-q -s NEW LEGACY` |0|95 passed,17.15s; final maximal selected-Lifecycle Commit measurement plus exact-envelope witness/Context category proof |

No warnings reported in these logs. No whole canonical suite, optional actual-model tests or native integrations were run. The root explicitly restricted the check wave to these six pure files.

## Final verification and bounds

Final exact command (exit0, **95 passed in17.15s**, no warnings reported):

```
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q -s tests/test_memory_transition_vnext.py tests/test_memory_decision.py tests/test_memory_task.py tests/test_memory_experiment.py tests/test_memory_decision_world.py tests/test_memory_world.py --basetemp=.superpowers/sdd/memory-terminal-vnext-implementation/task-1-evidence/green-final-03-temp > .superpowers/sdd/memory-terminal-vnext-implementation/task-1-evidence/green-final-03.log 2>&1
```

61 new authored cases plus34 approved legacy cases. They cover all five result variants, source-M/live-M distinction, one ordinary selector call, local selected-but-uncommitted exception effects, all nested alias/result isolation, exact four stage preimages, prior selection on later terminal, strict3/4 marker boundaries, source/configure/arm views, null resolved-empty versus no-event pending, all-nine no-event non-use/equality, idempotence, wrong packet digest/second/late trigger refusal, no-fresh-passage on terminal decision packet, index/Ref/record contradictions, original exception tamper and same-object rethrow, invalid descriptor/ID/float shapes, unknown generic-hook admission, and full actual writer escaping/envelope bytes.

Final authored maximum complete **exact Engine+RunWriter** event sizes:

- Witness12,244 bytes<=14,336 symbolic bound<16,384 proposed cap. Its verified categories are fixed text/envelope/newline/counters1,496, quoted hashes1,452, ASCII IDs1,572, complete20-circle JSON1,580 and exception escaped content6,144. Each of the first four is<=2,048. The symbolic25-H overapproximation is1,650 bytes (some Lifecycle/stage maxima cannot coincide), all60 finite binary64 coordinate representations require<=24 chars each, and the two512-UTF8-byte control strings attain worst6x expansion. The test compares complete bytes against the unchanged synchronous RunWriter, including newline and all actual envelope keys/counters.
- Canonical Context4,782 bytes<=8,192 derived bound<16,384 proposed cap, six maximum512-byte nonescaping descriptor paths with role wire size ceilings and longest case/condition/kind/counters. Six descriptors each<=768, remaining fields<=3,584.
- Complete selected-Lifecycle Commit793 bytes<2,048 proposed cap, with all three Lifecycle hashes, three outer hashes, counter maxima and exact Engine envelope. It is an authored encoding record, never evidence of actual assignment.

Paths513 bytes, IDs129 bytes, exception strings513 UTF8 bytes and envelope sequence/counters outside their exact limits refuse. No truncation or parent-cap change. Under the proved shape restrictions an admitted record cannot reach a16KiB complete event overflow; the explicit complete-byte cap remains an independent refusal guard. Tests do not establish current corpus convertibility, physical accounting slack or actual event authenticity.

`git diff --check` passed. A routine inspection command initially used unsupported `tail -1` with multiple logs; corrected to `tail -n 1`, preserving every log; no test result was affected. Root's plan clarification remains unstaged and outside this commit. No plan completion boxes or ledger edited by this implementer.

## Remaining limits

This is Task1 only, not the full plan or scientific goal. Engine journal fsync/assignment/commit/stop behavior, authentic held-source construction, actual raw/event audit, terminal numeric replay, publication/census, all-nine48+48 complete studies and all actual acceptance/qualification/resource/namespace/observer/GO gates remain unimplemented or closed. Source3 behavior tests do not qualify changed helper bytes against old pins. Actual inputs may not fit the new proposed restrictions; no observed IDs/paths/data are renamed or dropped. Parent byte/resource ceilings, retained raw/failures/partials, original thresholds/null/variance/precision guards, no retries/extra owners and prune refusal are unchanged. Independent root spec/code review must follow the four-file commit.

## Commit readback

`git show --stat --oneline HEAD` confirms exactly the four owned files,1,263 insertions/8 deletions; HEAD is `7f3c783868f8c878426e9ee02b44c86a125353c6` on `research/memory-vnext-spec-v1`. All four source/test/profile deliverables are clean against HEAD. The sole remaining tracked working-tree change is root-owned `docs/plans/memory-terminal-vnext-implementation.md`, intentionally untouched/unstaged by this implementer. No push/merge/CI/cleanup. Independent spec/code review next; proposed profile remains unqualified.

## Round 1 — three independent Important findings

Base `7f3c783868f8c878426e9ee02b44c86a125353c6`; root authorized this bounded fix after reading `task-1-review.md`, `task-1-evidence/review-lifecycle-wire-probe-01.log` and `task-1-evidence/review-cap-probe-01.log`. This implementer read the full review and both retained probes before writing the new regressions. Those source-only probe logs remain unmodified. The three findings were reproducible; the initial implementation was not yet compliant at these boundaries.

1. **F1, duplicate input coherence:** moved only the invariant Lifecycle/persisted-count check before the idempotent return. Selected input/count1 still returns an exact detached idempotent result without selector calls or Witness; selected/count0 now rejects. New-step continuation/schedule and terminal-phase checks remain after the idempotent branch, preserving valid duplicate behavior and legacy3 admission/order.
2. **F2, unconditional wire coherence:** standalone encoding now enforces selected **input** Lifecycle iff index1. A first-trigger pending-to-selected Witness remains index0. One fixed `_validate_reach_refs` helper supplies admission and encoding with exact Reach keys, required sensed Ref, paired gate/intervention, gate requires cue, distinct sequence/hash identities and prior-to-sensed order. Kind-specific checks remain in Context admission; actual event body/placement authentication still belongs to Task3. This adds no generic validation framework or evaluator permission.
3. **F3, output validation category:** the terminal-only worker now returns its local outputs to a fixed separate wrapper validation/encoding phase. That phase classifies strict4 output validation/cap/serialization failure as infrastructure `rejected` with no Witness. Available tiny detached input/local Lifecycles and the same original exception token are retained; proposed state/bearing remain null, returned decisions empty. The legacy terminal=None branch still calls `validate_state` at its unchanged original return cut. Ordinary core exceptions keep their existing classification; ordinary CueUnavailable still produces a raised Witness. No message-string matching or blanket reclassification of ordinary ValueError was introduced. The real legacy decision-size counterexample now rejects without Witness and rethrows the exact captured original ValueError object/class/message. Neither cap nor global memory._bounded changed.

The proposed profile explicitly documents these corrected invariants/phases. It remains PROPOSED/UNQUALIFIED, with no actual source/adoption/qualification authority.

### Round 1 retained verification

All three commands used the exact E2 environment above (`env -i`, research opt-ins absent, no bytecode, numerical threads1, empty CUDA visibility). Fresh explicitly named basetemps and every log are retained, including RED. No old workspace or partial log was removed.

RED command (exit1):

```
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_transition_vnext.py -k round1 --basetemp=.superpowers/sdd/memory-terminal-vnext-implementation/task-1-evidence/round1-red-01-temp > .superpowers/sdd/memory-terminal-vnext-implementation/task-1-evidence/round1-red-01.log 2>&1
```

Observed **6 failed,3 passed,61 deselected in1.84s** before production edits. Failures were the contradictory selected duplicate chain, rewritten selected-input index0, three missing paired/required Ref checks, and valid-input output-cap misclassification. The three already passing cases checked duplicate Ref sequence/hash and future Ref order. These were real boundary failures, not fixture/import errors.

Focused GREEN command (exit0):

```
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q tests/test_memory_transition_vnext.py -k 'round1 or local_selection_then_cue_failure or repeated_consumed_packet' --basetemp=.superpowers/sdd/memory-terminal-vnext-implementation/task-1-evidence/round1-green-focused-01-temp > .superpowers/sdd/memory-terminal-vnext-implementation/task-1-evidence/round1-green-focused-01.log 2>&1
```

Observed **11 passed,59 deselected in2.07s**, including the existing selected-then-CueUnavailable witness path and valid repeated consumed packet.

Final approved six-file GREEN command, run once after the source changes settled (exit0):

```
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q -s tests/test_memory_transition_vnext.py tests/test_memory_decision.py tests/test_memory_task.py tests/test_memory_experiment.py tests/test_memory_decision_world.py tests/test_memory_world.py --basetemp=.superpowers/sdd/memory-terminal-vnext-implementation/task-1-evidence/round1-green-final-01-temp > .superpowers/sdd/memory-terminal-vnext-implementation/task-1-evidence/round1-green-final-01.log 2>&1
```

Observed **104 passed in18.74s**, no warnings reported:70 new-file cases (nine added for this round),34 unchanged approved legacy cases. Exact complete writer maxima remain Witness12,244 / Context4,782 / Commit793 bytes; unchanged symbolic categories and parent caps still hold. `git diff --check` passes. No whole canonical/native/optional-model suite, payload reads/hashes, CI, dependency, push/merge, cleanup, nested agents or later tasks.

Self-review confirms only the invariant count check moved ahead of idempotence; the legacy worker return validation remains byte-for-byte at its original branch; source-M/live-M/one-execution and normal raised Witness paths are unchanged. Available local Lifecycles are now preserved on fixed output/serialization refusal. The same four owned source/test/profile files are the only files in this fix commit. Root-owned plan changes remain excluded. Scoped independent rereview of F1–F3 follows; no whole-plan/scientific acceptance claim.

Round1 commit readback: `5d9c204fcfa861e390dafbbfdaeec94bb71375ec` (`fix(memory): enforce terminal lifecycle and refusal boundaries`), exactly4 owned files,113 insertions/26 deletions. All four are clean against HEAD. Only root-owned `docs/plans/memory-terminal-vnext-implementation.md` remains modified and excluded. No push/merge/CI/cleanup. F1–F3 ready for scoped independent rereview.
