# M7 navigation training v2 — six frozen research models

The fixed paired training stage completed at producer `6feade9770dc40efa567633412baec4347ee33cb`. All six ORIGINAL-graph fits (old-corpus and augmented arms, seeds 10/11/12) completed 20 epochs. This is recorded-input imitation evidence; fresh closed-loop development and held-out navigation remain unstarted. No production checkpoint, capability threshold or promotion changed.

The [hash index](m7-navigation-training-v2.json) binds the retained control families, three pair reports and payloads, terminal/enclosing/drained-session receipts, independent audits and the [six-model development index](../../data/manifests/male-navigation-research-development-v2.json). The 1,180-entry raw/source/runtime/bundle ledger was copied from root's verified audit metadata without another producer corpus/checkpoint sweep. Local artifact paths require the retained sibling worktrees.

## Fixed inputs and results

The [admitted navigation data](m7-navigation-data-v2.md), manifest `47c4523c40e485ba4839cc80c9db891761791b801cc777755028122a1dbacb41`, supplies 2,117 old training rows or 7,197 augmented rows and the same 1,228 recorded-dev rows. The added 5,080 targets are recorded analytic-teacher advice, separately bound to actual learner actions. Training reused the unchanged fitter/cell: CPU float32, one thread, Adam .001, gradient cap 1, 32-row hidden-state carry/detach windows, fresh hidden per source, no rewiring. Old 67-row sources retain 32/32/3 windows. Selection is each fit's earliest strict minimum recorded-dev loss; all six models are retained.

| Seed | Old selected epoch / loss | Augmented selected epoch / loss | Pair supervisor wall |
| --- | --- | --- | --- |
| 10 | 20 / .025643583981726767 | 1 / .05646156711376451 | 145.164754892 s |
| 11 | 16 / .02962370051817319 | 1 / .0604871156646685 | 139.991090275 s |
| 12 | 17 / .023544041700782527 | 7 / .05394940920392543 | 138.497324531 s |

These runner-reported imitation losses are higher for every augmented arm. They do not establish navigation success or failure. Augmentation produces 236 rather than 72 optimizer updates per epoch (4,720 versus 1,440 over 20 epochs), an explicit treatment confound. Privileged analytic-teacher advice and its query-driven recovery counter remain label/observability limitations; extra advice is not proved expert-correct supervision.

## Execution, containment and independent checks

Corrected V2 exec session `70035` fully drained with exit 0. Launcher pre-publication wall was 429.579229769 s; enclosing pre-publication wall was 431.904795575 s. The enclosing supervisor admits completion only through its unconditional final return guard. Terminal SHA is `b15c8d473afe6670c67ec8c81d9203464d3febb1d05e98d3f5890c7fec96c111`; enclosing SHA is `1f10e3f3632fba65992718c84cce079d829447da920baa92429d8a09410a8d70`; drained-session SHA is `922139bb937b63972d3980c59ac7adaeb81d9cd5d1c6f001b53347a366b02ce7`.

The frozen bounds were 600 s internal / 660 s supervised per pair, 2,100 s cooperative overall, 2,150 s normal through return, TERM at 2,157 / KILL target 2,160 / fallback 2,163 s. Failure-only bounded waits give a nominal 2,183 s envelope, excluding measured publication or uninterruptible I/O; this is not a universal wall-time guarantee. The 256 MiB ledger reserves 192 MiB pair payloads, 32 MiB staging, 8 MiB logs, 16 MiB controls and 8 MiB headroom, with a 1 GiB free-space floor. Terminal usage before subsequent receipts was 3,808,953 bytes. Three identical retained upstream sparse-CSR beta-support warnings accompanied normal exits.

Both finite samplers stopped normally, with no errors, identity conflicts, forced signals or survivors. Seven union PID/start identities, including enclosing PID `1030752`/start `14265181` and startup PID `1029922`/start `14241842`, were absent after exec drain. The existing HOME writer lock was independently available and released with `fcntl`, without creating managed roots. Source, input, runtime, control and completed payload checks remained unchanged. Finite sampling does not prove every transient process was observed.

Root's retained audit passed its first execution: 6.287815722 s child / 6.945920713 s supervised, receipt SHA `6f393359bf7ccf4d573a23c6a04708d2a1e1ca33723f7bd98f91596f0f48bb90`. It verified 1,180 unique entries, all 120 epoch rows and earliest minima, and all six weights-only CPU checkpoints: 18 finite tensors, seven exact integer graph buffers and exact frozen weights each. It constructed no model and ran no forward pass or native simulation. The producer performed only small terminal/identity/control metadata checks after drain.

## Preserved failures and correction scope

The first actual attempt refused before any child/model started: an ad hoc startup `StorageBudget.lock` probe created the prospective managed output root, then the enclosing fresh-output guard correctly refused it. Its 42-file control family and empty output lock are retained unchanged; root's failure audit passed first in 4.119978423 s (SHA `e73b6745dd6c28c1c28f493443f9d2db6bec882eef28e7f2af7a996c40d52d48`). Its enclosing PID was not independently captured; that limitation stays explicit. Fresh V2 uses a frozen direct probe of the existing owned regular HOME lock and checks output absence after release, plus an enclosing PID/start receipt. No trainer, dataset, numerical setting or threshold changed.

The index also retains preparation failures: the initial fixture command ran zero tests; two admission fixtures failed on aggregate reservation/usage-key handling; a nonfinite rejection fixture exposed JSON failure-retention handling; and the initial full preflight resolved the venv executable to the base interpreter and refused missing `httpx`. Corrected fixtures and lexical venv execution passed without dependency installation. Root's V1 control review located the omitted exact monitor-function donor path; V2 records it explicitly. Source checks, 13 control checks plus one startup check, both control admissions, and all failed logs/receipts remain indexed rather than replaced.

The [frozen prospective protocol](../plans/m7-navigation-training-v2.md) still requires each augmented seed to achieve at least 3/4 on fresh development before opening the reserved held-out scenes, then at least 6/8 per augmented seed. Those stages are not part of this report. This result provides no topology, biological, hardware or automatic R3 qualification claim.
