# Hosted fixture environment repair — 25 October 2026

Workflow access is resolved. All completed commits through `f3645c2` were pushed
to [PR #184](https://github.com/Aadrika08/palimpsest/pull/184), which is ready for
review. Main remains `2814138` pending a passing hosted candidate and merge.

The first [hosted PR run](https://github.com/Aadrika08/palimpsest/actions/runs/40191242222)
passes frontend checks and fails fixtures. The four canonical passes report:

| Pass | Passed | Failed | Skipped | Seconds |
| --- | ---: | ---: | ---: | ---: |
| Ordinary | 5,890 | 473 | 88 | 1,082.30 |
| Process-isolated | 7 | 0 | 0 | 9.42 |
| Persistent runs | 0 | 5 | 0 | 10.15 |
| Tmpfs | 24 | 7 | 0 | 15.20 |

The [compressed original log](hosted-fixtures-2026-10-25/first-hosted-failure.log.gz)
retains all failures. The [index](hosted-fixtures-2026-10-25/checks.json) records
its compressed and original hashes, the local repair check and changed source
hashes. These 485 failures do not supersede the earlier passing local suite;
they expose a different, incomplete hosted environment.

The workflow selected CPython 3.11.17, while fresh-worker tests require the exact
3.11.15 executable. Other traces identify an absent pinned interpreter path,
the incompatible system-library layout, missing torchvision and UI dependencies,
an unavailable EGL loader, and mismatched campaign runtime metadata. Process
inspection and ancestor-timeout cases also fail; their result must be checked
again after environment admission, without treating missing or inaccessible
process information as proof of cleanup.

## Repair and verification

CI now declares a digest-pinned Arch Linux container, the fixture suite's library
layout, executable tmpfs, namespace/compiler/EGL dependencies and Node. Its extra
container capabilities support the existing bubblewrap and process-inspection
tests only, on the disposable hosted VM. Frontend retains its separate Ubuntu job.

The [Python download descriptor](../../.github/python-downloads.json) fixes the
upstream 23 June build and archive hash. The installer is pinned to uv 0.9.25 and
its archive hash. A fresh isolated local installation verifies the exact Python
ELF hash and byte-exact relocated sysconfigdata at the declared prefix. CI checks
both before `uv sync --locked --extra simulation --extra lab`, and records the
actual environment. The full canonical suite remains selected.

The authored CPU fixture now inventories its current interpreter prefix and
resolves declared library load paths before binding synthetic baseline data.
Historical baseline/native documents, production sources, interpreter pins,
native rosters and test assertions are unchanged. All five affected authored
tests pass serially in 49.20 seconds, with exit 0. Their exact command is:

```sh
set -o pipefail
PALIMPSEST_TEST_BASETEMP="$PWD/runs/authored-prefix-refresh-20261025" scripts/run_tests.sh -- \
  tests/test_puck_cpu_held_amendment.py::test_authored02_uses_fresh_capsule_preserves01_and_refuses_reentry \
  tests/test_puck_cpu_held_amendment03.py::test_authored03_completes_after_real_failed01_02_without_changing_their_bytes \
  tests/test_puck_cpu_amendment_audit.py::test_real_authored02_has_independent_current_epoch_audit_and_exclusive_cli \
  tests/test_puck_cpu_amendment03_audit.py::test_real_authored03_audit_binds_new_policy_capsule_and_retains_both_failures \
  tests/test_puck_cpu_amendment04_audit.py::test_real_authored04_independent_audits_fresh_bindings_and_preserves_history \
  2>&1 | tee runs/main-integration-2026-10-25/authored-prefix-refresh.log
```

Workflow YAML and all shell steps parse. This is a repair candidate, not a passing
hosted result. No actual model/study allocation, browser acceptance or scientific
qualification ran. Hosted verification and main landing remain required.
