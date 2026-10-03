# M5 fixed frozen-observation U diagnostic

Status: source-only preparation. No model/native launch, held-out access or new
acquisition is authorized until source and fresh controls are reviewed and GO is
given. Use the isolated `memory-observation-stream` checkout based on `480acfa`;
keep the producer at `memory-flynn-continuation` / `9393215` unchanged. The existing
six reference replays passed at `9dd805d`; this is the separate PRD §13.3/§15.2
sensor-stream diagnostic, not another executable trajectory replay.

## Fixed inputs and treatments

Use exactly the retained **own** stream for each selected cell. Unique `(cell,
stage=own)` joins must match both hash-pinned comparison plan and terminal report,
then reconcile the actual runtime job, B ancestor/history lineage, registered
initial SNP, worker report, every recorded row/policy-call hash and geometry gold.
No convenient alternative stream may replace a failed treatment.

| Wave | Cell | Own stream UUID | Intervals |
| --- | --- | --- | ---: |
| A / C4 | s25/local_cue/change | 3738f98942f94a058e8910fc950801c0 | 131 |
| A / C4 | s28/paired_cue/change | 961bb028d2ae44d984e54818d52de01d | 132 |
| A / C4 | s26/paired_cue/null | c40bde4304174a8eb2551f684de59001 | 128 |
| A / C4 | s31/local_cue/no-event | 092810659ed8484eb082559f69df015d | 130 |
| B / C3 | s24/local_cue/change | 4a91588188f3490798ea213f2b583796 | 130 |
| B / C3 | s29/paired_cue/change | 9e7b594954934d028b4a9302ab7eb270 | 131 |
| B / C3 | s30/local_cue/null | 027b3827af224839969285c70d161840 | 129 |
| B / C3 | s27/paired_cue/no-event | 49392deba7b74096a9b59b830c719a24 | 128 |

C4 plan/report SHA256: `f0ce3790bec39c29f59d7ea4490e35d669e4293d5565a68b9eddceca9a43d1a4` /
`91aa2aa30ae5a25daf0286f880b4372d66eca9eb98ee0b29fb4b8a54f5aefaf1`.
C3 plan/report: `f2389333ddbf0c6a0af00e38034261cadf735ecbd1da163bf1fb180f1cc03125` /
`c8ba721b0b861cb554811d78791a5f90a5bb2b7d2f2f4ff32e691db106aa376d`.
The verifier embeds all eight exact SNP hashes and source paths. A bounded
NumPy-only subprocess uses the frozen historical reader/PYTHONPATH; current
Engine code executes only in the new checkout. Audit their identities separately.

Every cell has own, swapped, sham and exact empty-U treatments. Own/swapped U are
existing E-only fitted artifacts, selected by the predeclared local/paired mapping;
sham is byte-identical own U. Historical E remains audit evidence, never a policy
or retrieval input. Live M/E, initial M, detector, cursor, requests, active target,
decisions, selector/version, world, graph/weights, controller and RNG all remain in
full initial `invariant_hashes`; only U and destination recorder identity/prefix
are excluded. No other five baseline resources or oracle input enter behavior.

## Explicit admission and C3 preparation

All raw C3/C4 SNPs use application schema 3. Prospectively reproduce only current
Engine's existing memory-profile compatibility upgrade: schema 3 without
`task_state` becomes schema 4 with `task_state=None`. Reject other schemas or an
already-present task field. Prove exact reversal yields the complete raw source
state, keep raw SNP bytes unchanged, record both digests and structural fields,
and pass that admitted copy to atomic restore. This matters because the existing
U-branch guard compares its supplied snapshot before/after restoration. Every
other field is unchanged; this is separate from selector preparation and U.

A uses the four existing C4 strict shared selectors, with no configuration change.
B first creates four newly named zero-tick preparations: configure only selector
`own`, limit 1, null resource/content hash and shared prospective B protocol
provenance. Both native and task proofs exclude **selector only**, retain task
version and exact U, and prove M/E/detector/cursor/requests/active/decisions and all
other state unchanged. Log/capture the preparation, then inherit it unchanged in
all four U forks. Historical C3 results are not relabelled strict U-only.

## Frozen stream, responses and failure semantics

Audit the complete source before model initialization or any policy call. Read
actual `memory_sensed` packets and lossless published RGB arrays. Exact contact
values come from recorded `neural_policy_call.sensors`, whose typed input/result
and camera hashes must match numeric rows. Reproduce every source task decision,
inspection/cue and full final memory using existing `advance_memory` first.

Each treatment atomic-restores the matched CPU FLYNN native/controller/RNG state.
For each actual consecutive packet, advance a local diagnostic memory copy, then
call real `FlynnPolicy.act` with the recorded RGB/contact and only the returned
visible cue bearing. Never call `Engine.advance`, `env.step`, a motor override,
private bearing/goal fallback, world schedule edit or manual driver. Engine/world
clocks and physical state stay at boundary 300; local diagnostic cursor advances.
The durable zero-row Engine recording/SNP proves admission. Separate labelled
JSONL/NPZ derivatives retain calls, task/cue decisions, revisions and neural arrays;
they cannot be consumed as a physically stepped recording or `replay_run` source.

Own/sham must reproduce source decisions/cues/inputs and numeric results under
existing 1e-6 absolute/relative tolerances. C4 task inspection prefixes match
exactly; C3 comparison substitutes only the explicitly prepared selector metadata,
never detector/cursor/request/M/E or task version. Own/sham final controller/RNG
hashes must agree. A missing required cue censors that treatment at its exact
boundary: no task state commits, no policy call, no fabricated decision or later
sample. Continue the remaining fixed treatments. Infrastructure, malformed stream,
identity, invariant, parity, quota or deadline failure stops the wave and retains
unattempted IDs; no retries or substitutions. Stop exactly at source termination;
its goal is context, not a counterfactual goal success. Extra attempted packets
without recorded numeric calls are rejected for these fixed completed sources.

Report actual committed targets versus independent retained occupancy/acquired-M
gold, false targets/precision/recall (undefined denominators stay null), censored
selection separately from abstention, correction versus unchanged confirmation,
inspection requests/resolutions/timeouts, first cue/neural/action differences and
shared prefix length. No-event has zero committed selector decisions/behavior
bytes/inspections; do not fabricate selection events. Behavior access is M,
witnessed trigger and U payload; envelope/history validation bytes are separate.
No minimum sensitivity or task-benefit threshold is imposed. Null/negative and
censored treatments remain results, not replacements.

## Finite bounds and scope

A has 16 serialized owners, maximum 4,800 policy calls, 4 GiB aggregate plus 2 GiB
floor; B has four zero-call preparations plus 16 stream owners, maximum 4,800 calls,
5 GiB plus 2 GiB floor. Exact fixed streams tighten complete-prefix calls to 2,084
and 2,072 respectively; these are ceilings, not promised completions. Each owner
has 160-second supervision/150-second final admission including cleanup and source
rechecks, 192 MiB combined zero-row recording plus derivative cap,
16 MiB initial SNP cap, 1 MiB streams and 64 MiB aggregate headroom. Retain no camera
duplicates in derivatives. Existing 4,813 float32 encoded inputs/two float32 outputs
and the conservative 121,975,592-byte 300-tick recording estimate remain upper
references. Maximum 208 MiB combined recording/derivative plus SNP per owner is the shared
numeric allowance; publication counts the existing recording bytes before
reserving derivative bytes. Controls/logs remain separately bounded inside the
aggregate. With 5 MiB per-owner streams/index/worker/supervisor plus 128 KiB job
controls and 90 MiB total plan/monitor/outer/headroom, conservative maxima are
3,500 MiB (A) and 4,352.5 MiB (B), below 4/5 GiB. Fresh-control preflight must bind
this non-duplicated layout.

A outer deadline is 2,620 seconds TERM/+15 KILL under 2,655-second supervision;
B is 3,260/+15 under 3,295. Single verifier-parent lease, existing bounded children,
finite PID/PPID/PGID/start monitor, exact start-verified descendant cleanup,
obtainable before/after inventories and any forced-signal operational failure.
Final publication/lease cleanup and the provisional printed return boundary are
included in elapsed admission; enclosing controls independently enforce cleanup-inclusive
2,655/3,295-second limits before operational pass. Controls must
freeze fresh UUIDs disjoint from all old gates, paths, code/tests/lock/upstream/assets
and historical input hashes before separate GO. No model/native was run while
preparing this source.

Supplied RGB/contact/occupancy belong to each recorded own-policy trajectory.
Counterfactual actions cannot alter that stream; direct targeting/cue/controller
sensitivity is not navigation, new task success, timing benefit or a self-consistent
counterfactual trajectory. These eight selected development cells do not complete
the 48-cell design, route/lexical/seed independence, held-out protocol, R2 acceptance,
biological fidelity or model necessity. Prior negative own-U benefit evidence and
all historical results stay unchanged; reserved held-out IDs remain unopened.
