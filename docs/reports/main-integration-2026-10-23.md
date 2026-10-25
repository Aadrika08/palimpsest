# Main integration verification — 23 October 2026

Initial runtime source: `cfddb09`, artwork branch descending from remote main
`2814138`. The user authorized delivering completed work on main. Landing and
hosted CI status are recorded separately when confirmed.

## Checks and repairs

The canonical four-pass suite ran to completion. It was **not green**:

| Pass | Result |
| --- | --- |
| Ordinary source tests | 6038 passed, 5 failed, 304 skipped; 1158.91 s |
| Isolated process checks | 7 passed; 8.97 s |
| Runs-directory fixtures | 5 failed; 10.74 s |
| Tmpfs fixtures | 29 passed, 2 failed; 21.64 s |

Runtime source/tests stayed fixed during that run. Concurrent documentation
updates broke a heading anchor, and unrelated temporary-directory activity may
have interfered with ancestor custody checks. The original log is retained.

All twelve failing cases were subsequently checked:

- Two process-supervision fixtures used the removed historical Python path.
  They now use the running interpreter for their synthetic child commands;
  the frozen production invocation is unchanged.
- The shared authored CPU fixture copied a historical loader-cache pin.
  `/etc/ld.so.cache` changed on the host. The fixture now binds current cache
  bytes in its own copied descriptor. Production admission and historical
  evidence remain untouched. All five amendment/audit cases pass in 51.21 s.
- Four optional-import/native cases pass serially (one plus three cases).
  Concurrent ancestor-directory mutation is a likely cause of their earlier
  fail-closed result, not independently proven. No custody checks were weakened.
- The original heading anchor was restored. The combined artwork, process and
  documentation-link recheck passes: 36 passed, 3 historical skips, 1.10 s.

These reruns resolve the observed failures; they are not a second wholly green
full-suite run. [Retained logs](main-integration-2026-10-23/tests.log) and the
neighboring targeted/fixture logs preserve both outcomes.

## Browser and frontend

Production UI build passed. All 15 measurement checks and the memory annotation
checks passed. The five artwork browser tests passed in 2.6 minutes, including
actual 120-second composed Choir playback. The new static introduction also
passed [direct local-file checks](guided-encounter-2026-10-23.md), with no new
recording or changes to artwork bytes.

## Hosted configuration

The preceding hosted run `39623848094` passed frontend but failed fixture
collection on `ModuleNotFoundError: verify_artwork_handoff`. The workflow now
uses the documented canonical runner/import paths, fetches full history for
frozen-source validation, uses `/dev/shm` for required tmpfs fixtures and allows
40 minutes for the four passes. Its resulting hosted status is not yet known.

All successful fixture, source and browser checks remain distinct from research
capability, human listening/viewing and independent operator acceptance.

## Landing state

All thirteen previously local artwork commits are pushed through `cfddb09`.
[PR #184](https://github.com/Aadrika08/palimpsest/pull/184) is draft with that
remote head. GitHub rejected the newer `e4ce6aa` push because the repository
owner's OAuth credential lacks workflow-write scope for `checks.yml`. The other
configured account has no push permission. The missing access was requested;
main remains `2814138` and no merge or force-push occurred.

Hosted run [39989172177](https://github.com/Aadrika08/palimpsest/actions/runs/39989172177)
passed frontend and failed old-workflow collection on `afterimage_material`,
`verify_artwork_handoff` and `record_choir_material`. The local canonical-runner
fix includes those script import paths. It has not yet run on the hosted runner.

The next local source commit, `29b438e`, adds the
[retained-condition reader and current-source profile](memory-retained-condition-v1-2026-10-23.md).
Its scoped checks pass: 482 affected Btrfs tests, 56 new tmpfs tests and 19
historical-pin/link tests. This restores the relevant memory tests against the
integrated source while preserving old profiles. It is additional local evidence,
not a rerun of the whole suite or a hosted CI result. A fresh remote check still
finds main at `2814138` and the feature branch at `cfddb09`; workflow access is
still pending.
