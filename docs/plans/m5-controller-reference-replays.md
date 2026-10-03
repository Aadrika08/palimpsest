# M5: six fixed s24 controller-reference executable replays

Status: the one frozen v1 attempt at `5d293bf` failed in the first ready guard
before any comparison; five owners remain unattempted. See the [retained failure
evidence](../reports/m5-controller-reference-replays-v1.md). The original protocol
below is historical; it authorizes no retry, later replay gate or held-out access.
The completed reference producer and earlier null/negative own-U results remain
unchanged. Replay compatibility and R2 completion are not established.

Use the three successful s24/local_cue/change recordings from producer
`169e0c8ac75be713d9cda0bdd852b926ec1261cc`, under the unchanged physical
`.worktrees/memory-controller-references` path. Its reference-report SHA256 is
`982c287ea591f3906b0218a0e52263fd38b75aa35148500b6078bd4d728ccb05`.
Join each fixed mode uniquely against that report, verifying the complete
recording index, worker hash, authoritative completed reader, registered SNP,
typed source inputs/outputs, source admission and actual producer upstream/assets.

| Reference | Source run | Rows | Initial SNP SHA256 |
| --- | --- | ---: | --- |
| Original checkpoint | `f1cefefc5e994f41a35ada0e8a5c2b18` | 129 | `50836512b963bed188a17d133367893d9f589204d9beec33d59f32b3ca87cd0b` |
| Visible-goal/contact script | `54608f3879704eb4aa6eb794af4a0a48` | 124 | `e182973a62bead2034e1023b6010fefba9f7f1d5b798c716a11ec27fbf64d420` |
| Privileged teacher | `cc6b99347a864452b158a21437a3a029` | 118 | `0e1dca845f5747ad1596ca6b071c9bc8a151002b5412553c81b8e07957171be1` |

Exactly six serialized fresh owners: original actions, original policy, script
actions, script policy, teacher actions, teacher policy. Maximum 742 rows; no
new source, acquisition, controller/U replacement, rescue, retry or tuning.
Actions replay uses saved motors and explicitly bypasses inference. Policy
replay recomputes the real existing controller route: original CPU FLYNN,
non-neural script or non-neural teacher. Only the original policy replay is
neural inference; neither non-neural reference is relabelled FLYNN. The original
true-pose/goal bearing and privileged teacher remain unequal-information
references. The earlier negative/null own-U benefit result is unchanged.

The new isolated executor is `.worktrees/memory-reference-replay`, based on
evidence commit `042cc26`, with actual upstream initialized from local objects
at `8d964599119b420de67ee259434d273651a1a76d`. Producer and historical paths stay
frozen. The existing `replay_run` conditional reference route atomically restores
each original reference SNP with the same controller, case and RNG. Every
relevant runtime hash (including `memory_reference.py`), upstream and lock must
match the recorded producer; no compatibility relaxation or production edit.
Track original producer and newly frozen executor commits separately.

At `ready`, require exactly one registered destination initial SNP, its checksum
and size at most 16 MiB. Compare the full typed snapshot digest after excluding
only destination `source_run_id`, durable `event_prefix`, and `execution_mode`.
Retain all physics/integration/model/observation, controller/teacher state, every
RNG, command/receipt state, world schedule/case and entire memory audit state in
that comparison. This is a post-publication/pre-tick size check; existing bounded
serialization and aggregate StorageBudget bound publication. No snapshot adapter.

The existing replay comparator checks cameras/integers exactly and floats at
absolute/relative 1e-6, reports first divergence, compares reference input/sensor/
teacher-cache events, lifecycle and terminal state. Policy mode additionally
compares inference fields; action mode declares its existing exclusions. The
source policy/teacher audit wrappers are not installed in destinations; their
source row/call linkage is verified, while policy rerun is bound by the existing
numeric/event comparator. Do not claim new per-call audit events were generated.
All source/native files stay hash-identical. Verify exact replay source/SNP,
atomic admission, mode/inference flags, recorded row count, final goal boundary,
worker cleanup and initial preservation again after each owner. Any divergence,
unrecorded failure or infrastructure/invariant error stops with the remaining
owners unattempted; retain every report and log. No failure is coerced to pass.

Per owner: 160-second watchdog, 150-second callback/internal admission including
final replay close and source checks, 192 MiB RunWriter recording cap, 16 MiB
registered initial SNP check before the first replay tick, 1 MiB per stream.
Aggregate: 2 GiB for output plus outer controls, 2 GiB free floor, 64 MiB headroom;
one verifier-parent writer lease and serialized children. Six 208 MiB recording/
SNP maxima total 1,308,622,848 bytes. Adding the same bounded six-owner envelopes,
streams, monitor, plan/report and headroom gives the prior conservative
1,435,238,400-byte estimate, below 2 GiB. Do not budget from successful lengths
alone. The fixed maximum is 742 rows, including 129 actual neural policy-replay
rows; action replay rows do not count as neural inference.

Outer bound: 1,020 seconds TERM, 15-second KILL grace under a 1,055-second
supervisor, with final aggregate elapsed admission after source checks. Reuse
the reviewed C3/C4/reference monitor, start-verified owned-descendant cleanup,
argv reread exit-race guard and obtainable after-inventory publication. Any
forced signal, survivor, monitor/watchdog/quota error or drift fails the
operational gate. Freeze six disjoint UUIDs, source/SNP/report/runtime pins,
launcher/plan/inventory hashes and full tracked/tests/lock/upstream/assets and
source-artifact inventories before a separate one-shot GO. Parent handles later
integration/release scope; held-out reservations and the frozen-observation
diagnostic remain unopened and unimplemented here.

Focused fixtures check real fixed job/plan validators, snapshot normalization
retaining memory/controller/RNG/physics/commands, late finalization rejection,
and before-next-owner failure accounting without retained data or native/model
construction. Read-only source preparation additionally uses actual authoritative
readers and compatibility checks; it cannot prove executable replay by itself.
