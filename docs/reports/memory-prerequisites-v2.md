# Memory prerequisites v2: eight recorded owners, failed scientific close

7 October 2026. The approved registration and single eight-cell invocation are
consumed. All eight owners exited successfully and their inline audits reported
the required acquisition/route/retreat or five-control invariant results. **The
campaign did not qualify:** final driver publication exceeded the unchanged
1 MiB control-envelope cap. Its independent readout then stopped on a missing
`readout_started_monotonic` field in the last persisted checkpoint.

`native_prerequisites_passed=False`, `r2_complete=False`,
`qualification_claims=[]`, `paired_pilot='unattempted-by-scope'`, and
`held_out_used=False` remain explicit. No retry, corrective study, pilot, held-out
run or physical operation followed. The old narrow restore pass is separate
evidence and does not replace this failed campaign.

## Frozen scope and actual entry

See [the approved plan](../plans/memory-prerequisites-v2.md). One selected
profile, eight cells, seed 400 and local-cue regime were frozen before native
entry. Both restores used this campaign's newly acquired south-prefix, rather
than the historical source used by the earlier narrow pair.

- Implementation: `f97653a`; committed registration/entry head:
  `1be1d7fe453fc31bc51bb1264e5f6ab1c8ca72d4`.
- Registration SHA: `2aaa8a2a853804ccb3eca1a9fe773f662f96c42967c542a622f1bb9c9168379b`.
- Profile: `7faba0a56d129ea051d5c28a019964034b546923dbe49cedb3a605af84437ec3`.
- Worker protocol: `ae7c4014868d5ade9928cfdda2729c3562df38404a32f7c4b7980d4cbb567a5d`.
- Runtime: Python 3.11.15, MuJoCo 3.3.6, NumPy 2.2.5, Torch 2.9.0 CPU;
  one numerical thread, EGL, CUDA disabled.
- Registration preparation exited 0 in 4.039770656 seconds, within its separate
  180-second cap, including the Git commit. The retained preparation receipt is
  a post-exit transcription of the actual tool result.
- Invocation: one attempt, eight owners maximum, zero retries/corrective studies;
  original 4,300-second owner phase plus 600-second readout, total 4,900 seconds.
  All three final exit codes (pipeline/native/watchdog wrapper) were 1. This was
  a software failure; the generic launcher wording does not prove timeout.
  The failed receipt contains no exact invocation duration, so none is invented.

## Recorded outcomes and their limits

These are retained inline owner reports, **not a completed independent eight-cell
qualification**. Every row reports `raw_audit_pass=True`, acquisition and completed
supervision with return code 0. Full/prefix acquisition changes memory, so their
`invariants_preserved=False` is expected; only repeats require that flag.

| Cell | Run ID | Reported result | Continuation controls | Owner seconds |
|---|---|---|---:|---:|
| south-no-event | 86af99bae2204c229f78c50e664dba2f | acquired, goal | 196 | 133.81 |
| south-change | e30feb308d624e89bf654bc28e9cbffb | acquired, goal, retreat, blocked first commitment, one replan | 541 | 205.76 |
| north-no-event | f702dd51776a496d94912212b3935bd8 | acquired, goal | 195 | 132.45 |
| north-change | a9df46aa0fc94b3e97e84c13024f31fc | acquired, goal, retreat, blocked first commitment, one replan | 565 | 190.77 |
| south-prefix | 5f11347a568043479769953d6bd856dd | acquired and paused; goal not required | 0 | 126.39 |
| north-prefix | 4850f12d2e904bfebaee1f5eec46f539 | acquired and paused; goal not required | 0 | 132.57 |
| restore-1 | f8001848d02044698fbcf73335a6c252 | acquired invariant preserved, five controls | 5 | 23.32 |
| restore-2 | 38be036007f64bf7a95969c4678d9ee8 | acquired invariant preserved, five controls | 5 | 22.67 |

Fresh south source: 1,559,948 bytes, SHA
`cecf38f27d83eb373b4deba62bb3edf8646a6ef61e506c594d0da458401c7f8f`,
invariant `0a764fda9d8e92863e095b91fbeb82eff9fb73436ff49232bc404f335c690b7e`.
The source-producing job, exact snapshot path and acquisition receipt identities
are retained in `fresh-source.json`. Both post-repeat snapshots remain unchanged.
Their recorded native SHA strings differ; **no completed legacy or candidate pair
comparison, exact trace-equality result, or final immutable-input attestation was
published**. Do not substitute inline results for those missing gates.

## Exact failure and repair boundary

`native-stdout.log` records the primary `ValueError: Control envelope exceeds
1 MiB`, followed by the auditor's `KeyError: 'readout_started_monotonic'`.
The driver adds readout timestamps in memory, merges independent owner analysis,
then writes its final receipt. That analysis embeds full `owners[].audit` reports
already represented in `attempted[]`, including large memory maps and receipt-ID
lists. Both normal and failure publication attempted the oversized envelope.
The previous 501,076-byte checkpoint therefore remains `status='running'` with
all eight attempts but without the final timestamps. It is preserved unchanged.

The separate authoritative `scientific-close.json` says
`status='scientific-close-stop'`. Its empty owner list means the auditor stopped
before populating/readback of campaign owners; it does not mean no owners ran.
No state projection or late scientific regrading was performed during retention.

A static independent review identified the smallest prospective software repair:
omit redundant nested audit reports from the driver's owner summary, while
retaining complete attempts, raw evidence, independent recomputation and the
1 MiB cap. A realistic nonnative eight-owner publication regression is necessary.
That repair belongs on a separate branch; it cannot alter this allocation's
disposition. A new scientific readout or invocation needs a new approved scope.

## Software verification

Before native entry, focused checks reported 49 passed in 15.99 seconds. The final
full suite reported 1,064 passed, 24 skipped and 39 warnings in 283.90 seconds.
The tool daemon restarted during that suite; the original process completed and
its final summary was retained, but its shell exit code is unavailable. Skipped
opt-in native checks are not native evidence.

An initial software run encountered the existing 2 GiB free-space admission floor
because `/tmp` had only 1.7 GiB free; software temporary files were moved to an
ignored workspace directory. No scientific gate was lowered. Review findings
about exact runtime versions, original launcher clock, first-repeat post-state
admission and detached nonnative process containment were fixed before entry,
with retained red/green checks. The fresh static review reported no remaining
Important/Critical finding in its reviewed scope, but missed this real receipt
growth. Existing tiny mocked owner reports did not cover it.

## Cleanup, retention and reproduction

Original launcher cleanup reports all eight exact owner identities already
exited, with no required kill. A separate post-close retention review observed
all eight PID paths absent. Invocation storage measured 1,335,036,511 bytes under
8 GiB. Retention readback measured 1,346,638,138 bytes across the same three roots
before subsequent prose/review receipt files; the cap remained unchanged.

The [publication](memory-prerequisites-v2-evidence/publication.json) and
[index](memory-prerequisites-v2-evidence/publication-index.json) retain the exact
closed-byte inventory. The [97-member ZIP](memory-prerequisites-v2-evidence/retained-records.zip)
is 10,954,436 bytes, SHA
`5f7a29ff110fe098b84b3d6660e1f164953a06be27dfbcde96310351d6898504`.
An independent readback matched all members and all 288 indexed original files,
including 189 raw NPZ chunks kept locally. Seven published canonical/log copies
are byte-identical to the originals. Snapshots, event streams, worker reports,
owner/jobs/supervision receipts, registration, marker and control logs are packed.

The complete local raw root is
`runs/memory-prerequisites-v2-20261007T171411Z` in the
`research/memory-prerequisites-v2` worktree. The ZIP excludes NPZ chunks and
zero-byte storage locks; it is **not a self-contained raw replay bundle**.
Retained hashes do not supply missing inputs to a fresh checkout. Use ZIP byte
readback for review, not the consumed launcher, registration preparer or auditor.
No scientific retry, decode or comparator invocation was part of packaging.

The selected-profile prerequisite gate, pilot, R2 benefit, held-out confirmation,
learned puck/navigation, sufficient Afterimage, browser acceptance and human
artwork/operator acceptance remain open. CI and physical rover remain deferred.
