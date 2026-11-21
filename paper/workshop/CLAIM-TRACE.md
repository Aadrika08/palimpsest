# W23 draft: provenance of numbers typed in prose (not macros)

Generated macros cover results. These prose-only constants trace to retained evidence (checked 2026-11-21):

| Draft text | Source |
| --- | --- |
| 10 continuation pairs, 5 replay trajectories, 10 overhead seeds | `paper/evidence/authority-replay-v1` summary (`ContinuationDeclared`, `ReplayDeclared`, `OverheadDeclaredSeeds`) |
| 69/111 first campaign | `initial-attempt/retention.json` (`completed: 69`) |
| 92 matched ticks, 30-event digest, tick-0/revision-1 receipt | `authority-replay-v1/worked-chain/chain.json` (`continuation_ticks: 92`) |
| 8-tick prefix, 100-tick comparison, 20 warm-up / 200 measured | frozen protocol under `authority-replay-v1` |
| 158 CPU-s, 55-s offline check | `paper/ARTIFACT.md:144` |
| 17 axiom reports, nine Lean modules | `formal/change-audit/evidence/parent-independent-axioms.log` |
| 16 conditions x 64 ticks = 1,024 | `docs/progress.md:33` (sixteen completed 64-tick conditions); `condition-manifest.json` (0 contacts in all 16) |
| 44/48 cells, 120 correction pairs | `docs/progress.md:110-117`, `m5-development-readout-44.md:11` |
| Recovery-navigation held-out did not qualify | `docs/progress.md:315-320` (48-owner held-out stage completed, no capability) |
| Puck v4: scene-ID admission only | `docs/progress.md` M6 rows; research status memory, S1 only |
| Augmented near-constant actions | `docs/reports/male-v4-s2/RESULT.md:58-60` (cause not established) |
| Loss ~11-12x (11.4, 12.2, 11.2), 7,197 vs 2,117 rows | `docs/reports/male-v4-s2/UNDERFIT-NOTE.md` (S1 report sha `6ca8af5f...`); descriptive, not a controlled test |
| 12 episodes, 4 scenes | now macros `\MaleVfourEpisodes`, `\MaleVfourScenes` |

Not re-derived from raw data: the 8/100/20/200-tick protocol constants and the puck statement beyond the progress notes.
