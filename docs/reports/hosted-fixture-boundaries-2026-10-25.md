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
