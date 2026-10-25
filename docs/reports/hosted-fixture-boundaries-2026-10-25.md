# Hosted fixture boundary repair — 25 October 2026

Candidate `510a750f7dc542564b1f8962c2388c914e81ee8c` resolves most of the
[first hosted environment failures](hosted-fixtures-2026-10-25.md). Both frontend
jobs pass. The complete fixture runs still fail:

| Event / run | Ordinary | Process-isolated | Persistent runs | Tmpfs |
| --- | --- | --- | --- | --- |
| [PR / 40197843867](https://github.com/Aadrika08/palimpsest/actions/runs/40197843867) | 6,338 passed, 25 failed, 88 skipped | 7 passed | 5 failed | 31 passed |
| [Push / 40197840061](https://github.com/Aadrika08/palimpsest/actions/runs/40197840061) | 6,337 passed, 26 failed, 88 skipped | 7 passed | 5 failed | 31 passed |

The [index](hosted-fixture-boundaries-2026-10-25/checks.json) binds both original
failure logs, their compressed copies, the changed source and the local check.
The earlier report and its indexed artifacts are preserved at their source
commit; its workflow hash describes that earlier candidate.

## Environment diagnosis and repair

Git reports dubious ownership at `/__w/palimpsest/palimpsest`: the checkout
belongs to the host user while the container runs tests as root, and the canonical
runner deliberately clears inherited Git configuration. This affects historical
pins, source enumeration and study fixtures. Root also bypasses the permission
denial required by the storage inventory test. CI now gives a dedicated ordinary
user ownership of this disposable checkout and interpreter prefix, and runs the
suite as that user. Git's ownership checks remain enabled.

Real namespace tests report `bwrap: Can't mount proc on /proc: Operation not
permitted`. Docker's masked/read-only system paths prevent the nested mount.
The job adds `systempaths=unconfined`, whose scope is described in the
[Docker reference](https://docs.docker.com/reference/cli/docker/container/run/#optional-security-options---security-opt).
The namespace and custody assertions remain unchanged. Arch's separate system
Python supplies `/usr/bin/python` for the deliberate wrong-interpreter rejection
test; actual fixture execution still uses the hash-checked CPython 3.11.15.

Before the complete suite, CI now checks Git and a real nested namespace under
the test user, then runs representative prior failures and one authored CPU
preparation test. A failure stops before the long fixture pass. This local
session cannot access the Docker daemon, so the next hosted run must establish
that the changed container admission works.

## Fixture corrections and local verification

- The rollback fixture creates a replacement while the original exists and
  proves their inode identities differ before replacing it. Immediate unlink
  and recreation had allowed legitimate inode reuse.
- The expired allocation fixture uses a controlled positive monotonic clock.
  A newly booted host can have less uptime than the 6,001-second expired offset.
- The escaped-child fixture records its exact identity before allocating the
  memory stimulus; the RSS guard could previously stop it before that write.
- The process-group watchdog test waits within a finite startup budget for the
  child identity before arming its short watchdog. The failed hosted runs stop
  at missing child readiness; they do not themselves prove a group-kill failure
  or the precise bootstrap cause. Readiness failures now include supervisor
  disposition and owner exit code. Production timeout defaults are unchanged.

The canonical selected runner passes **27 tests in 23.67 seconds, exit 0**:
all bounded-descendant tests, the two corrected memory tests and the complete
lab supervision class. It reports one existing Starlette/httpx deprecation
warning. The [retained log](hosted-fixture-boundaries-2026-10-25/local-boundaries.log)
records this check. Workflow YAML, all ten shell steps and the four modified
Python test files parse. Independent diff review finds no material issue;
hosted ownership and namespace behavior remain unverified until CI completes.

No production runtime, historical evidence, protocol pins or acceptance
assertions are relaxed. No scientific allocation or human acceptance ran.
Main remains `2814138`; the repaired candidate must pass before PR #184 lands.

## Follow-up: descriptor limits and process exit observation

Candidate `3739b3add54d881fece748d7c7590c9eff120240` passes the hosted namespace,
ownership and selected-fixture preflight, plus frontend. Its complete
[PR run / 40201506157](https://github.com/Aadrika08/palimpsest/actions/runs/40201506157)
reports 6,394 passes, 12 failures and 88 skips:

| Pass | Passed | Failed | Skipped | Seconds |
| --- | ---: | ---: | ---: | ---: |
| Ordinary | 6,354 | 9 | 88 | 1,651.18 |
| Process-isolated | 7 | 0 | 0 | 8.65 |
| Persistent runs | 2 | 3 | 0 | 51.50 |
| Tmpfs | 31 | 0 | 0 | 23.83 |

The [push run / 40201501954](https://github.com/Aadrika08/palimpsest/actions/runs/40201501954)
repeats the same twelve failures and all four pass counts. Its ordinary,
isolated, persistent and tmpfs passes take 2,075.17, 11.39, 63.22 and 30.22
seconds respectively. Both complete failure logs are retained in the follow-up index.

Eight ordinary failures reject a descriptor limit below the unchanged 40,000
floor. Three independent CPU audits exhaust their descriptors. The
[runuser implementation](https://github.com/util-linux/util-linux/blob/master/login-utils/su-common.c)
resets the soft limit to `FD_SETSIZE` (1,024); a local invocation at that limit reproduces the exact
held-runtime rejection. The workflow now declares a 65,536 container ceiling,
restores the soft limit after changing users, and records/asserts both limits.
All 15 held-runtime tests pass with the restored limit, in 7.67 seconds. All five
authored CPU tests pass at exactly 65,536 soft/hard limits in 49.90 seconds.
The hosted preflight now includes an independent CPU audit, not only its producer.

The remaining ordinary failure is a permission denial while observing an exited
tracker's `/proc/<pid>/fd`. The log does not capture its state at denial. Three
bounded local process probes cannot reproduce that kernel-specific denial, so
the original hosted cause remains qualified. The reader nevertheless attempted
resource enumeration for known zombies, preventing its caller from observing
their terminal state. A prospective correction returns their identity and
terminal resource row directly. A permission race is accepted only after a fresh
stat proves the same start-time/group identity is now a zombie. Inaccessible live
processes and changed identities still raise; diagnostics now retain both
identity observations. Missing processes retain the existing behavior.

Four regressions use real bounded children with narrow permission/race injection.
Before the correction, three fail and the PID-reuse safety control passes; after
it, the two complete verification-script/manual-refresh files pass 17 tests in
2.37 seconds, exit 0. Historical manual-refresh registrations and evidence remain
unchanged; this is not retrospective qualification. The next hosted preflight
includes the original tracker case and all four new regressions.

The [follow-up index](hosted-fixture-boundaries-2026-10-25/admission-checks.json)
binds the original failed log, RED/GREEN results and changed source. The original
index above still describes the earlier repair at `3739b3a`; it is not rewritten
to claim new source bytes. Review found no material issue. Full hosted verification
and main landing remain open.
