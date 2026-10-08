# M7 navigation-v2 selected-checkpoint output-support audit

This is the frozen prospective plan for `M7-NAV-CHECKPOINT-SUPPORT-V1`. Its machine-readable [protocol](m7-navigation-v2-checkpoint-support-v1.json) has SHA-256 `699f6b28e3f566416be1480d961cbca8be7e809501a4d59ed62e1b7c92f660ff`. At this freeze, no checkpoint byte has been opened, no model has been constructed, and no inference has run.

## Goal and evidence boundary

Run the six already-selected ORIGINAL-graph checkpoints once over the unchanged four-source, 1,228-row recorded-development split. Measure action and raw-readout support under the existing `0.05` command deadband. This is a prerequisite diagnostic before any navigation-v3 retraining. It uses no simulator, physics, development-run trajectory, fresh scene, or held-out input.

The completed closed-loop diagnosis found that every augmented development run had zero reverse-command ticks and zero velocity or heading sign changes, with lower median progress and path length. That pattern justifies checking whether the selected checkpoints already lack target-supported signs on common fixed inputs. It does not show that augmentation, optimizer exposure, label quality, or output restriction caused the navigation failures.

The prior independent checkpoint audit verified finite tensors, exact graph buffers and frozen weights, but explicitly constructed no model and ran no forward pass. Published recorded-development loss and MAE do not report output ranges, sign occupancy, within-source switching, or raw readouts. This audit fills only that gap.

## Exact inputs and workload

The protocol pins:

- model index `f938d9799b45b4c33d65a1d2c5363fea4e7b419ad9051722bff1a3df99ea77cf`;
- admitted data manifest `47c4523c40e485ba4839cc80c9db891761791b801cc777755028122a1dbacb41`;
- safe 28-array transfer `a15f4b9267de04a2f952c19e6ddc65b8338696977b764e7418f044b25e6a5271` and metadata `363445d80f13814804768a791bdff859e644f75dc39923daf762884fed70b2db`;
- original graph `5aba0fef99afba666b88e40fc535091454e46d9330580d9280b203e8da0abac0`, graph manifest `7a205342b4ada8ab8b78d6ca866c61735003e601531c65a1c1b6c819df00026f` and cell source `707cba79e7bf92923618ccc596e3d7a2d779edc02a970b0949f6dd3c0d28ae80`;
- the exact six checkpoint paths, sizes and hashes for seeds 10/11/12, old-corpus then augmented;
- four development sequences in exact order: 189, 338, 319 and 382 rows, totaling 1,228; and
- Python 3.11.15, NumPy 2.2.5 and Torch 2.9.0+cu128, CPU one thread, deterministic algorithms and hidden/uninitialized CUDA.

Each checkpoint receives one deterministic pass. Hidden state is zeroed at each source start and carried across its 32-row windows. The exact workload is 39 windows per checkpoint, 234 windows and 7,368 row inferences total. All six artifacts and the complete data roster must admit before Torch import or model construction.

## Existing budget confound

V2 did not match optimizer or data exposure. The old arm had 2,117 rows and 72 optimizer windows per epoch; augmented had 7,197 rows and 236 windows. Across all 20 epochs that is 42,340 versus 143,940 row presentations and 1,440 versus 4,720 updates per fit. The augmented arm appended twelve advice sources after the old sources without filtering, weighting or shuffle.

The selected checkpoints saw different effective budgets because the fitter restores the earliest strict recorded-development minimum:

| Seed | Old selected budget | Augmented selected budget |
|---:|---|---|
| 10 | epoch 20; 42,340 rows; 1,440 updates | epoch 1; 7,197 rows; 236 updates |
| 11 | epoch 16; 33,872 rows; 1,152 updates | epoch 1; 7,197 rows; 236 updates |
| 12 | epoch 17; 35,989 rows; 1,224 updates | epoch 7; 50,379 rows; 1,652 updates |

The selected-budget difference reverses direction for seed 12. Corpus composition, source order, row exposure, optimizer updates and checkpoint selection are therefore joint confounds. This audit reports them but cannot isolate any causal mechanism.

## Fixed measurements

For the target stream, and for each checkpoint's action and raw-output components, report minimum, maximum, mean, population standard deviation, the frozen `0/1/5/25/50/75/95/99/100` percentiles, negative/deadband/positive counts at `0.05`, and within-source cross-sign changes. Per checkpoint also report reverse and stopped velocity counts, exact `tanh` scaling, the frozen imitation loss, velocity MAE, wrapped-heading MAE, and output-stream SHA-256. Per matched seed report mean and maximum absolute action difference and the first differing row.

Recomputed loss and MAEs must exactly reproduce the model index. Classification is descriptive and component-specific:

- `target_support_absent`: targets lack both non-deadband signs, so the component is uninformative;
- `checkpoint_sign_missing`: targets have both signs and the checkpoint omits at least one;
- `checkpoint_signs_present_no_switch`: both signs appear but no source contains a cross-sign transition; or
- `checkpoint_switches`: at least one source crosses between non-deadband signs.

There is no new performance threshold, seed pooling, model selection or automatic next-stage decision.

## Execution and stopping rules

Implementation is one small script plus focused synthetic tests. Reuse the admitted old-transfer reader, six-model candidate admission, weights-only checkpoint loader, model forward diagnostics and frozen loss helper. Tests must first fail for missing behavior, then cover input pins/path escape, exact roster and budgets, sign classifications, source resets/window carry, count/nonfinite/scaling/published-metric failures, no held-out/simulator/training path, output cap and atomic success/failure evidence.

After tests pass, freeze the new script/test hashes in a separate execution manifest and obtain independent source review. Only a GO permits the sole actual invocation. Any pin, path, size, runtime, source, roster, storage or held-out mismatch stops before Torch import. After import, any load, shape, dtype, finite, scaling, count, metric-reproduction, source-drift, deadline or publication failure stops immediately, retains bounded failure evidence and permanently consumes the one attempt. No correction or retry is allowed.

The run is CPU-only with one thread. Limits are 180 seconds internal, 210 seconds normal through return, 16 MiB total output, 1 MiB per log, a 1 GiB free-space floor and a 1 GiB RSS budget. The safe transfer plus six checkpoints is about 7.1 MiB; retained prediction/raw/target arrays are below 0.2 MiB before container overhead. Expected runtime is under 30 seconds, but only the frozen hard limits govern admission.

Success writes a fixed, uncompressed, non-object compact array bundle, report and execution receipt under a fresh output directory. The final report is published last, with no fallible operation after its rename. Independent post-run review may recompute metrics only from that compact output; it may not reopen model/data inputs or repeat inference.

## What it can decide

The audit can determine whether each selected checkpoint expresses target-supported signs and switches sign on the same fixed inputs, whether published selected-development metrics reproduce, and whether any output-support restriction exists before closed-loop state divergence.

It cannot determine why support is restricted, whether analytic advice is correct or student-observable, whether source order or budget caused the result, whether matched-budget retraining would help, or whether any model has fresh-scene capability. It makes no topology, biology, hardware, held-out or R3 claim.

Any later navigation-v3 retraining must freeze exactly one intervention and match old/augmented optimizer and row-presentation budgets. It must reserve four fresh disjoint development scenes and eight fresh disjoint held-out scenes. The unchanged gates remain at least 3/4 goals per augmented seed before held-out, then at least 6/8 per augmented seed. A topology estimand remains a separate study.

## Implementation sequence

1. Commit this plan and protocol alone.
2. Write synthetic tests and record the expected RED failure before production code.
3. Add the smallest analyzer/runner needed to make those tests pass; keep metric logic pure and inject the one model-forward boundary.
4. Freeze script/test hashes in an execution manifest and commit.
5. Obtain independent source review; fix and recommit only before the run.
6. Execute the frozen command exactly once. On failure, retain evidence and stop permanently.
7. On success, independently verify compact arrays, report, receipts, hashes and counts without loading a checkpoint or running inference again.
8. Commit the compact report, push the branch and open a draft PR stacked on PR #103. Do not merge, run CI or edit the shared tracker.
