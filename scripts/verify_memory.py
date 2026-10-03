"""Actual owner/API U-only gate; authored rules, not a learned transfer result."""

import argparse
import hashlib
import json
from pathlib import Path
import time

from fastapi.testclient import TestClient

from palimpsest.artifacts import compare_runs, playback
from palimpsest.lab import create_app
from palimpsest.memory import artifact
from palimpsest.records import iter_ticks
from palimpsest.snapshots import invariant_hashes, read_snapshot
from verify_endurance import source_identity, write_json
from verify_execution import compare_array


def verify(args):
    root, output = args.repo.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'version': 1, 'status': 'running', 'controller': args.controller,
        'scope': 'Actual CPU owner, declared symbolic memory, sham and authored U-only branches',
        'limitations': ['No learned transfer or task-success qualification', 'No CUDA or physical claim'],
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'runtime_source': source_identity(root), 'branches': {}, 'replays': {}, 'closes': []}
    started = time.monotonic()
    app = None
    try:
        app = create_app(root, args.assets.resolve(), output / 'runs')
        supervisor = app.state.lab
        with TestClient(app, base_url='http://127.0.0.1:8765') as client:
            headers = {'X-Palimpsest-Session': client.get('/api/v1/session').json()['token'],
                       'Origin': 'http://127.0.0.1:8765'}
            def post(path, value):
                response = client.post('/api/v1' + path, json=value, headers=headers)
                if response.status_code not in (200, 202):
                    raise ValueError(f'{path}: HTTP {response.status_code}: {response.text[:2048]}')
                return response.json()
            def wait(identifier, predicate):
                deadline = time.monotonic() + 240.
                while time.monotonic() < deadline:
                    view = supervisor.describe(identifier)
                    if view['status'] == 'failed':
                        raise RuntimeError('Owner failed: ' + json.dumps(view.get('failure', {}))[:2048])
                    if predicate(view):
                        return view
                    time.sleep(.02)
                raise TimeoutError('Owner boundary not reached within 240 seconds')
            def ready(identifier):
                return wait(identifier, lambda v: v['status'] == 'ready' and v.get('sample') is not None)
            def step(identifier, tick):
                state = supervisor.describe(identifier)['state']
                name = f'step-{tick}'
                post(f'/runs/{identifier}/commands', {'id': name, 'kind': 'step',
                    'expected_state': 'paused', 'expected_episode': state['episode'],
                    'expected_revision': state['revision']})
                view = wait(identifier, lambda v: any(r['id'] == name and r['status'] != 'queued' for r in v['receipts']))
                receipt = next(r for r in view['receipts'] if r['id'] == name)
                if receipt['status'] != 'applied' or view['state']['total_tick'] != tick + 1:
                    raise ValueError('Step did not apply at the expected boundary')
            def close(identifier):
                result = post(f'/runs/{identifier}/close', {})
                owner = supervisor.workers[identifier]
                report['closes'].append({'run_id': identifier, 'status': result['status'],
                    'exitcode': owner.process.exitcode, 'alive': owner.process.is_alive()})
                if result['status'] != 'closed' or owner.process.is_alive() or owner.process.exitcode != 0:
                    raise ValueError('Owner did not close and exit cleanly')
            source = post('/runs', {'controller': args.controller, 'device': 'cpu', 'seed': 19,
                'scenario': 'memory-passages', 'texture': 'checker'})['run_id']
            report['source_run_id'] = source
            ready(source)
            for tick in range(8):
                step(source, tick)
            view = supervisor.describe(source)
            snapshot_id = post(f'/runs/{source}/snapshot', {'expected_revision': view['state']['revision']})['snapshot_id']
            path, registration = supervisor.snapshot(source, snapshot_id)
            original = read_snapshot(path)
            expected = invariant_hashes(original)
            report.update(snapshot_id=snapshot_id, snapshot_sha256=registration['sha256'], invariant_hashes=expected)
            for tick in range(8, 12):
                step(source, tick)
            close(source)
            source_path = supervisor.path(source)
            frozen = {str(p.relative_to(source_path)): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in source_path.rglob('*') if p.is_file()}
            for label, u in (('sham', original['application']['memory']['u']),
                             ('local', artifact('local_cue')), ('paired', artifact('paired_cue'))):
                identifier = post('/memory/branches', {'source_run_id': source, 'snapshot_id': snapshot_id, 'u': u})['run_id']
                view = ready(identifier)
                branch_snapshot, _ = supervisor.snapshot(identifier, view['initial_snapshot_id'])
                restored = read_snapshot(branch_snapshot)
                if invariant_hashes(restored) != expected or restored['application']['memory']['u'] != u:
                    raise ValueError('Published branch violates U-only invariants')
                for tick in range(8, 12):
                    step(identifier, tick)
                close(identifier)
                branch_path = supervisor.path(identifier)
                viewed = playback(branch_path, episode=0, tick=10)
                active = viewed['memory']['active']
                expected_target = {'sham': None, 'local': 'fact-passage-a', 'paired': 'fact-passage-b'}[label]
                if (None if active is None else active['fact_id']) != expected_target:
                    raise ValueError('Authored U did not produce the expected declared-cue inspection target')
                report['branches'][label] = {'run_id': identifier, 'invariants_equal': True,
                    'tick10_memory': viewed['memory'], 'comparison': compare_runs(source_path, branch_path)['differences']}
                if label == 'sham':
                    left = [row for row in iter_ticks(source_path / 'recording') if int(row['tick']) >= 8]
                    right = list(iter_ticks(branch_path / 'recording'))
                    if len(left) != 4 or len(right) != 4:
                        raise ValueError('Wrong sham continuation length')
                    errors, divergences = {}, []
                    for a, b in zip(left, right):
                        if set(a) != set(b):
                            raise ValueError('Sham continuation fields differ')
                        for name in a:
                            if 'latency' not in name:
                                compare_array(a[name], b[name], name, int(b['tick']), errors, divergences)
                    report['sham'] = {'max_abs_errors': errors, 'divergences': divergences,
                                      'float_atol': 1e-6, 'float_rtol': 1e-6, 'other_fields_exact': True}
                    if divergences:
                        raise ValueError('Sham continuation diverged')
            for mode in ('actions', 'policy'):
                branch = report['branches']['local']['run_id']
                identifier = supervisor.start({'job': 'replay', 'source_run_path': str(supervisor.path(branch)), 'replay_mode': mode})
                view = wait(identifier, lambda v: v['status'] == 'closed')
                close(identifier)
                report['replays'][mode] = {'run_id': identifier, 'report': view['replay']}
                if view['replay']['status'] != 'passed':
                    raise ValueError(f'{mode} memory replay failed')
            if frozen != {str(p.relative_to(source_path)): hashlib.sha256(p.read_bytes()).hexdigest()
                          for p in source_path.rglob('*') if p.is_file()}:
                raise ValueError('Immutable source changed')
            report['source_unchanged'] = True
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:4096]})
    finally:
        if app is not None:
            try:
                app.state.lab.shutdown()
                report['supervisor_shutdown_completed'] = True
            except Exception as error:
                report.update(status='failed', cleanup_error={'type': type(error).__name__, 'message': str(error)[:4096]})
        report['runtime_source_at_end'] = source_identity(root)
        report['runtime_source_unchanged'] = report['runtime_source'] == report['runtime_source_at_end']
        if not report['runtime_source_unchanged']:
            report['status'] = 'failed'
        report['wall_seconds'] = time.monotonic() - started
        write_json(output / 'report.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--controller', choices=('manual', 'flynn'), default='manual')
    args = parser.parse_args()
    result = verify(args)
    print(json.dumps({'status': result['status'], 'error': result.get('error'), 'output': str(args.output)}))
    raise SystemExit(0 if result['status'] == 'passed' else 1)
