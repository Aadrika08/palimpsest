# Final editorial review

Reviewed source commit: `a6f505b680688f86db6cc03dcdab8b6156565c2c`.

Reviewed PDF: `paper/build/palimpsest-systems-paper.pdf`, 10 pages.

PDF SHA-256: `5df95e2ad463a9880726ebfc27a55d05766a2b119888c4be18f9f187b0b54525`.

Scope: final scientific narrative, wording, tables, figures, readability, and bounded workshop/software-paper readiness. Read the complete PDF text and inspected all ten existing `runs/final-render/page-*.png` page images. Read verification metadata, manuscript source and the plot's actual drawing commands. This is an editorial review, not independent numerical reproduction. No model jobs, campaign jobs, builds, tests, or PDF/source edits were performed. This review file is the sole written artifact.

## Verdict

SPEC: pass for the implemented, bounded semantic-contract paper. The final manuscript retains the prior four Important editorial fixes. It leads with integration and actual continuation/ablation/cost observations, credits established replay distinctions, separates diagnostic predicates from competitors, limits causal statements to timing/input provenance, and explicitly disclaims compositional proof.

TASK QUALITY: credible focused workshop or research-software paper, with one Important figure fix before editorial sign-off. This is no longer principally an internal assurance memo. Its strongest concrete evidence is immediate pose-only action divergence alongside constructive complete-state continuation, declared execution-sensitive replay, and recording cost including the substantial storage tail. Controlled conformance remains engineering evidence rather than an estimate of widespread misuse or comparative superiority. Honest bounded claims do not establish novelty or guarantee acceptance. A flagship general systems contribution would require a stronger case than this paper presently makes; widening the current study is not requested.

## Findings

### Important: storage-series observations are not visibly marked in Figure 3

Location: PDF page 8, Figure 3; `paper/generated/overhead-plot.tex`, final TikZ drawing block; `paper/main.tex:5`.

The final page image shows the blue synchronous plus signs and red background crosses, but storage open-circle observations appear absent: gray stems terminate at their values without the black circles promised by the legend. The highest storage observations are consequently communicated mainly by unlabeled stem endpoints, although the surrounding text and table honestly disclose the tail. The generated plot requests `mark=o`, while the manuscript loads `arrows.meta,positioning,fit` and does not load `plotmarks`. This is a likely cause, not a verified compiler diagnosis.

Required narrow fix: make the storage observations visibly match their legend, using the appropriate TikZ mark support or explicit open circles. Rebuild and inspect page 8 at final reading size, preserving all observations, the 186% maximum, and regular nonoverlapping axis ticks. No new experiment or data transformation is needed. Reported promptly to root during review.

### Minor: identify medians directly in Table 4

Location: PDF page 7, Table 4 summary header/caption.

The prose identifies median overhead and median ms/tick, but the summary columns themselves read `ms/tick` and `delta (%)`. Label these `median ms/tick` and `median delta (%)`, or state explicitly in the caption that these two summary columns contain medians. The per-seed rows and IQR columns are useful and should remain. This is clarification, not a challenge to the reported values.

## Assessment of claims and presentation

- The abstract gives real results without asserting that all 111 descriptors completed. Section 4.1 retains 110 completed/111 declared and explains the unadmitted checkout unit. Section 4.5 separately discloses the follow-up dependency-cache failure before FLYNN execution. Neither is presented as successful reproduction.
- The benchmark amendment is candidly disclosed, including the initial accounting, reset semantics and retained attempts. It occupies substantial methodological space, but is warranted given the changed measurement workflow.
- Table 1 distinguishes runtime/fixture/subprocess evidence and interface detection/diagnostic comparison/study guards. The caption explicitly prevents diagnostic divergence from being mistaken for automatic runtime refusal. C3 alone supplies benign false rejection. Weak-predicate counts remain secondary to conformance and ablation observations.
- Table 2 separates velocity-command and heading errors and acknowledges that pose-only restoration jointly omits state. It does not attribute the divergence to one omitted component.
- The branch's 92 compared continuation ticks and action/policy replay's 100 source ticks are explicit. Table 3's trajectory count is not treated as independent ticks.
- Table 4 and the surrounding text preserve negative background overhead, the large storage outliers, IQR, and producer backpressure. The abstract also exposes the 186% tail rather than reporting only an attractive median.
- Table 5's differing scopes are stated: decode without display, restore into an already-open owner, and replay including startup/execution/comparison/output. It supports scoped operation costs, not a uniform speed ranking.
- Figure 1 correctly describes a queued intervention while execution can continue, and uses the actual application revision symbol rather than assuming requested revision plus one. Figure 2 accurately distinguishes recorded trajectories from computation and comparison.
- The complete paper remains readable. Tables 1 and 4 are dense but legible; the floating tables split nearby paragraphs across pages, without obscuring the argument. Figures 1 and 2 are clear. The tenth page contains references, rather than padded body prose. The 10-page total exceeds the initial 7--9-page target, so venue-specific formatting/page limits remain an integration decision, not a scientific defect.
- The nearest robomimic and ManiSkill precedents receive explicit semantic and research credit. No absence-of-feature matrix or competing-system superiority claim has returned. This final pass did not repeat the prior primary-source verification.
- Limitations preserve the one-host/controller/seeds scope, nonexhaustive fault interactions, shared implementation/study assumptions, adapter requirements, numerical portability limits, trusted host, limited custody observation, no power-loss recovery guarantee, and unresolved independent reproduction/public archive.

## Readiness boundary

After the Figure 3 correction and a targeted rendered-page check, the paper is editorially ready for external technical/workshop review within its stated scope. Public submission readiness still depends on the explicitly open archive/redistribution and independent reproduction decisions and a chosen venue's requirements. This review does not authorize publication and does not certify raw-evidence correctness; that is the separate evidence-review lane.
