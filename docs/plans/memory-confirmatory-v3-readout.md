# Memory v3: complete registered slots and family readout

8 October 2026. Software phase of the simulation completion goal, based on
`c307c83`. Zero native/model/physics owners, retained recording or SNP decoding,
held-out observations, fits, or scientific regrades. Historical pilot protocols
and all consumed evidence stay unchanged in their original worktrees.

## Decision

Do not add an all-success or all-visible gate for scored memory branches.
The existing raw audit reconstructs each required sensor boundary and the exact
terminal exception. Own/null FOV loss is a legitimate capped-900 outcome.
Existing prerequisite success requirements apply to their declared no-U open
route, retreat, acquisition and restore cells; they do not establish successful
travel for every condition and approach state. Visibility between control
boundaries remains unmeasured. Any task redesign needs a separate protocol.

Implement the missing nine-condition complete-slot and family endpoint component
before the prospective generator/driver. This component consumes declared audit
readouts. It does not establish their provenance or replace raw verification,
oracle/resource isolation, scientific opportunity gates or uncertainty analysis.

## Interface and invariants

One new `scripts/memory_confirmatory_v3.py` exposes `summarize(plan, rows,
prerequisites)` and a JSON-in/JSON-out CLI. Reuse existing `memory` validators,
the nine condition names, pilot `capped_score` and `prerequisite_pass`.

- Plan fixes schema, split, all nine conditions, 1–64 family IDs, exactly one
  change/null/no-event case ID per family, and a nonempty list of required
  prerequisite IDs/kinds. All family, case and prerequisite IDs are distinct.
  The 64-family software ceiling is not a selected sample count or allocation.
- Each observed slot has case ID, condition, unique run ID, owner status,
  owner-exit proof flag and an audit projection. Expected slots are the complete
  registered case × nine-condition matrix, independent of observed outcomes.
- Unknown or duplicate slots/identities and contradictory audit fields fail.
  Missing slots, unfinished/failed owner infrastructure, absent/failed audits,
  and unmet prerequisites produce an incomplete readout, never a 900 imputation.
- Goals use actual 0–900 continuation ticks; an independently retained natural
  failure uses 900. Require a declared natural terminal cause and retain actual
  path length, duration, outcome and trace identity. Unknown exceptions are
  infrastructure-incomplete. The audit producer still owns terminal proof.
- Every complete case shares its declared nonintervention invariant. Own/sham
  trace, goal, duration, path and terminal outcome must match even when both fail.
- Aggregate only if every slot and prerequisite is complete and valid. Within
  each registered family average change/null/no-event equally, then average
  families equally. Report own-minus-reference cost and goal-success contrasts,
  by stratum and overall. Expose per-family values for later inference. Never
  treat twins, conditions or ticks as independent samples.
- Report descriptive results only: `r2_complete=false`, no qualification claims,
  no confidence intervals, and no assertion that family IDs prove independence.
  Primary comparisons remain own versus no-U and own versus swapped. Other
  baselines are descriptive and preserve the broader resource contracts.
- CLI input is at most 32 MiB, strict finite JSON, with no file paths interpreted
  from data. Output goes to stdout; no models, recording readers or launchers.

The independent family generator, oracle proof, slot producer, raw audit
integration, effect/null-harm margins, interval method and sample/compute/storage
allocation remain required next work. This software alone cannot run or qualify
the nine-condition study.

## Verification and delivery

Write synthetic checks first: a complete two-family/nine-condition matrix with
early natural failure; equal family/stratum weighting; missing/duplicate/extra
slots; infrastructure timeout unscored; failed prerequisites; own/sham mismatch
on failures; changed invariants; nonfinite/Boolean counts; unknown terminal
exceptions; family twins counted once. The fixture contains no experimental data.
Exercise the CLI with a synthetic envelope and reject oversized/nonfinite input.
Run focused tests, then the required software suite; one independent source
review and a single material-fix pass. Retain actual results and commit through
the repo-local Aadrika identity. Publish a draft stacked on PR #94, without merge.
