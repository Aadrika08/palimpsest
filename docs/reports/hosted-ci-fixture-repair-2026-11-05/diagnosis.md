# b7e364a hosted CI diagnosis

Scope: read-only source/log diagnosis, plus one inert authored low/high disk probe. No code edits, hosted reruns, actual model execution, research execution, or protected input opens. Authoritative hosted log: `runs/ci-b7e364a-failure-42063786498.log`. Head supplied by orchestrator: b7e364a.

## Findings

### Nested authority regression wrapper: two distinct failure classes

The wrapper (`tests/test_authority_replay_process_ownership.py:10-20`) launches 101 ordinary authored tests; the hosted result is 23 failed / 78 passed (`failure log:679-705`). This is one canonical-suite failure, not 23 separate top-level hosted failures.

1. **Host disk capacity leaks into fixture-runner tests.** `_unit` checks actual output filesystem free bytes before invoking even an injected fixture runner (`paper/studies/authority_replay_v1/repeatability.py:301-316`). Protocol values require 6 GiB reserve plus a 512 MiB ordinary-unit output allowance (`protocol.json:10-13`), totaling 6.5 GiB. Hosted traces show callbacks not called (`failure log:223-255`) and expected fixture statuses replaced by `refused` (e.g. `failure log:598-618`, `660-677`). Of the 23 failing nested tests, 19 are in these `_unit` fixture paths; one additionally obscures the refusal when the intentionally failing final `_size` check sets status to failed, leaving no process record (`failure log:640-657`; `tests/test_repeatability.py:390-398`).

   **Verified mechanism, not a measured hosted byte count:** an inert probe using the existing `fixture_runner`, synthetic disk capacity, and the production `_unit` yielded:

   - synthetic free = 6 GiB: refused, runner calls = 0, error = `insufficient free-space reserve for unit admission`;
   - synthetic free = 7 GiB: completed, runner calls = 1.

   Retained rows, fixture outputs, and summary: `runs/ci-b7e364a-diagnosis-probe/`. The exact hosted filesystem capacity was not recorded in the failure excerpt. The source path plus refusal before callback supports insufficient admission capacity as the cause of these fixture failures; it does not establish where the hosted bytes went.

2. **Four timeout tests assume payload startup within 0.2–0.4 seconds.** Hosted failures are absent marker files or absent initial stdout, rather than a demonstrated live escaped descendant (`failure log:130-174`, `180-217`, `337-357`, `359-410`). Test budgets are `.4` and `.3` in `tests/test_repeatability_process_ownership.py:67,155`, and `.2` and `.3` in `tests/test_repeatability.py:153,179`. Production timeout starts before guardian startup (`repeatability.py:164-178`); payload execution follows guardian startup, a second interpreter launcher, ownership discovery, and two GO admissions (`repeatability.py:79-99`, `49-56`). The hosted status and SIGKILL assertions passed before the missing PID reads. These traces establish that the fixtures never observed readiness before timeout; they do not independently measure interpreter startup duration or prove a production cleanup defect.

### Five authored amendment failures share prepare admission

All five fail at the common `amendment_fixture` prepare CLI before amendment/audit behavior (`failure log:783-1083`; `tests/test_puck_cpu_held_amendment.py:184-187`). The generic `CPU held-runtime resource admission failed` condition combines four checks (`scripts/qualify_puck_cpu_held_runtime.py:821-828`):

| Check | Prepare threshold in authored fixture |
| --- | --- |
| soft and hard RLIMIT_NOFILE | 40000 each |
| MemAvailable | 128 MiB, explicitly scaled by authored clone |
| project filesystem free | 4 GiB |
| staging parent `/tmp` free | 2 GiB |

The authored project helper scales only RAM, retaining production disk/tmpfs reservations and asserting all other limit values unchanged (`tests/test_puck_cpu_held_parent_integration.py:48-79`). Workflow specifies NOFILE 65536 and a 4 GiB `/tmp` tmpfs (`.github/workflows/checks.yml:21-22,93`). Its separate selected admission preflight precedes the full suite (`checks.yml:86-88`). Full-suite outputs accumulate until all four passes finish (`scripts/run_tests.sh:51-56`). This makes cumulative filesystem use a credible explanation, consistent with nested disk refusals, but **the exact resource that failed this combined predicate remains unknown**: the failure log contains no contemporaneous free-byte/RAM/FD sample. Do not present root disk or tmpfs depletion as measured fact.

## Smallest correction and verification recommendations

1. Keep production protocol, admission checks, ownership behavior, and archived frozen evidence unchanged. In authored `test_repeatability.py`, provide a default synthetic sufficient `disk_usage` through a scoped pytest fixture so mocked verifiers test accounting rather than host capacity. Retain `test_admission_refuses_without_starting` and its explicit 6 GiB override; it must continue proving that 6 GiB without the full output allowance refuses before callback. Keep output-cap and monitor-failure negatives intact.
2. Increase only the four authored timeout budgets to a bounded value permitting the supervisor/launcher chain to start (e.g. 2 seconds), with sleepers still longer than the cap. Prefer a bounded readiness handshake if strict startup independence is needed. Do not weaken production timeout/admission semantics. Re-run the four tests and the 101-test wrapper locally before considering hosted execution.
3. Extend the existing authenticated authored project-clone limit replacement to small **nonzero** disk and tmpfs reserves appropriate to tiny authored modules (e.g. 128 MiB each), alongside the existing 128 MiB RAM scaling. Update byte round-trip and exact expected-limit assertions so only the declared test-clone adjustments are allowed. Hash/source bindings must continue to bind the changed clone. Do not patch the real parent, archived auditor/bootstrap, production limit constants, or retained historical evidence. This does not establish actual-package readiness.
4. Before a future hosted retry, add a compact failing-resource diagnostic in the authored test path: soft/hard NOFILE, MemAvailable, project `disk_usage(...).free`, `/tmp` free, and their configured thresholds. Capture at failure time, retaining existing CLI stdout/stderr receipts (`test_puck_cpu_held_parent_integration.py:265-285`). A workflow startup `df` alone cannot explain a late full-suite resource refusal. Preserve artifacts before cleanup if further evidence is needed.

Targeted local commands after a test-only correction (preserve this interpreter alias):

```bash
PALIMPSEST_PYTHON=/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python scripts/run_tests.sh -- tests/test_authority_replay_process_ownership.py
PALIMPSEST_PYTHON=/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python PALIMPSEST_TEST_BASETEMP="$PWD/runs/authored-ci-probe" scripts/run_tests.sh -- tests/test_puck_cpu_amendment03_audit.py::test_real_authored03_audit_binds_new_policy_capsule_and_retains_both_failures tests/test_puck_cpu_amendment04_audit.py::test_real_authored04_independent_audits_fresh_bindings_and_preserves_history tests/test_puck_cpu_amendment_audit.py::test_real_authored02_has_independent_current_epoch_audit_and_exclusive_cli tests/test_puck_cpu_held_amendment.py::test_authored02_uses_fresh_capsule_preserves01_and_refuses_reentry tests/test_puck_cpu_held_amendment03.py::test_authored03_completes_after_real_failed01_02_without_changing_their_bytes
```

These commands were recommendations only and were not run during diagnosis. The canonical test script removes its own basetemps on completion; preserve any newly needed raw diagnostic evidence beforehand. The only executed verification was the retained inert low/high disk probe, exit code 0. Hosted capacity measurements and a hosted green result remain outstanding.
