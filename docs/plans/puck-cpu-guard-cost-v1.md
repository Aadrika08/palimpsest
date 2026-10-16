# Runtime guard cost diagnosis

Goal: advance the real episode checkpoint by measuring one suspected source of
repeated runtime work. This source-only diagnosis does not qualify installed
imports, explain attempt 08's timeout, or create qualification 09 controls.

The active release goal remains
`docs/plans/simulation-release-execution-goal.md` on
`research/simulation-completion-next`. Qualifications 01–08 remain consumed.
The 180s normal-return deadline, 2GiB qualification RAM floor, existing admission
predicates, custody checks and refusal behavior remain unchanged.

## Scope and hypothesis

`HeldWorkerBootstrap._check` builds the allowed module-name unions for each
nonstandard-library module-cache entry. A larger cache and larger in-flight
allowance may therefore increase this portion of the check quadratically.
Neither this hypothesis nor a fixture timing establishes installed-runtime cause.

Reuse `tests/test_puck_worker_dependencies.py::dependency_fixture`: an isolated
real worker receives authored source and its real held dependency provider.
Insert 128, 512 and 2048 synthetic module-cache entries and corresponding
dependency in-flight allowances only inside the authored preflight; remove every
entry and restore original state before normal terminal verification. These are
synthetic cache workloads, not initialized installed dependencies or scientific
episodes. No native fixture extension, model, renderer or protected data is used.

## Work and finite exit

- [x] Record three unprofiled samples of three light checks at each fixed size.
  Separately count real dependency-dictionary `keys` calls with `sys.setprofile`
  during one check. Keep profiling outside timed samples and restore the previous
  profile hook. Retain exact sources, commands, timings and worker outcomes.
- [x] Exercise refusal/first-failure behavior through the real worker for an
  unknown cache entry, a lying container and a module-name callback that removes
  its own allowance. These constrain any proposed shortcut.
- [x] Measure two isolated experimental bootstrap copies: direct dependency
  membership and a hoisted whitelist. Run the same behavior cases against each
  to test the static counterexamples. Retain their source and failed checks;
  neither experimental copy replaces production code.
- [x] Review the measurement and choose the smallest supported change, or retain
  the current loop if preserving behavior requires disproportionate machinery.
  Any production correction first needs a meaningful failing regression, affected
  guard/CPU compatibility checks and independent review.
- [x] Publish the evidence, limitations, decision and next concrete action;
  commit and push the bounded source/evidence branch. Installed qualification
  remains unstarted by this work unit.

Files: this plan; an authored workload and behavior tests under `tests/`; and
`docs/reports/puck-cpu-guard-cost-v1.md` with its finite retained evidence packet.
Only a justified correction may touch `scripts/puck_worker_bootstrap.py`.
