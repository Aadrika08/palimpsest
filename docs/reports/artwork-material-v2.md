# Artwork material v2: retained partial failure

7 October 2026. The approved single offline preparation failed after 10.434
seconds. It consumed its marker and received no corrective attempt. No native
simulation owner, model inference or human artwork review ran.

The input ZIP and all 98 relocated members were admitted and hashed. The route
SVG exporter returned 0 (8,332,995 bytes), and sonification returned 0 (2,460,152
bytes). The third child returned 1 before writing comparison HTML:
`comparison metadata exceeds export limit`. Each child reported no imported
Torch/MuJoCo runtime and passed its same-invocation process/group absence check.
Final source/archive/registration/relocated-input rechecks reported no errors and
writer ownership was released. This is a failed preparation, not a qualified pack.

The HTML producer embeds both complete visible-event arrays, including repeated
`memory_inspected` inspector payloads. Its separate 4 MiB metadata limit refused
the output, independently of the CLI's 64 MiB storage allowance. See
[comparison.py](../../src/palimpsest/comparison.py),
[artifacts.py](../../src/palimpsest/artifacts.py) and the exact stderr in the
retained archive. No route points or source events were removed to obtain success.
The final geometry/audio/alternatives/package checks were never reached; neither
a nine-member review pack nor a usable comparison was produced.

The [failed receipt](artwork-material-v2-evidence/result.json), three child
receipts and consumed marker are byte-identical copies. The
[publication index](artwork-material-v2-evidence/publication-index.json) binds a
[partial raw archive](artwork-material-v2-evidence/partial-records.zip): 21 members,
1,821,526 ZIP bytes, SHA256
`89d951d296e850ef1ce3609b4b76e020290e8b5027a48323fb7b5fd4a46de794`.
It includes the two partial artifacts, original logs and frozen controls.
Every member was checked against its original bytes. The 577 MB input ZIP is not
duplicated; its exact manifest and hash remain bound by the
[registration](../plans/artwork-material-v2-registration.json).
Packaging added no export or acceptance measurement. Original failure bytes,
source ZIP and consumed v1/v2 markers remain unchanged. Counted new phase plus
handoff used 589,899,488 bytes after packaging, below 2 GiB.

Preparation software checks passed five tiny fixtures and the archive-path
self-check. These tested displayed-geometry corruption and interrupted provisional
passes; they did not demonstrate that development-sized metadata would fit HTML.

The next proposed source repair compacts only HTML event payloads into explicit
source-stream references, exact hashes/sizes and counts while preserving all
route points, worlds, metrics, provenance, JSON/API behavior and existing caps.
Validate secrets on the full report before compaction. A separately reviewed fresh
allocation is required to produce a complete pack. Afterimage still supplies only
0.5 source seconds and is insufficient for sustained review. All human, operator,
artwork adequacy and scientific gates remain open; qualification claims are empty.
