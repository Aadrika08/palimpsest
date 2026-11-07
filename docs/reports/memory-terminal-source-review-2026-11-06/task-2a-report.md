# Task2a implementer report

Scope: private Engine persistence and strict legacy default guard only. Base
`0dec243043faf97fd2d5ec5f88a7d1e7cfe51d6a`, branch
`research/memory-vnext-spec-v1`. Only `src/palimpsest/engine.py` and new
`tests/test_memory_engine_transition_vnext.py` are staged for the scoped commit.
Root-owned plan amendments and accounting-provider documents remain separate.

Scoped commit, verified by postcommit readback:
`8970a9681ba8921c82d914e9d6619de3e1340679`.

## Implementation and review

- `_step` calls `_require_memory_transition_mode` as its first operation.
  Genuine memory-decision-v2 defaults validate strict3 before sensing. State4,
  either new state field, either manifest field, or presence of any reserved
  Engine field (including null/partial values) refuses. Other scenarios retain
  their prior path unless one of these contradictory indications is present.
- `_persist_terminal_transition_vnext` requires the exact synchronous RunWriter,
  owner thread/live Engine, matching bound/supplied Context/job/chain and owner
  UUID/manifest, strict4 state, valid continuation counters and consistent typed
  result. Encoder validation preflights exact complete Witness/Commit events.
- Actual synchronous Witness event return follows real flush/fsync. Only then
  does the journal advance. Returned/idempotent proposed state is recursively
  detached at actual assignment. Only witnessed returns emit Commit, followed
  by ordinary memory_decision events with copied legacy route_anchor.
- Raised/rejected results never assign local effects or fabricate decisions or
  Commit. The fixed opaque-token rethrow helper verifies and raises the same
  original exception object; a changed exception projection refuses as
  infrastructure. Idempotent results add no events/journal entry.
- Any helper exception sets a one-way failure latch. Actual assignment survives
  later Commit/decision write failure. A returned supervisor failure commits its
  actual state and sets the stop latch. There is no rollback, retry, 900 verdict,
  public opt-in, held-source capability, Task6 import, or integrated branch.

Self-review checked exact envelopes/no case_id, sync ordering, result/Lifecycle
cross-links, event/chain hashes, detachment, idempotence, two-Witness ceiling,
failed-prefix retention, default path isolation, and scoped diff. It found and
fixed a missing defense against stripping a required Witness from a returned
supervisor failure, using the genuine authored worker deadline to establish RED.

## Fixed private Task2b interface

Default Engine instances have **none** of these attributes. Presence is itself
an indication for the default guard; null does not erase an indication.

- `_memory_terminal_vnext_mode`: literal `memory-terminal-vnext-v1`.
- `_memory_terminal_vnext_context`: independently detached validated Context.
- `_memory_terminal_vnext_job_sha256`: fixed job digest.
- `_memory_terminal_vnext_chain`: `(persisted_witness_count, witness_body_head)`;
  initially `(0, sha256(Context))`, updated only after synchronous Witness fsync.
- `_memory_terminal_vnext_failed`: false for a fresh private bound fixture, true
  after any failed helper call or reached terminal; no code clears the latch.
- `_memory_terminal_vnext_route_anchor`: exact `{tick,stage,xy}`, stage
  `pre-control`, tick exactly Engine total_tick == episode_step, xy two plain
  finite floats. Required before writes whenever returned decisions are nonempty.
  Task2b must bind this from the SAME actual sensing pose cut, and Task3 must
  independently prove it. Here values are authored; no source claim follows.

Manifest fields are `memory_terminal_vnext_context_sha256` and
`memory_terminal_vnext_mode`. The helper requires their exact matching values;
the default guard refuses their presence even if null. It also requires the
writer manifest run_id to match Context and Engine. Task2b owns authentic binding
and durable manifest configuration; this helper does not construct admission.

## Retained verification

All artifacts are under
`.superpowers/sdd/memory-terminal-vnext-implementation/task-2a-evidence/`.
Each pytest command used a distinct fresh `--basetemp`; all trees/logs remain.
Commands used this exact approved environment/interpreter prefix:

```text
env -i PATH=/usr/bin:/bin PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts:tests LC_ALL=C.UTF-8 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 MUJOCO_GL=egl CUDA_VISIBLE_DEVICES='' /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -B -m pytest
```

The full per-invocation arguments were:

```text
tests/test_memory_engine_transition_vnext.py -q --basetemp=<evidence>/red-01-tmp
tests/test_memory_engine_transition_vnext.py -q --basetemp=<evidence>/red-02-tmp
tests/test_memory_engine_transition_vnext.py -q --basetemp=<evidence>/green-01-tmp
tests/test_memory_engine_transition_vnext.py -q -k returned_supervisor_failure_cannot --basetemp=<evidence>/red-03-tmp
tests/test_memory_engine_transition_vnext.py -q -k returned_supervisor_failure_requires --basetemp=<evidence>/red-04-tmp
tests/test_memory_engine_transition_vnext.py tests/test_memory_transition_vnext.py tests/test_memory_decision_engine.py tests/test_engine.py tests/test_memory_decision.py tests/test_memory_task.py -q --basetemp=<evidence>/green-final-01-tmp
```

`<evidence>` expands to the exact directory above. Each invocation redirected
stdout/stderr to its matching `.log`, then separately recorded pytest status in
its `.exit` file and read the result.

| Log | pytest exit | Actual result and disposition |
| --- | --- | --- |
| red-01.log | 1 | 52 failed, 1 passed, 11.22s. Missing helper/guard; also exposed incomplete authored observation/task/world fields. Retained; fixture completed before repeating RED. |
| red-02.log | 1 | 52 failed, 1 passed, 13.33s. Genuine missing private APIs and early guard behavior, before production implementation. Legacy default test passed. No import/setup/native payload failure. |
| green-01.log | 1 | 1 failed, 52 passed, 11.63s. Test wrapper duplicated context keyword before calling helper; wrapper fixed. |
| red-03.log | 0 | 1 passed, 56 deselected, 0.42s. First constructed supervisor failure was invalid and refused incidentally. Not claimed as intended RED; replaced with actual worker progression. |
| red-04.log | 1 | 1 failed, 1 passed, 56 deselected, 4.18s. Valid actual returned supervisor failure accepted after required Witness stripped; expected DID NOT RAISE reproduced and fixed. |
| green-final-01.log | 0 | **174 passed in 38.37s**, all six approved files; no warnings reported. |

Tests prove real Witness fsync before journal/assignment/rethrow; injected fsync
failures on Witness, Commit and first ordinary decision; errors immediately
before assignment and immediately before Commit emission; unchanged input before
assignment and preserved actual state afterward; no continuation/retry after
failure; two-Witness/one-Commit selected-then-error chain; original exception
identity and tamper refusal; no new idempotent event; precise route-anchor and
identity/cap refusal; real default synthetic Engine path remains legacy.

`git diff --check` passed. Source headers confirmed authored/synthetic fixtures;
the existing SmallEnv/SmallPolicy default guard test and approved legacy files
execute no actual native/model payload. Helper and guard fixtures use objects
that raise on any environment/policy attribute access. No broad/native suite,
dependency install, protected data, actual raw/SNP/source/model read, research
owner, service, push, CI, merge or cleanup was performed.

`measurements.json` reports complete spaced JSON + newline bytes observed in the
final retained authored recording files: Witness max **12,244** (16 records),
Commit max **783** (6 records), within 16,384/2,048 caps. This includes retained
Task1 worst-case authored fixtures and partial failed-write records, not actual
research evidence. `inventory.tsv` hashes 449 retained files, 708,696 bytes
excluding inventory itself. Logs, failed prefixes, and workspaces remain intact.

Tested source SHA256: engine
`7001059ce5c8b7b7659cbbe848ce01d1bbadf9e32215d9fa0aa11738eb10ccc4`, tests
`8e21f425f398ac470b4c04bb99c3870467b48d2e6d993de9b243b0a2b874c1c9`.
The staged new-file whitespace check then detected one trailing blank line at
EOF. Removed that blank line only; final test SHA256 is
`4e6a7f13a74d7fcd558f878976e4d6bd1711a0776e5d650b4886cdadb3446d40`.
No semantic edits followed the passing suite. Final staged whitespace check
passed. The text-only whitespace trim used `/usr/bin/python3` without repository
imports or payload reads; all test executions used the approved interpreter.

Limitations: private software tests establish no source custody, public opt-in,
source closure qualification, scientific result, actual admission or GO. Task2b
and Task3 remain responsible for authentic binding/sensing and independent replay.
First-party quota telemetry and working_set bindings were unavailable; quota is
unknown. Fresh independent spec and quality review remain required after commit.
