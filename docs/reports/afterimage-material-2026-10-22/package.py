"""Fresh derivative pack; the raw camera and portrait records remain local."""
import hashlib
import json
from pathlib import Path
import zipfile
from record_afterimage_material import budget
from prepare_artwork_encounter import encounter_html

root = Path('runs/afterimage-material-2026-10-22-v1').absolute()
archive = Path('runs/choir-material-2026-10-22-v1/palimpsest-choir-encounter-2026-10-22.zip')
assert archive.stat().st_size == 22718753
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '16f2dfd7fd30d11cff13f5c564780927e1400626f55be37d2f9b3fa2fe85c81b'
audit = json.loads((root / 'independent-audit.json').read_text())
assert audit['status'] == 'passed'
store = budget(root)
with store.lock():
    with zipfile.ZipFile(archive) as z:
        files = {name: z.read(name) for name in z.namelist()}
    for name, pin in json.loads(files['checksums.json'])['files'].items():
        assert len(files[name]) == pin['size_bytes'] and hashlib.sha256(files[name]).hexdigest() == pin['sha256']
    files['afterimage.svg'] = (root / 'afterimage.svg').read_bytes()
    files['afterimage-source.json'] = (root / 'stimulus/afterimage-source.json').read_bytes()
    files['afterimage-audit.json'] = (root / 'independent-audit.json').read_bytes()
    files['afterimage-registration.json'] = (root / 'registration.json').read_bytes()
    files['afterimage-stimulus.json'] = (root / 'stimulus/stimulus.json').read_bytes()
    files['README.md'] = b'''# Afterimage and Choir encounter - 22 October 2026

Open index.html locally. Afterimage now contains 600 actual male-original CPU
responses to effective left-eye camera frames from a scripted manual-controller
lab recording. Open its inspection panel and select Play 60-second portrait.
Every fifth interval of the first 3,000 was used, starting at zero. Source time
is concatenated across episodes: samples span 0-59.9 s, held for 60 s at 10 fps.
Native episodes, ticks, eye masks and source-file hashes are in afterimage-source.json.
The recorded simulation time is the interval end; observation time is its start.
The model resets once and carries hidden state across all 600 duplicated-camera
inputs with fixed sensors; model index time is 12 s. This is an authored
artificial interface, not biological vision or a physical trajectory.

Playback starts only on request, has no looping and stops on closing the
inspection panel or hiding the page. Slow browser scheduling can skip visual
updates; each response remains inspectable in the exact alignment table.
Human viewing/listening acceptance remains open.

Choir retains the independently audited 120-second actual CPU FLYNN composition
from 6,000 intervals in 18 episodes, with its final prefix and boundaries labelled.
Start at low volume. The fixed audio mapping has no normalization or crossfade.
The other four modes remain historical development material: their 10-minute
viewing sessions and the new parent/branch route material remain pending.

## Rebuild and provenance

Source generation is pinned to commit 0a51ddd and the file hashes in
afterimage-registration.json. With the locked simulation dependencies, public
FLYNN assets and bundled male-reduced-v1 assets, run the bounded script
scripts/record_afterimage_material.py --output runs/NEW-UNUSED-DIRECTORY once,
then the documented public Afterimage record and render commands using the
generated stimulus and registered portrait UUID. Keep the 120-second inference
limit. The script requires a clean checkout. No automatic retries are allowed.
Fresh reruns need not reproduce identical bytes. Raw camera records, NPY frames
and portrait records remain local outside this portable derivative pack.
afterimage-stimulus.json is a provenance copy; its NPY is not shipped here.
See docs/plans/afterimage-material-2026-10-22.md and its report for the exact recipe.

The Choir public recipe is scripts/record_choir_material.py at a8f7ac2.
choir-source.json retains its registration, source hashes, audit and supervisor.
Source notices remain in THIRD_PARTY_NOTICES.md. Project-generated simulated
footage has no identifiable people; processing/retention declaration is retained
in SVG metadata. Exhibition rights, audience and custodianship require human review.
No scientific, biological, full exhibition or independent-operator qualification.
'''
    files['index.html'] = encounter_html(files)
    files['checksums.json'] = json.dumps({'qualification_claims': [], 'files': {
        name: {'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
        for name, raw in files.items() if name != 'checksums.json'}}, indent=2).encode()
    assert sum(map(len, files.values())) < 64 * 1024**2
    out = root / 'encounter'
    out.mkdir(exist_ok=False)
    for name, raw in files.items():
        assert Path(name).name == name
        store.check(len(raw), path=out / name)
        with (out / name).open('xb') as f:
            f.write(raw)
    target = root / 'palimpsest-afterimage-choir-encounter-2026-10-22.zip'
    store.check(sum(map(len, files.values())) + 65536, path=target)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_STORED) as z:
        for name in sorted(files):
            z.writestr(name, files[name])
    with zipfile.ZipFile(target) as z:
        assert set(z.namelist()) == set(files)
        assert all(z.read(name) == raw for name, raw in files.items())
    result = {'archive': str(target), 'size_bytes': target.stat().st_size,
              'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'files': len(files),
              'encounter_script_sha256': hashlib.sha256(Path('scripts/prepare_artwork_encounter.py').read_bytes()).hexdigest()}
    with (root / 'artifacts.json').open('x') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))
