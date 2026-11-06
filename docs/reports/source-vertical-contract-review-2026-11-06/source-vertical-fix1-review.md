# Source vertical contract: scoped fix1 re-review

2026-11-06. Reviewed only the six prior findings, contract amendments9–14 and their direct
effects, plus `source-vertical-contract-fix-report.md`. Basis3994d6aa and prerequisite63+119
passing units are root-reported, not independently checked here. No code, tests, imports,
probes, payload reads/hashes, HEAD/network checks or agents. Only this report written.

## Verdict

**The actual provider-neutral conditional workload contract is implementation-ready.**
All six original actual-path blockers have concrete engineering resolutions. One literal
authored-domain conflict introduced by the namespace amendment still needs the small correction
below before calling the complete actual-plus-authored contract ready. This requires no user
decision and does not justify delaying implementation of the actual-path algorithms.

## Six adopted findings

1. **Structured teardown: resolved in contract.** Explicit exact-bool opt-ins, source-local
   namespace overrides, originating Engine/writer error collection, original exception objects,
   complete BaseException drains and legacy-default compatibility are now specified. The
   stronger behavior remains an implementation/test obligation, separate from preservation.
2. **Replay custody: resolved in contract.** The private non-None seam preserves single-pass
   hidden-state progression, checks exceptional exits and restores every saved state/cache
   component independently. Default None behavior and actual identity guards remain intact.
3. **Directory/leaf custody: resolved for actual inputs.** Full-stat supplemental directory
   custody, exact empty-child closure, genuine bounded leaf batches and runtime-first global
   FD/inode registration close the prior API mismatch. Original single-file namespace-export-v3
   compatibility is retained without reopening catalogs or replacing accepted export semantics.
4. **Prospective slots: resolved in contract.** The fixed336 concrete reservations fit the512
   roster bound; actual inventories remain actual-only, and physical/metadata caps still bind.
5. **External controls: resolved in contract.** An independently prearmed observer publishes
   its terminal marker last; the fixed bounded parent rendezvous can complete while run_attempt
   remains synchronous. Sightings timestamps no longer purport to prove source CPU/lifetime.
6. **Policy closure: resolved in contract.** Closure now means explicit source-owned reference
   disposal after measured restoration, with no imaginary FlynnPolicy.close/native-unload claim.
   Authored fixture identity and the honest partial numerical-delivery fallback remain explicit.

## One residual correction: authored namespace binding and coverage

Contract line28 now requires Namespace.coverage_contract to identify unchanged real v3 coverage
with resolved authorized status, independently pinned expected identities and no fabricated
resolution. Sections8/14 require the private authored path to reject actual namespaces/authority
facts; only NEW record schemas receive the authored prefix. An unchanged v3 coverage record is
therefore not covered by that prefix rule. The contract gives no authored coverage representation
or explicit parser dispatch, so an implementation must currently either invent resolved external
authority, relax the actual validator, or refuse the intended positive authored path.

Minimum literal amendment, preserving the actual path exactly:

- Add `AuthoredNamespaceBinding={schema:'memory-source-authored-namespace-export-binding-vnext-v1',
  purpose,fixture_id,coverage_contract:AD,root:Abs,export:AD,scope:'software-unit-only',claims:F0}`.
  purpose keeps the fixed two source IDs. Remove authority_reference only in this authored type;
  do not manufacture an authority file. Roots/exports must lie inside the fresh registered fixture.
- Add `AuthoredNamespaceCoverage={schema:'memory-source-authored-namespace-coverage-vnext-v1',
  fixture_id,scope:'software-unit-only',sources,file_allowlist,max_identity_characters,
  max_metadata_bytes,max_values,claims:F0}`. `sources` has the same exact two source_id/kind/expected
  rows and expected ledger fields already frozen in line28; allowlist and bounds remain identical.
  It deliberately has no allocation_authorized, resolved status or independent authority claim.
- Retain unchanged v3 EXPORT bytes as fixed authored parser data: recompute genuine one-file/list
  evidence with the same pure algorithms. The private entry's fixed authored domain selects these
  two new validators; actual run_attempt accepts only the actual Namespace and original independently
  authorized coverage. Fixture IDs bind authorization/resources/both namespace wrappers/coverage.
  No public domain flag, injected guard, fabricated actual namespace enrollment or extra output slot.

After that narrow domain-dispatch amendment, **approve the complete contract for substantive
implementation and scoped authored tests**; no further planning round is needed for these findings.
Implementation still must demonstrate its promised positive authored paths and compatibility.
No passing vertical, actual full-model/native feasibility, resource/accounting/adoption, authorized
exports/GO, execution backend, accepted actual Q, source L, F/R or later study completion is claimed.
