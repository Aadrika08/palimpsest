# M7 fixed recovery held-out evaluation, source preparation

This separate named gate evaluates the six frozen executed-target/right-censored research candidates. **Acceptance is completed held-out evaluation only.** Original PRD §10.3 requires separate graph/interface/training evaluation but supplies no useful-navigation held-out threshold. No new threshold, R3 qualification or topology advantage is inferred from development. Production admission, the development-only route and historical v2 protocols remain unchanged.

The byte-pinned [protocol](m7-recovery-heldout-protocol.json) is `097321aaf71baaf27bedf6eb3225b17b6345fb667548d19cb4810d08f87bdbed`. It fixes three stages in order, once each, with no retraining, checkpoint/epoch/seed selection, reset, retry or replacement:

| Stage | Fixed work | Internal / supervised limit | Separate output quota |
| --- | --- | --- | --- |
| Teacher collection | Exactly 1012–1015, four fresh analytic-teacher owners, max 600 ticks each | 480 / 540 s | 1 GiB |
| Recorded inputs | All six frozen models evaluated on those same four completed recordings | 120 / 180 s | 64 MiB |
| Closed loop | 1200–1207 × seeds 10/11/12 × original/rewired, 48 fresh student owners, max 600 ticks each | 3,600 / 3,660 s | 8 GiB |

Native ceilings are 52 owners, 31,200 intervals and 52 initial snapshots. Owner/startup/progress bounds remain 180/60/30 seconds; combined recording plus initial snapshot remains 160 MiB per owner. Natural goal/collision/stall/time-limit outcomes, including unsuccessful navigation, are valid observations. The first infrastructure/source/finite/admission/deadline failure stops the stage and preserves all remaining `not_started` rows. Every final stage admission additionally needs unchanged ledgers, normal process exit and bounded verified-owned cleanup. Prospective controls must enforce these external/publication/cleanup bounds; they are not prepared or authorized by this source slice.

Separate output trees prevent the teacher allocation being silently counted inside the closed-loop 8 GiB quota. Their combined managed ceilings are **9 GiB + 64 MiB = 9,730,785,280 bytes**. Prospective admission reserves 52 × 160 MiB owner allowances + 52 × 2 MiB bounded native streams + 64 MiB recorded stage + 40 MiB bounded report/control/staging headroom = **8,942,256,128 bytes**. Including the unchanged 1 GiB free-disk floor requires **10,015,997,952 free bytes** before a stage starts; the CLI checks that conservative combined reservation before output creation. Each stage also retains its own exact storage admission. Reviewed actual controls must place the separate roots on the measured filesystem and retain actual usage/free space; the arithmetic is not a measured storage result.

Prerequisites are immutable local research dependencies, separate from current reader software: sibling `male-recovery-development` contains [the actual development result](../reports/m7-recovery-development.md) at source `228232c50d5fddcaad1fb72f65bcb89ad2a896c7`. The protocol pins evaluation SHA `cdcf32103d047f9a9904532f7ca281b8f5f8c6554c2051a93ac6156e744a81a3`, functional receipt `3328dd6bccf0b65879e8aa208c70707a01b5190e18fa65e47ce4671dbf674f8f`, terminal `16f7b17e22d54fd80ed33961cd512b076278bd9ab74abdf0801e349cab57a5d7`, enclosing `b27fed725758befac4b9ee44235d1d141c82560c87655009a4f85bbc9ca53a54` and its unchanged inventory. Full admission rechecks all 24 exact development run ledgers, normal exit/cleanup, per-original ≥2/4 eligibility, all six bundles and the fourteen-source corpus pinned by data manifest `402d2676668e88bb998457ba0a9ea92f8a4c2a27b92a19d67ad76b80e3a67014`. The model index remains `cf50fd2f6a96cfb1afd43e23eae05b76522116abdcf544ef41735033dc52b6b5`; no producer file or model bundle is rewritten.

The named [module](../../src/palimpsest/male_recovery_heldout.py) delegates numerical admission/loading to the unchanged recovery machinery. Its separate exact `Binding` records held-out protocol/development provenance; it cannot masquerade as the development-only binding. Engine accepts only this named trusted type in addition to the existing exact types. Worker rejects other scene IDs, continuations, interventions and memory. Every owner checks the small pinned normal-development documents and its exact model identity; bulk raw corpus/development inventories are rehashed at stage boundaries rather than copied into every policy provenance.

The [entrypoint](../../scripts/evaluate_male_recovery_heldout.py) reuses the existing collector, recorded evaluator and closed-loop evaluator. Development eligibility is checked before held-out paths are opened, output creation or Torch import. Output/input paths must be outside retained training/development trees. Recorded evaluation requires the exact supplied teacher-report SHA, all four completed independent teacher IDs in fixed seed order and authoritative manifests before numeric chunk reads. UUID/path/declared-seed disjointness precedes numeric reads; exact source and per-episode feature/target disjointness follows feature preparation but still precedes any model load/forward. All four sources must remain distinct from the admitted fourteen-source corpus. The collection report is also rehashed during finalization. No held-out data is added to the training manifest or used for selection.

Source fixtures use temporary authored recordings and model/owner boundary stubs. They cover locked admission before reads, normal terminal/cleanup refusal, preserved v2/default dispatch, raw/episode duplicate refusal, named held-out binding, actual collector/recorded/closed-loop orchestration and unattempted rows after injected native failure. They do not demonstrate simulator behavior or inference.

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest test_male_recovery_heldout
```

Prospective commands (not authorized/executed; each actual stage requires reviewed retained supervision and fresh separate outputs):

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/evaluate_male_recovery_heldout.py collect \
  --repo "$PWD" --assets /absolute/pinned/assets --output runs/fresh-heldout-teachers
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/evaluate_male_recovery_heldout.py recorded \
  --repo "$PWD" --assets /absolute/pinned/assets --output runs/fresh-heldout-recorded \
  --collection runs/fresh-heldout-teachers/collection.json --collection-sha256 EXACT_COMPLETED_REPORT_SHA
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/evaluate_male_recovery_heldout.py closed-loop \
  --repo "$PWD" --assets /absolute/pinned/assets --output runs/fresh-heldout-closed-loop
```

Reports retain every fixed seed/model loss and paired natural outcome, plus qualification claims `[]`. Completion does not establish useful-navigation competence, recovery after the deliberately censored source endpoint, biological sensor mapping, causal training-coverage improvement, physical hardware behavior or R3. The prior failed training-v2 Stage C and recovery collection v1/v2 results remain immutable failures. No held-out source has been opened by this source preparation.
