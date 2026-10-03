# Supervised artwork operation

For a finite offline software handoff, use the [six-mode plan](plans/m9-offline-handoff.md)
and its [19-file source manifest](artwork-handoff.json). The source folder must be
provided explicitly; a fresh clone does not include the local recording subsets.
The fixed driver, `scripts/verify_artwork_handoff.py --inputs INPUT --output NEWDIR`,
is for a separately supervised agent-operated export smoke. It neither captures
new imagery nor restores a model. The copied runs are derivative subsets without
native continuation or action/policy replay. Its operator/retention declarations
remain blank, and it does not complete the independent acceptance below. The
[2026-10-03 offline handoff](reports/m9-offline-handoff.md) passed all six fixed
exports from the byte-verified local bundle, with independent agent artifact
readback and clean shutdown. That short software check provides no independent
human, declared-duration exhibition or physical qualification.

This is an operator handoff for the implemented software modes, not an exhibition
qualification. Start with offline derivatives. A named operator must remain
present for any live lab or physical work. Physical rover/pen operation is not
released: no qualified hardware exists for this project.

## Declare one session before opening it

Record the operator, date, venue/machine, exact Git commit, intended start/end,
mode, source run IDs or input manifest hashes, model/profile when applicable,
output directory, access custodian and approved audience/use of the material.
Declare `duration_seconds`, a hard end time and stop action, maximum generated
bytes, and the episode/reset/playback-repeat policy before starting. Choose a finite
session duration; the existing mixed-operation hour test is not evidence that
this exhibition configuration can run for an hour. Archive the declaration with
its eventual actual start/end, interruptions and result.

Prepare using the [installation guide](../README.md), verify required assets,
and read the [distinct asset terms](../THIRD_PARTY_NOTICES.md). Keep assets outside
run/export roots. Use new output names and check available space; writers enforce
quotas but never delete history. For public use, review the intended reuse of each
source, including attribution and noncommercial restrictions. An operator rights
statement is not independent verification of permission.

## Select the mode and preserve its label

| Mode | Operator path | What the audience sees |
| --- | --- | --- |
| Afterimage | [Authorize a local RGB sequence, record, then render](artwork-afterimage.md). Review every supplied frame and its processing/retention declaration before inference. | Authored model response; offline inference/recorded playback. Fixed axes may show a nearly coincident path. No fly-perception or verified-consent claim. |
| One map, many possible lives | [Compare two completed runs](artwork-mappings.md#one-map-many-possible-lives-implemented-offline-comparison). Read condition/provenance differences before describing the comparison. | Recorded routes, with the actual intervention type and source IDs. A U-only claim applies only to a verified U-only transaction. |
| Counterfactual choir | [Select recorded populations and export WAV](artwork-mappings.md#counterfactual-choir-implemented-offline-derivative). Listen at low volume first and use the player's stop control; nothing autoplays. | A composed mapping of recorded model telemetry, not biological audio. Preserve the original WAV's embedded provenance. |
| Borrowed body | Export a completed simulator route as SVG/PNG, or use clearly labelled recorded playback in the lab. | Actual recorded simulator actions/positions. No physical rover or pen mark claim; that extension remains unavailable. |
| Atlas of what disappears | [Select the pinned graph and explicit isolated node IDs](artwork-atlas.md). Read graph size/boundary and the lost-reachability result. | Structural graph analysis, not measured memory loss or behavior. |
| The space between two flies | [Render the curated pair](artwork-specimens.md). Preserve the two source identities, shared scale and unequal-coverage labels. | Unregistered anatomical reconstructions with declared curatorial uncertainty; no population sex-effect claim. |

Provision the exact source bundle for every selected mode before handoff. Static
exports need the documented recording/graph/SWC readers, not a model runtime.
Afterimage recording needs its verified fixed male model; offline portrait rendering
needs only the completed Afterimage record. Choir specifically needs completed
FLYNN population telemetry; manual, teacher and male records are unsuitable.

Close the owner **and the lab server** before invoking any standalone writer CLI
(including export, sonify, atlas, specimens or Afterimage). A paused or closed run
alone does not release the server-held per-user writer lease.

For existing completed simulator run `RUN`, these commands perform no inference:

```sh
uv run --no-sync palimpsest export RUN --format svg --output exports/new-route.svg
uv run --no-sync palimpsest replay RUN --mode playback --tick 0
```

Keep source recordings and original exported files together. A screenshot, edited
audio file or projected crop can discard provenance; display a nearby label with
mode, source IDs, model/profile and mapping, and retain the complete artifact.
Do not crop away live/playback or scientific-limit labels.

## Live lab, pause and recovery

Use the documented local `palimpsest lab` command and its private session URL.
Start paused, select the declared profile, check the displayed sensors and use
one-step before running. Display/inspector layers do not belong in agent input.
Only deliberately configured scenarios may feed external imagery into inference.
A microphone, camera, pen, projector or artwork layer is not implicitly a sensor.

Pause before changing inputs or profiles. The default browser-disconnect policy
pauses at a control boundary; do not opt into headless continuation for a
supervised presentation unless the session declaration explicitly covers it.
Stop audio separately in its player. Close the run normally and wait for its
completed disposition before closing the server or archiving evidence.

If inference, recording, storage, contact validation or input availability fails,
stop the presentation and retain the failed manifest/events/logs. Do not call an
incomplete run a completed comparison. Follow the
[recovery boundaries](reports/lab-hardening-runbook.md#recovery-boundaries):
inspect the published prefix, use a registered snapshot/fresh owner where valid,
and create new output rather than overwriting or promoting orphan chunks.
Record recovery as a new disposition; a resumed presentation does not erase the
interruption. A static export may be shown instead only if labelled as such.

## Retention and independent acceptance

Before acquiring external imagery, choose who may access the original frames,
what may be shared, and the retention/deletion date. Afterimage retains complete
RGB inputs in recordings. Inventory the original NPY, duplicated RGB NPZ channels,
manifest/rights metadata, derivatives/screenshots and approved copies/backups.
Its SVG omits photos but includes declared attribution,
rights statements and response metadata. Those fields can still identify people.
The custodian records expiry and actual archive/deletion disposition for every
approved copy; resolve any failed-evidence retention requirement before accepting
personal input. No automatic upload or deletion is implemented. Close all writers before the
operator archives or removes approved files; keep failure evidence required by
the declared evaluation and do not delete unrelated work.

An independent operator must follow this document on the intended machine,
without relying on the implementer's undocumented help. Retain the following
record for each declared mode/session, with failures left visible:

- Exact source/software/model hashes, declared duration/data bounds and actual
  start/end. Acceptance requires the entire declared elapsed session, with every
  reset, repeated playback and interruption labelled; a shorter clean run is not a pass.
- Successful setup, correct labels and artifact provenance inspection.
- Pause/stop and a planned disconnect/recovery exercise where live operation is used.
- Readable display at the intended viewport, audible level checked when relevant,
  bounded disk use, source files unchanged and no remaining owned runtime.
- Operator identity, any implementer help, unexpected events, recovery actions and
  the operator's pass/fail decision. Undocumented help does not count as independence.

For each mode, the operator checks a supplied source hash, produces/views the
correct artifact, and explains its label. The small fixed-scale Afterimage output
is valid without enlargement; comparison retains coincident/null routes; choir
retains silence; atlas distinguishes the no-op from the declared cut; anatomy
retains shared scale and unequal coverage; Borrowed body identifies the simulator
source and does not describe a physical action. These checks require actual source
bundles, not invented example results.

These acceptance records do not yet exist. The short local render checks, eight
Afterimage inference frames and earlier mixed lab hour test do not replace
independent operation or a declared-duration exhibition trial. Physical work
additionally requires the complete rover qualification and stopping-envelope
measurements; adding pen marks to camera input creates a new feedback scenario.
