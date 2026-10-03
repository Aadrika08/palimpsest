# Paired anatomical structures

Implement the remaining “the space between two flies” mode as a local, offline
SVG of two explicitly curated SWC skeletons. Reuse artifact path, JSON, integrity,
exclusive-write and storage-lease helpers. No new dependency or live data fetch.

The first candidate is right-side DNge104: MaleCNS v1.0 body 12781 and FlyWire
783 root 720575940640723315. Male annotations explicitly name flywireType
DNge104; the FlyWire v3.1.0 annotation release (commit 8587524) matches MaleCNS
v1.0. This supports a curated cell-type pairing, not point-to-point registration
or a population-wide sex comparison. Record original annotation rows, versions,
URLs, hashes, provenance and uncertainty before publishing a candidate bundle.

Keep native coordinate spaces separate. Convert declared units to micrometres;
project native x horizontally and z upward. Center each skeleton's bounds in its
own panel, using one shared scale fitted to the larger extent. Preserve every
parent-child segment, disconnected root and coincident coordinate. No mirroring,
rotation, smoothing, synthetic bridges or independently fitted panel scales.
Male full-CNS and female brain coverage and different reconstruction/downsampling
remain visible; rendered size differences do not establish dimorphism.

Design: quiet pale blue-white (#f5f8fc), ink (#203444), two structural line colors
(#245b84, #81562b), muted annotation (#526578). Left-aligned serif title and plain
sans-serif source labels. The actual arbors occupy two equal panels; the gap
conveys that no anatomical registration is being asserted. Shared scale bars, root markers and source identities carry information; no decorative cards.

Strict manifest: exactly two specimen declarations, a curator/evidence/uncertainty
record, local basename-only SWC paths and SHA-256 hashes. Require dataset/version,
specimen, cell identity/type/side, sex, units, coordinate space, coverage, licence,
attribution and source URL. Limits: 64 KiB manifest, 4 MiB/50,000 nodes per SWC,
16 MiB SVG. Reject malformed rows, nonfinite values, duplicate/missing IDs,
cycles, corrupt hashes, symlinks, path escapes and overwriting sources/outputs.

Fixtures verify unit conversion/shared scale, exact segment topology, coincident
and disconnected structure, malformed inputs, escaped metadata and exclusive
publication/partial-write cleanup. Actual source rendering and a serialized
browser inspection are separate gates. Exhibition duration and independent
operation remain open; this slice supplies no model inference or physical work.
