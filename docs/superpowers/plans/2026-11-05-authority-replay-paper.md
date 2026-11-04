# Authority-Aware Replay Paper Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a substantially stronger Palimpsest systems paper whose central authority/replay claim is tested by a preregistered fault matrix, repeated continuation/replay study, matched overhead ablations, and clean-checkout reproduction.

**Architecture:** A frozen study protocol defines every unit and expected oracle before execution. Study-only drivers call production Palimpsest interfaces, retain raw outputs outside Git, and emit one append-only JSON row per declared unit; a pure analyzer rejects incomplete or drifted campaigns and generates the compact evidence consumed by the manuscript. The rewritten paper centers the tested semantic contract and treats historical controller outcomes as secondary context.

**Tech Stack:** Python 3.11, pytest, existing Palimpsest/MuJoCo/FLYNN runtime, JSON/CSV, LaTeX/BibTeX/TikZ, Poppler.

**Spec:** `docs/superpowers/specs/2026-11-05-authority-replay-paper-design.md`

## Global Constraints

- CPU-only; no training, tuning, held-out access, CUDA qualification, paid compute, human study, or physical-hardware study.
- Use full FLYNN assets read-only from `/home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn`; record their verified manifest identity.
- Never mutate historical reports, existing compact evidence, retained raw runs, or source assets.
- Commit the protocol and executable study implementation before creating paper-result rows.
- Refuse non-empty campaign output roots; never replace a failed unit with an undeclared retry.
- Treat seeds, fault variants, and paired conditions using the experimental units declared in the spec.
- Label fresh-checkout evidence on this host as same-host; do not call it independent reproduction.
- Preserve the current v1 PDF and verification record in Git history; the rewrite supersedes it only after the new evidence passes review.

## Review Focus

- A missing/duplicate/undeclared campaign row must make analysis fail, not silently change a denominator (Task 1 tests).
- A baseline predicate must be computed from the same underlying trace as the Palimpsest oracle (Task 2 tests).
- A fault that is explicitly refused must not be counted as a successful recovery, and a benign control must not be counted as a true positive (Task 2 tests).
- Timing conditions must preserve identical actions, tick counts, and final state before an overhead delta is accepted (Task 4 tests).
- Output from a different commit, protocol hash, asset identity, or reused non-empty root must be rejected (Tasks 1, 3, and 4 tests).

---

### Task 1: Freeze the protocol and campaign record contract

**Files:**
- Create: `paper/studies/authority_replay_v1/protocol.json`
- Create: `paper/studies/authority_replay_v1/common.py`
- Create: `paper/studies/authority_replay_v1/analyze.py`
- Create: `paper/studies/authority_replay_v1/tests/test_common.py`
- Create: `paper/studies/authority_replay_v1/tests/test_analyze.py`
- Create: `paper/studies/authority_replay_v1/README.md`

**Interfaces:**
- Produces: `load_protocol(path: Path) -> Protocol`, `campaign_identity(repo: Path, protocol: Path, assets: Path) -> dict[str, object]`, `prepare_output_root(path: Path) -> None`, `append_row(path: Path, row: dict[str, object]) -> None`, `load_complete_rows(protocol: Protocol, row_paths: list[Path], identity: dict[str, object]) -> list[dict[str, object]]`, and `summarize(protocol: Protocol, rows: list[dict[str, object]]) -> dict[str, object]`.
- Consumes: exact Git HEAD, protocol SHA-256, runtime source hashes, asset manifest hashes, declared unit IDs and expected conditions.
- `Protocol` fields are `schema_version`, `study_id`, `resources`, `comparison_policy`, `fault_cases`, `continuation`, `replay`, `execution_overhead`, `operation_cost`, and `offline_reproduction`. `FaultCase` fields are `id`, `family`, `path`, `seeds`, `variants`, `conditions`, `injection_stage`, `naive_predicate`, `semantic_oracle`, `expected_outcome`, `timeout_seconds`, and `max_output_bytes`.

- [ ] Write failing tests for schema/version validation, exact declared unit expansion, empty-root refusal, append-only unique unit IDs, finite numeric fields, failed-unit retention, duplicate/missing/undeclared rows, and commit/protocol/asset identity drift.
- [ ] Run `/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -m pytest -q paper/studies/authority_replay_v1/tests/test_common.py paper/studies/authority_replay_v1/tests/test_analyze.py` and confirm failures because the interfaces are absent.
- [ ] Implement the typed protocol/identity/row contract and deterministic summary generation using only the standard library.
- [ ] Populate the protocol with every A1--E3 case/seed/variant/control exactly as tabulated in the spec, continuation seeds 0--9, replay seeds 0--4, overhead seeds 0--9 and four cyclic matched conditions, operation-cost seeds 0--4, the exact comparison policy, 15-minute unit/four-hour campaign timeouts, 512 MiB/2 GiB/8 GiB output caps, 6 GiB reserve, metrics, and stop rules.
- [ ] Document raw-output ownership, commands, failure retention, and the distinction between same-host checkout and independent reproduction.
- [ ] Run the focused tests and `/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python paper/studies/authority_replay_v1/analyze.py --protocol paper/studies/authority_replay_v1/protocol.json --self-check`; require PASS.
- [ ] Commit as `paper: freeze authority replay study protocol`.

### Task 2: Implement the semantic fault matrix

**Files:**
- Create: `paper/studies/authority_replay_v1/fault_matrix.py`
- Create: `paper/studies/authority_replay_v1/tests/test_fault_matrix.py`
- Modify only if a reusable injection seam is missing: `src/palimpsest/{engine,replay,snapshots,records,storage}.py`
- Add corresponding production regression test for any modified production seam under `tests/`.

**Interfaces:**
- Consumes: Task 1 identity/row functions and protocol fault cases.
- Produces: `run_fault_case(case: FaultCase, output: Path, identity: dict[str, object]) -> dict[str, object]` and one row per `(fault_family, variant, condition, repetition)`.
- Each row records injection stage, Palimpsest outcome, baseline outcome from the same trace, silent acceptance, explicit detection, correct recovery, benign false rejection, elapsed time, and retained-prefix validity.

- [ ] Write failing tests for every exact case ID in the spec plus benign controls, same-trace naive-predicate evaluation, refusal-versus-recovery classification, deterministic first-divergence reporting, and immutable source fixtures.
- [ ] Run `/usr/bin/env PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 PALIMPSEST_SIMULATION_TESTS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -m pytest -q paper/studies/authority_replay_v1/tests/test_fault_matrix.py` and confirm RED failures.
- [ ] Implement deterministic fixture injections only for C1--C3, P1, and E1--E3; add a narrow dependency-injection seam only where deterministic process-death/write-boundary injection is otherwise impossible.
- [ ] Implement A1--A3, R1--R2, S1--S2, D1--D2, and B1--B2 through the actual FLYNN/lab/runtime path, with copied sources/assets under the output root and original before/after hashes.
- [ ] Implement the same-trace naive predicates and the pose-only, start-only-hash, direct-writer, and shared-owner/resource ablations named by the protocol.
- [ ] Run the fault tests plus `tests/test_engine.py tests/test_worker.py tests/test_snapshots.py tests/test_replay.py tests/test_records.py tests/test_records_background.py tests/test_recovery.py tests/test_storage.py`.
- [ ] Run a dry campaign to a temporary root and verify exact declared rows, source immutability, and analyzer acceptance.
- [ ] Commit as `paper: add semantic fault campaign`.

### Task 3: Implement repeated continuation and replay drivers

**Files:**
- Create: `paper/studies/authority_replay_v1/repeatability.py`
- Create: `paper/studies/authority_replay_v1/tests/test_repeatability.py`
- Modify: `scripts/verify_lab.py` only if required to expose `--seed`, `--prefix`, `--continuation`, and per-operation timings without changing replay semantics.
- Test any `verify_lab.py` change in its existing test module plus `test_repeatability.py`.

**Interfaces:**
- Consumes: Task 1 identity/row contract, `scripts/verify_execution.py`, the public lab/replay interfaces, seeds and bounds from the protocol.
- Produces: `run_continuation_unit(seed: int, ...) -> dict[str, object]` and `run_replay_unit(seed: int, ...) -> dict[str, object]` with exact agreement/refusal fields, first divergence, snapshot bytes/hash, and per-operation timings.

- [ ] Write failing tests using small fixture controllers for seed propagation, prefix/continuation bounds, fresh output enforcement, paired replay-mode accounting, failure retention, and comparison-field completeness.
- [ ] Run the focused tests and confirm RED failures.
- [ ] Implement thin process wrappers around the existing verifiers; do not duplicate snapshot or replay comparison logic.
- [ ] If needed, add the bounded `verify_lab.py` parameters and timestamps with backward-compatible defaults and regression tests.
- [ ] Run focused tests and one fixture-only dry unit for each driver; require analyzer acceptance.
- [ ] Commit as `paper: add continuation and replay campaign drivers`.

### Task 4: Implement matched overhead ablations

**Files:**
- Create: `paper/studies/authority_replay_v1/overhead.py`
- Create: `paper/studies/authority_replay_v1/tests/test_overhead.py`
- Create: `paper/studies/authority_replay_v1/null_writer.py`
- Modify production timing surfaces only if needed, with tests: `src/palimpsest/records.py`, `src/palimpsest/engine.py`, `src/palimpsest/replay.py`.

**Interfaces:**
- Consumes: Task 1 identity/row contract and the four protocol conditions.
- Produces: `run_execution_overhead_unit(seed: int, condition: str, ...) -> dict[str, object]` with action/final-state identity, tick count, open time, steady-state wall/tick, component timing, bytes/tick, RSS/FD/thread samples, backpressure, and storage recount; and `run_operation_cost_unit(seed: int, source: Path, ...) -> dict[str, object]` with capture/save/read/restore-first-tick/playback/action-replay/policy-replay timings from a retained full-writer source.

- [ ] Write failing tests that reject execution timing rows when actions, tick counts, or final-state digests differ; test null/sync/background/bounded-storage dispatch, cyclic order, 20 warm-up plus 200 measured ticks, finite metrics, and separation of operation-cost rows from null-writer conditions.
- [ ] Run focused tests and confirm RED failures.
- [ ] Implement a benchmark-only `NullWriter` matching the required writer contract without changing production behavior.
- [ ] Implement the four cyclic Latin-square rotations by `seed mod 4`, capture host-load/cache-order covariates, and apply the matched state/action gate before retaining timing results.
- [ ] Add only the minimal production timing counters needed for decomposition, preserving existing defaults and tests.
- [ ] Run focused tests plus performance/recording/replay regression slices and a short fixture dry campaign.
- [ ] Commit as `paper: add matched semantic overhead study`; this clean HEAD becomes the campaign source commit recorded by Task 5, while protocol identity remains its own content hash.

### Task 5: Preflight and execute the frozen local campaign

**Files:**
- Create from results: `paper/evidence/authority-replay-v1/campaign-manifest.json`
- Create from results: `paper/evidence/authority-replay-v1/rows.csv`
- Create from results: `paper/evidence/authority-replay-v1/summary.json`
- Create from results: `paper/evidence/authority-replay-v1/failures.json`
- Create from results: `paper/evidence/authority-replay-v1/fault-traces.jsonl`
- Preserve raw results outside Git under the protocol-declared run root.

**Interfaces:**
- Consumes: Tasks 1--4 at one clean committed SHA.
- Produces: complete append-only row sets and hash inventory for Tasks 6--8.

- [ ] Record free disk, memory, CPU/GPU environment, exact branch/SHA, clean status, asset identity, tool versions, and protocol hash; require at least 6 GiB free, cap study raw output at 8 GiB, cap ordinary units at 512 MiB and offline checkout at 2 GiB, run sequentially, and stop new units after four total hours or any 15-minute unit timeout.
- [ ] Run `/usr/bin/env PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 PALIMPSEST_SIMULATION_TESTS=1 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python -m pytest -q paper/studies/authority_replay_v1/tests tests/test_engine.py tests/test_worker.py tests/test_snapshots.py tests/test_replay.py tests/test_records.py tests/test_records_background.py tests/test_recovery.py tests/test_storage.py` at the frozen SHA.
- [ ] Execute `/usr/bin/env PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python paper/studies/authority_replay_v1/fault_matrix.py --protocol paper/studies/authority_replay_v1/protocol.json --assets /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn --output runs/paper-authority-replay-v1/faults`; preserve every declared unit and analyze immediately.
- [ ] Execute `/usr/bin/env PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python paper/studies/authority_replay_v1/repeatability.py --kind continuation --protocol paper/studies/authority_replay_v1/protocol.json --assets /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn --output runs/paper-authority-replay-v1/continuation` for seeds 0--9; never substitute a failed seed.
- [ ] Execute the same command with `--kind replay --output runs/paper-authority-replay-v1/replay` for seeds 0--4; never substitute a failed seed.
- [ ] Execute `/usr/bin/env PYTHONPATH=src MUJOCO_GL=egl OMP_NUM_THREADS=2 /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python paper/studies/authority_replay_v1/overhead.py --kind execution --protocol paper/studies/authority_replay_v1/protocol.json --assets /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn --output runs/paper-authority-replay-v1/overhead` for seeds 0--9; reject unmatched four-condition units rather than retaining misleading timing.
- [ ] Execute the same command with `--kind operations --replay-root runs/paper-authority-replay-v1/replay --output runs/paper-authority-replay-v1/operations` for replay seeds 0--4; null-writer conditions are not inputs.
- [ ] Execute `/usr/bin/env PYTHONPATH=src /home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python scripts/verify_offline.py --repo . --assets /home/utkarsh/Work/shraddha/palimpsest/data/assets/flynn --output runs/paper-authority-replay-v1/offline --duration 55 --setup --full-flynn` once and label it same-host clean-checkout evidence.
- [ ] Generate compact summaries and raw-tree hashes; independently recompute representative rows from raw output.
- [ ] Commit only the compact evidence as `paper: record authority replay study`.

### Task 6: Bind new results into generated paper evidence

**Files:**
- Modify: `paper/evidence/claims.yaml`
- Modify: `paper/scripts/build_evidence.py`
- Modify: `paper/tests/test_build_evidence.py`
- Create: `paper/generated/fault-matrix.tex`
- Create: `paper/generated/overhead-table.tex`
- Create: `paper/generated/replay-table.tex`

**Interfaces:**
- Consumes: Task 5 summary/manifest/failure files.
- Produces: source-bound LaTeX macros/tables for the new central claims; historical v1 claims remain available but are no longer all central.

- [ ] Write failing generator tests for exact JSON-pointer binding, denominators including failures, paired-condition labels, and rejection of stale or incomplete campaign summaries.
- [ ] Run focused tests and confirm RED failures.
- [ ] Extend deterministic generation for the three new tables without hand-copying values into figures or prose.
- [ ] Add only claims supported by Task 5; explicitly retain failed or inconclusive outcomes.
- [ ] Run generator tests and freshness checks; commit as `paper: bind authority replay evidence`.

### Task 7: Rewrite the manuscript around the tested thesis

**Files:**
- Rewrite: `paper/main.tex`
- Modify: `paper/references.bib`
- Replace/add: `paper/figures/authority-sequence.tex`
- Replace/add: `paper/figures/replay-semantics.tex`
- Add generated/table or data-backed fault/overhead visuals only when supported.
- Modify: `paper/ARTIFACT.md`, `paper/README.md`, `paper/SUBMISSION_CHECKLIST.md`.

**Interfaces:**
- Consumes: Tasks 5--6 generated evidence and primary related-work sources.
- Produces: a venue-neutral 7--9 page manuscript with one thesis, one coherent evaluation, and scoped artifact instructions.

- [ ] Replace the abstract/introduction with the motivating false-inference incident, the semantic-reproducibility thesis, and three tested contributions.
- [ ] Add the four-category failure model and explicit semantic invariants.
- [ ] Compress implementation details around the authority transition, full continuation state, and replay modes.
- [ ] Organize evaluation strictly by RQ1--RQ4; report denominators, failures, paired units, and actual costs from generated inputs.
- [ ] Keep one FLYNN case study; reduce historical memory/puck/MaleCNS material to scoped context or appendix.
- [ ] Replace the categorical bars and linear evidence ladder with the sequence diagram, replay-semantics matrix, fault matrix, and supported cost/continuation visualization.
- [ ] Rewrite related work using primary sources and a layer/semantics comparison table; use “not specified” rather than unsupported absence claims.
- [ ] Consolidate limitations and artifact administration; retain same-host, licensing, venue, author, archive, and independent-machine gates.
- [ ] Build and inspect page count/log after each major section; commit as `paper: rewrite around authority-aware replay`.

### Task 8: Final verification and independent evidence review

**Files:**
- Modify: `paper/scripts/verify_paper.py`
- Modify: `paper/tests/test_verify_paper.py`
- Regenerate: `paper/build/palimpsest-systems-paper.pdf`
- Regenerate: `paper/build/verification.json`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: verified PDF, machine-readable build record, and final claim/evidence review.

- [ ] Update build-input binding for every new generated table, figure, compact evidence file, and study protocol.
- [ ] Run all paper/study tests, focused production regressions, evidence generation checks, and `git diff --check`.
- [ ] Build the PDF from a clean source commit; require no LaTeX errors, undefined citations/references, overfull clipping, stale inputs, missing text, or blank pages.
- [ ] Render and visually inspect every page, table, figure, link, caption, and reference.
- [ ] Have a fresh independent reviewer trace each abstract/conclusion claim to compact/raw evidence and report critical/important/minor findings.
- [ ] Fix critical/important evidence mismatches with regression coverage; do not hide failed study units.
- [ ] Commit source corrections, rebuild the artifact against the exact source commit, and commit the verified PDF/record separately.
- [ ] Report the completed local paper separately from external submission gates.
