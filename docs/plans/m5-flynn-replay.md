# Fixed CPU FLYNN own-branch executable replay v1

Preparation only until separate runtime GO. This adds exactly two fresh owners to
replay the already completed own branch, in order: actions, then policy. It does
not rerun, replace, tune or extend the twelve-stage experiment, its nine conditions,
or any earlier manual data. Failure stops immediately and retains the unattempted
second owner; there are no retries. The gate checks reproducibility, not a new
memory benefit, counterbalance, null/no-event schedule, held-out result or R2 claim.

## Immutable source and conditional admission

Original experiment source is `6f355bdd9c0144c278c90cf53b468b429775fb8a`.
The own run is `12ef7a0db5af408fbdb47ad4de6c69b9`, beneath
`runs/m5-flynn-memory-transfer-20261002/runs/`. It has exactly 129 recorded
transitions at episode 0 ticks 300–428, ending at goal boundary 429. Its primary
experiment report SHA is
`f07a40e8cc6c84f307ef96d1ab2a4358969eb3d080a9e3ea450c629966c92f58`.
The initial registered SNP SHA is
`c09d4c67786ba354f8e8ad9c088c0867bea9af56f93054a9e44406d3ffb9a540`;
registration ID is `0a6a0d95cab94222ad56ff47ecda5dd4`. Its durable prefix, case,
source identity, full model/hidden/RNG/application state and complete recording
chunks must pass the existing authoritative readers. Preparation pins all source
recording files, SNP/index, worker report and primary experiment report; every
owner rechecks the same pins before and after execution.

Replay API source `136f3f3e893e5cbef553d9cd8cd33806eb7aa527` reuses the already
reviewed optional `replay_run(recording_max_bytes=None)` API from adaptive commit
`2abc9da`; omission preserves default callers. It preserves atomic restoration
and changes no Engine, policy, graph, weight, sensor, bridge or motor code. The
prepared launcher binds its final clean source commit independently from the
original experiment commit. Before GO and at owner startup, all twelve
`replay._RUNTIME` hashes, upstream and lock must match the original recorded
provenance exactly. `replay.py` is outside that runtime set; no compatibility
relaxation is permitted. Full current source/test/lock, actual pinned upstream and
asset inventories are independently recorded before and after.

Both destinations use the existing conditional acquisition-case CPU FLYNN atomic
restore route, same validated case and registered snapshot. No acquisition flag
is changed. Neither replaces the controller or U. At the ready boundary, read the
actually registered destination SNP and compare every typed snapshot field
exactly after excluding only destination recorder source ID, durable event prefix
and the explicitly changed execution mode. Memory M/E/U, selector, detector,
cursor, requests, active inspection, world/native/integration/model/controller
state and every RNG remain in that equality check. Retain each excluded field
with its explicit label. The original source remains byte/hash unchanged.

## Comparison and bounds

Actions replay executes the recorded motors, bypassing inference as explicitly
reported by the existing replay API. Policy replay executes real `policy.act`
with no action override or private/manual driver. Both restore the same fixed
CPU environment, model, hidden state and RNG. Existing replay compares every
physical tick, cameras/integers exactly and floats at absolute/relative 1e-6;
policy mode additionally compares all recorded inference fields except declared
wall latencies. Lifecycle/memory events and final phase/metrics/outcome use the
existing comparator. Passing requires exactly 129 compared ticks, authoritative
completed destination recordings, unchanged source, bound native/initial state,
matching source snapshot identity and correct inference/execution flags. Preserve
first divergence, failed report, supervisor and logs without interpretation as
success. No additional policy-call wrapper, rescue or scoring condition is added.

Two sequential children have 160 s external and 150 s callback wall limits each.
The aggregate launcher has 360 s (including 40 s audit/cleanup allowance),
512 MiB combined output/control allowance, 2 GiB free-space floor, 32 MiB reserved
control/log headroom, 1 MiB per stdout/stderr stream and 8 MiB ownership log.
Preflight requires the full 512 MiB allowance plus floor and headroom before
allocation. Existing StorageBudget admits one payload writer under its lease.
Explicit `recording_max_bytes=192*MiB` uses existing RunWriter admission and must
appear in each manifest. The original neural resource derivation of 216,094 raw
numeric/camera bytes per tick yields 27,876,126 bytes for 129 transitions, before
NPZ/event/metadata overhead; 192 MiB retains the previously reviewed margin.

Exactly one registered initial SNP per destination is allowed (two total).
The 16 MiB per-SNP check occurs at replay progress `ready`, after existing bounded
serializer publication and before any replay tick; this is deliberately not a
16 MiB pre-publication guarantee. Existing serializer and aggregate StorageBudget
bound publication. No snapshot-budget adapter or recording-quota subclass is
introduced. The actual source SNP is about 1 MiB; its exact bytes are in the plan.

Preparation pre-creates and pins exactly two UUID directories and job IDs, launcher
SHA, protocol SHA and plan SHA. The retained ignored launcher composes existing
bounded_process and the previously reviewed PID/start/PPID/PGID/session monitor,
with exact plan-bound child argv. Cleanup signals only start-verified owned
survivors; any forced signal, surviving owner, monitor error, quota/watchdog error
or source mismatch fails the operational gate. First failure and both planned
owner statuses remain retained; no model job is authorized by preparation.
