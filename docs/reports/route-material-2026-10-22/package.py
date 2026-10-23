"""Package audited routes with the existing actual Afterimage and Choir."""
import hashlib
import json
from pathlib import Path
import zipfile
from palimpsest.storage import StorageBudget
from record_route_material import LIMITS
from prepare_artwork_encounter import encounter_html

root = Path('runs/route-material-2026-10-22-v1').absolute()
previous = Path('runs/afterimage-material-2026-10-22-v1/palimpsest-afterimage-choir-encounter-2026-10-22.zip')
assert previous.stat().st_size == 23723504
assert hashlib.sha256(previous.read_bytes()).hexdigest() == 'afd7e147c398bd39f3896ed8679484742dfafe98b3cf234d810273bf8f402a80'
assert json.loads((root / 'independent-audit.json').read_text())['status'] == 'passed'
store = StorageBudget((root,), LIMITS)
with store.lock():
    with zipfile.ZipFile(previous) as z:
        files = {name: z.read(name) for name in z.namelist()}
    for name, pin in json.loads(files['checksums.json'])['files'].items():
        assert len(files[name]) == pin['size_bytes'] and hashlib.sha256(files[name]).hexdigest() == pin['sha256']
    for name in ('borrowed-body.svg', 'one-map-many-lives.html'):
        files[name] = (root / 'exports' / name).read_bytes()
    for destination, source in (('routes-source.json', 'routes-source.json'),
                                ('routes-audit.json', 'independent-audit.json'),
                                ('routes-registration.json', 'registration.json')):
        files[destination] = (root / source).read_bytes()
    files['README.md'] = b'''# Palimpsest recorded encounter update - 22 October 2026

Open index.html locally. No model or simulator runs in this pack.

## Routes

Borrowed body is the actual public FLYNN CPU parent route: 375 intervals,
376 points, 7.5 simulated seconds. One map compares this complete parent
with a registered tick-100 snapshot branch. Its sole declared edit moves
the goal to [0, 0], retaining the controller. The branch reaches that goal
after seven continuation intervals (0.14 simulated seconds, eight points).
This short natural result was retained without retries or aesthetic selection.
Parent and branch have unequal ranges: do not treat the comparison as paired
full episodes, a memory intervention, a causal result or physical pen marks.

The recorded branch start differs from parent tick 100 by approximately
[0.00184106827, -0.00171107054] world units. The goal edit calls mj_forward,
refreshing cached body position. The audit reproduces this offset without
advancing time; saved integration, controller and RNG state are unchanged.
Every recorded/exported coordinate is retained exactly; no alignment was added.
routes-source.json identifies the parent, snapshot, branch, edit and derivatives.
routes-audit.json retains all source file hashes and the independent checks.

## Other encounters

Afterimage: 600 actual male-original CPU responses to scripted manual lab
left-camera footage; select Play 60-second portrait in its inspection panel.
Source samples 0-59.9 s are held over 60 s at 10 fps; model index time is 12 s.
Hidden state carries through the frames, including source episode changes.
Each image enters both cameras with fixed sensors: an authored artificial
interface, not biological vision. Source index, stimulus declaration and audit
are retained. NPY frames and raw records are not included in this derivative pack.

Choir: the existing actual 120-second FLYNN population mapping, 18 episodes,
with its final prefix and reset boundaries labelled. Start at low volume;
there is no normalization, crossfade, automatic start or looping.

Atlas and The space between two flies retain their historical structural and
anatomical derivatives and source notices. All four static modes still need
declared ten-minute viewing sessions. Human viewing/listening decisions,
independent operator acceptance and audience/rights/custodian declarations
remain open. No full exhibition or scientific qualification is claimed.

## Public rebuild recipes

Install locked simulation dependencies and acquire the public hash-pinned assets
as documented in the repository. Route generation uses commit 681486f and
scripts/record_route_material.py --output runs/NEW-UNUSED-DIRECTORY.
The script requires a clean checkout, creates the registered parent/branch via
LabSupervisor, uses a 300-second watchdog, 2 GiB aggregate and 2 GiB disk floor,
and exports both derivatives. Retain outcomes; no automatic retries.
Source pins and the actual allocation are in routes-registration.json.
Raw route records and snapshots remain local, outside this ZIP and Git.
Fresh public reruns are not guaranteed byte-identical.

Afterimage generation uses scripts/record_afterimage_material.py at 0a51ddd,
then the existing public Afterimage record/render CLI; keep the 120-second
inference limit and explicitly pass --storage-max-bytes 2147483648
--min-free-bytes 2147483648. Choir uses scripts/record_choir_material.py at a8f7ac2.
Their registration, audits and source hashes remain included. See the respective
22 October reports for measured results, commands and verification limits.
THIRD_PARTY_NOTICES.md retains source notices; SVG metadata retains the explicit
Afterimage processing/retention statement, which is not exhibition permission.
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
        with (out / name).open('xb') as stream:
            stream.write(raw)
    target = root / 'palimpsest-route-encounter-2026-10-22.zip'
    store.check(sum(map(len, files.values())) + 65536, path=target)
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_STORED) as z:
        for name in sorted(files):
            z.writestr(name, files[name])
    with zipfile.ZipFile(target) as z:
        assert set(z.namelist()) == set(files) and all(z.read(name) == raw for name, raw in files.items())
    result = {'archive': str(target), 'size_bytes': target.stat().st_size,
              'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'files': len(files),
              'encounter_script_sha256': hashlib.sha256(Path('scripts/prepare_artwork_encounter.py').read_bytes()).hexdigest()}
    with (root / 'artifacts.json').open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result))
