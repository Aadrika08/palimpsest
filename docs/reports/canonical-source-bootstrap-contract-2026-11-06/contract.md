# Canonical prepared source bootstrap contract

2026-11-06; source-only preflight against supplied baseline92a6ce9498c45d25c0f1788ba28e5e6afd89b52f.
No implementation, imports, tests, runtime probes, payload reads/hashes or qualification occurred.
Root retains the architecture decision; this is an implementation-ready proposed contract.

## Decision and exact surface

The single-mode extension is useful and compatible with the inspected contracts, subject to the ordering fixes below.
Extend only existing `Engine.open(..., *, ..., diagnostics=None, source_bootstrap_mode=None)`.
Accept only `None` or exact `str` literal `canonical-prepared-vnext-v1`; reject every other value.
`None` preserves legacy validation order, optional diagnostics, preparation, UUID hex normalization and all controllers.
The literal selects canonical identity plus preprepared read-only assets; it is configuration, never authorization,
an admission token, qualification pin, accepted-source flag, strict4 opt-in or external GO check.
The future fixed owner is `scripts/memory_family_source_runtime_vnext.py`; its implementation is outside this slice.
That owner must select this mode only after separately adopted external GO/input admission.
No new public factory, CLI, actual source owner, Q/L/F/R placeholder, qualification backend or state4 API.

## Canonical-mode preconditions before payload reads or allocation

- Require exactly `scenario='memory-decision-v2'`, `texture='checker'`, `controller='flynn'`, `device='cpu'`.
- Require fresh family case: actual dict, exact integer `version == 3`, accepted by unchanged
  `memory_decision_world.validate_case` through `_memory_restore/_decision_restore`, including geometry_check.
  Use unchanged `validate_decision` and its registered profile; require validated case/profile version3.
  Do not admit arbitrary dicts by a version field, weaken any case/profile guard or invent a new split admission.
- Require `restore_snapshot is None`, `replace_controller is False` (exact bool), `memory_u is None`,
  `research_binding is None`, `expected_policy_identity is None`; run unchanged controller/device/seed checks.
  Require `_seed(seed) == validated_case['seed']` before the resolver.
- Require non-None diagnostics of the exact existing package `HeldProvenance` type; use its ordinary `report()`.
  Require the existing runtime predicate: every `python`, `upstream`, and `dependency:*` check has status `ok`.
  No doctor import/call, ambient diagnostics, foreign/subclass/duck record, fabricated type or token bypass.
  The factory validates supplied pins; it does not authenticate their external registration/admission.
- Require a supplied exact str `run_id` with `str(uuid.UUID(run_id)) == run_id` (canonical lowercase hyphen UUID).
  Reject None, hex, uppercase, braces, malformed or non-string values; never generate or normalize this mode's ID.
  Select/preserve this ID before writer/output/native/model allocation. Legacy omitted/supplied IDs stay unchanged.
- Require original repo_root and asset_root spellings to be absolute and lexically canonical, without resolution:
  `os.fspath` must yield str; except `/`, reject empty, `.` or `..` slash components (also repeated/trailing slashes).
  Pass those original unresolved values to `resolve_prepared_assets_readonly` before any caller `Path.resolve`.
  Its lexical `..`, symlink-component, real-directory/regular-leaf and pinned-byte checks remain unchanged.
  The helper's safe-relative allowance does not apply to this mode or future frozen actual jobs.
  Output remains the ordinary RunWriter argument; this mode does not establish admitted output/layout custody.

## One shared Engine.open path and exact order

1. Validate mode; preserve the ordinary diagnostics-type and controller/device/seed/profile/case checks.
   Canonical mode rejects missing diagnostics before the existing `from .doctor import diagnose` branch.
   Apply the narrow restrictions, canonical UUID test and absolute/lexical-root test before the resolver.
   For malformed memory_case, refuse with ValueError rather than accessing `.get` on an arbitrary object.
2. Obtain/check the held report before any asset payload read. Reuse the exact required-status predicate from
   engine.py:434–437 via a private helper shared with the ordinary post-event check; no changed default behavior.
   Canonical failure here raises the existing runtime-diagnostics failure without creating output.
3. Call `resolve_prepared_assets_readonly(original_repo_root, original_asset_root)` exactly once.
   It returns only archive/checkpoint/edge Paths; resolver failure creates no output and has no fallback.
   Only afterwards derive canonical `root, assets` using Path.resolve for the existing shared path.
4. Keep environment defaults, RunWriter construction, max_bytes/storage_budget and ordinary manifest fields.
   Add only canonical-mode manifest `source_bootstrap_epoch: 'canonical-prepared-vnext-v1'` as configuration.
   Do not write any acceptance/admission/authority or `memory_terminal_vnext_*` manifest/Engine fields.
5. Enter the existing try/except scope. Write ordinary diagnostics event using the same held report and unchanged
   run_id; execute shared required-status validation. Keep imports, Python/NumPy/Torch seeds and thread setting
   (one for memory-decision-v2), existing reference environment constructor and configure_world order.
6. At the existing FLYNN branch, canonical mode supplies resolver edge/checkpoint directly to unchanged
   `load_policy(root, edge, checkpoint, device, seed)`. Skip verify_assets/prepare_graph only in this mode.
   Default FLYNN still runs verify_assets, prepare_graph, manifest checkpoint lookup and load_policy unchanged.
   Preserve policy_loaded and environment provenance events (including normal lock/source-file hashes).
7. Return through the same `cls(env, writer, ...)` call. Keep real __init__, repeated case/profile/seed checks,
   reset/world setup, policy reset, engine_opened/episode_started, event ordering and existing close behavior.
   No direct __init__ call outside open, duplicate constructor, altered state validator or strict4 promotion.
8. Preserve the existing BaseException failure manifest/renderer/env/writer cleanup scope after writer creation.
   Preflight/resolver failure precedes writer creation and owns no runtime resources to close.
   Keep current behavior if RunWriter construction itself fails; no new cleanup/repair policy is introduced.

Successful open returns an ordinary Engine with genuine initialized memory version3, paused at tick0/episode0.
It does not return an acquired endpoint, qualified source, replay receipt or admission; native feasibility is unproven.
The supplied UUID remains identical in writer.manifest, Engine.run_id, all emitted run_id values and close summary.
SNP/job/owner/path creation is outside this API and must inherit that UUID in the future owner's separate contract.

## Owned edits and source-unit acceptance

Future ownership ONLY `src/palimpsest/engine.py` and new `tests/test_memory_source_bootstrap_vnext.py`.
Relevant existing spans: open339–491; _memory_restore204–218 / _decision_restore259–270;
__init__96–188; _reset_world651–702; _episode_started703–747; _event502–504; close1674–1710.
Resolver assets.py:222 onward and HeldProvenance factory/type remain unchanged.

- Positive coverage must traverse actual shared Engine.open + __init__, actual profiles/case/geometry guards,
  real held_provenance factory, real readonly resolver and real synchronous RunWriter on retained tiny files.
  Clone only declared static manifest metadata with authored tiny identity bytes, as readonly-resolver tests do.
  Use an actual generated development family-v3 case; never inspect held-out/protected inputs or model payloads.
- Controlled allocation boundaries may supply fake RNG/Torch modules, import_upstream/load_policy objects and
  inert native mj_forward plus a synthetic environment implementing real validation/joint/world array protocols.
  Keep real configure_world (twenty-obstacle early return), memory_world._validate_env, decision-world configure,
  initialize, reset/world/event/close logic. Assert load_policy arguments, seed/thread/constructor/reset order,
  exact held diagnostics/provenance/events, ordinary memory version3 and unchanged canonical UUID everywhere.
  Such boundary objects are unit evidence only, never native/backend/source qualification.
- Refusal matrix covers bad/unknown mode, every incompatible option/profile/controller/device, version2/tampered/
  malformed case, seed mismatch, missing/noncanonical ID, nonabsolute/lexical-alias/traversal/symlink roots, absent/bad/foreign/
  subclass diagnostics and genuine held reports with failed required checks. Assert no resolver payload reads,
  writer/output, RNG/native/model allocation on case/ID/held-diagnostic refusals; unsafe assets never allocate.
- Deny doctor, preparer/acquisition/network and ordinary verify_assets during canonical calls; no preparer fallback.
  Prove default None/omitted mode still has doctor/held behavior, hex IDs, preparation and ordinary controller path.
- Exercise errors after writer creation: diagnostics event, allocation, configure, policy, provenance and __init__/
  episode-start failures. Assert failed manifest and existing renderer/env/writer closure, including close errors.
  Use real writer errors where possible; do not fake RunWriter or patch source/profile/trust guards.
- Retain authored fixtures/logs under a unique basetemp; run only this new source-unit file when authorized.
  No actual checkpoint/graph/runtime/model/native/physics/source-owner/research launch or old asset suites.

## Concrete limits and conflicts resolved before implementation

The current held-status check is after writer creation/native preflight boundary (432–437); move only canonical
precheck ahead of resolver reads while preserving the shared post-event predicate/default failure evidence.
The current UUID `.hex` (388), early Path.resolve (389) and preparer path (455–459) must branch narrowly.
Existing constructor fixtures replace profile guards; decision-engine tests patch world.configure. They cannot
serve as this positive proof unchanged. A complete synthetic environment/inert dependency boundary is source-
feasible with the actual validators; it is not authored or executed here. Stop rather than weaken guards if it fails.
Read-only resolution is current path/byte validation, not FD custody, runtime/import closure or immutable lifetime.
Normal environment provenance still reads/hashes source/uv.lock during a future authorized open; this review did not.
CPU provider choice, two namespace exports, actual admission/GO/Q/L/F/R/6a.2 and later strict4 integration remain
pending. Full project/resource/scientific/rights/human/paper gates are unchanged; raw deletion stays disabled.
