# BGT-TURN-1: retained-fit turn transfer

This prospective contract was frozen before execution. The later single observed result is indexed below; the existing adaptive and loaded profiles remain unchanged.

The new regime is nominal `[0,+0.2]` and `[0,-0.2]`: opposite-sign wheel controls, unlike the same-sign straight calibration probes and prior straight ±0.3 evaluation. This is command transfer for one existing fitted body, authored lane and seed. It does not establish new-body, task/body composition, cross-seed or hardware competence.

## Immutable starting point

Use the accepted report from `5f22c1c06edec7ab0ba27447e0c2360f6e09243d`, SHA `231956442698655fc8f511018067a9515797b2baa7dd5e9f7d1a174374546121`, and its external `source/fitted.snp`, SHA `af42213e0bc0440906371a53fe23902b02c692e806c64b609621fed2feb63ca4`. The container must pass the current pure session validator: schema 6, episode 4/step 0/total 480, paused fitted phase, zero encoders/time/manual intent, no pending commands, exactly 400 accepted samples. Pins:

| Identity | SHA256 |
|---|---|
| Samples | `8dcc254855a32bf41870fa4fb8660f6e96e4fbb3411077f816802985b4d4284c` |
| Fit | `4d738e670b89cad1ca5db18dbb64d4465cc8f22663503d3c663fc6a6000a4428` |
| Complete fresh session | `2086d435f0bd40a5b85997ede4f7b8666ac042ecda8e135e34fba5ee239ba77b` |
| Fitted model | `bf3ca4b0d32600444e0f23e658c790da50a7675fb3c26fee8f9b0a16e0839d67` |
| Adaptive profile | `c65c123589c28bc2e19862e05d1369a6381ddca7c0c37381e78a2111475abdd5` |

Every compensated owner restores that same native snapshot through the existing Engine validator. A pure container read is not native restore qualification. No guard is weakened if current software is incompatible. This is not a replay of the historical recording; its strict same-software replay contract remains unchanged. Record current HEAD/runtime/harness/upstream/assets and original input pins separately.

## Six fixed owners and measurements

Order: baseline-left, uncompensated-left, compensated-left, then corresponding right trials. Each has 120 intervals; retain all raw data but score only ticks 20–119. Baseline gears are `[3,3]`; the other conditions use `[2.4,3]`. Start `[-3.5,0,0]`, goal `[-3.5,3]`, seed 1, checker texture, radius 0.06 m and track 0.36 m are fixed. Baseline/uncompensated reuse the standalone native collector and explicit world/model override. Compensated uses the actual adaptive Engine with unchanged accepted samples/fit and fixed nominal input. No refitting, arbitrary fit-preserving reset, direct ctrl write or true-pose feedback.

Before any numeric step, compare exact integration bytes, environment values **and absence**, and canonical model with only actuator gear excluded. Six initial SNPs are published under the aggregate quota, then immediately checked for ≤16 MiB before stepping. Actual camera admission uses the fresh observation. Authored standalone diagnostic traces retain their ordinary profile-world/playback limitation.

Keep the existing pinned Euler pipeline, ten pre-control caches plus end cache, bounded contact arrays/ownership/support classification, dt/rate/control bounds, exact effective conversion, and callback cleanup. Record world-only contacts; reject unexpected robot contacts, invalid cadence, overflow or terminal outcome. This is discrete cache coverage, not continuous collision/force measurement. First failure packets and unstarted rows remain visible.

Offline evaluator inputs (pose, shafts, increments, dt, control, action and time) must match the published arrays exactly. Compare aligned 100×2 shaft-rate RMSE, absolute cumulative wrapped-yaw deviation, and absolute authored lane/world-Y deviation against each direction's baseline. All three compensated errors must strictly improve over uncompensated, separately in both directions. Lane-Y alone does not establish planar tracking, and settled results do not qualify transient behavior.

**Collect all six valid trials before scoring.** A metric failure is a completed `failed-functional` outcome, not an infrastructure failure, and cannot suppress later valid trials. Contact/invariant/storage/owner failure stops immediately with the remaining rows `not_started`. A functional exit 1 is accepted only with complete six-owner/720-tick/six-SNP evidence and no supervisor error/failure; it is never relabelled a pass. No retries or threshold changes.

## Hard bounds and launch boundary

| Resource | Bound |
|---|---|
| Native owners / intervals | 6 / 720 |
| New initial SNPs | 6, each ≤16 MiB; historical input is external |
| Owner / inner / outer deadline | 180 / 1,200 / 1,260 s |
| Aggregate / free disk floor | 2 GiB / 1 GiB |
| Recording / result per owner | 256 / 64 MiB |
| Native log / control file | 1 MiB |
| Headroom / staging allowance | 8 / 128 MiB |

Fresh camera shape must be uint8 128×128 RGB. Per-interval admission is 233,472 bytes: four recorded camera arrays, ≤32 KiB body arrays and 4 KiB overhead. Aggregate: 168,099,840 numeric + 100,663,296 snapshots + 402,653,184 results + 16,777,216 logs + 25,165,824 controls + 134,217,728 staging + 8,388,608 headroom = **855,965,696 bytes**. Per-recording admission is **30,113,792 bytes**. Fresh storage recount and actual writer admission remain authoritative. One inner lease; the later outer launcher takes none. Finite 0.25 s PID/start sampling is not universal transient-process proof; any forced containment or survivor fails the gate.

Preparation checks:

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python -m unittest discover -s tests -p 'test_verify_body_turns.py'
PYTHONPATH=src ../lab-hardening/.venv/bin/python -m unittest discover -s tests -p 'test_verify_body_compensation.py'
```

The fixtures cover real numeric packet/metric/admission guards with simulated subprocess/native-reader boundaries; they do not claim physics or native restoration. The only shared extraction is the existing fixed 100-interval metric kernel; the old straight trial table/contact/settling/rate guards and arithmetic remain unchanged. No production src/API/profile/UI/dependency edits.

Prospective verifier arguments, to be launched **only after** inventory/outer-launcher review and runtime GO:

```sh
PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 ../lab-hardening/.venv/bin/python scripts/verify_body_turns.py \
  --assets ../r0-reproduction/data/assets/flynn \
  --calibration-report ../body-adaptation/runs/m6-body-adaptation-development-v2-20261002/report.json \
  --fitted-snapshot ../body-adaptation/runs/m6-body-adaptation-development-v2-20261002/source/fitted.snp \
  --output runs/m6-body-turn-transfer-development-20261003
```

Curved/transient/task motion, different body/load/friction/gear, broader held-out coverage and physical actuation remain separate open gates regardless of this result.

## Observed fixed-gate result

The single approved invocation at `1c87b273` passed six owners/720 intervals/six initial SNPs. All six settled metric comparisons strictly improved. Source/upstream/assets/external inputs were unchanged; every owner/inner/outer exit was 0, with no forced signals or sampled survivor. The [evidence report](../reports/m6-body-turn-transfer.md) binds the original results/inventories and independent retained audits. This closes only the stated same-fit turn-command-transfer diagnostic; the limits above remain. No retry, recalibration, source/control change or threshold change occurred.
