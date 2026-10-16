# Goal: prove and deliver Palimpsest in simulation

**Deliver a reproducible local Palimpsest simulation release with all six artworks
that another person can install, experience, inspect, replay, export and recover.
Complete and accept the simulation before starting the physical rover.**

The first visible proof is **one real manual CPU episode**: run it, record it with
registered snapshots, replay every recorded tick against a comparison declared
before execution, and export a portable bundle that independent checks accept.
Then finish the scientific results, supported controllers and all six encounters
on the same integrated release candidate.

## Measurable milestones

1. **One working episode.** Qualify the exact installed CPU runtime and the
   separate operator/renderer route. Run one bounded public episode with declared
   inputs, scene, controller, seed and limits. Retain source/runtime/input
   identities, recording, snapshots, replay comparison, source and replay exports,
   member hashes, terminal state and independently verified normal cleanup.
2. **Valid results and capable controllers.** Complete valid nine-condition
   memory development and separately admitted held-out analysis. Every required
   puck model and MaleCNS seed must meet the unchanged 3/4 development and 6/8
   held-out goal thresholds, with required mechanism replay and lab integration.
   A natural task failure may prove the engineering route in milestone 1; it
   cannot satisfy this capability milestone.
3. **A usable six-artwork lab.** Integrate all six encounters and pass actual
   browser, declared-duration visual/audio, keyboard/viewport, faithful mapping,
   provenance, replay/export, interruption/recovery and endurance checks.
4. **Human acceptance.** Record the user's artistic acceptance and an independent
   operator's installation and complete all-six-mode session.
5. **Reproducible delivery.** Close all seven existing release gates on that same
   candidate, with final review/verification, reproducible installation, licences,
   limitations, runbook and a complete requirements-to-evidence matrix.

## Active work unit: stock-absence import policy v5 and attempt 11

**Next finite exit:** independently reviewed source for missing-import policy v5
and CPU qualification epoch 11, with passing RED-to-GREEN regression checks.
Then freeze distinct epoch-11 controls, pass fresh admission and invoke attempt 11
once under the unchanged 180s/2GiB limits with an independent outcome audit.

**Verified status (2026-10-16):** runtime10 failed normally after 114.82s, before
its deadline. Its first refusal is unregistered `backports_abc` from
`numpy.random._common` during Torchvision → `torch._dynamo`. Evidence is in
[PR176](https://github.com/Aadrika08/palimpsest/pull/176) (local commit `a492e2e`,
not yet pushed). Attempts01–10 and admission01 remain immutable history.

The [contract v2](https://github.com/Aadrika08/palimpsest/blob/research/puck-cpu-optional-import-contract-v2/docs/plans/puck-cpu-optional-import-contract-v2.md)
proves, with read-only offline diagnostics on the inventory-matched held site:

- `backports_abc` is optional: Cython 3.0.12 `__Pyx_patch_abc` clears the failure
  and initialization continues. It is absent from the held site and inventory.
- The planned one-name successor would still fail. `torch._dynamo.trace_rules`
  calls bare `find_spec()` without a handler for its third-party skip list.
  The current raise semantics fail Torchvision on frozen negative `tqdm`.
- The four imports make 32 unresolved non-stdlib requests and four refused
  present-but-unregistered requests (`networkx`, `pandas`, `sklearn`,
  `torch.utils._cxx_pytree`). Stock absence (`None`) for exactly these names
  completes all four imports with the expected versions.

Policy v5 and epoch 11 source is implemented locally on the contract-v2 branch
(`bf6b980` RED tests, `ec4de6b` implementation): new and affected suites pass,
including 163 unit and 2 integration cases rechecked by root. Independent review
is pending. Offline timing places `backports_abc` at 70% of Torchvision's 990
module loads (~106s guarded), projecting ~135-145s for all four imports against
the 180s deadline; the margin is tight and unproven.

The next actions, in order, are:

1. Finish policy v5: declared-absent (32) and declared-hidden (4) names are
   verified, recorded and return `None`; remaining finders must not resolve them;
   undeclared requests still poison. Add epoch 11 to parent, observer and auditor.
   Policies v1–v4 and epochs 1–10 stay unchanged.
2. Independently review the source and its regression evidence.
3. Freeze distinct epoch-11 controls, independently review them, run fresh full
   admission and pre-execution guards, then invoke attempt 11 exactly once.

After accepted import qualification, separately qualify the finite public
operator/renderer route and produce the real episode bundle in milestone 1.
A failure consumes its named attempt; never overwrite or silently retry.
A newly discovered import is not permission to relax the loader or a threshold.

Project disk has about 45GiB free at the 2026-10-16 check. Every execution must
refresh its own resource checks; clearing disk space is not admission. Scientific
protocol decisions, protected-data access and human acceptance retain their named
owners. Physical rover work and CI are outside this goal.

This continues the [original completion scope](simulation-completion-next-goal.md).
Detailed prior status remains in the [unchanged pre-clarification goal](https://github.com/Aadrika08/palimpsest/blob/29c40a5983a20ea336ace7d9794720503fbbd553/docs/plans/simulation-release-execution-goal.md),
[earlier history](simulation-release-execution-goal-history-2026-10-15.md) and
[prior snapshot](simulation-release-execution-goal-history-2026-10-16.md).
Historical records are evidence, not instructions to repeat consumed attempts.

## What counts as finished

All seven gates must close on **one integrated candidate**. All seven are open.

| Gate | Required evidence |
| --- | --- |
| Memory / R2 | Complete valid nine-condition development and held-out studies, independently audited family analysis and controls. A valid positive or null result is acceptable; missing or invalid cells are not a null result. |
| Learned puck and supported tasks | Every required relabeled puck model reaches at least 3/4 development and 6/8 held-out goals; mechanism replay and lab integration pass. Supported exploration, homing and adaptation retain their scoped evidence. |
| MaleCNS | Every required seed reaches at least 3/4 development and 6/8 held-out goals under matched budgets. A topology benefit is not required. |
| Lab | Asset-backed installation and actual browser inspection, replay, exports, interruption/recovery and required endurance pass. |
| Six artworks | Sufficient portable inputs and declared-duration visual, audio, keyboard, viewport, faithful mapping, control and provenance checks pass for every encounter. |
| Human acceptance | Recorded user artistic acceptance and an independent operator's installation and all-six-mode session. |
| Integrated delivery | Reviewed integration, final verification, reproducible installation, licences, limitations, runbook and complete requirements-to-evidence matrix. |

The encounters are **Afterimage; One map, many possible lives; Counterfactual
choir; Borrowed body; Atlas of what disappears; The space between two flies.**
The [release matrix](../requirements-evidence.md) tracks individual requirements.
Source tests and additional PRs close implementation tasks only. They do not
substitute for numerical results, capability, actual browser use or human acceptance.

## What we do next

| Order | Product milestone | Done when |
| --- | --- | --- |
| 1 | One working episode bundle. | The exact runtime and public engineering route qualify; one nonzero episode has complete records and registered snapshots, all ticks pass the declared replay comparison, exports validate, and independent outcome/byte/cleanup audits pass. A task failure can prove this route, not controller capability. |
| 2 | Valid memory results. | Frozen ordering, seed-to-case and admission issues are resolved prospectively; all nine conditions have valid development and separately admitted held-out results with independently audited family/control analysis. A valid positive or null result counts; missing or invalid cells do not. |
| 3 | Supported controllers. | Every required relabeled puck model and MaleCNS seed meets unchanged 3/4 development and 6/8 held-out goals; mechanism replay and lab integration pass, with scoped exploration, homing and adaptation evidence retained. |
| 4 | A usable six-artwork lab. | One asset-backed candidate passes actual browser, declared-duration visual/audio, keyboard/viewport, faithful mapping, control/provenance, replay/export, interruption/recovery and required endurance checks for all six encounters. |
| 5 | Human acceptance. | The user records artistic acceptance, and an independent operator completes installation and an all-six-mode session. |
| 6 | Reproducible delivery. | All seven gates close on that same integrated candidate; final review/verification, reproducible installation, licences, limitations, runbook and the complete requirements-to-evidence matrix are ready. |

## Decisions and evidence boundaries

- Memory qualification amendment 02 in [PR119](https://github.com/Aadrika08/palimpsest/pull/119)
  remains uninvoked. Oracle precedes own in 42/48 families (126/144 cases),
  conflicting with prior-own/condition-close requirements. No resolution is selected;
  do not reorder the frozen protocol. The reviewed seed 400-to-case binding,
  exact single-condition/family admission and remaining cells still need closure.
- Protected mixed-catalog access versus independent identity projections in
  [PR123](https://github.com/Aadrika08/palimpsest/pull/123) remains a user decision.
  Use declared public engineering inputs while it is unresolved; continuation or
  disk clearance does not authorize protected reads.
- Navigation attempts 1/2 are consumed; no attempt 3 is authorized. R3 and the new
  navigation study/held-out decision remain open. Existing failed controller scores
  do not pass the capability thresholds above.
- Installation 01, retained admission 01, characterization 01 and every earlier
  consumed allocation remain historical failures. Distinct later scoped passes
  do not rewrite them. Never fabricate a missing receipt or silently retry.
- Runtime-import qualification cannot admit operators, rendering, physics,
  inference, collection or a scientific study. Freeze each actual route separately
  with exact source/input/custody/versions, finite limits, fresh resources and
  independent outcome checks. Keep build/evidence scratch on project disk and
  stage only required inputs on executable/writable tmpfs under the existing
  identity policy. Existing preparation/qualification RAM floors remain 4/2GiB;
  every future admission refreshes its own exact limits and bytes.

## Ownership and scope

The agent owns implementation, bounded verification, evidence, incremental
repo-local commits as Aadrika Maurya, and authorized draft PR updates/pushes as
Aadrika08. The user owns artistic acceptance and prospective study decisions.
An independent operator owns the installation/all-six-encounter session.
No automatic merge follows.

Physical rover work, fabrication, purchases, paid cloud and CI are outside this
goal. Simulation evidence makes no physical-actuation claim. Complete and accept
all seven gates on one candidate before a separate user decision starts the rover.
At each milestone report working behavior, observed result, first remaining gap
and next concrete action.
