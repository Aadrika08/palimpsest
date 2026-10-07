# Corrected prospective manual lab refresh v2

7 October 2026. Owner allocated one fresh phase after the v1 selector failure.
Preparation only: no selection preflight, build, server, browser, simulation owner
or export has run. Preserve `manual-lab-refresh-v1` and its consumed marker/failure.
This phase starts from `40f4597`, including artifact event-identity and recorded
snapshot recovery fixes. No production UI or workflow test changes are permitted.

Run precisely the existing `ui/tests/lab.spec.ts:21`, titled `actual local manual
workflow, snapshots, sequential branches, comparison and export`. Its unchanged
workflow covers manual CPU source, masked pixels, edits, blur clearing, reload,
one explicit snapshot, two sequential branches, comparison, playback, one SVG,
desktop/mobile screenshots and the final owner-close attachment. It supplies no
FLYNN/task-profile/replay/endurance qualification or human/artwork acceptance.

Use the corrected title suffix grep without v1's leading `^`. Exactly one
metadata-only Playwright `--list --reporter=json` preflight must return that title,
`lab.spec.ts`, line 21, with exactly one project/test and no reporter errors.
Reject any other selection before build/server/native allocation. This consumes
one preflight; there is no second preflight or workflow invocation on failure.

`scripts/manual_lab_refresh_v2.py` reuses the v1 producer's `bounded_process`,
endurance descendant sampling, storage/log controls, recording/SVG audit and
cleanup. `--register` only reads source/runtime/dependency metadata and freezes
`docs/plans/manual-lab-refresh-v2-registration.json`. Review and commit these
controls and registration before executing its registered outer argv from this
worktree, with the existing Python 3.11 lab-hardening environment and
`PYTHONPATH=src:scripts`. The parent source/control pins are rechecked before
selection and after the workflow. No new dependency, model or asset installation.
The pinned upstream 8d964599 checkout is populated from the existing local copy;
cached UI dependencies are symlinked from lab-hardening. Cached metadata pins
are not a rehash of every installed package file or a fresh-installation test.

One 360-second aggregate covers admission, selection, build, readiness, workflow,
shutdown, integrity readback and publication. Stage ceilings: preflight 30 seconds,
build 60, readiness 30, browser 180, server shutdown 20. The worker additionally
stops at 320 seconds and its process-group supervisor at 330; stages cannot each
spend their maximum and exceed that aggregate. Entire launch plus publication is
inside the registered outer `timeout`: TERM at 350 seconds, KILL grace 5 seconds.
Publication must finish by 345 seconds; no restarted readout/publication clock.
Retain actual worker/parent elapsed times and terminal status without calling
them universal process-return guarantees.

One fresh `.superpowers/sdd/manual-lab-refresh-v2/launched.json` consumed marker;
new phase runs/exports under that directory. Publication root is
`docs/reports/manual-lab-refresh-v2-evidence/`. Output/marker/publication reuse is
refused. At most three sequential manual owners, two snapshots per run, one SVG
export, one workflow invocation, zero corrective attempts. Sample at most 128
PID/start-time identities; any observed live survivor needing forced cleanup
fails the phase. Sampling cannot prove absence of unobserved transient processes.

Count phase controls/logs/runs/exports, `ui/dist`, `ui/test-results`, and publication
copies together against 1 GiB. Managed run/export limit remains 128 MiB, continuing
2 GiB free floor, 4 GiB initial free requirement, 1 MiB logs. No added enclosing
writer lease can block the lab's existing storage ownership. Source/runtime,
deadline, log/storage and cleanup violations stop and retain failure. Storage
observations are not an atomic filesystem quota.

Driver pass requires exactly three integrity-checked manual recordings, source
pins unchanged, one SVG whose run/coordinates match the recording, both
screenshots, clean owner-close response and server shutdown, no observed live
survivors, and counted time/storage bounds. Publication is bounded and copied
bytes are checked. Root independently reviews retained evidence before claiming
this narrow manual-workflow gate; `qualification_claims` remains empty. No CI,
scientific scoring, inference, held-out access, new research arms, hardware,
automatic merge or broader simulation-release completion follows from this phase.
