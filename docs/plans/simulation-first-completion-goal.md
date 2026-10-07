# Palimpsest simulation-first completion goal

7 October 2026. User-directed scope: finish the project in simulation, including
the artwork; defer the physical rover until the simulation release is proved.
Planning baseline: `9931906`, draft PR #74. This goal supplements the preserved
[PRD](../borrowed-body-prd-v1.md) and [implementation plan](../implementation-plan.md).
It is the project objective, not a frozen experiment protocol or a claim of completion.

## Goal

Deliver a complete, locally runnable Palimpsest simulation release: an inspectable
lab, working supported task controllers, reproducible memory and MaleCNS research,
all six artwork modes using simulated or recorded computation, and an independently
usable evidence and installation package. Complete the software and simulation
gates with retained measurements and honest limitations before proposing the
physical rover phase. Do not substitute tests, teacher demonstrations, attractive
exports or retrospective re-scoring for the missing scientific/capability gates.

The scope covers M0–M7, a simulation/offline version of M9, and the corresponding
M10 handoff. M8/R4 and physical rover/pen installation are deferred. R5's
physical/exhibition claims do not inherit success from this simulation release.

## Completion criteria

- [ ] **Lab and recovery:** a fresh, documented local setup verifies assets and
  provenance, launches the lab, and supports the declared policy profiles,
  interventions, actual-input inspection, pause/step/reset, snapshot branches,
  playback/actions/policy replay, comparison and SVG/PNG/bundle export. Required
  asset-backed and browser checks run; skips do not count as proof. Retain the
  existing R0/R1 evidence and reverify changed paths, operational faults, storage
  limits and declared endurance. Report CPU/GPU and display-rate limitations.
- [ ] **Restore prerequisite:** prospectively review/freeze the
  [v2 candidate contract](restore-state-contract-v2.md), then qualify it on fresh
  same-source five-control restore pair before dependent memory work. Require
  audited raw records, source invariants, exact non-timing traces and declared
  candidate state equality. This narrow restore validation is distinct from the
  complete profile-feasibility gates below. Preserve original snapshot/native hashes,
  profiling diagnostics and legacy results. The candidate's synthetic tests and
  historical timer attribution alone do not pass this gate.
- [ ] **Memory/R2:** establish a decision-bearing, executable v2 scene with real
  observed beliefs and no privileged-state leak; pass all eight fresh profile
  prerequisites before the four-condition, six-case development pilot. Then freeze
  and execute the full nine-condition matched-control development and held-out
  study, including targeting, justified revisions, action/task propagation,
  false revisions, costs and uncertainty. Include every required condition and
  all failures. Pair by independent case family, not ticks or repeated condition
  branches; use the same capped failure score. Freeze meaningful effect/null-cost
  criteria, family count and multiplicity rules after the pilot and before test
  access. A valid positive or null scientific result can complete this
  study; retired v1's incomplete matrix is not resurrected as v2 evidence.
- [ ] **Task capabilities/M6:** deliver usable exploration, encoder homing,
  measured body adaptation and learned puck pushing within their declared scopes.
  Retain the bounded passing subgates; complete learned puck development and
  held-out gates, native simulation/replay checks, and lab integration. A teacher
  or manual driver must remain labelled and cannot qualify a learned model.
  Existing puck thresholds remain at least 3/4 development and 6/8 held-out goals
  for every required model; failed historical arms remain failed.
- [ ] **MaleCNS/R3:** retain reproducible extraction/mappings and separately
  trained compatible profiles; establish useful closed-loop navigation before
  opening its reserved evaluation. Preserve the existing per-seed 3/4 development
  and 6/8 held-out goal thresholds. Use matched information/training budgets and
  multiple seeds for any topology comparison. A null topology advantage is
  acceptable research evidence; unsuccessful navigation does not finish R3.
- [ ] **Six simulation artwork modes:** Afterimage; One map, many possible lives;
  Counterfactual choir; Borrowed body; Atlas of what disappears; The space between
  two flies. Reuse the current computation/recording/export paths. Borrowed body
  uses recorded simulated routes. Optional live capture/sonification extensions
  are outside this completion gate. Provide an accessible encounter with clear
  live/playback, composed/observed and scientific-limit labels; provenance and
  faithful mappings; bounded sessions; pause/stop/recovery where relevant; and
  complete portable inputs or a verified setup path. Six exported files alone
  do not complete the experience.
- [ ] **Human artwork and operator acceptance:** provide concrete reviewable
  visual/audio artifacts and a short guided simulation workflow. The user judges
  artistic usefulness; an independent operator follows setup and all six modes
  without undocumented implementation help. Retain named, finite-duration session
  records covering each entire declared elapsed session, with labelled repeats,
  resets and interruptions; viewport/audio checks where applicable; source/data
  bounds, unchanged source hashes, termination with no remaining owned runtime,
  recovery results, and agreed audience/retention declarations. Agent tests
  cannot supply this human judgment; prepare everything needed before requesting it.
- [ ] **Final handoff:** a requirements-to-evidence matrix marks each nonphysical
  requirement passed, failed or explicitly limited; documents installation,
  architecture, models, experiments, artwork operation and reproduction; includes
  source/licence identities and measured resource limits. Review and deliver
  verified changes through the existing branch/PR workflow. No unresolved required
  capability can be hidden behind an overall "complete" label.

## Execution order and boundaries

1. Reconcile current evidence and the PR stack; write the next narrow, reviewable
   restore-qualification plan from the candidate in PR #74.
2. Freeze its contract and bounded protocol, run narrow fresh restore validation
   once within that allocation, and independently audit the resulting evidence.
3. Complete the full fresh memory-profile prerequisites, then the pilot and
   confirmatory work in that order. A narrow restore pass alone unlocks no pilot.
   In parallel, diagnose the existing puck/navigation failures and propose
   evidence-supported, finite new development studies; serialize heavy jobs.
4. Complete and integrate qualified task/MaleCNS profiles. Improve the artwork
   experience and portable source handoff using already supported records while
   these research gates proceed; do not imply missing capability through artwork.
5. Run the final local acceptance matrix, prepare human artwork/operator review,
   and finish the reproducible simulation delivery and rover-readiness dossier.

Use local compute first and existing helpers/dependencies. Keep CI outside this
goal per the user's direction. Commit verified increments on focused or stacked
branches with repo-local Aadrika Maurya <aadrikamaurya@gmail.com>; publish as
Aadrika08. No automatic merge, force-push, purchases, paid cloud or physical
actuation is authorized by this goal.

New experiments need new prospectively reviewed/versioned protocols that fix
source/model/profile identities, splits, metrics, controls, compute/storage/time
caps and stopping rules before execution. Each phase must also freeze a finite
corrective-study count and aggregate resource allocation per unresolved lane.
After that allocation is exhausted, stop the lane and present a concrete decision
to the user; do not automatically propose and execute rescue studies until success.
Existing consumed allocations and no-retry decisions remain intact. Collect all
planned natural task outcomes in fixed capability matrices, including failures;
source/invariant/storage/deadline/cleanup violations stop further owners. A failed
mandatory stage gate stops downstream work. Keep the evidence and diagnose the result.
Do not quietly add seeds, tune on held-out results, lower thresholds, promote
failed models or continue fitting until a desired answer appears. Unknown
feasibility and exhausted resources are explicit blockers, not success.

"Proved" means these scoped criteria have reproducible evidence and the remaining
limitations are disclosed; it does not promise universal competence, memory or
topology superiority, biological experience, or a robot's physical safety.
If a required capability remains unattainable under the agreed studies, report
the incomplete gate and a concrete scope decision instead of claiming completion.

## Physical rover transition

After the simulation release passes, present its evidence and a separate physical
implementation proposal. That later phase requires its own approved costs/BOM,
component selection, calibration, command expiry/emergency stop, timing/stopping
measurements and staged physical fault qualification. Simulation acceptance is
a prerequisite for starting that work; it is not physical qualification. The
rover and physical artwork remain inactive throughout this goal.

## Evidence anchors

- [Current restore candidate and software verification](../reports/restore-state-contract-v2.md).
- [Capability exploration: no model selected](../reports/research-capability-phase.md).
- [Memory v1 retirement](../reports/m5-v1-structural-null.md).
- [Existing puck capability gate](m6-puck-pushing.md).
- [Existing navigation capability gate](m7-navigation-study.md).
- [Six-mode export smoke and its limits](../reports/m9-offline-handoff.md).
- [Artwork operator acceptance](../exhibition-runbook.md).
