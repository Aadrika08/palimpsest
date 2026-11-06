# Source child CPU compatibility implementation plan

**Goal:** Keep the existing source parent's requested worker CPU ceiling compatible with an observed inherited hard CPU limit, without changing any allocation or enabling actual execution.

**Spec:** Existing `qualify_memory_family_source_v2.py::launch` and unchanged `paper/studies/change_audit_v1/process.py` worker setup; full project completion and source-preservation plans remain binding. This is a narrow bug fix, not the unadopted external-manifest or lifetime-wrapper design.

## Scope and constraints

Baseline source/test code is the locally verified `53ab035`; `108c6ef` adds documents only. Work occurs on separate local `research/source-cpu-compat-v1`; remote PR186 stays at108c6ef during hosted checks. Reuse the existing isolated worktree. No worktree/model checkout or dependency installation is needed.

Only modify `scripts/qualify_memory_family_source_v2.py`, `tests/test_memory_family_source_qualification_v2.py`, and create `tests/test_memory_source_cpu_limits.py` as necessary. Preserve the supervisor, owner, protocols, trust pins, schemas, actual CLI hard stops, deadlines, output budgets and all research allocations. No actual model/raw/SNP/checkpoint/catalog reads or hashes; no Engine/model/service/native owner launch or operational probe. Authored stdlib subprocess tests are permitted. Do not hash all tracked files. Preserve logs and failures; no cleanup/deletion.

## Mechanism and exact interface

The unchanged supervisor installs `(max(1, ceil(cpu_seconds)), max(1, ceil(cpu_seconds))+1)` in its child. Passing the parent's remaining aggregate allowance (up to1800) can attempt to raise a smaller inherited hard limit and fail before exec. This is a source-derived failure mode; no actual stage failure is asserted.

Add private `_worker_cpu_budget(remaining_cpu_seconds, inherited_hard_limit)` to the parent. Require exact non-bool numeric finite `0 < remaining <= ALLOCATION['cpu_seconds']`. An observed `resource.RLIM_INFINITY` is known unlimited, not unknown: return remaining unchanged. Otherwise require an exact integer hard limit >=2 and return `min(remaining, hard_limit-1)`. Unknown/invalid/nonfinite/inadequate hard limits refuse. The returned budget must satisfy `max(1, ceil(budget))+1 <= inherited_hard_limit` for finite limits. No setrlimit call raises a limit in this parent.

In `launch`, get the current hard `RLIMIT_CPU`, derive this budget before the runner, and record/pass that exact requested value as the existing `cpu_seconds`. Aggregate phase accounting and monitor thresholds remain unchanged. A reduced per-worker allowance is not a new aggregate CPU proof. Do not add a registry, loader, helper process, configurable override or deadline change.

## One task with red/green verification

- [ ] Reproduce the real setup failure in a fresh authored stdlib child with a finite hard limit and the unchanged supervisor. Keep the parent pytest process limits untouched, bound wall/log output, and require the intended exec/setup error rather than an unrelated import or timeout failure. Choose a safe fixed authored limit (e.g.10CPU seconds) above import overhead; no research owner.
- [ ] Write failing tests for finite clamp, low/unknown/invalid limits, known infinity, partial CPU remainder and parent runner/record integration. Show the old unbounded request failing and the clamped request completing a tiny authored command. Keep the existing parent fake-owner boundary; never let a fixture call the real model loader.
- [ ] Run targeted tests and retain genuine red output before production edits. Read the TDD skill's writing-good-tests guidance. Failures must demonstrate the budget/setup or integration behavior, not a malformed fixture.
- [ ] Implement only the helper and launch call-site change. Do not change `process.py` or parent scope/claim fields.
- [ ] Run the new test file and the nearest existing parent qualification suite under the canonical clean environment, using the shared venv alias, `-B`, thread limits and private tmpfs if needed. Retain exact commands, counts and logs; hash only explicitly owned source/test files and unchanged supervisor source for continuity. No full-suite completion claim from focused checks.
- [ ] Commit the owned fix/tests. Fresh independent spec/code review is required. This patch remains local pending integration with the next source batch and its required complete canonical/hosted checks; no duplicate CI wave for this patch alone.

## Acceptance and remaining project gates

The unsafe authored finite-limit setup is reproduced; the fixed path completes without requesting a higher inherited hard limit; positive/negative/known-infinity tests and existing parent checks pass; supervisor/source allocations and actual gates remain unchanged. Record implementation and independent review in a separate ignored workspace. This bounded software result is not full lifetime accounting, a qualified runtime, source preservation, scientific evidence, actual GO, raw deletion authority or full project completion.
