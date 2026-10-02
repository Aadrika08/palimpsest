"""Two fresh owners, zero physics steps: fixed thin-puck construction only.

Requires a reviewed runtime slot and retained outer TERM180/+15/KILL200 bound.
No Engine, policy, training, action, automatic retry or mechanics gate is run.
"""
import argparse
from dataclasses import asdict
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

from verify_afterimage import digest, write_json, process_identity, cleanup_check
from puck_construction_compare import compare_native_data

PROTOCOL_FILE = 'docs/plans/m6-puck-construction-v4.json'
PROTOCOL_SHA256 = 'c11d31fb0892c036bcbbe908ee1463859b49392958de290a2ef3b31fa4d6694d'


def protocol(root):
    path = root / PROTOCOL_FILE
    raw = path.read_bytes()
    if len(raw) > 16384 or hashlib.sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('Construction protocol byte/hash mismatch')
    result = json.loads(raw)
    if digest(root / 'src/palimpsest/puck_profile.py') != result['puck_module_sha256']:
        raise ValueError('Construction module differs from reviewed pin')
    return result


def sources(root):
    files = {*sorted((root / 'src/palimpsest').glob('*.py')),
             *sorted((root / 'upstream/fly-gym').rglob('*.py')),
             root / 'upstream/fly-gym/environment/mujoco_model_random_obstacles.xml',
             root / 'scripts/verify_afterimage.py', Path(__file__).resolve(),
             root / 'scripts/puck_construction_compare.py',
             root / 'tests/test_puck_profile.py', root / 'tests/test_puck_construction.py', root / PROTOCOL_FILE,
             root / 'docs/plans/m6-puck-pushing-protocol.json', root / 'pyproject.toml', root / 'uv.lock'}
    if len(files) > 1024 or any(path.stat().st_size > 2*1024**2 for path in files):
        raise ValueError('Construction source inventory exceeds bound')
    return {str(path.relative_to(root)): digest(path) for path in sorted(files)}


def store(path, raw, budget, cap):
    if type(raw) is not bytes or len(raw) > cap:
        raise ValueError('Construction payload exceeds byte/type bound')
    budget.check(len(raw), path=path)
    with path.open('xb') as stream:
        stream.write(raw)
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def owner(config):
    """One process owns all native resources; parent checks exact process exit."""
    from palimpsest.storage import StorageBudget, StorageLimits
    root, output = Path(config['repo']), Path(config['output'])
    spec = protocol(root)
    limits = spec['limits']
    budget = StorageBudget((Path(config['gate_output']),), StorageLimits(**config['storage_limits']),
                           headroom_bytes=limits['headroom_bytes'])
    write_json(output / 'process.json', process_identity(), budget)
    result = {'status': 'running', 'qualification_claims': [], 'cleanup': [], 'finalization_errors': []}
    env, old_renderer = None, None
    started = time.monotonic()
    try:
        if sources(root) != config['sources']:
            raise ValueError('Source changed before owner admission')
        import numpy as np
        import mujoco as mj
        from palimpsest.flynn import import_upstream
        from palimpsest import puck_profile
        from palimpsest.snapshots import state_digest
        versions = {'python': platform.python_version(), 'numpy': np.__version__,
                    'mujoco': mj.__version__, 'backend': os.environ.get('MUJOCO_GL')}
        if versions != spec['runtime'] or 'torch' in sys.modules:
            raise ValueError('Unreviewed runtime or unexpected Torch import')
        result['runtime'] = versions
        cls = import_upstream(root, 'environment.mujoco_two_cam_env_random_obstacles').MuJoCoTwoCamEnv
        env = cls(**spec['environment_kwargs'])
        old_renderer = env.renderer
        result['profile_identity'] = puck_profile.install_fixed_model(env, root)
        result['task_state'] = puck_profile.authored_reset(env, root, spec['layout_seed'],
                                                         spec['layout_split'], spec['episode_id'])
        if old_renderer._gl_context is not None or old_renderer._mjr_context is not None:
            raise ValueError('Retired baseline renderer still owns a context')
        # These state/containers are captured only after authored mj_forward.
        # Renderer scene updates must leave the native owner at this same time.
        values = {name: getattr(env.data, name).copy() for name in
                  ('qpos', 'qvel', 'ctrl', 'qfrc_applied', 'xfrc_applied')}
        if (env.data.time != 0. or env._t != 0 or any(np.any(values[key]) for key in
                ('qvel', 'ctrl', 'qfrc_applied', 'xfrc_applied')) or mj.get_mjcb_control() is not None):
            raise ValueError('Construction owner advanced time or applied control/force')
        if any(not np.isfinite(value).all() for value in values.values()):
            raise ValueError('Nonfinite construction state')
        result['qpos_qvel_ctrl_forces_sha256'] = state_digest(values)
        result['time_s'], result['control_ticks'], result['physics_steps'] = 0., 0, 0
        result['full_native_model'] = store(output / 'model.native', env.model.__getstate__(), budget,
                                            limits['native_model_bytes'])
        result['full_native_data'] = store(output / 'data.native', env.data.__getstate__(), budget,
                                           limits['native_data_bytes'])
        result['cameras'] = {}
        for camera in spec['retained_cameras_per_owner']:
            env.renderer.update_scene(env.data, camera=camera)
            frame = env.renderer.render()
            if frame.dtype != np.uint8 or frame.shape != (128, 128, 3):
                raise ValueError('Wrong declared RGB camera shape/dtype')
            payload = io.BytesIO()
            np.save(payload, frame, allow_pickle=False)
            result['cameras'][camera] = store(output / (camera + '.npy'), payload.getvalue(), budget,
                                              limits['camera_file_bytes'])
        if (env.data.time != 0. or env._t != 0 or
                state_digest({name: getattr(env.data, name) for name in values}) != result['qpos_qvel_ctrl_forces_sha256'] or
                hashlib.sha256(env.data.__getstate__()).hexdigest() != result['full_native_data']['sha256']):
            raise ValueError('Explicit rendering mutated native construction state')
        if 'torch' in sys.modules:
            raise ValueError('Construction unexpectedly imported a model runtime')
        result['status'] = 'passed'
    except Exception as error:
        result.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:4096]})
    finally:
        # Retain old/current handles separately even if installation raised after
        # committing the new owner and old-renderer close was the failing action.
        seen = set()
        for label, renderer in [('retired', old_renderer), ('current', getattr(env, 'renderer', None))]:
            if renderer is None or id(renderer) in seen:
                continue
            seen.add(id(renderer))
            receipt = {'resource': label, 'closed': False}
            try:
                if renderer._gl_context is not None or renderer._mjr_context is not None:
                    renderer.close()
                receipt['closed'] = renderer._gl_context is None and renderer._mjr_context is None
                if not receipt['closed']:
                    raise RuntimeError('Renderer contexts remain live')
            except Exception as error:
                receipt['error'] = str(error)[:1024]
                result['finalization_errors'].append(label + ': ' + str(error)[:1024])
            result['cleanup'].append(receipt)
        if env is not None:
            try:
                env.close()
                if env.window is not None or env._view_ctx is not None:
                    raise RuntimeError('Unexpected native window/view context')
            except Exception as error:
                result['finalization_errors'].append('env: ' + str(error)[:1024])
        try:
            result['sources_unchanged'] = sources(root) == config['sources']
            if not result['sources_unchanged']:
                raise ValueError('Sources changed during construction')
        except Exception as error:
            result['finalization_errors'].append('sources: ' + str(error)[:1024])
        result['elapsed_seconds'] = time.monotonic() - started
        if result['finalization_errors']:
            result['status'] = 'failed'
        write_json(output / 'result.json', result, budget)
    return 0 if result['status'] == 'passed' else 1


def main(args):
    from palimpsest.evaluate import bounded_process
    from palimpsest.storage import StorageBudget, StorageLimits, _safe_path
    root, output = args.repo.resolve(), _safe_path(args.output)
    if Path(__file__).resolve() != root / 'scripts/verify_puck_construction.py':
        raise ValueError('--repo must select this script checkout')
    if output.exists():
        raise FileExistsError('Construction gate output must be new')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True, timeout=5).strip()
    if commit != args.expected_commit:
        raise ValueError('Source HEAD differs from reviewed frozen commit')
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD'], cwd=root, check=True, capture_output=True, timeout=5)
    upstream = root / 'upstream/fly-gym'
    spec = protocol(root)
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=upstream, text=True, timeout=5).strip() != spec['upstream_commit']:
        raise ValueError('Upstream revision differs from frozen construction source')
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD'], cwd=upstream, check=True, capture_output=True, timeout=5)
    limits = spec['limits']
    storage = StorageLimits(max_bytes=limits['storage_bytes'], min_free_bytes=limits['min_free_bytes'],
                            max_runs=2, max_exports=4, max_snapshots=4)
    budget = StorageBudget((output,), storage, headroom_bytes=limits['headroom_bytes'])
    report = {'status': 'running', 'commit': commit, 'protocol': spec,
              'protocol_sha256': PROTOCOL_SHA256, 'script_sha256': digest(__file__),
              'owners': [{'id': name, 'status': 'not_started'} for name in spec['owners']],
              'qualification_claims': [], 'finalization_errors': []}
    started = time.monotonic()
    frozen = sources(root)
    report['sources'] = frozen
    with budget.lock():
        budget.check(48 * 1024**2, path=output)
        write_json(output / 'report.json', report, budget)
        try:
            child_env = {**os.environ, 'PYTHONPATH': str(root / 'src'), 'MUJOCO_GL': 'egl',
                         'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}
            for row in report['owners']:
                if time.monotonic() - started + limits['per_owner_seconds'] > limits['internal_seconds']:
                    raise TimeoutError('Insufficient total budget to admit next owner')
                child_output = output / row['id']
                config = {'repo': str(root), 'output': str(child_output), 'gate_output': str(output),
                          'sources': frozen, 'storage_limits': asdict(storage)}
                row.update(status='running', output=str(child_output))
                write_json(output / 'report.json', report, budget)
                row['supervisor'] = bounded_process([sys.executable, str(Path(__file__).resolve()), '--child',
                    json.dumps(config, separators=(',', ':'))], child_output, limits['per_owner_seconds'], child_env,
                    storage_budget=budget, log_max_bytes=limits['log_bytes_each'])
                row['status'] = 'failed'
                if (child_output / 'process.json').is_file():
                    row['process'] = json.loads((child_output / 'process.json').read_text())
                    row['cleanup'] = cleanup_check(row['process'])
                if (child_output / 'result.json').is_file():
                    row['result'] = json.loads((child_output / 'result.json').read_text())
                    row['result_sha256'] = digest(child_output / 'result.json')
                if (row['supervisor']['status'] != 'completed' or not row.get('cleanup', {}).get('passed') or
                        row.get('result', {}).get('status') != 'passed'):
                    raise RuntimeError(row['id'] + ': failed construction/supervision/cleanup')
                row['status'] = 'passed'
                write_json(output / 'report.json', report, budget)
            left, right = (row['result'] for row in report['owners'])
            for key in ('profile_identity', 'full_native_model',
                        'qpos_qvel_ctrl_forces_sha256', 'cameras', 'task_state'):
                if left[key] != right[key]:
                    raise ValueError('Fresh-owner equality failed: ' + key)
            contract = spec['native_data_comparison']
            raw_data = []
            for row in report['owners']:
                model_path = Path(row['output']) / 'model.native'
                if (model_path.stat().st_size != contract['model_bytes'] or
                        digest(model_path) != contract['model_sha256'] or
                        row['result']['full_native_model'] != {
                            'bytes': contract['model_bytes'], 'sha256': contract['model_sha256']}):
                    raise ValueError('Retained native model differs from v4 pin')
                with (Path(row['output']) / 'data.native').open('rb') as stream:
                    raw = stream.read(contract['data_bytes'] + 1)
                if (len(raw) != contract['data_bytes'] or row['result']['full_native_data'] != {
                        'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}):
                    raise ValueError('Retained native data differs from owner receipt')
                raw_data.append(raw)
            report['native_data_comparison'] = compare_native_data(*raw_data, contract)
            report['status'] = 'passed'
        except Exception as error:
            report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:4096]})
        finally:
            try:
                report['sources_unchanged'] = sources(root) == frozen
                if not report['sources_unchanged']:
                    raise ValueError('Source changed during construction gate')
            except Exception as error:
                report['finalization_errors'].append('sources: ' + str(error)[:1024])
            try:
                report['retained_inventory'] = {str(path.relative_to(output)): {'sha256': digest(path), 'bytes': path.stat().st_size}
                    for path in sorted(output.rglob('*')) if path.is_file() and path.name != '.palimpsest-storage.lock'
                    and path != output / 'report.json'}
                report['storage'] = budget.usage()
            except Exception as error:
                report['finalization_errors'].append('inventory: ' + str(error)[:1024])
            if report['finalization_errors']:
                report['status'] = 'failed'
            report['elapsed_seconds'] = time.monotonic() - started
            write_json(output / 'report.json', report, budget)
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == '--child':
        raise SystemExit(owner(json.loads(sys.argv[2])))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--expected-commit', required=True)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
