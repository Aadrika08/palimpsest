# Portable release-evidence matrix

## Objective

Make the simulation-release handoff matrix explicit and usable from a fresh
checkout without changing any scientific, capability, artwork or human gate.

## Scope

1. Give every PRD requirement and each of the seven simulation-completion gates
   one conservative `passed`, `failed`, `limited` or `deferred` status.
2. Point release-facing links at committed reports or indexes. Keep ignored raw
   run paths and hashes in their existing committed evidence indexes.
3. Add one focused test for exact requirement coverage, status vocabulary,
   physical deferral and portable relative links.

## Acceptance

- The 26 requirement IDs in the PRD appear exactly once as matrix rows.
- `HW-001` is `deferred`; the seven nonphysical completion gates are present.
- Every relative link in the release-facing matrix resolves in this checkout,
  and no link targets the ignored `runs/` tree.
- The focused pytest command and `git diff --check` pass.

This is handoff validation only. It cannot qualify a stale browser run, a model,
a scientific result, an exhibition session or physical hardware.
