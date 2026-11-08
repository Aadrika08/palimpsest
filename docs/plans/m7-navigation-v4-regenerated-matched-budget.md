# M7 navigation v4: regenerated corpus, matched training-and-selection clock

> **Status:** prospective, documentation-only draft (7 November 2026, base `eb6b48d`),
> revised after independent review (APPROVE WITH CHANGES). Nothing here authorizes source
> work, corpus generation, Torch/MuJoCo import, training, simulation, scene generation or
> held-out access. Every stage needs its own reviewed execution manifest and an explicit
> owner GO. The machine-readable
> [protocol](m7-navigation-v4-regenerated-matched-budget-protocol.json) is authoritative.

## Relationship to v3 (supersedes nothing)

[V3](m7-navigation-v3-matched-budget.md) remains immutable history: **unexecutable, lost
inputs**. Its attempts [1](../reports/m7-navigation-v3-matched-budget-attempt-1.md)
(argv guard) and [2](../reports/m7-navigation-v3-matched-budget-attempt-2.md)
(`ModuleNotFoundError: httpx`) are consumed. Its corpus (`47c4523c…`, `402d2676…`,
`historical-arrays.npz`, ~1.79 GB raw) and the recovery learner checkpoints were lost with
the former `brain` checkout ([feasibility](../reports/research-feasibility-2026-11-07/README.md)).
V4 does not amend, repair, retry or reinterpret v3 or any v2 result. The v2 development
failure (augmented 0/4 on every seed) stands.

**The regenerated corpus is a new corpus, not v3's.** Producers embed `uuid4` run IDs,
`perf_counter` latencies, absolute paths and elapsed times, and they render features
through EGL. No repeat run has ever matched hashes. The advice learners are retrained from
regenerated data, so advice rollouts and source lengths will differ. V4 pins new hashes
**after generation and before any training reads them**.

## Question, intervention and what is new

Question: under one deterministic matched training-and-selection clock on the unchanged
ORIGINAL MaleCNS topology, does the **regenerated-then-frozen** advice-augmented corpus
meet the unchanged fresh-scene simulator capability gates? The old-corpus arm is a paired
descriptive comparator.

The clock is v3's, unchanged:

- every model gets **46,080 real loss-bearing rows in 1,440 Adam updates of exactly 32
  rows**, and only the terminal update-1,440 checkpoint is selectable;
- Hamilton largest-remainder tails, seeded cyclic remainder segments, resets at
  source/sweep/wrap, multi-fragment packing, no padding and no dropped rows;
- ORIGINAL graph `5aba0fef…`, cell `707cba79…`, seeds 10/11/12, Adam lr .001, gradient
  cap 1, the v3 loss, float32 CPU with one thread.

**New relative to v3:** (1) the regenerated corpus and pins; (2) regenerated advice
learners (S0d), so advice rows come from different learners; (3) the project interpreter
and the MuJoCo 3.3.6 / EGL / Mesa / GPU-driver stack; (4) source drift between producing
commits and HEAD; (5) the S0 pin overlay; (6) a re-pinned v4 trainer and a new evaluator;
(7) the remainder-hash domain string `M7-NAV-V4-REGEN-MATCHED-BUDGET-1`; (8) post-pin
derivation of every per-arm array (N, `q,r`, allocations, totals, starts).

The 1,440-update anchor stays a predeclared constant. Under the regenerated N it no
longer equals the old arm's v2 20-epoch full fit, and that is disclosed.

**Inference scope.** The within-v4 old-vs-augmented contrast stays unconfounded by the
new elements: both arms share the regenerated prefix, the clock, the learners and the
runtime. A difference between v4 and v2 can **no longer be attributed to the clock**,
because corpus, learners, runtime and source changed jointly.

## Thresholds (unchanged; no relaxation)

- **Development:** all 24 owners must be admitted and normal, and **each augmented seed
  independently must reach ≥3/4 goals** (`last_outcome.reason == "goal"` within 600
  ticks) on fresh scenes.
- **Held-out:** reachable only after a development pass **and a separate explicit owner
  GO**. All 48 owners must be normal, with **≥6/8 per augmented seed**.
- There is no pooling, winning seed, retry, replacement case, rescue, threshold or
  budget change.
- A natural non-goal is a functional failure. A wall-clock kill or timeout is an
  **operational failure**, never a non-goal: it stops v4 and does not score.

## Stages

Each stage requires, in this order: a reviewed execution manifest (hash-bound source
closure, argv/env/cwd, inputs, outputs, `RuntimeMaxSec`, `CPUQuota`); lane admission; an
explicit owner GO naming the manifest digest; and a durable fsynced reservation before
any input is opened. One attempt per stage. The first fault is retained, ends v4, and
leaves later stages `not_started`. Any further work needs a new protocol version.

| Stage | Content | Producer, run from a detached worktree at |
| --- | --- | --- |
| P | Dependency-closure import probe | each stage's worktree + project venv |
| S0a | Teacher **development stage only**: train 1000–1007, recorded-dev 1008–1011 (not 1012–1015) | `collect_male_teachers.py` @ `cc1cea9` |
| S0b | Recovery first-cycle collection, seeds 2100/2101 | `collect_male_recovery.py` @ `c382c86` |
| S0c | Recovery data preparation | `prepare_male_recovery_data.py` @ `7d5fc1f` |
| S0d | Recovery training; ORIGINAL seeds 10/11/12 become the advice learners | `train_male_recovery.py` @ `19d275d` |
| S0e | Advice collection, scenes 3100–3103 × learners 10/11/12 | `collect_male_navigation_v2.py` @ `736e0cf` |
| S0f | Navigation data preparation (historical reader root @ `217cbee`) | `prepare_male_navigation_v2.py` @ `4ecb354` |
| S0z | Pin + independent compact audit (inside a census unit) | new audit |
| S1 | Six-model matched-clock training | v4 trainer (re-pinned from `train_male_navigation_v3.py`) |
| S2 | Fresh development, 24 owners | v4 evaluator (new) |
| S3 | Fresh held-out, 48 owners, separate GO | v4 evaluator, held-out route |

**P (import probe).** Run in the project interpreter (`palimpsest/.venv`: Python 3.11.15,
NumPy 2.2.5, Torch 2.9.0+cu128 CPU, MuJoCo 3.3.6), once per entrypoint and from that
stage's worktree. Each fresh `python -I` child imports the transitive closure without
calling `main`. It records `sys.modules`, versions, per-producer thread environment
(recovery collector `OMP_NUM_THREADS=2`, navigation collector 1, Torch 1), CUDA-uninitialized
state, and EGL vendor/Mesa/GPU-driver identity from one offscreen context created with no
model loaded. It also checks whether a producer asserts an interpreter path. P must pass
the v3 failure chain, which runs from the v2 trainer through recovery and runtime-verification
modules to `verify_endurance.py` and `import httpx` (`httpx==0.28.1` is locked). P opens
no input and is not a scientific attempt. If P fails, v4 is blocked. An environment repair
and any re-probe need a new manifest and GO, and every probe is charged.

## Stage 0 route: producing-commit worktrees plus a data-only pin overlay

**Finding.** The producers guard two kinds of pins:

- **Source-behaviour pins.** Examples: the recovery reader's six-file `source_code_sha256`
  (`artifacts.py`, `male_research.py` and `records.py` differ at HEAD); the
  navigation-data `historical_identity` (HEAD `217cbee`, a 70-file Python inventory and
  per-file code pins); and `FITTER_SHA256`.
- **Data/path pins to lost artifacts.** `402d2676…`, `72da787b…`, `01251434…`, per-case
  `result_sha256`, the recovery index `cf50fd2f…`, `pair_report_sha256`,
  `producer_root ../task-phases`, absolute `brain` `immutable_inputs` paths, historical
  `feature_target_sha256` bytes, and `47c4523c…` in the v3 trainer.

The JSON `stage_0_pin_inventory` lists every pin with its file:line, field and class.

**Recommended route.** Run each S0 producer from a **detached worktree at its producing
commit**. All seven commits, including `217cbee`, exist locally, so source-behaviour guards
pass on unchanged bytes. A reviewed v4 driver then imports the unchanged producer module
and rebinds only data/path constants before any dependent import or read. It points them
at v4 copies of the pinning documents, which differ only in data/path fields. Producer
file bytes never change. Bounded local setup must initialize `upstream/fly-gym` at
`8d96459` and assets in each worktree. **Fallback:** running at HEAD would require
source-pin overrides too, which the reviewer and v4 both reject. If the recommended route
is rejected, v4 is blocked at Stage 0.

**Pin rule.** Each S0 sub-stage hashes all of its outputs into a v4 pin record. The next
manifest binds those pins before it opens any input. S0z freezes the v4 data-manifest SHA
and the source rosters, and S1 cannot start before S0z passes review.

**Structural admission (S0z).** The unchanged preparer decides source inclusion, and the
result must have v3's shape: old arm = 8 teacher train sources (1000–1007) then 2
recovery sources (2100/2101); augmented = that prefix + 12 advice sources (`3100…3103` ×
`10,11,12`); recorded-dev = 4 sources (1008–1011); zero held-out rows; executed-action
targets for old rows and recorded `nav_advice_action` for advice rows. Any other shape
blocks v4. There is no filtering, substitution or recollection. Rewired
by-product fits from S0d are retained but never evaluated or cited.

## Fresh scene IDs

Candidates: **development 3160–3163**, **held-out 3170–3177**.

The drafting screen covered `docs/`, `data/manifests/`, `scripts/`, `src/`, `tests/` and
`paper/` at `eb6b48d`, plus `docs/` and `data/manifests/` on all 248 local/remote refs.
The independent reviewer then verified both ranges clean across all 186 distinct ref tips,
including `scripts/`, `src/`, `tests/` and `paper/` (JSON `candidate_screen`). Hits were
incidental byte sizes, hash substrings or SWC coordinates, never a scene/seed/family ID.
IDs on record: MaleCNS 1000–1015, 1100–1103, 1200–1207, 2100–2101, 3100–3103, 3110–3113
and the v3-reserved, never-generated 3120–3127 and 3130–3133; puck 5990–5994, 6000–6019,
6100–6103, 6110–6113, 6120–6123 and 6200–6207.

The screen is not proof. Each S2/S3 preparation must repeat the ID-roster scan over all
refs, worktrees and retained roots before generation. After generation it must reject
canonical-scene, scientific-initial and payload duplicates against every generatable or
retained prior scene, including all S0 scenes. Never-generated reserved IDs are compared
by ID only and never generated. The lost `brain` registries cannot be scanned; that
limitation is reported.

## CPU lane, cost table and admission

Lane: MaleCNS, **14,400 CPU-s**. Prior charge: **1.832 CPU-s**, the systemd service CPU
of v3 attempt 1 (0.431) plus attempt 2 (1.401); the feasibility ledger said 0, so v4
charges it conservatively. Remaining at start: **14,398.168 CPU-s**.

**Census and limits.** Every stage, including S0z and all reviewer audits, runs inside a
transient systemd unit and is charged from `cpu.stat usage_usec`. Unknown tails (processes
outside units, GPU/EGL driver time) are reported as unknown, never excluded or imputed.
Each unit sets `RuntimeMaxSec` to the stage's kill target and `CPUQuota=k×100%`, where k is
the declared CPU concurrency: k=2 for S0b (`OMP_NUM_THREADS=2`) and k=1 elsewhere. A
stage's worst-case CPU is therefore k × kill target.

**Throttling risk (I4).** `CPUQuota` can stretch the wall time of supervisors with
samplers or extra threads whose internal deadlines were calibrated unthrottled. Review of
each manifest must justify k. A kill caused by throttling is an operational failure.

**Prior figures are wall seconds**, and transferring them to CPU is an assumption.

| Stage | Expected (prior wall s; source) | k | Kill target s (basis) | Worst CPU s |
| --- | ---: | :-: | --- | ---: |
| P | ≤30 (estimate) | 1 | 120 (declared) | 120 |
| S0a | 277.697 (Stage-A supervised) | 1 | 1,260 (`collection_limits` 1,200 dev + 60 grace) | 1,260 |
| S0b | 15.565 (coverage v3 outer) | 2 | 480 (`outer_timeout_seconds`) | 960 |
| S0c | 13.701 (launch/cleanup) | 1 | 180 (`preparation_limits.seconds`) | 180 |
| S0d | 194.681 (enclosing) | 1 | 2,160 (stage enclosing bound) | 2,160 |
| S0e | 543.022 (launcher) | 1 | 2,240 (2,210 normal-return + 30 kill margin) | 2,240 |
| S0f | 79.460 (pre-publication) | 1 | 263 (nominal failure envelope) | 263 |
| S0z | ≈82 (sum of prior root audits) | 1 | 300 (≈3.7× that sum) | 300 |
| S1 | 240–480 (v3 estimate) | 1 | 2,160 (v3 enclosing) | 2,160 |
| S2 | 988.524 (v2 host-observed) | 1 | 4,430 (v3 enclosing) | 4,430 |
| S3 | ≈1,977 (2× S2) | 1 | 8,750 (v3 enclosing) | 8,750 |
| **Total** | **≈4,682 (32.5 %)** | | | **22,823** |

**Admission rule.** Before each stage, compute remaining = 14,400 − 1.832 − Σ census CPU of
every earlier v4 stage, including failures and audits. Admit only if the stage's worst CPU ≤
remaining. Otherwise stop and report **blocked on budget**, with no threshold or limit
change.

- Worst case through S2 is **14,073 ≤ 14,398.168** (slack 325.168), so S0–S2 are
  admissible even if every stage hits its limit.
- **S3 is admitted only if the measured charge through S2 is ≤ 5,648.168 CPU-s.**
- Expected cost through S2 is ≈2,705 s.

**Storage.** Producer caps apply to S0; S2 is 4 GiB and S3 is 8 GiB. The free-space floor
is 1 GiB, measured at run time. Raw deletion stays disabled.

## Before execution freeze (summary; JSON is exact)

Tests must show that the overlay rebinds only the listed data/path pins (every read
site sees the v4 value) and that producer bytes and source guards are unchanged; that
the v4 pinning documents differ only in declared fields; that schedule derivation is
pure and replayable; that the re-pinned trainer refuses `47c4523c…` and unpinned
corpora; that the evaluator gates hold (3160–3163 order, 3/4 per seed, held-out
unreachable); and that the kill-target, CPUQuota and census ledgers work. Planned files
(overlay driver, v4 pinning-document copies, v4 trainer, v4 evaluator, each with tests)
and execution stops are listed in the JSON.

## Estimands and what this protocol does NOT claim

**Primary:** the absolute fresh-scene simulator capability of the frozen v4
augmented-corpus, ORIGINAL-topology, matched-clock procedure under the per-seed gates.
**Secondary (descriptive):** old vs augmented as complete procedures.

V4 makes no claim about **topology** (no rewired model is evaluated, compared or cited),
**biology** (no correspondence to MaleCNS or *Drosophila* neural function or behavior) or
**physical** behavior (no rover, hardware, contact-safety or operator-readiness claim).
Nor does it claim mechanism inside the clock, advice correctness or student
observability, equivalence with or attribution relative to v2/v3, generality beyond these
seeds, scenes and budget, automatic R3, or novelty.

## Related work and rationale

- **DAgger** (Ross, Gordon & Bagnell, AISTATS 2011, PMLR 15:627–635). The augmented
  corpus is one fixed round of teacher labels on learner-visited states. V4's analytic
  teacher is history-dependent (a private recovery counter advances per query), unlike
  DAgger's state-wise expert. V4 runs no iterated no-regret loop and inherits no guarantee.
- **FLYNN** (Wang & Chen, arXiv:2607.00025; `github.com/ben-gitdev/fly-gym`). The pinned
  upstream `8d96459` supplies the environment and cell: a two-wheeled, two-camera MuJoCo
  robot trained by DAgger-style imitation, with connectivity from FlyWire FAFB v783. V4
  swaps in a reduced MaleCNS graph.
- **MaleCNS connectome** (Berg et al., bioRxiv 2025, doi:10.1101/2025.10.09.680999). This
  is the source of the reduced neighborhood (`male-cns:v1.0` in the graph manifest).
- **Lappalainen et al.** (*Nature* 634:1132–1140, 2024) fix structure from measured wiring
  and train the remaining parameters. **Dorkenwald et al.** (*Nature* 634:124–138, 2024)
  give whole-brain FlyWire context. Neither licenses a neural-activity or biological claim
  here.
- **Budget-controlled comparison.** Lucic et al. (NeurIPS 2018) showed that apparent GAN
  differences shrink under matched hyperparameter-search budgets. Dehghani et al.
  (ICLR 2022) warn against single cost indicators. V4 matches rows *and* updates, and
  reports both CPU and wall time.

NeuroMechFly v2 (Wang-Chen et al., *Nature Methods* 2024) simulates the legged fly body
and is **not** this environment. It is cited only to mark that distinction.

## Open owner decisions (recommended defaults)

1. **Stage 0 route.** Recommended: producing-commit worktrees plus a data/path-only
   overlay. Rejecting it blocks v4.
2. **Rewired by-products in S0d.** Recommended: run unchanged, retain, never evaluate or
   cite.
3. **Prior charge.** Recommended: count the 1.832 CPU-s.
4. **Scene IDs.** Recommended: adopt 3160–3163 and 3170–3177.
5. **S0 GO granularity.** Recommended: one GO per S0 sub-stage.
6. **Reserve for unknown tails.** Recommended: none; report the tails as unknown.
7. **CPUQuota multipliers.** Recommended: k=2 for S0b and k=1 elsewhere, unless manifest
   review shows a need.
8. **S0e kill target.** Recommended: 2,240 s. The cap that keeps S0–S2 admissible at their
   limits is 2,565 s.

`qualification_claims` is empty.

## Owner resolution — 8 November 2026

All open decisions above were resolved by the owner to their recommended defaults (puck: D8 = 120 s hard audit kill; D9 = S1 before S0). Independent manifest review: a fresh AI reviewer agent, recorded as AI review, not human acceptance. Machine-readable record: `owner_decisions_resolution` in the protocol JSON. Each stage still requires its own reviewed execution manifest and explicit owner GO.

## Amendment 1: v4 producer ports (draft, 8 November 2026; awaiting owner decision A1)

Revision 2 applies the independent review of Amendment 1 (APPROVE WITH CHANGES). The
exact per-hunk record is in JSON `amendment_1`.

**Why the overlay fails.** Milestone 1 (`fbaa421`) showed that the owner-approved route,
an in-process overlay that rebinds only data and path pins inside producing-commit
worktrees, cannot reach S0e or S0f:

- **Producers re-launch themselves.** `collect_male_navigation_v2.py:466` and
  `prepare_male_navigation_v2.py:422` (under `-I`) start child processes.
- **Pins are written inline in code.** The index path is inline at
  `collect_male_navigation_v2.py:326,458,485`; the plan is read at import time (`:50`);
  `male_recovery_research.py:114,117` hard-codes the recovery-learning SHA `091c4e98…`;
  and v1 `collect_male_navigation.py:27`, called through S0e's `source_pins`, hard-codes
  the study-plan SHA `a3612cdc…`. That plan pins four files whose bytes change in v4.
- **Row counts are asserted exactly.** See the hunk list below.
- **The S0d controller is lost.**
- **No v4 stage produces seven data-v2 inputs.** They came from the v2 launcher, host
  and audit steps, whose scripts were in the lost `runs/`.

**This is a source-behaviour change.** The owner chose a data/path-only Stage 0
(`owner_decisions_resolution.choices.1_stage0_route`), so this needs a **new explicit
owner approval (A1)**. The resolution record is not rewritten.

**Port trees.** A port tree is a **committed v4 branch: the producing commit plus only the
listed hunks.** Ports keep their original relative paths, so
`git rev-parse HEAD` (in `source_identity`, `historical_identity` and the terminal head
gates) reports the port commit. v4 pin documents are passed in by path; they are never
committed into a port tree. S0a (`cc1cea9`) and S0b (`c382c86`) run unchanged.

| Tree | Base | Ported files | Used by |
| --- | --- | --- | --- |
| T-c | `7d5fc1f` | `prepare_male_recovery_data.py` | S0c |
| T-d | `19d275d` | `prepare_male_recovery_data.py` (reader import), `train_male_recovery.py` | S0d |
| T-e | `736e0cf` | `male_recovery_research.py`, `collect_male_navigation_v2.py`, `collect_male_navigation.py` (+ the ported reader, if review finds it imported) | S0e |
| T-h | `217cbee` | `prepare_male_recovery_data.py` | S0f historical reader root |
| T-f | `4ecb354` | `prepare_male_navigation_v2.py`, `prepare_male_recovery_data.py` (parent `old` import at `:75`, check at `:430`) | S0f |

**Hunk classes.** No other behaviour change is permitted.

- **H1, externalized literal.** A path or pin literal is read from a v4 pin document or
  a CLI argument, with read timing unchanged (including import-time reads). This covers
  `collect_male_navigation.py:26-27` (PLAN/PLAN_SHA → a v4 copy of
  `m7-navigation-study-protocol.json`).
- **H2, relaunch target.** Because ports keep their original paths and relaunch via
  `__file__`, the hunks at `:466` and `:422` are **empty**. Tests still prove that the
  child is the port.
- **H3, count → structural invariant.** The hunks and their replacements:

  | Site | Hard-coded value | Replaced by |
  | --- | --- | --- |
  | `prepare_male_recovery_data.py:90,198` | 67 per recovery source | S0b per-source pins |
  | same file, `:140` | 2117/1228/0 | S0c pins |
  | same file, `:160` | 134 | S0b pins |
  | same file, `:177` | 1983/1228 | S0a pins |
  | `train_male_recovery.py:77,123` | 2117/1228 | S0c pins |
  | `train_male_recovery.py:80` | windows `[32,32,3]` | windows derived from each pinned recovery length (32-row chunks + remainder) |
  | `male_recovery_research.py:71,73,85` | same values, inside `_gate`/`_history` (run in S0e) | same derivations |
  | `prepare_male_navigation_v2.py:327` | 5080 | S0e pins |
  | same file, `:430` | 2117/1228 | S0c pins |
  | same file, `:464` | 7197/1228 | S0c train + S0e ticks |

  The original numbers survive only as descriptive `v2_reference_counts`.
- **H4 is now a declared-field change, not a code hunk.** It rewrites the data-v2 copy's
  `source_binding/old_historical_reader/{root, head, all_tracked_project_python_inventory/{count, canonical_map_sha256}, adapter_sha256, code}`
  to point at T-h, and adds `source_binding/navigation_producer_commit` (checked at
  `:338`), which is set to T-e.

**Structural invariants.** Every port must enforce:

- the old arm is 8 teacher train sources (1000–1007) followed by 2 recovery sources
  (2100, 2101);
- the augmented arm is that old prefix followed by 12 advice sources in scene
  `3100…3103` × learner `10,11,12` order;
- there are 4 dev sources and 0 held-out rows;
- there are 14 old-manifest sources and 26 combined;
- there are 12 collection owners and 2 recovery owners;
- every length is greater than 0, each recovery source is at most 120 rows, and each
  advice source is at most 600 rows;
- **per-source, order-preserving equality** with the upstream v4 pin records. Matching
  sums alone is not enough.

**Pins and documents added** (staged in `declared-fields.json` under
`amendment_1_pending`; not yet active, because the copies are unchanged):

- the recovery-index pins `training_source_code` and `training_source_commit`, checked at
  `male_recovery_research.py:47,64,109`;
- a new v4 study-plan copy;
- in the contact-v2 copy, the `prior_version` cascade: `protocol_path`, `protocol_sha256`
  and `collector_sha256`, checked at `collect_male_navigation_v2.py:42`;
- the stale `counts` field in the data-v2 copy. It is copied into the S0f output at
  `:470`, so it is now declared and pinned from S0c/S0e;
- the recovery-learning copy's `counts`, `recovery_ticks_each` and `recovery_windows`,
  now declared and pinned from S0a/S0b.

**Reconstructed controllers** are new source under full review, bound to the surviving
evidence:

- **S0d controller.** `run_male_recovery_training_v4.py` runs seeds 10, 11 and 12 once
  each, in order. It is bound to `docs/reports/m7-recovery-training.{md,json}` at
  `217cbee`: a 0.25 s PID/start sampler; a five-part inventory (355/122/181/16/7); pair
  deadlines of 600 s internal / 660 s outer; stage deadlines of 2,100 s internal /
  2,160 s enclosing. It emits the full `_gate` field set: terminal `status`, `head`,
  `inventories_unchanged`, `completed_pair_content_unchanged`, before/after inventory,
  `cleanup{sampler_stopped, sample_errors, forced_signals, survivors}`, and
  `pairs[].supervision{status, returncode}`. The outer supervisor reports `completed`
  with `returncode` 0 and `elapsed_seconds` ≤ 2,160.
- **S0e launcher.** `run_male_navigation_collection_v4.py` is bound to
  `docs/reports/m7-navigation-collection-v2.md`: a 2,210 s normal-return bound, inner and
  outer samplers, and inventories. It emits the exact `admit_collection` fields at
  `prepare_male_navigation_v2.py:331-344`.
- **S0e-D drain receipt.** Built from the systemd unit's exit status and an empty cgroup.
- **S0e-A root raw audit.** Uses the v2 root-audit scope and must record a `passed`
  status, which S0z checks.
- **S0e-I index publisher.**

**Tests before freeze.**

- A diff-restricted review per tree, which regenerates the diff and requires an exact
  match with the hunk manifest.
- **Function-level** behaviour-equivalence tests for S0c, S0f and `_gate`: original pins
  are rebound in-process, and synthetic fixtures satisfy the original counts.
- Negative fixtures: off-v2 lengths, bounds, order and `PENDING-` values.
- Tests that each relaunched child is the port, and that import-time reads touch only v4
  documents.
- Controller fixtures, and P coverage of every port and controller.

**Budget rules.** Every unit sets `TimeoutStopSec` ≤ 5 s, and its worst-case CPU is
k × (kill target + 5). Reviewer audits run inside the unit they review, within its kill
target; they are never separate budget lines. If either rule is not met, the claim that
everything fits even at worst case is withdrawn. The 30 s limits for S0e-D and S0e-I
**need fixture measurement before freeze**. S0c has no controller.

| Stage | Expected (wall s) | k | Kill + stop (s) | Worst CPU (s) |
| --- | ---: | :-: | ---: | ---: |
| P / S0a / S0b / S0c | 30 / 277.697 / 15.565 / 13.701 | 1/1/2/1 | 125 / 1,265 / 485 / 185 | 2,545 |
| S0d (incl. controller) | 194.681 | 1 | 2,165 | 2,165 |
| S0e (incl. launcher) | 543.022 | 1 | 2,245 | 2,245 |
| S0e-D / S0e-A / S0e-I | ≤5 / 43.100 / ≤5 | 1 | 35 / 155 / 35 | 225 |
| S0f / S0z | 79.460 / 82 | 1 | 268 / 305 | 573 |
| S1 / S2 / S3 | 480 / 988.524 / 1,977 | 1 | 2,165 / 4,435 / 8,755 | 15,355 |
| **Total** | **≈4,734.75** | | | **23,108** |

Worst case through S2 is **14,353 ≤ 14,398.168** (slack 45.168), so every stage through
development stays admissible even at worst case. That holds only while the S0e kill
target is ≤ 2,285 s; the chosen 2,240 s fits. **S3 is admitted only if the measured charge
through S2 is ≤ 5,643.168 CPU-s.** S3's worst case is now 8,755, which lowers the ceiling
by 5 s from Amendment 1's draft.

**Decision A1** (recommended: **approve**). Should S0c–S0f run on committed v4 port trees
(producing commit plus only H1–H3 hunks; H2 empty), with the H4/pin changes as declared
fields, reconstructed S0d/S0e controllers bound to the surviving evidence, and
diff-restricted review plus function-level equivalence tests? **Alternative:** keep
data/path-only, and v4 is **blocked at S0e**.

**Implementation follow-ups** (not done here):

- Create the v4 study-plan copy and regenerate the pin copies with `PENDING-` placeholders
  for the `amendment_1_pending` fields.
- Update the hard-coded study-plan pin in `regenerate_male_navigation_v4.py:118` and the
  test's `PROTOCOL_SHA` (`tests/test_male_navigation_v4_overlay.py:22`); resealing
  `declared-fields.json` changes its `protocol_sha256`.

Thresholds, the matched clock, scene IDs, the lane cap and v3 are unchanged.
