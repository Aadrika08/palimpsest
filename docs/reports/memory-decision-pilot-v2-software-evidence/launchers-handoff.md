# Selected pilot launcher/preparer software handoff

No real registration, native campaign, commit or push was performed by this lane.
Registration and the runtime control root remain absent.

`register.py` has a single public entry point: an ancestor hard KILL at 180 s
encloses byte-only admission, the registration write and its registration-only
Git commit. It holds the existing real-user writer lease read-only, without
creating prospective output/control roots. It checks the 8 GiB reservation,
2 GiB floor and 64 MiB headroom, then uses the existing three-root storage budget.
Existing registration/control/output, dirty software, resource refusal or an
expired preparation stops admission. Failed Git work retains the registration
and blocks reentry; no native work is started by preparation.

`execute-pilot.py` reuses the shared restore supervisor with the selected driver
facade. It requires independent `run`/`audit` exit codes and `pilot_complete`.
The inner foreground TERM/KILL watchdog is 6,590 s; the ancestor hard KILL is
6,600 s. The only shared source change adds `decision-pilot-v2` to the existing
campaign-mode tuple, preserving the original origin, foreground watchdog,
inherited process groups and direct PID signaling seams. Fresh control is
required before bounded/supervised admission. The pipeline uses the original
registered marker rather than requesting new time.

All checks used the lab-hardening Python, one numerical thread, EGL, CUDA
disabled, simulation opt-ins unset and `/tmp/palimpsest-software-tests.lock`.
The lifecycle checks launch only harmless sleepers and inspect exact PID,
starttime and PGID; they never import a model, decode old SNPs or run science.

- Initial red: 14 failed in 0.12 s; wrappers absent (`launchers-red.log`).
- First green attempt: 4 failed, 32 passed in 11.23 s; the completed preparer
  fixture omitted `protected_roots` (`launchers-first-green.log`). The fixture
  was corrected; deadline refusal expects the existing `TimeoutError`.
- Green: 39 passed in 16.26 s (`launchers-green.log`).
- Final selected plus legacy launcher checks: 42 passed in 16.23 s, exit 0
  (`launchers-final-green.log`), including registration commit failure/reentry,
  read-only lease, admission-clock origin and real harmless ancestor cleanup.

The whole-branch software suite and independent review remain integration work.
Account quota telemetry is unavailable; quota is unknown.
