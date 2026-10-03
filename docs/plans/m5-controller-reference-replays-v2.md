# M5 controller-reference replay v2: source path admission correction

Status: the separately frozen six-owner v2 gate completed and passed at source
`9dd805d`; see [audited evidence](../reports/m5-controller-reference-replays-v2.md).
No further native gate or held-out access is authorized. The preparation sections
below are historical. Preserve the [v1 zero-row failure](../reports/m5-controller-reference-replays-v1.md), its
source `5d293bf`, controls, output, five unattempted IDs and all review receipts.
The v1 producer/executor paths stay unchanged. Author and later execute this
separately frozen correction in `.worktrees/memory-reference-replay-v2`.

The only verifier behavior change wraps the JSON source path with `Path` before
the existing `artifacts._events` call in `ready_guard`. The helper's contract and
all production Engine/replay/snapshot/controller/sensor code remain unchanged.
No threshold, tolerated difference, native guard, selected source, schedule,
action/policy comparison, maximum row count or scientific condition changes.

The focused regression uses real bounded snapshot/event files with synthetic
state, no native decoding and no retained data dependency. It reproduced the
exact v1 TypeError through real `ready_guard` and `_events` before the call-site
correction, then passed afterward. It also checks the helper still rejects a
direct string argument and an altered initial invariant digest rejects.
These fixtures are not executable replay qualification.

Reuse the [original six-owner protocol](m5-controller-reference-replays.md):
same three s24 recordings/SNP hashes, actions then policy per reference, 742
maximum rows and only 129 possible neural inference rows, 160/150-second owner
deadlines, 192 MiB recordings and 16 MiB registered-SNP ready cap, one inner
lease, 2 GiB aggregate plus 2 GiB floor and 64 MiB headroom, 1020-second TERM /
15-second KILL grace under 1055-second supervision with final elapsed admission.

After evidence/source review, prepare six fresh UUIDs disjoint from v1 and prior
plans, fresh v2 output/control roots, new executor/driver/document inventories
and exact launcher/plan/meta hashes. Keep sources, relevant runtime compatibility
and assets pinned to the completed reference producer. Reuse the reviewed
corrected monitor/after-inventory/cleanup wrapper, without a same-source retry.
Any later first failure stops and retains the remaining queue. No new acquisition,
held-out access, motor rescue, U change or R2/benefit claim is authorized here.
