# M5 recorded-history acquisition, development contract

This slice implements offline evidence collection, not acquisition or held-out
execution. All regression recordings are authored synthetic fixtures. They are
not physically acquired history, embodied transfer or R2 completion. The existing
[synthetic targeting protocol](m5-development-protocol.md) remains development-only.

## Collector and admission

`memory_history.collect_history(run_paths)` takes a list/tuple of completed
authoritative **run directories** and returns a bounded plain-JSON audit bundle:
`e`, `u = memory.fit(e)`, `sources`, `links`, scoped `independence`, hashes and
separate retained-history, U-payload and U-envelope byte counts. Nothing is written.
Run ordering is canonical by run ID; duplicate sources are rejected.

It preflights recorded input sizes and uses the existing artifact reader, which
exhausts the numeric recording reader to verify chunk checksums, terminal aggregate
counts and `completed` status. It hashes manifest, events and published chunks and
checks file fingerprints before/after reading and again after collection/fitting. This is local consistency evidence,
not a signature or independent guarantee of source authenticity. Geometry is
validated by that reader; the collector never derives observations from it or
copies it into E.

Every recorded control tick must have exactly one `memory_sensed` packet and one
complete `memory_inspected` bank/U, in their recorded boundary order, with linked
`memory_decision` events between them. Episodes start at tick zero with contiguous
episode numbers starting at zero; outer memory-event ticks must equal prior recorded
episode lengths plus the local tick. Every event carrying a run ID must agree with
the manifest, including `engine_opened` and world events. Packet IDs,
subject IDs, episode/tick identities, bank hashes, retained factual evidence and
complete association counts are checked. Initial M must be unknown, E empty and
U hash-bound. This first collector rejects branch/restoration/replay, controller
replacement, runtime failures and a changing bank or U.

Acquisition controller is checked against the recorded `engine_opened` event;
`teacher_privileged` is retained and must agree with its controller label. Full U
must have an empty rule payload throughout, trigger selections must be empty with
`no_rule`, and each bridge must use the visible public common-goal landmark and its
recorded bearing. An inspection route is rejected. The declared result is exactly
**no engine U guidance**, with `u_guidance_used=false`; the selector still consumes
empty U on a trigger. Operator blindness, absence of external knowledge and source
authenticity are explicitly unverified. Teacher access would remain privileged;
the current memory-passages runtime disallows teacher, and the teacher-labelled
synthetic regression fixture does not establish its runtime support.

## Evidence construction

A trigger is accepted only if reconstructible from consecutive recorded packets
in which the same cue is visible with distinct tokens, including its deterministic
before/after observation IDs. A cue disappearing and reappearing is not evidence
of a witnessed change. Recorded trigger/selection lists must match this construction.
The collector supports one trigger per recorded episode; more triggers reject the
recording, rather than blending outcomes or inventing independent episodes.

For each `local_cue`/`paired_cue` relationship, the public recorded bank must identify
one unambiguous subject associated with the observed cue. Use the nearest actually
observed sample before the trigger and the first actually observed sample at/after
it, from that subject and episode. Require `before.tick < trigger.tick <= after.tick`.
If a phase has only recorded `unobserved` samples, retain its nearest recorded
sample and audit the gap; fitting cannot count it as unchanged. If no valid sample
pair or association exists, omit the relation check and retain its linked gap.
No observation is fabricated. A no-trigger episode produces an audit gap and no
historical episode. Observed equal passage values are legitimate unchanged checks;
missing/occluded values never become negative evidence.

New E IDs are deterministic namespaces of source run/episode/raw IDs, preventing
collisions between runs that reuse `episode-0` and sensor IDs. Links preserve raw
run, episode, trigger, fact and subject IDs, packet/event sequences, ticks, sample
hashes, bank hash and the recording content identity. Full source recordings must
remain available for audit; the bundle is not a replacement for those recordings.

Only validated E enters `fit`. No world geometry, regime, test bank, future evaluator
gold, acquisition controller or audit metadata enters fitting. Its existing fixed
support thresholds still apply; partial or insufficient histories can yield empty U.
Frames are not treated as independent experimental samples.

## Bounds and pending actual acquisition

Fixed engineering ceilings: 16 input runs, 512 MiB aggregate manifest/event/chunk
bytes, the existing 1024 historical episodes/4 MiB E cap, and an 8 MiB whole-bundle
cap. Complete banks are limited by the existing inspector to 16 facts and eight
associations per fact; any truncation rejects collection. Ambiguous relation/subject
mapping also rejects it. Every ceiling fails explicitly; there is no silent truncation.
Protocol and collector-source hashes identify these choices. These limits are not
scientific success thresholds and may make a large camera-rich run ineligible.

A separate [manual development pilot](m5-runtime-cases.md) recorded one actual
acquisition with visible pre/post evidence. Its collected E has one observed check
per relation and fitted U abstains under the fixed four-support threshold. The
[bounded batch protocol](m5-acquisition-batch.md) prepares four fresh acquisitions
per regime without reusing that pilot. The 512 MiB aggregate cap replaces 256 MiB
because four measured 84.3 MB camera-rich pilot-size recordings would exceed the
old cap. This engineering cap is bound in the collector protocol hash and still
rejects explicitly; it does not change E bounds or fitting thresholds. Missing
samples remain gaps. The authored gate schedule itself is not observed evidence.

Current recordings already provide the required fields for this bounded collector.
Older/truncated records are rejected. Supporting broader acquisition would require
complete hash-bound bank associations when inspector caps are exceeded, an explicit
acquisition policy/objective and its identity/allowed inputs, and a recorded schedule
that proves the required visible pre/post coverage. Operator-blind acquisition needs
its own auditable design; a manifest assertion alone is insufficient. No engine,
CLI or UI change, learned exploration/manipulation claim, held-out freeze or model
job is part of this slice.

## Verification

Pure recorded-fixture checks use the shared existing environment:

```sh
PYTHONPATH=src:tests ../lab-hardening/.venv/bin/python -m unittest test_memory_history test_memory_experiment test_memory_task test_memory test_records -v
```

They cover nearest visible evidence, missing versus unchanged outcomes, source-ID
collisions, integrity/terminal rejection, cue linkage, truncated bank/nonempty U,
event ordering, hidden-goal rejection and private-geometry exclusion. No simulator,
model, EGL, browser or held-out job is launched.

Root review added a source-mutation-during-fitting regression: it failed before
the final fingerprint guard and passes afterward. The final focused run passed
39 tests (2.120 s, no skips), including 11 collector checks. Retained local index:
`runs/m5-history-collector-20261002/report.json`, SHA256
`7702e6c96c9fd990d4a9393c4c6c920437be9c9ae2de5127a8e14e3e77de0a10`.
That historical fixture check establishes no actual acquisition or held-out result.
The separate pilot and planned batch are described in their linked protocols.
