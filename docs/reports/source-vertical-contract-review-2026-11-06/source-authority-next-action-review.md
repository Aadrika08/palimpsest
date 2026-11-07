# Source authority: next action review

2026-11-06. Source-only review against root-supplied b7a967026d1261b20450024e271f7cfc790dfd17;
HEAD/cleanliness not independently checked. No tests, imports, probes, network, payload reads/hashes,
service inspection or execution. Only this report written. Line references below name source/docs.

## Verdict

**YES: root can now freeze a complete provider-neutral owner/genesis-qualifier contract.**
Missing CPU adoption and actual namespace/runtime identities do not prevent selecting its interfaces,
serialization, custody algorithm, outputs or refusal behavior. They prevent an actual admitted invocation.
The current contract is incomplete; its omissions are root engineering work, not unanswered user choices.
A frozen contract can have explicit externally discharged preconditions without pretending those hold.
**NO existing module supplies the actual external execution backend.** Do not label its absence solved by
an empty pin set, a new exact Python class, a callback, or another always-refusing public wrapper.

## Evidence fixing the boundary

- Readiness `source-owner-contract-readiness.md:48–59,121–139` distinguishes four engineering clauses from
  actual inputs/adoption; its suggestion to request an unnamed interface is premature if root can define it.
- `scripts/qualify_memory_family_source_v2.py:300–317,630–640,695–707` explicitly lacks enclosing supervision,
  load isolation, namespace exports and prior-cost reconciliation; its actual entry refuses.
- `scripts/memory_family_source_runtime_v2.py:214–244` checks an admission assertion's consistency only.
  Its private reference path holds bytes before loading (`:487–525`), while public V3 refuses (`:530–534`).
- `scripts/memory_source_runtime_closure_v1.py:584–595,641–701` owns current-byte custody, expressly not
  execution permission. `src/palimpsest/held_provenance.py:1–7,97–125` formats supplied provenance pins;
  neither authenticates the independent authority that supplies those pins.
- `scripts/memory_condition_replay_admission_v1.py:240–269` requires an already accepted qualification pin
  before reads/loading. Its `:159–186` implements load/model checks. That later-consumption gate is not
  a genesis-qualification gate. Requiring its own future Q would make the first qualification impossible.
- `scripts/memory_family_cell_replay_v4.py:51–129` supplies substantive positive-row/source-endpoint replay;
  it does not supply independent input admission. Old owner `:393–444` supplies acquisition/close sequencing,
  not successor canonical envelopes. Preflight `custody-next-design-preflight.md:33–46` already fixes the DAG.

## Minimum root decisions: adopt these together, then implement one vertical slice

1. **Trust boundary and first attempt.** Define an independently frozen `AttemptAuthorization` for one
   `attempt_id`, canonical source run, exact P/J/job descriptors, role roster, two namespace descriptors,
   load-environment descriptor, resource contract descriptor, finite process/phase roster and deadline.
   Its authority is the operator's separately authenticated exact-stage GO plus independently admitted
   enclosing resource/load contract; it is NOT source qualification and contains no `accepted:true` field.
   Freeze expected authorization descriptor outside P and outside every subject it authorizes. Neither
   worker discovery nor a digest embedded in the job authenticates it. Keep actual enrollment empty now.
   Specify external parent obligations as preconditions, with named evidence bindings, not invented facts:
   clean pinned interpreter/native load environment before Python/native startup; enforced allocation,
   no escape, namespace ownership, finite descendant closure, final accounting and retained failure paths.
   These describe what a future admitted provider must establish; selecting GNU Time is unnecessary.
2. **Concrete parent/workload seam.** Name `scripts/memory_source_parent_entry_vnext.py` as the fixed trusted
   workload entry, separate from any future launcher. Use `run_attempt(job_bytes, authorization_bytes)` only
   inside the independently admitted enclosing process. Its fixed implementation validates bounded
   canonical bytes and external frozen pins, derives all paths, opens/owns the actual input leases, creates
   diagnostics from those authenticated pins and calls fixed owner/qualifier functions. No loader callback,
   arbitrary command, caller-selected module or caller-supplied HeldProvenance. External launch validity is
   an explicit trusted-parent precondition; in-process metadata checks must never claim to establish it.
   Root must name this precondition in the API and receipt; the entry alone is not a complete actual backend.
   Owner signature: `produce_source(job, live_inputs)` in `memory_family_source_runtime_vnext.py`.
   Qualifier signature: `qualify_source(job, closed_source, live_inputs)` in
   `memory_family_source_qualifier_vnext.py`. Both accept only the parent module's exact private lease type.
   The lease proves active custody under this trusted call path, not permission by Python type identity.
3. **Live inputs, not detached summaries.** Parent alone constructs that lease from genuine RuntimeHandle
   plus held model/graph/mapping/provenance/namespace descriptors, using fixed readers and an ExitStack.
   Require exact admitted absolute roots/roster, alias checks, canonical path-role equality and no overlaps.
   Recheck before/after import/load, each owner step, SNP capture/write, independent decode/replay and
   output publication; hold through policy/native teardown. Poison permanently on failure; invalidate
   before release; drain every holder, preserve body and teardown errors; return success only after exit.
   RuntimeHandle retains all-false execution/qualification semantics. Namespace descriptors alone are
   insufficient: their independently authorized scope and exact closed subtree ownership must be bound.
4. **Owner and direct codec epoch.** Shared canonical-prepared Engine.open is the sole construction path;
   preserve original canonical UUID in every job/path/writer/event/application/SNP. Source3 only, no selector,
   1..1200 genuine queued steps, one original acquired SNP, original preregistration event prefix, real close.
   Create `memory_family_source_records_vnext.py` for exact direct job/owner/report/outcome/A/E/V/C/Q codecs;
   create `memory_family_source_raw_audit_vnext.py` for independent closed-output validation. Retain preflight
   J/E/F/R outer keysets verbatim; job stores J descriptor, while J stores only a prospective job slot.
   New source manifest registration binds J+job+case+run+P; old hex admission/receipt validators stay unchanged.
   Reuse array/ZIP/math primitives, never rename schemas or normalize old UUIDs to gain acceptance.
5. **Genesis replay and acceptance.** The authorized first attempt names producer, independent raw auditor,
   converter and independent qualifier as distinct fixed roles; producer cannot author or accept Q.
   Qualifier loads the exact candidate runtime/model permitted for this attempt, verifies its actual identities
   and uses real held SNP/raw/V/C inputs with `_replay_rows(operation='source',first_tick=0,input_width=4813)`.
   It checks every row, raw/action bits and original source hidden endpoint, restores policy/cache state and
   rechecks custody through teardown. No prior source Q is needed to ATTEMPT this work. Candidate runtime
   execution still requires the external load/environment/resource permission; byte custody cannot supply it.
   Q result binds P,J,job,E,A,SNP,V,C, runtime/model/input identities, rows checked, endpoint hashes and
   scope `encoded-source-cell`; independent acceptor pins that exact result only after reviewing real evidence.
   Q result existence is not Q acceptance. Later condition loaders require independently accepted Q plus
   F/R/admission; their gate must remain distinct from this one-shot genesis entry. No fake actual unit Q.
6. **Physical slots and lifecycle.** Freeze the preflight layout: `.pending/<case_id>/.raw/<run>/recording/`,
   sibling `worker-report.json`, `source/owner.json`, sole `source/snapshots/initial.snp`, numeric candidate
   subtree, and external `controls/<run>/`. Place J/job/supervisor/stdout/stderr/cleanup/A/E/V/C/Q/L/F/R and
   authorization/acceptance records in individually named external control slots; no unbudgeted receipt tree.
   Reserve a named incomplete/failure slot per writing phase plus each simultaneously live atomic temporary.
   Root must allocate per-slot caps whose *sum*, including failures/copies, fits controls8MiB/atomic8MiB;
   stdout/stderr each<=256KiB inside controls. Preserve raw512/SNP16/candidate32/headroom64MiB =>640MiB.
   A generic decoder maximum is not a slot allocation. Count initial frozen inputs/precreated directories
   separately in the full storage census; do not charge only successful new outputs or assume capacity.
   Precreate every writable branch before holding shared ancestors; immutable control subtrees gain no later
   files. Freeze stage-specific holds so later Q/L/F/R writes cannot mutate held input directories/ancestors.
   Sequence: source close -> A/E -> V/C -> replay Q -> independent Q acceptance -> source-stage L -> F -> R.
   L closes the declared finite source-production/qualification scope only. F/R/readback/holder jobs belong
   to separately named finite accounted phases; neither L nor a later reader claims its own future CPU tail.

## Productive work and external stop boundary

Root should now write/review this ONE complete contract, filling literal nested keysets and slot caps,
then implement the real owner + direct raw codec/auditor + parent-owned custody + independent genesis replay
as a single useful slice. Genuine authored positive/negative unit paths can validate these mechanisms under
separate authored authorization; they do not qualify actual inputs. Do not stop at holder/report wrappers.
No accounting launcher implementation follows before the CPU decision: provider option `:103–108` requires
adoption; current all-project-process tails remain unknown (`memory-source-accounting-contract-next.md:25–29,
37–64`). Both authorized namespace exports, actual runtime/load/provider facts, prior reconciliation, exact
capacity and separate GO remain external prerequisites. They block actual invocation, not this engineering.
Full actual Q/L/F/R/backend, conditions/publication/study and project completion remain unfinished root work.
No actual source03/qualification/held-out attempt, paid compute, retry or deletion is authorized by this review.
