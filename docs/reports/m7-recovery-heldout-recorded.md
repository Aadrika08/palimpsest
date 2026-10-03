# M7 recovery held-out recorded-input evaluation

**All six frozen candidates completed one recorded-input evaluation against the four reserved teacher sources.** Source was `e4014081faff07c498fbba526da730599c1d5195`, with clean upstream `8d964599119b420de67ee259434d273651a1a76d`. This is held-out teacher imitation, not closed-loop navigation success, R3 qualification or topology advantage. No checkpoint, epoch, seed or model was selected or changed.

The unchanged [protocol](../plans/m7-recovery-heldout-protocol.json), SHA `097321aaf71baaf27bedf6eb3225b17b6345fb667548d19cb4810d08f87bdbed`, fixes all six seed/variant combinations. The [completed teacher stage](m7-recovery-heldout-teachers.md) supplies four independent sources, seeds 1012–1015, at 378/284/274/218 rows. Every candidate evaluated all **1,154 recorded rows** (6,924 model-row evaluations total); there were no new physics intervals or native environment owners. Exact source/episode disjointness from all fourteen admitted train/development sources precedes student loading. Fresh hidden state starts each teacher episode; the unchanged evaluator carries it across its existing windows. No held-out target enters fitting or selection.

| Training seed | Candidate | Normalized imitation loss | Velocity MAE | Wrapped heading MAE (rad) |
| --- | --- | ---: | ---: | ---: |
| 10 | male-original | 0.022269124046 | 0.081493786137 | 0.165927646375 |
| 10 | male-control | 0.020624771482 | 0.086575640033 | 0.155875725184 |
| 11 | male-original | 0.017864021184 | 0.037989053352 | 0.124161690809 |
| 11 | male-control | 0.018912795511 | 0.092328631175 | 0.129404641081 |
| 12 | male-original | 0.021443221970 | 0.052368669256 | 0.159024169297 |
| 12 | male-control | 0.022813123759 | 0.049142185282 | 0.175895983879 |

These are **runner-reported neural metrics**, retained at full precision in the [hash index](m7-recovery-heldout-recorded.json) and original `evaluation.json`. Both retained auditors checked finite, nonnegative values, exact six-row order and 1,154 rows per model; neither independently recomputed neural predictions/losses. Small descriptive differences between these fixed models establish no topology advantage or navigation criterion.

The evaluator reported 12.492681 seconds. Its supervised child completed with exit 0 in 22.280640 seconds; launcher pre-publication wall time was 46.366785 seconds. Enclosing supervision completed with exit 0 in **46.692348 seconds**, covering terminal publication and launcher exit. Internal/child/normal-full/enclosing-hard limits remained 120/150/170/180 seconds. The dedicated recorded tree and controls retain a 64 MiB stage budget, a 1 GiB free-disk floor and the unchanged combined-stage startup reservation of 10,015,997,952 free bytes. Terminal accounting measured 961,326 bytes before terminal publication; later retained audit/index bytes are not part of that observation. Teacher inputs are outside the recorded evaluator's budgeted parent tree. Only the evaluator acquired the writer lease; no outer nested lease was used.

Before and after inventory SHA is `618c2d69d771cea6cc2556523b30f95e6c6c267fe86861629362340d58b16be4`. All **1,193 input identities** remained unchanged: 419 tracked files, 122 upstream files, 20 shared assets, 171 retained corpus files, eighteen model-bundle files, 374 development records, four development documents, 53 teacher records, five teacher-stage documents and seven runtime files. CPU inference binds the original Python 3.11.15 / NumPy 2.2.5 / CUDA-capable Torch 2.9.0+cu128 build, with one CPU thread and CUDA devices hidden; this result is CPU computation.

The finite .25-second monitor retained one descendant PID/start pair, absent after normal exit. There were no sampled survivors, forced sampled signals, sampler errors or PID conflicts. Own and root checks independently acquired and immediately released the actual home writer lease after the command drained. Finite process sampling does not prove universal transient-process coverage. The model child emitted a single existing 417-byte upstream PyTorch sparse-CSR beta-support warning; its stdout and both relevant outer stderr streams are empty. No semaphore warning occurred. The index hashes final drained logs, including the final launcher console, after the top command exited.

The own NumPy-only audit passed in 3.563887 seconds after one auditor-only correction. Its first script treated documented `recovery_input:/absolute/path` source-map keys as literal filenames; the script and failure log are retained. Only namespace/ROOT-relative decoding changed. The corrected audit rehashed all 600 evaluator source-map entries, checked retained teacher fingerprints, all six exact identities/metrics and normal terminal/enclosing bindings, without Torch/MuJoCo imports, model construction, forward or physics. The initial fixed-six control fixture also retained its failure before canonical candidate names and integer-key JSON normalization were corrected; no model job occurred in that fixture.

Root's independent retained audit passed on its **first execution** in 16.950931 seconds: all 1,193 current input identities match before/after, exact teacher/payload disjointness and fixed model identities/order hold, all 6,924 reported model-row evaluations have finite nonnegative metrics, and sampled cleanup/home-lease availability holds. Root receipt SHA is `3d7ffb2fb83d2540384d1f9a4e2031867a367d87bd9aecd2c76956a3789761eb`. The prior root control review passed first execution in 15.951719 seconds. The compact index binds both reviews/audits, failed auditor/control drafts, final controls and primary results without duplicating raw teacher ledgers.

Primary evaluation SHA: `a618f193995b4a1ea1c22e66f3cee26166d5be04e36d65fc6274e40b76197290`. Terminal SHA: `ff28faf2e02793cf63f53dd9840cd869e171a2685b5a1658a775a3427c7f7626`. Enclosing SHA: `c5e34f78bb3e7824b8a7e9ce779336966adc3389cd30ed793306c76f6bd53d36`.

Exact one-shot command from the isolated held-out worktree:

```sh
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=1 ../lab-hardening/.venv/bin/python \
  runs/m7-recovery-heldout-recorded-control-e401408/supervise.py \
  > runs/m7-recovery-heldout-recorded-control-e401408/launcher-console.log 2>&1
```

The actual model slot was released after normal drain and cleanup. Closed-loop held-out execution remains pending separate control review and GO. No useful-navigation held-out threshold appears in the frozen protocol; completion of this stage does not supply one. [Prior negative training-v2 Stage C](m7-training-v2-stage-c.md) and recovery collection v1/v2 failures remain unchanged. Later-driving competence, causal training-coverage improvement, biological mapping, topology advantage, production promotion, R3 and hardware behavior remain unqualified; qualification claims are `[]`.
