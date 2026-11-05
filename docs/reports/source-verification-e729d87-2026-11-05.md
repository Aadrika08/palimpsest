# Full local source verification at e729d87

The four-pass canonical runner completed with **6,530 passed, 305 skipped and 41 failed**. This candidate is not green and is not delivered on main. The exact tested commit was `e729d8772851a500ab9ce9077b0db57fc4b12a27`.

| Pass | Passed | Failed | Skipped | Seconds |
| --- | ---: | ---: | ---: | ---: |
| Ordinary source fixtures | 6487 | 41 | 305 | 1581.21 |
| Isolated process fixtures | 7 | 0 | 0 | 9.82 |
| Persistent runs-basetemp fixtures | 5 | 0 | 0 | 59.18 |
| Tmpfs-basetemp fixtures | 31 | 0 | 0 | 23.72 |

The runner used the existing exact Python 3.11.15 venv, disabled optional research/runtime opt-ins, retained its canonical clean environment and used a private 4 GiB `/tmp` tmpfs in a bubblewrap mount namespace. `/dev` was separately device-bound. The first wrapper attempt lacked that device binding and failed before pytest could initialize; its log is retained. Neither invocation changed the host `/tmp` mount.

Raw logs remain at `runs/full-source-e729d87-20261105.log` and `runs/full-source-e729d87-20261105-device-corrected.log`. Ordinary authored fixture scratch followed the existing runner's temporary-directory lifecycle; no research recording or historical evidence was removed.

## Diagnosed failures and current repair scope

- One compact-protocol test asserts that a historical profile equals the newly selected publication successor. It is being explicitly classified under the existing historical-pin policy; active current-profile coverage remains separate.
- Twelve Memory amendment negatives and one command-construction test fail in fixture setup, before their assertions, because the live source tree contains ignored bytecode. The old freeze also names another absolute worktree, so merely avoiding caches would make those negatives pass on an unrelated root rejection. New authored immutable-prior fixtures first pass the real metadata validator, then check each intended error. Command construction is tested independently of repository admission. No production validator, historical freeze or trust anchor is changed.
- Twenty-five Puck metadata cases also fail before their assertions at the correct bytecode refusal. They remain current tests. Their repaired fixture uses an authored source namespace and copied public index/historical-source bytes, with a positive validation baseline before every negative and two additional bytecode-refusal cases. Actual model/runtime inputs are not opened. Independent metadata verification passed 27 cases.
- The ancestor-hard-timeout test observes exact owned identities immediately after GNU timeout exits. A separate diagnostic captured matching processes with pending SIGKILL; both disappeared 1.4566 ms later without another signal. A bounded identity-aware exit observation is being checked while preserving the original 5-second hard kill, 12-second outer guard and strict final no-survivor assertion.
- The 600-interval authored Puck closure fixture encountered ancestor metadata churn above its held input root. A controlled unrelated sibling write reproduces the same refusal while protected files and root identities remain unchanged. Independent review confirmed that the existing public policy deliberately rejects this churn. The proposed scope relaxation was withdrawn and retained only as an unapproved draft. Production custody source, its tests and the old unchanged-policy assertion remain byte-identical to `e729d87`. The original 600-interval fixture passes once in36.76seconds on a dedicated outside-repository basetemp, with sibling writers serialized. Future full verification uses that dedicated ancestry instead of shared `~/.cache`.

Root verification of the integrated metadata-only repair passes **47 cases with 13 explicitly historical skips**. A subsequent combined affected run passes **90 cases with16 historical skips** in10.98seconds, covering all Puck original-bundle tests, the new Memory authored guards, amendment helpers, selected-pilot launcher and current publication-profile checks. The final repair changes tests and prospective source bindings; production validators and cleanup behavior are unchanged. No existing ignored bytecode has been deleted, and actual-study admission continues to require a clean qualified source installation. A complete canonical rerun is still required before a green-candidate claim.

## Frontend and profile checks

The locked frontend installation completed from the local npm cache. The initial shell selected Node 25 and emitted the declared engine warning; installation was repeated under the exact pinned **Node 24.21.0**. That runtime passes TypeScript/Vite production build, all 15 measurement checks and memory-annotation checks. These are software checks, not browser, human, fresh-machine or research acceptance.

The three prospective Memory publication profiles were refreshed after the reviewed test-policy repair. Structural comparison shows only the bound `tests/frozen_pins.py` descriptor size/hash and dependent base/condition hash links changed. Historical protocol bytes, scientific contracts, claims and empty actual qualification/execution anchors remain unchanged. New profile SHA-256 values are base `84ab31e256880723a08ffda265898d560f1b130b498630086c315196321b3285`, condition `21fa62bd861afb6ddd1ce0f8f1d1ab590198af27459bb27c91d7ca07114de22d` and publication `a8ab8e4684dbcf8d3dc3f95cc64b3ad121b5034f67c811a71395938ea7537db3`.

No hosted CI was triggered during the failed baseline or repair. The user subsequently confirmed approximately3,000 included GitHub Actions minutes and authorized careful use. The plan is to complete local verification before one reviewed hosted validation wave, avoiding intermediate pushes and cancelling duplicate push/PR event runs. Billing usage remains user-reported because the API credentials cannot read that endpoint. This local run does not substitute for exact-head hosted checks or main integration.
