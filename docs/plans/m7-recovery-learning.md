# M7-REC-LEARN-1: executed-action, right-censored research data

This is a **source-only preparation and preregistration slice**. It does not prepare the actual corpus, train, evaluate a model, unlock held-out data, or admit a production checkpoint. The earlier v2 training and development failure remain unchanged. More recovery data is a plausible coverage intervention, not established causal improvement.

The frozen declaration is [m7-recovery-learning-protocol.json](m7-recovery-learning-protocol.json). The research adapter is [prepare_male_recovery_data.py](../../scripts/prepare_male_recovery_data.py); its pure checks are [test_male_recovery_data.py](../../tests/test_male_recovery_data.py).

## Admission and targets

Admit only the exact Stage A collection document (`72da787b…78b72`) and two successful v3 source recordings from `c382c86781a7a5d6651af721119789729cc890ae`, through the pinned report (`01251434…70ad3`). All full hashes, case IDs, run IDs and result hashes are in the protocol. The failed v1 and v2 sources are excluded; neither failure is cured or reclassified. The [v3 evidence](../reports/m7-recovery-coverage-v3.md) establishes first-cycle collection only, with later driving intentionally censored.

The baseline sources still pass the **unchanged** `male_model.prepare_splits(..., research_stage='development')` reader and its v2 seed, split, natural-ending, byte, feature and provenance admission. Preserve its eight training runs (1,983 rows) and four dev runs (1,228 rows). The separate research adapter checks the exact v3 profile, report/result/file/SNP pins, all 67 rows per source, raw prefix/action/counter bindings, contact ownership/admission and earliest complete 45-returned-label-plus-clearance boundary using the existing collector's pure validators. It neither reruns the teacher nor decodes native state.

Append both entire 67-row sequences to training: **2,117 train / 1,228 dev / zero held-out rows**, fourteen independent source starts. Targets are all 134 recorded **executed** float32 actions, including the 21 distinct prefix actions in each source. Private expert labels and teacher state are audit metadata only; no expert substitution, prefix cropping, balancing, repetition or weighting. Inputs remain the unchanged artificial 388 RGB/contact/bearing features, with no pose, planner, teacher counter or prefix flag supplied to the model. The prefix depends on history; a partially observed executed-action objective does not imply that privileged expert policy is fully student-observable.

Each recovery source is a fresh, separate, **right-censored** sequence. Its ending is paused/`coverage_complete`, with no natural task outcome. Start hidden state at zero; train every row through **32/32/3** windows, carrying and detaching hidden between windows; discard final hidden at the source boundary. Do not pad, bootstrap a terminal target, join mirrored records, carry state into another source, or claim continuation beyond the recorded end. The old loader continues to reject this profile and its short paused ending.

## Immutable preparation artifact

Two explicit document paths are the only data-selection arguments. The adapter does not scan for candidate runs or accept a held-out list. The output must be a new exclusive directory outside both document-parent corpus trees. It verifies exact recording/SNP inventories before feature preparation, rechecks all source bytes afterward, rejects duplicate source identities/payloads or split overlap, and records ordered feature/target digests and full source inventories in a bounded research manifest.

Historical producer identity and current admission-reader identity are separate. Historical runtime/harness maps are retained unchanged. Current reader pins cover feature, record, artifact, research, body contact allowlist and frozen collector-validator sources; unrelated current Engine/profile/replay bytes are not equated with producer bytes. Integration that changes a pinned reader requires explicit review of compatibility; there is no hash fallback. The adapter's own initial bytes and reader pins are rechecked after preparation, before publication and after final fsync. Any error or drift leaves failure/pending evidence without an admissible `data-manifest.json`; a successful manifest is never overwritten. Later training must bind this manifest's exact SHA and re-admit/recheck all inputs before fitting.

The source ceiling remains 3 GiB, with combined 160 MiB per source; fourteen ceilings total**2,348,810,240 bytes**, below 3 GiB. The actual count is bounded 3,345 rows. Preparation has a 180-second cooperative internal deadline, 4 MiB manifest, 1 GiB free-disk floor and no training allocations. The initial slice does not introduce an actual supervision launcher or take a global storage lease; a later reviewed preparation/training launch must provide retained external supervision and aggregate output admission. It does not write derived camera or feature copies.

## Fixed six-model preregistration

The declaration preserves v2's graph/cell/artificial interface and all fitting settings: fresh original and degree-rewired models paired at seeds 10/11/12; 20 epochs, 32-row windows, CPU float32 / one thread, Adam 0.001, gradient norm 1, and the same velocity/circular-heading loss. Order all baseline training sources by seeds 1000–1007, then recovery 2100/2101, with episode 0/increasing tick; dev 1008–1011 remains unchanged. All six models use identical data order, settings and checkpoint selection. Select each model's earliest minimum recorded-dev loss over exactly 20 epochs; no winning-seed selection, graph screening, extra initialization, optimizer change or hyperparameter search. No training code is implemented by this slice.

Retain the existing 600-second internal / 660-second supervised budget per pair, 64 MiB per pair / 192 MiB total, 8 MiB artifact ceiling and 4 MiB reports. No existing v2 report/checkpoint is overwritten or relabelled. A future research-only checkpoint/data contract and separately reviewed thin trainer are required; the production registry and v2 loaders/protocols remain untouched. Closed-loop dev evaluation is a later stage using its unchanged 24-owner, four-scene-per-model declaration and at least 2/4 goals for each original seed. Both recorded and closed-loop held-out stages stay unopened until a separately reviewed unlock. This preregistration provides no task-success, topology-advantage, biology, generalization or physical claim.

## Runnable pure checks

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python -m unittest discover -s tests -p test_male_recovery_data.py
```

Prospective preparation argv (not run or authorized by this source slice):

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/prepare_male_recovery_data.py \
  --baseline-collection ../male-training-v2/runs/m7-v2-stage-a-cc1cea9-20261002/collection/collection.json \
  --recovery-report runs/m7-recovery-coverage-development-v3-20261003/report.json \
  --output runs/m7-recovery-learning-data-development
```

The supplied paths intentionally locate the original retained sources. A fresh checkout needs those exact evidence trees transferred with hashes; the adapter does not fetch, substitute or regenerate them. Native collection, actual preparation, training, closed-loop evaluation and held-out reads are pending separate review/GO.
