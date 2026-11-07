# Source vertical implementation fix1

**DONE for the four accepted review findings; ready for root's scoped review.** This is conditional software and authored unit evidence only. No accepted actual Q/L/F/R, backend, admission, experiment or scientific cost is created. Original implementation report, independent review and earlier logs remain unchanged. Root retains HEAD/integration; no commits or agents were used.

Basis: `source-vertical-implementation-review.md` findings1–4, the frozen contract, implementation rulings1–6, and root's decision7 approving the fixed checked submit/advance orchestration in the new owner.

## Findings and corrections

1. **Actual namespace metadata before acquisition.** Added `_validate_actual_namespace_coverage`, called by actual preflight before input closure/execution. Its exact original v3 outer schema stays separate from authored coverage. A shared pure expected-value validator requires exactly two ordered fixed IDs/kinds, exact row/expected keys, exact bounded ints (including entries/files), all hash fields, byte equalities, historical empty seeds and total value limits. Held namespace consumption explicitly requires cardinality2 and indexes both rows; no third row can disappear through zip. Tests use parser metadata only, accepting the exact detached value and rejecting third-row/kind/extra/bool/oversize/hash defects while payload I/O and RuntimeHandle entry are forbidden. No external authority/export enrollment or actual execution is manufactured.

2. **Raw leaf admission before each write.** Added the narrow private `RunWriter._check_budget(...,target=None)` seam. Default calls and recording-directory budget paths remain unchanged. Preservation/source writes provide the manifest/events/chunk leaf path and exact incoming size. The fixed source budget checks events' existing size plus append, manifest64KiB and chunk7MiB prospective/pending bounds, in addition to its existing aggregate/atomic/report/headroom/free-space admission. Flush prechecks BOTH chunk and event targets before allocating/publishing the chunk. Tests refuse an oversized manifest, near7MiB event append, and chunk whose event cannot fit, with no write/pending creation or chunk publication. Near-cap events use sparse logical sizing, not a multi-MiB payload allocation. Caps were not raised.

3. **Original exception preservation.** Publisher write/fsync+FD-close and parent-fsync+close independently collect original BaseExceptions in body-first order and drain every acquired FD. Failed pending/final prefixes remain retained. `_failure` now guards its entire inventory/construction/publication operation and appends diagnostic failures to the existing primary/teardown list, never replacing it. Three paired publication failure tests check exact exception-object identity/order and close attempts; a diagnostic PermissionError test preserves the original primary object first.

4. **Loaded identity at every boundary.** Added fixed `_LoadedPolicyIdentity`, owned by `_OwnedPolicyReferences.custody_check`. It binds immutable controller-tensor digest, runtime profile, complete policy provenance and policy/agent/cell lifetime identities. Every call applies the unchanged actual/authored guard plus the existing runtime validator and current tensor/provenance equality. Hidden/retina/cache state is excluded from immutable identity. Owner checks surround commands, capture and close; qualifier uses the same fixed object through the existing whole-trace per-row hook. Root's decision7 copies only the old ordinary step orchestration: fixed neural command ID/kind/paused episode, real submit, a check BETWEEN submit/advance, real advance, and postcheck. No Engine/world/cell arithmetic or old helper is changed. References/checker aliases are cleared on disposal. Genuine generated-model faults in tensor/provenance/training state stop after one owner step or one replay row. Mutation during real submit prevents every advance and drains the queued command, environment, writer and source policy references.

Files changed in this round only:

- `scripts/memory_family_source_records_vnext.py`
- `scripts/memory_family_source_runtime_vnext.py`
- `scripts/memory_family_source_qualifier_vnext.py`
- `scripts/memory_source_parent_entry_vnext.py`
- `src/palimpsest/records.py`
- Matching records/runtime/parent tests, `tests/test_memory_source_control_rendezvous_vnext.py`, and the existing optional `tests/memory_source_vnext_fixture.py`.

No existing replay arithmetic/default-None path, actual full-model guard, public recorder API, Puck core, old receipt/pin/profile/body schema or output roster/cap was weakened or repinned.

## Retained verification

All commands used the exact clean environment, named Python and retained stable evidence root:

```sh
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests \
 LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' \
 TMPDIR=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-scratch-20261106-11 \
 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest -q <selection> \
 --basetemp=/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/<fresh-run-name>
```

Logs are in this SDD directory; basetemps use the same log stem without `.log`.

| Log | Selection/result |
| --- | --- |
| `source-vertical-fix1-red-01.log` | records/runtime/control/parent `-k fix1`:17 failed, reproducing all four gaps |
| `source-vertical-fix1-green-01.log` | same17 cases:17 passed |
| `source-vertical-fix1-green-02.log` | records/runtime/control `-k fix1`, including legacy default budget call:16 passed |
| `source-vertical-fix1-green-03.log` | parent `-k fix1`, expanded tensor/provenance/training and submit faults:7 passed |
| `source-vertical-fix1-covering-01.log` | exact9-file direct covering wave below:229 passed,4 tiny-fixture setup errors; full-parent positive, all mutation negatives and recorder/bootstrap/preservation compatibility passed |
| `source-vertical-fix1-covering-02.log` | exact ordered reproduction below after the fixture-only repair:14 passed |

The covering01 setup errors were an import-registration isolation defect: a parent fixture's newly imported copied upstream modules leaked when the original registration was absent. The unchanged import origin guard correctly refused those modules in the later tiny fixture. The optional fixture now records/restores exact original OR absent registrations for its fixed seven upstream module names. No unrelated sys.modules entries are cleared, no import guard is bypassed and no files are deleted. The ordered parent-before-tiny reproduction passes after this repair. These overlapping scopes are not summed into a fictional all-green aggregate run.

Covering01 exact selection:

```
tests/test_memory_family_source_records_vnext.py
tests/test_memory_family_source_runtime_vnext.py
tests/test_memory_source_control_rendezvous_vnext.py
tests/test_memory_source_parent_entry_vnext.py
tests/test_memory_source_policy_release_vnext.py
tests/test_memory_source_replay_custody_vnext.py
tests/test_memory_source_structured_teardown_vnext.py
tests/test_memory_source_bootstrap_vnext.py
tests/test_source_failure_preservation_vnext.py
```

Covering02 exact ordered selection:

```
tests/test_memory_source_parent_entry_vnext.py::test_real_authored_source_writer_snp_audit_codec_and_independent_cell
tests/test_memory_source_parent_entry_vnext.py::test_fix1_submit_mutation_refuses_advance_and_drains_pending_command
tests/test_memory_source_replay_custody_vnext.py
tests/test_memory_family_source_records_vnext.py::test_fix1_actual_coverage_metadata_refuses_before_any_payload
```

Latest successful full-parent fixture is under:

`/home/utkarsh/Work/shraddha/palimpsest-authored-test-evidence/source-vertical-fix1-covering-02/test_real_authored_source_writ0/attempt`

It still uses real FlynnPolicy/upstream cell, generated4813-wide/N12 weights/graph, genuine Engine/world/queued processing, original SNP/FD audit and direct16+3 V/C, a fresh independent replay policy, restoration, reference disposal and custody drain. Native/environment acquisition geometry and installed-runtime provenance remain explicitly controlled authored premises. All source claims stay false and the candidate is `software-unit-only`, unaccepted. A successful ordinary unit is not actual1200-step/native/full-model feasibility or experiment cost.

Source self-review and scoped AST/whitespace/diff checks completed. No new protected payload/model/native physics/runtime hashes, namespace study, research/probe, CI/network/dependency operation, cleanup/deletion or CPU debit was performed. Actual externally authenticated GO/load/resources/isolation/exports/backend/acceptance/L/F/R remain absent. Root's scoped review is next.
