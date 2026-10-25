"""Correct the review destination and attach completed duration evidence."""
import hashlib
import json
import re
from pathlib import Path
import zipfile

from prepare_artwork_encounter import encounter_html
from palimpsest.storage import StorageBudget
from record_route_material import LIMITS

root = Path('runs/route-obstacle-material-2026-10-22-v1').absolute()
receipt = json.loads((root / 'artifacts.json').read_text())
previous = Path(receipt['archive'])
assert hashlib.sha256(previous.read_bytes()).hexdigest() == receipt['sha256']
sessions = json.loads((root / 'sessions/result.json').read_text())
assert sessions['status'] == 'passed'
assert {s['name'] for s in sessions['sessions']} == {'borrowed-body.svg', 'one-map-many-lives.html'}
with zipfile.ZipFile(previous) as z:
    files = {n: z.read(n) for n in z.namelist()}
for name, pin in json.loads(files['checksums.json'])['files'].items():
    assert len(files[name]) == pin['size_bytes']
    assert hashlib.sha256(files[name]).hexdigest() == pin['sha256']
for session in sessions['sessions']:
    assert session['status'] == 'passed' and session['duration_seconds'] >= 600
    assert session['browser_disconnected'] and not session['errors'] and not session['blocked']
    assert hashlib.sha256(files[session['name']]).hexdigest() == session['source_sha256']
artwork_hashes = {n: hashlib.sha256(files[n]).hexdigest() for n in (
    'borrowed-body.svg', 'one-map-many-lives.html', 'afterimage.svg',
    'counterfactual-choir.wav', 'atlas.svg', 'space-between-two-flies.svg')}
files['human-review.md'] = Path('docs/plans/artwork-human-review-2026-10-22.md').read_bytes().replace(
    b'runs/route-obstacle-material-2026-10-22-v1/handoff/index.html', b'index.html')
# The portable sheet uses local paths; repository-only references remain named text.
files['human-review.md'] = re.sub(rb'\[([^]]+)\]\(\.\./reports/[^)]+\)', rb'\1 (repository report)', files['human-review.md'])
files['route-session-results.json'] = (root / 'sessions/result.json').read_bytes()
files['README.md'] += b'\nBoth updated route views passed their automated 600-second sessions; see route-session-results.json. Human acceptance remains pending.\n'
files['index.html'] = encounter_html(files)
assert all(hashlib.sha256(files[n]).hexdigest() == h for n, h in artwork_hashes.items())
files['checksums.json'] = json.dumps({'qualification_claims': [], 'files': {
    n: {'size_bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
    for n, b in files.items() if n != 'checksums.json'}}, indent=2).encode()
store = StorageBudget((root,), LIMITS)
with store.lock():
    store.check(2 * sum(map(len, files.values())) + 65536, path=root)
    out = root / 'handoff'
    out.mkdir(exist_ok=False)
    for name, raw in files.items():
        assert Path(name).name == name
        with (out / name).open('xb') as stream:
            stream.write(raw)
    target = root / 'palimpsest-obstacle-review-2026-10-22.zip'
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_STORED) as z:
        for name in sorted(files):
            z.writestr(name, files[name])
    with zipfile.ZipFile(target) as z:
        assert set(z.namelist()) == set(files)
        assert all(z.read(n) == b for n, b in files.items())
    result = {'archive': str(target), 'size_bytes': target.stat().st_size,
              'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
              'artwork_sha256': artwork_hashes, 'all_six_artworks_unchanged': True,
              'source_archive_sha256': receipt['sha256'], 'files': len(files)}
    with (root / 'handoff.json').open('x') as stream:
        json.dump(result, stream, indent=2)
print(json.dumps(result))
