# Artwork material v2: one prospective offline preparation

7 October 2026. Approved separate allocation after the failed, consumed
[development preparation](../reports/artwork-review-development-material.md).
Preparation only at this checkpoint: no extraction, exporter or artwork has run.
The v1 marker, receipts, inputs and review packs remain immutable.

Reuse the existing 98-source ZIP, 577,247,342 bytes, SHA256
`80251ccd5889ce01ac2cf447f7ff591848be69b3d5fb38a70ec6ef55c7708aed`.
Its pinned embedded manifest is
`6cac84d9b733ed1e1fb7267b302dd0f7d1105e288e9b53fac65fe497501d77e9`.
Do not recollect/crop sources, recreate that input ZIP or substitute recordings.
Freshly relocate the exact 98 files under the new v2 phase after archive/member
admission. Then invoke the three existing CLI exporters exactly once each:
south route SVG; south visual_left/visual_right/descending WAV; south/north HTML.
Reuse unchanged Afterimage, atlas and anatomical SVGs from the pinned v2 short
review pack. Produce one new nine-member six-mode review ZIP and guide.

Limits: one invocation, zero corrective attempts, zero native owners, 300 seconds
aggregate, 120 seconds per export child, outer TERM at 290 seconds and five-second
KILL grace. Count all new controls, relocated inputs, artifacts, logs and review
ZIP against 2 GiB. Require 4 GiB free initially and 2 GiB continuously; reserve
1 MiB headroom and cap each child log stream at 1 MiB. Serialize existing writer
leases and never hold a preparation lease while an exporter owns one. Existing
process-group supervision includes TERM/KILL cleanup; inspect recorded PID/start
and group absence. Checks/reservations are not an atomic filesystem quota.
Stop on admission, hash, export, storage, deadline or cleanup failure; retain
partial outputs and failed receipts. Never retry the consumed namespace.

The prospective [registration](artwork-material-v2-registration.json) binds the
exact input inventory, existing SVG pins, current implementation/control hashes,
Python identity and child argv. The [producer](../../scripts/prepare_artwork_material_v2.py)
checks these pins before consuming a new marker, records actual Git HEAD, validates
ZIP member type/size/CRC/content hashes during relocation, and checks relocated
hashes again after exports. No model/upstream assets or scientific decoding are
admitted. A missing/changed source or setup input fails; there is no fallback.

Validate original route identities and 1,268/1,293 genuine points, actual SVG
polyline points, SVG alternatives, comparison identities and geometry; the
25.34-second 48 kHz mono 16-bit WAV, exact timing boundaries/voices/PCM hash;
unchanged reused SVGs; every new review ZIP member and footer; unchanged source
ZIP and source/control pins; released writer ownership and bounded cleanup.
The final receipt remains failed until every check passes. Publish retained
receipts, original logs, archive hashes and the reproducible local handoff after
root independently reviews the result. No automatic upload or human review.

The guide remains at most ten minutes with at most two manually started,
low-volume audio plays. Explicitly label Afterimage's unchanged 0.5 source
seconds / 0.16 model seconds as insufficient for assessing sustained material.
Adequate new Afterimage, aesthetics, screen-reader use, independent operator
sessions and audience/custody/retention decisions remain open. These derivatives
supply no causal memory, learned-control, restore, biological or physical claims.
Qualification claims remain empty even if offline preparation passes.

Root review and commit precede the single later execution. Do not run this command
while another lab/native/writer phase owns the shared machine:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src:scripts \
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
timeout --signal=TERM --kill-after=5s 290s \
/home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python \
-B scripts/prepare_artwork_material_v2.py
```

This command is recorded for review; it has not been executed. The approved v2
allocation is separate from the preserved v1 failure and authorizes no additional
study, corrective attempt, model inference, browser session or human acceptance.
