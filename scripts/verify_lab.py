"""Bounded actual-owner gate: masked inputs, continuation, replay and exports."""

import argparse
import hashlib
import json
from pathlib import Path
import time

from palimpsest.artifacts import compare_runs, export_run, playback
from palimpsest.lab import LabSupervisor
from palimpsest.records import iter_ticks
from verify_execution import compare_array


def verify(args):
    root, output = args.repo.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    supervisor = LabSupervisor(root, args.assets.resolve(), output / 'runs', startup_timeout=180.)
    report = {'version': 1, 'status': 'running', 'controller': args.controller,
              'device': 'cpu', 'prefix_ticks': 4, 'continuation_ticks': 4}
    started = time.monotonic()

    def wait(identifier, predicate):
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            view = supervisor.describe(identifier)
            if view['status'] == 'failed':
                raise ValueError(f'Owner failed: {view.get("failure") or view.get("replay")}')
            if predicate(view):
                return view
            time.sleep(.02)
        raise TimeoutError('Owner did not reach the requested boundary within 240 seconds')

    def ready(identifier):
        return wait(identifier, lambda v: v['status'] == 'ready' and v['sample'] is not None)

    def command(identifier, name, kind, payload=None):
        state = supervisor.describe(identifier)['state']
        supervisor.call(identifier, 'command', {
            'id': name, 'kind': kind, 'expected_state': state['phase'],
            'expected_episode': state['episode'], 'expected_revision': state['revision'],
            'payload': payload or {}})
        view = wait(identifier, lambda v: any(r['id'] == name and r['status'] != 'queued' for r in v['receipts']))
        receipt = next(r for r in view['receipts'] if r['id'] == name)
        if receipt['status'] != 'applied':
            raise ValueError(f'Command not applied: {receipt}')
        return view

    try:
        source = supervisor.start(dict(controller=args.controller, device='cpu', seed=0,
                                       scenario='vision-ablation', texture='checker'))
        report['source_run_id'] = source
        view = ready(source)
        goal = view['sample']['world']['goal'][:2]
        goal[0] += .1
        supervisor.call(source, 'preview', {'payload': {'kind': 'move_goal', 'xy': goal},
                                          'expected_revision': view['state']['revision']})
        command(source, 'edit', 'intervene', {'kind': 'move_goal', 'xy': goal})
        command(source, 'mask', 'set_eyes', {'left': False, 'right': True})
        if args.controller == 'manual':
            command(source, 'intent', 'set_action', {'action': [1., .1]})
        for tick in range(4):
            command(source, f'prefix-{tick}', 'step')
        view = supervisor.describe(source)
        snapshot_id = supervisor.call(source, 'snapshot', {'expected_revision': view['state']['revision']})['snapshot_id']
        snapshot_path, item = supervisor.snapshot(source, snapshot_id)
        report.update(snapshot_id=snapshot_id, snapshot_sha256=item['sha256'])
        for tick in range(4):
            command(source, f'continuation-{tick}', 'step')
        supervisor.close(source)
        source_path = supervisor.path(source)

        branch = supervisor.start({**item['config'], 'snapshot_path': str(snapshot_path),
            'snapshot_sha256': item['sha256'], 'snapshot_id': snapshot_id,
            'source_run_path': str(source_path), 'replace_controller': False})
        report['branch_run_id'] = branch
        ready(branch)
        for tick in range(4):
            command(branch, f'continuation-{tick}', 'step')
        supervisor.close(branch)
        branch_path = supervisor.path(branch)
        expected = [row for row in iter_ticks(source_path / 'recording') if int(row['tick']) >= 4]
        actual = list(iter_ticks(branch_path / 'recording'))
        if len(expected) != 4 or len(actual) != 4:
            raise ValueError('Wrong recorded continuation length')
        errors, divergences = {}, []
        for left, right in zip(expected, actual):
            if set(left) != set(right):
                raise ValueError('Continuation schema differs')
            for name in left:
                if 'latency' not in name:
                    compare_array(left[name], right[name], name, int(right['tick']), errors, divergences)
            if right['cam_left'].any() or right['eyes'].tolist() != [False, True]:
                raise ValueError('Actual masked inputs did not survive the branch')
        report['continuation'] = {'status': 'diverged' if divergences else 'passed',
                                  'max_abs_errors': errors, 'divergences': divergences}
        if divergences:
            raise ValueError('Actual owner continuation diverged')
        report['playback'] = {'mode': playback(branch_path, tick=4)['mode'], 'first_tick': 4}
        report['comparison'] = compare_runs(source_path, branch_path)
        interrupted = supervisor.start({**item['config'], 'snapshot_path': str(snapshot_path),
            'snapshot_sha256': item['sha256'], 'snapshot_id': snapshot_id,
            'source_run_path': str(source_path), 'replace_controller': False})
        view = ready(interrupted)
        x, y, _ = view['sample']['world']['obstacles'][0]
        relocation = None
        for dx, dy in ((.3, 0), (-.3, 0), (0, .3), (0, -.3)):
            candidate = {'kind': 'move_obstacle', 'index': 0, 'xy': [x + dx, y + dy]}
            try:
                supervisor.call(interrupted, 'preview', {'payload': candidate,
                                                       'expected_revision': view['state']['revision']})
            except RuntimeError:
                continue
            relocation = candidate
            break
        if relocation is None:
            raise ValueError('No validated nearby obstacle relocation')
        command(interrupted, 'start-travel', 'run')
        view = command(interrupted, 'live-obstacle-edit', 'intervene', relocation)
        receipt = next(r for r in view['receipts'] if r['id'] == 'live-obstacle-edit')
        command(interrupted, 'pause-after-edit', 'pause')
        supervisor.close(interrupted)
        report['live_interruption'] = {'run_id': interrupted, 'command': relocation, 'receipt': receipt,
            'comparison': compare_runs(branch_path, supervisor.path(interrupted)),
            'scope': 'Exploratory world intervention; no required direction or size of behavioral effect'}
        report['replays'] = {}
        for mode in ('actions', 'policy'):
            identifier = supervisor.start({'job': 'replay', 'source_run_path': str(source_path), 'replay_mode': mode})
            view = wait(identifier, lambda v: v['status'] == 'closed')
            supervisor.close(identifier)  # Reap before loading the next full model.
            result = view['replay']
            report['replays'][mode] = {'run_id': identifier, 'report': result}
            if result['status'] != 'passed':
                raise ValueError(f'{mode} replay did not agree: {result}')
        report['exports'] = {}
        for kind, suffix in (('svg', 'svg'), ('png', 'png'), ('bundle', 'zip')):
            path = export_run(branch_path, output / ('route.' + suffix), kind)
            report['exports'][kind] = {'path': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                       'size_bytes': path.stat().st_size}
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)})
    finally:
        supervisor.shutdown()
        report['wall_seconds'] = time.monotonic() - started
        (output / 'verification.json').write_text(json.dumps(report, allow_nan=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--controller', choices=('manual', 'teacher', 'flynn'), default='manual')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = verify(args)
    print(json.dumps({'status': result['status'], 'output': str(args.output), 'error': result.get('error')}, indent=2))
    raise SystemExit(0 if result['status'] == 'passed' else 1)
