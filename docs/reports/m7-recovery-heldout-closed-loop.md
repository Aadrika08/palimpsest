# M7 fixed recovery held-out closed-loop evaluation

**All 48 reserved runs completed once with normal process dispositions; both retained-data audits passed.** This closes the separately declared held-out **evaluation** stage, not useful-navigation/R3 qualification. Original candidates reached 5/24 goals, matched rewired controls 8/24. No useful-navigation held-out threshold appears in the frozen protocol; no threshold, model selection, topology advantage or promotion is inferred after these results.

Source was `177982e583bd7457a6da2be47021fa799b801cf9`, with clean pinned upstream `8d964599119b420de67ee259434d273651a1a76d`. The unchanged [protocol](../plans/m7-recovery-heldout-protocol.json), SHA `097321aaf71baaf27bedf6eb3225b17b6345fb667548d19cb4810d08f87bdbed`, reserved scenes 1200–1207 × training seeds 10/11/12 × original/control, all six checkpoints unchanged. The exact [development prerequisite](m7-recovery-development.md), [teacher collection](m7-recovery-heldout-teachers.md) and [recorded-input evaluation](m7-recovery-heldout-recorded.md) were admitted before the first new owner. No refitting, checkpoint/epoch/seed selection, retry, reset, replacement, intervention or masked eye was used.

| Training seed | Original goals | Control goals | Original stalled / time limit | Control stalled / time limit |
| --- | ---: | ---: | ---: | ---: |
| 10 | 1/8 | 3/8 | 4 / 3 | 4 / 1 |
| 11 | 4/8 | 3/8 | 2 / 2 | 5 / 0 |
| 12 | 0/8 | 2/8 | 3 / 5 | 5 / 1 |

All non-goal outcomes are retained: 35 runs stalled or reached the declared time limit; none was replaced or omitted. The full per-scene rows, distances, action/input hashes, policy/physics timing and raw ledger remain in the original `evaluation.json`. The result contains **21,461 numeric rows, 48 initial native snapshots, eight matched scene initials and 24 original/control comparisons**. Scientific physical state and effective initial observations match within each scene across the six model candidates. These are eight scenes and three fixed model seeds, not 21,461 independent experimental units.

The raw ledger binds **885 recording/snapshot files, 4,286,694,743 bytes**. The [compact evidence index](m7-recovery-heldout-closed-loop.json) references that ledger rather than duplicating every raw file. Terminal accounting measured 4,296,178,786 managed bytes before terminal publication under the unchanged 8 GiB stage ceiling; later audit/index bytes are not part of that observation. Each owner retains a 160 MiB recording-plus-snapshot allowance, 600-tick cap and bounded 1 MiB native streams. The free-disk floor remained 1 GiB and the combined three-stage startup reservation 10,015,997,952 free bytes. Only the existing evaluator/LabSupervisor held the writer lease; no outer nested lease was used.

Evaluator-reported wall time was 2279.451365 seconds. The evaluator child exited 0 in 2286.750444 seconds. Launcher pre-publication wall time was 2303.203327 seconds; enclosing supervision exited 0 in **2303.544422 seconds**, covering terminal publication and launcher exit. Internal/child-hard/full-normal/enclosing-hard limits remained 3,600/3,630/3,650/3,660 seconds. Maximum reported owner wall time was 80.514614 seconds, below 180 seconds. This mixed owner/inference/render/recording wall time is not a real-time or display-performance qualification.

The before and after inventories are byte-identical, SHA `66204f7ac46ed7e0347d9a4036f1fe005e80050cd67216bdcd32d035409d0f74`: **1,211 identities**, including all tracked source/test/docs bytes, pinned upstream, shared assets, immutable fourteen-source corpus, six bundles/eighteen model files, prior development raw/documents, completed teacher/recorded prerequisites, their fixed control sources and seven final recorded-stage log files. All 636 evaluator source-map entries also remained unchanged. Runtime is the original Python 3.11.15 / NumPy 2.2.5 / CUDA-capable Torch 2.9.0+cu128 build doing one-thread CPU inference with EGL rendering; no training or production bundle byte changed.

All 48 owners closed normally with exit 0. The .25-second finite monitor retained 54 PID/start pairs, all absent after top-command exit, with no sampler error, PID conflict, sampled survivor or forced sampled cleanup. Own and root checks independently acquired and immediately released the actual home writer lease after drain. This is finite observed containment, not universal transient-process coverage. All 48 native stdout streams are empty. Each native stderr contains the same 1,115-byte existing TF32-settings and sparse-CSR upstream warnings; no semaphore warning was observed. Final log hashes were taken after enclosing exit, so this index binds final bytes rather than an in-flight log prefix.

Own retained NumPy-only audit passed on its **first execution** in 9.690337 seconds. It rehashed all 885 raw files, read all 21,461 action/control rows, independently reconstructed the unchanged normalized wheel-control equation, checked finite action/control/pose arrays, reported scientific initial-fingerprint equality, exact outcome counts, all native logs and sampled cleanup. It did not independently decode native initial state, construct a model, recompute neural predictions or run physics.

Root's independent raw audit also passed on its **first invocation**, in 76.971623 seconds with exit 0. It verified all raw rows/files, 48 native initial snapshots, eight matched scene states/24 pairs, 636 evaluator source entries and the full before inventory, normal dispositions, 54 sampled exits and free writer lease without Torch/MuJoCo imports or inference/physics. Root receipt SHA is `816ab24e3359d07ab61f9c64b197aca3ce27000cbdbadd9b91086113de41d77d`; auditor SHA is `6d7664caf754f37991e2718f854c05f2359b80be652588dda3c4cdd911eae080`. The prior root control readmission passed first invocation in 12.974542 seconds; the index binds both root receipts and own audit. A separately disclosed root fixture attempted the global writer lease during this stage and was correctly refused before a model/native owner; it did not change this run or justify a rerun.

Primary evaluation SHA: `3491c7ca36fc4fcfcb088ea538d211f8d7aec9423cb66727c44801f5cf003c59`. Terminal SHA: `44b657e4886167171b164643797b290fcd45351780e7c02aa28a00751dcd0125`. Enclosing SHA: `0cdc98cb110638a2bc83430fa1b5302dedbc8e9625cf093662702e41d621213f`.

Exact one-shot command from the isolated held-out worktree:

```sh
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=1 ../lab-hardening/.venv/bin/python \
  runs/m7-recovery-heldout-closed-loop-control-177982e/supervise.py \
  > runs/m7-recovery-heldout-closed-loop-control-177982e/launcher-console.log 2>&1
```

The runtime slot was released only after normal enclosing drain and independently checked cleanup. The separately authorized three-stage held-out evaluation is now complete; all model/source/threshold bytes stayed fixed. It does **not** prove robust useful navigation, biological sensor mapping, later-driving recovery beyond the deliberately censored training-source endpoint, causal training-coverage benefit, topology advantage, hardware behavior or R3. The [prior negative training-v2 Stage C](m7-training-v2-stage-c.md) and recovery collection v1/v2 failures remain immutable failures. Qualification claims are `[]`; no candidate is promoted.
