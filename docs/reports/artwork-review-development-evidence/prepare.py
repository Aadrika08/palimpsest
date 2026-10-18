"""One finite existing-export preparation; no model or native invocation."""
import hashlib
import html
import json
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import sys
import time
import wave
import xml.etree.ElementTree as ET
import zipfile

import verify_artwork_handoff as h

PHASE = Path(__file__).resolve().parent
OLD = h.ROOT.parent / 'artwork-portability-preparation/.superpowers/sdd'
INPUT = OLD / 'artwork-portability-preparation/operator-inputs'
REVIEW = OLD / 'artwork-review-preparation-v1/review-v2'
RAW = h.ROOT.parent / 'research-phase/runs/memory-travel-recovery-20261004T133718Z'
INDEX = h.ROOT / 'docs/reports/memory-travel-recovery-evidence/owners/execution.json'
IDS = ('d60e7d78cb1d4d04a4268f2528a6c534', 'c0ac36d0bcf54c9e90f948fe28454e0f')
REUSED = ('afterimage.svg', 'atlas.svg', 'space-between-two-flies.svg')
REUSED_INDEX = h.ROOT / 'docs/reports/artwork-review-preparation.json'
BUDGET = h.StorageBudget((PHASE,), h.StorageLimits(max_bytes=2 * 1024**3,
    min_free_bytes=2 * 1024**3, max_exports=3), headroom_bytes=1024**2)


def digest(path):
    h.require(path.is_file() and not path.is_symlink(), 'source is not a regular file')
    with path.open('rb') as stream:
        return {'size_bytes': path.stat().st_size, 'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()}


def relative(name):
    path = Path(name)
    h.require(bool(name) and '\\' not in name and not path.is_absolute() and '..' not in path.parts and path.as_posix() == name,
              'noncanonical member path')
    return path


def selections():
    old = h.load_manifest()
    pins = h.admit(INPUT, old)
    rows = [{**row, 'source': str(INPUT / row['path'])} for row in old['files']
            if not any(row['path'].startswith('runs/' + old['run_ids'][key] + '/') for key in ('left', 'right'))]
    indexed = json.loads(INDEX.read_text())['artifact_index']
    for run in IDS:
        prefix = 'prerequisites/runs/' + run + '/recording/'
        chosen = [row for row in indexed if row['path'].startswith(prefix)]
        h.require(len(chosen) == (42 if run == IDS[0] else 43), 'recording index differs')
        for row in chosen:
            suffix = relative(row['path']).as_posix()[len(prefix):]
            rows.append({'path': 'runs/' + run + '/recording/' + suffix, 'size_bytes': row['bytes'],
                         'sha256': row['sha256'], 'source': str(RAW / row['path'])})
    h.require(len(rows) == 98 and len({row['path'] for row in rows}) == 98
              and sum(row['size_bytes'] for row in rows) == 577207446, 'source selection differs')
    for row in rows:
        relative(row['path'])
        h.require(digest(Path(row['source'])) == {k: row[k] for k in ('size_bytes', 'sha256')}, 'source pin differs')
    return rows, pins


def commands():
    paths = [str(PHASE / 'inputs/runs' / run) for run in IDS]
    calls = [('borrowed-body.svg', ['export', paths[0], '--format', 'svg']),
             ('counterfactual-choir.wav', ['sonify', paths[0], '--episode', '0', '--population', 'visual_left',
                                        '--population', 'visual_right', '--population', 'descending']),
             ('one-map-many-lives.html', ['compare', *paths])]
    return [(name, ['--repo', str(h.ROOT), *args, '--output', str(PHASE / 'artifacts' / name),
                   '--storage-max-bytes', str(64 * 1024**2), '--min-free-bytes', str(2 * 1024**3),
                   '--max-exports', '3', '--log-max-bytes', str(1024**2)]) for name, args in calls]


def exports():
    h.require(not {'torch', 'mujoco'}.intersection(sys.modules), 'runtime already imported')
    sys.meta_path.insert(0, h.NoInference())
    report = {'process': h.process_identity(), 'status': 'failed', 'rows': [], 'qualification_claims': []}
    try:
        for name, argv in commands():
            row = {'output': name, 'argv': argv, 'returncode': h.cli.main(argv)}
            report['rows'].append(row)
            h.require(row['returncode'] == 0, 'export failed: ' + name)
            row['artifact'] = digest(PHASE / 'artifacts' / name)
        report['status'] = 'passed'
    except BaseException as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        report['runtime_imported'] = sorted({'torch', 'mujoco'}.intersection(sys.modules))
        report['numpy_version'] = getattr(sys.modules.get('numpy'), '__version__', None)
        if report['runtime_imported']:
            report['status'] = 'failed'
        h.write_json(PHASE / 'worker.json', report, BUDGET)
    return 0 if report['status'] == 'passed' else 1


def check_and_package(result):
    art = PHASE / 'artifacts'
    svg = ET.parse(art / 'borrowed-body.svg').getroot()
    route = json.loads(svg.find('{http://www.w3.org/2000/svg}metadata').text)
    h.require(route['run_id'] == IDS[0] and len(route['traces'][0]['points']) == 1268, 'route source/count differs')
    raw = (art / 'one-map-many-lives.html').read_text()
    match = re.search(r'<pre id="comparison-metadata">([^<]*)</pre>', raw)
    h.require(match is not None, 'comparison metadata missing')
    comparison = json.loads(html.unescape(match[1]))
    h.require(comparison['mode'] == 'offline recorded comparison', 'comparison mode differs')
    for side, run, count in [('left', IDS[0], 1268), ('right', IDS[1], 1293)]:
        source = comparison['comparison'][side]
        h.require(source['run_id'] == run and len(source['traces'][0]['points']) == count, 'comparison source/count differs')
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
    guide = (PHASE / 'review-guide.md').read_text().replace('@@INPUT_ZIP_SHA256@@', result['input_zip']['sha256'])
    guide = guide.replace('@@INPUT_MANIFEST_SHA256@@', result['input_manifest']['sha256'])
    guide = guide.replace('Preparation status: **pending final checks**. All six outputs, source identity,\narchive hashes and file links must be checked before this pack is handed over.\nOpen the supplied files in a local browser or audio player once those checks pass.',
                          'Byte, provenance and artifact checks passed. Open the supplied files in a local\nbrowser or audio player; human review has not been performed.')
    guide = guide.replace('Mode and expected file', 'Mode and file').replace('Final artifact checks remain pending.', 'Artifact checks passed.')
    guide = guide.replace('Both final values are pending checks.', 'Both values identify the supplied files.')
    h.require('@@' not in guide and 'pending final checks' not in guide, 'unresolved guide values')
    with (art / 'README.md').open('x') as out:
        out.write(guide)
    with (art / 'THIRD_PARTY_NOTICES.md').open('xb') as out:
        out.write((INPUT / 'THIRD_PARTY_NOTICES.md').read_bytes())
    files = {name: digest(art / name) for name in sorted([*h.OUTPUTS, 'README.md', 'THIRD_PARTY_NOTICES.md'])}
    h.write_json(art / 'checksums.json', {'files': files, 'qualification_claims': []}, BUDGET)
    names = sorted([*files, 'checksums.json'])
    review_zip = PHASE / 'palimpsest-artwork-review-development-v1.zip'
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


def main():
    started = time.monotonic()
    h.require(not any((PHASE / name).exists() for name in ('registration.json', 'launched.json', 'inputs',
              'artifacts', 'result.json', 'palimpsest-artwork-inputs-development-v1.zip')), 'one-pass namespace consumed')
    h.require(shutil.disk_usage(PHASE).free >= 4 * 1024**3, 'initial free-space floor')
    source_commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=h.ROOT, check=True,
                                   text=True, capture_output=True).stdout.strip()
    h.require(subprocess.run(['git', 'status', '--porcelain'], cwd=h.ROOT, check=True,
                            text=True, capture_output=True).stdout == '', 'source is dirty')
    rows, old_pins = selections()
    source_pins = h.sources()
    source_pins['prepare.py'] = digest(Path(__file__))
    source_pins['review-guide.md'] = digest(PHASE / 'review-guide.md')
    source_pins['recovery-index'] = digest(INDEX)
    source_pins['control-check.py'] = digest(PHASE / 'control-check.py')
    source_pins['phase-plan'] = digest(h.ROOT / 'docs/plans/artwork-review-development-material.md')
    source_pins['reused-index'] = digest(REUSED_INDEX)
    published = json.loads(REUSED_INDEX.read_text())['artifact_files']
    for name in REUSED:
        h.require(digest(REVIEW / name) == published[name], 'reused artifact differs from published pin')
        source_pins['reused:' + name] = published[name]
    manifest = {'id': 'artwork-development-material-v1', 'files': [{k: row[k] for k in
                ('path', 'size_bytes', 'sha256')} for row in rows], 'source_bytes': 577207446,
                'run_ids': {'left': IDS[0], 'right': IDS[1], 'afterimage': h.load_manifest()['run_ids']['afterimage']},
                'scope': 'Derivative source subset; no native states, restore/replay or human acceptance',
                'qualification_claims': []}
    registration = {'invocations': 1, 'exports': 3, 'native_owners': 0, 'corrective_studies': 0,
                    'aggregate_seconds': 300, 'child_seconds': 120, 'outer_term_seconds': 290,
                    'kill_grace_seconds': 5, 'phase_bytes': 2 * 1024**3, 'min_free_bytes': 2 * 1024**3,
                    'source_commit': source_commit, 'python_version': sys.version,
                    'python_resolved': str(Path(sys.executable).resolve()),
                    'python_sha256': digest(Path(sys.executable).resolve())['sha256'],
                    'sources': source_pins, 'inputs': rows, 'argv': commands(), 'qualification_claims': []}
    h.write_json(PHASE / 'registration.json', registration, BUDGET)
    with (PHASE / 'launched.json').open('x') as stream:
        json.dump({'registration_sha256': digest(PHASE / 'registration.json')['sha256']}, stream)
    result = {'status': 'failed', 'qualification_claims': [], 'finalization_errors': []}
    old_handler = signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        BUDGET.check(2 * manifest['source_bytes'] + 32 * 1024**2, path=PHASE / 'inputs')
        h.write_json(PHASE / 'input-manifest.json', manifest, BUDGET)
        input_zip = PHASE / 'palimpsest-artwork-inputs-development-v1.zip'
        with BUDGET.lock():
            with zipfile.ZipFile(input_zip, 'x', compression=zipfile.ZIP_STORED) as bundle:
                for row in sorted(rows, key=lambda row: row['path']):
                    info = zipfile.ZipInfo(row['path'], date_time=(1980, 1, 1, 0, 0, 0))
                    info.create_system, info.external_attr = 3, 0o100644 << 16
                    bundle.writestr(info, Path(row['source']).read_bytes())
                info = zipfile.ZipInfo('input-manifest.json', date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system, info.external_attr = 3, 0o100644 << 16
                bundle.writestr(info, (PHASE / 'input-manifest.json').read_bytes())
            (PHASE / 'inputs').mkdir()
            with zipfile.ZipFile(input_zip) as bundle:
                h.require(bundle.namelist() == sorted(row['path'] for row in rows) + ['input-manifest.json'], 'ZIP allowlist')
                h.require(bundle.read('input-manifest.json') == (PHASE / 'input-manifest.json').read_bytes(), 'ZIP manifest differs')
                for row in rows:
                    target = PHASE / 'inputs' / relative(row['path'])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with bundle.open(row['path']) as source, target.open('xb') as out:
                        shutil.copyfileobj(source, out, 64 * 1024)
                    h.require(digest(target) == {k: row[k] for k in ('size_bytes', 'sha256')}, 'relocated source differs')
                    BUDGET.check(1024**2, path=target)
        (PHASE / 'artifacts').mkdir()
        result['supervisor'] = h.bounded_process([sys.executable, str(Path(__file__)), '--exports'],
            PHASE / 'supervisor', 120, log_max_bytes=1024**2, storage_budget=BUDGET)
        result['worker'] = json.loads((PHASE / 'worker.json').read_text())
        result['cleanup'] = h.cleanup_check(result['worker']['process'])
        h.require(result['supervisor']['status'] == 'completed' and result['supervisor']['returncode'] == 0
                  and result['worker']['status'] == 'passed' and result['cleanup']['passed'], 'export/cleanup failed')
        for name in REUSED:
            h.check_artifact(REVIEW / name, h.load_manifest())
            with (PHASE / 'artifacts' / name).open('xb') as out:
                out.write((REVIEW / name).read_bytes())
            h.require(digest(PHASE / 'artifacts' / name) == source_pins['reused:' + name], 'reused copy differs')
        result.update(input_zip=digest(input_zip), input_manifest=digest(PHASE / 'input-manifest.json'),
                      artifacts={name: digest(PHASE / 'artifacts' / name) for name in h.OUTPUTS})
        check_and_package(result)
        result['status'] = 'passed'
    except BaseException as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        for label, check in [('original source subset', lambda: h.admit(INPUT, h.load_manifest()) == old_pins),
                             ('selected sources', lambda: all(digest(Path(row['source'])) == {k: row[k] for k in
                              ('size_bytes', 'sha256')} for row in rows)),
                             ('relocated sources', lambda: all(digest(PHASE / 'inputs' / relative(row['path'])) ==
                              {k: row[k] for k in ('size_bytes', 'sha256')} for row in rows)),
                             ('implementation', lambda: h.sources() == {k: v for k, v in source_pins.items()
                              if k not in {'prepare.py', 'review-guide.md', 'recovery-index', 'control-check.py', 'phase-plan', 'reused-index'}
                              and not k.startswith('reused:')}),
                             ('reused artifacts', lambda: all(digest(REVIEW / name) == source_pins['reused:' + name] for name in REUSED)),
                             ('controls', lambda: all(digest(path) == source_pins[key] for key, path in
                              [('prepare.py', Path(__file__)), ('review-guide.md', PHASE / 'review-guide.md'),
                               ('recovery-index', INDEX), ('control-check.py', PHASE / 'control-check.py'),
                               ('phase-plan', h.ROOT / 'docs/plans/artwork-review-development-material.md'), ('reused-index', REUSED_INDEX)]))]:
            try:
                h.require(check(), label + ' changed')
            except BaseException as error:
                result['finalization_errors'].append(str(error))
                result['status'] = 'failed'
        try:
            with BUDGET.lock():
                result['writer_lease_released'] = True
        except BaseException as error:
            result['status'] = 'failed'
            result['finalization_errors'].append('writer lease: ' + str(error))
        if time.monotonic() - started > 300:
            result.update(status='failed', error='aggregate deadline exceeded')
        result['elapsed_before_receipt_seconds'] = time.monotonic() - started
        h.write_json(PHASE / 'result.json', result, BUDGET)
        signal.signal(signal.SIGTERM, old_handler)
    if time.monotonic() - started > 300:
        result.update(status='failed', error='aggregate deadline exceeded during receipt publication')
        h.write_json(PHASE / 'result.json', result, BUDGET)
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(exports() if sys.argv[1:] == ['--exports'] else main())
