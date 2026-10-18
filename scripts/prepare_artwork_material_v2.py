"""One approved offline material allocation; prepare/review before invoking once."""
import hashlib
import html
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import struct
import subprocess
import sys
import time
import wave
import xml.etree.ElementTree as ET
import zipfile

import verify_artwork_handoff as h

PHASE = h.ROOT / '.superpowers/sdd/artwork-material-v2'
REGISTRATION = h.ROOT / 'docs/plans/artwork-material-v2-registration.json'
IDS = ('d60e7d78cb1d4d04a4268f2528a6c534', 'c0ac36d0bcf54c9e90f948fe28454e0f')
REUSED = ('afterimage.svg', 'atlas.svg', 'space-between-two-flies.svg')
BUDGET = h.StorageBudget((PHASE,), h.StorageLimits(max_bytes=2 * 1024**3,
    min_free_bytes=2 * 1024**3, max_exports=3), headroom_bytes=1024**2)


def digest(path):
    path = h.artifacts._safe_path(path)
    h.require(path.is_file(), 'source is not a regular file')
    with path.open('rb') as stream:
        return {'size_bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def registration():
    return json.loads(REGISTRATION.read_text())


def pins_match(reg):
    return sys.version == reg['python']['version'] and importlib.metadata.version('numpy') == reg['numpy_version'] and all(digest(h.ROOT / name) == pin for name, pin in reg['sources'].items()) and all(
        digest(Path(row['path'])) == row['pin'] for row in reg['reused']) and digest(
        Path(sys.executable).resolve()) == reg['python']['pin']


def relative(name):
    path = Path(name)
    h.require(bool(name) and '\\' not in name and not path.is_absolute() and '..' not in path.parts
              and path.as_posix() == name, 'noncanonical member path')
    return path


def check_clock(start):
    h.require(time.monotonic() - start < 280, 'prepublication deadline exceeded')
    BUDGET.check(1024**2, path=PHASE / 'result.json')


def relocate(reg, start):
    archive = Path(reg['input_archive']['path'])
    h.require(digest(archive) == reg['input_archive']['pin'], 'input ZIP pin differs')
    raw_manifest = (h.ROOT / reg['input_manifest']['path']).read_bytes()
    manifest = json.loads(raw_manifest)
    h.require(digest(h.ROOT / reg['input_manifest']['path']) == reg['input_manifest']['pin'], 'inventory pin differs')
    rows = manifest['files']
    h.require(len(rows) == 98 and len({row['path'] for row in rows}) == 98
              and sum(row['size_bytes'] for row in rows) == 577207446, 'inventory differs')
    expected = {row['path']: row for row in rows}
    expected['input-manifest.json'] = {'size_bytes': len(raw_manifest),
        'sha256': hashlib.sha256(raw_manifest).hexdigest()}
    with BUDGET.lock():
        BUDGET.check(577207446 + 64 * 1024**2, path=PHASE / 'inputs')
        with zipfile.ZipFile(archive) as bundle:
            members = bundle.infolist()
            h.require(len(members) == 99 and {m.filename for m in members} == set(expected), 'ZIP allowlist differs')
            for member in members:
                relative(member.filename)
                h.require(stat.S_ISREG(member.external_attr >> 16) and member.compress_type == zipfile.ZIP_STORED
                          and member.file_size == expected[member.filename]['size_bytes'], 'ZIP member metadata differs')
            h.require(bundle.read('input-manifest.json') == raw_manifest, 'embedded manifest differs')
            (PHASE / 'inputs').mkdir()
            for row in rows:
                check_clock(start)
                target = PHASE / 'inputs' / relative(row['path'])
                target.parent.mkdir(parents=True, exist_ok=True)
                with bundle.open(row['path']) as source, target.open('xb') as out:
                    shutil.copyfileobj(source, out, 64 * 1024)
                h.require(digest(target) == {key: row[key] for key in ('size_bytes', 'sha256')}, 'relocated pin differs')
                BUDGET.check(1024**2, path=target)
    return rows


def relocated_match(rows):
    return all(digest(PHASE / 'inputs' / relative(row['path'])) == {
        key: row[key] for key in ('size_bytes', 'sha256')} for row in rows)


def export_child(index):
    reg = registration()
    report = {'status': 'failed', 'process': h.process_identity(), 'qualification_claims': []}
    old_handler = signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    sys.meta_path.insert(0, h.NoInference())
    receipt = PHASE / f'export-{index}.json'
    try:
        h.write_json(receipt, report, BUDGET)
        h.require(not {'torch', 'mujoco'}.intersection(sys.modules), 'runtime already imported')
        h.require(pins_match(reg), 'source changed before export')
        call = reg['exports'][index]
        report.update(argv=call['argv'], output=call['output'])
        report['returncode'] = h.cli.main(call['argv'])
        h.require(report['returncode'] == 0, 'export failed')
        report['artifact'] = digest(PHASE / 'artifacts' / call['output'])
        report['status'] = 'passed'
    except BaseException as error:
        report['status'] = 'failed'
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        report['runtime_imported'] = sorted({'torch', 'mujoco'}.intersection(sys.modules))
        report['numpy_version'] = getattr(sys.modules.get('numpy'), '__version__', None)
        if report['runtime_imported'] or report['numpy_version'] not in (None, reg['numpy_version']):
            report['status'] = 'failed'
        try:
            h.write_json(receipt, report, BUDGET)
        finally:
            signal.signal(signal.SIGTERM, old_handler)
    return 0 if report['status'] == 'passed' else 1



def check_comparison_geometry(raw, comparison):
    """Bind the displayed SVG routes/worlds to the verified comparison metadata."""
    ns = '{http://www.w3.org/2000/svg}'
    views = [ET.fromstring(value) for value in re.findall(r'<svg\b[^>]*>.*?</svg>', raw, re.S)]
    h.require(len(views) == 3, 'comparison SVG view count differs')
    arena = comparison['projection']['arena']
    scale = 360 / arena
    labels = ['overlay-title overlay-description', 'world-A world-A-description', 'world-B world-B-description']
    groups = []
    for root, label in zip(views, labels):
        h.require(root.get('aria-labelledby') == label, 'comparison world/view identity differs')
        found = root.findall(ns + 'g')
        h.require(len(found) == 1 and found[0].get('transform') ==
                  f'translate(400 400) scale({scale} {-scale})', 'comparison world projection differs')
        group = found[0]
        rectangles = group.findall(ns + 'rect')
        h.require(len(rectangles) >= 1 and [float(rectangles[0].get(key)) for key in
                  ('x', 'y', 'width', 'height')] == [-arena, -arena, 2 * arena, 2 * arena],
                  'comparison world arena differs')
        groups.append(group)
    def points(line):
        return [[float(value) for value in point.split(',')] for point in line.get('points', '').split()]
    expected = [(source['run_id'], str(trace['episode']), trace['points'])
                for side in ('left', 'right') for source in [comparison['comparison'][side]]
                for trace in source['traces']]
    actual = [(line.get('data-run-id'), line.get('data-episode'), points(line))
              for line in groups[0].findall(ns + 'polyline')]
    h.require(actual == expected, 'comparison overlay route identity/points differ')
    for side, group in zip(('left', 'right'), groups[1:]):
        source = comparison['comparison'][side]
        episodes = group.findall(ns + 'g')
        h.require(len(episodes) == len(source['worlds']) == len(source['traces']),
                  'comparison world episode count differs')
        for episode, world, trace in zip(episodes, source['worlds'], source['traces']):
            h.require(episode.get('data-episode') == str(world['episode']) == str(trace['episode'])
                      and world['world']['arena'] == arena, 'comparison world episode/projection differs')
            circles = [[float(circle.get(key)) for key in ('cx', 'cy', 'r')]
                       for circle in episode.findall(ns + 'circle')]
            h.require(circles == [*world['world']['obstacles'], world['world']['goal']],
                      'comparison displayed world geometry differs')
            lines = episode.findall(ns + 'polyline')
            h.require(len(lines) == 1 and points(lines[0]) == trace['points'],
                      'comparison world route points differ')


def check_and_package(result):
    art = PHASE / 'artifacts'
    svg = ET.parse(art / 'borrowed-body.svg').getroot()
    route = json.loads(svg.find('{http://www.w3.org/2000/svg}metadata').text)
    h.require(route['run_id'] == IDS[0] and len(route['traces'][0]['points']) == 1268, 'route source/count differs')
    points = svg.find('.//{http://www.w3.org/2000/svg}polyline').attrib['points']
    h.require([[float(v) for v in point.split(',')] for point in points.split()] == route['traces'][0]['points'], 'SVG route points differ')
    raw = (art / 'one-map-many-lives.html').read_text()
    match = re.search(r'<pre id="comparison-metadata">([^<]*)</pre>', raw)
    h.require(match is not None, 'comparison metadata missing')
    comparison = json.loads(html.unescape(match[1]))
    h.require(comparison['mode'] == 'offline recorded comparison', 'comparison mode differs')
    for side, run, count in [('left', IDS[0], 1268), ('right', IDS[1], 1293)]:
        source = comparison['comparison'][side]
        h.require(source['run_id'] == run and len(source['traces'][0]['points']) == count, 'comparison source/count differs')
    check_comparison_geometry(raw, comparison)
    for name in ('afterimage.svg', 'borrowed-body.svg', 'atlas.svg', 'space-between-two-flies.svg'):
        root = ET.parse(art / name).getroot()
        nodes = {node.get('id'): node for node in root.iter() if node.get('id')}
        labels = root.get('aria-labelledby', '').split()
        h.require(root.get('role') == 'img' and len(labels) == 2 and
                  all(key in nodes and (nodes[key].text or '').strip() for key in labels), 'SVG alternatives missing')
    audio_path = art / 'counterfactual-choir.wav'
    with wave.open(str(audio_path)) as audio:
        h.require((audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()) ==
                  (1, 2, 48000, 1216320), 'WAV framing/duration differs')
        pcm = audio.readframes(1216320)
    wav = audio_path.read_bytes()
    h.require(wav[:4] == b'RIFF' and struct.unpack_from('<I', wav, 4)[0] == len(wav) - 8, 'RIFF length differs')
    position, meta = 12, None
    while position < len(wav):
        kind, length = struct.unpack_from('<4sI', wav, position)
        h.require(position + 8 + length <= len(wav), 'truncated RIFF')
        if kind == b'plmp':
            h.require(meta is None, 'duplicate WAV provenance')
            meta = json.loads(wav[position + 8:position + 8 + length])
        position += 8 + length + length % 2
    h.require(position == len(wav) and meta is not None and meta['source']['run_id'] == IDS[0] and
              meta['pcm_sha256'] == hashlib.sha256(pcm).hexdigest() and 'not biological audio' in meta['label'], 'WAV provenance differs')
    h.require(meta['timing']['sample_boundaries'] == list(range(0, 1216321, 960)) and
              [voice['population'] for voice in meta['mapping']['voices']] ==
              ['visual_left', 'visual_right', 'descending'], 'WAV timing/voices differ')
    guide = (h.ROOT / 'docs/reports/artwork-review-development-evidence/review-guide-template.md').read_text().replace('@@INPUT_ZIP_SHA256@@', result['input_zip']['sha256'])
    guide = guide.replace('@@INPUT_MANIFEST_SHA256@@', result['input_manifest']['sha256'])
    guide = guide.replace('Preparation status: **pending final checks**. All six outputs, source identity,\narchive hashes and file links must be checked before this pack is handed over.\nOpen the supplied files in a local browser or audio player once those checks pass.',
                          'Byte, provenance and artifact checks passed. Open the supplied files in a local\nbrowser or audio player; human review has not been performed.')
    guide = guide.replace('A small model portrait, not fly perception.', 'Insufficient for assessing sustained material; not fly perception.')
    guide = guide.replace('Mode and expected file', 'Mode and file').replace('Final artifact checks remain pending.', 'Artifact checks passed.')
    guide = guide.replace('Both final values are pending checks.', 'Both values identify the supplied files.')
    h.require('@@' not in guide and 'pending final checks' not in guide, 'unresolved guide values')
    with (art / 'README.md').open('x') as out:
        out.write(guide)
    with (art / 'THIRD_PARTY_NOTICES.md').open('xb') as out:
        out.write((PHASE / 'inputs/THIRD_PARTY_NOTICES.md').read_bytes())
    files = {name: digest(art / name) for name in sorted([*h.OUTPUTS, 'README.md', 'THIRD_PARTY_NOTICES.md'])}
    h.write_json(art / 'checksums.json', {'files': files, 'qualification_claims': []}, BUDGET)
    names = sorted([*files, 'checksums.json'])
    review_zip = PHASE / 'palimpsest-artwork-review-development-v2.zip'
    with BUDGET.lock():
        BUDGET.check(32 * 1024**2, path=review_zip)
        with zipfile.ZipFile(review_zip, 'x', compression=zipfile.ZIP_STORED) as bundle:
            for name in names:
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system, info.external_attr = 3, 0o100644 << 16
                bundle.writestr(info, (art / name).read_bytes())
        with zipfile.ZipFile(review_zip) as bundle:
            h.require(bundle.namelist() == names and all(bundle.read(name) == (art / name).read_bytes()
                                                       for name in names), 'review ZIP differs')
    result.update(review_zip=digest(review_zip), review_members=names, artifact_checks='passed')

def self_check():
    """Software-only trust-boundary check; no files, leases or exports."""
    assert relative('runs/source/recording/chunks/000000.npz').as_posix() == 'runs/source/recording/chunks/000000.npz'
    for name in ('', '/absolute', '../escape', 'a/../escape', 'a\\b', 'a//b'):
        try:
            relative(name)
        except ValueError:
            pass
        else:
            raise AssertionError('Unsafe archive member accepted: ' + name)
    return 0


def main():
    start = time.monotonic()
    reg = registration()
    marker = PHASE / 'launched.json'
    h.require(not PHASE.exists(), 'Consumed/nonfresh phase; do not retry')
    h.require(Path(sys.executable).resolve() == Path(reg['python']['resolved']), 'Python identity differs')
    h.require(subprocess.check_output(['git', 'status', '--porcelain'], cwd=h.ROOT, text=True) == '', 'Clean committed source required')
    h.require(pins_match(reg), 'prospective source pins differ')
    h.require(Path(reg['input_archive']['path']).stat().st_size == reg['input_archive']['pin']['size_bytes'], 'ZIP size differs')
    h.require(shutil.disk_usage(h.ROOT).free >= 4 * 1024**3, 'initial free-space floor')
    h.require(all(os.environ.get(key) == '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')), 'CPU thread caps differ')
    PHASE.mkdir(parents=True, exist_ok=False)
    with marker.open('x') as out:
        json.dump({'registration': digest(REGISTRATION), 'source_commit': subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=h.ROOT, text=True).strip()}, out)
    result = {'status': 'failed', 'qualification_claims': [], 'exports': [], 'finalization_errors': []}
    rows = None
    old_handler = signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        with BUDGET.lock():
            for source in (REGISTRATION, Path(__file__), h.ROOT / 'docs/plans/artwork-material-v2.md'):
                BUDGET.check(source.stat().st_size, path=PHASE / source.name)
                with (PHASE / source.name).open('xb') as out:
                    out.write(source.read_bytes())
        rows = relocate(reg, start)
        (PHASE / 'artifacts').mkdir()
        for index, call in enumerate(reg['exports']):
            check_clock(start)
            remaining = min(120, 275 - (time.monotonic() - start))
            h.require(remaining > 0, 'No export deadline remains')
            supervision = h.bounded_process([sys.executable, '-B', str(Path(__file__)), '--export', str(index)],
                PHASE / f'export-{index}-supervision', remaining, log_max_bytes=1024**2, storage_budget=BUDGET)
            worker = json.loads((PHASE / f'export-{index}.json').read_text())
            cleanup = h.cleanup_check(worker['process'])
            result['exports'].append({'supervisor': supervision, 'worker': worker, 'cleanup': cleanup})
            h.require(supervision['status'] == 'completed' and supervision['returncode'] == 0
                      and worker['status'] == 'passed' and cleanup['passed'], 'Export or cleanup failed')
        with BUDGET.lock():
            for row in reg['reused']:
                target = PHASE / 'artifacts' / Path(row['path']).name
                BUDGET.check(row['pin']['size_bytes'], path=target)
                with target.open('xb') as out:
                    out.write(Path(row['path']).read_bytes())
                h.require(digest(target) == row['pin'], 'reused copy differs')
        result.update(input_zip=reg['input_archive']['pin'], input_manifest=reg['input_manifest']['pin'])
        check_clock(start)
        check_and_package(result)
        result['artifacts'] = {name: digest(PHASE / 'artifacts' / name) for name in h.OUTPUTS}
        result['status'] = 'passed'
    except BaseException as error:
        result['status'] = 'failed'
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        checks = [('input ZIP', lambda: digest(Path(reg['input_archive']['path'])) == reg['input_archive']['pin']),
                  ('implementation/controls/reused inputs', lambda: pins_match(reg)),
                  ('registration', lambda: digest(REGISTRATION) == json.loads(marker.read_text())['registration'])]
        if rows is not None:
            checks.append(('relocated input', lambda: relocated_match(rows)))
        for label, check in checks:
            try:
                h.require(check(), label + ' changed')
            except BaseException as error:
                result['status'] = 'failed'
                result['finalization_errors'].append(label + ': ' + str(error))
        try:
            with BUDGET.lock():
                result['writer_lease_released'] = True
        except BaseException as error:
            result['status'] = 'failed'
            result['finalization_errors'].append('writer lease: ' + str(error))
        if time.monotonic() - start >= 300:
            result.update(status='failed', error='aggregate deadline exceeded')
        result['elapsed_before_receipt_seconds'] = time.monotonic() - start
        try:
            h.write_json(PHASE / 'result.json', result, BUDGET)
            if time.monotonic() - start >= 300:
                result.update(status='failed', error='deadline exceeded during publication')
                h.write_json(PHASE / 'result.json', result, BUDGET)
        finally:
            signal.signal(signal.SIGTERM, old_handler)
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(self_check() if sys.argv[1:] == ['--self-check'] else
                     export_child(int(sys.argv[2])) if len(sys.argv) == 3 and sys.argv[1] == '--export' else main())
