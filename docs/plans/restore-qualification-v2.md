# Fresh narrow restore validation under the v2 comparison

7 October 2026. **Scope approved by the user; native attempt not executed.** Parent `25dff6b`, project
[completion goal](simulation-first-completion-goal.md), candidate in PR #74.
This is one bounded extension of the existing restore driver, not another
controller, geometry, recorder, snapshot format or generic experiment framework.
The user's subsequent "approved" authorizes this concrete implementation and
single native invocation. The finite allocation and excluded downstream work
below remain unchanged.

## Question and outcome

Do two fresh, sequential five-control CPU FLYNN continuations from the same
audited source reproduce all declared non-timing traces and the complete
normalized state under `restore-reproducibility-v2-candidate`?

The narrow outcome is `narrow_restore_passed`, contingent on independent readback
and timely scientific close. Preserve legacy `comparison`, raw
`restore_pair_matches`, original hashes and duration diagnostics alongside the
candidate result. Raw equality may be true or false; report it rather than require
a timing mismatch. This is one source/profile/host and ten total new controls,
not a population estimate, general reproducibility, or a memory benefit result.

`native_prerequisites_passed` remains false, `qualification_claims` stays empty,
and the memory pilot remains unattempted. A later separate campaign must pass all
eight fresh profile prerequisites before the pilot; this pair substitutes for none
of those future owners. Historical failures and consumed markers remain intact.

## Fixed scientific inputs and permitted change

- Source run: `2f1ac4fbae794737b174e6e1fc2a7541` from the audited recovery study.
- Source SNP: `runs/memory-travel-recovery-20261004T133718Z/prerequisites/runs/2f1ac4fbae794737b174e6e1fc2a7541/snapshots/initial.snp`.
- Source size: 1,559,915 bytes; SHA256:
  `c839fae1fe3d981cf4b7073970f7eb06d5738f009d6cb23f249408fd227cf6bf`.
- Source invariant:
  `86fa2ebcee8305a1b39c779a9a52e7c844345142fdbc4fd19175584a695a8b78`.
- Selected profile:
  `7faba0a56d129ea051d5c28a019964034b546923dbe49cedb3a605af84437ec3`.
- Unchanged worker travel protocol:
  `ae7c4014868d5ade9928cfdda2729c3562df38404a32f7c4b7980d4cbb567a5d`.
- Existing assets: sibling `r0-reproduction/data/assets/flynn`; frozen histories:
  sibling `memory-experiments/runs/m5-acquisition-batch-20261002/`.
- Runtime: existing Python 3.11 environment, MuJoCo 3.3.6, NumPy 2.2.5,
  Torch 2.9.0 CPU float32, one thread, EGL; pin actual executable path/resolved
  target, versions, platform/host and backend in registration before admission.

No refit, new geometry/sensor/control policy, acquisition, layout selection,
manual rescue, history substitution, held-out access, tolerance or broader byte
exclusion. The declared state projection is exactly the existing
[candidate](restore-state-contract-v2.md): verify raw native SHA first; prove the
same 15 disjoint float64 duration intervals; zero only 120 bytes per side on
copies; derive separate projected hashes; compare every other normalized typed
field and native byte exactly. Timer counts remain included. Stored data is never
patched. The controller path must retain its documented lack of duration consumers.

## Minimal implementation path

Extend `scripts/memory_restore_diagnostic.py` with explicit mode `restore-v2`
and registration schema `memory-restore-registration-v2`. Existing `diagnose` and
`qualify` accept only their existing v1 schema and keep their current paths.
New v2 mode requires the exact candidate contract ID and `[600, 300]` caps.

Reuse `copy_source`, `run_pair`, `audit_owners`, `audit_post_state`,
`compare_states`, and existing storage/cleanup/control publication. Import
`memory_restore_offline_readout.compare_reproducibility_states` only in the new
readout branch. Do not reuse its `audit_pair`: that function is deliberately
bound to an old failed close and historical cleanup records.

The pair calls the existing last two `travel_specs('travel-feasibility', PROFILE)`
as `restore-1` and `restore-2`, sequentially, with `retain_repeat_state=True`.
The existing worker validates the source, restores the acquired decision boundary,
checks the invariant, executes exactly five real controls and captures its final
state once. Preserve that capture, its SNP/native checksums, complete normalized
digest/component hashes, initial snapshot and source receipt IDs.

For the new mode only, registration and admission additionally bind/recheck the
candidate comparator, runtime, launcher and independent auditor. Protect the
source SNP and every preserved root explicitly from output overlap: existing
`source_paths` does not include prior run roots. Do not broaden or relax an old
registration. Keep `prerequisite_pass`, `validate_feasibility`, worker source and
full-profile qualification logic unchanged.

New receipt fields: `state_contract`, `candidate_comparison`,
`candidate_restore_pair_matches`, and provisional `narrow_restore_passed=False`.
Only the complete new path can set the narrow flag after all final checks; every
source, audit, storage, interruption, cleanup or late-close failure clears it.
Unequal traces or failed invariants defeat candidate equality. A scientifically
failed or incomplete narrow attempt returns nonzero; operational completion is
never inferred to be a scientific pass.

## Finite phase allocation

One new study registration, one native invocation, at most two native owners.
No repair/retry, further candidate or automatic corrective study in this phase.
Software implementation and tests are separate from scientific compute.

- Registration/inventory preparation: at most 180 s; no native owner or physics.
- Native preparation and two owners: 600 s.
- Cleanup and both in-driver and independent readout: 300 s, limited by the same
  recorded deadline; the independent audit gets no restarted 300 s window.
- Native total: 900 s, no allocation transfer; phase nonsoftware total at most
  1,080 s. One outer watchdog covers the driver, independent auditor and terminal
  scientific close together: TERM at 890 s and KILL after 5 s. Do not copy the old
  launcher structure that times only the driver and then runs unbounded readback.
  Late completion fails; these limits do not promise universal process-return time.
- Each owner: existing 150 s internal / 160 s external, with 10 s cleanup reserve.
- Storage: existing 8 GiB phase cap, 10 GiB free at admission, continuing 2 GiB
  free floor, 64 MiB headroom, 512 MiB per repeat recording, 16 MiB per SNP and
  1 MiB per stdout/stderr stream. Use existing measured controls, not custom quotas.
  The v2-only counted roots include the run output, exact new workspace control
  directory (marker and bounded live logs), and new publication evidence directory.
  Reuse `StorageBudget` across that exact root set for admission, control/audit
  writes, publication copies and final recount; do not assume the old run-root-only
  `phase_budget(root)` counts sibling logs or evidence. No extra outer writer lease
  may block the existing native writer. Checks remain observations/reservations,
  not an atomic filesystem quota against unrelated writers.

Use distinct output `runs/restore-v2-pair-<registration UTC stamp>`, evidence
`docs/reports/restore-qualification-v2-evidence/`, and marker
`.superpowers/sdd/restore-qualification-v2/launched.json`. Freeze exact paths in
registration. Commit implementation, software checks, protocol, auditor, launcher
and registration before invocation. Keep live logs ignored until the child exits
so its clean-checkout admission sees no untracked publication files. Refuse an
existing output/marker; absence of an old qualification marker is not permission
to repurpose it.

## Proof and independent readback

A pass needs exactly the two registered jobs/started owners; byte-identical source
copies and initial invariants; five audited controls each; exact non-timing traces;
candidate state equality; valid raw/native/SNP/component integrity; all registered
inputs/evidence unchanged; bounded storage/time and clean owner termination.

Prepare the independent auditor before registration. Starting from registered
jobs and fresh raw records, reconstruct bindings, sensors/controls and every
non-timing numeric field using existing readers. Re-audit initial/post SNP checksums
and receipt IDs; recompute both comparisons rather than trusting the driver's
boolean. Rehash the allocated/started sets and preserve incomplete owners.
Check exact PID/starttime/PGID exit in the fresh invocation's process namespace;
another namespace's historical PID absence is not current cleanup proof.
The wrapper must complete this readback within the original readout allocation
before the final narrow pass is published. The driver may publish its audited
candidate result provisionally; only the independently checked terminal scientific
close can declare `narrow_restore_passed=True`. Independent final review cannot extend a failed close or
retrofit success. No extra physics or policy inference occurs in readback.

Before native execution, reuse the comparator's seven synthetic positive/negative
cases and add the minimum new-mode checks: v1/v2 cross-schema refusal before
allocation, missing/wrong comparator/runtime pin, protected-output overlap,
candidate equality with unequal trace/failed invariant, and readout/close failure
clearing the narrow pass flag. Exercise the real new main through supplied
completed-owner doubles. Extend the existing temporary-Git launcher rehearsal
to check clean parent/child admission, explicit mode, exclusive marker and refusal
of a second invocation; never launch an actual native owner in software fixtures.
Run focused tests and the full local suite, then one independent branch review.

## Review and next action

The current [preflight record](../reports/restore-qualification-v2-preflight.json)
checks source/history bytes, runtime metadata, preserved inventory and point-in-time
space. It decodes no retained snapshot and is not simulation qualification.
The candidate is still software-only. Approving this scope permits its minimal
implementation and one bounded fresh pair; it does not permit the eight-owner
campaign, paired pilot, more fits, held-out, CI, merge, hardware or exhibition.
On pass, prepare the separate full-profile prerequisite plan. On failure, preserve
all outcomes, stop this allocation and present the exact failed requirement.

Repo-local author Aadrika Maurya <aadrikamaurya@gmail.com>; publication as Aadrika08.

## Independent proposal review

Fresh-context reviewer `restore_v2_protocol_review` checked the candidate, goal,
worker/comparator/driver/launcher paths and this proposal. No blocking scientific
flaw or legacy-gate promotion was found. Two documentary clarifications were
identified and incorporated: the outer watchdog covers the entire driver/auditor/
scientific-close pipeline, and the counted roots include fresh controls/logs and
publication evidence as well as native records. The final narrow flag is explicitly
owned by the independently checked terminal close, not the provisional driver.

The reviewer independently rehashed the source SNP, both histories, all 473
preserved files, current source/assets baseline and resolved Python binary.
Its free-space observation was 19,121,115,136 bytes. It decoded no snapshot,
launched no native owner and ran no software suite. The source invariant and
simulation outcome remain unverified by this preparation. Account quota telemetry
is unavailable; use one implementation lane and sequential heavy work.
