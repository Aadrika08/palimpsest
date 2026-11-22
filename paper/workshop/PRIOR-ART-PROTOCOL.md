# W23 prior-art search protocol (DRAFT, not executed)

Status: **draft, no search has been run.** This file fixes the questions, sources, queries and decision rules
*before* searching, so the result can be audited and cannot be tuned to a preferred answer. It authorises no
compute and no protected reads. Search results are public literature only.

Purpose: test whether the W23 draft's contribution wording is supported by the literature, and find missed
prior work. It produces a documented search and a list of findings. **It does not produce a novelty verdict**;
at most it shows the draft's claims were not contradicted by what this protocol could find.

## 1. Claims under test

Taken from `aaai27-w23.tex` (the draft is the reference; re-extract if it changes). Each claim gets a row in the
results log.

| ID | Claim (short) | Draft location |
| --- | --- | --- |
| C1 | One contract joins applied-command receipts (actual control tick and revision), controller-visible observation projection, complete continuation snapshots, replay reports naming the executed computation, and staged publication | Intro (1)-(2), Sections 2-3 |
| C2 | An application receipt that identifies when an operator intervention actually took effect in a running closed-loop simulation, distinct from request acceptance | I1 |
| C3 | Continuation state includes controller hidden state, wrapper counters, RNG state and pending commands, bound to source/asset fingerprints; refusal before mutation on incompatibility | I2 |
| C4 | Replay reports declare mode (playback / action replay / policy replay), whether inference executed, comparison fields, tolerances, first divergence | I3 |
| C5 | Staged no-overwrite publication leaves a validated prefix and an ignored tail without a terminal-success claim | Sec. 3 |
| C6 | Machine-checked (Lean 4) finite-candidate fixed-horizon and anytime bounds for auditing a controller change, with an exact-rational bridge | RQ5 |
| C7 | A measured cost of that audit shows the one-hour lane affords only a vacuous radius | RQ5 |
| C8 | Pose-only restoration changes the first action while complete continuation agrees (as an ablation result) | RQ2 |

Concessions already in the draft (do not search to overturn them, only to confirm attribution is correct):
state-vs-action replay taxonomy (robomimic, ManiSkill); Ville / time-uniform concentration theory; the adapted
Ville helper.

## 2. Questions

- Q1. For each claim C1-C8, does a prior work already provide the same capability, or a close substitute?
- Q2. If so, does the draft cite it and describe the difference correctly? If not cited, is the omission material?
- Q3. Are there existing Lean/mathlib results for finite-family or anytime-valid (Ville-type) bounds that C6 duplicates?
- Q4. Are there known failure modes of state restore or replay (hidden state, RNG, pending inputs) that the draft presents as new?

## 3. Sources (all searched, none skipped without a logged reason)

1. Google Scholar, Semantic Scholar, arXiv (cs.RO, cs.AI, cs.LG, cs.SE, cs.LO, cs.PL, stat.ML), DBLP, ACM DL,
   IEEE Xplore, ACL/NeurIPS/ICML/ICLR/CoRL/RSS/ICRA/IROS/AAAI proceedings via the above.
2. Code and docs: GitHub code search and repository search, Zenodo, Software Heritage; official docs of MuJoCo,
   Gymnasium, dm_control, Isaac Sim/Lab, robomimic, ManiSkill, Habitat, rosbag2/ROS 2, CARLA, Gazebo, Brax, MuJoCo MJX,
   Weights & Biases / MLflow / DVC (provenance tooling), `rr`, ReproZip.
3. Formal: mathlib4 (docs and source grep), Lean Zulip archive, the Lean 4 `Probability` and `MeasureTheory`
   namespaces, Archive of Formal Proofs (Isabelle) and Coq/Mathcomp analysis for any anytime-valid or Ville
   formalisation.
4. Forward and backward citation chasing from every included item (one hop each way).

## 4. Queries (fixed; additions allowed only by logged amendment)

Run each query in each applicable source. Record the date, source, exact string and hit count.

Replay / continuation / checkpoint (C1, C3, C4, C8):
- `simulator state restore continuation hidden state RNG replay`
- `deterministic replay robot learning simulator checkpoint pending actions`
- `action replay vs state replay policy replay simulation`
- `MuJoCo restore state mjData warmstart determinism continuation`
- `recurrent policy hidden state checkpoint resume simulator evaluation`
- `record and replay closed-loop simulation applied commands receipt`

Intervention application / authority (C2):
- `intervention applied tick acknowledgement operator interactive simulation`
- `teleoperation command latency applied at control boundary receipt log`
- `human-in-the-loop experiment simulator intervention provenance log`
- `web interface live edit simulation environment obstacle injection reproducibility`

Publication / recorder (C5):
- `atomic append-only trajectory recorder validated prefix crash consistency`
- `episode recorder staged publication no overwrite experiment logs`
- `rosbag2 storage durability partial bag recovery`

Provenance / reproducibility tooling (C1, C4):
- `experiment provenance embodied AI replay evidence`
- `reproducible robotics experiments record replay framework`
- `claims vs evidence logging for ML experiments machine checkable`

Audit bound / formal (C6, C7):
- `Lean 4 formalization concentration inequality Hoeffding finite candidates union bound`
- `Lean mathlib Ville inequality supermartingale maximal inequality`
- `formal verification anytime-valid inference confidence sequence`
- `time-uniform concentration finite candidates policy comparison off-policy evaluation sample cost`
- `evaluation cost of certifying controller improvement simulation scenarios budget`
- `formally verified statistical guarantee machine learning evaluation proof assistant`

Variants: also run each query with `survey`, `benchmark`, `tool` and `framework` appended; log any skipped source.

## 5. Screening rules

Date range: from 2000-01-01 to the search date. Language: English (log non-English hits that look relevant).

Include (title/abstract stage) if the item describes a system, standard, formal result, or empirical study about
any of: restoring or replaying simulator or robot-learning runs; applying and logging interventions in running
simulations; recorder durability or publication semantics for experiment logs; formalised concentration or
anytime-valid bounds; evaluation-cost analyses for certifying controller changes.

Exclude: pure rendering/visual replay with no state; generic video logging; general MLOps with no run-level
semantics; theory with no formalisation for C6 (keep it only for Q2 attribution).

Full-text stage: keep if it **materially** implements, specifies or proves one of C1-C8, or contradicts a
concession. "Materially" = a reader could reproduce the capability from the item. Record the deciding sentence.

## 6. Procedure

1. **Freeze** this file (commit hash recorded in the results log) before any query is run.
2. Two independent screeners (one may be an AI agent recorded as such; the other should be a human author or a
   second AI instance given only this protocol and not the draft's conclusions). Each screens separately, then
   disagreements are listed, not silently resolved.
3. Log every query: date, source, string, filters, hits seen, hits screened. Keep raw exports under
   `paper/workshop/prior-art/` (public items only).
4. For each C1-C8 fill the results table (Section 7). Include near-misses, not only hits.
5. Backward and forward citation chase one hop from every included item; screen the new items the same way.
6. Stop rule: stop a query after 100 screened hits or when 30 consecutive hits are irrelevant, whichever is
   first. Log the stop reason. Do not stop early because a hit looks supportive.
7. Search date cutoff: the day of execution; late items are logged as post-cutoff, not added silently.

## 7. Results log (template)

| Claim | Closest prior work found | Same capability? (yes / partial / no / unclear) | Cited in draft? | Difference stated correctly? | Action |
| --- | --- | --- | --- | --- | --- |
| C1 | | | | | |
| C2 | | | | | |
| C3 | | | | | |
| C4 | | | | | |
| C5 | | | | | |
| C6 | | | | | |
| C7 | | | | | |
| C8 | | | | | |

"Action" is one of: none / add citation / soften wording / narrow claim / remove claim.

## 8. Decision rules (fixed in advance)

- Any claim with a "yes" prior work: the draft must cite it and reword the claim to the actual difference, or drop it.
- Any claim with "partial": the draft names the part that is prior and the part this work adds.
- A claim is described as "not found in the literature searched" only with the log attached, and never as "novel"
  or "first". No result of this protocol licenses the word "novel".
- Findings that weaken a claim are not suppressed; they go in the draft or the limitations.
- If screeners disagree on an item, the stricter reading (counts as prior art) governs until resolved with the
  disagreement noted.

## 9. Limits

Public search cannot find unpublished or paywalled work, internal tooling, or work in venues the sources index
poorly. Search engines are non-deterministic and time-varying; logs make runs inspectable, not exactly repeatable.
A negative result means "not found by this protocol on that date".

## 10. Approvals

This is a literature search and edits to draft wording only. It needs no stage manifest, compute or protected
read. Edits to the draft that change a claim are reviewed independently before merge. Authors, not this protocol
or any AI reviewer, decide the final claim wording.
