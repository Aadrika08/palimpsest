# The space between two flies

A local, offline SVG places two curated anatomical skeletons in separate panels.
The first bundle pairs right-side DNge104: MaleCNS v1.0 body 12781 and FlyWire
783 root 720575940640723315, with annotations pinned to v3.1.0. Both sources name
DNge104 and supertype 12601; the male annotation explicitly names its FlyWire type.
This supports a curated cell-type pairing, without independent anatomical review.

```sh
PYTHONPATH=src .venv/bin/python -m palimpsest specimens data/assets/specimens/dnge104-v1/pair.json --output /path/to/new-pair.svg
```

No network, model or simulator is loaded. The existing export writer lease,
aggregate disk limits and export-count admission apply. The output must be a new
SVG, distinct from all input files. The source bundle includes separate licences
and attributions; see [third-party notices](../THIRD_PARTY_NOTICES.md).

The renderer keeps all original parent-child segments, coincident coordinates
and disconnected roots. It converts declared units to micrometres and projects
native x/z, centers each bounding box in its panel, and uses one shared scale.
Every edge is a separate move/line pair within a batched SVG path; batching
reduces document elements without joining or simplifying edges. Root circles
mark disconnected components. Radii are retained in the SWC but not rendered.
There is no mirroring, rotation, registration, smoothing or synthetic bridge.

Male full-CNS and female brain-only coverage are deliberately labelled alongside
different extraction/sampling. The female reconstruction occupies a smaller part
of the shared-scale panel. That visual difference is not evidence of population
sex effects, completeness equivalence, or point-to-point homology. The dataset
and cell identities, declared evidence/uncertainty, hashes, projection and exact
scale are embedded in the SVG; the source SWCs remain authoritative geometry.

A custom pair requires the same strict manifest fields as the bundled
[pair.json](../data/assets/specimens/dnge104-v1/pair.json): exactly two distinct
local basename SWCs, hashes, declared units (`nm`, `8nm` or `um`), dataset/version,
specimen/sex/cell/side, coordinate space, coverage, licence, attribution and
source URL, plus curator/evidence/uncertainty/source URL. Limits: 64 KiB manifest,
4 MiB and 50,000 nodes per SWC, 16 MiB SVG. Invalid values, missing parents,
cycles, duplicate IDs, symlinks, changed sources and overwrites are rejected.

This supplies one offline artwork mode. It does not qualify physical drawing,
exhibition duration, independent operation or biological function.
