# Closed diagnostic 09 source support

**Goal:** make the existing parent, observer and independent auditor understand a
fixed qualification 09 source epoch carrying bounded guard accounting, so the
next separately reviewed installed qualification can locate runtime cost on the
route to a real recorded/replayed/exported episode.

**Architecture:** extend explicit 08 branches through 09. Keep the original
preparation 01 data acceptance and its exact five changed source paths. Reuse the
existing observer transport, q3 worker protocol and independent audit; accounting
stderr remains best-effort diagnostic data, never a new acceptance requirement.
No new worker protocol, dependency, policy surface or general framework.

**Spec:** the active simulation-release goal's closed09 work unit and
[published accounting contract](puck-cpu-guard-accounting-v1.md).

## Invariants and scope

- Modify only `scripts/qualify_puck_cpu_held_runtime.py`,
  `scripts/audit_puck_cpu_held_runtime.py` and
  `scripts/observe_puck_cpu_held_allocation.py` in production.
- Add closed kind/version/allocation-id 09 and fixed 09 output paths. Reject bools,
  aliases, caller-selected outputs, prepare phase and policy additions.
- Keep 24 sources, 16 input roles, candidate D, 19 missing-import probes, exact five
  preparation-relative changed paths and q3 registration/result schemas.
- Old 05–07 still require exactly four preparation-relative changed paths;
  08 still requires exactly five. Preserve all earlier identity/limit checks.
- Keep 180s normal-return deadline, 2GiB RAM floor, all custody/refusal checks and
  best-effort cost 32-attempt/32KiB/1024B and phase 24-attempt/16KiB budgets.
- Attempts 01–08 are consumed. No actual 09 controls, admission or invocation;
  no installed vendor execution, protected data reads, CI or physical work.
- Later actual 09 controls must bind genuine failed 08 streams/refusal and all 14
  historical absences. Missing 07/08 results/baselines must remain absent.
- All seven simulation-release gates stay open. Authored passes do not qualify
  installed runtime, operator/renderer, episode, model, study or release.

## Tasks and verification

- [x] Record a clean existing 08 metadata/observer baseline before production edits.
- [ ] Add 09 metadata tests using `acceptance08_case()` with fixed v9/id9. Require
  both parent and auditor to accept only the exact five-path projection, reject
  each missing or sixth changed source, preserve noncandidate inputs, 19 probes,
  candidate D and all limits, and reject malformed/aliased identities. Run RED.
- [ ] Add 09 observer tests for normal/nonzero transport, exact exclusive paths,
  preserved failed 07/08 streams and missing receipts, no overwrite and prelaunch
  alias rejection. Run RED before changing observer mappings.
- [ ] Extend explicit parent selectors/execution memberships through 09; extend
  only the 08 five-path predicate to 08/09. Extend matching auditor identity,
  preparation, source namespace, authored transport and report branches; extend
  the observer's fixed mapping. Do not change worker or acceptance semantics.
- [ ] Add a full authored 09 integration using the existing publication05 fixture:
  current five-path source, candidate D, q3 imports, source identities, API and CLI
  audit, historical byte preservation, balanced descriptors/children/threads,
  exclusive 09 reentry and bounded diagnostic rows. Keep old integrations intact.
- [ ] Run affected metadata/parent/auditor/observer/worker suites in private tmpfs;
  run complete historical integrations in their required persistent project paths.
  Preserve all commands, source pins, raw logs and terminal outcomes, including REDs.
- [ ] Independently review source and final evidence; retain a finite byte-verifiable
  packet/report, commit/push a draft source PR and update both active goal mirrors.

Use the existing CPython3.11 R0 environment with pytest plugin autoload, bytecode
and cache disabled. Root owns final validation and integration; implementation
lanes own distinct files. Reviews run no installed payloads. Runtime controls and
fresh complete resource/byte/custody admission are the next separately reviewed
unit after this source exit.
