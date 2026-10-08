# M7 navigation v3 matched-budget implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:test-driven-development` for source work and `superpowers:verification-before-completion` before each source or execution freeze. Complete the tasks in order; a later numerical stage needs its own reviewed execution manifest and GO.

**Goal:** Test the fixed advice-augmented corpus on the ORIGINAL MaleCNS topology with exactly the same real loss-bearing row presentations and optimizer updates as its paired old-corpus arm, then apply the unchanged per-seed fresh-scene capability gates.

**Architecture:** Replace the v2 epoch and arm-local checkpoint-selection clocks with one deterministic matched training-and-selection clock. Every model receives 46,080 real rows in 1,440 updates of 32 rows and only its terminal checkpoint is admissible; partial source fragments are packed into an update without padding or cross-source hidden carry. All other data, model, optimizer, loss, seed, runtime, simulator, and threshold choices remain fixed. The machine-readable [protocol](m7-navigation-v3-matched-budget-protocol.json) is authoritative.

**Tech stack:** Python 3.11.15, NumPy 2.2.5, Torch 2.9.0+cu128 on CPU with one thread, existing Palimpsest record/storage/model helpers, and the existing native simulator evaluator only after separate review.

**Spec:** [`docs/plans/m7-navigation-v3-matched-budget-protocol.json`](m7-navigation-v3-matched-budget-protocol.json)

## Global constraints

- This commit is documentation only. It does not open a corpus, manifest input outside tracked planning evidence, model, checkpoint, trajectory, simulator, generated scene, or held-out payload; it does not import Torch or MuJoCo.
- The sole intervention is the matched training-and-selection clock: equal real-row/update exposure plus terminal-only selection. Data arms, source identities and order, ORIGINAL graph, cell/model, seeds 10/11/12, Adam `.001`, gradient cap `1`, loss, float32 CPU/one thread, and capability thresholds stay fixed.
- V2 evidence remains immutable. V3 uses fresh output roots and new model identities; it does not overwrite, reinterpret, or promote any v2 asset.
- Synthetic tests may run repeatedly before source freeze. Each retained-input or numerical stage has one attempt, durable pre-input reservation, no retry, and no replacement case.
- Capability and topology remain separate. This lane creates no rewired model and supports no topology, biological, physical-rover, or automatic R3 claim.

## Why this is the next study

The completed checkpoint audit found a common-input restriction in all three selected augmented checkpoints: each emitted only one heading sign and made zero within-source sign changes, while all old-corpus checkpoints switched. That is descriptive evidence, not a mechanism. V2 also trained the old arm for 42,340 rows and 1,440 updates but the augmented arm for 143,940 rows and 4,720 updates; selected checkpoints had unequal, seed-dependent effective budgets. A new retrospective read cannot separate those causes.

V3 tests one prospective procedure: hold total real-row and optimizer exposure equal while retaining the fixed old and augmented corpora. The budget is anchored once at the historical old full-fit ceiling of 1,440 updates. With exactly 32 loss-bearing rows per update, both arms receive 46,080 presentations. This changes old exposure by `+3,740` rows and augmented exposure by `-97,860` rows relative to their v2 full fits. That asymmetry is disclosed and will not be tuned after results.

The selected checkpoint is always the terminal state after update 1,440. Recorded-development loss is measured once afterward and cannot select a different state. This terminal rule is part of the budget-control intervention: retaining arm-specific earliest minima would recreate unequal selected budgets. The result estimates the complete V3 procedure and cannot isolate terminal selection from the rest of the matched clock.

## Exact source and schedule contract

The immutable data manifest is `47c4523c40e485ba4839cc80c9db891761791b801cc777755028122a1dbacb41`. Its ordered old training arm has ten sources of:

```text
277, 182, 315, 245, 199, 265, 243, 257, 67, 67 = 2,117 rows
```

The augmented arm is that exact ten-source prefix followed by the twelve advice sources in scene/learner order `3100/10,11,12`, `3101/10,11,12`, `3102/10,11,12`, `3103/10,11,12`:

```text
600, 485, 496, 600, 196, 600, 600, 243, 198, 600, 276, 186
= 5,080 advice rows; total = 7,197 rows
```

The manifest hash binds each `run_id`, episode, length, feature-target hash, label, source path, split, and order. Old targets remain executed actions; advice targets remain exact recorded `nav_advice_action`. There is no filter, weighting, shuffle, relabeling, recollection, or new training source.

For each arm, let `R=46,080`, corpus rows `N`, and `(q,r)=divmod(R,N)`. Emit `q` full canonical sweeps, then allocate the `r` remainder rows among sources by Hamilton largest remainder: start with `floor(r*n_i/N)`, then add one to the largest integer remainders `(r*n_i) mod N`, breaking ties by lower manifest index. The frozen allocations are:

| Arm | Full sweeps | Remainder | Exact per-source remainder allocation |
| --- | ---: | ---: | --- |
| old-corpus | 21 | 1,623 | `212,140,242,188,153,203,186,197,51,51` |
| augmented | 6 | 2,898 | `111,73,127,99,80,107,98,103,27,27,242,195,200,242,79,242,241,98,80,241,111,75` |

Thus every eligible row appears exactly `q` or `q+1` times. A seed-specific SHA-256 rule in the JSON protocol selects one contiguous cyclic remainder segment per source; the arm is absent from the hash so a shared old source starts at the same row in both arms. A wrap is split and resets hidden before row zero. This avoids fixed tail preference while preserving real local sequence fragments. The execution report must publish every allocation, start, fragment, exposure count, and the complete schedule hash before fitting.

The fragment stream is packed into 1,440 units of exactly 32 real rows. An update can contain the tail of one source and the head of another, but they are separate forward fragments with separate hidden states. Start with `model.reset()` at every source, full-sweep restart, remainder start, and remainder wrap. Carry through contiguous rows; detach once if the same fragment continues across an optimizer boundary. For each unit, zero gradients once, sum exactly 32 per-row losses across its fragments, divide by 32, backpropagate once, clip once, and call Adam once. Padding, masked filler, loss-free rows, tail dropping, cross-source recurrence, and fractional updates are all forbidden.

## Fresh capability stages

The new development IDs are **3130–3133**. A tracked plan/report/manifest-roster scan at base `a875024` found no occurrence of those IDs. That scan is only a candidate screen. Future preparation must inspect every retained raw scene registry and manifest plus every prior branch, worktree, and evidence root, then prove exact ID, canonical-scene, scientific-initial, and complete-payload disjointness against all earlier train/development/evaluation cases and held-out IDs; seed disjointness and base text alone are insufficient.

Development order is scene increasing, training seed 10/11/12, old-corpus then augmented: 24 owners, at most 14,400 ticks. Every owner must complete normal admission, and **each augmented seed independently must reach at least 3/4 goals** under the unchanged native `last_outcome.reason == "goal"` within 600 ticks. A natural non-goal is a functional failure. Any incomplete owner, admission failure, or augmented seed below 3/4 leaves held-out locked.

Held-out **3120–3127** remains reserved and unopened. Passing development is necessary but does not authorize it. A separate held-out manifest, independent review, resource admission, and explicit GO precede any geometry generation or payload opening. The later fixed order has 48 owners and at most 28,800 ticks; all must be admitted, and **each augmented seed independently must reach at least 6/8 goals**. There is no pooling, winning-seed choice, replacement scene, rescue, retry, or threshold change.

The primary estimand is the absolute simulator capability of the fixed augmented-corpus ORIGINAL-topology procedure at the matched budget. Old-corpus outcomes are paired descriptive controls. A data-arm contrast describes the two complete procedures; it does not identify advice correctness, coverage, source order, row frequency, selection, or optimizer mechanisms. Topology requires a different prospective study.

## Resource and attempt envelope

Training totals 276,480 real presentations and 8,640 optimizer updates across six models, plus 7,368 terminal recorded-development rows. This is 49.5% of v2 presentations and 46.8% of v2 updates. Historical v2 took about 140 seconds per pair; 4–8 minutes for V3 training including admission/publication is a planning estimate, while the existing conservative bounds govern:

| Stage | Attempts | Time bounds | Output/free-space bounds |
| --- | --- | --- | --- |
| Training | one enclosing attempt; each seed pair starts at most once | 600 s internal / 660 s outer per pair; 2,100 s internal / 2,150 s normal return / 2,160 s enclosing | 64 MiB per pair; 256 MiB aggregate; 1 GiB RSS per pair; 1 GiB free floor |
| Development | one stage; each fixed owner once | 180 s/owner; 4,320 s child allowance + 50 s parent = 4,370 s internal / 4,420 s normal return / 4,430 s enclosing | 160 MiB/owner; 4 GiB stage; 1 GiB free floor |
| Held-out | one later stage after separate GO; each fixed owner once | 180 s/owner; 8,640 s child allowance + 50 s parent = 8,690 s internal / 8,740 s normal return / 8,750 s enclosing | 160 MiB/owner; 8 GiB stage; 1 GiB free floor |

The child allowances are only the full sums of owner maxima (`24×180=4,320` and `48×180=8,640`); they do not include parent work. Each stage separately reserves 50 internal parent seconds: 20 for pre-owner admission and durable reservation, 20 cumulative for owner launch/reap/accounting, and 10 for reduction and pending-report staging. The internal deadlines are therefore 4,370 and 8,690 seconds. Another 50 seconds is reserved through normal return—15 for final source/input/cap checks, 20 for fsync and atomic publication, 10 for release and identity drain, and 5 for the return guard—followed by a separate 10-second enclosing hard margin. Unused child time cannot enlarge a parent or publication ledger, and neither stage relies on typical cases finishing early.

A durable fresh-output attempt receipt must be fsynced before any retained input, Torch, model, simulator, or scene access. A crash or outer timeout consumes the attempt. The first source, input, schedule, finite, runtime, deadline, RSS, storage, publication, or admission fault stops the stage, retains the failure, and leaves later work `not_started`.

## Review focus

- A source shorter than 32 or a final tail must contribute every real row without padding or an extra optimizer step.
- A 32-row unit spanning several sources must reset at each source boundary while still producing one row-weighted gradient step.
- A cyclic remainder that crosses a source end must split and reset rather than create artificial last-to-first recurrence.
- A corpus or source-order change must fail before Torch import, and a held-out argument must be unreachable from training/development preparation.
- Terminal checkpoint publication must remain fixed at update 1,440 even if an earlier recorded-development score is lower.
- All maximum-duration owners plus mandatory parent work must fit their separate ledgers; a one-tick overrun in any ledger must retain failure and prevent admissible publication.

---

### Task 1: Implement the pure matched-row schedule

**Files:**
- Create: `src/palimpsest/male_matched_budget.py`
- Create: `tests/test_male_navigation_v3.py`

**Interfaces:**
- Produce `build_schedule(sources: tuple[SourceIdentity, ...], seed: int, presentations: int = 46080, rows_per_update: int = 32) -> Schedule`.
- `Schedule` exposes immutable fragments, 1,440 packed update units, per-source allocations/exposures, and a canonical SHA-256; it has no NumPy, Torch, filesystem, or simulator dependency.

- [ ] Write pure failing tests for the exact old and augmented length arrays. Assert 46,080 rows, 1,440 units, 32 real rows/unit, the frozen Hamilton arrays, the frozen per-source totals, `q/q+1` row exposure, deterministic seed starts, and byte-identical canonical replay.
- [ ] Add failing synthetic cases for 1-, 31-, 32-, and 33-row sources, Hamilton ties, multi-source packing, and cyclic wrap. Assert no padding/drop and explicit reset/continuation markers.
- [ ] Implement the smallest immutable schedule builder using integer arithmetic and `hashlib.sha256`; reject booleans, duplicate identities, empty sources, invalid lengths, overflow, mismatched totals, and any fragment not exactly covering its declared rows.
- [ ] Run `python -m unittest tests.test_male_navigation_v3 -v`; expected result is all pure schedule tests passing with neither `torch` nor `mujoco` imported.
- [ ] Commit the pure source/tests and request independent review. Do not open retained inputs.

### Task 2: Implement the bounded V3 trainer and atomic evidence

**Files:**
- Create: `scripts/train_male_navigation_v3.py`
- Modify: `tests/test_male_navigation_v3.py`

**Interfaces:**
- Consume the exact v2 data-reader/model/publication boundaries and `build_schedule`.
- Produce one fresh pair directory with durable attempt/failure receipts, two terminal checkpoints, schedule/protocol reports, terminal recorded-development metrics, and before/after source/input hashes.

- [ ] Write failing synthetic admission tests for every corpus, graph, cell, runtime, behavior-source, output, storage, deadline, RSS, and held-out boundary named in the protocol. Importing the module must remain Torch/MuJoCo-lazy.
- [ ] Write a fake-model test that traces reset, forward, detach, zero-grad, loss denominator, backward, clip, and optimizer-step calls across a multi-fragment unit. Assert exactly one update per 32 real rows and no cross-source hidden carry.
- [ ] Implement the narrow trainer. Reuse the v2 reader/admission and unchanged model/loss definitions, but do not call the epoch fitter. Admit and canonically hash the schedule before Torch import; then execute its units exactly.
- [ ] Select only the state after update 1,440. Copy terminal weights before running the single unchanged 1,228-row recorded-development evaluation; never retain or publish an intermediate alternative.
- [ ] Add durable pre-input reservation and fault-injection tests for crash, timeout, fsync, rename, source drift, nonfinite values, wrong counts, and final caps. Success publication is the last fallible commit step; failure never creates an admissible report.
- [ ] Run the focused suite and `py_compile`, inspect the exact diff, freeze all new/transitive source hashes and the invocation in a separate execution manifest, then obtain independent GO. Tests may rerun; retained-input training has not started.

### Task 3: Execute and review the single training attempt

**Files:**
- Create after reviewed GO: a fresh `runs/m7-navigation-v3-matched-budget-*` evidence family
- Create after compact review: `data/manifests/male-navigation-research-development-v3.json` and a compact report under `docs/reports/`

- [ ] Start the one enclosing training attempt with seed pairs 10, 11, 12 in order. Never inspect inputs outside the reviewed runner and never retry a failed pair.
- [ ] Require exact schedules, 46,080 rows, 1,440 updates, terminal selection, normal exit, unchanged hashes, and complete atomic evidence for all six models. A mismatch stops and preserves the failure.
- [ ] Have an independent reviewer inspect compact outputs and hashes without another corpus/model pass. Only a GO may freeze the six-model V3 index for development.

### Task 4: Implement and freeze fresh-development evaluation

**Files:**
- Create: `scripts/evaluate_male_navigation_v3.py`
- Create: `tests/test_male_navigation_development_v3.py`

**Interfaces:**
- Consume only the admitted six-model V3 index and exact generator/runtime/contact bindings.
- Produce the fixed 24-case development evidence and a per-seed gate reduction; it has no held-out route.

- [ ] Write failing source-only tests for exact case order 3130–3133 × seeds 10/11/12 × old/augmented, model-index admission, all-six matched scientific initials, canonical/payload disjointness, source/runtime/contact guards, native goal scoring, and first-failure retention.
- [ ] Add reducer tests proving all 24 normal owners plus 3/4 goals independently for each augmented seed are necessary; old-arm counts remain descriptive and no pooled criterion exists.
- [ ] Add a synthetic monotonic-clock boundary test for both 24 and 48 owners. Prove `owners*180` is only the child allowance, the `20+20+10` parent work reaches the internal deadline exactly, `15+20+10+5` reaches normal return exactly, and the 10-second enclosing margin is separate. Exact-limit completion passes; a one-tick child, parent, publication, or hard-target overrun stops, retains the first failure, leaves later owners `not_started`, and never publishes success.
- [ ] Implement the smallest named V3 evaluator by reusing the v2 evaluator's bounded owner, record, contact, and publication helpers. Keep teacher queries, rescue, replacement seeds, checkpoint selection, and held-out IDs unreachable.
- [ ] Freeze source hashes and one exact development invocation, obtain independent GO, then run once. If any augmented seed is below 3/4 or any owner is inadmissible, publish that result and stop with held-out locked.

### Task 5: Gate a separate held-out study

**Files:**
- Create only after a development pass: a separate held-out plan/execution manifest and compact report path

- [ ] Verify the immutable 24-case development report and each augmented seed's 3/4 gate without reopening training or trajectory inputs.
- [ ] Freeze 3120–3127, the exact 48-case order, disjointness checks, 6/8 per-seed reduction, resources, source hashes, invocation, durable attempt, and no-retry policy in a new reviewable manifest.
- [ ] Obtain independent review and explicit GO before any held-out geometry or payload access. Run at most once; preserve every outcome and report capability only within the simulator evidence boundary.

## Stop conditions and unresolved risks

Implementation stops before numerical work if the protocol, inputs, source roster, exact corpora, schedule, graph, cell, runtime, output freshness, storage, or supervision cannot be bound. Numerical work stops permanently on its first failure; later owners remain unstarted. Development cannot start without six independently admitted terminal checkpoints. Held-out cannot start without a complete 24-case development pass and a separate GO.

The 1,440-update anchor is one unsearched budget. Equal compute deliberately presents an old row 21/22 times and an augmented row 6/7 times. Terminal selection and fragment packing differ from v2 and are inseparable parts of the matched clock. Advice remains privileged, history-dependent supervision whose correctness and observability are unresolved. Scene IDs 3130–3133 are roster-disjoint now, while exact geometry/payload disjointness remains a future admission result. Even a held-out pass would establish only the declared simulator capability criterion; topology, biology, artwork integration, physical rover behavior, operator readiness, and R3 remain separate decisions.

`qualification_claims` remains empty in this planning slice.
