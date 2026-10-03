# Puck model mechanism — bounded fixture evidence

Frozen source `bea60f06493e7ec163cda1bcae5612f0434a9d2f` passes all **four checks, no skips**, in 5.010 s. The 60-second supervisor exits zero in 6.440 s (6.442 s measured wrapper wall); all 311 tracked source identities remain unchanged and the checkout remains clean. All four indexed retained files were independently rehashed and the terminal test log checked.

The checks cover the actual float32 tanh → float64 scaling at ±0.4, finite gradients, deterministic repeated seeded fixture fitting through all 30 epochs, earliest recorded-dev selection and exact prediction from reloaded numeric parameters. Pure fixtures admit all 20 fixed source slots, preserve float64 labels, reject malformed archive headers before allocation, and bind report/protocol/source identities. A reviewed publication defect was fixed before this gate: final sync failure or an expired deadline leaves only `report.pending`, which the loader cannot admit. Failure injection and successful atomic publication both pass.

This is **authored fixture evidence**. No actual demonstrations were collected or trained here, and no learned manipulation, native student replay, held-out or physical result is claimed. The independent phase supervisor and model remain separate; the model supplies both continuous actions.

Run the explicit CPU mechanism check from the source checkout with the existing simulation environment:

```sh
PALIMPSEST_TEST_PUCK_TORCH=1 PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest tests.test_puck_model -v
```

Use one model/runtime job at a time. The retained wrapper under `runs/` adds source inventories, the 60-second bound and byte limits. Exact hashes and artifact paths are in [the evidence index](m6-puck-model-mechanism.json). Raw files remain in the ignored `.worktrees/puck-training/runs/` directory; the [training plan](../plans/m6-puck-training.md) describes the still-required collection, actual three-seed training and separate runtime stages.
