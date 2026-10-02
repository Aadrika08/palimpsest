"""One fixed eight-frame Afterimage mechanism gate; no visitor or biology claim.

Run only in an approved runtime slot, under an external 330s process-group bound:
  PYTHONPATH=src PYTHON scripts/verify_afterimage.py --assets ASSETS --output NEWDIR
No training, simulator, camera, second variant, tuning, retries or extra frames.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

TIMES = [0., .04, .08, .12, .20, .28, .36, .50]
PROTOCOL = {'id': 'afterimage-geometric-mechanism-v1', 'frames': 8, 'controller': 'male-original',
            'seed': 0, 'source_times_seconds': TIMES, 'model_dt_seconds': .02,
            'stimulus': 'nonhuman authored geometric RGB; no camera or external media',
            'reference': 'fresh fixed CPU model, reset once, one carried-state forward per frame',
            'atol': 1e-6, 'rtol': 1e-6, 'recorder_timeout_seconds': 120,
            'reference_timeout_seconds': 120, 'render_timeout_seconds': 15,
            'total_seconds': 300, 'outer_seconds': 330, 'storage_bytes': 256 * 1024**2,
            'min_free_bytes': 1024**3,
            'claim': 'actual model mechanism on authored verification fixture, not perception or exhibition'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value, budget):
    payload = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    if len(payload) > 4 * 1024**2:
        raise ValueError('verification JSON exceeds 4 MiB')
    budget.check(len(payload), path=path)
    temporary = path.with_suffix('.tmp')
    with temporary.open('xb') as stream:
        stream.write(payload)
    temporary.replace(path)


def sources(root):
    paths = [*sorted((root / 'src/palimpsest').glob('*.py')), root / 'pyproject.toml', root / 'uv.lock',
             Path(__file__).resolve(), root / 'upstream/fly-gym/models/connectome_rnn_model.py',
             root / 'data/manifests/male-reduced-policy-v1.json', root / 'data/manifests/malecns-reduced-neighborhood-v1.json']
    return {str(path.relative_to(root)): digest(path) for path in paths}


def frames():
    import numpy as np
    result = np.empty((8, 128, 128, 3), dtype=np.uint8)
    result[:] = [12, 16, 24]
    for index in range(8):
        x = 8 + 12 * index
        result[index, 40:88, x:x + 20] = [224, 80 + 16 * index, 32]
        result[index, 16:32, 16 + 8 * index:20 + 8 * index] = [32, 176, 224]
    return result


def process_identity():
    pid = os.getpid()
    fields = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
    return {'pid': pid, 'start_ticks': int(fields[19]), 'process_group': os.getpgrp()}


def cleanup_check(identity):
    path = Path(f'/proc/{identity["pid"]}/stat')
    try:
        fields = path.read_text().rsplit(') ', 1)[1].split()
        same_process = int(fields[19]) == identity['start_ticks']
    except FileNotFoundError:
        same_process = False
    try:
        os.killpg(identity['process_group'], 0)
        group_absent = False
    except ProcessLookupError:
        group_absent = True
    return {'same_process_alive': same_process, 'process_group_absent': group_absent,
            'passed': not same_process and group_absent}


def reference(config, budget):
    """Compare the one recorded sequence against direct model.forward, not act."""
    import numpy as np
    from palimpsest import afterimage
    from palimpsest.male_model import features
    from palimpsest.male_policy import load_pinned_policy, resolve_profile
    from palimpsest.records import iter_ticks
    source = Path(config['run'])
    manifest, rows, paths, fingerprints = afterimage._load_recording(source)
    if (manifest['policy_identity'] != config['identity'] or manifest['source_code_sha256'] != config['afterimage_sources'] or
            manifest['input_frames'] != 8 or manifest['stimulus'] != config['stimulus']):
        raise ValueError('recorded provenance differs from admitted inputs/model/source')
    policy = load_pinned_policy(config['repo'], config['assets'], 'male-original', 0, config['identity'])
    import torch
    hidden = policy.agent.reset()
    if hidden.shape != (1, 138) or hidden.dtype != torch.float32 or not torch.equal(hidden, torch.zeros_like(hidden)):
        raise ValueError('reference initial hidden state is not the exact zero reset')
    authored = frames()
    maxima = {key: 0. for key in ('encoded_input', 'raw_output', 'action')}
    checked = []
    iterator = iter_ticks(source / 'recording')
    try:
        with torch.inference_mode():
            for index, row in enumerate(iterator):
                if index >= 8:
                    raise ValueError('unexpected ninth recorded frame')
                for eye in ('cam_left', 'cam_right'):
                    np.testing.assert_array_equal(row[eye], authored[index], err_msg='exact authored RGB differs')
                np.testing.assert_array_equal(row['sensors'], np.array([0., 0., 1., 0.], np.float32))
                if float(row['source_timestamp_seconds']) != TIMES[index] or float(row['model_time_seconds']) != (index + 1) * .02:
                    raise ValueError('source/model timestamp alignment differs')
                value = features({'cam_left': authored[index], 'cam_right': authored[index],
                                  'sensors': np.array([0., 0., 1., 0.], np.float64)})
                hidden, actions, diagnostics = policy.agent(torch.from_numpy(value).reshape(1, 1, 388), hidden, diagnostics=True)
                if hidden.shape != (1, 138) or hidden.dtype != torch.float32 or not torch.isfinite(hidden).all():
                    raise ValueError('invalid carried reference hidden state')
                actual = {'action': actions, **diagnostics}
                for key in maxima:
                    tensor = actual[key]
                    if tensor.dtype != torch.float32 or tensor.device.type != 'cpu' or not torch.isfinite(tensor).all():
                        raise ValueError('nonfinite or unsupported reference diagnostic: ' + key)
                    expected = tensor.reshape(-1).numpy()
                    np.testing.assert_allclose(row[key], expected, atol=1e-6, rtol=1e-6, err_msg=f'frame {index}: {key}')
                    maxima[key] = max(maxima[key], float(np.max(np.abs(row[key].astype(np.float64) - expected))))
                checked.append({'frame': index, 'source_timestamp_seconds': TIMES[index],
                                'model_time_seconds': float(row['model_time_seconds']),
                                'features_sha256': hashlib.sha256(value.tobytes()).hexdigest(),
                                'carried_hidden_sha256': hashlib.sha256(hidden.numpy().tobytes()).hexdigest()})
    finally:
        iterator.close()
    if len(checked) != 8 or afterimage.artifacts._fingerprint(paths) != fingerprints:
        raise ValueError('recorded source changed or not exactly eight rows')
    resolve_profile(config['repo'], config['assets'], 'male-original', config['identity'])
    return {'status': 'passed', 'frames_compared': 8, 'reference_forward_calls': 8, 'reference_sequence_resets': 1,
            'max_absolute_differences': maxima, 'rows': checked, 'reset_and_carry_scope': 'one zero initial reset; direct carried hidden state at all eight forward calls',
            'numpy_version': np.__version__, 'torch_version': torch.__version__, 'mujoco_imported': 'mujoco' in sys.modules}


def child(mode, config):
    from palimpsest.storage import StorageBudget, StorageLimits
    storage = config['storage']
    budget = StorageBudget(storage['roots'], StorageLimits(**storage['limits']), headroom_bytes=storage['headroom_bytes'])
    stage = Path(config['stage'])
    write_json(stage / 'process.json', process_identity(), budget)
    if sources(Path(config['repo'])) != config['sources']:
        raise ValueError('frozen sources changed before child stage')
    if mode == 'record':
        from palimpsest.afterimage import worker
        code = worker(config['record_config'])
        result = {'status': 'passed' if code == 0 else 'failed', 'frames': 8}
    elif mode == 'reference':
        result = reference(config, budget)
    else:
        from palimpsest.afterimage import render
        output = render(config['run'], stage / 'portrait.svg', storage_budget=budget)
        if 'torch' in sys.modules or 'mujoco' in sys.modules:
            raise ValueError('recorded rendering imported Torch or MuJoCo')
        result = {'status': 'passed', 'svg_sha256': digest(output), 'torch_imported': False, 'mujoco_imported': False}
    if sources(Path(config['repo'])) != config['sources']:
        raise ValueError('frozen sources changed during child stage')
    write_json(stage / 'result.json', result, budget)
    return 0


def main(args):
    import numpy as np
    from palimpsest import afterimage
    from palimpsest.evaluate import bounded_process
    from palimpsest.male_policy import resolve_profile
    from palimpsest.storage import StorageBudget, StorageLimits
    root, assets, output = args.repo.resolve(), args.assets.resolve(), afterimage.artifacts._safe_path(args.output)
    if Path(__file__).resolve() != root / 'scripts/verify_afterimage.py':
        raise ValueError('--repo must select this harness checkout')
    if output.is_relative_to(assets) or assets.is_relative_to(output):
        raise ValueError('model assets must be outside gate output')
    if output.exists():
        raise FileExistsError('verification output must be new')
    limits = StorageLimits(max_bytes=PROTOCOL['storage_bytes'], min_free_bytes=PROTOCOL['min_free_bytes'],
                           max_runs=1, max_exports=2, max_snapshots=1)
    budget = StorageBudget((output,), limits, headroom_bytes=10 * 1024**2)
    started = time.monotonic()
    report = {'status': 'running', 'protocol': PROTOCOL, 'harness_sha256': digest(__file__),
              'phases': {name: {'status': 'not_started'} for name in ('record', 'reference', 'render_one', 'render_two')},
              'qualification_claims': [], 'finalization_errors': []}
    with budget.lock():
        budget.check(afterimage.MAX_RECORD_BYTES + 16 * 1024**2, path=output)
        # StorageBudget.lock creates this exclusive task's previously absent root.
        identity, _ = resolve_profile(root, assets, 'male-original')
        frozen = sources(root)
        report.update(sources=frozen, policy_identity=identity,
                      commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True, timeout=5).strip())
        input_dir = output / 'stimulus'
        input_dir.mkdir()
        with (input_dir / 'frames.npy').open('xb') as stream:
            np.save(stream, frames(), allow_pickle=False)
        spec = {'schema_version': 1, 'title': 'Afterimage geometric verification fixture',
                'creator': 'scripts/verify_afterimage.py', 'frame_file': 'frames.npy',
                'frame_file_sha256': digest(input_dir / 'frames.npy'), 'source_times_seconds': TIMES,
                'rights': {'basis': 'self_created', 'statement': 'The verification script generates only nonhuman geometric RGB arrays and authorizes local processing and retention; no camera, person or externally sourced media.',
                           'attribution': 'scripts/verify_afterimage.py; authored verification fixture',
                           'authorized_processing_and_retention': True, 'subject_consent': 'no_identifiable_people'}}
        write_json(input_dir / 'stimulus.json', spec, budget)
        stimulus = afterimage.load_stimulus(input_dir / 'stimulus.json')
        report['stimulus'] = stimulus['metadata']
        run = output / uuid.uuid4().hex
        storage = {'roots': [str(output)], 'limits': asdict(limits), 'headroom_bytes': budget.headroom_bytes}
        common = {'repo': str(root), 'assets': str(assets), 'run': str(run), 'identity': identity, 'sources': frozen,
                  'storage': storage, 'stimulus': stimulus['metadata'], 'afterimage_sources': afterimage._source_hashes()}
        record_config = {'repo': str(root), 'assets': str(assets), 'controller': 'male-original',
                         'stimulus': str(input_dir / 'stimulus.json'), 'output': str(run), 'identity': identity,
                         'expected_stimulus': stimulus['metadata'], 'expected_sources': common['afterimage_sources'], 'storage': storage}
        env = {**os.environ, 'PYTHONPATH': str(root / 'src'), 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'}
        write_json(output / 'report.json', report, budget)
        try:
            for name, mode, directory, timeout in (('record', 'record', run, 120), ('reference', 'reference', output / 'reference', 120),
                                                   ('render_one', 'render', output / 'render-one', 15), ('render_two', 'render', output / 'render-two', 15)):
                if time.monotonic() - started + timeout > PROTOCOL['total_seconds']:
                    raise TimeoutError('insufficient total gate budget to admit next stage')
                config = {**common, 'stage': str(directory), 'record_config': record_config}
                phase = report['phases'][name]
                phase.update(status='running', output=str(directory))
                write_json(output / 'report.json', report, budget)
                phase['supervisor'] = bounded_process([sys.executable, str(Path(__file__).resolve()), '--child', mode, json.dumps(config)],
                    directory, timeout, env, storage_budget=budget, log_max_bytes=1024**2)
                receipt = directory / 'process.json'
                if receipt.is_file():
                    phase['process'] = json.loads(receipt.read_text())
                    phase['cleanup'] = cleanup_check(phase['process'])
                phase['status'] = 'failed'
                if phase['supervisor']['status'] != 'completed' or not phase.get('cleanup', {}).get('passed'):
                    raise RuntimeError(f'{name}: supervision or process-group cleanup failed')
                phase['result'] = json.loads((directory / 'result.json').read_text())
                if phase['result'].get('status') != 'passed':
                    raise RuntimeError(f'{name}: stage did not pass')
                phase['status'] = 'passed'
            left, right = (report['phases'][name]['result']['svg_sha256'] for name in ('render_one', 'render_two'))
            if left != right:
                raise ValueError('fresh-process recorded renders differ')
            report.update(status='passed', deterministic_svg_sha256=left, actual_recording_run_id=run.name)
        except Exception as error:
            report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:4096]})
        finally:
            for label, check in (('sources_unchanged', lambda: sources(root) == frozen),
                                 ('assets_unchanged', lambda: resolve_profile(root, assets, 'male-original', identity)[0] == identity),
                                 ('stimulus_unchanged', lambda: afterimage.load_stimulus(input_dir / 'stimulus.json')['metadata'] == stimulus['metadata'])):
                try:
                    report[label] = check()
                    if not report[label]:
                        raise ValueError(label)
                except Exception as error:
                    report['status'] = 'failed'
                    report['finalization_errors'].append({'check': label, 'type': type(error).__name__, 'message': str(error)[:1024]})
            report['elapsed_seconds'] = time.monotonic() - started
            if report['elapsed_seconds'] > PROTOCOL['total_seconds']:
                report['status'] = 'failed'
                report['finalization_errors'].append({'check': 'total_timeout', 'message': 'exceeded 300 seconds'})
            report['artifact_sha256'] = {str(path.relative_to(output)): digest(path) for path in sorted(output.rglob('*'))
                                         if path.is_file() and path.name not in ('report.json', '.palimpsest-storage.lock')}
            report['storage'] = budget.usage()
            write_json(output / 'report.json', report, budget)
    print(json.dumps({'status': report['status'], 'report': str(output / 'report.json')}, allow_nan=False))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == '--child' and sys.argv[2] in ('record', 'reference', 'render'):
        raise SystemExit(child(sys.argv[2], json.loads(sys.argv[3])))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    raise SystemExit(main(parser.parse_args()))
