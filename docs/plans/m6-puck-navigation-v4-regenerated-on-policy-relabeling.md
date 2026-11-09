# M6 puck navigation v4: one on-policy relabeling round on regenerated inputs

> **Status:** prospective documentation only, drafted 7 November 2026 at `eb6b48d`. It authorizes no
> simulator, collection, fitting, scene minting, registry access, model loading, Torch or MuJoCo import,
> development, or held-out access. The [machine-readable protocol](m6-puck-navigation-v4-regenerated-on-policy-relabeling-protocol.json)
> is authoritative. Every stage still needs a reviewed execution manifest and an explicit owner GO.

## Why v4 exists

[v3](m6-puck-navigation-v3-on-policy-relabeling.md) (sha256 `355e2e3a…`, JSON `fe8b2615…`) is
**immutable and unexecutable**. Its inputs are lost: the seed-21/22/23 `checkpoint.npz`/`protocol.json`/`report.json`
and the teacher-collection-v2 recordings lived in the deleted `brain` checkout
([feasibility record](../reports/research-feasibility-2026-11-07/README.md)). No v3 stage ever ran. The owner
directed (2026-11-07) that inputs which cannot be reconstructed bit-for-bit need a new prospective protocol.
v4 is that protocol. v3, its numbers and all earlier results stay unchanged as history.

v4 asks **the same scientific question with the same intervention** as v3. The only differences are listed
here. (1) Stage 0 regenerates the teacher corpus and base students. (2) New scene IDs are disjoint from all
earlier IDs. (3) A lane admission rule replaces v3's worst-case budget overflow. (4) Retention admission uses
measured bytes. (5) The held-out roster is an open owner decision (D1).

## Question, intervention and estimand (unchanged from v3)

Does one fixed round of the unchanged analytic teacher's labels on states visited by the base puck students
21/22/23 produce three freshly fitted models that each reach at least 3/4 goals on fresh development scenes?

The intervention works like this. The base students act. The teacher labels each pre-action state once, and
only the student's action advances the world. Every admitted row is appended to the base training split, and
three fresh models are fitted with unchanged settings. The fit is `9→32 tanh→32 tanh→2 tanh` with 1,442
float32 parameters, float64 targets and float64 `0.4` scaling. The loss is unweighted normalized MSE. Training
runs 30 epochs with batch 64, the seeded permutation, Adam `1e-3`, weight decay 0 and gradient cap 1, on CPU
with one thread. Selection is the earliest strict recorded-dev minimum. The study does not use filtering,
weighting, teacher takeover, blending, a second round, or warm starts. The estimand is the whole fixed
aggregation procedure. It cannot separate targeted-state coverage from added data volume, other new states,
or extra optimizer updates.

## Thresholds and gates (unchanged; no retries, replacements or relaxation)

- **Collection gate (v3):** all 12 owners must be normal and admitted, and each collector model 21/22/23 must
  produce at least one row in the motivating condition. The condition is own-mode approach, contact true,
  axial distance in `[0.35,0.63]` m, |lateral| ≤ `0.06` m, and behind-point distance > `0.08` m. Zero rows
  for any model is a valid falsification: keep the data and do not train.
- **Development gate:** all 24 owners must be normal, and **each relabeled-v4 model must independently reach
  ≥3/4 goals** (`final_state.reason == 'puck_goal'` within 600 ticks). The base-model arm is descriptive.
  Pre-registered: if a seed's **base** arm also reaches ≥3/4 on 6520–6523, that seed's relabeled pass is
  reported as **not attributable** to the intervention. The gate verdict is still computed as written.
- **Held-out gate:** runs only after a passed development report, a separate held-out manifest, review and an
  explicit owner GO. All 48 owners must be normal, and each relabeled-v4 model must reach **≥6/8**.
- A wall-clock timeout is an operational failure, never a natural non-goal. Stop on the first failed gate. A failed coverage gate forbids training. Failed training or mechanism
  admission forbids development. A failed development gate keeps held-out locked.

## Stage 0: regenerate inputs, pinning each output before the next stage uses it

The interpreter is `/home/utkarsh/Work/shraddha/palimpsest/.venv` (`pyvenv.cfg`: CPython 3.11.15; dist-info
NumPy 2.2.5, Torch 2.9.0, MuJoCo 3.3.6; nothing was imported for this draft). Fitting and inference run on
CPU with one thread. Hashes are pinned in the order the bytes are produced:

- **S0a teacher corpus.**
  - Runs the existing `scripts/collect_puck_teachers.py` (`c0218642…`, unchanged since producer `69fd445`)
    under the unchanged learning-v2 protocol (`bfdd047c…`).
  - 20 owners: 6000–6015 train and 6016–6019 recorded-dev. The unchanged complete-batch admission
    requires every owner to reach a natural goal; each train owner needs ≥32 ticks, ≥10 contact intervals
    and ≥10 terminal zero labels.
  - **S0a's own close publishes the gate-report hash and the train/recorded-dev feature and target array
    hashes and row counts (`N_train`, `N_dev`).**
  - The lost outer launcher (`b23b4c99…`) is re-authored as a thin launcher with the same bounds
    (1500/1560/+15/1580 s) and reviewed.
  - The collector sets `OMP_NUM_THREADS=2`.
- **S0b base students.**
  - Runs the existing `scripts/train_puck.py` (`a1dfc8c4…`). Since `82e2bd9` it has only gained an opt-in
    balanced path; the default path is used. Bound: 680 s outer.
  - **It accepts only the S0a-published bytes**, through its existing `expected_sha256` argument.
  - The trainer is deterministic: one thread and `use_deterministic_algorithms`. The fit ladder reproduced
    every historical epoch loss exactly from identical inputs.
- **S0c pin and offline regression.**
  - **Pins the three bundles and a new v4 model index.** The historical
    `m6-puck-student-models-v1.json` is never edited.
  - Later stages admit only bytes pinned by S0a or S0c.
  - Descriptive only: compares the new array hashes with the tracked ones (`4a679026…`/`f46827ed…` train,
    `b502f4b6…`/`4bcf8d83…` dev), and the 90 epoch losses and selected epochs 30/27/26 with
    `m6-puck-training-v2.json`.
  - Counts **motivating-condition rows in the regenerated teacher corpus** (historically 0).
- **S0d base-model regression on 6100–6103 (descriptive; D3).**
  - The regenerated base students run the pinned 12-owner `m6-puck-student-development-v1` evaluation. The
    only change is a v4 model-index binding. Its pinned bound is 1,200 s inner, TERM at 1,260 s with 15 s
    grace, and 1,280 s enclosing.
  - Each owner is compared with the recorded table: ticks, end reason, end goal distance, contact
    intervals. Historically every model scored 0/4 and every owner ran 600 ticks.
  - Also reports student-side motivating-condition row counts (historical diagnosis: 1,575) and the maximum
    owner wall and CPU under the one-CPU quota.
  - Differences are reported but never stop the study. An operational failure does stop it.
  - **S0d cannot change any later stage**: data, seeds, scenes, order, thresholds and selection stay as
    written.
  - **Margin calibration:** if any S0d owner's wall time exceeds 90 s (50 % of the 180 s per-owner bound),
    the study is reported **blocked** before S3. Changing a bound needs a versioned protocol.

**Honest reproduction statement.** The new bytes will differ from the old pins. The causes are `uuid4` run
IDs, `perf_counter` latencies, elapsed times, absolute paths, EGL native rendering and possible container
timestamps. Hash equality has never been shown for any repeat run. Equality or inequality is reported but is
never a gate. If `N_train ≠ 5,710`, the data and update maxima are recomputed mechanically: `N_train + 7,200`
rows and `ceil(rows/64)` updates per epoch.

## Fresh scene IDs and disjointness

Puck IDs already used in tracked docs are 6000–6019, 6100–6103, 6110–6113 and 6120–6123, and 6200–6207. The
6110–6123 IDs were v3 reservations, never minted but treated as occupied. Other lanes use 1000–1015,
1100–1103, 1200–1207 and 3100–3133. **Every historical puck ID is ≤ 6207.**

| Role | Proposed IDs | Geometry |
| --- | --- | --- |
| On-policy collection | `6510–6513` | v3's reviewed 8-slot domain (`puck_on_policy._PARAMETER_DOMAIN` slots 0–3); never minted or run |
| Closed-loop development | `6520–6523` | same domain, slots 4–7 |
| Held-out (D1, open) | `6200–6207` authored task-v5 rows, never run, **or** fresh `6600–6607` | authored rows unchanged, **or** a new 8-slot domain frozen at source freeze and minted (S8a) only after the held-out GO |

**Planning screen (not proof).** At HEAD, a context-filtered scan of tracked `docs/src/scripts/tests` files
checked seed, scene, layout, split, held-out, roster and reservation fields. It found zero hits for all 16
candidates. Positive controls behaved as expected: 6110 (100 hits), 6120 (16), 6200 (57), 3130 (10). A
`git grep` over the 186 unique tips of 248 refs also found zero hits; the positive control 6120–6123 found
37 hits on 40 tips. Lines were truncated to 400 characters.

**Preparation-time proof (S1).**
- S1 runs v3's contamination admission with one frozen change. It scans:
  - every reachable commit under local and remote refs;
  - fresh remote advertisements and every worktree;
  - typed scene fields in tracked documents and surviving raw registries.
- It rejects any exact ID reuse outside v4's lineage and atomically publishes one reservation covering every
  v4 ID.
- **Intentional reuse, not collisions:** S0a regenerates 6000–6019 and S0d replays 6100–6103. Both are
  listed exceptions.
- **Frozen lost-root exception.** The deleted `/home/utkarsh/Work/shraddha/brain` root, including every
  `.worktrees/*/runs/` registry, is declared lost and is excluded from inventory by name. It is never treated
  as clean.
  - *Risk:* an ID or payload that was recorded only in those lost raw registries would go undetected.
  - *Mitigation:* every executed puck roster is in tracked reports, all of them ≤ 6207, and v4's
    collection and development IDs are ≥ 6510.

**Payload disjointness.**
- **S2** (after S0) mints the 8 collection and development payloads. It rejects any duplicate canonical
  scene, scientific initial state or payload against:
  - S0a's regenerated train and recorded-dev payloads;
  - authored rows 6100–6103;
  - the other new payloads;
  - authored 6200–6207, but only as the pure comparison under D2.
- **S8a** (only if D1 chooses fresh IDs) checks its 8 held-out payloads against all of the above, the 8 S2
  payloads, authored 6200–6207 (pure comparison) and each other.
- Any collision stops v4. No ID is substituted, and continuing needs a versioned protocol.

## Collection, data, fitting, mechanism, development (v3 rules, renamed)

1. **S3 collection:** scenes 6510→6513 × models 21→22→23, 12 owners, ≤600 ticks each (≤7,200 rows).
2. **S4 data preparation:** the base `N_train` rows, then all admitted rows in fixed scene/model/tick order.
   The recorded-dev `N_dev` rows are used only for epoch selection.
3. **S5 training:** fresh seeds 21/22/23, ≤202 updates per epoch and ≤6,060 per model when
   `N_train = 5,710`. Per-seed bounds stay at 120 s internal and 200 s supervised.
4. **S6 mechanism admission:** relabeled-v4 model 21 on the spent scene row 6510, under v3's four-owner
   contract.
5. **S7 development:** scenes 6520→6523 × seeds 21→22→23 × base then relabeled, 24 owners, with matched
   scientific initial states per scene.

The base students are not refitted after S0b. v3's query isolation, commit-after-step cursor, mode agreement
and failure semantics all apply unchanged.

## Lane admission rule and CPU census (fixes v3's 19,440 s > 18,000 s)

**Census.**
- Each stage runs in its own cgroup-v2 leaf with `cpu.max` set to one CPU. The leaf holds the launcher, its
  children, the `/proc` sampler (keyed by PID and start time) and the audits.
- The sampler runs **inside** the leaf, so its CPU is counted and bounded. It also detects any descendant
  outside the leaf.
- After the leaf is empty, the registrar's reader runs **outside** it. It reads `cpu.stat usage_usec` once
  and adds its own `getrusage` CPU to the charge.
- An *unknown tail* is any of:
  - a descendant found outside the leaf;
  - a failed census read;
  - sampled per-process CPU greater than the cgroup total.

  An unknown tail is reported as **unknown**, never excluded, and it blocks every later admission.
- Audits (local and root combined) run after stage publication. They have a **hard 120 s deadline** (kill at
  120 s). A killed audit is an operational failure.

**Admission.**
- `L` = 18,000 CPU-s for the puck lane.
- `C` = the measured charge so far: 0 per the 2026-11-07 record, re-read at the first stage.
- `W` = (enclosing hard deadline + 120 s audit) × 1 CPU, for every stage.
- A stage is admitted only if all of these hold: no unknown tail so far, `C + W ≤ L`, the retention check
  passes, the manifest has been reviewed, and the owner has given GO.
- Otherwise the stage publishes **blocked** with the numbers. Stages are never reordered, skipped or split
  to make them fit, and caps are never raised.
- A fresh held-out mint (S8a) is admitted **jointly** with S8b.

| Stage | Worst case `W` (CPU-s) | Prior **wall** seconds (not CPU) |
| --- | ---: | --- |
| S0a teacher corpus (20 owners) | 1,580+120 = 1,700 | 159.6 + 30.0 audits (teacher v2) |
| S0b base training (3 seeds) | 680+120 = 800 | 59.8 + 13.3 audits (training v2) |
| S0c pin + offline regression | 240+120 = 360 | none |
| S0d regression on 6100–6103 (12) | 1,280+120 = 1,400 | 194.8 + 26.7 audits (student dev) |
| S1 refs/registry + reservation | 660+120 = 780 | none |
| S2 mint 8 scenes | 1,550+120 = 1,670 | none |
| S3 collection (12) | 2,270+120 = 2,390 | ~195 by analogy; teacher-query cost unknown |
| S4 data preparation | 240+120 = 360 | none |
| S5 training (3) | 710+120 = 830 | 59.8 × ≤2.24 ≈ ≤134 |
| S6 mechanism (4) | 830+120 = 950 | 27.4 (prior mechanism) |
| S7 development (24) | 4,430+120 = 4,550 | 2 × 194.8 + ~46 audits ≈ 436 |
| **Pre-held-out total** | **15,790 ≤ 18,000** | **≈1,277 for stages with priors; others unknown** |
| Held-out, D1 = 6200–6207: S8b only (48) | 8,750+120 = 8,870 → admissible iff `C ≤ 9,130` | ~780 + audits |
| Held-out, D1 = 6600–6607: S8a + S8b | 1,670 + 8,870 = 10,540 → admissible iff `C ≤ 7,460` | ~780 + audits |

Every stage before held-out fits the lane even at its worst case. All priors are wall seconds from single
runs; **no puck process CPU has ever been measured.** The one-CPU quota bounds CPU by wall time, but it may
throttle S0a's two OMP threads. **Any wall-clock timeout is an operational failure and is never scored as a
natural non-goal.**

## Retention (fixes v3's 17.4375 GiB > 16 GiB)

Thresholds and cohorts are unchanged, and nothing is deleted.

1. **Measured-bytes admission.**
   - Before each stage, the measured bytes v4 has retained so far, plus this stage's cap, plus the 1 GiB
     floor, must be ≤ 16 GiB.
   - Measured free space must be ≥ the stage cap plus the floor.
   - Otherwise the stage is blocked.
2. **Caps.**
   - New native stages keep **v3's 160 MiB per owner** and v3's stage caps: S3 3 GiB, S6 1 GiB, S7 4 GiB,
     S8b 8 GiB, plus 256 MiB for S8a. Each cap leaves headroom above owners × 160 MiB for the parent report,
     ledgers and census output: 1,152, 384, 256 and 512 MiB respectively.
   - The 128 MiB figure in the earlier draft came from the *teacher* recorder, not the on-policy recorder, so
     it is withdrawn. Tightening the per-owner cap needs D7 and a synthetic 600-tick measurement of the S3
     recorder before freeze.
   - S0a, S0b and S0d keep their pipelines' pinned caps: 4 GiB, 64 MiB and 3 GiB.
3. **Check after S0, before the next non-S0 stage.**
   - The caps from S1 through S7 add up to 8.4375 GiB, or 9.4375 GiB with the floor.
   - Measured S0 bytes must be **≤ 6.5625 GiB**, so that no stage before held-out can be blocked by
     retention. Otherwise the study stops as blocked. (The earlier 3.25 GiB figure assumed the withdrawn
     128 MiB caps.)
   - Held-out has no static guarantee. It needs measured retained bytes ≤ 7 GiB (6.75 GiB if fresh).
4. **What the expected numbers rest on.**
   - Sourced: S0a measured 0.806 GiB (teacher v2). S0b is bounded by its 64 MiB cap; its checkpoints are
     about 7 KB each.
   - Unsourced extrapolation: about 0.83 GiB each for S0d and S3 and about 1.65 GiB for S7, all at 123,177 B
     per teacher interval. The development report records no byte totals.
   - Compact recording of only what the gates need was rejected. It would need a new recorder mode and
     would weaken the raw-data audits.

## Governance, attempts and source

The owner, Utkarsh, is the single stage-GO authority and registrar
([authority record](../reports/user-authority-2026-11-07/README.md)). Each stage gets its own reviewed,
hash-bound execution manifest. The manifest pins the protocol, the complete transitive source closure, the
interpreter, argv, environment, inputs, caps, deadlines and the cgroup configuration. An independent review
and an explicit GO follow. The default is one GO per stage. Each stage has one durable attempt: a crash,
timeout or partial output consumes it, and there are no retries. Held-out reads (as defined under D2) need their own explicit GO.

The source work reuses the v3 path: `puck_on_policy.py`, the scene registry and inventory modules, the
collection close and ledger modules, and the explicit-layout seam. It adds a versioned v4 ID binding with
v3's IDs treated as occupied and the frozen lost-root exception. It also adds a held-out slot domain, only if
D1 chooses fresh IDs; thin S0 launchers; a v4 model index; the cgroup census, the admission ledger and the
120 s audit kill; and the measured-bytes checks. Synthetic tests must cover
v3's list plus: exact-fit admission accepted and a one-second-over admission refused; joint held-out
admission; unknown-tail blocking; retention boundaries, including the post-S0 6.5625 GiB check; S0 pin-before-use;
and the classification of any timeout as an operational failure. Implementation ends with a
manifest and review before any protected access.

## Related work and rationale

Behaviour cloning trains on the teacher's state distribution, but it is tested on the student's own. Errors
then compound: Ross & Bagnell bound the cost growth as quadratic in the horizon
([AISTATS 2010, PMLR 9:661–668](https://proceedings.mlr.press/v9/ross10a.html)). DAgger
([Ross, Gordon & Bagnell, AISTATS 2011, PMLR 15:627–635](https://proceedings.mlr.press/v15/ross11a.html))
fixes this by aggregating expert labels on learner-visited states over **many** iterations, and its
guarantees apply to that iterated, no-regret setting. v4 runs exactly one round with pure student roll-in, so
no DAgger guarantee applies. A pass or a fail neither confirms nor refutes DAgger. DART
([Laskey et al., CoRL 2017, PMLR 78:143–156](https://proceedings.mlr.press/v78/laskey17a.html)) frames the
same covariate shift and addresses it off-policy, by injecting noise into supervisor demonstrations. That is
an alternative this study does not test. [de Haan et al. (NeurIPS 2019)](https://papers.nips.cc/paper/9343-causal-confusion-in-imitation-learning)
show that imitation can fail through causal misidentification rather than missing support, which is one
reason the support-gap diagnosis is not treated as causal.

The puck task builds on the FLYNN `upstream/fly-gym` MuJoCo two-wheeled rover
([Wang & Chen, arXiv:2607.00025](https://arxiv.org/abs/2607.00025)), whose README says navigation was trained
with DAgger against an analytic teacher. It does **not** build on NeuroMechFly v2 (Wang-Chen et al., *Nature
Methods* 2024), so that work is not cited as its basis. **No novelty is claimed.** This is a standard single
aggregation step, applied prospectively to a documented failure of behaviour cloning.

## What v4 does not claim

A passed development gate supports only one claim: simulator capability of this fixed one-round procedure on
four fresh scenes. A later passed held-out gate supports only its eight-scene simulator criterion. v4 does
not claim that the support gap caused the earlier 0/4 results, or that targeted states, data volume and extra
updates were separated. It does not claim the regenerated corpus or students are bit-identical to, or stand
in for, the lost originals (S0c and S0d are descriptive). It does not claim the analytic teacher is correct
or fully observable by the student, that more rounds would help, or any benefit over v3, which never ran.
It claims no physical, biological, safety, UI or release capability. `qualification_claims` is empty.

## Open owner decisions

All nine decisions remain **open**. Each must be resolved, and this protocol re-hashed, before source freeze.

| ID | Decision | Reviewer-recommended default |
| --- | --- | --- |
| D1 | Held-out roster: authored 6200–6207 or fresh 6600–6607 | **6200–6207.** v3's held-out stays unchanged, and S8a (1,670 CPU-s) is not needed. Held-out `W` = 8,870, admissible iff `C ≤ 9,130`. |
| D2 | Scope of the S2/S8a comparison against 6200–6207 | A "held-out read" means executing those scenes or loading them into reset or the simulator. The pure ID/payload comparison runs under its own explicit GO. |
| D3 | Keep S0d (`W` 1,400) | Keep. |
| D4 | One-CPU cgroup-v2 quota as the census and CPU bound | Yes, after cgroup-v2 delegation is verified. |
| D5 | Independent manifest reviewer | Must be independent of the protocol drafter. |
| D6 | "Blocked" is final: no larger retention contract and no lane borrowing | Yes. |
| D7 | Per-owner byte cap and stage headroom | Keep 160 MiB and v3 stage caps; tighten only after a synthetic 600-tick S3 recorder measurement. |
| D8 | Hard 120 s audit deadline (prior audits ≤ 23.1 s wall); a kill is an operational failure | No reviewer default. |
| D9 | Order S1 before S0, so an ID collision stops v4 before ~4.3k worst-case CPU-s of S0 | No reviewer default. S1 does not depend on S0 outputs, but S2 does. |

## Owner resolution — 8 November 2026

All open decisions above were resolved by the owner to their recommended defaults (puck: D8 = 120 s hard audit kill; D9 = S1 before S0). Independent manifest review: a fresh AI reviewer agent, recorded as AI review, not human acceptance. Machine-readable record: `owner_decisions_resolution` in the protocol JSON. Each stage still requires its own reviewed execution manifest and explicit owner GO.

## Amendment 1 — 9 November 2026 (S1 non-scene content allowlist)

**Disclosure.** This amendment was written because S1 attempt 1 was refused
([evidence](../reports/puck-v4-s1-2026-11-08/README.md), `65b196a`). That attempt found 0 typed collisions
and 63 ambiguous documents, and published no reservation. All 63 documents are byte-identical copies of one
file: FLYNN `upstream/fly-gym/connectomes/ws_small_world/consolidated_cell_types.csv` at `8d96459`. Its
`root_id` column lists the neuron IDs 0–138,602 in sequence, so every integer, 6510–6523 included, appears in
it. Attempt 1 is consumed and its records are kept unchanged; it was charged 86.676 CPU-s (86.606 + 0.070 for
the audit). No scientific outcome was observed. No scene was minted, no simulator or model ran, and held-out
6200–6207 was only byte-read, within the S1 scope of D2.

**Change (frozen, one entry).** A non-scene content allowlist, matched only by exact sha256 of the whole
content: `52c1b2340c7df1311687584e8642b007eae65001315b7a64a0ff109c238e020e`, the FLYNN `8d96459` cell-type
table, a neuron table whose ID column enumerates all integers. Path and location do not matter. Any byte
difference means the unamended rule applies. ID mentions inside allowlisted content are reported as
`non_scene_asset_mentions` diagnostics, never as ambiguous or as collisions. Nothing else changes: the
ambiguity rule, fail-closed refusal on any remaining ambiguity, scope, typing, IDs and thresholds all stay as
written.

**S1 attempt 2.** Exactly one more attempt is allowed. It needs an independent review of this amendment and
a new owner GO. It uses the same declaration method, calibration, S1 scope of D2, and D8 audit (120 s hard
kill). Its worst case is unchanged at 660 + 120 = 780 CPU-s. **If attempt 2 is refused for any reason,
puck v4 is final-blocked, with no further S1 amendment.**

**Lane.** The pre-held-out worst case adds up as follows:
- 86.676 CPU-s already charged for attempt 1;
- 780 CPU-s for attempt 2;
- 15,010 CPU-s for S0a–S7.

The total is **15,876.676 ≤ 18,000**. Under D1 (authored 6200–6207), held-out `W` = 8,870, so held-out is
still admissible only if the measured charge `C` ≤ **9,130** CPU-s. That `C` includes attempt 1.
Machine-readable record: `amendment_1` in the protocol JSON.
