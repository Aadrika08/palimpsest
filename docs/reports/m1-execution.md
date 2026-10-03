# M1 execution and recovery evidence

Measured on 2 October 2026, on the R0 Linux laptop and pinned Python 3.11 / MuJoCo 3.3.6 / PyTorch 2.9.0 environment. These results qualify the observed simulation cases on this host, not arbitrary machines or physical hardware.

## Implemented behavior

The single-owner engine supplies manual, privileged analytical teacher and guarded FLYNN paths. Bounded command queues preserve idempotency and distinguish receipt from actual application. Run/pause/single-step/reset/stop and all four ending classes have tests. Only declared camera/contact/goal-bearing inputs reach the student. Invalid policy outputs and recording failures stop execution.

Goal/obstacle edits validate before mutation. Obstacle motion updates joint positions, locked ranges, velocities, geometry and planner caches. Snapshots retain native integration and post-step derived state, mutable model arrays, environment state, complete hidden/retinal state, teacher recovery/PID/planner state, RNGs, pending commands and receipts. Restoration validates runtime/model identity and the initial teacher reset template before application. Branches have new run IDs and a hashed durable parent event prefix.

Snapshots use bounded typed arrays and JSON with native MuJoCo bytes, not general Python pickle. The native decoder is only for trusted matching-version local artifacts. Browser supervision, imported bundles and the interactive workflow belong to M2/M3.

## Checks and results

`PALIMPSEST_SIMULATION_TESTS=1 MUJOCO_GL=egl .venv/bin/python -m pytest -q`: **98 passed**, no skips. This includes actual EGL obstacle persistence, active-contact teacher recovery through recovery exit, goal termination, time-limit crossing, raw-output guards, recorder/queue failures, malformed snapshots and a tiny upstream recurrent fixture. Warnings came from pinned upstream tensor construction, PyTorch CSR support and deprecated TF32 accessors.

Fresh source/restored processes use the actual 128 × 128, 20-obstacle environment, a moved goal, eight preceding ticks and a pending run command. The verifier checks every recorded continuation field except wall latency, final native integration/derived state, full hidden and six retinal tensors, RNG draws, branch IDs and the durable event prefix. Both workers must complete with matching source/lock/upstream hashes. Camera/integer comparison is exact; floating tolerances are fixed at `atol=rtol=1e-6`.

| Controller/device | Compared continuation | Result |
|---|---:|---|
| Manual / CPU | 12 ticks | Passed; all compared values identical |
| Teacher / CPU | 12 ticks | Passed; all compared values identical |
| Full FLYNN / CPU | 100 ticks | Passed; all compared values identical |
| Full FLYNN / CUDA | 12 ticks | Failed strict continuation; retained below |

Machine-readable results, provenance and local evidence paths are in [the evidence index](m1-execution-2026-10-02.json). `runs/flynn-cpu-continuation-qualified` was excluded because an engine metadata edit occurred between its two workers; `runs/flynn-cpu-continuation-stable` is the replacement with matching source identities. Earlier exploratory runs are not substitutes for the indexed cases.

## CUDA limitation and diagnosis

In the retained failed CUDA case, the first bitwise numerical difference was at tick 9: raw readout differed by `2.9802322387695312e-8` and action by `1.1920928955078125e-7`, with identical recorded inputs. These were inside the float tolerance. At tick 10, two right-camera channel values differed by one level, failing exact image comparison. That input difference propagated into retinal/recurrent state; final hidden-state maximum error was `2.696644514799118e-5`. RNG draws matched. This is a failed repeatability result, not a successful snapshot comparison.

An independent frozen-input probe isolates the pinned upstream cell's `torch.sparse.mm` on CUDA from its `index_add`. It repeats each operation 30 times with identical tensors under deterministic algorithms both disabled and enabled, with `CUBLAS_WORKSPACE_CONFIG=:4096:8`. CSR varied by up to `8.940696716308594e-8` with the flag disabled and `5.960464477539063e-8` with it enabled; only the reference trial matched itself in each 30-trial set. Index addition matched exactly in all 30 trials under both settings. No upstream code, weights, action scaling or comparison tolerances were changed. PyTorch's documentation distinguishes seeded randomness from algorithmic reproducibility and does not guarantee results across releases or devices. [PyTorch 2.9 reproducibility](https://docs.pytorch.org/docs/2.9/notes/randomness.html)

Full-model CPU continuation is the measured repeatable profile. CUDA remains explicitly selectable for inference, with strict replay reporting divergence when observed. No silent CPU fallback is used. This does not invalidate lossless recorded playback, and does not establish cross-device numerical equivalence or navigation competence beyond R0's reported development trials.

## Reproduce

```sh
PALIMPSEST_SIMULATION_TESTS=1 MUJOCO_GL=egl uv run --no-sync pytest -q
uv run --no-sync python scripts/verify_execution.py --controller manual \
  --assets data/assets/flynn --output runs/manual-continuation
uv run --no-sync python scripts/verify_execution.py --controller teacher \
  --assets data/assets/flynn --output runs/teacher-continuation
uv run --no-sync python scripts/verify_execution.py --controller flynn --device cpu \
  --assets data/assets/flynn --continuation 100 --output runs/cpu-continuation
uv run --no-sync python scripts/verify_execution.py --controller flynn --device cuda \
  --assets data/assets/flynn --output runs/cuda-continuation
uv run --no-sync python scripts/probe_cuda_repeatability.py \
  --assets data/assets/flynn --output runs/cuda-kernels
```

All output directories must be new. CUDA continuation is not expected to pass reliably; an occasional passing short run does not erase the observed failure. The kernel probe completing means the measurement completed, not that its outputs were identical.
