"""Fresh review handoff; every tested artwork byte remains unchanged."""
import hashlib
import json
from pathlib import Path
import zipfile
from palimpsest.storage import StorageBudget, StorageLimits
from prepare_artwork_encounter import encounter_html

root = Path('runs/static-artwork-sessions-2026-10-22-v1').absolute()
previous = Path('runs/route-material-2026-10-22-v1/palimpsest-route-encounter-2026-10-22.zip')
assert hashlib.sha256(previous.read_bytes()).hexdigest() == '0ef85fba961c9d207a6023232132929a82f908b6324d3493a4edd31fa8a6230d'
audit = json.loads((root / 'independent-audit.json').read_text())
assert audit['status'] == 'passed'
store = StorageBudget((root,), StorageLimits(max_bytes=2 * 1024**3, min_free_bytes=2 * 1024**3))
with store.lock():
    with zipfile.ZipFile(previous) as z:
        files = {name: z.read(name) for name in z.namelist()}
    before = {n: hashlib.sha256(files[n]).hexdigest() for n in (
        'afterimage.svg', 'borrowed-body.svg', 'one-map-many-lives.html',
        'counterfactual-choir.wav', 'atlas.svg', 'space-between-two-flies.svg')}
    old = b'All four static modes still need\ndeclared ten-minute viewing sessions.'
    assert old in files['README.md']
    files['README.md'] = files['README.md'].replace(old, b'All four static modes passed concurrent automated ten-minute browser sessions.\nActual human viewing remains pending.')
    files['README.md'] += b'\n## Duration results and human review\n\nstatic-session-results.json retains the automated duration audit. These were\nindependent headless browser sessions, not human viewing or exhibition acceptance.\nUse human-review.md to record human decisions; all judgments remain pending.\n'
    files['static-session-results.json'] = (root / 'independent-audit.json').read_bytes()
    files['human-review.md'] = Path('docs/plans/artwork-human-review-2026-10-22.md').read_bytes()
    files['index.html'] = encounter_html(files)
    files['checksums.json'] = json.dumps({'qualification_claims': [], 'files': {
        n: {'size_bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
        for n, b in files.items() if n != 'checksums.json'}}, indent=2).encode()
    assert all(hashlib.sha256(files[n]).hexdigest() == digest for n, digest in before.items())
    assert sum(map(len, files.values())) < 64 * 1024**2
    out = root / 'encounter'
    out.mkdir(exist_ok=False)
    for n, b in files.items():
        assert Path(n).name == n
        store.check(len(b), path=out / n)
        with (out / n).open('xb') as f:
            f.write(b)
    archive = root / 'palimpsest-human-review-2026-10-22.zip'
    store.check(sum(map(len, files.values())) + 65536, path=archive)
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_STORED) as z:
        for n, b in sorted(files.items()):
            z.writestr(n, b)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist()) == set(files) and all(z.read(n) == b for n, b in files.items())
    result = {'archive': str(archive), 'size_bytes': archive.stat().st_size,
              'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'files': len(files),
              'all_six_artwork_hashes_unchanged': before}
    with (root / 'handoff.json').open('x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))
