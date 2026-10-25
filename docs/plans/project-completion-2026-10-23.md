# Complete Palimpsest and deliver on main

The user's 23 October goal renews the full simulation-first completion scope
and explicitly requires all completed work to land on remote `main`. This
supersedes earlier exclusions of main and CI. Physical rover deployment remains
deferred. Existing scientific requirements, held-out locks and retired attempts
are preserved; this goal does not turn an engineering check into capability or
human acceptance.

## Current integration baseline

The [verified main landing](../reports/main-landing-2026-10-25.md) completes the
integration gate. [PR #184](https://github.com/Aadrika08/palimpsest/pull/184) merged
on 25 October at `9ac01a2`, containing all 25 commits through `89fb77d`.
Both hosted workflows pass 6,410 canonical fixture tests with 88 skips and zero
failures, 45 preflight checks and the frontend checks. Remote main's complete Git
tree matches the tested candidate; local main was fast-forwarded. Workflow access
and delivery of this batch are resolved. Current documentation records the result
without changing the tested implementation.

The [environment repair](../reports/hosted-fixtures-2026-10-25.md) and
[boundary/resource repair](../reports/hosted-fixture-boundaries-2026-10-25.md)
preserve the failed hosted candidates and their local repair checks. Original-code
licensing, human/operator acceptance and the research gates remain open.

## Earlier scoped validation

The [integration report](../reports/main-integration-2026-10-23.md) records the
completed canonical run, all twelve failing cases and their passing targeted
rechecks. All artwork browser checks passed. Hosted run `39989172177` on the
published `cfddb09` passed frontend and failed fixture collection under the old
workflow (three missing script imports). The current published candidate includes
the CI repair; this historical failed run is retained separately.

Source commit `29b438e` subsequently adds the retained-condition reader and its
prospective current-source profile. Its 482 affected Btrfs checks, 56 new tmpfs
checks and 19 historical-pin/link checks pass. This is part of the pushed
integration batch; those local results are not hosted CI or a final-release suite.

The [25 October integration check](../reports/main-integration-2026-10-25.md)
ran all four passes on `b36b46b`: 6,349 passed, 11 failed, 88 skipped. Five
authored fixtures needed current host-library descriptors; six custody-sensitive
cases pass in a quiet recheck, with controlled `/tmp` interference retained
separately. The runner's dropped opt-in flags are repaired and tested, including
one actual EGL intervention. The subsequent complete four-pass candidate run on
`39a266f` passes **6,372 tests, with 88 skips and zero failures**. Its retained
log covers the canonical non-integration suite with default runtime opt-ins;
it is not hosted CI or scientific qualification. Workflow access and the push
subsequently completed as recorded above. Original-code and
new-parameter licensing is an explicit pending owner decision.

The [retained-case reader](../reports/memory-retained-case-v1-2026-10-25.md)
now validates a source and all nine conditions under continuous custody.
Source `1ad4f8a` passes 392 affected Btrfs checks; all 34 new checks also pass on
tmpfs. Existing profiles stay unchanged. This closes staged case validation,
while publication, actual ordering, pruning and qualification remain open.

## Ordered work and evidence required

| Order | Work | Present evidence / remaining exit |
| --- | --- | --- |
| 1 | Integrate completed artwork work | Complete: PR #184 merged at `9ac01a2`; all 25 commits through `89fb77d` are on remote main. Both hosted suites pass 6,410 tests with 88 skips and no failures; preflight/frontend checks also pass. The merge tree exactly matches the tested candidate. |
| 2 | Finish the guided artwork introduction | One map now has a 5.58 s obstacle branch; Afterimage pairs 600 exact source frames with responses. The [guided introduction](../reports/guided-encounter-2026-10-23.md) is implemented; direct local-file opening, keyboard/mobile navigation and unchanged-derivative checks passed. Portable ZIP is included for delivery. |
| 3 | Prepare independent acceptance | Produce a usable package and current runbook; user viewing/listening decisions and an independent operator's installation/all-six-mode session remain required. Record audience/use, source permissions and custody rather than assigning fictitious owners. |
| 4 | Complete memory/R2 engineering and qualification | Single-condition sealing, retained-condition reading and [staged whole-case validation](../reports/memory-retained-case-v1-2026-10-25.md) are implemented. The latest source passes 392 affected checks, including 34 new checks also passed on tmpfs. Historical profiles remain preserved; the case reader does not create a new accepted qualification profile. The [publication contract](memory-case-publication-v1.md) now defines three-file closure, accepted order attestation, final reading and the durable no-replace transaction; its [implementation plan](memory-case-publication-v1-implementation.md) is still unexecuted. Trusted qualification pins are empty, seed-400/family-case applicability and actual ordering remain unresolved, and pruning still refuses. Implement the contract using the existing seals, then obtain actual qualification and valid nine-condition development/held-out evidence under their separate gates. |
| 5 | Qualify learned puck | Earlier original/balanced development arms scored 0/4 per model. Complete v3 runtime, source/scene/custody and collection admission; resolve protected catalog access versus independent identity projections. Then execute the declared collection/training/evaluation stages. Required capability remains 3/4 development and 6/8 held-out per model. |
| 6 | Qualify MaleCNS navigation | v2 augmented models scored 0/4 per seed. Matched-budget attempt 2 failed importing httpx before training and is consumed. A new reviewed prospective design/allocation and dependency/source closure precede training. Preserve the 3/4 development and 6/8 held-out thresholds. |
| 7 | Verify one integrated release candidate | Fresh setup/assets, supported-controller browser flows, replay/export (including PNG), recovery and applicable endurance; explicit timing limits; source/licence/runbook/evidence matrix review. All agreed gates must close on the candidate actually delivered on remote main. |

Research capability cannot be guaranteed by implementation. Retain valid null
results and failed capability gates honestly; obtain a new explicit scope decision
if a required scientific outcome proves infeasible. Do not silently redefine
completion around the already passing subset.

## Current sources and historical boundaries

- [Release gate definitions](../requirements-evidence.md#simulation-completion-gates)
  and [simulation execution scope](simulation-release-execution-goal.md).
- [Retired memory v1](../reports/m5-v1-structural-null.md): 44/48 accepted cells;
  do not revive the remaining four or v1 held-out as backlog.
- [Current condition-seal source report](../reports/memory-directory-census-v1-source.md)
  supersedes the historical missing-seal finding in the old gap audit.
- [Memory qualification amendment](memory-full-cell-qualification-v4-amendment-02.md)
  still requires current checkout/runtime applicability and independent review.
- [Puck v3 protocol](m6-puck-navigation-v3-on-policy-relabeling.md) and
  [consumed navigation attempt 2](../reports/m7-navigation-v3-matched-budget-attempt-2.md).
- [Artwork acceptance](artwork-acceptance-v1.md), [human review sheet](artwork-human-review-2026-10-22.md),
  and [latest Afterimage presentation](../reports/afterimage-presentation-2026-10-22.md).

The October 18 episode16 proof and manual-lab v5 evidence remain scoped passes.
Historical reports are not instructions to repeat consumed allocations. Agent
curatorial recommendations do not fill the human or independent-operator gates.

## Next independent source slice

The [publication contract](memory-case-publication-v1.md) and
[implementation plan](memory-case-publication-v1-implementation.md) complete the
specification step. They name manifest/close/commit schemas, accepted supervisor
attestation, explicit final-path reading, marker-last writes, the same-filesystem
no-replace directory move, both parent fsyncs and indeterminate failure. Existing
supervisor records do not prove execution order; the new acceptance anchor must
remain empty until independent real evidence is accepted.

Next, execute implementation Task 1: the bounded order-attestation validator and
empty-pin refusal tests. Then extract shared staged/final semantics, implement
the custody-preserving transaction and final reader, and qualify the source change
on a prospective profile. Preserve the combined 32 MiB case-close and 454-entry
limits, existing qualification gate, real-pruning refusal and unresolved ordering/
seed decisions. Source-only tests cannot authorize a study or fabricate a receipt.
