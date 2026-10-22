"""Package audited routes with the existing actual Afterimage and Choir."""
import hashlib
import json
from pathlib import Path
import zipfile
from palimpsest.storage import StorageBudget
from record_route_material import LIMITS
from prepare_artwork_encounter import encounter_html

root = Path('runs/route-obstacle-material-2026-10-22-v1').absolute()
previous = Path('runs/static-artwork-sessions-2026-10-22-v1/palimpsest-human-review-2026-10-22.zip')
assert previous.stat().st_size == 15257310
assert hashlib.sha256(previous.read_bytes()).hexdigest() == '2eee0b9c731752372fd6a22664226510783c2661bc688accf79c2c487bba867b'
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
    audit = json.loads((root / 'independent-audit.json').read_text())
    left, right = audit['routes']['left'], audit['routes']['right']
    files.pop('static-session-results.json', None)  # Prior route duration receipts do not cover new derivatives.
    files['README.md'] = f"""# One interruption, two traces — 22 October 2026

Open index.html locally. No model or simulator runs in this pack.

A is a public FLYNN CPU run. At tick 100 its full application state was saved.
A continued unchanged; B restored that snapshot with obstacle 0 moved to
[0.75, -0.75]. The goal, controller and eye masks were unchanged.
Parent: {left['intervals']} intervals, {left['simulation_seconds']:g} simulated seconds.
Branch: {right['intervals']} continuation intervals, {right['simulation_seconds']:g} simulated seconds.
Common post-snapshot window: {audit['matched_continuation_intervals']} intervals,
{audit['matched_continuation_seconds']:g} simulated seconds. Full routes are retained.
The square marks B's start; blue solid is A and amber dashed is B. Both use the
same fixed axes. Overlap and early termination are retained without retry.
See routes-source.json for identities, routes-registration.json for the frozen
allocation, and routes-audit.json for coordinate and state checks. The obstacle
edit refreshes derived body position through mj_forward; the small recorded
branch-start offset is disclosed without aligning or smoothing coordinates.

This is an exploratory recorded intervention, not a controlled memory experiment,
a navigation benchmark or physical pen drawing. Source records stay local;
the derivative archive contains audited provenance, not all camera data.

Afterimage, Choir, Atlas and the specimen pair are byte-identical to the previous
human-review package. Their source notices, mappings and limitations still apply.
Afterimage uses scripted manual camera footage through a duplicated-camera model
interface. Choir is 120 seconds of mapped telemetry across 18 episodes, not
biological audio; no normalization or autoplay. Start at low listening volume.
Atlas is structural reachability only. The anatomical pair has unequal coverage
and does not establish population sex differences.

Previous automated duration checks apply only to the unchanged derivatives.
The new route duration receipts are recorded separately under this run's sessions/
and the repository report. Human viewing/listening and independent operator,
rights/use and custody declarations remain pending; see human-review.md.

Rebuild the source with scripts/record_route_material.py at efc913b using locked
dependencies and the public pinned assets, with a fresh --output directory.
The frozen allocation uses seed 0, tick 100, one obstacle edit, 300 seconds,
2 GiB aggregate storage and a 2 GiB free-space floor. No automatic retries.
Audit and packaging scripts are retained in docs/reports/route-obstacle-material-2026-10-22/.
Reruns are not guaranteed byte-identical. The earlier goal-edit study is preserved.
""".encode()
    files['human-review.md'] = files['human-review.md'].replace(
        b'Parent 7.5 s; branch continuation only 0.14 s after a goal edit at tick 100.',
        f"Parent {left['simulation_seconds']:g} s; branch continuation {right['simulation_seconds']:g} s after an obstacle edit at tick 100.".encode())
    for name in ('afterimage.svg', 'counterfactual-choir.wav', 'atlas.svg', 'space-between-two-flies.svg'):
        with zipfile.ZipFile(previous) as z:
            assert files[name] == z.read(name)
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
