# Fixed puck mechanics v2 — prepared, not executed

This verifier implements the mechanics stage of the frozen
[puck plan](m6-puck-pushing.md) and [v2 task protocol](m6-puck-pushing-protocol-v2.json).
The [v2 mechanics contract](m6-puck-mechanics-v2.json) pins its lifecycle and
resources without changing the disk, fixed actions, layouts or task thresholds.
V2 changes only the analytical teacher target-selection rule described below. The prior [v4 construction result](../reports/m6-puck-construction-v4.md)
qualifies zero-step construction only. This gate has **not** established contact
stability, pushing, continuation or learned control.

`verify_puck_mechanics.py` is an explicit **pre-product exception** to the plan's
prospective LabSupervisor ownership sentence: ten serialized, separately
supervised subprocesses directly own the existing fixed-profile environment.
There is no Engine, worker, REST, UI, registry or production snapshot change.
Product wiring and a separately trained controller remain later reviewed work.
No Torch, training, external camera, network or physical hardware is involved.

V1 remains a [failed mechanics result](../reports/m6-puck-mechanics-v1.md) at
`0560886`; both original protocol JSON files and every raw artifact remain
unchanged. V2 chooses the goal direction whenever the **existing** axial/lateral
push corridor is ready, or the existing behind-point arrival test passes.
Otherwise it still approaches the behind point. Stop priority, heading alignment,
velocity/heading caps, numerical thresholds, state, layouts and all budgets are
unchanged. No hysteresis or added controller state is introduced. These are the
same already-inspected development scenes, not fresh held-out scenes.

The caller review found the analytical teacher is used only by this standalone
mechanics verifier and pure tests. The XML derivation, installer, authored reset,
contact interpretation, task transition and native snapshot helpers are unchanged.
New task and gate hashes bind the current profile/application identity; a v1
cursor or snapshot is rejected before native restore. The numeric record schema
remains v1 because its fields are unchanged; its protocol hashes distinguish the
new semantics. The historical construction verifier deliberately retains its old
module pin and rejects this checkout; reproduce it at its committed source.
Unchanged XML bytes and expected native hashes do not automatically transfer
construction qualification to v2. Each prospective fresh owner must still admit,
construct and check the fixed model, then pass its own mechanics conditions.

| Owner order | Fixed source/layout | Maximum control ticks | Owner storage |
| --- | --- | ---: | ---: |
| zero | 5990, command `[0, 0]` | 120 | 64 MiB |
| push-positive | 5991, command `[.25, 0]` | 120 | 64 MiB |
| push-negative | 5992, command `[.25, 0]` | 120 | 64 MiB |
| teacher-positive | 5993, frozen privileged demonstrator | 600 | 160 MiB |
| teacher-negative | 5994, frozen privileged demonstrator | 600 | 160 MiB |
| continue-tick1 | teacher-positive after completed tick 1 | 4 | 32 MiB |
| continue-contact | teacher-positive at first contact interval end | 4 | 32 MiB |
| continue-dwell | teacher-positive at first `dwell_ticks == 1` | 4 | 32 MiB |
| replay-actions | push-positive initial native snapshot | 120 | 64 MiB |
| replay-policy | teacher-positive initial native snapshot | exact source episode, ≤600 | 160 MiB |

The five layouts and commands come directly from the frozen task JSON. The zero
case checks maximum displacement over all ticks, ≤.001 m, with no rover-puck
contact. Each constant push requires actual contact and ≥.1 m final displacement
in its declared X direction. Both demonstrators must reach the unchanged
10-tick dwell goal. These are analytical/mechanical checks, never learned success.
Any task, protocol, storage, watchdog or infrastructure failure stops the batch;
all later planned rows stay `not_started`. A completed natural failure retains
its completed record and actual task reason, while the gate fails. No retry,
replacement layout, later trigger selection or parameter adjustment is allowed.

Every control tick projects eight float32 values from **current qpos/qvel** and
the prior interval contact summary, selects one command, then runs the pinned
upstream ten .002 s Euler steps. The teacher uses privileged world coordinates;
these eight virtual sensors are an explicit authored interface, not biological
sensing. Fixed float64 layout/site coordinates define the puck goal. Upstream
float32 goal caches and navigation reward/done/truncated/stall flags are retained
as separate diagnostics; they never stop, reward or reset the puck task. After
stepping, the upstream obstacle cache is updated from current puck qpos; cached
positions are never written into native physics.

`ContactProbe` observes the ten actual pre-integration contact caches, from
`t` through `t+.018`, followed by the unchanged final cached contact list while
current qpos is at `t+.02`. It must observe exactly ten stages and constant actual
wheel controls. There is no extra `mj_forward` after an interval. Its original
calibration classes remain in the raw numeric packet; `puck.classify_contacts`
separately distinguishes intended rover-puck contact, puck-floor support, named
rover-floor support and failures. Initial contacts are explicitly forwarded
zero-time contacts, not a fabricated previous interval. Probe coverage failure
retains its bounded partial packets and cannot publish a fabricated complete row.

The callback is removed after every interval. At a snapshot boundary the
synchronous step has returned, the writer is flushed, and no next control is
admitted until capture ends. "Paused" describes this lifecycle, not zero body
velocity or zero next command. The first qualifying dwell tick is captured even
if the teacher's next command is nonzero: task distance ≤.2 and speed ≤.03 differ
from the teacher's ≤.18 stop rule. Its actual velocity is retained, and the next
command is the source record's next action. Missing first contact/dwell, a terminal
boundary, or fewer than four source successors fails; no later boundary is used.

Snapshots retain full native bytes and the existing `mjSTATE_INTEGRATION` audit.
A verifier-owned, hash-bound generic application payload carries the fixed puck
identity, full model hash, source case, task cursor, exact world, contact summary
and projected inputs. Before native decoding, each source snapshot must match
its completed owner's receipt, ≤8 MiB file and uncompressed member limits, and
pure cursor/input checks. After restore, validate all cached named bindings,
current qpos/qvel/world, full model and cursor before movement; construct a new
probe for the new native addresses. Generic snapshot restore stages native
resources and closes its retired renderer. This does not add puck admission to
production snapshot/replay APIs. Native allocation padding and diagnostic timer
bytes are retained; cross-owner raw-byte equality is not a mechanics criterion.

A recorded row includes the exact pre-action eight inputs, actual pre-action
camera frames (not controller inputs), action, post-step controls/qpos/qvel/
applied forces, before/after world, all contact numeric packets, puck reward,
exact task/world/contact hash and upstream diagnostics. `RunWriter` publishes
bounded numeric chunks; `iter_ticks` revalidates their checksums, schema and
coverage. All floats must be finite. Each derivative compares every recorded
array's exact dtype, shape and bytes, including images and inputs. Action replay
uses only recorded actions; policy replay and native continuations invoke the
same stateless demonstrator once per interval. Neither makes a learned claim.
Source rows and snapshots remain immutable; both child and parent check parity.

Per-owner startup is 60 s, progress 30 s and total 180 s. A script-local watchdog
uses existing `/proc` descendant/identity helpers and `bounded_process`. Before
any child receipt it identifies a **new direct child** whose full command argv
matches this owner's exact invocation and whose PID equals its new session's
PGID. It excludes pre-existing descendants, the verifier PID and verifier group.
Atomic progress receipts bind owner name, PID, process-start ticks and PGID;
completed control ticks may only advance, and startup cannot resume after ready.
An unchanged tick does not refresh the progress deadline. Poll period is .1 s.
On timeout/error, only the still-matching direct owner identity/group can receive
TERM, then KILL after 3 s if needed; any such action fails the gate. The existing
180 s supervisor remains a backstop even when no trusted receipt arrives.
Its terminal return code, exact PID/start and group absence, bounded observed
process inventory (≤128), renderer/callback closure and final source/model hashes
must all pass. Sampling cannot prove observation of every transient process.

The verifier alone holds the existing per-user storage lease; the retained outer
launcher must not acquire it again. Owner allowances sum to **832 MiB** under the
1 GiB stage cap, leaving 192 MiB for controls/logs; 8 MiB concurrent headroom is
reserved. Before first control, each owner reserves its exact 4/120/600-tick upper
bound at ≤128 KiB numeric arrays plus ≤16 KiB interval event per tick, 1 MiB chunk
metadata allowance, and ≤8 MiB per planned snapshot. Actual writes are checked
again. These are conservative byte estimates, not measured runtime throughput.
Each log is ≤1 MiB, JSON ≤4 MiB, snapshot ≤8 MiB; free space must remain ≥1 GiB.
The declared retention root, including prior retained evidence, is capped at
16 GiB. Full remaining owner allowances are checked before each owner. No cap is
extended on observed failure. The 600 s internal budget admits a new owner only
if its full 180 s remaining ceiling fits. The retained outer layers are exactly
TERM at 660 s, KILL grace 15 s, inside `bounded_process` at 680 s.

After focused pure fixtures and root review, freeze the source and retain a
hash-pinned launcher/plan before any execution:

```sh
PYTHONPATH=src ../lab-hardening/.venv/bin/python scripts/verify_puck_mechanics.py \
  --repo "$PWD" --expected-commit FROZEN_HEAD \
  --output runs/m6-puck-mechanics-v2-YYYYMMDD/gate --retention-root runs
```

The actual invocation must use the reviewed outer launcher, not this unbounded
shell example. Execution requires a separate coordinator GO and exclusive native
slot. Independent terminal audit must cover every planned status, raw record,
source/model identity, exact selected boundary/successors, outcomes and cleanup.
No downstream teacher collection, learning or physical qualification follows
automatically from this gate.

V2 preparation validation: 85 focused pure tests passed in 0.881 s, no skips.
The actual v1 tick-109 fixture failed with the old `[0, -.4]` action before the
correction, then passed with `[.2, -.03331900718597027]`. Reflected, outside-corridor,
misaligned and stop-priority checks pass; numeric/physics/layout/budget equality
and explicit historical task/snapshot/construction-pin rejection are covered.
These are pure counterfactual checks at seen development states, not a v2 native
result or proof of task completion.
