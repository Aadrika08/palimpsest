# M7 recovery research development evaluation

**The fixed development gate passed once:** each original candidate reached at least two goals in its four declared scenes. Source was `228232c50d5fddcaad1fb72f65bcb89ad2a896c7`, with clean pinned upstream `8d964599119b420de67ee259434d273651a1a76d`. It is development evidence, not held-out qualification, a topology advantage, a causal recovery-data benefit or a production promotion.

The [source contract](../plans/m7-recovery-development.md) and [protocol](../plans/m7-recovery-development-protocol.json) fixed seeds 10/11/12, both frozen variants and scenes 1100–1103. Explicit research admission reused the existing tensor loader and evaluator; production/v2 admission and the [training bundles](m7-recovery-training.md) were unchanged. All 24 planned serial CPU owners completed naturally, recording 8,552 intervals and 24 initial native snapshots. Twelve paired initial fingerprints matched exactly, with all six candidates sharing the same scientific initial state for each of four scenes.

| Training seed | Original goals / 4 | Rewired goals / 4 | Original intervals | Rewired intervals |
| --- | ---: | ---: | ---: | ---: |
| 10 | 2 | 3 | 1,218 | 1,428 |
| 11 | 2 | 1 | 1,244 | 1,356 |
| 12 | 3 | 3 | 1,693 | 1,613 |

Both variants total 7/12 goals. Originals retained four stalls and one time limit; controls retained four stalls and one time limit. These small, fixed development counts support no topology advantage or generalization claim. No scene, checkpoint, model seed or outcome was replaced, and no fitting or held-out input was opened. The earlier negative [v2 Stage C development result](m7-training-v2-stage-c.md) remains retained under its unchanged threshold; this new corpus/candidate result does not reclassify that failure.

Enclosing supervision completed with exit 0 in **833.704264 seconds**, below the 1,850-second normal-admission deadline and 1,860-second hard bound. Launcher pre-publication wall time was 833.416500 seconds. Every owner closed normally with exit 0 and no owner alive. The finite .25-second sampler retained 28 PID/start identities, all absent after exit; sampler stopped with no errors, forced signals or surviving sampled process. This does not prove coverage of every possible transient descendant.

Policy timing and environment-step timing are recorded separately from owner wall time. Summed policy-call time was 29.084537 seconds and environment-step time 54.739523 seconds across all 8,552 intervals. These measured sections exclude model startup, rendering/publication outside those sections and shutdown; they are not end-to-end throughput or continuous-inference claims. Runtime remained Python 3.11.15, NumPy 2.2.5 and CUDA-capable Torch 2.9.0+cu128 doing CPU float32 computation with one student thread. All 24 stderr files are identical 1,119-byte Sparse CSR beta and TF32-settings deprecation warnings; no semaphore warning was found. Both outer stderr streams are empty.

The [hash index](m7-recovery-development.json) references the original evaluation, functional receipt, terminal/enclosing receipts, controls, byte-identical inventories, final drained logs and both audits. The full raw file ledger stays in `evaluation.json` rather than being duplicated here: 374 recording/snapshot files, 1,710,948,058 bytes. Terminal managed usage was 1,714,816,760 bytes under 4 GiB, with the 1 GiB free-disk floor unchanged. Per-owner combined recording/snapshot cap was 160 MiB, with 180-second owner, 1,800-second internal evaluator and 1,830-second evaluator supervision limits. Before/after inventory SHA is `c3269a9162058234076c9d45e692be4722290ca25cc892ecfec662378bbfc009`; tracked source, upstream, assets, fourteen-source corpus, six models / eighteen frozen bundle files and scoped runtime metadata/entrypoint bytes were unchanged.

Own NumPy-only retained audit passed in 3.829107 seconds after an auditor-only correction. It checked all indexed hashes, numeric action/control/pose guards, exact scientific initial fingerprints, outcomes, logs and sampled cleanup. The initial auditor incorrectly collapsed the pinned two-stage float32 wheel conversion into algebraically equivalent `2v ± heading`; that failed script/log is retained. The corrected auditor follows the exact upstream conversion, clipping and scale. No product or result bytes were changed.

Root's independent retained audit passed on its **first execution**, in 29.589011 seconds, without importing Torch/MuJoCo, running inference or stepping physics. It independently checked all 8,552 numeric rows, 374 files, all 24 native scientific initials, four scenes, outcomes, 255 evaluator source entries, tracked/upstream/assets/runtime/model identities and cleanup. Root receipt SHA: `cda837ffbb128ba14a2981512421501fff61359d8090c9ca18553474d3711f09`.

Primary evaluation SHA: `cdcf32103d047f9a9904532f7ca281b8f5f8c6554c2051a93ac6156e744a81a3`. Development receipt SHA: `3328dd6bccf0b65879e8aa208c70707a01b5190e18fa65e47ce4671dbf674f8f`. Terminal SHA: `16f7b17e22d54fd80ed33961cd512b076278bd9ab74abdf0801e349cab57a5d7`. Enclosing SHA: `b27fed725758befac4b9ee44235d1d141c82560c87655009a4f85bbc9ca53a54`.

Exact one-shot invocation:

```sh
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 ../lab-hardening/.venv/bin/python \
  runs/m7-recovery-development-control-228232c/supervise.py \
  > runs/m7-recovery-development-control-228232c/launcher-console.log 2>&1
```

The runtime slot was released after normal enclosing exit. The earlier collection failures and right-censored first-cycle corpus remain immutable; this result does not cure those failures or establish later recovery. Historical v2 reserves held-out teacher scenes 1012–1015 and closed-loop scenes 1200–1207, but defines no useful-navigation held-out success threshold. Any next held-out stage needs separate reviewed admission and execution; reported outcome counts alone cannot establish R3 or capability qualification. No biological sensor mapping or physical hardware claim is made.
