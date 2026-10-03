# M7 recovery executed-target research training

**All six fixed research fits passed once**, on source `19d275d7ba3d8c7da642a4b41d3a6a8f2d5c720f`. This is recorded-input fitting evidence, not closed-loop navigation, held-out qualification, a topology advantage or a production checkpoint change. The exact [training contract](../plans/m7-recovery-training.md) reused the unchanged fitter, model and rewiring functions. [Data preparation](m7-recovery-data.md) remains a separate audited stage.

Retained controls: `runs/m7-recovery-training-control-19d275d`; output: `runs/m7-recovery-learning-training-development-19d275d-20261003/bundles/seed-{10,11,12}`. The machine-readable [index](m7-recovery-training.json) binds controls, all eighteen pair artifacts, final drained logs, both inventories, runtime attestations, audits and initial audit-helper failures by path, size and SHA. Terminal SHA: `2acf7119732c11a30f4a3e86784f169a53402a3ca7b378e5219bd3fc30a544b6`.

The stage completed in 194.367220 seconds. Enclosing supervision completed with exit 0 in 194.681183 seconds; the retained console reports `accepted: true`. Each pair completed both 20-epoch models with a normal exit 0:

| Seed | Pair supervision, seconds | Original selected epoch / dev loss | Rewired selected epoch / dev loss |
| --- | ---: | --- | --- |
| 10 | 64.948332 | 20 / 0.025643583981726767 | 19 / 0.026338911794295917 |
| 11 | 61.635408 | 16 / 0.02962370051817319 | 20 / 0.030216107296633023 |
| 12 | 59.487713 | 17 / 0.023544041700782527 | 20 / 0.025414894016441383 |

All 120 epoch rows contain exactly 2,117 training and 1,228 recorded-dev observations and finite losses/error metrics. Earliest exact dev-minimum selection was checked independently; no seed, graph or epoch was replaced. The table is descriptive for three fixed seeds on one frozen corpus, not evidence of topology or generalization advantage.

The pinned prepared manifest is `402d2676668e88bb998457ba0a9ea92f8a4c2a27b92a19d67ad76b80e3a67014`: fourteen ordered sources, 3,345 rows, no held-out sources. Both complete 67-row recovery sequences retain all 134 executed-action targets, including their distinct prefix actions. The executed byte-pinned fitter resets hidden at each source start and carries/detaches across 32/32/3 windows; no cropping, endpoint bootstrap or expert-target substitution was added. Hidden trajectories were not logged. The right-censored source endings and earlier v1/v2 collection failures remain unchanged.

Runtime was Python 3.11.15, NumPy 2.2.5 and Torch distribution 2.9.0/build 2.9.0+cu128, **doing CPU float32 computation**. This is a CUDA-capable installation, not a CPU-only wheel. Guards verified one CPU intra-op and inter-op thread, one OMP/OpenBLAS/MKL thread setting, hidden CUDA devices, CUDA uninitialized before/after, and no MuJoCo import. Each checkpoint contains eighteen finite CPU tensors: seven int64 anatomical buffers and float32 values. There are 61,872 trained scalar parameters per model; fixed recurrent values were unchanged.

Before/after inventories match byte-for-byte at SHA `422aba8586643dbd8efca9a7228f3dfd2bd83ce95cbb0d93cf115d31406c6d9e`: 355 tracked source/test/lock files, 122 upstream files, 181 fixed raw/document files, sixteen original-model/production files and seven runtime metadata/entrypoint files. Exact upstream HEAD was `8d964599119b420de67ee259434d273651a1a76d`. Runtime inventory covers the listed versions/bytes, not every installed package file. Both local/shared seven-file production bundles remain unchanged; no research model was promoted. Existing production/v2 admission continues to refuse the distinct research status/protocol.

The preflight reserved 172,359,680 bytes under the unchanged 192 MiB aggregate limit, with 64 MiB per pair, 1 GiB free-disk floor, 8 MiB payload, 4 MiB report/failure and 1 MiB stream caps. Terminal-time usage was 2,735,066 bytes, before post-terminal audit copies were added. All pairs met the 600-second internal and 660-second supervised deadlines; the stage met 2,100/2,160-second bounds. Publication occurred only after payload/pending sync, successful pair lease cleanup, final source/data/deadline checks and final-destination absence. Normal process exit and immutable final ledgers were additionally required.

The finite .25-second monitor observed three child PID/start pairs; all are absent. Sampler stopped, no sampling errors, no surviving sampled process and no forced cleanup occurred. This is not universal proof about every possible transient descendant. Each 407-byte pair stderr contains only the pinned upstream PyTorch Sparse CSR beta UserWarning at cell line 98. Enclosing stderr is empty; no semaphore warning was found. Final enclosing log/console hashes were taken after exit, not from a live prefix.

Own retained audit passed in 1.276570 seconds without importing Torch/MuJoCo or running a model: 681 identity entries, eighteen pair artifacts, all 120 histories/selections, graph degree/count comparisons and sampled cleanup. Tensor shape/dtype fields in this audit are bound child attestations. Its first attempted duplicate archive decoder failed an overly strict storage-layout assertion; that script and failure receipt are retained separately and it was abandoned in favor of root's weights-only audit. This was an auditor error, not a checkpoint finding.

Root's independent audit passed in 4.408297 seconds **after one auditor correction**. It checked 699 source/runtime/raw/bundle entries; all six weights-only CPU checkpoints, eighteen finite tensors each; all seven anatomical buffers exactly against each graph; frozen recurrent values exactly against scaled adjacency; paired degree/weight-count preservation; epoch selection and cleanup. It constructed no model, ran no forward pass and imported no native simulator. The initial auditor assumed a JSON ordered-ID digest; pinned `male_model.py` specifies newline-separated decimal serialization. The failed script/log/receipt and corrected audit are all indexed. Root audit JSON SHA: `7619223178524a12c0dec9b1e649ec7083201502c4fc7cfd6337783ef10a0f2b`.

Exact one-shot command:

```sh
PYTHONPATH=src OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES= \
 ../lab-hardening/.venv/bin/python runs/m7-recovery-training-control-19d275d/supervise.py \
 > runs/m7-recovery-training-control-19d275d/launcher-console.log 2>&1
```

Source checks passed before launch: seven trainer fixtures, nine data-admission fixtures and eight collection fixtures; root independently reran all 24. Read-only control review checked all 681 entries and sampler-failure fixtures. The runtime slot was released after terminal cleanup. No development or held-out native evaluation has run for these candidates. The next gate requires separate explicit research admission and frozen paired development evaluation; no loader fallback, production promotion, training retry or held-out unlock follows from these fits.
