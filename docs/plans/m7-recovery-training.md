# M7-REC-LEARN-1: thin fixed six-model trainer

This source-only slice implements a seed-pair adapter over the **unchanged** `train_male_reduced.fit/evaluate` and `male_model.make_model/rewire`. It does not add a numerical training loop, optimizer, architecture, production loader or dataset selector. No actual Torch/training execution is authorized by this plan. The [learning preregistration](m7-recovery-learning-protocol.json) remains immutable; the [prepared-data evidence](../reports/m7-recovery-data.md) qualifies data preparation only.

The data manifest is pinned to full SHA `402d2676668e88bb998457ba0a9ea92f8a4c2a27b92a19d67ad76b80e3a67014`: fourteen ordered sources, 2,117 training / 1,228 recorded-dev rows, zero held-out. Before fitting, the adapter re-admits it through the existing research data reader and requires exact manifest equality, including source fingerprints and ordered feature/target hashes. Every source, document, result, graph/extraction/cell and reader/trainer byte is checked again after fitting and after final report sync. The old fitter's SHA is pinned separately; historical producer identities are not equated with unrelated current Engine/replay files.

Run all three paired seeds **10, 11, 12**, in that order, each with fresh **original then degree-rewired** models. No winning seed, topology screening, extra initialization or replacement is allowed. Preserve 20 epochs, CPU float32/one thread, Adam 0.001, gradient norm 1, the unchanged loss and earliest minimum recorded-dev checkpoint rule. The unchanged fitter zeros hidden at every source start and carries/detaches it at every 32-row window: both complete 67-row recovery sequences therefore use 32/32/3, without cropping, padding, cross-source carry or endpoint bootstrap. All 134 targets remain actual executed actions; expert/private metadata is not a training feature or target. Validation checks every returned epoch's 2,117/1,228 counts and finite metrics, including first-epoch exact-tie selection.

Each entry handles exactly one fixed pair (`--training-seed 10|11|12`) with no held-out argument. Its 600-second cooperative internal deadline includes admission, both fits, serialization and final source checks; the prospective external supervisor cap remains 660 seconds. A future retained launcher must run all three entries once, report all six planned models and retain unstarted rows after the first infrastructure/data/finite/budget failure. No actual launcher is introduced by this source slice.

Keep 64 MiB per pair / 192 MiB aggregate, 8 MiB artifact and 4 MiB report/failure bounds, with a 1 GiB free-disk floor and 1 MiB streams. The managed output root must be disjoint from the prepared-data, baseline and recovery document-parent trees; directories are fresh `aggregate-root/seed-N`, never resumed. Raw cameras/features/hidden trajectories are not duplicated in outputs.

Protocol, graph and the existing checkpoint payload schema are serialized with file hashes. Reports use the distinct `completed-research-training` status/protocol; current strict production and v2 bundle admission continues to reject them. Failure retains written/partial artifacts, `report.pending` when applicable and a bounded separate failure report. It never publishes an admissible `report.json`.

Publication order is explicit: write/flush/fsync all payloads and `report.pending` while holding the pair's existing storage lease; successfully release the resource/lease context; recheck all source/data bytes and deadline; check final destination absence; rename staged bytes as the **last fallible operation**. There is no cleanup or reporting write after publication. The later outer stage must additionally require normal process exit and all complete unchanged report/artifact pins; report presence alone does not qualify a failed child.

Prospective per-pair command (not executed):

```sh
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  ../lab-hardening/.venv/bin/python scripts/train_male_recovery.py \
  --data-manifest runs/m7-recovery-learning-data-development-7d5fc1f-20261003/data-manifest.json \
  --training-seed 10 \
  --output runs/m7-recovery-learning-training-DEVELOPMENT-SOURCE/seed-10
```

Repeat only for fixed seeds 11 and 12 under the subsequently reviewed three-pair launcher. Graph/cell defaults point to the existing pinned reduced graph/extraction manifest and upstream cell; no downloading or asset replacement occurs. Concrete output name, exact shared-interpreter Python/NumPy/Torch CPU versions, original graph/cell byte pins, full source/upstream/assets/data inventories, launcher deadlines and cleanup controls must be reviewed and frozen before actual GO. The outer audit must verify all three seeds, six reports/checkpoints, normal exits, unchanged artifact content and sampled PID/start-time cleanup; no held-out path may be supplied.

Pure checks:

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python -m unittest discover -s tests -p test_train_male_recovery.py
```

Fixtures cover unchanged helper identity, fixed settings and old-loader refusal, all-epoch/count/finite/tie guards, source-root isolation, fsync/source/deadline/publication failures and lazy imports in a fresh bounded interpreter. They do not fit a model or claim numerical training success. Model fitting, recorded-dev performance, closed-loop development and any held-out unlock remain pending; prior failures and intentional collection censoring remain unchanged.
