# Remaining-02 fixed lower-route comparison

The one-shot comparison at source `7a956b0` completed **40 owners / 4,650 neural
intervals**: four zero-row own-U anchors and 36 actual CPU FLYNN continuations.
All owners and exec session `16166` exited 0. No owners were unattempted; there
were no retries, signals, monitor errors or surviving sampled processes. Normal
enclosing supervision took 1,812.749 seconds; drain and inventory finished in
1,816.169 seconds. The runtime slot was released before retained audits.

All **36 evaluator task readouts passed**; worker task flags remain `null`.
There is **no observed own-U task or timing benefit**. This completes four more
development comparisons: 16 of the fixed 48 cells are now compared, with 32 and
held-out evaluation still open. R2 acceptance is not complete.

| Cell | Independent gold | Goal boundaries | Actual revision / confirmation |
| --- | --- | --- | --- |
| s24/paired_cue/no-event | empty | 428, all nine | Upper confirmed at 300, lower at 358; zero selector invocations, behavior bytes or inspections. |
| s25/local_cue/null | empty | 429, all nine | Upper confirmed at 300, lower at 358; no stale-value correction. |
| s25/local_cue/no-event | empty | 429, all nine | Same confirmations; zero selector invocations, behavior bytes or inspections. |
| s25/paired_cue/change | lower fact a | 431 for own/sham/history-independent/traversal/retrieval/oracle; 430 for swapped/no-U/hand-authored | Lower observed and corrected at 358 in all nine; upper confirmed at 300. |

Exact target suffixes are below. Both no-event cells have empty targets in every
condition, with zero recorded selector invocation and behavior bytes.

| Condition | Local null | Paired change |
| --- | --- | --- |
| own | z | a |
| swapped | a | z |
| sham | z | a |
| no-U | empty | empty |
| hand-authored | z | z |
| history-independent | a | a |
| traversal | a | a |
| retrieval | z | a |
| oracle | empty | a |

Local null has one false target for each of the seven selectors other than no-U
and oracle. Own/sham target the already-observed upper fact and generate no
inspection; swapped/history-independent/traversal request, start and resolve
one unnecessary lower inspection. These are confirmations, not stale corrections.
In paired change, own/sham/history-independent/traversal/retrieval/oracle target
correctly and request, start and resolve one lower inspection. Swapped and
hand-authored target the wrong upper fact; no-U misses the lower fact. Every
condition nevertheless corrects the lower fact at 358. Own/sham reach the goal
one tick later than no-U. Empty-target precision and empty-gold recall remain
undefined as declared.

**Sixteen core boundaries pass full U-only non-U invariants**: own/swapped/sham/
no-U inherit identical own selector configuration and provenance. The other five
baselines retain declared configuration/resources and are not U-only comparisons.
Retrieval alone receives historical E; oracle alone receives evaluator gold.
U artifacts retain their original E-only fitting provenance. All continuations
use real fixed CPU FLYNN `policy.act`, declared sensing and no motor override or
private steering. Source M is backed by actual packets from the
[admission gate](m5-remaining-02-admission.md); source acquisition remains
explicitly privileged manual supervision.

The [JSON index](m5-remaining-02-comparison.json) pins all UUIDs, full per-condition
scores, timing, resources and immutable evidence. Its **411 recording, worker,
SNP/index and runtime-job files total 1,095,601,849 bytes**; supervisors and outer
controls are separate. Primary report SHA is
`844f6aa82cd583f40b500902b4d166b499208c8272995f08d2d38bce1d0f2603`;
comparison plan SHA is
`909c3f3b86f346362cd521458cf4f3a9c7b5a8384eaee94ae88a154620be36c5`.
Original admission lineage and history bundles are unchanged.

Local retained audit passed first in 16.645 seconds using shared stage/evaluator
checks plus direct counts, hashes and exact own/sham input/output/action/pose
arrays. Root raw audit passed first in 16.232 seconds: all 4,650 rows, 40 SNPs,
16 strict boundaries, 577 source/upstream/asset entries and 120 input pins.
Independent root outcomes reconstruction passed first in 8.176 seconds for all
36 occupancy/gold, selection/inspection, timing, task and trajectory checks.
Both root scripts and receipts are pinned under sibling
`project-integration/runs/memory-remaining-02-comparison-root-audit-7a956b0/`.
Neither audit recomputed neural inference. Fixed controls and prepared/before/
after/enclosing inventories match. Cleanup independently checked **42
non-launcher PID/start pairs plus the launcher**, all absent, and the home writer
lease was available before release. The launcher's observed count 43 includes
that launcher; an earlier status message counted it twice and was corrected.

Fixed lower-route opportunity, namespace dependence, unequal local observation
and seed-dependent initialization remain. This is a development result retaining
null false targets and negative timing comparisons; no biological-learning,
operator-blindness, held-out or R2-completion claim is made. Hosted CI remains
blocked by account payments/spending limits; unchanged numerical runtime retains
the separate 697-test enabled local pass.
