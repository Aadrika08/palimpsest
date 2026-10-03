# Fixed puck trainer and research model

This implements the separate trainer/model slice of the
[hybrid learning plan](m6-puck-learning.md). Collection, native student ownership,
development rollouts and held-out admission remain separate. Production assets
and controller registration are unchanged.

`scripts/train_puck.py` accepts only seeds 21, 22 and 23. Each invocation requires
the expected SHA256 of a passing collection report, then independently admits
all 16 train and four recorded-dev sources using the existing reader. Source,
feature, float64 target, protocol and collection-report hashes enter the training
protocol. All source bytes are checked again before and after optimization.
No held-out input argument exists. `--prepare-only` imports neither Torch nor
MuJoCo and writes no model or output directory.

The procedure remains 30 epochs, Adam .001 without weight decay, batch 64,
gradient norm cap 1, one CPU thread, float32 parameters and seeded training-only
permutation each epoch. The stateless network is `9→32 tanh→32 tanh→2 tanh`.
Its normalized float32 result is promoted to float64 before multiplication by
.4; the normalized MSE consumes unchanged float64 labels. Recorded-dev selection
uses the earliest minimum, with all 30 epochs retained. Each of the three seeds
must be reported; this code does not choose a winning seed.

`puck_model.py` shares that exact action arithmetic between fitting and inference.
The checkpoint holds only six fixed finite float32 parameter arrays in an
uncompressed NPZ. The reader rejects duplicate/unknown members, compression,
object arrays, invalid shapes/dtypes and nonfinite values, and checks NPY headers
before allocation. It retains the existing 1 MiB checkpoint / 2 MiB expanded caps.
No pickle loader is used. The research loader requires the expected completed
training-report SHA, exact file ledger, 30-epoch earliest-minimum selection,
learning protocol and runtime source hashes before importing Torch. Prediction
receives the nine declared inputs; it has no world, teacher or own cursor access.
The future native owner remains responsible for staging and committing that
independent cursor only after a completed interval.

Outputs require a new `runs/.../seed-N` directory outside all teacher owners.
The existing storage lease enforces 16 MiB per seed, 64 MiB aggregate and 1 GiB
free floor. The internal 120-second deadline includes source checks and is observed again
after the final report staging file is synced, before atomic publication. Failed
report staging remains `report.pending` and cannot be admitted by the loader.
The report labels its earlier elapsed sample as preceding report staging; the
external supervisor measures complete process duration. A separately frozen launcher must preserve the original
180-second TERM / 15-second grace / 200-second supervisor limits, sequential
seed order, all planned statuses and cleanup. No launcher or actual training run
is admitted by this source document.

Pure checks:

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest tests.test_puck_model.PuckCheckpointTests
```

The separate opt-in CPU mechanism check (`PALIMPSEST_TEST_PUCK_TORCH=1` with
`tests.test_puck_model`) exercises exact output limits, finite gradients,
deterministic seeded fixture fitting and restored parameter prediction. It must
wait for the exclusive model slot. Fixture success is not learned task success.
