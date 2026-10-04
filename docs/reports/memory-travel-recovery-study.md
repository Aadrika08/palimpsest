# Fresh memory travel recovery study

4 October 2026. The frozen **0.25 m candidate passes complete changed-route
travel**, and all four fresh full-route plus both fresh acquisition-prefix
prerequisites pass. The two native restores each execute exactly five audited
ticks from the same new south-prefix snapshot, preserve their initial invariants
and produce identical non-timing traces, but their final post-state digests differ.
**Six of eight prerequisite gates pass; the restore pair gate fails. No pilot is
admitted, and no native retry occurred.**

This is a separately registered study after the historical ENOSPC abort, using the
unchanged scientific source frozen at `0f1f8ea`. CI is outside this work.
[Prospective contract](../plans/memory-travel-recovery-study.md),
[machine registration](memory-travel-recovery-evidence/registration.json),
[exact invocation](memory-travel-recovery-evidence/native-launch.json).

## What changed and what was reused

The new branch starts at `4913c43`. Registration commit `b2f7776` precedes the
readout preparation commit `8824da0`, which is the native implementation head.
No executable science, geometry, sensor, controller, recorder or public API changed.
The version-3 opt-in CLI, candidate hashes/order, CPU FLYNN, unknown initial M,
no-U, fixed visibility/arrival rules, task budgets and old defaults remain frozen.
The standalone independent readout and its tests are documentary tooling.

The measured 2,100-tick actual writer/reader storage qualification was retained;
source/assets/historical inputs and exclusive real-user lease admission were
rechecked before launch. Initial registration observed 47,671,992,320
bytes free. Historical evidence remains unchanged. The exact earlier ENOSPC cause
is still unproved; a finite storage qualification is not a future capacity guarantee.

## Actual ordered development

| Candidate | Disposition |
|---|---|
| d=.25 m | Acquired after727 ticks; blocked first commitment, completed retreat/replan and goal at1267 controls; independently audited and selected |
| d=.20 m | Unattempted after first candidate selection |
| d=.15 m | Unattempted after first candidate selection |

Selected profile:
`7faba0a56d129ea051d5c28a019964034b546923dbe49cedb3a605af84437ec3`.
Acquisition loops remain radius1.4 m. Only the already-frozen nonpreferred detour
is at (.6, ±1.25). Authored preferred/nonpreferred route costs are
5.054335509/5.154335509 m. These are graph lengths, not measured rover path lengths.
Candidate selection does not authorize returning to smaller offsets after a
mandatory failure.

## Eight fresh prerequisites

Controls below count new recorded motor rows. Restore worker `total_ticks=732`
is the inherited727-tick episode counter plus five new controls; it is not732 new
restore actions. Prefix/restore goals are intentionally not required.

| Prerequisite | New control rows | Continuation ticks | Goal | Gate |
|---|---:|---:|---|---|
| south-no-event | 923 | 196 | yes | PASS |
| south-change | 1267 | 540 | yes | PASS |
| north-no-event | 922 | 195 | yes | PASS |
| north-change | 1292 | 565 | yes | PASS |
| south-prefix | 727 | 0 | n/a | PASS |
| north-prefix | 727 | 0 | n/a | PASS |
| restore-1 | 5 | 5 | n/a (five-tick check) | PAIR GATE FAIL |
| restore-2 | 5 | 5 | n/a (five-tick check) | PAIR GATE FAIL |

Both changed-route runs independently show blocked preferred-route inspection,
completed retreat and replanning before reaching the declared goal region.
No task or acquisition failure, unavailable cue or infrastructure stop occurred
in these nine native owners. Goal radius is .8 m; a goal label means geometric
termination inside that region, not arrival at its exact center.

[Independent readout](memory-travel-recovery-evidence/readout-completion.json)
rechecks all326 original indexed files and audits all nine owners/7,135 new controls.
Every exact recorded PID/starttime/PGID owner was confirmed exited by the readout
in the invocation's process namespace. The execution receipt saying
`finished-bounded-attempt` and CLI exit0 do not mean the prerequisite gate passed.

## Restore boundary: what matches and what fails

Both restore jobs bind the same freshly recorded south-prefix SNP and expected
invariant. Five actual ticks are727,728,729,730,731. Both individual raw auditors
pass and both `invariants_preserved` flags are true.

Common initial invariant:
`86fa2ebcee8305a1b39c779a9a52e7c844345142fdbc4fd19175584a695a8b78`.

Common non-timing trace digest:
`bf05e4fe707954ab3ed9e28cbf39137c778918279228cbabef2ed4272f76c9cf`.

| Restore | Post-state digest |
|---|---|
| restore-1 | `ab719cde4a3bf1adf5060399b929b3d99b705157ca72f8e679ee7e7e7e45da0d` |
| restore-2 | `bfa93f15923e04d1f0c7bd98a0ed462003b4aa98eabe67c35ddcfb5f3dd8d7c2` |

Supplementary retained-data verification compares every raw field across all five
rows. Only the excluded wall-time `latency` and `step_latency` measurements differ;
cameras, encoded inputs, neural raw outputs, motor actions, control, poses, sensors,
simulation time and remaining recorded fields match exactly. The retained workers'
complete `final_memory` and `world_state` dictionaries also match.
[Exact boundary receipt](memory-travel-recovery-evidence/restore-boundary.json).

The whole captured post-state payload and component fingerprints were not retained;
only its digest was published. Therefore the differing component is **unlocalized**.
Neither hidden/native/RNG divergence nor bookkeeping/normalization error is proved.
Identical observable traces do not authorize dropping the frozen post-state gate,
relaxing its normalization or calling deterministic restore qualified.

Read-only local reproduction, with retained raw outputs present:

```sh
env PYTHONPATH=.:src:scripts OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1 \
  /home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python \
  docs/reports/memory-travel-recovery-evidence/verify-restore-boundary.py
```

This verifier launches no policy/native owner and writes no original evidence.
Its offline120-second verification bound does not extend the historical study or
create a new qualification. [Actual verification](memory-travel-recovery-evidence/restore-verification.log).

## Budgets and scientific close

One CLI invocation, nine sequential CPU owners, zero automatic retries. Fixed
7,200 s global /2,300 development /4,300 prerequisites /600 readout caps remain.
[Scientific-close receipt](memory-travel-recovery-evidence/scientific-close.json)
reports **2963.91 s total** and
**309.49 s readout**, including the
supplementary restore-boundary readback and final immutable-file/source rechecks.
Deadlines were checked after closing receipt writes. At close, before those receipt
writes, raw outputs were 1,619,919,123 bytes and documentary files
4,619,116 bytes, comfortably within8 GiB including both receipts.
Publication accounting retains later documentary copy sizes separately.

Report editing, branch review and Git publication occur after scientific close;
they do not extend scientific clocks or introduce new experimental measurements.
Original historical recordings, receipts and pending drafts are preserved.

## Software verification and evidence limits

Nine independent-readout safety tests pass. They cover immutable hashes/path
escape, stale canonical receipts, started-but-unscored owners, audited task versus
resource stops, selection order/retreat proof, restore source binding and exact
five-tick trace/state equality. Missing implementation/gate methods were observed
failing before implementation; [RED logs](memory-travel-recovery-evidence/readout-red.log),
[gate RED log](memory-travel-recovery-evidence/gates-red.log),
[GREEN log](memory-travel-recovery-evidence/readout-tests.log).

The prior full software suite remains **915 passed /24 skipped**, bound to unchanged
scientific source; it was not rerun for this documentation/readout-only branch.
Skipped opt-in checks and unexecuted CI are not green qualifications.

[Final independent review](memory-travel-recovery-evidence/final-review.md) found
no blocking or important findings. All 88 compact copies were checked against
their indexed sizes/hashes and Git tracking; no raw NPZ/SNP payload is tracked.
[Publication integrity check](memory-travel-recovery-evidence/publication-check.json)
records checks made after scientific close, without adding native measurements.

Compact publication contains immutable inputs, metadata, supervision, worker and
readout receipts plus measured-path SVGs. Raw NPZ camera/control chunks and SNP
payloads remain local under `/home/utkarsh/Work/shraddha/brain/.worktrees/research-phase/runs/memory-travel-recovery-20261004T133718Z`.
Compact Git evidence is not a self-contained raw replay bundle. Full tick-zero
neural prefix replay remains unsupported; packet/M/commitment replay and policy
camera/output bindings are distinct from that unavailable proof.

Measured path figures show registered base obstacles/cues and audited rover poses;
they are not physical hardware evidence or a time-varying renderer of gate edits.

- [Development changed-route path](memory-travel-recovery-evidence/owners/measured-e6c52627ef324962a41645db358162f9.svg)
- [South changed-route path](memory-travel-recovery-evidence/owners/measured-d60e7d78cb1d4d04a4268f2528a6c534.svg)
- [North changed-route path](memory-travel-recovery-evidence/owners/measured-c0ac36d0bcf54c9e90f948fe28454e0f.svg)

## What this resolves and what is next

Earlier evidence showed the original acquisition failure, then successful radius1.4
acquisition/open travel but a changed-route CueUnavailable handoff, followed by an
incomplete ENOSPC travel attempt. This fresh registered study supplies completed
native evidence for the .25 m travel amendment on both route sides. It does not
retroactively qualify the ENOSPC recording or other historical missing cells.

The remaining memory bottleneck is the **whole post-state restore comparison**.
Next: prepare a separately registered diagnostic amendment retaining complete
post-step snapshots/component fingerprints for both five-tick restores. Compare
native bytes/integration, environment, policy/retina, RNG, observation and application
components under the existing declared recorder normalization. Localize the
mismatch before proposing a narrow fix; preserve this failed gate and raw evidence.
That diagnostic is not executed or authorized by this one-shot study.

Paired pilot remains unattempted; the contingent pilot draft is not published as
an execution contract because its prerequisite gate failed. R2 benefit, R3
navigation, learned puck capability, held-out, physical hardware, operator and
exhibition acceptance remain open. No fitting or reserved-data use occurred.

Repo-local author Aadrika Maurya <aadrikamaurya@gmail.com>; publication account
Aadrika08 verified without a global account switch. Stack on draft PR #68,
base `research/memory-travel-handoff`; main remains `ee6bf61ea8faec02d5522c7eee30ab7cf333f29d`. No merge or CI work.
