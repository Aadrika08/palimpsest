"""One fixed offline handoff pass. Run only under separately reviewed outer controls.

No copying, inference or exhibition qualification. Each CLI owns its writer lease.
Storage checks are preflight/final observations, not an atomic filesystem quota.
"""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
import signal
import struct
import sys
import time
import wave
import xml.etree.ElementTree as ET

from palimpsest import artifacts, cli
from palimpsest.evaluate import bounded_process
from palimpsest.storage import StorageBudget, StorageLimits
from verify_afterimage import cleanup_check, process_identity, write_json

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/artwork-handoff.json'
MANIFEST_SHA256 = '9766f285b7f4008f894845cc12d51e34a14dafc5eaf88fba6e13bdec36944982'
OUTPUTS = ('afterimage.svg', 'borrowed-body.svg', 'one-map-many-lives.html',
           'counterfactual-choir.wav', 'atlas.svg', 'space-between-two-flies.svg')
SOURCE_NAMES = ('__init__', '__main__', 'cli', 'artifacts', 'records', 'afterimage',
                'comparison', 'sonification', 'atlas', 'specimens', 'male_model',
                'male_policy', 'storage', 'evaluate')
SOURCE_SCOPE = 'Selected offline implementation files and lock metadata; not the whole tracked source tree or Python runtime.'


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def fingerprint(path, limit):
    raw = artifacts._read(path, limit)
    return {'size_bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def load_manifest():
    raw = artifacts._read(MANIFEST, 64 * 1024)
    require(hashlib.sha256(raw).hexdigest() == MANIFEST_SHA256, 'fixed handoff manifest changed')
    manifest = artifacts._json(raw)
    require(tuple(row['file'] for row in manifest['outputs']) == OUTPUTS, 'fixed output order differs')
    return manifest


def sources():
    paths = [ROOT / ('src/palimpsest/' + name + '.py') for name in SOURCE_NAMES]
    paths += [Path(__file__), ROOT / 'scripts/verify_afterimage.py', MANIFEST,
              ROOT / 'pyproject.toml', ROOT / 'uv.lock']
    return {str(path.relative_to(ROOT)): fingerprint(path, 4 * 1024**2) for path in paths}


def admit(inputs, manifest):
    """Exact relocated allowlist; descriptive original_source is never resolved."""
    inputs = artifacts._safe_path(inputs)
    pending, actual, entries = [inputs], set(), 0
    while pending:
        with os.scandir(pending.pop()) as directory:
            for entry in directory:
                entries += 1
                require(entries <= 64 and not entry.is_symlink(), 'input tree exceeds bound or contains symlink')
                if entry.is_dir(follow_symlinks=False):
                    pending.append(Path(entry.path))
                else:
                    require(entry.is_file(follow_symlinks=False), 'input is not a regular file')
                    actual.add(Path(entry.path).relative_to(inputs).as_posix())
    expected = {row['path'] for row in manifest['files']}
    require(len(expected) == 19 and actual == expected, 'input allowlist differs')
    require(sum(row['size_bytes'] for row in manifest['files']) == manifest['source_bytes']
            <= manifest['limits']['input_bytes'], 'input bytes exceed fixed bound')
    result = {}
    for row in manifest['files']:
        path = Path(row['path'])
        require(not path.is_absolute() and '..' not in path.parts, 'nonrelative source path')
        value = fingerprint(inputs / path, row['size_bytes'])
        require(value == {key: row[key] for key in ('size_bytes', 'sha256')}, 'input hash/size differs: ' + str(path))
        result[str(path)] = value
    return result


def commands(inputs, output, manifest):
    ids = manifest['run_ids']
    left, right, portrait = [str(inputs / 'runs' / ids[key]) for key in ('left', 'right', 'afterimage')]
    calls = [['afterimage', 'render', portrait], ['export', left, '--format', 'svg'],
             ['compare', left, right], ['sonify', left, '--population', 'visual_left',
              '--population', 'visual_right', '--population', 'descending', '--episode', '0'],
             ['atlas', '--graph', str(inputs / 'graph/source-graph.json'), '--graph-manifest',
              str(inputs / 'graph/extraction.json'), '--cut-node', '12781'],
             ['specimens', str(inputs / 'specimens/pair.json')]]
    limits = manifest['limits']
    flags = ['--storage-max-bytes', str(limits['output_bytes']), '--min-free-bytes',
             str(limits['min_free_bytes']), '--max-exports', '6', '--log-max-bytes', str(limits['log_bytes_per_stream'])]
    return [['--repo', str(ROOT), *call, '--output', str(output / name), *flags]
            for call, name in zip(calls, OUTPUTS)]


def check_artifact(path, manifest):
    raw = artifacts._read(path, 16 * 1024**2)
    ids, name = manifest['run_ids'], path.name
    if name.endswith('.wav'):
        with wave.open(str(path), 'rb') as audio:
            require((audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes())
                    == (1, 2, 48000, 3840), 'choir PCM format/duration differs')
            pcm = audio.readframes(3840)
        position, meta = 12, None
        require(raw[:4] == b'RIFF' and struct.unpack_from('<I', raw, 4)[0] == len(raw) - 8, 'invalid RIFF framing')
        while position < len(raw):
            kind, length = struct.unpack_from('<4sI', raw, position)
            require(position + 8 + length <= len(raw), 'truncated RIFF chunk')
            if kind == b'plmp':
                require(meta is None, 'duplicate WAV provenance')
                meta = artifacts._json(raw[position + 8:position + 8 + length])
            position += 8 + length + length % 2
        require(position == len(raw) and meta is not None, 'missing WAV provenance')
        require(meta['source']['run_id'] == ids['left'] and 'not biological audio' in meta['label']
                and meta['pcm_sha256'] == hashlib.sha256(pcm).hexdigest(), 'choir provenance differs')
        require([voice['population'] for voice in meta['mapping']['voices']]
                == ['visual_left', 'visual_right', 'descending'], 'choir voices differ')
    elif name.endswith('.html'):
        match = re.search(r'<pre id="comparison-metadata">([^<]*)</pre>', raw.decode())
        require(match is not None, 'comparison metadata missing')
        meta = artifacts._json(html.unescape(match[1]))
        comparison = meta['comparison']
        require(meta['mode'] == 'offline recorded comparison' and meta['route_arrays_equal'] is True,
                'comparison label/null route differs')
        for side in ('left', 'right'):
            require(comparison[side]['run_id'] == ids[side]
                    and len(comparison[side]['traces'][0]['points']) == 5, 'comparison source/ticks differ')
        require(comparison['left']['traces'] == comparison['right']['traces'], 'coincident traces changed')
    else:
        svg = ET.fromstring(raw)
        meta = artifacts._json(svg.find('{http://www.w3.org/2000/svg}metadata').text)
        if name == 'afterimage.svg':
            require(meta['source_run_id'] == ids['afterimage'] and meta['model_dt_seconds'] == .02
                    and [row['frame'] for row in meta['alignment']] == list(range(8)), 'portrait alignment differs')
            require('not verified consent' in meta['rights_limit'], 'portrait rights limitation missing')
        elif name == 'borrowed-body.svg':
            require(meta['run_id'] == ids['left'] and len(meta['traces'][0]['points']) == 5, 'route source/ticks differ')
        elif name == 'atlas.svg':
            require(meta['intervention']['node_ids'] == [12781] and meta['removed_edges'] == 135
                    and meta['lost_input_output_pairs'] == 137, 'atlas structure differs')
        else:
            require(sum(row['edges'] for row in meta['structures']) == 37007
                    and meta['projection']['registration'] == 'none', 'anatomical geometry/registration differs')
    return {'status': 'passed', **fingerprint(path, 16 * 1024**2)}


class NoInference:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'torch', 'mujoco'}:
            raise RuntimeError('offline handoff forbids Torch/MuJoCo imports')


def worker(inputs, output, manifest, budget):
    started = time.monotonic()
    calls = commands(inputs, output, manifest)
    report = {'id': manifest['id'], 'agent_operated': True, 'qualification_claims': [],
              'source_inventory_scope': SOURCE_SCOPE,
              'status': 'failed', 'declarations': manifest['declarations'],
              'rows': [{'output': name, 'label': spec['label'], 'argv': argv, 'status': 'not_started'}
                       for name, spec, argv in zip(OUTPUTS, manifest['outputs'], calls)]}
    guard = NoInference()
    try:
        require(not {'torch', 'mujoco'}.intersection(sys.modules), 'offline process already loaded runtime')
        sys.meta_path.insert(0, guard)
        report['process'] = process_identity()
        write_json(output / 'worker.json', report, budget)
        report['sources_before'] = sources()
        report['inputs_before'] = admit(inputs, manifest)
        for row in report['rows']:
            row.update(status='failed', started_elapsed_seconds=time.monotonic() - started)
            budget.check(2 * 1024**2, path=output / row['output'])
            write_json(output / 'worker.json', report, budget)
            row['returncode'] = cli.main(row['argv'])
            require(row['returncode'] == 0, 'CLI failed: ' + row['output'])
            row['artifact'] = check_artifact(output / row['output'], manifest)
            row.update(status='passed', finished_elapsed_seconds=time.monotonic() - started)
        require(time.monotonic() - started <= manifest['limits']['child_seconds'], 'worker deadline exceeded')
        report['status'] = 'passed'
    except BaseException as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        report['finalization_errors'] = []
        for key, read in (('inputs', lambda: admit(inputs, manifest)), ('sources', sources)):
            if key + '_before' in report:
                try:
                    report[key + '_after'] = read()
                    require(report[key + '_after'] == report[key + '_before'], key + ' changed')
                except BaseException as error:
                    report['finalization_errors'].append(type(error).__name__ + ': ' + str(error))
                    report['status'] = 'failed'
        report['numpy_version'] = getattr(sys.modules.get('numpy'), '__version__', None)
        if guard in sys.meta_path:
            sys.meta_path.remove(guard)
        report['elapsed_before_publication_seconds'] = time.monotonic() - started
        write_json(output / 'worker.json', report, budget)
    return report


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    manifest = load_manifest()
    inputs, output = artifacts._safe_path(args.inputs), artifacts._safe_path(args.output)
    require(not output.is_relative_to(inputs) and not inputs.is_relative_to(output), 'input/output roots overlap')
    limits = manifest['limits']
    budget = StorageBudget((output,), StorageLimits(max_bytes=limits['output_bytes'],
                           min_free_bytes=limits['min_free_bytes'], max_exports=6))
    if args.worker:
        return 0 if worker(inputs, output, manifest, budget)['status'] == 'passed' else 1
    output.mkdir(parents=True, exist_ok=False)
    report = {'id': manifest['id'], 'manifest_sha256': MANIFEST_SHA256, 'agent_operated': True,
              'source_inventory_scope': SOURCE_SCOPE,
              'qualification_claims': [], 'status': 'failed', 'python': sys.version,
              'rows': [{'output': name, 'status': 'not_started'} for name in OUTPUTS],
              'storage_enforcement': 'preflight and final recounts; not an atomic filesystem quota'}
    old_handler = signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        report['sources_before'] = sources()
        report['inputs_before'] = admit(inputs, manifest)
        budget.check(2 * 1024**2, path=output)
        command = [sys.executable, str(Path(__file__).resolve()), '--inputs', str(inputs), '--output', str(output), '--worker']
        report['supervisor'] = bounded_process(command, output / 'supervisor', limits['child_seconds'],
                                              log_max_bytes=limits['log_bytes_per_stream'], storage_budget=budget)
        child = artifacts._json(artifacts._read(output / 'worker.json', 4 * 1024**2))
        report['worker'] = child
        report['rows'] = child['rows']
        report['cleanup'] = cleanup_check(child['process'])
        elapsed = report['supervisor'].get('elapsed_seconds')
        require(report['supervisor']['status'] == 'completed' and report['supervisor']['returncode'] == 0
                and type(elapsed) in (int, float) and 0 <= elapsed <= limits['child_seconds']
                and child['status'] == 'passed' and report['cleanup']['passed'], 'child/export/cleanup failed')
        require(child['sources_before'] == child['sources_after'] == report['sources_before']
                and child['inputs_before'] == child['inputs_after'] == report['inputs_before'], 'worker admission differs')
        require([row['output'] for row in child['rows']] == list(OUTPUTS)
                and [row['argv'] for row in child['rows']] == commands(inputs, output, manifest)
                and all(row['status'] == 'passed' for row in child['rows']), 'incomplete six-mode pass')
        for row in child['rows']:
            require(check_artifact(output / row['output'], manifest) == row['artifact'], 'artifact changed after child drain')
        require(time.monotonic() - started <= limits['normal_total_seconds'], 'normal total deadline exceeded')
        report['storage'] = budget.check(128 * 1024, path=output / 'report.json')
        report['status'] = 'passed'
    except BaseException as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
    finally:
        report['finalization_errors'] = []
        for key, read in (('inputs', lambda: admit(inputs, manifest)), ('sources', sources)):
            if key + '_before' in report:
                try:
                    report[key + '_after'] = read()
                    require(report[key + '_after'] == report[key + '_before'], key + ' changed')
                except BaseException as error:
                    report['finalization_errors'].append(type(error).__name__ + ': ' + str(error))
                    report['status'] = 'failed'
        signal.signal(signal.SIGTERM, old_handler)
        report['elapsed_before_publication_seconds'] = time.monotonic() - started
        write_json(output / 'report.json', report, budget)
    if time.monotonic() - started > limits['normal_total_seconds']:
        report.update(status='failed', error='normal deadline exceeded during publication')
        write_json(output / 'report.json', report, budget)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
