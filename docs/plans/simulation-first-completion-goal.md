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
- [x] **Restore prerequisite:** prospectively review/freeze the
  [v2 candidate contract](restore-state-contract-v2.md), then qualify it on fresh
  same-source five-control restore pair before dependent memory work. Require
  audited raw records, source invariants, exact non-timing traces and declared
  candidate state equality. This narrow restore validation is distinct from the
  complete profile-feasibility gates below. Preserve original snapshot/native hashes,
  profiling diagnostics and legacy results. The candidate's synthetic tests and
  historical timer attribution alone do not pass this gate.
- [ ] **Memory/R2:** establish a decision-bearing, executable v2 scene with real
  observed beliefs and no privileged-state leak; pass all eight fresh prerequisite cells for the selected profile
  before the four-condition, six-case development pilot. Then freeze
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
3. Complete the eight fresh memory prerequisite cells, then the pilot and
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

## Current scoped results, 7–8 October 2026

The fresh narrow restore pair passes under the reviewed timer-aware contract;
raw inequality (74 native bytes) stays explicit. See
[the report](../reports/restore-qualification-v2.md) and
[PR #85](https://github.com/Aadrika08/palimpsest/pull/85). This checks only the
restore prerequisite above; full memory qualification and the pilot remain open.
The separately approved [eight fresh cells](memory-prerequisites-v2.md) ran once
for one selected profile from a fresh south-prefix. All eight owner reports
record the required inline outcomes, but final publication exceeded its 1 MiB
control-envelope cap and independent scientific close stopped. Candidate pair
comparison and final qualification remain unconfirmed. See
[the retained failed result](../reports/memory-prerequisites-v2.md) and
[PR #90](https://github.com/Aadrika08/palimpsest/pull/90). Registration
preparation and the one invocation are consumed; zero corrective studies/retries
were authorized. A separate software-only receipt repair cannot qualify this
closed allocation. Any new scientific readout needs a new approved scope; the
prerequisite gate and pilot remained open at that failed close. The separate software-only
[receipt repair](../reports/memory-campaign-receipt-size.md) removes duplicate
driver audit payloads while preserving full attempts and independent recomputation.
Its 152 focused software checks passed; they supply no native qualification.
The separately approved [fresh v3 campaign](memory-prerequisites-v3.md) has now
passed all eight selected-profile prerequisite cells once. Its independent close
finished 898.37 seconds from the original launcher origin. Both five-control
restores used the new south-prefix; acquired invariants, exact non-timing traces
and frozen timer-aware candidate equality passed. Legacy raw state remains
unequal at 67 native bytes. The 180-second registration and single 4,900-second
invocation allocations are consumed, with zero retries/corrective studies.
Required software checks passed 1,082 tests (24 skipped), and review found no
Critical/Important issue. See [the retained scoped pass](../reports/memory-prerequisites-v3.md).
This finishes prerequisites on one profile/source/host, not Memory/R2. It permits
the [separate six-case/four-condition pilot proposal](memory-decision-pilot-v2.md):
six acquisitions and 24 continuations, maximum 30 owners, requested separate
180-second registration and one 6,600-second invocation, fail-closed 8 GiB,
zero retries/corrective studies. The admission bridge, new protocol and pilot
remain unapproved/unstarted; no held-out or other lane is authorized by v3 approval.

The fresh artwork-material v3 allocation passed in 22.06 seconds. Its compact
comparison preserves source geometry and complete raw-event references while
remaining below the original byte limits. All six artifact hashes and the
nine-member review ZIP were independently checked:
[PR #88](https://github.com/Aadrika08/palimpsest/pull/88),
[retained report](https://github.com/Aadrika08/palimpsest/blob/verify/artwork-material-v3/docs/reports/artwork-material-v3.md).
This finishes bounded offline material preparation, not the artistic experience
or human acceptance gates. Afterimage is still insufficient for sustained review.

Manual-browser v3 failed in 15.30 seconds after its first owner completed 56 ticks.
The approved 256 MiB managed budget admitted its recording; Chromium then returned
ERR_INSUFFICIENT_RESOURCES on a placement-preview fetch. No exhausted-resource
cause is established. Its paused snapshot, branches, comparison and export were
not reached. Original cleanup passed with no required kill or observed survivor.
See [PR #89](https://github.com/Aadrika08/palimpsest/pull/89) and
[retained report](https://github.com/Aadrika08/palimpsest/blob/verify/manual-lab-refresh-v3/docs/reports/manual-lab-refresh-v3.md).
No retry is authorized. Earlier failed browser/artwork v1/v2 evidence is preserved.

Learned puck/navigation, adequate Afterimage, browser acceptance, human
artwork/operator acceptance and final delivery remain open. Physical rover work
remains deferred. The project remains incomplete; these bounded results do not
lower any required capability, research or acceptance threshold.
