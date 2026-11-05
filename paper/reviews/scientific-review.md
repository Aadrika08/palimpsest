# Independent scientific review

Reviewed manuscript source commit: `a6f505b680688f86db6cc03dcdab8b6156565c2c`.

Reviewed PDF: `paper/build/palimpsest-systems-paper.pdf`, 10 pages, SHA256 `5df95e2ad463a9880726ebfc27a55d05766a2b119888c4be18f9f187b0b54525` (independently recomputed). Build metadata binds that PDF and manuscript inputs; the PDF and verification file were already modified relative to Git when reviewed. Runtime evidence identifies `cc57edf9f70323926237d887d766627d8c9cdd42`, protocol revision 3, protocol SHA256 `570a4afe8179425bb2b25b86364470af34052ecc4929b74f207c279076728860`.

## Verdict

**A defensible, borderline-to-weak-accept focused systems/software/reproducibility workshop paper.** It is a credible engineering integration with unusually explicit evidence boundaries. It is not a strong general systems research result, and its narrow claims do not by themselves establish that the integration solves a prevalent research problem or transfers to other controllers. I would support a workshop submission after the concrete presentation fixes below; I would not describe the artifact as independently reproducible or release-ready yet.

Scores on a 1–5 scale, where 3 is borderline and 5 exceptional: contribution novelty **2**, practical significance **3**, evidence soundness within stated scope **4**, clarity **3.5**, reproducibility readiness **2.5**, overall workshop recommendation **3.5**. Confidence **4/5** for this bounded review. These are current-artifact judgments, not measured improvement over earlier drafts.

The useful contribution is connecting command application, recurrent continuation, declared executed computation, and publication status in one inspectable workflow. Individual ingredients are established. The strongest evidence is executable full-state agreement versus a numerically visible pose-only failure, plus an honest recording-cost result that retains severe storage stalls. The weakest evidence is the deliberately weak predicate comparison: it demonstrates distinctions by construction, not empirical superiority over existing tools or measured user mistakes. The paper mostly acknowledges this correctly.

## Checks and supported conclusions

I read the complete PDF text, `paper/main.tex`, the protocol, all four requested compact evidence objects, and relevant analysis/fault/repeatability source. No experiments, inference, Engine execution, or heavy tests were run. I used the research-evidence-check workflow. I did not rerun the 4.62 GB full raw inventory or certify every runtime implementation path.

* `summary.json` has 111 descriptors, 110 completed and one incomplete. Completed units are exactly 50 fault challenges, 10 continuation pairs, 5 replay trajectories, 40 cost conditions, and 5 operation units. The missing offline unit was not admitted; it is not a failed FLYNN run. The separately disclosed dependency-install follow-up also establishes no fresh-environment FLYNN result. The manuscript does not pool these outcomes.
* The continuation rows report 10/10 and replay rows 5/5 agreement. Seeds are engineering repetitions, not independent held-out tasks; source trajectories, not ticks, are counted. Replay conditions are paired with their source. Tables and prose use the right denominators and scope.
* I independently recomputed all three cost medians from the 40 retained scalar rows: synchronous 68.0280%, background 5.9588%, storage 18.0352%. Storage maximum 186.0446% and IQR 38.2467 percentage points reproduce the PDF. The negative background sample and storage slow samples remain visible. Ten matched sets, cyclic order, warm-cache policy, state-match gate, startup/close exclusions, and descriptive rather than significance-based inference are explicit.
* I opened all three compact S1 NPZs, checked their SHA256 against the summary traces, and recomputed first-action component errors. Pose velocity errors are 0.0319381, 0.0275598, 0.0270598; heading errors 0.0136870, 0.0192769, 0.0260514 rad. Complete-state errors are zero for both components. Table 2 is supported. This jointly removed-state ablation cannot assign blame to recurrent state alone; the caption correctly says so.
* Finite-only comparisons and exact identity/integer policy are stated. The post-run cost-state audit reports 40/40 canonical/finite checks, while explicitly limiting native coverage to exposed views and trusting the MuJoCo decoder. The PDF correctly labels this as post-run rather than a benchmark-time guard. Timer normalization is restricted to private cost-match copies, with recorder identities excluded by construction, not silently applied to replay agreement.
* `raw-inventory-audit.json` reports 2,938 files, 4,620,576,732 regular bytes, zero symlinks and no errors. This is evidence-custody accounting, not independent validation of the scientific oracle.
* R1/R2 are explicitly study label guards, S1/B2 diagnostic ablations, and storage faults interface fixtures. Table 1 does not collapse them into production runtime refusals. The stated trust boundary excludes hostile hosts, power-loss recovery, GPU/cross-version behavior, and causal identification appropriately.

## Findings requiring attention

### Important 1 — The integration contribution is less concrete on the page than in the retained evidence (fixable presentation)

`main.tex:64–80` makes integration the contribution; `main.tex:140–142` says application tick/revision link to snapshot provenance, replay, and publication. Figure 1 is illustrative, and Tables 1–3 report separate checks. No actual recorded example walks the reader across those links. The RQ2 continuation record already contains the stronger fixture description, “goal edit, nonzero controller/physics state and pending run command,” with queued-command idempotency and source-event-prefix checks; the PDF reduces it to “eight-tick prefix” (`main.tex:345–357`). This makes a real systems contribution look like an inventory of good practices.

Smallest fix: add one compact, retained-data example with the applied command/tick/revision, snapshot identity and pending-state scope, resulting branch/replay mode and comparison, and admitted publication status. Explicitly identify which links are verified together versus separately. Describe the actual nontrivial RQ2 fixture. Reuse existing traces; do not invent a new combined-fault result. If the retained record cannot support a particular cross-link, name that gap instead. This could materially improve intelligibility without new research.

### Important 2 — Reproduction is unestablished and the opening contribution list is slightly ahead of its own result (writing fix plus genuine missing execution)

`main.tex:79–80` lists evaluation of “same-host reproduction,” whereas `main.tex:447–460` correctly reports the declared unit incomplete and the separate follow-up stopped at a missing locked Torch wheel. The qualification is honest later, but the contribution list should say “a same-host reproduction attempt and its packaging failure” or omit reproduction from the achieved contribution. The retained results support no successful clean installation/execution.

Actual missing work, not reparable with wording: execute the workflow in a fresh environment with an explicit dependency/asset acquisition path and retain its outcome separately. Public archive/redistribution permissions also remain open (`main.tex:526–531`). These are artifact acceptance/release gates; they need not invalidate the narrow same-host measurements or force unrelated deployment experiments.

### Important 3 — Incremental novelty is the limiting factor; narrow scope alone does not prove usefulness (genuine research limitation, partly addressable with existing evidence)

The paper candidly credits state/action replay and physics continuation (`main.tex:462–503`). I checked the primary [robomimic implementation](https://github.com/ARISE-Initiative/robomimic/blob/master/robomimic/scripts/playback_dataset.py), [ManiSkill replay documentation](https://maniskill.readthedocs.io/en/latest/user_guide/datasets/replay.html), and [MuJoCo computation documentation](https://mujoco.readthedocs.io/en/stable/computation/): their semantics support the paper's conservative attribution. Thus the replay taxonomy and need to restore integration state cannot carry novelty. The paper's claim is an implementation joining boundaries, but there is no demonstrated downstream research diagnosis, adoption, reduction of analyst error, or second adapter showing transfer.

For a focused workshop, the implemented integration, ablation and cost can suffice, especially with the concrete trace in Finding 1. For a stronger research claim, supply a real analysis that the joined records make possible or an independent controller/wrapper integration. Merely adding seeds or more deliberately weak predicates would not settle usefulness or novelty. A feature comparison should not infer competitors lack capabilities merely because their docs emphasize different boundaries. No unrelated physical or medical deployment evidence is needed for this paper.

### Important 4 — Absolute cost results need a self-contained execution configuration (fixable presentation)

`main.tex:367–437` reports milliseconds and seconds but never states the actual CPU model, MuJoCo/Torch versions, thread configuration or material workload dimensions in the PDF. It only says covariates are retained. The evidence supplies at least AMD Ryzen 7 7735HS, performance governor, MuJoCo 3.3.6 and the locked Torch dependency. Readers cannot interpret 14 ms/tick or the approximately 21-second replay totals from “one host CPU” alone.

Smallest fix: a short evaluated-configuration paragraph/table giving verified hardware/software identifiers, thread policy, camera/input dimensions, recorder queue/chunk parameters, and workload scope, with detailed settings left in the artifact. Include the runtime/protocol SHA or a compact immutable artifact pointer. This does not require rerunning anything.

## Lesser issues and interpretation limits

* The “41 false acceptances” are evaluated deliberately weak predicates (`fault_matrix.py:47–73`), not a measured baseline tool or population of analysts. The current text says so, but a per-family example would be more useful than emphasizing a pooled counter across heterogeneous predicates. Keep the production/diagnostic/label split prominently visible.
* One 200-tick sample per seed/condition measures a short local throughput window; 4.55 seconds of accumulated producer backpressure is not a maximum single-tick latency or latency percentile. The manuscript currently avoids that stronger interpretation. Preserve this distinction in any shortened abstract or venue rewrite.
* Full-state restoration is supported over the tested 100-tick continuation. It is not a completeness proof for every mutable field or long execution, and the mathematical state tuple is a contract model rather than a verified theorem. Current limitations appropriately constrain this.
* RQ2's playback “agreement” is recording integrity/reading retained transitions, while executable replay compares recomputed values. Figure 2 and Table 3 largely protect this interpretation; retaining this distinction matters more than an aggregate four-condition pass count.
* The operation costs include different startup and recording work. They do not isolate the marginal cost of inference. The paper correctly states their scope; do not sell 20.9 versus 21.8 seconds as a controller-speed comparison.

## Readiness and venue fit

There is no critical factual contradiction identified in the reviewed scope. The manuscript is scientifically defensible as a narrow engineering case study and has enough actual execution evidence to warrant a workshop discussion. Its current weakness is limited incremental contribution and an artifact that has not reproduced in a fresh environment, not absent hardware deployment or absent statistical significance tests. Best fit: a systems-for-ML, reproducibility, scientific software, or embodied-AI tooling workshop that welcomes implemented case studies and transparent negative operational results. It is currently too incremental and single-path for a strong general systems or robot-learning full-paper claim.

Recommended next action: make the retained end-to-end evidence chain and evaluated configuration visible, correct the reproduction contribution wording, preserve all failed/incomplete attempts and tails, then target that venue archetype. Complete the fresh-environment/public-artifact gates before claiming reproducible delivery. No new study was authorized or launched in this review.
