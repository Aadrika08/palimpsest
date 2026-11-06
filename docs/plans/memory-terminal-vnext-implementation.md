# Memory Terminal Vnext Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Execution method and architecture still require root review; this document authorizes neither agents nor implementation.

**Goal:** Specify a separately versioned, independently replayed condition terminal-prefix and reached-event oracle evidence path without altering historical scientific rules or granting actual execution authority.

**Architecture:** Proposed software architecture, subject to root approval: one fixed shared internal pure transition worker retains the legacy public function/default behavior and also serves a versioned detached-result API. A narrowly admitted Engine branch persists bounded exception-safe transaction evidence before assignment or rethrow, and commit evidence only after actual assignment. Successor raw/numeric/pair/replay/condition/endpoints consume that evidence; actual entry remains closed and old pins are never rebound.

**Tech Stack:** Existing Python canonical JSON/SHA256, synchronous `RunWriter`, NumPy ZIP_STORED codecs, pytest authored fixtures; existing guarded encoded-cell and held-input custody interfaces. No new dependencies, model acquisition, native test owner or paid compute.

**Spec:** [Unadopted oracle/order proposal](memory-family-vnext-oracle-order-amendment-design.md), [scoped scientific review](../reports/memory-vnext-design-review-2026-11-06/README.md), [condition-prefix design](memory-case-cell-qualification-v2-design.md), [approved full-project scope](project-completion-2026-11-05.md). Read these with this plan. Baseline `caf919b18817c44304a0bc4fe19ffefd3284e7e1`; plan only, no tests/imports/data/runtime/CI run.

## Global Constraints

- UNADOPTED successor proposal: old JSON protocols, pins, historical evidence, source acceptance and Task 3 own-pair authority remain unchanged. Source acquisition/public numeric source remain nonempty. Changing helper/Engine source bytes requires a successor source closure; legacy behavior equivalence does not qualify those bytes against old pins. Old identity mismatch must refuse, never rebind.
- Exactly 48 development and separately 48 held-out families ×3 kinds ×9 conditions; family is unit; equal kind/family weights; 900 natural non-goal, 90 benefit, 45 harm, all original precision/null/success-harm/no-event/nonzero-variance guards; no retries, replacement, extra donor/diagnostic owners or changed thresholds. Separate held-out GO remains required.
- Actual research preparation/qualification/evaluator/terminal/replay/audit/control/teardown charges memory12h within project24h. Approved standalone formal-proof builds and ordinary software tests retain their exclusion; no borrowing or paid compute.
- Existing raw source/condition 512/384MiB, source SNP16MiB, compact source/condition32/25MiB, combined metadata/container/control overhead1MiB, source/condition events7/5MiB, source/condition rows1200/900, chunks38/29 and other existing caps remain. New subcaps below are proposed software restrictions inside those caps, not adopted actual profiles or proof that every current input fits.
- Keep all raw, candidates, failed/partial outputs and logs. Prune always raises `PermissionError`, including after a future pass. Account every physical witness/context/commit copy, raw+candidate/atomic peaks and teardown; no compression/deletion credit. Closed namespace, complete lifetime/resource, actual qualification, observer/order/publication and GO gates remain closed.
- No real payloads or repository modules are executed to prepare this plan. Future authored tests must be isolated from actual model/raw/SNP/catalog/protected payloads and must not claim native/model qualification.

## Review Focus

1. Local selection followed by `CueUnavailable`: preserve actual local activity without fabricating returned decisions or mutating Engine input aliases (Task 1).
2. Witness/commit write failure before/after assignment: retain actual committed state and fail infrastructure without a scientific 900 or retry (Task2a helper, then Task2b integrated branch).
3. Source-M versus changed live-M gold, null resolved-empty versus no-trigger pending, fresh passage evidence on a terminal sensed packet (Tasks 1/3).
4. Empty numeric continuations and positive partial chunks: exact commitments/arrays/counters, no fake neural replay and no malformed-full fallback (Tasks 3–5).
5. Companion files plus retained raw differ from historical owner/entry census: use only an explicitly proposed successor census after review/adoption; old gates still refuse, and unchanged byte/resource ceilings still apply (Task 6).

---

## Ownership and interface map

Names in this plan are **proposed new software names**, not existing accepted profiles. Each task is one reviewable deliverable. The dependency order is **1→2a→3a→4a→5→6→3b→4b→2b→7**. Task3a is a pure conditional proof; its authentic public adapter Task3b waits for Task6's actual source holder. Task4a and private Task5 software may consume authored pure proofs, but actual receipt/publication acceptance waits for3b and the separately reviewed Task4b adapter. Task2a is not an integrated opt-in; only Task2b integrates the authentic Task6 custody dependency. No task changes old protocol/pin files. Root must approve any shared-helper factoring before implementation.

| Task | Files owned during implementation | Responsibility |
| --- | --- | --- |
| 1 | Modify `src/palimpsest/memory_decision.py`; create `src/palimpsest/memory_transition_vnext.py`, `tests/test_memory_transition_vnext.py`, proposed `docs/plans/memory-terminal-vnext-v1-protocol.json` | Fixed transition semantics, detached exception witnesses, exact schemas/DAG/subcaps. |
| 2a | Modify `src/palimpsest/engine.py`; create `tests/test_memory_engine_transition_vnext.py` | Private synchronous persistence helper and default legacy-rejection guard only; no opt-in integration claim/import of future custody class. |
| 3 | Create `scripts/memory_family_terminal_audit_vnext.py`, `tests/test_memory_family_terminal_audit_vnext.py` | Independently reconstruct reached world/packet/transition/terminal evidence from authored or separately admitted raw. |
| 4a / later4b | Create `scripts/memory_family_terminal_numeric_vnext.py`, `tests/test_memory_family_terminal_numeric_vnext.py`, `docs/plans/memory-terminal-numeric-pure-vnext-v1-protocol.json`; narrow helper factoring only in `memory_family_compact_v4.py` / `memory_family_numeric_preservation_v2.py` if separately approved | Pure empty/early condition codec now; actual receipt adapter after3b. Reuse numerical primitives, old APIs reject successor/pure output. |
| 5 | Create `scripts/memory_family_terminal_condition_vnext.py`, `tests/test_memory_family_terminal_condition_vnext.py` | Guarded replay scope, successor pair/seal/read/endpoints, real public gate closed. |
| 6 | Create `scripts/memory_family_source_consumer_vnext.py`, `scripts/memory_family_terminal_case_vnext.py`, `tests/test_memory_family_source_consumer_vnext.py`, `tests/test_memory_family_terminal_case_vnext.py` | New source-consumption/case epoch and exact successor physical census; byte/resource refusal. |
| 2b (after6) | Modify `src/palimpsest/engine.py`, `tests/test_memory_engine_transition_vnext.py` sequentially after Task6 | Authentic fixed-class opt-in and integrated version4 Engine branch; old default remains strict. |
| 7 | Create `scripts/memory_family_terminal_analysis_vnext.py`, `tests/test_memory_family_terminal_analysis_vnext.py`; proposed `docs/plans/memory-terminal-vnext-study-v1-protocol.json` | New order/analysis identity, complete full-family roster/gates and closed adoption package. |

The new modules are adapters around existing pure row/NPZ/commitment and custody/loader/publication primitives, not a replacement owner framework. No generic callable hook, registry, externally supplied witness sink or fake production policy/engine argument. Task 5 may factor fixed private custody/orchestration helpers from existing source only with reviewed ownership; do not copy a second unrestricted sealer or weaken old validation.

## Exact proposed wire contract and acyclic identities

All key sets below are exact; unknown/missing keys, duplicates in JSON/member lists, bool-as-int, nonfinite numbers, invalid UTF-8, noncanonical encodings, aliases and trailing bytes refuse. Canonical JSON is `memory.canonical_bytes` (UTF-8, sorted keys, compact separators, finite only, nesting≤32). Hash each canonical **body**; no body includes its own digest. Events retain the writer's existing spaced JSON/newline bytes byte-for-byte; an event reference hashes the canonical decoded complete event including its actual sequence, not a reserialized replacement for raw bytes.

Types: `H` = 64 lowercase hex; `I` = exact nonnegative int≤2100 for ticks (counts use their explicit caps); `ID` = proposed successor-wire restriction `[A-Za-z0-9][A-Za-z0-9._:-]*`, length≤128 (generated family and sensor IDs must be proved to fit before adoption; old APIs retain their broader existing ID validation, and no observed ID is renamed); `D` = exact `{path,size_bytes,sha256}` with normalized relative path≤512 bytes using only `[A-Za-z0-9._/-]`, nonempty components other than `.`/`..`, no leading/trailing/repeated slash, and exact integer size within its role's existing bound plus `H`. This new path alphabet explicitly excludes quotes, backslash, whitespace/control/non-ASCII bytes, so its JSON characters need no escaping; historical broader path validators remain unchanged and no original path is renamed. `Ref` = exact `{sequence,sha256}`, sequence exact int<50000, hash of an earlier actual event. `Schedule` = exact `{boundary_tick,event_tick,decision_tick}` (`I`, `I|null`, `I`), equality to the registered profile; boundary positive. Existing old exact schemas are referenced by their frozen source/protocol definitions, not inferred from arbitrary dictionaries.

| Record / schema | Exact fields and restrictions |
| --- | --- |
| `memory-terminal-context-vnext-v1` (`Context`) | `schema,profile,source_closure,source_registration,source_commit,source_raw_audit,source_snapshot,source_application_sha256,source_m_sha256,source_world_sha256,source_run_id,case_id,case_sha256,kind,run_id,condition,condition_resources_sha256,source_invariant_sha256,schedule`. Six descriptor roles `profile,source_closure,source_registration,source_commit,source_raw_audit,source_snapshot` are `D`; remaining digests `H`, run IDs canonical UUIDs under existing rules, `kind` one of change/null/no-event, `condition` one of the nine fixed conditions, `Schedule`. Source M and actual acquired source world are held authenticated from source SNP/events/rows; do not duplicate their payloads in this record. |
| `Lifecycle` (state4 metadata and witnessed) | Exact `{status,resource_sha256,provenance_sha256,selection_sha256}`. `not-oracle`/`pending` have all three null; `selected` has all three `H`. Selected hashes bind the installed IDs, resolution provenance and actual selection, respectively. Pending cannot be consumed as resolved empty. No intermediate status can authorize resumption. |
| Condition state4 | Exact legacy state3 key set at `memory_decision.py:145–146` plus only `terminal_context_sha256:H,terminal_lifecycle:Lifecycle`, and `version=4`. Old public `validate_state/advance_memory/configure_selector/arm` remain strict3 and reject this record. Source acquisition/SNP remain strict3. Oracle pending ordinary config uses syntactic[] only inside this legacy-rejected marked state. |
| `Reach` | Exact `{cue_event,gate_event,intervention_event,sensed_event,before_occupancy,after_occupancy,actual_circles}`. Event fields `Ref|null` except sensed required. Occupancies are exact dictionaries with the two authenticated case subject IDs and values open/blocked only when oracle resolution occurs in this transition; otherwise both null, including nonoracle triggers and later terminal witnesses. Task3 independently reconstructs actual occupancy from held source/case/raw geometry; actual circles finite float triples, at most20, matching the same real circles used by sensing. Gate/intervention null is required for null/no-event. No-event cue null. No future geometry. |
| `Stage` | Exact `{stage,input_sha256,output_sha256}`; stage enum `trigger,resolved,installed,selected`; `H` digests bind the exact typed inputs/output at that logical cut. Ordered once-only subsequence; resolved/installed only oracle. Trigger uses existing exact trigger schema (`memory.validate_trigger`); source-M resolver inputs include both occupancy maps and actual trigger. |
| `memory-transition-witness-vnext-v1` (`Witness`) | `schema,context_sha256,job_sha256,index,previous_sha256,tick,packet_sha256,input_memory_sha256,input_lifecycle,local_lifecycle,reach,trigger,stages,gold,selection,local_memory_sha256,local_decisions_sha256,result,exception`. Hashes `H`; index0/1; previous=context hash at0 or earlier witness body hash at1; trigger null or existing exact trigger; stages≤4; gold nonnull **only if resolved in this transition**, then sorted IDs length1(change)/0(null); selection nonnull only if selected in this transition. Later terminal with prior selected resource has both null/no new resolve/install/select stages and binds that prior resource/provenance through input/local Lifecycle and the earlier witness chain. Result `returned`/`raised`/`rejected`; exception null iff returned, otherwise exact `{type,message}` strings each≤512 UTF-8 bytes. Unknown/oversize exception is infrastructure, never truncated into a natural cause. Local memory/decisions are hashes of detached actual local values, independently reconstructed by pure replay; no fabricated ordinary return events. A rejected input without valid bounded local evidence has no Witness. |
| `memory-transition-commit-vnext-v1` (`Commit`) | Exact `{schema,context_sha256,witness_sha256,tick,memory_sha256,lifecycle}`; all referenced hashes already exist. Emitted only after actual Engine assignment for a witnessed returned transition. No commit for raised or idempotent return. |
| Engine event envelope | Exact `{run_id,episode,tick,episode_step,sequence,kind,witness}` or the same keys with `commit` instead of `witness`, matching `Engine._event` and `RunWriter.event`; no case_id field. Canonical owner UUID, exact integer episode0, exact nonboolean tick/episode_step0..2100 both equal body.tick, exact bounded sequence. Context/body validation additionally enforces the acquired origin and continuation window. Size checks include the real spaced writer JSON and newline. |
| `memory-terminal-proof-vnext-v1` (`TerminalProof`) | Exact `{schema,context,job,raw_manifest,raw_events,worker_report,source_snapshot,boundary_tick,terminal_sensor_tick,first_motor_tick,last_motor_tick,row_count,chunk_count,world_applied,trigger_reached,decision_reached,witnesses,commits,outcome,goal,path_length,capped_ticks,trace_digest,row_sequence_sha256,camera_sequence_sha256,invariant}`. Descriptors for named immutable inputs; witnesses/commits lists of `Ref` (≤2 each); positive row count≤900; zero first/last motor null, count/chunks/path0, goal false, score900; positive first=b,last=b+n−1; terminal sensor tick null for a row-backed normal terminal or b+n for a sensor-only tail; exact finite path and original outcome. Reached booleans are audit outputs recomputed from evidence, never caller permissions. |

### State4 boundaries, exact stage commitments and detached results

Task1 owns strict wrappers in `memory_transition_vnext.py`: `validate_terminal_state_vnext(state:dict,*,context:Context)->dict`; `promote_terminal_state_vnext(configured_state3:dict,*,context:Context)->dict`; `configure_terminal_condition_vnext(source_state3:dict,config:dict,u:dict,*,context:Context)->dict`; `arm_terminal_state_vnext(state4:dict,*,boundary_tick:int,context:Context)->dict`; `inspect_terminal_state_vnext(state4:dict,*,context:Context)->dict`; `terminal_acquired_boundary_vnext(state4:dict,*,context:Context)->bool`; `terminal_goal_allowed_vnext(state4:dict,*,context:Context)->bool`; `mark_terminal_goal_vnext(state4:dict,*,context:Context)->dict`; `terminal_source_view_vnext(state:dict,*,context:Context|None=None)->dict`; `terminal_condition_invariant_vnext(application:dict,*,context:Context|None=None)->str`. Configure validates/configures the genuine unarmed acquired state3 through the unchanged old API, then promotes its detached copy; promotion never changes M/E/detector/request/supervisor/native state. Only the new strict wrapper accepts4; no public4→3 projection or fake old receipt. Shared **private** field-validation/arm/core helpers may dispatch only fixed3/4 wrappers with exact key/version checks. All version4 Engine inspection/acquired/goal/mark-goal uses call these fixed strict4 wrappers; old public helpers stay strict3.

Strict4 retains the existing aggregate state-size ceiling, including its new metadata. Its inspection output is the existing exact `inspect` view (`memory_decision.py:486–491`) with version4 plus `terminal_context_sha256,terminal_lifecycle`; every nested value is detached. Acquired/goal/mark-goal/arm predicates and changes remain the existing algorithm's, under strict4 validation. No helper silently strips the marker to obtain legacy admission.

The exact state-level source view deep-copies the validated state and removes only `version,u,selector,terminal_context_sha256,terminal_lifecycle` (new keys absent from genuine3). Full application invariant reuses the existing `condition_state` exclusions verbatim and additionally excludes only these memory version/new metadata fields; it introduces no native/model/RNG/world/M/E normalization. Compute the source invariant from original3 with no Context dependency, then place that hash in Context (acyclic). Strict4 views require Context validation. Require source-view equality after declared U/selector configuration/promotion **before arm**; arm then proves only its existing declared schedule/supervisor/world changes, without pretending armed state equals the unarmed source or excluding those changes. State hashing for witnesses always hashes full strict4 state including markers; source-view projection is never an accepted transition input. A supplied context/hash, state marker and Lifecycle must agree with the fixed held context/config and chain. Removing context/Lifecycle, changing version or losing Engine mode must refuse before selection/policy. Task2a's default guard checks state marker **or** manifest context **or** Engine bound-mode latch: any vnext indication requires the integrated strict4 path; inconsistent/missing indications refuse. A genuine legacy default call requires strict3 and no vnext indication, so pending[] cannot fall through to legacy selection.

Before Context exists, pending oracle config provenance hashes exact `{schema,profile,source_application_sha256,case_sha256,run_id}` with schema `memory-oracle-pending-provenance-vnext-v1`, profile `D` and already known source/case/owner inputs. Config resource is syntactic[], resource hash sha([]), condition oracle, limit1; this provenance is not resolved gold. `Context.condition_resources_sha256` hashes exact `{selector,u}` of the configured3 fork, so it has no backward Context-hash edge. Promotion checks acquired/unarmed3, source-M/case/config identities and preserves its detached source view; **full native/application equality is Engine2b's held-source check**, not a claim that a state-only function authenticates an absent native payload. Strict4 selected validation checks config resource/provenance against Lifecycle, reconstructs the frozen pending-config projection only internally for Context resource equality, and Task3 independently re-establishes prior selection from actual witness chain. No private projection is public3 transition input or scientific permission.

Every Stage input/output is exactly the canonical object below (no unlisted keys); `Stage.input_sha256/output_sha256=sha256(canonical_bytes(object))`. All `*_sha256` values are `H`; trigger/selection/config/map types are the exact validated types already named. Inputs are captured before the named action; outputs after that single action, before the next. Hashes do not replace Task3's replay of actual bodies.

| Stage | Exact input preimage | Exact output preimage |
| --- | --- | --- |
| trigger | `{context_sha256,packet_sha256,detector_sha256,cue_id,previous_cue_sha256,current_cue_sha256}`. Detector is complete pre-transition detector; cue hashes are complete actual detector/packet cue records. | `{trigger}`: exact detector-produced validated trigger. |
| resolved (oracle only) | `{context_sha256,packet_sha256,trigger_sha256,source_m_sha256,source_world_sha256,case_sha256,event_evidence_sha256,before_occupancy,after_occupancy}`. Event evidence hashes complete independently checked Reach, and source M is the authenticated acquired M. | `{gold_target_ids,resource_sha256}`; resource hash is canonical sorted gold list. |
| installed (oracle only) | `{context_sha256,selector_before_sha256,input_lifecycle,resource_sha256,resolution_provenance_sha256}`. Input Lifecycle is pending; selector hash is actual detached pre-install config. | `{selector_after}`: exact config with only resource/resource hash/provenance changed to resolved IDs/hash/provenance; condition oracle, limit1, other fields unchanged. |
| selected | `{context_sha256,packet_sha256,trigger_sha256,live_m_sha256,selector_sha256,u_sha256,resources_sha256}`. Live M is the actual ordinary selection argument; resources hashes exact `selector_resources(config,u)` arguments, using only that arm's allowed resources. | `{selection}`: exact existing selection, sorted-ID/limit1; no second selector invocation. |

`resolution_provenance_sha256` hashes exact `{schema,context_sha256,input_sha256,output_sha256}`, schema `memory-oracle-resolution-provenance-vnext-v1`, with the **resolved** Stage hashes. This exists before installation and has no forward witness/commit edge. Selected oracle Lifecycle is `{status:'selected',resource_sha256:sha(gold_ids),provenance_sha256:resolution_provenance_sha256,selection_sha256:sha(selection)}`. This last hash is of the selection itself; Stage selected output hashes its `{selection}` wrapper. Nonoracle lifecycle stays not-oracle, with no source-M/evaluator input. Later selected resource/provenance is checked against strict4 selector and prior chain; it cannot masquerade as a new resolution.

Exact frozen in-memory `TransitionResult` fields are `status,proposed_state,bearing,decisions,input_lifecycle,local_lifecycle,witness,error,idempotent`. Error is a fixed private frozen `_ExceptionToken` holding the original Exception, captured exact type identity and independent canonical `{type,message}` bytes, or null; it is not serialized authority. `rethrow_transition_error_vnext(result:TransitionResult)->NoReturn` checks current type/message and any witnessed exception projection against those captured bytes immediately before raising the same original exception object. Tampering or unavailable projection refuses as infrastructure; no type-name lookup, reconstruction, global registry or callback invents a natural cause. Immediately before rethrow, verify the token still matches the detached captured exception projection; a changed token refuses as infrastructure rather than constructing a new natural error. A raised result is not a scientific verdict: Task3 independently proves an allowed natural cause or leaves it unscored infrastructure. Deep-copy **all** nested result projections from input, binding, local worker and each other: proposed state, both Lifecycles, decisions, witness and stage preimages cannot alias. Mutation of assigned Engine state or one result projection must not change another or a hashed witness. Frozen dataclass alone is insufficient. Pure result never asserts Engine commit.

| Result status | Exact valid combination |
| --- | --- |
| ordinary-return | Proposed strict4 state, two-float bearing, actual returned decisions; nonnull input/local Lifecycles, local equals proposed state's marker; witness/error null; idempotent false. |
| witnessed-return | Same proposed values, Witness result returned; witness exception/error null; idempotent false. Local Lifecycle is proposed, not committed. Includes an actual returned supervisor-failure state awaiting existing Engine failure handling. |
| raised | Proposed state/bearing null, ordinary returned decisions[]; input/local Lifecycles nonnull; Witness result raised and exact exception type/message; original error nonnull; idempotent false. Local Lifecycle may be selected although Engine input remains pending; only detached local effects are hashed/replayed. |
| idempotent | Detached strict4 input copy, cursor bearing, decisions[], equal detached input/local Lifecycles; witness/error null; idempotent true. No new calls/stages/journal update. |
| rejected | Proposed state/bearing null, decisions[], infrastructure error nonnull, idempotent false. Input/local Lifecycle null iff unavailable before a valid local snapshot. Witness absent for pre-validation/cap/serialization/index refusal; otherwise a post-validation reached refusal must produce bounded Witness result rejected with its actual defined local fields/stage prefix, never an optional success path. Never scored natural or eligible to resume. |

For a validated non-idempotent packet, emit exactly one Witness iff **T or E**: T is this condition's first valid oracle trigger while input Lifecycle pending; E is a pre-control raised transition, post-validation reached infrastructure refusal, or an actual returned supervisor-failure state. Same-transition T+E is one witness. Other arms have no T and at most their terminal E; their ordinary terminal-local trigger/selection, if any, is replayed with no evaluator stages. A later E after an earlier oracle T has no new gold/selection/stages unless those actions actually occurred in that same transition (a new oracle trigger after selected is an infrastructure rejection **before** a second call). Context/state/admission/sequence/identity/event/resource/cap failures are rejected; a bounded exception from the ordinary core after valid inputs is raised, whose natural eligibility still requires Task3 proof. The explicit pre-validation/cap/serialization/index refusal exceptions in the result table have no valid Witness and stop immediately; they cannot be disguised as a natural raised result. Owner cannot consume another packet after E/rejection. Input chain count must be0/1 for emission, index equals count, previous=context hash at0 or prior persisted Witness hash at1. Index≥2 or contradictory status/stage/gold/selection/state/Lifecycle refuses. Engine updates journal head/count only after Witness fsync; it assigns proposed state/Lifecycle only for returned results, and emits Commit only afterward. Journal persistence never implies local Lifecycle committed. This proves≤2 transactions/condition and≤2 genuine commit records without900×metadata.

Context descriptor metadata uses a proposed wire ceiling of1MiB per referenced metadata object and16MiB for source_snapshot. These descriptor-only maxima are not per-role payload permissions, six free metadata MiB, or a replacement for stricter inherited reader bounds (numeric V2 commit16KiB, conversion64KiB) or the combined1MiB output envelope. The later authentic consumer must apply the applicable stricter role bound. source_closure here means descriptor-only software closure, not the separate16MiB runtime-reference manifest. No referenced payload is opened by this pure contract.

Subcaps proposed **inside** existing byte/resource caps: canonical Context≤16KiB; complete serialized writer Witness event≤16KiB; Commit event≤2KiB; at most2 Witness plus2 Commit events per condition (first oracle-trigger transition and terminal pre-control transition; same-packet trigger+failure is one). Use hashes of local decisions, not a possibly64KiB decision-list copy. With≤4 fixed digest stages,≤1 target, bounded trigger/selection IDs,≤20 circles and bounded errors, 16KiB is a proposed conservative allowance; Task1 must prove exact worst-case encoded size from these shapes, including writer ASCII escaping/envelope/newline, before freezing it. If proof fails, revise this proposed subcap **within unchanged parent byte/resource caps** through review, not automatic adoption. A one-byte-over record refuses; no truncation. Context's original control copy plus its candidate/final copies are each physical allocations charged within their enclosing aggregate1MiB overhead and stage peak; witnesses/commits occur in original raw and each copied candidate/final events file under5MiB. Receipt/report/candidate metadata all share the existing1MiB combined ceiling: none is free reserve or assumed slack. Actual admission requires measured exact serialized totals and prior worst-case capacity proof; broad legacy input caps alone do not ensure convertibility.

Proposed witness-size derivation for Task1 to encode/check as a symbolic bound: fixed field/schema/enum text, punctuation, writer envelope and newline≤2048 bytes; all scalar/reference/stage/lifecycle hashes≤2048 (seven outer hashes +four Reach references +eight Stage hashes +six input/local Lifecycle hashes =25 quoted hashes×66=1650); all allowed ASCII ID material (four occupancy keys, five trigger IDs, selection event/target, gold and envelope IDs)≤2048; at most60 finite IEEE-float64 coordinates (≤24 JSON characters each) plus bounded counters/punctuation≤2048; two≤512-UTF8-byte exception strings require at most`2×512×6=6144` ASCII-escaped bytes. Sum≤14336<16384. Context's six descriptor records at≤768 bytes each plus all remaining IDs/hashes/fixed fields≤3584 gives≤8192<16384; Commit's fixed fields/hash/lifecycle have no unconstrained payload and fit≤2048. New D path alphabet makes the descriptor path subtotal unescaped. These are new shape-restricted software bounds, not measured data or accepted runtime serialization claims. Task1's worst-case authored serializer tests must verify each category and reject invalid family-ID/shape input before owner admission; a failed bound blocks adoption, never permits dropping a natural outcome afterward.

Identity DAG: schema/limits profile → descriptor-only software closure (including profile, worker/resolver/helpers/runtime requirements; excludes any later trust-anchor/pin module) → accepted source registration/commit/audit/SNP and typed application/M hashes → Context → fixed owner job (references Context) → actual prior world/sensed events → Witness body/stage chain → Commit (if actually committed) → terminal manifest/report/event close → independently produced TerminalProof/raw audit → candidate/conversion/pair/replay/condition commit → case/order/readout/analysis. No Context job hash (job references Context); no witness final raw hash (raw contains witness); no audit descriptor in raw that the audit hashes; no qualification receipt self-pinning its source closure. Source/context hashes authenticate identities only; independent replay and held custody establish the claims. Qualification/adoption authorities remain external and later, never supplied by these records.

### Exact successor adapters (no old-receipt impersonation)

Task1's proposed profile records exact inherited descriptors to the existing compact/numeric/analysis protocols but no new accepted pins. Task3's raw receipt is the old V4 exact raw-audit key set with schema `memory-family-raw-audit-vnext-v1`, successor `protocol_sha256`, and added `terminal_proof:D,context:D`; its new nested source identity is exact `{schema,protocol,owner_source_sha256,source_closure}`, schema `memory-family-raw-audit-source-vnext-v1`, protocol/closure `D`, owner hash `H`, not old V4 provenance. Task4's base manifest is the old compact exact manifest key set with schema `memory-family-compact-manifest-vnext-v1`, format `palimpsest-family-compact-vnext-v1`, successor protocol and added `terminal_proof:D,context:D`; first/last tick become nullable **only for the authenticated zero condition variant**. The numeric envelope is the current V2 exact envelope key set with schema `memory-family-numeric-manifest-vnext-v1`, format `palimpsest-family-numeric-compact-vnext-v1`, successor profile/base descriptors and added `terminal_proof:D,context:D`. All chunks/indexes/snapshot/field commitments keep their existing exact structures. New adapters validate successor receipts directly; never project a new receipt into an old-schema fake receipt to pass old readers.

Task5's pair receipt is the old exact pair key set with schema `memory-family-pair-vnext-v1` and successor protocol identity, replaces `oracle_result` with exact `{status,terminal_proof,source_m_sha256,event_evidence_sha256,resolver_sha256,gold_target_ids,selection_sha256}`: status `terminal-prefix-pass`/`reached-decision-pass`; unreached gold/selection null; no prior-own key or donor. All reached full proofs remain in TerminalProof and its independently replayed inputs. Qualification/replay result exact `{schema,protocol_sha256,case_id,run_id,context,terminal_proof,trace_digest,source_snapshot_reference,scope,rows_checked,model_inference_calls,raw_output_equal,action_equal,initial_hidden_sha256,final_hidden_sha256,claims}`, schema `memory-family-cell-replay-vnext-v1`. Scope `no-neural-call-terminal-prefix` requires rows/calls0, equality flags null, hidden hashes source-anchored unchanged, claims no condition model qualification; positive scope `observed-prefix-encoded-cell-only` requires every actual row/call and exact comparisons under accepted guarded qualification. No absent post-state SNP is called a matched endpoint. Claims remain all-false for qualification/allocation/publication authority unless separately supplied by existing accepted actual mechanisms. Successor registration/marker retain their old exact key sets with schema `memory-condition-terminal-registration-vnext-v1` / `memory-condition-terminal-commit-vnext-v1`, successor protocol/extension identities, add `context:D,terminal_proof:D`; registration removes `prior_own_receipt`. No public input can bypass the actual qualification gate or select a fake consumer.

Task6's case manifest/close/commit retain exactly `MANIFEST_KEYS/CLOSE_KEYS/COMMIT_KEYS` at `memory_family_case_publication_v1.py:254–256`, with successor schema strings `memory-family-numeric-case-vnext-v1`, `memory-family-numeric-case-close-vnext-v1`, `memory-family-numeric-case-commit-vnext-v1`, successor protocol/publication descriptors and added `source_reference:D` in each. Manifest retains the same exact analysis cells, ten run-receipt identities and sole source snapshot reference. Close inventory/directories cover owned stage/final case leaves only; externally referenced original source/raw/control objects are independently held and counted by their frozen inventories, never omitted from the enclosing ledger or falsely counted as copied case leaves. New case root and copy publication rule below require new readers; no old manifest is forged.

New condition/case quarantine exact `{schema,case_id,run_id,stage,error_type}` uses schema `memory-condition-quarantine-vnext-v1` / `memory-case-quarantine-vnext-v1`; case run_id null, condition run_id the canonical owner UUID; stage one of prepare/compare/replay/publish/revalidate/teardown; bounded ID error type, no unbounded traceback/error payload. Proposed maximum2KiB fits inside existing combined metadata allowance. Original sourceV2 quarantine remains its existing schema. Quarantine presence always refuses a positive read; failure to persist it leaves an indeterminate failed attempt, never permission to resume.

Task7's analysis design retains exactly the old `memory_family_analysis_v3.py:169–171` design fields plus `order:D,publication_profile:D`; verification retains its old exact fields (`:182–183`) plus `terminal_provenance:D,census:D`; readout retains its old exact fields (`:233–236`) and exact cell keys, with only versioned schema/protocol identities. Result retains the old exact analysis result keys. Their exact new schema strings are respectively `memory-family-analysis-design-vnext-v1`, `memory-family-analysis-verification-vnext-v1`, `memory-family-analysis-readout-vnext-v1`, `memory-family-analysis-result-vnext-v1`. Task7's proposed study protocol schema is `memory-terminal-vnext-study-protocol-v1`; Task1's software/schema profile is `memory-terminal-vnext-protocol-v1`. Registered original interval/guard arithmetic is factored/reused without adding receipt-shaped permission flags; actual accepted verification authorities stay external. No actual complete verification object is generated by this plan.

## Task 1: Exception-safe pure transition and canonical evidence

**Files:** ownership table Task1. **Consumes:** spec's source-M rule; legacy `advance_memory(state,packet)` and `validate_state`. **Produces:** strict4 validate/promote/configure/arm/inspection/goal wrappers and the fixed `rethrow_transition_error_vnext` helper specified above, plus `advance_transition_vnext(state4:dict,packet:dict,*,context:Context,oracle_binding:OracleBinding|None,reach:Reach,job_sha256:str,chain:tuple[int,str]) -> TransitionResult`; fixed internal `_advance_memory_core` (no public hook parameter) and exact result table above. Input Lifecycle comes only from validated state4, never a second caller authority argument. `OracleBinding` is an internal detached immutable data record containing exactly authenticated `source_m,case,source_world` matching Context hashes, with no callable/member setters; only oracle receives it. A dataclass/frozen flag does not authenticate its payload: the actual source consumer constructs it only while held source custody and external admission are active. `resolve_gold_vnext(binding:OracleBinding,reach:Reach,trigger:dict) -> list[str]` is the fixed internal resolver. Derive both occupancy maps from bound actual source geometry/current real circles and exact applied edit at the trigger cut; pre-cut `Reach` maps are null, and witnessed maps are outputs independently reproduced by Task3, never trusted caller flags. No evaluator lookup runs merely because the world changed.

- [x] Write red `tests/test_memory_transition_vnext.py`: `test_local_selection_then_cue_failure_preserves_detached_witness`, `test_input_and_all_nested_aliases_unchanged_on_success_and_exception`, `test_mutating_each_result_projection_cannot_change_other_projections_or_witness`, `test_every_stage_preimage_and_result_variant_is_exact`, `test_later_terminal_binds_prior_selection_without_new_gold_or_call`, `test_state4_rejects_direct_legacy_api_and_missing_or_mismatched_markers`, `test_promote_configure_arm_preserve_exact_source_view_and_declared_changes`, `test_source_m_gold_ignores_changed_live_m_but_selector_still_uses_live_m`, `test_null_empty_is_distinct_from_pending_noevent`, `test_repeated_consumed_packet_has_no_second_calls_or_witness`, `test_wrong_packet_digest_or_second_trigger_refuses`, `test_witness_predicate_index_and_commit_candidates_never_contradict`, `test_canonical_worst_case_witness_and_context_fit_subcaps`, `test_descriptor_quotes_backslash_control_and_noncanonical_path_refuse`. Use authored two-fact states/packets/geometry; spy only on existing selector to assert one actual invocation, no policy/physics objects. Assert raised proposed state/bearing null, local decisions hash matches actual pre-exception work, ordinary decisions are not invented, source/input mutation absent and no generic hook accepted. Mutate nested proposed selector/resource/Lifecycle/decision and witness copies separately to prove recursive detachment.
- [x] Run focused red command in the retained fresh test layout below; expect import/API missing or specified assertion failure, not fixture/protected-read failure.
- [x] Factor the current algorithm at `memory_decision.py:357–469` without moving a sensory/revision/supervisor cut. Legacy `advance_memory` keeps its signature, strict3 keys/version, returned tuple/exception and default behavior. Fixed private validators/core accept only validated3/4 from their respective strict entry wrappers; never publicly turn4 into accepted3. `validate_state:145–160` deep-copies; prove all nested aliases remain detached. Versioned builder captures the exact stage preimages at `:378–385` and local state/decisions on exception in one execution. Legacy exceptions remain exceptions; new result transports the same class/message control flow without committing local state.
- [x] Implement marked state4 Lifecycle outside ordinary M/E: after declared selector/U config at the genuine unarmed3 fork, promote its detached copy and bind context hash/pending or not-oracle marker. The syntactic oracle[] config is usable only by the strict4 branch; old validators reject4, and default Engine guard in2a refuses marker loss/mismatch. At the one valid trigger, resolve source-M gold, install resource/provenance, select with original live M and record detached local selected Lifecycle. No other arm receives evaluator truth or binding. Source acquisition/SNP stay3; all version4 configure/arm/inspect/goal helpers use fixed strict4 wrappers and exact source-view comparison, not old public projection.
- [x] Freeze exact proposed profile/schema/subcaps after proving record-size formulas; reject contradictory reached evidence, new/late/duplicate install and fresh passage evidence in every reached packet through decision. Mark proposed profile not adopted; no actual launcher or trusted pin.
- [x] Run Task1 green and legacy pure-memory regression files; exact assertions above pass with preserved outputs/exceptions and one selector call. Review source factoring/alias semantics before committing only Task1 files after root's implementation authorization.

## Task 2a: Private persistence helper and strict legacy default guard

**Files:** ownership table Task2a. **Consumes:** Task1 strict4/result/schema contract. **Produces:** private `Engine._persist_terminal_transition_vnext(result:TransitionResult,*,context:Context,job_sha256:str,chain:tuple[int,str])->None` and `_require_memory_transition_mode()->None`. No public opt-in, Task6 import, absent-class stub, fake/duck-typed custody object or integrated Engine claim in this task. Private authored helper tests are not public admission.

Fixed private journal fields are `_memory_terminal_vnext_mode` (literal
`memory-terminal-vnext-v1`), `_memory_terminal_vnext_context`,
`_memory_terminal_vnext_job_sha256`, `_memory_terminal_vnext_chain` and the
one-way stop latch `_memory_terminal_vnext_failed`. The finite manifest
indications are `memory_terminal_vnext_context_sha256` and
`memory_terminal_vnext_mode`. Presence, including null/partial values, refuses
the default path. The helper additionally consumes a fixed private
`_memory_terminal_vnext_route_anchor` datum when returned decisions are
nonempty: exact `{tick,stage,xy}`, stage `pre-control`, exact tick equal to
Engine total_tick and episode_step, and two plain finite floats. Validate it
before any write; ordinary decision events retain legacy
`route_anchor={stage,xy}` after Commit. Task2b must bind this datum from the
same actual sensing pose cut, and Task3 independently verify it. It is authored
data in Task2a tests, never a claim of actual pose/source authentication. Its
presence also refuses the default path. Do not omit the existing anchor or
derive pose from a transition that deliberately has no pose input.

- [x] Write red `test_default_engine_path_emits_no_vnext_events`, `test_default_refuses_state4_or_lost_context_lifecycle_mode_before_selection`, `test_witness_fsync_precedes_assignment_and_natural_rethrow`, `test_failed_witness_write_keeps_input_and_blocks_policy`, `test_failed_commit_write_records_actual_assigned_state_and_infrastructure_failure`, `test_assignment_cannot_mutate_detached_hashed_witness`, `test_trigger_plus_failure_single_transaction`, `test_background_writer_refused_for_vnext`. Authored Engine/RunWriter objects exercise only the private helper and default guard; ordinary fake env/policy raises if touched. No fake public held-source argument. Inject failures exactly before/after assignment; compare nested identities and canonical bytes.
- [x] Run Task2a red command, then implement the helper and guard without wiring an opt-in. For `memory-decision-v2`, guard at the start of `_step` before old validation/sensing/selection accepts only strict3 with no vnext state/manifest/mode indication. Any4/new marker/manifest context/bound-mode indication currently refuses as not integrated; inconsistent/removed markers refuse rather than call legacy oracle[]. Other scenarios are unaffected unless a contradictory vnext indication is present (then refuse). Genuine3 default behavior/events remain unchanged.
- [x] Helper requires synchronous writer (`records.py:213–234`). New event kinds are exactly `memory_transition_witness_vnext` / `memory_transition_commit_vnext`: existing Engine/RunWriter envelope keys `run_id,episode,tick,episode_step,sequence,kind` plus only `witness:Witness` / `commit:Commit`. Hash canonical Witness body; preserve actual spaced JSON/newline bytes. Confirm Witness fsync **before** updating journal or assigning proposed state/rethrowing. Assign a recursively detached proposed strict4 state only for returned/idempotent variants; Commit only for witnessed returned variant and only after real assignment, then ordinary returned decision events. Raised/rejected variants never assign local state/Lifecycle or fabricate ordinary decisions/Commit; retain witness if valid and use `rethrow_transition_error_vnext` for original class/message or infrastructure refusal, never directly raise its opaque token. Idempotent has no new witness/call/event. No result field claims commit.
- [x] A failed write/drain/identity/cap blocks later policy/physics and remains infrastructure-failed with partial evidence. Preserve actually assigned state after commit-write failure; no rollback fiction/900. A crash between fsync/assignment/commit is incomplete, never resumed. Zero retries. Run Task2a green plus legacy fixture checks; review helper/default guard only, not integrated opt-in. Commit only Task2a files after implementation authorization.

## Task 3a: Pure independent terminal/reached-transition proof

**Files:** ownership table Task3, serial ownership for3a then3b. **Consumes:** Task1 schemas/transitions and Task2a helper event semantics; authored raw fixtures until real Task2b integration/admission. **Produces now:** `prove_terminal_vnext(raw:dict,*,context:Context,source_application:dict,source_events:list,source_rows:list,deadline:float) -> TerminalProof` only. Pure raw has exact keys `{manifest,events,rows,worker_report,job,descriptors}`; descriptors has exact `{context,job,raw_manifest,raw_events,worker_report}` with proposed D bounds. Exact byte-versus-decoded-value representation must be settled before implementation: never derive an actual raw-byte identity merely by reserializing decoded input. Supplied source inputs and geometry are conditional premises, not held-SNP/native-placement/qualification authority.

Preflight found a real public custody dependency: the authentic fixed source
holder is Task6. The Task5 finalization registration includes this auditor's
outputs and cannot serve as its producer input. Public audit/validate APIs are
therefore deliberately absent in3a, not always-raising stubs or fake receipt
flags. Old source UUID-hex and new canonical-hyphen UUID requirements also need
an explicit successor source identity contract; no legacy byte relabeling or
global validator patch is permitted. The old nonempty reader and old manifest
envelope must not be used to admit zero-row successor data.

Task3a input representation is fixed as follows. `raw.job` is a D equal to
`descriptors.job`, not an invented partial owner-job body. Witness job hashes
must equal it; actual job-body/Context correspondence is an explicit premise
for3b to establish from held bytes. Context and worker-report descriptors bind
`memory.canonical_bytes`; manifest and event descriptors bind the unchanged
RunWriter `json.dumps(sort_keys=True,allow_nan=False)` representation plus a
newline per object. This proves equality to that deterministic representation,
not that physical originals used it;3b must compare the held original bytes.
Pure proof opens no repository or referenced file. Supplied source application
hash and exact event-prefix commitments must be checked, with nonempty source
rows, without claiming held-SNP origin or native placement authentication.

Manifest metadata remains the real extensible RunWriter object, with its whole
byte identity bound. Independently require the relevant fixed semantic fields:
run/case/condition/source lineage, closed status, recording format, configured
CPU FLYNN/device/eye state, counters/final state and original normal terminal
obligations. The new Context descriptor field is
`memory_terminal_vnext_context`, equal to `descriptors.context`; the existing
Task2a mode and Context-hash markers must agree. Unknown bounded metadata
confers no permission and cannot replace required fields. Do not claim a new
exact whole-manifest key set or forge the old admission envelope. Worker report
retains exactly `admission.REPORT_FIELDS` and data schema
`memory-family-owner-report-v3`, whose fields do not encode state3/4; verify its
contents independently. This is not reuse of an old qualification receipt.

#### Frozen Task3a semantic projection

Here M is the whole manifest, R the worker report, C the validated Context,
A the supplied source application, E the whole ordered condition event list,
and b=C.schedule.boundary_tick. K is the validated version3 case from
A.world_task_state.case. All counters below are exact nonboolean integers;
all required fields must be present. Metadata outside this projection stays
byte-bound and supplies no acceptance permission.

| Required path / evidence | Exact check |
| --- | --- |
| M.run_id | Canonical hyphenated UUID equal C.run_id. |
| M.memory_case | Validated world.validate_case, version3, exactly K; preserve K's actual split without relabeling. Existing public held-out GO remains separate. |
| M.memory_case_sha256 | H equal C.case_sha256 and sha256(K); K.case_id equal C.case_id, K.kind equal C.kind. |
| M.seed, M.acquisition_protocol_sha256 | Exact integer K.seed; H equal K.acquisition_protocol_sha256. |
| M.controller, M.requested_device, M.teacher_privileged, M.texture | Exactly `flynn`, `cpu`, boolean false, `checker`. |
| M.scenario | Exactly existing pure validate_decision(world.SCENARIO,'checker','flynn',profile_sha256=K.profile_sha256) result. |
| M.recording_format, M.recording_max_bytes | Exactly `palimpsest-npz-v1`, integer384*1024**2. Physical byte total remains3b's obligation. |
| M.parent_run_id | Equal C.source_run_id and A.source_run_id. No UUID normalization of original bytes. |
| M.parent_event_prefix | Exact keys sha256,size_bytes,event_count, equal A.event_prefix; H and nonnegative integer byte/count fields, checked against the deterministic supplied source-event prefix through its actual acquired cut. Source rows nonempty. |
| M.memory_terminal_vnext_mode | Exactly `memory-terminal-vnext-v1`. |
| M.memory_terminal_vnext_context_sha256, M.memory_terminal_vnext_context | sha256(C), and D exactly raw.descriptors.context respectively. |
| M.memory_family_oracle_admission_v3 | Must be absent; an old envelope cannot stand in for successor semantics. |
| Condition / owner binding | R.condition equals C.condition (one of nine), R.run_id equals C.run_id; raw.job D equals descriptors.job and every Witness job hash. Actual job body, resource/closure execution and source authority remain explicit3b premises, not manifest flags. |
| M.recorded_ticks | n=len(rows), integer0..900. |
| M.recorded_chunks | Integer equal number of chunk events, ceil(n/32), at most29; zero exactly no chunks. |
| M.recorded_events | Integer equal len(E), at most50000; E has exact consecutive sequence values. |
| Chunk events / rows | Contiguous chunks/{i:06d}.npz, episode integer0, start=b+32*i, positive count=min(32,n-32*i), required H. Rows exactly ticks b..b+n-1, same inherited required fields/dtypes/shapes and policy/array digest obligations. No fake zero row or chunk. Chunk container bytes/inventory remain3b premises. |
| M.total_tick, R.total_ticks | Equal integer b+n, at least1. First/last motor ticks null iff n=0, otherwise b and b+n-1. |
| M.world_state, R.world_state | Equal validated state2, exact K/profile/schedule/acquired hash and independent replay of supplied applied-world events from A.world_task_state. Last_tick b+n for a terminal sensed tail, otherwise b+n-1. This is the worker-added world_state field, not an invented Engine final-memory field. |
| M.status, M.final_phase, R.final_phase | Status failed iff phase failed; otherwise completed with terminated/truncated. Phases equal; no generic paused early-prefix acceptance. |
| M.last_outcome | Exactly the sole verified terminal runtime_failure.error or episode_finished.outcome, with preserved exact nested schema/types. |
| M.metrics | Exact reward,contact_ticks,path_length keys; reward/path finite floats, contact_ticks nonnegative integer. Match A.metrics plus actual continuation row rewards/collision flags/path using original accumulation order. Each path increment is exactly float(np.linalg.norm(next_pose[:2]-pose[:2])), matching Engine; proof path_length accumulates the same increments from zero. |
| M.close_reason | Exactly `operator_closed`. |
| R | Exactly admission.REPORT_FIELDS; schema memory-family-owner-report-v3; run_id/case_id/condition equal C, operation condition, status recorded, acquired boolean true; both snapshot hashes equal C.source_snapshot.sha256. Other fields equal M as above. |
| Eyes / initial application | A.eyes and actual application_restored.eyes exactly {left:true,right:true}; restored parent prefix/source revision equal A at b; restored world.pose and first condition pose equal the last supplied source row.next_pose (A has no pose member). Every positive row has full eyes; eyes_changed and original forbidden replacement/replay events refuse. No M.eyes or synthetic run_started requirement. |
| Configuration / arm | Exactly one condition configure/promote/arm chain from supplied A.memory strict3, actual configured resource hash equal C.condition_resources_sha256, Context/schedule/source invariant agree. No manufactured final SNP or final memory member. |
| Assigned memory | Replay once per actual sensed packet. Assign only returned proposals; compare exact strict4 memory_inspected at every reached returned inspection and exact journal/Commit order. Raised local state remains local Witness evidence. |

Positive motor rows require their actual sensed/cue/inspection/policy-call
ordering and all original row/policy bindings. A terminal pre-control sensed
tail is at b+n and requires n<900 and b+n<min(2100,b+900). At n=900
the Engine already stops after its last motor row: only a row-backed normal
terminal satisfying the original cap/outcome checks is possible, never another
sensed-tail advance. There are two exact existing mechanism branches: (a) replayed
CueUnavailable with the same type/message, no Commit/ordinary decisions/
inspection/cue/policy after its raised transition; (b) replayed returned
supervisor failure with Witness, Commit, actual ordinary decisions and
memory_inspected, then the existing Engine ValueError message
`Memory-v2 supervisor failure: ` plus that replayed failure_reason, with no
cue/policy/motor afterward. Either may have n=0; zero motor rows alone say
nothing about whether a transition committed. Unknown exceptions or unproved
causes refuse rather than becoming900. This creates no new exception class
or arbitrary ValueError permission. Normal row-backed goal/stalled/collision/
time_limit terminals retain the full original normal-terminal requirements,
including reached decision and exact cap/outcome/metrics/episode_finished
ordering. Pure proof still cannot certify physical bytes, custody or admission.

- [x] Write red authored all-nine `test_zero_one_two_and_full_prefixes_all_arms`, `test_world_applied_without_trigger_stays_pending`, `test_selected_then_exception_replays_local_not_committed_state`, `test_terminal_packet_fresh_passage_before_decision_refuses`, `test_spoofed_flags_and_witness_hash_chain_do_not_replace_transition_replay`, `test_unknown_exception_or_missing_reached_proof_is_unscored`, `test_normal_malformed_evidence_cannot_fall_back_to_prefix`. Assert supplied source rows remain nonempty, declared source SNP identity plus supplied application/event-prefix/invariant bindings agree (physical SNP custody waits3b); exact zero motor counters/calls/path/900; independent packet reconstruction and exact exception target/message/cursors; no postterminal progress.
- [x] Run Task3 red command.
- [x] Reuse compatible pure array/policy-binding helpers and source application/geometry reconstruction (`raw_audit_v4.py:296–384,405–456,663–715`; `oracle_v3.py:340–400,452–484`; `memory_decision_world.py:486–537`). Under supplied-source premises, verify edit acceptance and world before deriving occupancy; replay every sensed packet using Task1, checking reached no-fresh-passage invariant, source-M cardinality and every witness/commit/ordinary event sequence. Compare local effects on raised transition separately from assigned Engine memory. A JSON validator or producer flag is insufficient; physical custody/inventory belong3b.
- [x] Preserve all normal/full terminal obligations when reached. Proved early natural failure is900; owner/audit/custody/resource/unknown/absent reached proof remains incomplete/unscored. Do not create any new natural exception type. Version raw limit support only for condition n=0; positive n contiguous from b, chunks ceil(n/32); exact empty list/index for zero, metadata/events/report still nonempty; old source/nonempty APIs unchanged.
- [x] Run Task3a green and negative exact byte/shape/count/cap and one-byte-over authored cases under unchanged caps. Review reproducible terminal cause versus operational disposition and conditional premises; commit only Task3 files after authorization. Held-inventory/custody/publication negatives wait for3b.

### Task 3b (after6): Authentic public terminal audit adapter

Pending reviewed design and implementation, not completed by3a. Produces
`audit_terminal_run_vnext(run_path:Path,receipt_root:Path,*,registration:dict,deadline:float) -> dict`
and `validate_terminal_receipt_vnext(run_path:Path,receipt_root:Path,*,registration:dict,deadline:float) -> dict`.
Use the real Task6 fixed holder, held-path/exclusive-publication primitives and
actual source registration/qualification checks. Before code, freeze the exact
pre-audit producer registration without output/self edges, root/location
binding, source identity compatibility and lifecycle close. The final receipt
remains the successor contract above; no old-receipt impersonation or
qualification bypass. Exact inventory/custody/publication failure tests belong
here;3a's authored byte/shape refusal tests do not establish those properties.
Tasks4/5/6 may not claim actual acceptance through a missing3b receipt.

## Task 4a: Conditional pure empty/early compact numeric preservation

**Files:** ownership table Task4a, serial ownership for later4b. **Consumes:** independently established conditional Task3a TerminalProof, never a fabricated old raw-audit receipt. `receipt` below is exactly that proof, whose source replay validity remains a premise. **Produces:** `convert_terminal_numeric_vnext(raw:dict,*,receipt:dict,context:Context,external_overhead_bytes:int) -> dict[str,bytes]`; `read_terminal_numeric_vnext(bundle:dict[str,bytes],*,receipt:dict,external_overhead_bytes:int) -> dict`; `prove_terminal_numeric_vnext(raw,bundle,receipt,*,external_overhead_bytes:int) -> dict`. No public source/condition authority.

The actual Task4 schema strings in the successor-adapter section above are
reserved for later4b. Task3a supplies no published condition raw-audit D or
owner-source identity; neither can be derived from unrelated Context hashes.
Task4a therefore has a distinct PURE wire format. In its envelope `raw_audit`
and `source_identity` must be exactly null; readers refuse nonnull values.
Pure output cannot be relabeled as accepted output or grant permission by
injecting a digest or claim flag. Inherited claims remain false.

### Frozen Task4a wire and inputs

- Base schema `memory-family-compact-pure-manifest-vnext-v1`, format
  `palimpsest-family-compact-pure-vnext-v1`; numeric envelope schema
  `memory-family-numeric-pure-manifest-vnext-v1`, format
  `palimpsest-family-numeric-pure-compact-vnext-v1`.
- Base exact keys: compact.MANIFEST_FIELDS plus terminal_proof and context.
  Envelope exact keys: numeric.ENVELOPE_FIELDS plus those same two fields.
  Index/entry exact keys and index schema strings remain inherited. First/last
  tick are null iff zero; snapshot_event_prefix is null for this condition-only
  codec. audit_schedule has exactly event_tick and decision_tick, equal the
  corresponding Context.schedule projection; boundary_tick binds separately
  through proof/row intervals. event_tick is null only no-event.
- Exact output members are numeric-pure-vnext.json, numeric-index.json,
  terminal-proof.json, context.json, base/manifest.json,
  base/legacy-manifest.json, base/legacy-events.jsonl, base/chunk-index.json,
  base/audit-frames.npz, plus base/chunks/{i:06d}.npz and
  numeric/{i:06d}.npz for each partition. Thus9+2*k files, exactly9 at zero.
  No partition at zero, no extra/duplicate/alias/trailing members.
- Raw exact keys: terminal_raw, recorded_manifest_bytes,
  recorded_events_bytes, snapshot_reference. terminal_raw has exactly Task3a's
  six input keys. Both recorded payloads are built-in bytes, equal the unchanged
  writer encoding of decoded objects and the proof D hashes/sizes, and copied
  without alteration. This verifies supplied representations, not physical
  original-byte custody. The codec opens no caller-referenced paths.
- snapshot_reference retains the inherited exact six fields; kind shared-source,
  source_run_id and SNP D equal Context. Its supplied source_receipt_sha256 is
  specifically a source CONVERSION digest. It remains a conditional declaration,
  not an inferred value, proof of that conversion or source authority.
- Output context and terminal_proof D refer to their actual copied members.
  The proof's own Context D still identifies its original input; validate the
  common bytes/hash/size without silently rewriting that original descriptor.
- New profile file schema memory-terminal-numeric-pure-protocol-vnext-v1 freezes
  these pure wire rules, limits and inherited16+3 array layout. It references
  terminal_profile D (exact Task1 profile) plus inherited_base_protocol and
  inherited_numeric_protocol D for the existing actual parent protocol files.
  No self/source-code hash or accepted pin. Base protocol_sha256 is the new
  profile hash; envelope protocol/base_protocol are its D (one profile describes
  both PURE layers). Context.profile equals the profile's terminal_profile D,
  not the new codec profile. Later external closure must bind code/profile.

### Frozen Task4a per-API bindings and preservation scope

Every entry point validates the exact Task3a TerminalProof key set, schema,
descriptor/reference types and bounded lists, exact nonboolean counts and
booleans, finite metrics/outcome types, and their coherence. Proof validity from
source replay remains the explicit premise, not a replacement receipt flag.
Bind proof boundary_tick, source_snapshot and invariant to validated Context;
goal, outcome, capped_ticks, path_length, row/chunk counts, first/last motor
ticks and terminal_sensor_tick must retain Task3a's zero/positive/normal/tail
relationships. Both manifest layers, copied recording metadata/events,
partition census and proof agree on owner/case/condition, operation condition,
counts and interval. Validate available Witness/Commit references against the
copied complete events, not caller reached flags. A normal terminal still
requires the original full decision/cap/terminal obligations.

| API | Required checks / permitted claim |
| --- | --- |
| All | New profile and exact Task1 Context profile relationship; canonical proof and Context, fixed copied-member D bindings; every available proof count/interval/sequence/trace/terminal binding; strict schema/array/container/census/role/ledger checks. Bundle terminal-proof.json equals canonical_bytes(receipt) exactly. Proof.context still binds the original input Context bytes/hash/size; copied context.json D binds the same bytes at its new fixed member, without rewriting the proof's original path. |
| convert / prove input | terminal_raw's five descriptors equal the proof's five D exactly; raw.job equals proof.job. Bind canonical worker_report bytes and both recorded payloads to their proof D. Decoded recording objects must encode exactly to those supplied bytes. Validate plain decoded array/safe scalar types before any inherited numerical coercion; no opaque loader/subclass hook. Actual job body, physical original bytes and raw origin remain premises/3b duties. |
| read | Recompute ASCII trace and the camera/row sequences from stored digest arrays, compare with both manifest and proof, validate selected pixels against camera digests, and verify copied bytes/index/chunk mappings. These are stored-format/commitment checks, not reconstruction of opaque original row digests or authentication of every retained field. The reader lacks most raw pixels and the proof excludes latency/step_latency from row digests. It cannot independently assert original raw timing equality or complete raw-array equality. Returned raw_comparison_performed is false and actual_acceptance is false. |
| convert / prove raw comparison | Independently project supplied raw rows and rederive original row/camera/ASCII-trace commitments, comparing them with the proof. Compare every retained base field and all three companion fields by exact dtype.str, shape and tobytes, selected pixel bytes, and copied recording/proof/Context bytes. Conversion verifies its actual encoded result before returning; prove performs the comparison explicitly. Only this performed comparison may report raw_comparison_performed true. It proves equality to supplied raw, not physical source authority; actual_acceptance stays false. |

No entry point may claim all retained values are authenticated by opaque
per-row digest arrays. Internal hashes alone cannot authenticate a caller's
rewritten bundle. Task4b must separately authenticate conversion/bundle identity
and raw origin through the genuine held receipt/publication path. No new
timing digest, Task3a proof-schema change, fabricated receipt or actual adapter
is required in4a. Preserve the inherited false claims and explicitly document
reader-only versus performed raw-comparison scope in the profile/API results.

### Frozen Task4a limits and accounting

Context<=16KiB; canonical proof, recorded manifest, report/job D and each
base/envelope/index JSON<=1MiB individually, with the shared1MiB limit stricter.
Source SNP identity remains nonempty<=16MiB. Recorded condition events are
nonempty<=5MiB. Audit frames use min(inherited1.5MiB, count*98312+4096);
base partitions count*19534+8192; companions retain count*112+4096. Require
the fixed NPY v1/C-order/128-byte header schema and stored ZIP limits before
decoding and exact re-encoding afterward. Keep all inherited field dtype/shape
and role restrictions; source commit16KiB/conversion64KiB byte limits still
apply when those actual payload roles are present, not merely a digest premise.
Sixteen selected camera pairs occupy1.5MiB before container headers, so that
cardinality may fail the unchanged1.5MiB frame-file cap. Retain the resource
refusal; do not raise the cap or drop policy-selected frames to fit.

external_overhead_bytes means the caller's COMPLETE distinct external metadata
cost, not an additional amount above a separately added floor. Its mandatory
known floor is canonical proof + canonical Context + declared raw-manifest,
worker-report and job byte sizes. Require external>=floor, never add it twice.
This prospectively charges original declared metadata copies beside bundle
copies; it is not a physical measurement or a free reserve. Let T be actual
sum of bundle bytes plus external. Metadata overhead is T minus the verified
19646*n dense bytes,98304*selected-frame-count pixels and actual copied event
bytes. Container/NPY headers, all proof/Context/reference/support copies remain
charged. Require total<=25MiB and shared metadata<=1MiB, alongside each5MiB
event-file bound. An excessive floor refuses. Additional distinct controls,
markers/profile copies and other external costs remain the caller's declared
premise; no physical lifetime/RSS/stage peak completeness is claimed. Original
raw events/SNP stay in the separate physical raw/source ledger, never compact
subtractor slack or permission to remove raw.

Test genuine Task3a-proof-admitted conversions for0/1/2/31/32/33 where they fit.
The authored900 normal recording exceeds5MiB and remains an unscored resource
refusal, not a positive conversion. Private fixed partition primitives may
exercise900 numeric rows solely for wire-boundary coverage; do not fabricate a
900 TerminalProof, drop events/IDs/inspections or waive a cap to make a public
conversion pass. Such primitive coverage is not admission or paper evidence.

- [x] Write red `test_zero_numeric_has_no_partition_and_typed_empty_frames`, `test_fitting_one_two_31_32_33_rows_preserve_all_bytes`, `test_900_numeric_primitive_is_not_proof_admission`, `test_signed_zero_latency_population_and_commitments_are_exact`, `test_old_reader_refuses_successor_and_new_reader_refuses_old_or_malformed_full`, `test_extra_duplicate_missing_member_or_census_refuses`, `test_combined_metadata_and_event_caps_include_every_copy`. Authored NumPy arrays only; no sample rows/models.
- [x] Run Task4 red command.
- [x] Reuse existing 16 base +3 companion numeric arrays/partitions, little-endian shapes and exact byte proof from numeric V2 (`numeric_preservation_v2.py:20–31,86–106,119–137,170–217,300–314`), original legacy ASCII trace and binary sequence formulas, copied event/manifest bytes and selected-pixel rules. Factor fixed pure codec primitives only where old whole-reader/provenance validation cannot be reused; do not impersonate old audit receipts or monkeypatch protocol globals. New profile identifies that shared code closure. No duplicated generic converter framework.
- [x] For zero condition: empty base/companion indexes, no partition; first/last motor null; audit ticks `<i8 (0,)`, raw left/right `|u1 (0,128,128,3)`; no `stack([])`/fake image/row. Positive prefixes use exact original rows and in-range selected schedule, including all timing and `(3,4)` population arrays/order. Preserve source SNP reference and empty-sequence commitments; terminal packet belongs to events, never motor rows. Source codecs remain unchanged/nonempty. Preserve all existing omissions (most full pixels; no perception/physics replay).
- [x] Count Context/TerminalProof/receipts/conversion/support/controls/markers in combined1MiB overhead, witness and commit bytes in actual5MiB event cap, companions/header/index bytes in actual25MiB total and all declared distinct external metadata copies in the pure serialized ledger. Physical raw+stage+candidate/final peaks remain later held-ledger obligations, not a passed4a check. Exhaustive dtype/shape/bytes equality; no allclose, outcome drop, fallback or cap increase. Run green/maxima/one-byte-over negatives. Commit only reviewed Task4a files after authorization.

### Task 4b (after3b): Actual receipt adapter

Not implementation-ready and no stub/API is produced in4a. Freeze a separate
real raw-audit/source-identity/held-input contract after3b exists, then review
the actual successor envelope specified above. It must not promote pure null
authority fields or a caller flag into accepted provenance. Tasks5/6 actual
acceptance waits for3b/4b; pure array preservation alone cannot admit a study.

## Task 5: Pair, guarded replay scope, closed public condition route and endpoints

**Files:** ownership table Task5; any private shared-helper factoring requires root review of exact additional files first. **Consumes:** Tasks1–4; existing accepted guarded-loader/custody/publication primitives. **Produces:** `prove_pair_vnext(source:dict,condition:dict,*,context:Context,terminal_proof:TerminalProof,deadline:float) -> dict`; `replay_terminal_vnext(condition:dict,*,qualified_inputs,terminal_proof:TerminalProof,deadline:float) -> dict` (qualified_inputs is the existing guarded held-policy context, never caller JSON); `seal_terminal_condition_vnext(evidence_root:Path,registration:dict,*,case_id:str,condition:str,deadline:float) -> dict`; `read_terminal_condition_vnext(evidence_root:Path,registration:dict,*,case_id:str,condition:str,deadline:float) -> dict`; `terminal_cell_vnext(result:dict,*,case:dict,source_snapshot:dict) -> dict` matching the old analysis cell exact keys.

Task5's authored proof/sealer-reader tests may use Task1/2a-produced fixture evidence. This is not an integrated owner route; actual closed-raw acceptance additionally awaits real Task2b branch integration plus independent qualification/admission. Public actual entry remains pre-read refused at its existing-style qualification gate, without importing an absent Task6 class; no fake public capability or future-class import bridges the dependency. Private fixture proof tests do not claim a production owner/sealer round trip.

- [ ] Write red `test_zero_scope_is_not_condition_model_replay`, `test_positive_prefix_replays_every_actual_row`, `test_missing_qualification_refuses_before_loader_or_output`, `test_all_nine_resources_and_source_invariants_are_bound`, `test_no_prior_own_dependency_but_missing_reached_gold_refuses`, `test_disk_reread_and_marker_last_failure_remain_incomplete`, `test_endpoints_zero_and_short_failure_keep_900_and_actual_path`. Authored private consumer fixtures only; public route has no fake-policy argument, and an unaccepted actual receipt must fail before import/output.
- [ ] Run Task5 red command.
- [ ] Zero returns scoped no-call integrity result only (not vacuous raw/action equality); require nonvacuous accepted source-cell qualification separately. Positive rows reuse existing guarded immutable loader and bitwise cell consumer (`memory_family_cell_replay_v4.py:51–129,157–210`; `memory_condition_replay_admission_v1.py:52–58,159–168,240…`), preserve caller/tensor state and exact-runtime receipt custody. Do not broaden old trust roots or admit source/seed through a caller flag. New actual pin set stays empty; no CLI executes a condition or qualification in this deliverable.
- [ ] Reuse condition seal/read held-custody/on-disk equality/independent pair/marker-last/failure/quarantine semantics (`memory_family_condition_seal_v4.py:474–656`) through reviewed fixed helpers. Successor profile binds no donor; every other condition mapping/U/history identity and reached proof remains exact. Producer-supplied proof/status cannot qualify itself. Preserve raw, partials and refusal to prune.
- [ ] Derive goals from independently checked terminal reason/radius (zero never goal), actual count and ordered XY path sum, capped900 and source invariant; preserve own/sham and all-nine no-event equality including terminal/outcome/count/path/invariant, plus actual zero resolver/selector for no-event. Run Task5 green with failed-before/after-publication and closed-gate tests; commit only reviewed files after authorization.

## Task 5a: Independent conditional resource/history mapping

Root freezes the [exact pure pair contract](../reports/memory-terminal-pair-contract-2026-11-06/contract.md).
This closes a concrete gap beyond3a: registered nonoracle U/selector/history
mapping, with an independent E-only refit and complete fresh3a proof equality.
Ownership is the new terminal_condition_vnext script and focused test only.
Supplied history bodies/descriptors are conditional value premises; physical
origin, seed/relation/profile registration and custody are not certified.
Oracle remains pending until reached gold is independently reconstructed;
no prior-own receipt, loader, qualified flag or actual adapter is introduced.

- [x] Genuine authored held-source positive, all-nine mapping/forgery negatives,
  zero/short natural endpoint cases and input preservation.
- [x] Required focused TDD and independent spec/code review.

Accepted conditional source: [Task5a evidence and limitations](../reports/memory-terminal-pair-pure-review-2026-11-06/README.md);
159 passes/no skips, independent SPEC PASS/QUALITY APPROVED.

Pair equality does not establish cross-condition equality. Own/sham and all-nine
no-event checks remain complete-family6b/7 obligations, including terminal/count/
path/outcome/invariant and actual no-event nonuse. Task5a does not complete Task5,
actual replay/seal/read, source/backend/accounting, study or deletion gates.

## Task 6: Source consumption, case publication epoch and physical census

**Files:** ownership table Task6. **Consumes:** Task5 exact cells/receipts. **Produces:** `open_source_numeric_vnext(evidence_root,registration,*,case_id,deadline) -> ContextManager[HeldSourceVnext]`; `read_source_numeric_vnext(evidence_root,registration,*,case_id,deadline) -> dict`; `read_terminal_case_vnext(evidence_root,registration,*,case_id,deadline) -> dict`; `publish_terminal_case_vnext(evidence_root,registration,*,case_id,deadline) -> dict`; `check_terminal_census_vnext(inventory,*,scope) -> dict`. `HeldSourceVnext` in `scripts/memory_family_source_consumer_vnext.py` exposes read-only detached `context,case,source_application,source_world,source_m,source_snapshot_reference` and fixed `recheck()->None`; internally owns existing held-path descriptors/ExitStack and active lifetime, no supplied callbacks. Private construction occurs only after source/qualification/admission checks; read returns detached data without claiming a still-active lifetime. Pure software/closed public adapters only; actual study execution remains unavailable.

- [ ] Write red `test_successor_census_counts_source_raw_stage_final_and_failed_copies`, `test_old_41_49_418_gates_remain_unchanged`, `test_source_v2_requires_new_consumer_and_actual_authority`, `test_unregistered_or_one_over_successor_census_refuses`, `test_copy_publication_keeps_stage_source_and_snp_paths`, `test_failed_copy_or_teardown_never_admits_case`. Authored held-file fixtures only; no actual source/model/SNP access.
- [ ] Run Task6 red command.
- [ ] Implement the explicit successor census below, with new case/source-consumption/protocol descriptors and exact per-directory reads. Old physical gates remain unchanged: condition `len(bundle)+len(support)+1≤41` (`condition_seal_v4.py:346–398`); old conversion inventory≤36/46 and owner≤41/49 (`retained_case_v1.py:37–56`); old case source+conditions≤418 files/33 directories (`memory-case-publication-v1.md:191–197`). They are compact-publication counts, not raw-only counts. Do not route numeric V2 through those readers or relabel its provisional source marker as qualified. New source consumer must independently bind the original retained raw/SNP, V2 bundle/marker/registration, externally accepted source qualification and lifetime authority. Existing public sourceV2 remains development-only; a held-out source needs its own separately admitted successor source registration/consumer, never a fake development label or weakened old gate.
- [ ] Keep source V2 layout and numerical proof primitives; do not introduce a merged19-array carrier merely to fit old41. A packed carrier would create another format/qualification burden without resolving global byte/custody constraints and is rejected from this plan unless V2 later proves impossible for an independent reason requiring a new reviewed decision. New finite **file/directory census** is an explicit unqualified software-policy proposal under root's design ruling; it changes no old count cap or actual authority. Existing byte/CPU/wall/RSS and1MiB overhead ceilings remain. An over-byte/unknown-accounting case refuses even if it fits this count proposal; no failed/partial raw is removed to fit.
- [ ] Run Task6 green including source consumer live-custody checks and failed copy/marker/fsync/teardown. Independently review exact source/schema/census/byte closure. Keep actual acceptance sets empty and retain all staged/final/raw failures. Commit only reviewed Task6 files after authorization.

## Task 6a.1: Fixed authored source custody prerequisite

Root accepts the exact narrow contract in
[authored-source-contract-addendum-var-tmp.md](../reports/memory-terminal-custody-preflight-2026-11-06/authored-source-contract-addendum-var-tmp.md),
with the [exact inherited profile-byte clarification](../reports/memory-terminal-custody-preflight-2026-11-06/authored-profile-byte-rule.md),
and the [fixed output topology rule](../reports/memory-terminal-custody-preflight-2026-11-06/authored-output-topology-rule.md),
including predecode SNP expansion limits and the distinction between current
root custody and unproved exclusive creation history. It supersedes the older
preflight's unbound/rebinding suggestion only for this authored slice. Ownership
is exactly `scripts/memory_family_source_consumer_vnext.py` and its focused test.
The [nested FD-drain amendment](../reports/memory-terminal-custody-preflight-2026-11-06/authored-nested-fd-drain-rule.md)
additionally authorizes teardown-only repairs in compact/replay-custody primitives,
with all stat/hash/path/format/qualification rules unchanged.
Implement one genuine private authored opener and fixed holder, one immutable
condition slot, actual held files/decoded nonempty source/derived Context,
complete rechecks/detached views and teardown. Public actual factories and
Engine opt-in remain absent; no actual Q/L/R/admission-shaped fixtures.

- [x] Genuine authored positive and OS custody/role/source/slot/lifetime negatives.
- [x] Required TDD and focused software checks; independent spec/code review.

Accepted source-only: [Task6a.1 evidence and limitations](../reports/memory-source-authored-holder-review-2026-11-06/README.md).
Settled208 passes/2 historical skips; independent SPEC PASS/QUALITY APPROVED.
This checks neither actual6a.2 nor any study/admission box.

Order for this bounded prerequisite is 6a.1 before later separately reviewed
3b/4b/2b and Task5/6b integration. It does not make actual6a.2 or those adapters
implementation-ready. Actual source production/bootstrap, replay qualification,
namespace/capacity, complete finite process accounting and accepted final
endpoints remain required. A source-production lifetime record cannot cover
later finalization, registrations, holders or bespoke final-reader CPU.
No provider exemption, accounting policy, global census, study or deletion
authority is adopted. The full completion objective and all other gates stand.

## Task 2b (after6): Authentic opt-in and integrated strict4 Engine branch

**Files:** ownership table Task2b. **Consumes:** Task1 strict4 APIs, Task2a persistence/default guard, Task6's actual fixed `HeldSourceVnext` class/private constructor/recheck logic. **Produces:** `Engine.configure_memory_terminal_vnext(context:dict,*,held_source:HeldSourceVnext)->None` and the integrated private `_advance_memory_terminal_vnext(packet:dict,reach:Reach)->None`. Before this task these interfaces do not exist as integrated public capabilities. Import the exact Task6 class only inside this new opt-in path after its module exists; legacy import/default path has no eager Task6 dependency. No duck typing, class stub, dynamic loader override or caller-provided sink.

- [ ] Write red `test_integrated_vnext_branch_uses_fixed_admitted_source_and_strict4_helpers`, `test_real_public_source_admission_refuses_before_payload_or_output`, `test_integrated_marker_context_lifecycle_or_mode_loss_refuses`, `test_integrated_other_eight_arms_receive_no_evaluator_binding`, `test_integrated_selected_then_cue_failure_has_witness_without_state_commit`, `test_integrated_return_has_commit_after_assignment`, `test_legacy3_default_still_unchanged`. Integrated authored test obtains the real fixed class through **Task6's reviewed fixed internal authored-admission seam**, with real constructor/recheck/held authored-file checks; no fake public held source. Test real public pre-read refusal separately without that isolated seam. If Task6 has not specified/reviewed that seam and exact constructor/recheck, Task2b is blocked, not simulated with a stub.
- [ ] Run Task2b red command after Task6 green/review. The ordinary declared selector/U configuration occurs exactly once while Engine still holds3 (existing configuration event preserved); opt-in validates that configured fork and promotes its detached copy with Task1, rather than configuring again. Bind held context/manifest mode, compare exact full source invariant before arm, then use strict4 arm/inspection/acquired/goal wrappers throughout this branch. Save `memory_terminal_vnext_context:D` in the opt-in manifest. Default guard now permits4 only with exact active fixed held-source type/lifetime/context and matching state/manifest/Lifecycle; source recheck failure or mode/marker loss refuses before selection/policy. Old3 functions/default behavior stay strict and unchanged.
- [ ] Wire only `engine.py:838–858`'s versioned branch and the corresponding fixed4 helper calls. Preserve world application→sensing order, use existing sensed pose/circles without another sensor/native/motor call, and retain at most the current sensed plus three world/intervention records with actual sequence/body hashes (≤4). Call Task1 once, then Task2a helper. Only oracle gets immutable binding/resolver; all other arms get None and terminal-integrity recording only. Validate actual event/occupancy at the real cut, not scheduled labels; preserve no ordinary update/RNG work between resolve/install/select.
- [ ] Run integrated green/default regressions and independently audit genuine branch event order, nested detachment,≤2 witnesses/commits, pre/postassignment failure, no extra calls, real public refusal and Task3/4 replay of that same authored branch evidence. Do not claim integration from private persistence tests alone. Source-code delivery still grants no actual owner, model, qualification or GO. Commit only reviewed Task2b files after implementation authorization.

## Task 7: Complete-family study identity, unchanged estimators and closed handoff

**Files:** ownership table Task7. **Consumes:** Task5 exact cells, Task6 source/case/census descriptors, completed/reviewed Task2b actual branch integration (still no actual execution), and the prospective order candidate source (currently STATIC_ONLY). **Produces:** `build_terminal_study_design_vnext(split:str,block:int,*,order_descriptor:dict) -> dict`; `analyze_terminal_vnext(design:dict,readout:dict,verification:dict) -> dict` with the exact successor schemas above.

- [ ] Write red `test_complete_48_by_three_by_nine_slots_required`, `test_natural_zero_stays_in_family_while_missing_cell_blocks_inference`, `test_order_is_source_own_then_registered_remaining_eight`, `test_exact_guards_weights_and_nonzero_variance_unchanged`, `test_zero_trace_without_noevent_nonuse_is_insufficient`, `test_wrong_alias_roster_or_naive_row_mod_eight_refuses`. Use authored mixed zero/positive cells and independently fixed fixture rosters; own/sham mismatch and missing cells must refuse inference. No actual held-out draw/case construction or model/native dependency.
- [ ] Run Task7 red command.
- [ ] New study/profile identities explicitly supersede only donor/full-decision-prefix/condition-order clauses mapped in the proposal. Reuse analysis-v3 score, family grouping, fixed contrasts, blocked intervals and all original guards; no reweighting/normalization/post hoc adjustment. Bind actual observer/source→own→remaining-eight receipts and exact accepted factor/position alias table separately from static balance. State own+first-position alias and conditional qualified-reset/deterministic-tick interpretation, residual stationarity assumption and no order-robust claim. No new owner, actual donor, runtime or draw.
- [ ] Run Task7 green. Complete independent source/science/whole-feature review and exact successor source/schema/capacity closure; prepare concrete namespace/runtime/input/CPU/storage/observer/qualification/adoption/GO package. All new actual acceptance/pin sets remain empty, no old pins rebound, no full-study launch command delivered. Root adjudicates remaining specification/feasibility decisions; separate actual adoption and GO follow only after the package is reviewable. Commit only reviewed Task7 files after authorization.

## Proposed successor census (Task 6; unqualified software policy)

This **new epoch** preserves public numeric V2's base+companion layout. It does not alter old41/49/418/77824 limits, route a new tree through their readers, or authorize an actual larger allocation. Root permitted proposing a new finite count policy for review; the numerical proposal here still requires approval and exact serialized byte/lifetime qualification. Roots are per separately admitted phase, not a combined development/held-out namespace; no held-out identities are generated by this plan.

Proposed closed tree per phase evidence root:

- Original source export remains `.pending/<case>/{source/{owner.json,snapshots/initial.snp},.raw/<source-run>/{recording/{manifest.json,events.jsonl,chunks/*},worker-report.json,...exact-raw-inventory}}`; original paths and one sole source SNP remain. The raw inventory has existing max42 files, not a permission for arbitrary names.
- Public source candidate stays `numeric-v2/<case>/<source-run>/{base/{five-base-metadata,chunks/*},numeric/*,numeric-index.json,numeric-v2.json,conversion.json,commit.json}`; at most one failure `quarantine.json` additionally remains. Five base metadata names are `manifest.json,legacy-manifest.json,legacy-events.jsonl,chunk-index.json,audit-frames.npz`. Source bundle proof/identity remains publicly bound to original raw. New source consumer/actual source authority is required before case use; old retained-source reader is not reused unchanged.
- Original condition raw stays `terminal-vnext-raw/<case>/<condition>/<run>/{recording/{manifest.json,events.jsonl,chunks/*},worker-report.json}` with existing max32 leaves. No local snapshot.
- Stage `terminal-vnext-stage/<case>/conditions/<condition>/recording/{base/{five-base-metadata,chunks/*},numeric/*,numeric-index.json,numeric-v2.json}`. Condition root's exact ten regular metadata slots are `context.json,terminal-proof.json,raw-audit.json,conversion.json,owner.json,worker-report.json,snapshot-reference.json,pair-admission.json,replay.json,commit.json`, plus at most one failure `quarantine.json`. All their bytes remain inside aggregate1MiB overhead, never eleven independent MiB allowances. Context/terminal proof/raw audit/owner/worker are real copied bytes bound to originals, not rewritten evidence.
- Stage case root's exact four regular files are `source-reference.json,manifest.json,close.json,commit.json`, plus at most one failure `quarantine.json`, and directory `conditions`. `source-reference.json` is a new exact `{schema,source_registration,source_commit,source_qualification,source_numeric_commit,source_snapshot}` descriptor-only record (schema `memory-source-reference-vnext-v1`, five `D` fields), not a copied source tree or SNP. Four regular case files together retain the old32MiB case-close byte allowance; new file-count policy does not add bytes.
- Publication copies the complete staged case to fresh exclusive `terminal-vnext-cases/<case>` once, rereads/authenticates the full candidate, and commits marker last. Keep the original stage and original raw, including on failure. Do not rename/move/delete them or use hardlinks to reduce accounting. A partially copied final tree is retained as incomplete and never resumed/retried. Source descriptors continue referencing the original retained source export/SNP and source numeric candidate, so no source/SNP copies are created. This is a proposed new case publication namespace/protocol, not old rename publication with a relaxed counter.
- Control roster under `terminal-vnext-controls/<owner-run>/` is frozen before each owner: at most136 unique leaf slots = existing source registration+six control roles+owner slot (8) plus the public numeric source's at most128 additional controls (`source_seal_v2.py:217–233,323–343`). Applying the same136 upper bound to successor condition controls is a **new proposed count policy**, not inherited actual authority; Context and independent TerminalProof use two of those additional slots. All role/path/digest equalities are exact and whole-roster frozen; neither extra controls nor repeated copies grant more byte/RSS/CPU allowance. Count physical aliases once only when the same already-inventoried file/path is intentionally referenced; reject conflicting role descriptors, symlinks or hardlinked leaves. Future runs use this fixed control root; do not relocate historical controls. If an independently frozen eligible source uses another control layout, its exact original control directories must be registered and counted separately before admission instead of silently fitting this proposed tree.
- Global campaign root `terminal-vnext-campaign` has at most16 separately named slots: `study-profile.json,software-closure.json,registration.json,namespace-export-index.json,order.json,order-audit.json,source-qualification.json,condition-qualification.json,execution-audit.json,case-index.json,readout.json,verification.json,analysis.json,accounting.json,adoption.json,terminal.json`. Actual absence/incomplete disposition remains absence/incomplete; do not create fictitious success files to fill slots. Case-bound qualification receipts may occupy owner controls; these global slots do not grant broad-seed qualification.

Counts below reserve failure files as well as all retained stage/final copies. `p_s≤38,p_c≤29`; zero conditions retain the same empty directories but no partition files. Atomic `.commit.tmp` replaces the **slot** occupied by `commit.json`, never coexists; a violating coexistence refuses. Reserve one additional active raw manifest `.tmp` file because synchronous raw manifest replacement can coexist with its old manifest (`records.py:26–32,198–207`); concurrent owners remain one. No other atomic copy is unaccounted: a partially copied final tree is bounded by the reserved complete final tree.

| Namespace scope | Proposed file bound / derivation | Directory bound including named root(s) |
| --- | --- | --- |
| Original source export + source candidate, per case | `42 raw + owner + SNP + (5 base metadata +2p_s +2 envelopes + conversion +commit +quarantine) =130` at p_s38 | 7 original export directories +5 numeric candidate directories =12; shared `.pending`/`numeric-v2` roots counted once per phase. |
| Condition raw, per case | `9×32=288` | one case +9×(condition/run/recording/chunks)=37; shared raw root counted once. |
| One staged or final condition | `7+2p_c` bundle leaves +10 regular metadata +1 quarantine =76 at p_c29 | condition,recording,base,base/chunks,numeric =5. |
| One staged or final case | `9×76 +4 case files +1 case quarantine =689` | case +conditions +9×5 =47. |
| Stage **and** final, 144 cases | `2×144×689=198432` | `2×144×47=13536`, plus two shared roots. |
| All source exports/candidates and condition raw, 144 cases | `144×130 +1296×32=60192` | `144×12 +144×37=7056`, plus three shared roots. |
| Owner controls, 1440 owners | `1440×136=195840` | 1440 owner directories +one shared root. |
| Campaign / raw atomic reserve | 16 campaign files +one active raw manifest temp | one campaign root. |
| Whole one-phase **output** forest | **454481 files**, **22040 directories** (includes phase evidence root), **476521 entries** | Derived sum above, not an existing accepted profile. |

Direct-child read caps proposed for this epoch: chunks/numeric at most38/29; source run candidate≤7 direct entries plus children, source case parents≤2, snapshots1; condition candidate root≤12, recording4, base6; case root≤6, `conditions`9; shared case parents≤144; controls owner≤136, controls root≤1440; campaign≤16. Implement bounded readers with exact expected names, not just these maxima (`directory_names` read limits respectively64,256,2048 as appropriate). A count under cap never permits an unexpected name. Test zero, maximum, failure quarantine and exact one-over cases. Verify source/condition raw directories against their exact existing audit inventories, not a padded name set.

For two separately admitted full phases reserve twice the output forest (953042 entries) plus any shared parent **once**. Existing prerequisite/input forests are **additional**: freeze their exact unique path/inode/size inventory from authorized metadata and add their actual file/directory/byte bounds, without opening protected payloads for this plan or treating descriptors as the payload bytes. No global whole-process/capacity admission is asserted by an output-only count. All raw/candidate/controls/original inputs/atomic copies and all competing lane reservations remain in unchanged byte/RSS/wall/CPU admission. The old full compact minimum assumes raw removal and cannot certify this retained forest; raw ceilings alone are558GiB/block before candidate copies and controls. Failure to fit a predeclared complete envelope leaves actual admission closed and requires a separate reviewable resource decision, never outcome-based selection or deletion. No numerical global-byte expansion is proposed here.

## Prospective red/green commands and retained evidence

Commands below are **not run in this plan**. Use the repository's independently approved software-test Python as an absolute `TEST_PYTHON` supplied by root; this is not permission to inspect/execute an actual interpreter payload now. No install, test-environment acquisition or native/model allocation is included. Task tests must import only pure source/codecs and authored fixtures; guarded APIs' pre-read refusal tests must not import model/native dependencies.

At execution time reserve a **fresh exclusive** directory, e.g. `.superpowers/sdd/memory-terminal-vnext-authored-<unique-run-id>/`, outside actual evidence roots; fail if it exists. For TaskN red use `$TEST_PYTHON -m pytest tests/<TaskN file from ownership table> -q --basetemp=<fresh-root>/taskN-red-tmp > <fresh-root>/taskN-red.log 2>&1`; green uses distinct `taskN-green-tmp` / `taskN-green.log`. Record exit code independently, read log, retain both failed and successful trees/logs and inventory. Legacy-focused checks use fresh `taskN-legacy-tmp` and log; Task1 pins unchanged ordinary transition behavior, Task2a strict default guard, Task2b actual branch/default integration after6, Task4 old-reader rejection. No `pytest --basetemp` may name an occupied/previous evidence directory (pytest can delete its base). A red pass is not accepted; a setup/import/native-payload failure is not proof of the intended red. Expected green is all named assertions pass with zero native/model/policy/motor calls except the ordinary pure selector call count under test. Test completion grants no actual qualification.

Concrete first authored wave (reserve literal root with exclusive `mkdir .superpowers/sdd/memory-terminal-vnext-authored-plan-v1` only after confirming its parent exists; if occupied, stop and register a new unique root, never reuse/clean it). Run the following **red** commands; each green command is the identical command with both `-red` path components replaced by `-green`, thereby retaining separate temporary trees/logs:

```bash
"$TEST_PYTHON" -m pytest tests/test_memory_transition_vnext.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task1-red-tmp > .superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task1-red.log 2>&1
"$TEST_PYTHON" -m pytest tests/test_memory_engine_transition_vnext.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task2a-red-tmp > .superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task2a-red.log 2>&1
"$TEST_PYTHON" -m pytest tests/test_memory_family_terminal_audit_vnext.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task3-red-tmp > .superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task3-red.log 2>&1
"$TEST_PYTHON" -m pytest tests/test_memory_family_terminal_numeric_vnext.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task4-red-tmp > .superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task4-red.log 2>&1
"$TEST_PYTHON" -m pytest tests/test_memory_family_terminal_condition_vnext.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task5-red-tmp > .superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task5-red.log 2>&1
"$TEST_PYTHON" -m pytest tests/test_memory_family_source_consumer_vnext.py tests/test_memory_family_terminal_case_vnext.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task6-red-tmp > .superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task6-red.log 2>&1
"$TEST_PYTHON" -m pytest tests/test_memory_engine_transition_vnext.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task2b-red-tmp > .superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task2b-red.log 2>&1
"$TEST_PYTHON" -m pytest tests/test_memory_family_terminal_analysis_vnext.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task7-red-tmp > .superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task7-red.log 2>&1
```

After green for the relevant task, legacy commands are respectively `"$TEST_PYTHON" -m pytest tests/test_memory_decision.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task1-legacy-tmp > .superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task1-legacy.log 2>&1`, `"$TEST_PYTHON" -m pytest tests/test_memory_decision_engine.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task2a-legacy-tmp > .superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task2a-legacy.log 2>&1`, and `"$TEST_PYTHON" -m pytest tests/test_memory_family_numeric_preservation_v2.py -q --basetemp=.superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task4-legacy-tmp > .superpowers/sdd/memory-terminal-vnext-authored-plan-v1/task4-legacy.log 2>&1`. After2b rerun only the Engine default regression with fresh `task2b-legacy-tmp`/`task2b-legacy.log` because the integrated branch is newly changed. Inspect test markers before execution and refuse native/actual-payload tests; do not run the whole repository through this focused authored allowance.

## Self-review and decision boundary

- [x] Spec coverage: S1 source-M/cardinality/no-fresh-passage→Task1/3; S2 transition/exception→Task1, private persistence/default guard→2a, actual integration→2b after6; numeric preservation→4; replay/pair/condition/endpoints→5; source/case/census→6; all-nine/order/analysis→7. P1 strict4 marker/configure/arm/default refusal, P2 exact preimages/results/alias/emission, P3 dependency split each have named tests.
- [x] Interfaces/types: Task1 Context/Lifecycle/Reach/Witness shared through Task3; TerminalProof shared through Task4/5; Task5 cells retain old exact analysis cell keys; successor receipts never masquerade as old receipts. Metadata types/caps/DAG above are proposed exact software choices, not scientific adoption.
- [x] Scope/proportion: same bounded seven-task scope with Task2 explicitly split into2a/2b at its real custody dependency; no generic registry, new owner framework or callback. Pure transition/private persistence come first; actual branch integration is not claimed until after6.
- [x] Source risks explicit: deep-copy/alias semantics need authored proof; postassignment failures cannot roll back reality; new numeric companion/retained-raw census needs a separate profile and actual feasibility/adoption. No claim that software alone resolves full-study byte/CPU feasibility or qualification.
- [ ] Root approval and scoped independent rereview of this P1–P3 plan repair remain required before code. Task1 is independently reviewable;2a is private persistence/default guard only;2b awaits6's reviewed authentic fixed custody/seam. Tasks5–7 remain **not implementation-ready** until root approves exact helper ownership, held-source construction/recheck, new source-reference/copy-publication/census epoch. State4/pending[] is now strictly legacy-rejected, not a permissive metadata flag. No full-plan, actual file-cap/adoption or GO authority follows. If fixed factoring cannot preserve strict3/default behavior and receipt isolation, stop rather than choose another architecture.

No implementation, actual data access, tests, protocol generation, pin change, commit/push or GO occurred in preparing this plan. Full project and separate scientific/operational/human gates remain open.
