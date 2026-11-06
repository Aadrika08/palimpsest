# First qualified memory experiment: source-only critical path

2026-11-06; inspected source baseline `27f093f8d24c2f70eb0d39a285c0e00cc318328b`.
No implementation, imports, tests, probes, execution, payload inspection or new qualification occurred.
All paths below are repository-relative; this is a readiness finding, not adoption or GO.

## Finding

The next useful engineering step is to freeze ONE literal canonical-source producer/bootstrap and independent qualification contract. It is not another terminal wrapper. That contract is not yet complete enough for honest actual-adapter implementation. Pending provider choice and namespace exports are necessary external inputs, but supplying them alone would not create the missing source producer/backend.

Evidence: `docs/plans/memory-terminal-vnext-implementation.md:478–485` expressly leaves source/bootstrap, replay, namespace, complete accounting and later final readers unresolved. `scripts/memory_family_source_consumer_vnext.py:1–5,248–258` implements an authored-only constructor; it supplies no actual domain/backend. `scripts/qualify_memory_family_source_v2.py:300–310,630–640,695–707` still refuses unavailable external lifetime/load execution interfaces. These are substantive missing mechanisms, not empty acceptance lists to fill.

## Engineering versus externally supplied/adopted inputs

| Dependency | Can finish now from existing exact contracts? | Required before actual completion |
| --- | --- | --- |
| Canonical source production/bootstrap | Source-only call-path and literal asset candidate below: yes. Actual new owner/factory: no frozen complete contract. | Root names new owner/Engine ownership; freezes canonical IDs from creation, job/E/J/codec schemas, exact input/output roles and bootstrap equivalence. |
| 6a.2 actual holder/source epoch | No. 6a.1 is complete and authored-only. | Actual producer plus independently accepted nonempty source replay Q; exact L/F/R/admission trust anchors and namespace lifetime. |
| 3b public disk/raw audit adapter | No. Existing 3a can be reused after authentic source-origin contract exists. | Exact pre-audit registration, held source, root/location binding, original NPZ/SNP identity, final publication/lifecycle contract. |
| 4b actual numeric receipt adapter | No. Pure 4a already exists. | 3b's real independent raw-audit/source-origin result and same live source/conversion identity. |
| 2b strict4 Engine integration | No as the planned public capability. Existing authored holder is insufficient to implement its actual gate. | Actual fixed holder/domain, exact source/condition construction path and reviewed private authored integration seam; preserve ordinary Engine behavior. |
| Task5 real numerical replay/seal/read | Existing genuine positive-row worker is reusable; a zero-result wrapper adds no missing backend. Full route: no. | Successor admission/loader/source qualification plus 6a.2/3b/4b; integrated owner evidence additionally needs2b. |
| 6b copy publication/census | Arithmetic candidate is available; complete publisher: no frozen exact contract. | Nine accepted Task5 cells, execution/order/source references, adopted exact physical roles/census, immutable-input/output lifetime and copy/failure/atomic peaks. |
| 7 study/analysis handoff | Unchanged estimator semantics available; complete accepted handoff: no. | Complete Task5/6b/2b identities, independent order/observer acceptance, exact roster/guards and actual adoption package. |

Evidence: implementation plan `:259–269,400–418,438–451,487–503`; custody preflight `.superpowers/sdd/memory-terminal-vnext-implementation/custody-next-design-preflight.md:86–103,119–135`. Existing conditional5a is already complete (`docs/plans/project-completion-2026-11-05.md:91–103`); repeating pure mapping work does not advance actual qualification.

## Literal producer/bootstrap boundary root can finish next

1. Name one fixed new source-owner/producer path and one Engine editor; choose canonical hyphen UUIDs before any writer/job/events/SNP/owner/path creation. Preserve all old bytes and public defaults. Current `Engine.open` converts even supplied UUIDs to hex (`src/palimpsest/engine.py:388`); old source jobs require hex (`scripts/memory_family_source_runtime_v2.py:143–148`). Merely changing the consumer or passing a hyphen UUID cannot work.
2. Freeze bootstrap equivalence to current `Engine.open`: exact profile/case/restore validation, held provenance, RNG/thread settings, environment/world construction, asset verification and policy provenance, writer/failure/teardown behavior (`src/palimpsest/engine.py:339–429,430–491`). Direct `Engine.__init__` would omit these checks. Existing owner uses `_load_engine -> Engine.open` (`scripts/memory_family_source_runtime_v2.py:305–307,487–525`).
3. Freeze a read-only preprepared asset resolver for the new path, or separately budget/name graph preparation before immutable leases. Current `prepare_graph` may extract a temporary tree, write `palimpsest-prepared.json` and rename it (`src/palimpsest/assets.py:166–218`); it is not unconditionally a read-only loader. Complete runtime/native/import closure remains independent of the finite asset candidate below.
4. Specify the actual nonempty source replay consumer and source-endpoint Q, with independent acceptance authority. Existing `_replay_rows` is genuine `FlynnPolicy` replay, covers source1..1200 and condition1..900, checks bitwise actions/raw output, source endpoint and restores caller state (`scripts/memory_family_cell_replay_v4.py:51–74,99–129`). Its public wrapper still requires old source/receipt/compact identities (`:157–210`); zero has no model-replay scope. A successor must bind genuine held inputs/runtime/model directly, not relabel an old receipt.
5. Settle exact Q/L/F/R/admission schemas, trust roots, process roster and independent close/readback ownership together; do not invent their contents as fixtures. Existing loader admits a qualification pin BEFORE payload/import and holds source/assets/runtime through teardown (`scripts/memory_condition_replay_admission_v1.py:52–57,159–186,240–269`). The proposed J→E→V/C→Q/L→F→R DAG is documented, not an implemented/adopted backend (custody preflight `:33–46`).

This is a single concrete contract review, not another project rewrite. Until these choices are fixed, engineering can prepare that literal contract and stop; it cannot honestly declare 6a.2/3b/4b/2b/5/6b/7 implementation-ready. Exact namespaces and platform facts cannot be supplied by source reasoning.

## Read-only asset allowlist candidate derived without asset reads

Source/config metadata only: `model_manifests/flynn-full-vision.json:6–114` supplies the following literal relative paths and expected identities; `src/palimpsest/flynn.py:32–61,69–99` explains their loader use. No listed payload was opened, hashed, checked for presence or qualified here.

| Role | Candidate path below a future admitted asset root | Existing metadata identity |
| --- | --- | --- |
| Original archive | `drosophila adult connectome.7z` | manifest `:8–13`, 45,111,367 bytes |
| Checkpoint | `connectome_rnn_dagger_princeton_full_vision.pt` | manifest `:16–21`, 108,220,841 bytes |
| Prepared graph edge | `graph-49d19491c1df4b8f02af0e285b71dc171f47488a93ee5b91be8ee4e280bee9f1/drosophila adult connectome/connections_princeton.csv` | manifest `:108–112`, 273,646,145 bytes; fixed prepared-path derivation in `assets.py:175,213–219` |
| Seven prepared mapping leaves | Same prepared edge directory: `visual_column_L1_L2_L3_rear_view_left.csv`, `visual_column_L1_L2_L3_rear_view_right.csv`, `head_bristles_left.csv`, `head_bristles_right.csv`, `descending_neurons.csv`, `consolidated_cell_types.csv`, `JO-C_and_JO-E.csv` | manifest `:29–106` separately pins Git and archived bytes; choose the exact required representation, never normalize an observed original. |
| Prepared bookkeeping | `graph-49d19491c1df4b8f02af0e285b71dc171f47488a93ee5b91be8ee4e280bee9f1/palimpsest-prepared.json` | generated schema in `assets.py:176–182,214–217`; no committed content hash supplied, so cannot currently be an accepted descriptor. |

This is an allowlist CANDIDATE, not the full admitted forest. Absolute roots, prepared metadata bytes, actual namespace ownership/export, upstream/runtime/native closure, unused/extraneous files, directory identities, source/SNP/condition outputs and controls remain unbound. Manifest provenance itself limits original training graph/mapping claims (`model_manifests/flynn-full-vision.json:116`). No mixed held-out catalog or protected namespace was inspected.

## External decisions and first measured cost

- User CPU decision: retain complete-all-project-process accounting with currently absent final endpoints, or prospectively adopt the independently reviewed provider exclusion/interval-charge option. The latter is UNADOPTED and excludes provider overhead; neither option supplies retrospective tails (`docs/plans/memory-source-accounting-contract-next.md:25–29,50–64,89–99`; `docs/plans/memory-accounting-provider-option.md:15–20,74–108`). A new launcher cannot be implemented as an adopted mode before this choice.
- Independent inputs: both namespace-only exports with authorized exact roots/identities; actual admitted runtime/platform/provenance; prior-cost reconciliation; input/output/ancestor layout and enforceable resource lifetime. These are not substitute payload reads or a permission to inspect held-out catalogs. Old freeze source explicitly records missing projections, cgroup, final supervision, load isolation and prior CPU (`scripts/qualify_memory_family_source_v2.py:259–310`).
- Engineering then finishes and independently reviews the concrete source/bootstrap/Q/L/F/R/admission implementation and exact retained storage/metadata/physical-copy contract; only afterwards prepare the exact bounded source-stage freeze and request separate sealed GO. Source03 remains a separately pending OS-only toy and cannot validate the proposed provider topology (`docs/plans/memory-accounting-provider-option.md:110–112`).
- The first accepted source attempt must retain actual covered CPU intervals/final close evidence, wall time, peak memory/storage and every failure/partial output, including preparation, qualification, finalization/readback and teardown. Unknown terms stay unknown. The existing source-stage proposal is1,800 CPU seconds/900 wall seconds/8GiB/640MiB (`docs/plans/memory-source-accounting-contract-next.md:66–76`), not measured feasibility or source GO.
- Before any larger experiment, reconcile this observed source cost with an exact prospectively approved condition/calibration roster and storage/resource forecast. One source measurement is not a whole-study estimate; do not multiply a historical startup sample into a measured study result or add diagnostic/replacement owners. The unchanged project cap is24 aggregate CPUh with lanes1/12/5/4/2 and no borrowing (custody preflight `:132–133`).

Actual memory cost is still unknown. The historical audit charge1222.455497s is not complete whole-operation accounting (`docs/plans/project-completion-2026-11-05.md:66–72`). Retain raw and every partial/candidate; deletion stays disabled. Actual source/held-out GO, full cohort capacity, scientific improvement and final project completion remain open.
