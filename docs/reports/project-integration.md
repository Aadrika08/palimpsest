# Combined checkout verification

The integrated checkout at `0a783af` combines the completed lab/memory mechanics,
recorded memory acquisition, exploration/homing, MaleCNS training/wrapper,
sonification/comparison and rover proposal branches. It does not include the
pending male lab integration or recorded transfer verifier.

An EGL-enabled full suite ran 319 tests in 66.660 seconds: **316 passed and three
explicit MaleCNS asset/opt-in checks skipped**. The supervised child exited 0 in
70.240 seconds under a 240-second bound. Runtime and test hashes stayed unchanged.
The one-off outer reporting script exited 1 because it read `exit_code` instead
of the existing supervisor's `returncode` field. This reporting error and the
unaltered log/report/script are retained; the suite was not rerun.

Cached offline npm installation, production build, seven UI measurement checks
and memory annotation checks passed in this checkout. These are build/fixture
results, not a new browser endurance or full-model navigation claim.

The [evidence index](project-integration.json) preserves logs, bounds, skipped
coverage and hashes. Each historical actual model/task report still names its
original source. Unified qualification and remaining M5–M10 gates remain open.
