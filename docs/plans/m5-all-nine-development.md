# M5 fixed two-block, all-nine development protocol

Implement one bounded targeting dispatch in the existing memory task and reuse the
current verifier. No actual execution is authorized until root review and source
freeze. Preserve [v4 evidence](../reports/m5-goal-handoff-v4.md) and PR29. This
protocol tests relation transfer only; it does not establish physical-side,
lexical-order, useful-memory, held-out or R2 effects. The lower common-goal route
confound remains explicit, and a null outcome is valid.

Fix two blocks, in this order:

| Block | Case | Historical generator case self-SHA at64c8ccb | Changed fact |
| --- | --- | --- | --- |
| Local | development-test seed 8/local/change | `02e99c315631db532ed86bfde2905e231a3ff4eecd926553ccc5e480ac788b9f` | `live-development-test-00000008-fact-a`, physical lower, local association |
| Paired | development-test seed 9/paired/change | `f395a8af24de074d0480595c6e0ee479a6c5be6303b3e9c63cd7f8c094d46239` | `live-development-test-00000009-fact-a`, physical lower, paired association |

These two historical hashes are not current raw-case pins. Adding dispatch changes
the memory-task source hash, then the world-profile and experiment protocol hashes.
The runner verifies every non-provenance case field through canonical semantic
hashes, excluding exactly the top-level `protocol_sha256`, `source_sha256` and
`case_sha256` fields. Seed8's semantic SHA is
`3750fa458baf335552ac168e0ad9a3c1cf39f76004d800baf7391e3b93c82635`;
seed9's is `d47f632b856a768632b0d9988e0847d41ac47eac18714d88dc724a842583fa61`.
They were checked against the historical64c8ccb generator with its original sensor
source pin. Each new plan retains and validates current whole-case canonical,
generator self-case and semantic hashes in `case_identities`; manifests and native
world state retain the exact current case. Historical recordings/bundles keep their
original source/world identities and pinned bytes unchanged.

Each block has a new unknown-M/empty-E/U source episode of 300 ticks, the fixed
source-only ticks 200–299 velocity-zero/yaw-nine-degrees preparation, and the existing
paused boundary-300 goal intervention to effective float32
`[-0.5,-2.700000047683716]`. Require actual evidence-backed open lower/upper facts,
actual packet299 visibility, separately labelled post-move visibility probe,
unchanged authoritative state/memory and native integration binding. Case, initial
goal and acquisition schedule stay unchanged. Local seed8 is an explicitly repeated
development instance, not a novel test. Do not reuse old source identities as new
ones or seed synthetic samples into live M.

For each source, create a zero-step own-U anchor, then fork exactly these nine
conditions: own, swapped, sham, no-U, hand-authored, history-independent, traversal,
retrieval, oracle. Thus there are exactly 22 serialized stages (two sources, two
anchors, eighteen continuations), no retries, replacement scenes, tuning or
conditional extra runs. Each continuation has at most 300 additional ticks,
velocity0.65 and the previous-published-declared-bearing driver. All stages retain
160-second external/150-second internal,192MiB recording and1MiB log bounds.
Stop on first failure and list remaining planned stages as unattempted.

Pin existing local history bundle SHA
`016c5b5e9472b116d065fb922b32d64089db6e27839aec09d751238f8ce7ffc1`,
U SHA `032d40d14192eadc66588a2b63339bb990750a1f70aef036a54453f8746ed9bb`,
and paired bundle SHA
`64628e37cc6e861194f810baa92926eba8f57260047cdd8ad320a4601023d213`,
U SHA `aa37a394fee509275adddb06355388c23e5ef9e8d31c3306327ac29d54800700`.
Own and sham/anchor use local U for seed8 and paired U for seed9; swapped uses the
other artifact. Revalidate exact E-only refits and disjoint current/history IDs.
Only retrieval receives the matching full historical E; current live E remains
empty. No current case, gold or bank enters fitting.

Use a versioned bounded selector configuration in memory-task state, preserving
legacy version1 unchanged. Default legacy selection remains `memory.select`.
Configured dispatch calls the existing shared `selection_for_condition` with a
budget of one; artifact conditions use current U, retrieval gets only its declared
E resource, oracle gets only its declared gold IDs. Other conditions receive no
historical E or gold. Validate/reset/restore configuration through the shared task
validator; add no Engine application schema. Condition/resource provenance,
canonical hashes and access bytes must be retained. Motors/inspection bridge still
receive only existing declared bearings and target requests.

The API is `memory_task.configure_selector(state, config) -> normalized_state`.
Legacy task version1 has exactly its existing fields, update audit and public
inspection result. Configured task version2 adds only `selector`, with strict keys
`version=1`, `condition`, `limit=1`, `resource`, `resource_sha256` and
`provenance_sha256`. U stays in its existing field. Resource is `None` except
retrieval's validated full E or oracle's unique, non-dangling gold-ID list. The cap
is the existing4MiB E allowance plus2KiB of fixed configuration overhead, with
explicit rejection and no truncation. Current live E remains empty. The metadata
snapshot ceiling still applies independently. Provenance is the matching immutable
history-bundle hash, the fixed protocol hash for independent/authored conditions,
or a hash of independently bound actual donor evidence for oracle. Native state,
manifest and the prefix-bound `selector_configured` event must all agree exactly.
Public inspection exposes condition/hashes/byte count, not the full E resource.

Every worker may read full pinned E to audit E-only refits before using U; this is
validation access, not selector behavior access. Only retrieval dispatch receives
historical E. Target-score output reports payload, envelope, history and behavior
bytes separately. Neither current history acquisition nor this source prefix is
passed to fitting.

All nine forks preserve native physical/model/controller/RNG/M/E/cursor/supervisor
state, permitting only declared selector configuration/resource and U differences.
Call this a selector comparison, not nine U-only branches. Keep a narrowly scoped
invariant normalization for selector configuration/version plus the existing U
exclusion; do not ignore other scientific state. The zero-step own anchor and four
original artifact conditions retain their explicit U identities and sham parity.

The oracle's targets must derive from independently evaluated actual source before
and own-branch post cylinder clearance plus the actual witnessed trigger, rather
than from regime labels or selection. Own runs first; if its required actual
recording/proof is unavailable, stop. Oracle alone is explicitly privileged at
targeting. It gets no hidden goal/inspection bearing or navigation rescue. Require
all recorded branch post geometry to agree before comparing outcomes.

Oracle evidence retains source/own run IDs, source snapshot hash, recording file
content-index hashes, worker-report hashes, pre-M hash, retained before/post
circles, and the actual trigger. Reconstruct the trigger from native cue299 and
actual packet300; reject a summary without matching consecutive visible samples.
Before launching oracle, the parent constructs this evidence from validated source
and own recordings; the oracle worker rereads those donors with existing terminal,
chunk/count and initial-snapshot readers, checks block/case/protocol identity and
recomputes exact evidence. Its task receives only gold IDs. Own runs first; no
actual donor means no oracle execution. All other jobs have `oracle_evidence=None`.

| Condition | Distinguishing access/behavior |
| --- | --- |
| Own/swapped | Learned local/paired relation transfer across IDs; wrong relation control |
| Sham | Same own artifact and inert replacement; exact branch parity |
| No-U | Abstention; separates deliberate targeting from incidental direct sensing |
| Hand-authored | Frozen local rule: lower/correct in8, upper/wrong in9 |
| History-independent | First bank fact-a: correct in both chosen blocks; no learned advantage demonstrated |
| Traversal | First cue-associated fact-a: correct in both; same limitation |
| Retrieval | Latest complete matching historical episode; full-E versus compact-U access |
| Oracle | Actual-geometry gold targeting ceiling; no privileged steering |

Report every target set/false target/missed target/abstention, requested/started/
resolved/timeout disposition, first correct observed and committed occupancy,
uncertainty duration, final navigation/revision/task scores, goal ticks and source/
recording/native/history/config hashes. Separate evaluator scores from the worker's
conservative placeholder. Do not treat frames as independent samples. V4 showed
all four branches repaired lower at354 and reached goal426; the relocated goal may
again make all nine succeed without an own-U benefit. Other physical-side/lexical
counterbalances, null/no-event cases and a reviewed held-out protocol remain later
work, with no outcome-driven geometry change in this slice.

First correct observation is the earliest actual passage sample matching retained
post geometry at or after300. First correct commitment is the earliest recorded
revision whose resulting fact is observed and matches that geometry. A sensed
sample discarded during a failed atomic boundary has no committed revision.
Uncertainty intervals run from recorded entry into `uncertain` to its recorded
resolution, in control ticks; unresolved intervals are explicitly censored at the
terminal control boundary. Same-boundary resolution has duration zero. Worker
`task_pass=False` is retained as a conservative placeholder; the evaluator reports
navigation and fresh-correct revision independently, with task pass requiring both
and no unresolved inspection. Failures retain their actual phase/outcome and never
become accepted completion. Reports contain one comparison per block, not pooled
frame samples.

Prepare-only command (no simulator initialization):

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/verify_memory_transfer.py \
  --repo "$PWD" \
  --assets /home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn \
  --output "$PWD/runs/m5-all-nine-development-20261002" --plan-only
```

After root reviews, commits and freezes source, the same command without
`--plan-only` is the fixed22-stage actual gate. It requires an exclusive runtime
slot; no execution has occurred during this preparation. Maximum child execution
is22×160seconds; the launch owner must retain an external whole-gate watchdog and
normal process-group cleanup. Do not add runs or retries after examining outcomes.
