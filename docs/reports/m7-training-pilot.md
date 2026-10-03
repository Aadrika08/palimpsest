# M7 reduced-model training pilot

The original and degree-rewired models both completed the frozen CPU imitation pilot. This is a separately trained artificial interface to a 138-node MaleCNS neighborhood; it does not qualify closed-loop navigation, a topology benefit or R3.

At frozen training commit `e1f9ba8`, the actual CPU mechanism check passed in 2.482 seconds: seeded forward/reset equality, finite gradients, fixed recurrent weights, bounded actions and invalid-input/readout rejection. All captured sources remained unchanged.

The existing R1 LabSupervisor collected 16 fresh teacher runs, scene seeds 100–115, each exactly 150 ticks: 2,400 total. All owners exited zero with completed recordings, unchanged runtime and normal supervisor shutdown in 224.078 seconds (external watchdog 224.328 seconds). No reset, replacement scene or retry was used. The retained collection is 483,627,343 bytes including snapshots. Each run passed pre-step storage estimation and final 32 MiB size acceptance; writes shared a 1 GiB hard limit. The code is preserved as [collect_male_teachers.py](../../scripts/collect_male_teachers.py); the exact invoked copy and protocol remain in the hashed collection bundle.

Train scenes 100–107 supplied 1,200 ticks; dev 108–111 and held-out 112–115 supplied 600 each. Both variants received the same feature/target arrays, initialization seed 0, five epochs and optimizer budget. Both dev-selected checkpoints were written before either held-out evaluation. Training and both evaluations completed in 23.336 seconds under a 660-second process watchdog, with source and input fingerprints unchanged. Each model has 61,872 trainable parameters; both selected epoch 5.

| Variant | Held-out loss | Velocity MAE | Wrapped heading MAE (rad) |
| --- | ---: | ---: | ---: |
| Original extracted topology | 0.048314735 | 0.023965252 | 0.259441179 |
| Degree-preserving rewired control | 0.046464557 | 0.015329567 | 0.252368256 |

Loss is the frozen `mean(0.5*((velocity_error/3)^2 + 1-cos(heading_error)))`. These are 600 correlated recorded control ticks from four scenes, not 600 independent trials. The control's smaller loss in this one paired run supports no topology or population claim. A model evaluated on teacher observations has not demonstrated that its own actions reach goals.

The [protocol](../plans/m7-training-protocol.md) retains graph boundaries, type missingness, the artificial 388-feature encoder, positive-count weight normalization, allowed inputs and storage/time limits. Fresh 303,341-byte checkpoints and their hashes are retained locally. The [JSON index](m7-training-pilot.json) binds the collection, mechanism check, training protocol, source checks, both checkpoint/graph files and complete epoch/held-out reports. Raw data and checkpoints are ignored by Git.

Next: bounded checkpoint loading, explicit male-policy state/snapshots and actual closed-loop evaluation. Multiple training/control seeds and a separately frozen analysis are required before a topology-effect claim. Physical and biological-interface claims remain absent.
