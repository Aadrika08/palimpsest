# Memory family v3 software verification

8 October 2026. Implementation commit
`f00982b8cbb23c72f4a1907bf6e5010a3d967842`, stacked on PR #95 commit
`599141edbe3f45dea98979dbd904c29bff19ca7b`.

This unit implements a deterministic, runtime-consumable candidate family
distribution and complete nine-condition slot descriptions. It is software
evidence only. It did not launch a native owner, step physics, run a model, read
scientific observations, select a held-out block or grant a study allocation.

## Result

One block contains 48 independently identified families, 144 change/null/no-event
cases and 1,296 condition slots. The generator supplies:

- three equally represented public route-cost strata, including actual symmetric
  ties, with both routes carrying real path-derived detours;
- a 12-row strength-2 public projection for fact, subject, route and schedule
  order, crossed with both learned relations and both relation sides;
- two registered event/decision schedules, `(1,2)` and `(2,3)`, consumed by the
  world and categorical supervisor through the existing Engine and replay paths;
- canonical reconstruction of every case from split/block/row/kind, disjoint
  31-bit development/held-out seed partitions, and exact rejection of edits;
- a bounded one-block slot builder accepted by the existing complete-family
  readout. It launches nothing and sets `native_allocation` false.

All 15 binary factor pairs contain each combination 12 times. Every binary factor
is 8/8 within each 16-family cost stratum. All 243 declared geometry catalog
combinations pass the analytic geometry guards. The old 84-case hash-set digest
remains `6ecaf341c9270bf422a133a31c3782ae6f208263dad5968be9ea0240ca8faec8`;
old serialized cases, graphs and schedules are unchanged.

## Review corrections

The first proposed seed partition put held-out seeds above the Engine's 31-bit
limit. An actual mocked Engine constructor rejected seed 2,147,483,671. The final
design uses bases `2^29` and `2^30`, stride 64 and blocks below `2^23`; both split
endpoints now enter the mocked Engine and snapshot restore path.

Independent source review then found that the initial 24-row aliases let the
public graph reconstruct the future closure for every row. That table was never
published or used for collection. The final 48-row design crosses every public
tuple with all four relation/relation-side combinations. The original decoder
now matches only 24/48 rows (8/16 in each cost stratum), and a stronger regression
groups the actual public graph plus initial fact associations and requires both
closure sides and both learned relations for every visible signature. Follow-up
review found no Critical, Important or Minor issue. This removes the structural
alias; it is not a general secrecy claim against enumerating private case inputs.

## Verification

Focused family/runtime tests: 60 passed in 14.10 seconds. The broader affected
set, including legacy decision, Engine, replay, profile and waypoint tests:
94 passed, 1 skipped in 18.89 seconds.

The full 1,272-test collection required split execution because the managed
sandbox forbids loopback sockets. The non-TestClient sweep reported 1,220 passed,
21 skipped and two `PermissionError: Operation not permitted` failures at
`socket.socket()` in existing endurance verifier fixtures. Those exact two tests
passed in 0.11 seconds with loopback permission. The three TestClient files,
which hung at TestClient entry under the same socket restriction even for an
empty FastAPI app and on the unchanged PR #95 checkout, passed 26 tests with
3 skips in 18.77 seconds with loopback permission. Final accounting over the
collected suite is 1,248 passed and 24 skipped, with no code failure. This is
split local verification, not one monolithic green run and not CI.

The retained file hashes and exact segment results are in
[`memory-family-v3-evidence/verification.json`](memory-family-v3-evidence/verification.json).

## Remaining scientific work

The family source and profile have no native qualification. A future registered
development phase still needs an actual native driver and raw audit, oracle proof
and isolation, historical training/entity/seed disjointness, event visibility and
no-predecision-passage-evidence checks for both schedules, finite owner/storage
allocation, development family choice, effect and null-harm margins, interval
estimator and held-out freeze. Natural task failures must remain scored outcomes;
families cannot be replaced because a controller fails or own U does not help.

