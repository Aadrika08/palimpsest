# Fixed CPU FLYNN own-branch executable replay

Both predeclared replays passed once on source `3bcd311`, without divergence:
actions replay compared 129 transitions using recorded motors; policy replay
compared 129 transitions while executing actual `policy.act`. Both compared
835 lifecycle/memory events and retained goal boundary 429. This verifies
reproducibility for the completed own branch; it adds no memory timing or task
benefit to the [original nine-condition result](m5-flynn-memory-transfer.md).
All nine original conditions corrected the changed fact at tick 358 and reached
goal at tick 429, so the measured own-U timing/task benefit remains absent.

The original experiment was frozen at `6f355bd`; its own source run is
`12ef7a0db5af408fbdb47ad4de6c69b9`, with initial registered SNP
`c09d4c67786ba354f8e8ad9c088c0867bea9af56f93054a9e44406d3ffb9a540`.
Replay API commit `136f3f3` adds only the previously reviewed optional recording
limit and focused test, preserving atomic restoration and default callers. No
Engine, motor, model, graph, weight, sensor or memory policy changed. All twelve
required replay runtime hashes, upstream and lock match the original source;
`replay.py` is outside that compatibility set. The [frozen replay protocol](../plans/m5-flynn-replay.md)
and [machine-readable evidence](m5-flynn-replay.json) retain exact identities.

| Owner | Run ID | Compared ticks/events | Inference | Elapsed | Result |
| --- | --- | --- | --- | --- | --- |
| actions | `4147e5bd3ad344c79ac5aa9d55ed273f` | 129 / 835 | bypassed, recorded motors | 39.577 s | passed |
| policy | `7b623b4ce16a442bb45af4a5f4f24e03` | 129 / 835 | actual fixed CPU FLYNN | 41.341 s | passed |

The existing comparator requires exact integer/camera arrays and float absolute/
relative tolerance 1e-6. Policy replay also checks recorded encoded/raw inference
fields; actions replay explicitly excludes them. Wall latencies are excluded.
Both reports have `first_divergence=null`, no errors, correct inference/mode flags
and an explicit 192 MiB recording cap. The conditional atomic route restores the
same acquisition case, controller, world, hidden/retina state and RNG without
changing acquisition, replacing U/controller, or introducing hidden steering.

At each ready boundary, the registered initial SNP passed exact typed-state
comparison after excluding only destination recorder source ID, durable prefix
and declared execution mode. All M/E/U, selector, detector, cursor, requests,
active inspection, observation, physical/native/integration/model/controller and
RNG fields remain in that equality check. Common guard SHA is
`402e7fc3a1e7728c157741aed5320132bff8a3140f643d157e939096a26a5c95`.
Actions/policy SNP sizes are 1,153,125 / 1,153,124 bytes. The 16 MiB SNP check ran
after bounded publication, before the first replay tick; it is not a
pre-publication 16 MiB guarantee. Existing serializer and aggregate quota bound
publication. Source/native/index/worker/recording hashes remain unchanged.

The 360 s outer supervisor completed exit 0 in 83.192 s; elapsed time including
cleanup was 85.278 s. Both 160 s child supervisors completed exit 0. Four sampled
PID/start identities are now absent, with no surviving owner, forced cleanup
signal or monitor error. Full source/tests/lock/upstream/assets before/after
identities are equal. No retry, replacement scene or tuning occurred.

Retained raw paths are `runs/m5-flynn-replay-20261002` and
`runs/m5-flynn-replay-launch-3bcd311` in the memory-flynn-continuation worktree.
Gate report SHA is
`899b5c2b747da6c8c9fd45e87219bd71fbc3b778de85b00bd5e04b9e7b652fbe`;
launch report SHA is
`eca97263beb0efa96c821f2b55e3c71ff332ca3cc6e51cdcc94a6c0d3e333a02`.
The JSON indexes 14 recording files / 55,354,166 bytes and 22 recording/SNP/index/
worker/replay-report files / 57,666,202 bytes. Additional supervisors, logs,
control/monitor files and zero-byte leases are separately counted; they are not
included in those indexed totals.

A NumPy-only read-only audit passed in 4.858 s: all 281 frozen source/upstream/asset
identity files, ten original source files, both 129-row comparisons, native/full
initial guards, mode flags and four absent owner identities rechecked without
Torch/MuJoCo import. Root independently audited 32 indexed original-source and
destination files, both comparisons and initial/inference/cleanup guards in
0.938 s. Both audit scripts/results are retained with hashes in the JSON.

Evidence remains one local-cue development change case, with privileged manual
source acquisition and declared goal relocation before the neural anchor.
Counterbalanced physical-side/relation/lexical/goal-route cases, null/no-event
controls and reviewed held-out execution remain pending. No biological or R2
completion claim follows from these replays.
