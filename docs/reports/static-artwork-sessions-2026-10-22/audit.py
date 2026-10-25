"""Independent readback of the four completed, unaccelerated browser sessions."""
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

root = Path('runs/static-artwork-sessions-2026-10-22-v1')
source = Path('runs/route-material-2026-10-22-v1')
registration = json.loads((root / 'registration.json').read_text())
overall = json.loads((root / 'result.json').read_text())
assert overall['status'] == 'passed'
assert registration['required_seconds_each'] == 600 and registration['concurrent'] is True
assert len(registration['modes']) == len(set(registration['modes'])) == 4
script = subprocess.check_output(['git', 'show', registration['head'] + ':scripts/verify_static_artwork.cjs'])
assert hashlib.sha256(script).hexdigest() == registration['script_sha256']
archive = source / 'palimpsest-route-encounter-2026-10-22.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == registration['source_archive_sha256']
with zipfile.ZipFile(archive) as z:
    assert len(z.namelist()) == len(set(z.namelist())) == 18
    assert set(z.namelist()) == {p.name for p in (source / 'encounter').iterdir()}
    for name in z.namelist():
        assert z.read(name) == (source / 'encounter' / name).read_bytes()
sessions = []
for name in registration['modes']:
    identifier = name.rsplit('.', 1)[0]
    result = json.loads((root / (identifier + '.json')).read_text())
    assert result['status'] == 'passed' and result['browser_disconnected']
    assert result['automated'] and result['concurrent_sessions'] and not result['human_viewing_or_acceptance']
    assert 600 <= result['duration_seconds'] < 640
    elapsed_utc = (datetime.fromisoformat(result['ended_utc']) - datetime.fromisoformat(result['started_utc'])).total_seconds()
    assert abs(elapsed_utc - result['duration_seconds']) < 1
    assert result['counts']['actual'] == result['counts']['expected']
    assert not result['errors'] and not result['blocked']
    assert hashlib.sha256((source / 'encounter' / name).read_bytes()).hexdigest() == result['source_sha256']
    previous, frames = 0., 0
    for probe in result['probes']:
        assert 0 < probe['elapsed_seconds'] - previous <= 5
        assert abs(probe['probe_gap_seconds'] - (probe['elapsed_seconds'] - previous)) < 1e-8
        assert probe['visibility'] == 'visible' and probe['fully_in_view']
        assert probe['max_frame_gap_ms'] <= 5000 and probe['frame_age_ms'] <= 5000
        assert probe['frames'] > frames and not probe['mutations'] and not probe['visibility_events']
        previous, frames = probe['elapsed_seconds'], probe['frames']
    assert previous >= 600 and len(result['probes']) >= 590
    screenshots = {}
    for stage in ('start', 'end'):
        path = root / f'{identifier}-{stage}.png'
        assert path.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
        screenshots[stage] = hashlib.sha256(path.read_bytes()).hexdigest()
    sessions.append({'name': name, 'duration_seconds': result['duration_seconds'],
                     'started_utc': result['started_utc'], 'ended_utc': result['ended_utc'],
                     'probes': len(result['probes']), 'frames_observed': frames,
                     'max_probe_gap_seconds': max(p['probe_gap_seconds'] for p in result['probes']),
                     'max_frame_gap_ms': max(p['max_frame_gap_ms'] for p in result['probes']),
                     'counts': result['counts'], 'screenshots_sha256': screenshots})
out = {'status': 'passed', 'sessions': sessions, 'all_extracted_members_match_pinned_zip': True,
       'actual_executed_script_matches_committed_source': True, 'qualification_claims': [],
       'limitations': ['concurrent headless automation, not physical display or human attention',
                      '640-second watchdog covers presentation work, not startup or shutdown',
                      'no human artistic, independent operator or exhibition acceptance']}
with (root / 'independent-audit.json').open('x') as stream:
    json.dump(out, stream, indent=2)
print(json.dumps(out))
