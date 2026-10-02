"""One frozen teacher-collection pilot using the existing single-owner lab."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import signal
import sys
import time
import uuid

from palimpsest import artifacts
from palimpsest.lab import LabSupervisor
from palimpsest.storage import StorageLimits


def identity(root):
    paths = [*sorted((root / 'src/palimpsest').glob('*.py')), root / 'uv.lock', root / 'pyproject.toml']
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def collect(args):
    root, assets, output = args.repo.resolve(), args.assets.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    protocol_bytes = args.protocol.read_bytes()
    protocol = json.loads(protocol_bytes)
    (output / 'protocol.json').write_bytes(protocol_bytes)
    shutil.copyfile(__file__, output / 'collector.py')
    report = {'status': 'running', 'protocol_sha256': hashlib.sha256(protocol_bytes).hexdigest(),
              'runtime_source': identity(root), 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'frozen teacher imitation sources, no student evaluation or collection retries', 'runs': []}
    started, deadline = time.monotonic(), time.monotonic() + 480
    supervisor = None
    interrupted = []
    old = {sig: signal.signal(sig, lambda sig, frame: interrupted.append(sig)) for sig in (signal.SIGTERM, signal.SIGINT)}
    def save():
        temporary = output / 'collection.tmp'
        temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        temporary.replace(output / 'collection.json')
    def view(identifier):
        if interrupted or time.monotonic() > deadline:
            raise TimeoutError('Collection interrupted or exceeded its 480-second deadline')
        value = supervisor.describe(identifier)
        if value['status'] == 'failed':
            raise RuntimeError(str(value.get('failure')))
        return value
    def wait(identifier, predicate):
        while True:
            value = view(identifier)
            if predicate(value):
                return value
            time.sleep(.01)
    try:
        save()
        supervisor = LabSupervisor(root, assets, output / 'runs', startup_timeout=60., step_timeout=30.,
            storage_limits=StorageLimits(max_bytes=1024**3, min_free_bytes=1024**3, max_runs=16, max_snapshots=1))
        for split, seeds in protocol['scene_seeds'].items():
            for seed in seeds:
                identifier = supervisor.start({'controller': 'teacher', 'device': 'cpu', 'seed': seed,
                                               'scenario': 'reproduction', 'texture': 'checker'})
                entry = {'run_id': identifier, 'run_path': str(supervisor.path(identifier)),
                         'seed': seed, 'split': split, 'status': 'running'}
                report['runs'].append(entry); save()
                initial = wait(identifier, lambda v: v['status'] == 'ready' and v.get('state') is not None)
                state = initial['state']
                if state['total_tick'] != 0 or state['phase'] != 'paused':
                    raise ValueError('Teacher did not start at the fresh paused boundary')
                preflight = initial['storage_preflight']
                per_tick = preflight['raw_and_effective_camera_bytes_per_tick'] + preflight['neural_bytes_per_tick'] + 4096
                run = Path(entry['run_path'])
                initial_bytes = sum(p.stat().st_size for folder in ('recording', 'snapshots')
                                    for p in (run / folder).rglob('*') if p.is_file())
                estimated = initial_bytes + protocol['max_ticks_per_run'] * per_tick + 1024**2
                entry['storage_preflight'] = {'initial_bytes': initial_bytes, 'per_tick_estimate': per_tick,
                    'estimated_total_bytes': estimated, 'limit_bytes': protocol['recording_plus_snapshot_limit_bytes'],
                    'scope': 'admission estimate; actual final size is independently checked; shared writes have a 1 GiB hard cap'}
                save()
                if estimated > protocol['recording_plus_snapshot_limit_bytes']:
                    raise ValueError('Teacher estimated recording plus snapshot exceeds the frozen per-run limit')
                for tick in range(protocol['max_ticks_per_run']):
                    command_id = uuid.uuid4().hex
                    supervisor.call(identifier, 'command', {'id': command_id, 'kind': 'step',
                        'expected_state': 'paused', 'expected_episode': 0, 'expected_revision': state['revision']})
                    value = wait(identifier, lambda v: any(r['id'] == command_id and r['status'] != 'queued' for r in v['receipts']))
                    receipt = next(r for r in value['receipts'] if r['id'] == command_id)
                    if receipt['status'] != 'applied':
                        raise ValueError('Teacher step was not applied')
                    state = wait(identifier, lambda v: v['state']['total_tick'] == tick + 1)['state']
                    if state['episode'] != 0:
                        raise ValueError('Teacher collection must not reset')
                    if state['phase'] in ('terminated', 'truncated'):
                        break
                    if state['phase'] != 'paused':
                        raise ValueError('Unexpected teacher phase')
                entry.update(ticks=state['total_tick'], final_phase=state['phase'], last_outcome=state['last_outcome'])
                owner = supervisor.workers[identifier]
                closed = supervisor.close(identifier)
                entry.update(close_status=closed['status'], owner_exitcode=owner.process.exitcode,
                             owner_alive=owner.process.is_alive())
                if closed['status'] != 'closed' or owner.process.exitcode != 0 or owner.process.is_alive():
                    raise ValueError('Teacher owner did not close normally')
                run = Path(entry['run_path'])
                source_files = [p for folder in ('recording', 'snapshots') for p in (run / folder).rglob('*') if p.is_file()]
                size = sum(p.stat().st_size for p in source_files)
                if size > protocol['recording_plus_snapshot_limit_bytes']:
                    raise ValueError('Teacher recording and snapshot exceed the frozen per-run limit')
                data = artifacts._load(run)
                if sorted(data['episodes']) != [0] or len(data['episodes'][0]['ticks']) != state['total_tick']:
                    raise ValueError('Teacher recording differs from the owned episode')
                if split == 'train' and state['total_tick'] < protocol['minimum_training_ticks_per_run']:
                    raise ValueError('Frozen training scene has insufficient data; no replacement')
                entry.update(status='completed', recording_and_snapshot_bytes=size,
                    files=[{'path':str(p.relative_to(run)), 'bytes':p.stat().st_size,
                            'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(source_files)])
                save()
                print(json.dumps({'seed':seed, 'split':split, 'ticks':entry['ticks'], 'status':entry['status']}), flush=True)
        report['status'] = 'completed'
    except BaseException as error:
        report.update(status='failed', error={'type':type(error).__name__, 'message':str(error)[:2048]})
    finally:
        try:
            if supervisor is not None:
                supervisor.shutdown()
            report['supervisor_shutdown'] = 'completed'
        except BaseException as error:
            report.update(status='failed', cleanup_error={'type':type(error).__name__, 'message':str(error)[:2048]})
        report.update(runtime_source_unchanged=identity(root) == report['runtime_source'],
                      protocol_unchanged=args.protocol.read_bytes() == protocol_bytes,
                      script_unchanged=hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == report['script_sha256'],
                      wall_seconds=time.monotonic()-started)
        if not all(report[k] for k in ('runtime_source_unchanged', 'protocol_unchanged', 'script_unchanged')):
            report['status'] = 'failed'
        save()
        for sig, handler in old.items():
            signal.signal(sig, handler)
    return 0 if report['status'] == 'completed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('repo', 'assets', 'output', 'protocol'):
        parser.add_argument('--' + key, type=Path, required=True)
    sys.exit(collect(parser.parse_args()))
