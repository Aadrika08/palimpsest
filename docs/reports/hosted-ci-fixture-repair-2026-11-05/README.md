# Hosted fixture repair, 5 November 2026

Hosted run [42063786498](https://github.com/Aadrika08/palimpsest/actions/runs/42063786498)
at b7e364a passed install and preflight, then failed fixture tests. Frontend
passed. The [original failure](hosted-failure-42063786498.log) is retained.

The [diagnosis](diagnosis.md) separates production disk admission leaking into
authored verifier fixtures, four subsecond startup assumptions, and a combined
resource refusal whose exact failed hosted resource remains unmeasured.

Source repair 570438c changes authored tests and adds two hosted preflight nodes.
Authored capacity is explicitly synthetic; it is not a host measurement. The
production admission thresholds, scripts, protocols and archived auditor remain
unchanged. An initial attempt to scale cloned disk thresholds failed the intact
historical auditor; its [failed log](rejected-limit-scaling.log) is retained.
The corrected clone keeps those thresholds and supplies bound, labeled authored
capacity samples instead.

Focused verification with a private 4 GiB tmpfs passed: ownership wrapper
**1 passed**, comprising **101 nested tests**; five amendment cases plus the new
source-binding/isolation regression **6 passed**. The [independent review](independent-review.md)
approved this scoped repair without rerunning tests. The [manifest](manifest.json)
binds all eight retained records; originals and generated fixture trees remain
under the worktree's ignored runs directory.

No full suite or hosted rerun is represented by these focused results. A fresh
exact-head hosted result is still required before merging PR185. This software
repair performs no research execution, actual runtime qualification, protected
read, raw deletion or pruning.
