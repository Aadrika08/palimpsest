"""Check snapshot continuation across fresh worker processes using the actual simulator."""

import argparse
import io
import json
import math
import os
from pathlib import Path
import sys

from palimpsest.evaluate import bounded_process


def resource_boundary(value):
    """Preserve structured quota/log failures through owner/process wrappers."""
    if isinstance(value, dict):
        if value.get('type') in ('StorageLimitError', 'LogLimit') or value.get('errno') == 28:
            return value
        for child in value.values():
            found = resource_boundary(child)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = resource_boundary(child)
            if found is not None:
                return found
    return None


def worker_budget(config):
    """Study-only shared quota; the legacy verifier has no extra quota."""
    if config.get('storage_max_bytes') is None:
        return None
    from palimpsest.storage import StorageBudget, StorageLimits
    return StorageBudget((Path(config['storage_root']),), StorageLimits(
        max_bytes=config['storage_max_bytes'], min_free_bytes=config.get('minimum_free_bytes', 0)))


def write_payload(path, payload, budget):
    if budget is not None:
        budget.check(len(payload), path=path)
    Path(path).write_bytes(payload)


def worker(config):
    import random
    import numpy as np
    import torch
    import mujoco
    from palimpsest.engine import Engine
    from palimpsest.snapshots import capture, restore, save_snapshot, read_snapshot

    output = Path(config['output'])
    budget = worker_budget(config)
    engine = Engine.open(Path(config['repo']), Path(config['assets']), output / 'recording',
                         controller=config['controller'], device=config['device'], seed=config['seed'], storage_budget=budget)
    queued = {'id': 'resume-from-snapshot', 'kind': 'run', 'expected_state': 'paused',
              'expected_episode': 0}

    def command(identifier, kind, state, payload=None):
        message = {'id': identifier, 'kind': kind, 'expected_state': state, 'expected_episode': 0}
        if payload is not None:
            message['payload'] = payload
        receipt = engine.submit(message)
        if receipt['status'] != 'queued':
            raise ValueError(f'Command rejected: {receipt}')
        engine.advance()
        result = engine.submit(message)
        if result['status'] != 'applied':
            raise ValueError(f'Command not applied: {result}')

    try:
        if config['mode'] == 'source':
            if config.get('mask_left'):
                command('mask-left', 'set_eyes', 'paused', {'left': False, 'right': True})
                if engine.policy:
                    before = engine.policy._state()
                    projected = {**engine.effective_cameras(), 'sensors': engine.observation['sensors']}
                    parity = engine.policy.act(projected, check_parity=True)['parity']
                    engine.policy._restore(before)
                    write_payload(output / 'input-parity.json', json.dumps(parity, allow_nan=False).encode(), budget)
            goal = engine.env._goal_xy.copy()
            goal[0] += .1  # Seeded goals begin with ample wall/obstacle clearance.
            command('edit-before-snapshot', 'intervene', 'paused',
                    {'kind': 'move_goal', 'xy': goal.tolist()})
            if config['controller'] == 'manual':
                command('manual-intent', 'set_action', 'paused', {'action': [1., .2]})
            command('initial-run', 'run', 'paused')
            for _ in range(config['prefix'] - 1):
                engine.advance()
            command('pause-for-snapshot', 'pause', 'running')
            engine.submit(queued)
            engine.writer.flush()
            snapshot = capture(engine.env, engine.observation, policy=engine.policy,
                               teacher=engine.teacher, application=engine.application_state())
            save_snapshot(snapshot, Path(config['snapshot']), storage_budget=budget)
        else:
            snapshot = read_snapshot(Path(config['snapshot']))
            engine.validate_application(snapshot['application'])
            observation, application = restore(snapshot, engine.env, policy=engine.policy, teacher=engine.teacher)
            engine.observation = observation
            engine.restore_application(application)
        for _ in range(config['continuation']):
            engine.advance()
        duplicate = engine.submit(queued)
        if duplicate['status'] != 'applied':
            raise ValueError(f'Restored idempotency state lost: {duplicate}')
        integration = np.empty(mujoco.mj_stateSize(engine.env.model, mujoco.mjtState.mjSTATE_INTEGRATION))
        mujoco.mj_getState(engine.env.model, engine.env.data, integration, mujoco.mjtState.mjSTATE_INTEGRATION)
        final = {'integration': integration, 'xpos': engine.env.data.xpos.copy(),
                 'geom_xpos': engine.env.data.geom_xpos.copy(),
                 'contacts': engine.env.data.contact.pos.copy()}
        for name in ('jnt_range', 'geom_rgba', 'site_pos'):
            final[name] = getattr(engine.env.model, name).copy()
        for name in ('_obstacle_xy', '_goal_xy', '_prev_xy', '_speed', '_t', '_last_action', '_stall_steps'):
            final[name] = np.asarray(getattr(engine.env, name)).copy()
        for name in ('cam_left', 'cam_right'):
            final['final_' + name] = engine.observation[name].copy()
        if engine.policy:
            final['hidden'] = engine.policy.hidden.detach().cpu().numpy().copy()
            for eye in ('left', 'right'):
                for name, value in getattr(engine.policy.agent, 'state_vision_' + eye).items():
                    final[eye + '_' + name] = value.detach().cpu().numpy().copy()
        if budget is None:
            np.savez(output / 'continuation-state.npz', **final)
        else:
            archive = io.BytesIO()
            np.savez(archive, **final)
            write_payload(output / 'continuation-state.npz', archive.getvalue(), budget)
        random_draws = {'python': random.random(), 'numpy': np.random.random(3).tolist(),
                        'environment': engine.env.np_random.random(3).tolist(),
                        'torch_cpu': torch.rand(3).tolist()}
        if config['device'] == 'cuda' and config['controller'] == 'flynn':
            random_draws['torch_cuda'] = torch.rand(3, device='cuda').cpu().tolist()
        write_payload(output / 'random-draws.json', json.dumps(random_draws, allow_nan=False).encode(), budget)
    finally:
        engine.close()


def validate_scientific_rows(rows):
    """Study finite-only policy, including source prefixes and replay outputs."""
    import numpy as np
    for row in rows:
        for name, value in row.items():
            if 'latency' in name:
                continue
            array = np.asarray(value)
            if array.dtype.kind in 'fc' and not np.isfinite(array).all():
                raise ValueError(f"Nonfinite scientific array: {name} at tick {int(row['tick'])}")


def compare_array(a, b, component, tick, errors, divergences):
    import numpy as np
    a, b = np.asarray(a), np.asarray(b)
    if a.shape != b.shape or a.dtype != b.dtype:
        raise ValueError(f'Continuation type/shape mismatch: {component}')
    if a.dtype.kind in 'fc' and (not np.isfinite(a).all() or not np.isfinite(b).all()):
        raise ValueError(f'Nonfinite scientific array: {component} at tick {tick}')
    delta = np.abs(a.astype(float) - b.astype(float))
    difference = float(delta.max()) if a.size else 0.
    if not math.isfinite(difference):
        raise ValueError(f'Nonfinite comparison difference: {component} at tick {tick}')
    errors[component] = max(errors.get(component, 0.), difference)
    equal = np.allclose(a, b, atol=1e-6, rtol=1e-6) if a.dtype.kind in 'fc' else np.array_equal(a, b)
    if not equal:
        divergences.append({'tick': tick, 'component': component, 'max_abs_error': difference,
                            'different_values': int(np.count_nonzero(delta))})


def verify(config):
    output = Path(config['output']).resolve()
    output.mkdir(parents=True, exist_ok=False)
    config['snapshot'] = str(output / 'continuation.snapshot')
    if config.get('storage_max_bytes') is not None:
        config['storage_root'] = str(output)
    env = os.environ.copy()
    env.setdefault('MUJOCO_GL', 'egl')
    env['MPLBACKEND'] = 'Agg'
    env['OMP_NUM_THREADS'] = '2'
    result = {'status': 'failed', 'controller': config['controller'], 'device': config['device'],
              'prefix_ticks': config['prefix'], 'continuation_ticks': config['continuation']}
    try:
        for mode in ('source', 'restored'):
            child = {**config, 'mode': mode, 'output': str(output / mode)}
            report = bounded_process([sys.executable, __file__, '--worker', json.dumps(child)],
                                     output / mode, config['timeout'], env, storage_budget=worker_budget(config))
            if report['status'] != 'completed':
                error_path = output / mode / 'worker-error.json'
                detail = json.loads(error_path.read_text()) if error_path.exists() else report
                result.update(worker=mode, worker_report=report, worker_error=detail)
                result['resource_boundary'] = resource_boundary(detail) or resource_boundary(report)
                raise ValueError(f'{mode} worker failed; inspect retained worker report and stderr.log')
        result = compare(output, config)
    except Exception as error:
        detail = {'type': type(error).__name__, 'message': str(error)[:4096]}
        if getattr(error, 'errno', None) is not None:
            detail['errno'] = error.errno
        result.update(status='failed', error=detail)
        result['resource_boundary'] = result.get('resource_boundary') or resource_boundary(detail)
    (output / 'verification.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps(result, indent=2, allow_nan=False))
    return result


def compare(output, config):
    import numpy as np
    from palimpsest.assets import sha256_file
    from palimpsest.records import iter_ticks

    output = Path(output)
    all_source = list(iter_ticks(output / 'source/recording'))
    restored = list(iter_ticks(output / 'restored/recording'))
    validate_scientific_rows(all_source)
    validate_scientific_rows(restored)
    source = [row for row in all_source if row['tick'] >= config['prefix']]
    if len(source) != config['continuation'] or len(source) != len(restored):
        raise ValueError(f'Wrong continuation length: {len(source)}, {len(restored)}')
    manifests = [json.loads((output / mode / 'recording/manifest.json').read_text())
                 for mode in ('source', 'restored')]
    runtime = []
    for mode, manifest in zip(('source', 'restored'), manifests):
        supervisor = json.loads((output / mode / 'supervisor.json').read_text())
        if supervisor['status'] != 'completed' or supervisor['returncode'] != 0 or manifest['status'] != 'completed':
            raise ValueError(f'{mode} recording did not complete')
        if manifest['controller'] != config['controller'] or manifest['requested_device'] != config['device']:
            raise ValueError(f'{mode} controller/device differs from requested evidence')
        events = [json.loads(line) for line in (output / mode / 'recording/events.jsonl').read_text().splitlines()]
        identity = next(event for event in events if event['kind'] == 'environment')
        runtime.append({key: identity[key] for key in ('source_sha256', 'lock_sha256', 'upstream_commit')})
    if runtime[0] != runtime[1]:
        raise ValueError('Worker source/runtime provenance differs')
    if manifests[1]['parent_run_id'] != manifests[0]['run_id'] or manifests[1]['run_id'] == manifests[0]['run_id']:
        raise ValueError('Branch run identity or ancestry differs')
    prefix = manifests[1]['parent_event_prefix']
    import hashlib
    with (output / 'source/recording/events.jsonl').open('rb') as stream:
        original_prefix = stream.read(prefix['size_bytes'])
    if (hashlib.sha256(original_prefix).hexdigest() != prefix['sha256'] or
            original_prefix.count(b'\n') != prefix['event_count']):
        raise ValueError('Source event prefix changed after snapshot')
    errors, divergences = {}, []
    for expected, actual in zip(source, restored):
        if config.get('mask_left') and (expected['cam_left'].any() or actual['cam_left'].any() or
                                       not np.array_equal(actual['eyes'], [False, True])):
            raise ValueError('Masked input or restored eye configuration differs')
        if set(expected) != set(actual):
            raise ValueError('Continuation schema mismatch')
        for key in expected:
            if 'latency' in key:
                continue
            compare_array(expected[key], actual[key], key, int(actual['tick']), errors, divergences)
    draws = [json.loads((output / mode / 'random-draws.json').read_text()) for mode in ('source', 'restored')]
    if draws[0] != draws[1]:
        raise ValueError('RNG continuation differs')
    with np.load(output / 'source/continuation-state.npz', allow_pickle=False) as expected:
        with np.load(output / 'restored/continuation-state.npz', allow_pickle=False) as actual:
            if set(expected.files) != set(actual.files):
                raise ValueError('Final state schema differs')
            for key in expected.files:
                compare_array(expected[key], actual[key], 'final_' + key, None, errors, divergences)
    result = {'schema_version': 1, 'status': 'failed' if divergences else 'passed',
              'first_divergence': divergences[0] if divergences else None, 'divergences': divergences,
              'controller': config['controller'], 'device': config['device'],
              'runtime': runtime[0],
              'fixture': 'goal edit, nonzero controller/physics state and pending run command',
              'prefix_ticks': config['prefix'], 'continuation_ticks': len(restored),
              'snapshot_sha256': sha256_file(output / 'continuation.snapshot'), 'max_abs_errors': errors,
              'source_event_prefix_unchanged': True, 'branch_identity_distinct': True,
              'random_draws_match': True, 'queued_command_idempotency': True, 'finite_scientific_arrays': True,
              'atol': 1e-6, 'rtol': 1e-6, 'scope': 'Fresh-process simulation continuation on this numeric/rendering regime'}
    result['mask_left'] = bool(config.get('mask_left'))
    if result['mask_left'] and config['controller'] == 'flynn':
        result['masked_input_parity'] = json.loads((output / 'source/input-parity.json').read_text())
        if not result['masked_input_parity'].get('ok'):
            raise ValueError('Masked upstream preprocessing parity failed')
    (output / 'verification.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        config = json.loads(sys.argv[2])
        try:
            worker(config)
        except Exception as error:
            detail = {'type': type(error).__name__, 'message': str(error)[:4096]}
            if getattr(error, 'errno', None) is not None:
                detail['errno'] = error.errno
            (Path(config['output']) / 'worker-error.json').write_text(json.dumps(detail, allow_nan=False) + '\n')
            raise
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
        parser.add_argument('--assets', type=Path, required=True)
        parser.add_argument('--controller', choices=('manual', 'teacher', 'flynn'), default='manual')
        parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
        parser.add_argument('--seed', type=int, default=0)
        parser.add_argument('--prefix', type=int, default=8)
        parser.add_argument('--continuation', type=int, default=12)
        parser.add_argument('--timeout', type=int, default=180)
        parser.add_argument('--storage-max-bytes', type=int, help='optional shared source/restored payload quota')
        parser.add_argument('--minimum-free-bytes', type=int, default=0)
        parser.add_argument('--mask-left', action='store_true', help='verify masked preprocessing and continuation')
        parser.add_argument('--output', type=Path, required=True)
        args = parser.parse_args()
        if not 1 <= args.prefix <= 100 or not 1 <= args.continuation <= 100 or not 1 <= args.timeout <= 3600:
            parser.error('prefix/continuation must be 1–100 and timeout 1–3600')
        result = verify({key: str(value.resolve()) if isinstance(value, Path) else value for key, value in vars(args).items()})
        sys.exit(0 if result['status'] == 'passed' else 1)
