# Connect native intervals to durable owner and collection close

Continue the approved complete simulation release goal from PR #130 (`b559699`).
The contract map found that the existing interval writer has no terminal close,
and reservation/scene publication deliberately rejects owner/stage target names.
A committed prefix cannot establish a completed owner or a complete collection.

Implement this missing part of the existing complete launcher plan:

1. Reuse the exact durable publication transaction for two separately typed
   recording-close targets. Preserve reservation/scene behavior. Add a final
   pre-admission guard inside the transaction; drift leaves no admitted terminal.
2. Stream and reread the actual committed interval chain, rejecting empty/pending
   tails, gaps, resets, episode/state/world/contact discontinuity and continuation
   after any natural task terminal. Verify first task state from initialization,
   exact admitted layout pose/puck/goal/velocity and fixed owner ordinal/scene/seed.
   Bind counts, raw interval commitment hashes, final task/cursor and motivating
   condition counts. A stopped/failed prefix is not a normal recording close.
3. Connect HeldCollectionExecution.native_interval to one natural episode, initial
   sensor-only cursor, no reset/retry/takeover, <=600 intervals, permanent writer
   stop and the typed recording close. Keep the historical owner(config) denial.
4. Reduce exactly twelve scene-major/model-minor owner closes, rereading their
   recordings. Every collector seed needs >=1 motivating row. Preserve zero
   coverage as a durable failure; never authorize training or drop rows.
5. Exercise authored arrays and faithful native fixtures with real temporary disk
   publication; review one complete branch and verify relevant affected checks.
   Commit/push a stacked draft and update the full goal/evidence matrix.

Recording close is distinct from process/native owner acceptance. These APIs
remain source/data checks: runtime/native/source closure, independent process
identity/exit/drain, parent lease/storage/clock seals and actual stage admission
remain required. All authority/executable/fitting fields stay false. Guards bind
live source/parent custody at the transaction boundary; they do not supply atomic
multi-object filesystem proof or a sandbox against admitted code.

Do not expand the seven-role 80 MiB input limit. Recording verification uses its
separate existing <=600 interval /149 MiB recording allocation and <=1 MiB close
metadata. Keep namespace/retained/output budgets explicit. No actual catalog,
retained/model/study execution, consumed attempt retry, CI or rover work.

All seven simulation release gates and the three prospective decisions stay open.
This unit advances the complete inventory-to-durable-collection route; it does
not replace that route or the full release goal with a component-test exit.
