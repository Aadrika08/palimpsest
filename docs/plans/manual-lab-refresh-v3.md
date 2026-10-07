# Manual Browser Admission and Cleanup Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans task by task. This is a
> approved preparation and one later finite manual QA allocation. Root reviews and
> commits these controls before execution; preparation does not consume the phase.

**Goal:** Complete the existing actual manual workflow with adequate managed
storage and honest bounded cleanup, preserving both consumed failures.

**Architecture:** Reuse the v2 producer, unchanged UI/workflow and recording
admission. Bind a new allocation/registration and test its resource arithmetic.
Add bounded natural-exit observation for exact descendant identities before any
forced cleanup; forced cleanup still fails the phase. No production UI change or
private multiprocessing shutdown API is justified by the retained evidence.

**Tech Stack:** Python stdlib, existing storage/process helpers, existing pinned
Playwright/Chromium and cached UI dependencies.

**Spec:** [v2 protocol](manual-lab-refresh-v2.md) and
[actual failure](../reports/manual-lab-refresh-v2.md), source `78e9dd5`.

## Global constraints and review focus

Keep the test at `ui/tests/lab.spec.ts:21` unchanged, including Step readiness,
three sequential manual owners, snapshots, comparison, one SVG and screenshots.
Keep the corrected one-test metadata preflight, 360-second aggregate, worker 320,
supervisor 330, publication deadline 345, outer TERM350/KILL5, 1 GiB aggregate,
2 GiB continuing/4 GiB initial free floor and 1 MiB stream caps. No corrective
attempt, research model, asset recollection, CI, merge or hardware belongs here.

Explicitly guard: inadequate owner reservation; stale/reused process identity;
a descendant that exits naturally after its parent; one that survives the grace;
interruption/publication after provisional pass. All mandatory failures remain
failures. Never merely enable Step on a failed runtime or raise a scientific gate.

## Task 1: source-only preparation and software proof

**Files:** new `scripts/manual_lab_refresh_v3.py`,
`tests/test_manual_lab_refresh_v3.py`, and
`docs/plans/manual-lab-refresh-v3-registration.json`; reuse
`scripts/manual_lab_refresh_v2.py`, `verify_afterimage.py`, `verify_endurance.py`
and `palimpsest.storage`. Keep v1/v2 worktree bytes and their controls unchanged.

- [x] Reproduce the storage refusal with a tiny engine stub carrying camera
  arrays and `StorageBudget`; call existing `worker._episode_preflight` without
  physics, owners or snapshots. Verify its real reservation uses 121,470,976
  bytes for the recorded camera regime and reproduces the original sum:

```python
used, reserve, headroom = 8_354_907, 121_470_976, 10_485_760
assert used + reserve + headroom == 140_311_643
assert used + reserve + headroom > 128 * 1024**2
assert used + reserve + headroom < 256 * 1024**2
```

  The arithmetic alone is a check of the retained receipt. The runnable test must
  also exercise the actual existing reservation function/budget with synthetic
  camera data and temporary files, so a changed camera estimate cannot silently
  invalidate the proposed configuration.
- [x] Bind proposed managed runs/exports storage to **256 MiB**; keep the total
  phase/controls/build/test/publication ceiling **1 GiB** and every admission and
  actual-write refusal unchanged. Three owners are sequential; aggregate counts
  include all previous recordings/snapshots rather than resetting on branches.
  Check failed admission still refuses a deliberately over-budget fixture.
- [x] Reproduce descendant cleanup using software processes only: one naturally
  exits shortly after its parent; one stays live; one PID observation has a
  different starttime. Add at most **two seconds** of natural-exit observation
  within the existing worker/outer deadline, checking exact PID/starttime/group.
  A live matching survivor at the end is killed and the phase fails as before.
  A reused PID is neither killed nor called the old process. Record grace elapsed
  and outcomes; interruption cannot silently promote a pass.
- [x] Investigate the retained resource-tracker outcome against this fixture and
  the normal lab shutdown code. If references/IPC persist beyond the bounded
  grace, diagnose and fix the proven lifecycle cause with a focused check before
  registration. Do not assume that adding a delay fixes the real tracker, call
  private `_stop` methods or exclude tracker processes from cleanup requirements.
- [x] Keep the producer small by reusing v2 supervision/publication helpers.
  Freeze every reused implementation and new wrapper/test/plan hash; ensure child
  argv enters the same newly bound allocation. Test final publication refusal,
  late close and TERM, then root reviews the source and commits the verified controls.
  Run focused software tests; report actual red/green outcomes. These are not a
  new browser gate or resource-tracker qualification.

## Task 2: separately approved fresh browser allocation

- [ ] After software review, freeze absent v3 phase/control/publication paths and
  an exclusive `launched.json` marker; bind exact source commit, runtime,
  dependencies, corrected selection, build/server/browser/outer argv and caps.
  Present the committed controls for review before consuming this allocation.
- [ ] Once expressly approved, run **one** metadata selection and **one** existing
  workflow, with at most three owners, two snapshots/run and one SVG export;
  **zero corrective attempts**. Serialize against other writer/native phases.
- [ ] Require all recording/source/actual SVG coordinate checks, desktop/mobile
  screenshots, owner close `closed`, graceful server shutdown, exact descendant
  exit, released ownership and timely independent terminal publication. A grace
  permits natural exit only; any forced cleanup still fails. On failure, stop,
  preserve every partial file and marker, and keep qualification claims empty.

## Prepared mechanism and limits

The v3 wrapper binds the v2 finite producer to fresh v3 paths, schema and worker
argv. A default-disabled callback in the shared v2 helper permits one collective
natural-exit observation window, at most two seconds and capped by the existing
worker deadline. It checks PID, start ticks and process group; changed identities
are untouched. Matching live survivors retain the existing kill-and-fail rule.
Source pins explicitly include the shared helper, wrapper, both software tests,
v3 plan, runtime, UI, installed dependency metadata and tracked upstream assets.

A harmless software fixture used the public multiprocessing spawn Event and
observed the tracker's pipe descriptors. It deliberately inherited the writer
into a short-lived sleeper: the tracker remained alive after its parent exited,
then exited naturally after the last writer closed. This characterizes CPython's
EOF mechanism. It does not prove which writer delayed the consumed v2 tracker,
or qualify two seconds as sufficient for every actual browser shutdown. Real
matching survivors after that window still fail. No private tracker shutdown API
or special exemption is introduced.

Development red/green logs are under ignored
`.superpowers/sdd/manual-lab-refresh-v3-development/`, outside the absent finite
phase. Only tiny software fixtures and harmless Python processes ran. The
metadata-only registration is prospective; root commits and reviews source before
invoking its frozen outer command once. No selection/build/browser/native phase
ran during preparation.

This preparation supplies no new UI acceptance, scientific, human or simulation
release claim. Actual manual QA remains unexecuted; consumed v1/v2 phases are
never rerun.
