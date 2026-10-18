# Natural episode to durable recording close

Continue the full simulation release goal from PR #130 (`b559699`). Corrected
source is `f93aa9668748b54f89d9bb9bdd0f07ba8f2a9e21`. The existing interval writer
previously admitted committed prefixes but had no owner/stage terminal. This unit
connects the held native interval loop to a natural episode recording close and
reduces exactly twelve closed recordings. All seven release gates remain open.

These are recording/data closes, not native or process owner acceptance. The fixed
fresh-worker entry still performs preflight only; complete parent/worker dispatch,
actual runtime qualification and integrated execution admission remain required.
No original model, real inventory/catalog/retained scan or scientific study ran.

## Implemented path and invariants

`puck_collection_close.run_collection_episode(...)` requires held execution, one
fresh initialized task/environment/writer and exact admitted scene pose/puck/goal/
velocity before action. It uses the existing `execution.native_interval` for one
natural episode, without reset, retry, perturbation, takeover or fallback, ending
at the existing task reason or 600 intervals. The held context now claims the
complete episode once. Completion stops its writer and refuses subsequent
native intervals, labels/predictions or another episode while leaving final
parameter/source checks available for cleanup. Failures poison execution/writer.

The source still exposes its older interval component for independent component
consumers; the new complete episode route owns the one-shot lifecycle. The legacy
`owner(config)` v3 denial remains. No actual CLI gains a native collection grant.

`close_owner_recording(...)` streams the actual strict committed rows, then
revalidates them before admission. It rejects empty/unfinished recordings, pending
tails/gaps, inconsistent initial task/layout, state/world/contact discontinuity,
continuation after a natural terminal and unexpected entries at every recording
level. Exact interval commitment hashes, counts, final task/cursor and motivating
condition counts bind the close. Recording bytes include all committed named files
and both commitment links; hidden extra files cannot evade the 149 MiB limit.
The recording must be the owner's own `intervals` directory. Maximum remains
600 rows and one MiB close metadata, enforced before publisher/reader copies.

The publisher reuses the existing identity-bound, fsync/commit/admission-link
transaction for two separately typed target names. A final live guard executes
inside the transaction immediately before admission; guard failure leaves no
admitted terminal. Reservation and scene-manifest behavior/caps remain unchanged.
Readers bind terminal publication identities and reread the actual row chain;
a previously closed dataset changed afterward is not accepted as the old close.
This is windowed observation on a trusted host, not atomic multi-object filesystem
proof or a sandbox against arbitrary admitted code.

`close_collection_recordings(...)` requires all twelve fixed scene-major owners
(6110–6113, seeds 21–23), matching execution/reservation bindings, the same scene
for its three collectors and no scene identity aliases. It rereads every owner
and all its rows. Every model must have at least one motivating BEFORE-approach,
contact/ready/non-arrival row under the unchanged float32 sensor predicates.
All owners/rows remain. Missing coverage produces a durable `coverage_failed`
record; it cannot crop, extend, replace or retry collection. Positive coverage
produces `recordings_complete`, still with all execution/fitting authority false.

Both schemas retain `native_authorized`, `collection_authorized`,
`fitting_authorized`, `executable` as false and qualification claims empty.
A terminal cannot establish source/runtime closure, actual scene/model provenance,
process identity/exit/drain, parent lease/storage/clock acceptance or training GO.
The seven-role 80 MiB input ceiling and existing scientific/capability gates remain.

## Measured verification and retained failures

- `16dca64`: five missing-API failures. Twenty imported fixture checks were
  accidentally collected; module-qualified fixture access removed duplication.
  The expanded intended suite then produced eleven missing-API failures, 0.23s.
- Authored CPU-model/native fixture initially patched a different module alias;
  correction preceded the intended wrong-initial RED. That RED showed a native
  action before refusal. Initial task/layout admission now precedes action.
- Namespace alias, changed collector scene, duplicate scene identity and reader
  copy-limit REDs were reproduced/fixed. Full twelve-owner temporary batches
  exercise positive coverage, all-zero coverage and exactly one uncovered model;
  the latter two retain every owner/row and deny fitting.
- `1197667`: 20 focused pass, 6.55s; 1390 affected pass, six inherited exclusions,
  84.03s. Whole-branch review found three Important defects: reused episodes,
  hidden recording files and publisher rereads at 64 MiB. All three reproduced
  intended RED in 1.91s and were fixed in one pass. The hidden-file test uses a
  sparse 150 MiB extra file, which now refuses before admission.
- The one-shot fix also blocks staged labels/predictions after completion. Its
  first test capture was incomplete and was not credited as the intended RED;
  corrected complete fixture capture reproduced the actual extra label/prediction
  before that guard's fix was credited. Targeted fixed regression checks pass.
- The maximum-duration authored fixture reached publication under its old small
  fixture deadline but correctly refused final admission at 30 seconds: one
  failure, 32.61s. No production limit was changed. The maximum fixture now
  constructs custody under the existing 180-second owner allocation. It completes
  exactly 600 intervals and closes the unchanged `time_limit` outcome; the
  24-case suite at that point passed in 46.98s. A final staged-query case brings
  the suite to 25. These are fixture timings, not physical/runtime timing bounds.

Final source `f93aa96`:

| Verification | Root | Independent serialized repetition |
| --- | --- | --- |
| 25 collection-close cases | Included in final affected run | 25 passed, 47.77s |
| 29 affected files | 1395 passed, six deselected, 125.72s | 1395 passed, six deselected, 125.66s |

Both final affected commands and independent focused command exited 0. This is
one initial source review plus author regression fixes and independent test
repetition, not an independently reviewed exact final execution/runtime GO.
Root's two affected logs remain locally at
`runs/source-validation/puck-v3-collection-close/` (ignored test artifacts).
`git diff --check` passes.

Commands use the unchanged R0 interpreter/environment:

```bash
env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:.:tests \
  /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python \
  -m pytest -q tests/test_puck_collection_close.py --tb=short
```

Affected command: the exact 25-file command in the
[inventory-scope report](puck-v3-inventory-scope-source.md), plus
`test_puck_worker_bootstrap.py`, `test_puck_dependency_files.py`,
`test_puck_worker_dependencies.py`, `test_puck_collection_close.py`; unchanged
six mechanics construction-pin/missing-httpx exclusions. Default pytest still
stops collecting `tests/test_lab.py` because FastAPI is missing in this interpreter:
one collection error, 0.30s. No repository-wide pass is claimed.

## Remaining complete launcher and release goal

Ruling: implement this missing recording-close source seam before actual runtime
qualification, which remains a prerequisite for actual collection. It can be
built on authored inputs without consuming any original/study attempt. Final
runtime/parent integration may require adaptation; this unit changes no gate.

Ruling: full data revalidation remains the source reference close behavior. Its
cost has not been qualified against the fixed parent reduction/publication/return
buckets. Measure the complete integrated path and, if needed, review a
custody-preserving optimization. No time borrowing or cap increase is granted.

Next bind the active held inventory and durable reservation/scene publications to
one parent seal and its four-scene child projection; measure/qualify the exact
supported numerical dependency/runtime configuration; dispatch this episode path
through the fixed authenticated worker under a distinct complete admission;
connect exact environment, independent identity/progress/escaped-descendant drain,
parent writer lease, sampled resources/storage and all clock ledgers. Promote
recording closes to owner/stage acceptance only after those separately verified
contracts. Complete memory replay-to-case-close source work in parallel where
independent. Actual memory amendment02, catalog access and navigation decisions
remain pending. No consumed attempt was retried. All seven release gates stay
open; CI/rover stay excluded and all six artworks remain in simulation first.
