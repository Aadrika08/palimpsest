# Portable artwork inputs prepared; artwork acceptance remains open

7 October 2026. Prepared toward the
[simulation-first completion goal](../plans/simulation-first-completion-goal.md).
The existing exact source folder is now packaged as a deterministic local ZIP,
and a relocated copy passes the existing handoff admission. No new product
packaging CLI, dependency, exporter invocation, inference or native owner was needed.

Archive: `palimpsest-artwork-inputs-v1.zip`, **4,855,640 bytes**.
SHA256: `35ff2f665e52d1a0cce9aa90af2874b0fed2c6a801fafc7046144483a45dac4d`.
Manifest SHA256:
`9766f285b7f4008f894845cc12d51e34a14dafc5eaf88fba6e13bdec36944982`.

The archive contains exactly the 19 relative regular files / 4,852,480 bytes from
[artwork-handoff.json](../artwork-handoff.json), with original contents unchanged.
It uses fixed sorted names, timestamps and permissions, and `ZIP_STORED`;
two independent packaging passes produce byte-identical archives. Existing
`verify_artwork_handoff.admit` verifies both the original and relocated folders.
No native snapshots, checkpoint assets or additional camera records are included.
Copied recordings remain derivative subsets, not restorable/replayable run bundles.

The local archive and exact executed preparation script are retained under:

```text
/home/utkarsh/Work/shraddha/brain/.worktrees/research-phase/.superpowers/sdd/simulation-first-completion-goal/artwork-portability/
```

The ZIP is intentionally outside Git and has not been uploaded or publicly shared.
A fresh clone needs this explicitly supplied local archive and the documented
Python 3.11 / NumPy 2.2.5 environment. Original provenance, distinct source notices
and blank operator/audience/retention declarations remain intact. Packaging is
not new permission to redistribute the source material.

## Verify and relocate the fixed archive

Run from the intended source checkout, with its documented Python environment.
Pass the supplied ZIP and a **new** destination directory as the two arguments.
The pinned archive is checked before creating output; the existing admission
validates the complete relocated source folder. This operation invokes no exporter.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src:scripts python - "$ARCHIVE" "$NEW_INPUT" <<'PY'
import hashlib, stat, sys, zipfile
from pathlib import Path
import verify_artwork_handoff as h

archive = h.artifacts._safe_path(Path(sys.argv[1]))
output = h.artifacts._safe_path(Path(sys.argv[2]))
if archive.stat().st_size != 4855640:
    raise ValueError('Archive size differs')
with archive.open('rb') as f:
    if hashlib.file_digest(f, 'sha256').hexdigest() != '35ff2f665e52d1a0cce9aa90af2874b0fed2c6a801fafc7046144483a45dac4d':
        raise ValueError('Archive checksum differs')
manifest = h.load_manifest()
expected = {row['path']: row for row in manifest['files']}
with zipfile.ZipFile(archive) as z:
    members = z.infolist()
    if len(members) != 19 or {m.filename for m in members} != set(expected):
        raise ValueError('Archive member allowlist differs')
    if any(not stat.S_ISREG(m.external_attr >> 16) or m.compress_type != zipfile.ZIP_STORED or m.file_size != expected[m.filename]['size_bytes'] for m in members):
        raise ValueError('Archive member type or size differs')
    output.mkdir(parents=True, exist_ok=False)
    z.extractall(output)  # Only this checksum-pinned, exact reviewed archive.
verified = h.admit(output, manifest)
print({'verified_files': len(verified), 'source_bytes': manifest['source_bytes']})
PY
```

Next, use the existing [six-mode commands](../plans/m9-offline-handoff.md#exactly-six-existing-commands)
with this folder supplied explicitly. The historical one-shot export driver
retains its separately reviewed invocation requirements; this package does not
consume or reopen it. No model runtime or upstream submodule is needed for these
offline export paths, and no machine-specific original-source fallback is added.

## Verification and remaining work

Preparation passed in 0.0546 s with original inputs unchanged and no Torch/MuJoCo
import. Fresh independent read-only verification checked all archive members,
their sizes/hashes, fixed metadata, both archive bytes and both admitted folders.
The complete preparation folder had exactly 24 expected files / 14,568,977 bytes;
the receipt's earlier 23-file storage snapshot excludes its own 1,739 bytes.
[Compact preparation receipt](artwork-portability-preparation.json).

The exact instruction block above is also checked against this archive in a
separate fresh worktree, with a new extraction directory and identical admission.
An existing destination is refused, and a deliberately corrupted archive is
refused before any output directory is created. Original inputs remain unchanged.
This is source portability evidence, not independent human operation or an
exhibition-duration/artistic acceptance result.

The sample material remains the short historical export smoke: eight Afterimage
frames, coincident route traces and a 0.08 s choir. A usable simulation encounter,
user visual/audio review and full declared-duration independent-operator sessions
remain open under the [runbook](../exhibition-runbook.md). No R5, memory, navigation,
physical rover or public-sharing claim is promoted by packaging.

The relocated inputs have since produced a [local six-mode review pack](artwork-review-preparation.md)
through the existing exporters in a separate bounded preparation. Its captions,
short-source limitations and identified route-accessibility gap remain explicit.
