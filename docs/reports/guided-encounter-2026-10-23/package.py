"""Fresh portable introduction; preserve all artwork and source-frame bytes."""
import hashlib
import json
from pathlib import Path
import zipfile

import prepare_artwork_encounter as encounter
from palimpsest.storage import StorageBudget, StorageLimits

root = Path('runs/guided-encounter-2026-10-23-v1').absolute()
previous = Path('runs/afterimage-presentation-2026-10-22-v2/palimpsest-afterimage-presentation-2026-10-22.zip')
assert not root.exists(), 'fresh output required'
assert previous.stat().st_size == 17269977
assert hashlib.sha256(previous.read_bytes()).hexdigest() == '91e14087ca31bd3ab2a30c51e34420a6016a2e0709c5a9659109567188d774b5'
with zipfile.ZipFile(previous) as z:
    files = {n: z.read(n) for n in z.namelist()}
for n, pin in json.loads(files['checksums.json'])['files'].items():
    assert len(files[n]) == pin['size_bytes'] and hashlib.sha256(files[n]).hexdigest() == pin['sha256']
protected = {n: hashlib.sha256(b).hexdigest() for n, b in files.items()
             if n not in ('index.html', 'README.md', 'human-review.md', 'checksums.json')}
files['README.md'] = ('''# Palimpsest: a guided development encounter

Extract this complete ZIP and open index.html locally. No server, installation,
model download or network connection is required for this recorded encounter.
The introduction links all six modes and leaves playback under your control.
Start with One map and Borrowed body, then inspect Afterimage, listen to Choir,
and explore the structural/anatomical studies. These use different records and
models; they are not six views of one trial.

The guided introduction is not timed. Preserve the declared source durations:
60 seconds for Afterimage, 120 seconds for Choir; the four static modes have
ten-minute review sessions. Do not count this introduction as those sessions.
No source material or artwork mapping changed. See checksums.json, embedded
provenance and the retained source notices. Live lab installation, independent
operator acceptance, human listening/viewing and use declarations remain open.
Complete human-review.md after actual exposure; automated evidence is separate.

Earlier guide and source record (historical checks are scoped to their versions):

''' + files['README.md'].decode()).encode()
files['human-review.md'] += b'\n23 October: the guided introduction is implemented. Record actual viewing/listening and independent installation separately; agent review is not human acceptance.\n'
files['index.html'] = encounter.encounter_html(files)
assert all(hashlib.sha256(files[n]).hexdigest() == h for n, h in protected.items())
files['checksums.json'] = json.dumps({'qualification_claims': [], 'files': {
    n: {'size_bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
    for n, b in files.items() if n != 'checksums.json'}}, indent=2).encode()
assert sum(map(len, files.values())) < 64 * 1024**2
store = StorageBudget((root,), StorageLimits(max_bytes=128 * 1024**2, min_free_bytes=2 * 1024**3))
with store.lock():
    store.check(2 * sum(map(len, files.values())) + 65536, path=root)
    out = root / 'encounter'
    out.mkdir(parents=True, exist_ok=False)
    for n, b in files.items():
        assert Path(n).name == n
        with (out / n).open('xb') as f:
            f.write(b)
    archive = root / 'palimpsest-guided-encounter-2026-10-23.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED) as z:
        for n in sorted(files):
            z.writestr(n, files[n])
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist()) == set(files) and all(z.read(n) == b for n, b in files.items())
    result = {'archive': str(archive), 'size_bytes': archive.stat().st_size,
              'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'files': len(files),
              'protected_member_sha256': protected, 'all_artwork_and_source_members_unchanged': True,
              'template_sha256': hashlib.sha256(Path(encounter.__file__).read_bytes()).hexdigest(),
              'human_acceptance': 'pending', 'qualification_claims': []}
    with (root / 'artifacts.json').open('x') as f:
        json.dump(result, f, indent=2)
print(json.dumps(result))
