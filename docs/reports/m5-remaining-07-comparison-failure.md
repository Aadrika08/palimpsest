# Remaining-07 comparison: retained infrastructure failure

The one-shot attempt at source `0e32482` ended **comparison_unverified**, actual session 30311 exit 1. It attempted 39 of 40 owners: 38 supervisors completed with exit 0, retrieval failed, and the final oracle was unattempted. The 39 native snapshots and 4,528 actual CPU FLYNN intervals remain retained. This failed batch does not promote development coverage: **32/48 cells remain accepted**; held-out and R2 acceptance remain open.

The failed owner `df1ee6371dca46dca09372fd1bb0d925` was s29/local_cue/no-event retrieval. Its worker reported `TimeoutError: Continuation internal wall bound`, paused at boundary 390 after 90 intervals, without a task outcome. Closing produced a completed recording with `operator_closed`; this does not admit the failed experiment stage. The 160-second supervisor recorded return code −15 at 162.222035 s and `LogLimit: native log drain/final sync timed out`. The enclosing invocation also recorded the drain failure and exit 1. Oracle `63afb0928c864976a80b270c88c1ab3a` never started. No retry, replacement owner or bound change occurred.

The worker's 150-second timer starts before `Engine.open`, covering model loading, atomic restoration, snapshot admission and continuation. It checks before each step; close/report publication follow. Existing `bounded_process` separately enforces 160 seconds and a two-second log-thread join. These receipts do not isolate which operation consumed time. Post-failure IO pressure is not cause proof; the LogLimit label here identifies drain/final-sync timeout, not demonstrated log-byte overflow.

Three completed cell readouts are descriptive only; all 27 reconstructed evaluator task checks are true, while worker task flags remain null:

| Cell | Actual readout under all nine conditions |
|---|---|
| s28/paired/no-event | Goal 430; zero selector invocations, behavior bytes and inspections. |
| s29/local/change | Upper fact z passively observed and corrected at tick 300; goal 432. Own/sham select z without inspection; swapped/history-independent/traversal select a and make one unnecessary inspection. No-U abstains. |
| s29/local/null | Empty gold; goal 430. Own/sham/hand/retrieval falsely target z, swapped/history-independent/traversal falsely target a and inspect once; no-U/oracle abstain. Upper confirmation at tick 300 and lower confirmation at tick 358 are not corrections. |

Own/sham retained numeric trajectories agree exactly in these three readouts. No own-U task, correction or goal-time benefit is observed. The incomplete fourth no-event cell is not imputed or scored as a completed comparison; its failed 90-row retrieval prefix has no trigger, selector invocation or task outcome.

Local failure-preservation audit passed first in 16.050558 s: 38 normal owners through shared `validate_stage`, the failed stage explicitly rejected, its native/recording/typed-policy prefix checked separately, and the three readouts/own-sham arrays reconstructed. Root failure audit passed first in 20.898129 s; independent partial-outcome reconstruction passed first in 6.518421 s. They checked 597 source/upstream/asset identities, 120 inputs, 39 snapshots, 16 strict core boundaries, 23 broader/anchor boundaries and the recorded 4,528 intervals without neural recomputation. Original success auditors were preserved but never executed against this failed batch.

Actual session drained with exit 1. Launcher including cleanup took 1929.079524 s; enclosing drain/inventory took 1939.431897 s. Root verified 41 non-launcher PID/start identities plus the launcher absent and writer lease available. Outer monitor cleanup recorded no forced signals, errors or survivors; the child supervisor’s −15 is separately preserved. Source, inputs, controls and prepared/before/after inventories match. No local lease probe followed drain.

[The JSON index](m5-remaining-07-comparison-failure.json) binds aggregate `a821638f…`, launch `17fd439b…`, enclosing `603632b0…`, local audit, root failure audit `380b1253…`, root partial outcomes `13a84884…`, complete raw ledger and controls/unused preparation receipts. Raw-output and local-subset index counts have separate scopes. Publication copies verified raw hash metadata without repeating the bulk sweep during navigation preflight; root publication verification is separate. Historical data, lower-route geometry, sensor/controller behavior and all numerical sources are unchanged. This is neither a completed four-cell gate nor full-matrix/held-out/R2 evidence.
