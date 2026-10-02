# M5 first development transfer mechanism check

Preparation only. This protocol fixes one fresh `development-test` instance:
seed 8, local_cue, change, acquisition layout, cue/gate event tick 300. It enables
no held-out split and makes no R2, FLYNN, biological or generalization claim.
There is no actual result yet. A development case can reveal a targeting rule
and still fail to inspect its target; that outcome must remain visible.

The only production extraction is the pure
`memory_experiment.selection_for_condition(condition, m, trigger, *, u=None,
history=None, gold_target_ids=None, limit=1)`. The existing synthetic comparison
and this recorded-case evaluator share that selector. It validates normalized
copies, never fits or mutates input, accepts E only for retrieval and gold only
for oracle, and bypasses selection when there is no observed trigger. Nine
conditions retain the same target budget: own, swapped, sham, no-U,
hand-authored fixed local rule, history-independent canonical first fact,
association traversal, nearest complete matching-history retrieval, and
privileged oracle. Their access differs and is reported explicitly; payload,
envelope, runtime history, validation input and behavior input bytes are separate.
The source/test bank, evaluator gold and regime never enter fitting.

The verifier pins the two actual E/U collector bundles from frozen `1cb70a3`:

| Role | Relative artifact | SHA256 |
| --- | --- | --- |
| own | `runs/m5-acquisition-batch-20261002/local_cue-history.json` | `016c5b5e9472b116d065fb922b32d64089db6e27839aec09d751238f8ce7ffc1` |
| swapped | `runs/m5-acquisition-batch-20261002/paired_cue-history.json` | `64628e37cc6e861194f810baa92926eba8f57260047cdd8ad320a4601023d213` |

It validates both bundles and requires an exact E-only refit to reproduce each
stored U. Own/swapped history and new-case entity/evidence namespaces must be
disjoint. The shared-selector edit changes the whole-file case producer hash;
new case IDs/hashes belong to the next frozen source. Old `1cb70a3` case
recordings/snapshots are not reinterpreted as new-source cases. The retained
historical E/U remains usable because its core memory producer/protocol is
unchanged and its bundle identities are checked. Current source, lock, pinned
upstream, driver, case and transfer protocol identities are retained and checked
again after execution.

Six fresh recording stages execute serially, without retries or substitutes:

1. **source**: acquire exactly ticks 0..299 with the existing explicitly
   privileged manual pose supervision. Live M starts unknown; E/U is empty.
   Both facts must be known from retained declared observations. No synthetic
   known samples seed live state. Capture a registered native snapshot paused
   at episode_step 300, sensor cursor 299, before the scheduled event.
2. **anchor**: restore that snapshot and install own U only, take zero steps,
   then register a new paused native snapshot at the same boundary.
3. **own, swapped, sham, no-U**: restore the anchor independently and replace
   only U with the declared artifact. Sham is an exact copy of own; no-U is
   empty. All native/environment/observation/controller/RNG/application/M/E and
   supervisor hashes must equal the anchor before any continuation step. Each
   registered initial snapshot must also contain its exact expected U, checked
   separately because the invariant hash deliberately excludes U.

Continuation accepts only the previous published effective declared bearing,
with a fixed one-tick delay: velocity command .65 and `atan2(y,x)` heading
bounded to [-pi,pi]. It receives no pose, distance, map, private world truth,
regime or U. Every command is paired with its declared bearing and exact
episode_step. Recorded manual actions must equal the exact float64 conversion
used by unchanged `Engine._action`; policy float32 behavior is irrelevant to
this manual driver. At most 300 continuation ticks are allowed. No scripted
return, target visibility override, private goal fallback or rescue is present.

The lower landmark is invisible after the cue in this acquisition geometry.
An own-U lower request can remain queued without starting inspection; the
active-inspection timeout does not apply to an unstarted request. Engine defers
common-goal completion while inspection is pending, so forward continuation may
lose all eligible goal cues. This expected `CueUnavailable` remains a failed
terminal recording, with its explicit runtime_failure event and unstarted
queue. Unchanged Engine.close writes `status=failed`, `final_phase=failed`,
`close_reason=operator_closed`; the worker outcome and manifest must agree.
Only this declared cue-loss failure with queued requests and no active target is
admitted for mechanism reporting. It permits exactly one extra declared driver
input at the failed attempted tick, without inventing a numeric transition.
Any unexpected child, identity, cleanup or validation failure stops subsequent
stages at the first failure. Source and anchor must complete paused.

The reader accepts completed or failed terminal recordings explicitly, exhausts
existing `iter_ticks` checksums/counts, checks safe paths/run IDs/world geometry
and retains fingerprints. It never coerces failed status to use a completed-only
artifact reader. Each child has the existing 160s process-group watchdog,
150s internal wall bound, 192MiB recording ceiling and 1MiB per-stream logs.
Worst-case six recording quotas total 1.125GiB, plus bounded logs/native snapshots.
Engine cleanup is attempted normally; timeout and cleanup failures remain
failures. Runtime requires the parent's exclusive reviewed/frozen source slot.

Evaluator gold uses the retained actual before/after cylinder-clearance labels
and the genuinely observed pre-event M: only a previously known expectation
changed by geometry is a gold target. U/select/fit do not construct gold. Nine
targeting scores report exact set, false/missed targets, precision/recall and
correct null abstention without arbitrary success thresholds. Four actual
branches additionally report requested/started/resolved/timed-out and unresolved
inspection, fresh correct post-event facts, navigation_pass, revision_pass and
their conjunction task_pass. Reaching the common goal while retaining a stale
changed expectation is not a revision pass. Own/sham trajectories must match
under existing replay tolerances; own versus other U trajectories are reported
with first divergence. Frames are not independent experimental samples.
`mechanism_checked` does not override a branch task failure or establish R2.
Operator blindness/source authenticity remain unverified.

Pure preparation checks (no actual simulator/model jobs):

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest \
  test_memory_transfer test_memory_experiment test_memory_cases \
  test_memory_history test_memory_task test_memory test_records -v
```

Exact proposed gate command, only after root review/commit/freeze and GO:

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/verify_memory_transfer.py \
  --repo "$PWD" \
  --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn \
  --output "$PWD/runs/m5-memory-transfer-20261002"
```

Adding `--plan-only` reads/pins histories and emits the fixed plan without
creating output directories or starting runtime. The first plan-only check
completed successfully; actual acquisition/branch behavior remains pending.
