# One fresh manual lab browser workflow

7 October 2026. Recheck the existing local lab workflow after the shared artifact
reader change in `c2dcd4b`, parent `1031c5a`. This is a finite software/simulator QA
phase under the simulation completion goal. It is separate from the stopped
artwork material pass and pending timer-aware restore study. No model inference,
scientific scoring, new research arm, held-out access or human acceptance.

Use a new worktree, unchanged pinned upstream `8d96459`, the existing Python 3.11
environment, Node 24.21.0, Chromium and cached UI dependencies matching the lock.
This tests cached setup, not a new dependency installation or model-asset fetch.
Freeze source/control/runtime identities before launch; keep one consumed marker.

Build the current UI once and run exactly the existing Playwright test
`actual local manual workflow, snapshots, sequential branches, comparison and export`
once, with retries disabled and one browser worker. It admits at most three
sequential manual CPU simulation owners, one source snapshot in addition to
automatic initial snapshots, and one SVG export. Preserve actual masks/pixels,
boundary edits, manual blur clearing, reload, two snapshot branches, provenance
comparison, recorded playback, authenticated SVG download and desktop/mobile
screenshots. Collect natural failures and stop; zero corrective attempts.

Aggregate phase bound 360 seconds: one 60-second build, 30-second readiness,
180-second browser-test bound, 20-second server shutdown and the remaining time
for integrity/cleanup/readback. A 330-second isolated-process-group supervisor
and outer TERM at 350 seconds plus five-second KILL grace cover owned descendants.
No timeout restart or additional test invocation. Pin the full launch commands.

Managed simulation/export roots: 128 MiB, three runs, two snapshots per run,
one export, 2 GiB continuing free floor and 1 MiB per worker log. Count all new
phase controls/logs/runs/exports/build/browser artifacts against 1 GiB; require
4 GiB initially. Existing cached dependencies/upstream checkout are declared
setup inputs. Reuse storage/log/process helpers; observations are not an atomic
filesystem quota. On any source, budget, deadline or cleanup error retain failure.

An independently audited pass requires three completed manual recordings, exact
published numeric/event integrity, clean owner/server/browser termination, source
pins unchanged, SVG source identity and coordinates, owner-close response, both
screenshots and bounded storage/elapsed time. Publish receipts and a reproducible
handoff. This short workflow does not requalify FLYNN, all task profiles, replay,
endurance, display-rate targets or the full simulation release.
