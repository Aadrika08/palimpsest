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

## Progress ledger

- Plan/API RED `16dca64`: five missing-API failures (20 imported fixture checks
  were accidentally collected; fixture module import now prevents duplication).
  Expanded intended suite: eleven missing-API failures, 0.23s.
- Initial connected source `1197667`: twenty focused pass, 6.55s; 1390 affected
  pass, same six inherited exclusions, 84.03s. Faithful native fixture import alias
  was corrected before crediting its intended wrong-initial RED. That RED showed
  an action before layout refusal; the initial guard now runs before action.
- Namespace alias, changed collector scene, duplicate scene identities and
  reader-copy cap REDs were reproduced and fixed before review.
- Whole-branch review found reused episodes, hidden extra recording files and
  publisher rereads at 64 MiB. Three intended REDs, 1.91s; fixed in one pass.
  Completed contexts now refuse second episodes, native continuation and staged
  labels/predictions. The extra staged-query RED initially used invalid capture
  metadata; corrected complete fixture capture reproduced the actual unintended
  label/prediction before the fix was credited.
- Maximum-duration authored fixture initially reached final publication but the
  old small fixture's 30s custody expired: one failure, 32.61s. Preserved refusal;
  no production clock/cap change. The maximum fixture now constructs custody under
  the existing 180s owner allocation. Twenty-four then pass, 46.98s, including an
  exact 600-interval time_limit close; the final post-terminal-query case was added
  afterwards and independently reproduced RED -> GREEN.
- Final corrected source: 1395 affected pass, same six inherited exclusions,
  125.72s; all 25 new close cases are included. No full-runtime/source GO claimed.
- Ruling: implement this independent recording-close seam while actual runtime
  qualification remains open. It was absent from the executable collection path;
  building it needs no original/catalog/study invocation. Cost if wrong: final
  runtime/parent integration may require adaptation. Recording terminals never
  imply native/process/study admission or fitting authority.
- Ruling: complete data revalidation remains the source reference close behavior.
  Its timing against fixed parent/return buckets is not qualified; integrated
  measurement and a reviewed custody-preserving optimization may be needed.
  No clock borrowing or timing-cap change is authorized by these fixtures.
