# W23 prior-art search: results (executed 2026-11-22)

Protocol: `../PRIOR-ART-PROTOCOL.md`, frozen at main `3ea7803`. Two independent **AI** screeners (A and B), both
given only the protocol, not the draft or its conclusions. Neither is a human screen. Public web only, via a web
search engine plus page fetches. A negative result means "not found by this protocol on that date".

## Deviations from the protocol (read before trusting any "not found")

- Sources not accessible to either screener: Google Scholar, Semantic Scholar, DBLP, ACM DL, IEEE Xplore, GitHub code
  search, Zenodo, Software Heritage, Lean Zulip archive. Everything was reached through general web search.
- ~10 hits per query, so the stop rules (100 screened / 30 irrelevant) never fired. Coverage shortfall, not a stop.
- "Variants" (survey/benchmark/tool/framework suffixes) run only partly (B: 3 variants; A: none). Docs sweeps for
  Gymnasium, dm_control, Habitat, CARLA, Brax, W&B/MLflow/DVC, rr, ReproZip were mostly not done.
- Citation chase one hop was thin and informal in both. Most items were verified from abstracts or snippets, not
  full text. Several items are dated Aug-Nov 2026 and could not be date-checked against the draft's timeline.
- Raw query logs are in the two screener reports (not committed). Logs list ~22 and ~21 fixed queries each plus logged
  amendments.

## Items, by verification level

Verified by me against the primary page this session (page loads, title, authors, abstract paraphrase):
- Gupta & Mittal, "Anytime-Anywhere-Valid PAC-Bayes: Certifying Post-Training Improvement of a Robot World Model",
  NeurIPS 2026 RoboPAD workshop (https://neurips.cc/virtual/2026/162900). Lean 4 machine-checked time-uniform
  PAC-Bayes inequality; complexity term over a deployed baseline vs posterior. No repo or theorem names on the page.
- Sneiderman, three NeurIPS 2026 workshop papers (https://neurips.cc/virtual/2026/170263, /175487, /164463): Lean 4
  checked anytime-valid bounds for a finite catalog of predictors, for interim looks with arm selection, and for an
  empirical-Bernstein confidence sequence with a stated 1.7x-3.4x width price. No repos or theorem names on the pages.
- `Robby955/formal-martingales` (Apache-2.0 Lean 4 library; `ville_inequality`, `ville_maximal_ineq`, e-process API).
- `facebookresearch/atlas-lean` PR #1250, merged 2026-11-12 (`Supermartingale.ville_maximal_ineq`).
- BiGym 2.0 (arXiv 2610.07594): page exists, but its **abstract says nothing about snapshots, RNG or pending commands**.
  Screener B's claim that its snapshot stores warmstart and controller state came from the paper body and is
  **unverified by me**; treat as a lead only.

Reported by both screeners, abstract-level read (not independently re-verified by me): Traceable World State
(arXiv 2610.12033), SimuGuard (arXiv 2610.41857), Formal-AVS (ICML 2026 listing, 60 Lean 4 theorems, four
anytime-valid families), Mittal & Gupta (arXiv 2606.11417, Lean mechanization of a finite-audit bound), LMLExplore PR #5
(merged 2026-10-30), MuJoCo simulation docs (integration state and warmstart), RoboVerse (action vs state replay),
mathlib `MeasureTheory.maximal_ineq` (Doob, submartingale only on the page read).

Reported by one screener, snippet or page level only: mathlib PR #45429 "add Ville's inequality" (open, A);
Isaac Lab-Arena record/replay, RoboSandbox policy replay, Observer notebook publication, commonware journal (A);
Ortega et al. arXiv 2605.29973 provenance, Isaac Sim Episode Recorder, Gazebo logger, rosbag2 resilient preset (A/B).

Disagreements: none that change a table row. B found the closer C6 items (Gupta & Mittal, Sneiderman); A found the
atlas-lean and mathlib Ville PRs; both found LMLExplore, Formal-AVS, TWS, SimuGuard. Under the protocol the union
governs.

## Section 7 table (stricter reading; "cited in draft" left to the authors' pass)

| Claim | Closest prior work | Same capability? | Proposed action |
| --- | --- | --- | --- |
| C1 joint contract | Traceable World State; SimuGuard; Isaac Sim Episode Recorder; provenance work 2605.29973 | partial | soften; cite TWS, SimuGuard, Isaac recorder |
| C2 applied-tick receipt | monoDrive per-command response (snippet); teleop latency logging; steering/provenance papers | partial / unclear | add citation; narrow to actual control tick and revision; verify monoDrive |
| C3 full continuation state | MuJoCo integration state + warmstart; SimuGuard warmstart write-back; BiGym 2.0 (unverified lead) | partial | narrow to the unfound parts (RNG, wrapper counters, pending commands, refusal before mutation); cite |
| C4 replay-report fields | RoboVerse; Isaac Lab-Arena complete/partial replay; RoboSandbox mode field; SimuGuard | partial (two-mode taxonomy is prior) | soften; cite |
| C5 staged publication | TWS rejected-append semantics; generic valid-prefix logs; Gazebo no-overwrite | partial (separately prior) | soften; "not found in the literature searched" with the log attached |
| C6 machine-checked anytime bounds | Gupta & Mittal; Sneiderman x3; Formal-AVS; formal-martingales; LMLExplore; atlas-lean; mathlib PR #45429 | partial to yes for "Lean-checked time-uniform bound auditing a system change over a finite set" | narrow; must cite these; remove any implication the Lean-checked anytime bound itself is new |
| C7 audit cost | Sneiderman ("nearly vacuous at the smallest stopping sizes"); Gupta & Mittal half-widths | partial | soften; cite |
| C8 pose-only ablation | SimuGuard and MuJoCo warmstart docs; ManiSkill state caveats | partial (failure mode known; first-action ablation not found) | frame as measurement of a known failure mode; cite |

No claim reaches "same capability, uncited" proven; none may be called novel or first. C6 is the weakest: several
Lean-checked anytime-valid results exist, some for robot post-training audits, all dated Jun-Nov 2026.

## Consequences for the draft (proposed, NOT applied; authors decide wording)

1. Intro contribution (4) and the RQ5 section: narrow "machine-checked ... audit" to what is specific here (finite-
   candidate fixed-horizon and anytime bounds for controller change, exact-rational bridge, nine-module package,
   cost at measured CPU), and cite Gupta & Mittal, the Sneiderman papers, Formal-AVS and the Lean Ville libraries.
2. Check the draft's "Apache-2.0 upstream proof" attribution against LMLExplore, atlas-lean and formal-martingales.
3. Related work: add TWS, SimuGuard, Isaac recorder/Lab-Arena, RoboVerse, MuJoCo state docs; add a sentence that the
   joint contract, not any single component, is the claim, and that each component has precedent.
4. Soften C1-C5 wording to "we found no work combining ..." only with the search log attached, never "first".
5. Describe C8 as measuring a known restore pitfall.
6. A human second screen and the sources neither AI could reach (Scholar, ACM, IEEE, DBLP, GitHub code search, Zulip)
   remain open; this run does not discharge the protocol's two-screener independence requirement beyond two AIs.

## Addendum 2026-11-23 (after independent AI review of PR #197)

- Cited after GitHub/arXiv verification: formal-martingales, atlas-lean PR #1250 (merged 2026-11-12), mathlib4 PR #45429 (open), RoboVerse (arXiv 2504.18904; metadata verified, its state-vs-action replay content rests on the screeners' abstract-level read). The Ville helper upstream (`noumenal-ai/anytime-anywhere-pac-bayes`, `Ville.lean`) is authored by Dhruv Gupta (`Ville.lean` header); the repo README says it accompanies a paper but does not name it, so the draft does not claim it is Gupta & Mittal's companion code. formal-martingales is credited to Rob Sneiderman per its README.
- Not cited: Isaac Sim Episode Recorder, Isaac Lab-Arena, RoboSandbox, Ortega et al. 2605.29973. Each was reported at snippet or page level only (Isaac Sim Episode Recorder by both screeners, the rest by one) and was not re-verified; under the stricter-reading rule they remain counted as prior art for C1/C4 in Section 7, and the draft's C1/C4 wording already disclaims priority.
- SimuGuard is no longer cited for the restore pitfall: its abstract does not mention restore or warm start (abstract-level only, never re-verified).
- Section 7 rows C3/C8 still list a SimuGuard warmstart write-back; that came from a screener's reading of the paper body and was not verified.
