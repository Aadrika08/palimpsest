"""One frozen historical full-model cell qualification; no physics or study."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sys
import time
import signal
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
RUNS = ('e91cf0a8efbe4712b01a0a469991fcb8', 'e0277617fcd64bc0b1314f723b45b30f',
        '4c41bdc2007940a9bbade1f65add77b9')
INDEX_SHA = 'b9e571a8fff0d9c1bc0a2d10b47355ad9cff96fc0e056d5f994789a95748e3a3'
META = 'docs/reports/memory-prerequisites-v3-evidence/'
SOURCE_FIXED = ('pyproject.toml', 'uv.lock', 'model_manifests/flynn-full-vision.json',
                'docs/plans/memory-family-compact-evidence-v4-protocol.json',
                'docs/plans/memory-full-cell-qualification-v4.md')


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _selected_raw_descriptors(index, raw_root):
    root = Path(raw_root)
    selected = []
    for row in index['files']:
        parts = PurePosixPath(row['member']).parts
        if len(parts) < 5 or parts[:3] != ('output', 'stage', 'runs') or parts[3] not in RUNS:
            continue
        raw = row['source']
        if type(raw) is not str or any(part in ('.', '..') for part in raw.split('/')[1:]):
            raise ValueError('Original indexed source path is noncanonical')
        try:
            relative = Path(raw).relative_to(root).as_posix()
        except ValueError as error:
            raise ValueError('Original indexed source has a different root') from error
        if relative != '/'.join(parts[3:]):
            raise ValueError('Original publication member/source differ')
        selected.append({'path': relative, 'size_bytes': row['bytes'], 'sha256': row['sha256']})
    paths = [row['path'] for row in selected]
    if len(paths) != len(set(paths)) or {p.split('/')[0] for p in paths} != set(RUNS):
        raise ValueError('Original selected tree roster is incomplete or ambiguous')
    return sorted(selected, key=lambda row: row['path'])


def _endpoint(proof, snapshot):
    from palimpsest.snapshots import state_digest
    if proof['final_hidden_sha256'] != state_digest(snapshot['policy']['hidden']):
        raise ValueError('Cell replay final endpoint differs')


def _negative_copy(kind, rows, snapshot):
    import numpy as np
    changed = copy.deepcopy(rows)
    state = copy.deepcopy(snapshot)
    if kind == 'encoded-input':
        changed[710]['encoded_input'] += np.float32(100)
    elif kind == 'raw-output':
        changed[0]['raw_output'] += np.float32(100)
    elif kind == 'initial-hidden':
        state['policy']['hidden'] += np.float32(100)
    else:
        raise ValueError('Unregistered negative')
    return changed, state


def _source_roster(root):
    root = Path(root)
    paths = set(SOURCE_FIXED)
    for prefix in ('src/palimpsest', 'scripts', 'upstream/fly-gym'):
        base = root / prefix
        if not base.is_dir() or base.is_symlink():
            raise ValueError('Qualification source root is absent or aliased')
        for directory, directories, files in os.walk(base, followlinks=False):
            current = Path(directory)
            if any((current / name).is_symlink() for name in directories):
                raise ValueError('Qualification source directory is aliased')
            for name in files:
                path = current / name
                if path.suffix == '.pyc':
                    raise ValueError('Qualification source has unbound bytecode')
                if path.suffix not in ('.py', '.xml'):
                    continue
                if path.is_symlink():
                    raise ValueError('Qualification source file is aliased')
                paths.add(path.relative_to(root).as_posix())
                if len(paths) > 500:
                    raise ValueError('Qualification source roster exceeds its ceiling')
    return sorted(paths)


def _freeze(path, expected_sha):
    payload = Path(path).read_bytes()
    if len(payload) > 1024**2 or hashlib.sha256(payload).hexdigest() != expected_sha:
        raise ValueError('Reviewed execution freeze differs')
    from palimpsest.artifacts import _json
    value = _json(payload)
    if payload != _canonical(value) or value['schema'] != 'memory-full-cell-qualification-v4':
        raise ValueError('Execution freeze is not canonical/recognized')
    if (value['repo_root'] != str(ROOT) or value['run_ids'] != list(RUNS)
            or value['positive_cells'] != 737 or value['max_cells'] != 1470
            or value['model_seed'] != 400 or value['native_owners'] != 0
            or value['physics_steps'] != 0 or value['attempts'] != 1
            or value['claims'] != {'family_admission': False, 'pruning_authorized': False,
                                  'qualification_claims': []}):
        raise ValueError('Execution freeze scope differs')
    if (set(value['inputs']) != {'sources', 'metadata', 'raw', 'assets', 'runtime'}
            or value['inputs']['sources']['root'] != str(ROOT)
            or value['inputs']['metadata']['root'] != str(ROOT)
            or value['environment'].get('PYTHONDONTWRITEBYTECODE') != '1'
            or value['environment'].get('PYTHONPATH') != 'src:.'):
        raise ValueError('Execution freeze input/source boundary differs')
    return value


def _held_inputs(freeze, deadline, stack):
    from scripts.memory_family_replay_custody_v4 import HeldReplayFiles
    if _source_roster(ROOT) != [row['path'] for row in freeze['inputs']['sources']['files']]:
        raise ValueError('Qualification source roster differs from reviewed freeze')
    return {role: stack.enter_context(HeldReplayFiles(
        section['root'], section['files'], deadline,
        exact_subtrees=tuple(RUNS) if role == 'raw' else ()))
        for role, section in sorted(freeze['inputs'].items(), key=lambda pair: pair[0] != 'sources')}


def _raw_roster(freeze, inputs):
    from palimpsest import artifacts
    metadata = inputs['metadata']
    index = artifacts._json(metadata.read(META + 'publication-index.json', 1024**2))
    index_raw = metadata.read(META + 'publication-index.json', 1024**2)
    if hashlib.sha256(index_raw).hexdigest() != INDEX_SHA:
        raise ValueError('Original committed publication index differs')
    rows = _selected_raw_descriptors(index, freeze['inputs']['raw']['root'])
    if (rows != freeze['inputs']['raw']['files'] or len(rows) != 45
            or sum(row['size_bytes'] for row in rows) != 173646919):
        raise ValueError('Selected original input roster differs')
    registration = artifacts._json(metadata.read(META + 'registration.json', 1024**2))
    fresh = artifacts._json(metadata.read(META + 'fresh-source.json', 1024**2))
    close = artifacts._json(metadata.read(META + 'scientific-close.json', 1024**2))
    if (registration['assets'] != freeze['inputs']['assets']['root']
            or fresh['run_id'] != RUNS[0] or fresh['source_job_id'] != 'south-prefix'
            or fresh['snapshot_sha256'] != 'c426c119eb73028626d7fb5e393708dd476cf71b96d1397bc154ba62d528f4a3'
            or close['status'] != 'native-prerequisites-passed'
            or not set(RUNS) <= {row['run_id'] for row in close['owners']}):
        raise ValueError('Original campaign metadata linkage differs')
    return rows


def _qualify(freeze, inputs, deadline):
    import numpy as np
    import torch
    from palimpsest import snapshots, assets
    from palimpsest.flynn import load_policy
    from scripts import memory_family_cell_replay_v4 as cell
    from scripts import memory_family_oracle_admission_v3 as raw_reader
    from scripts.verify_flynn_memory_transfer import policy_bindings

    if (sys.version_info[:3] != (3, 11, 15) or np.__version__ != '2.2.5'
            or str(torch.__version__).split('+')[0] != '2.9.0'):
        raise ValueError('Frozen numerical runtime differs')
    torch.set_num_threads(1)
    _raw_roster(freeze, inputs)
    source = inputs['raw']
    traces, snps = {}, {}
    for run in RUNS:
        data = raw_reader._read_run({'run_id': run, 'run': source.path(run + '/owner.json').parent}, deadline)
        policy_bindings(data)
        expected = list(range(727)) if run == RUNS[0] else list(range(727, 732))
        if [row['tick'] for row in data['rows']] != expected or any(row['episode'] != 0 for row in data['rows']):
            raise ValueError('Original row order/count differs')
        traces[run] = data
        snps[run] = {'initial': snapshots.read_snapshot(source.fd_path(run + '/snapshots/initial.snp'))}
        if run != RUNS[0]:
            snps[run]['post'] = snapshots.read_snapshot(source.fd_path(run + '/snapshots/post-repeat.snp'))
    acquired = snps[RUNS[0]]['initial']
    model_inputs = inputs['assets']
    model = load_policy(ROOT, model_inputs.path(freeze['model_edge']),
                        model_inputs.path(freeze['model_checkpoint']), 'cpu', 400)
    cell._pinned_policy(model)
    calls = [0]
    def counted(module, arguments):
        calls[0] += 1
        if calls[0] > 1470:
            raise RuntimeError('Qualification exceeds frozen cell-call ceiling')
    count_hook = model.agent.cell.register_forward_pre_hook(counted, prepend=True)
    for pair in snps.values():
        for snapshot in pair.values():
            cell._equal(snapshot['identity']['policy']['provenance'], model.provenance,
                        'indexed policy provenance')
            cell._equal(snapshot['application']['controller_tensors'], snapshots.controller_hashes(model),
                        'indexed immutable model')
    for run in RUNS[1:]:
        cell._equal(snps[run]['initial']['policy'], acquired['policy'], 'original restored initial policy')
    def replay(rows, snapshot, operation, first_tick):
        return cell._replay_rows(policy=model, rows=rows, source_snapshot=snapshot,
            operation=operation, first_tick=first_tick, input_width=4813, deadline=deadline)
    positives = []
    positives.append(replay(traces[RUNS[0]]['rows'], acquired, 'source', 0))
    for run in RUNS[1:]:
        result = replay(traces[run]['rows'], snps[run]['initial'], 'condition', 727)
        _endpoint(result, snps[run]['post'])
        positives.append(result)
    negatives = []
    for kind in ('encoded-input', 'raw-output', 'initial-hidden'):
        run = RUNS[1] if kind == 'initial-hidden' else RUNS[0]
        rows, state = _negative_copy(kind, traces[run]['rows'], snps[run]['initial'])
        try:
            result = replay(rows, state, 'condition' if run != RUNS[0] else 'source', 727 if run != RUNS[0] else 0)
            if run != RUNS[0]:
                _endpoint(result, snps[run]['post'])
        except ValueError as error:
            message = str(error)
            if not (message.startswith('Cell replay raw output or action differs at tick ')
                    or message in ('Cell replay acquired source endpoint differs', 'Cell replay final endpoint differs')):
                raise
            negatives.append({'kind': kind, 'rejected': True, 'reason': message})
        else:
            raise ValueError('Frozen negative failed to discriminate: ' + kind)
    parameter = dict(model.agent.named_parameters())['cell.readout_head.0.bias']
    before = parameter.detach().clone()
    try:
        with torch.no_grad(): parameter.add_(100)
        try:
            replay(traces[RUNS[0]]['rows'], acquired, 'source', 0)
        except ValueError as error:
            if str(error) != 'Cell replay immutable model tensors differs':
                raise
            negatives.append({'kind': 'model-parameter', 'rejected': True, 'reason': str(error)})
        else:
            raise ValueError('Frozen model negative failed to discriminate')
    finally:
        with torch.no_grad(): parameter.copy_(before)
    cell._equal(snapshots.controller_hashes(model), acquired['application']['controller_tensors'], 'restored original model')
    count_hook.remove()
    if 'mujoco' in sys.modules or 'palimpsest.engine' in sys.modules or torch.cuda.is_initialized():
        raise ValueError('Qualification loaded a forbidden physics/Engine/CUDA route')
    for held in inputs.values(): held.recheck()
    return {'scope': 'three-historical-traces-full-model-encoded-cell-only', 'positive_cells': 737,
            'total_cell_calls': calls[0],
            'positives': positives, 'negatives': negatives, 'model_provenance': model.provenance,
            'controller_tensors': snapshots.controller_hashes(model), 'torch_profile': snapshots._torch_profile(),
            'claims': copy.deepcopy(freeze['claims'])}


def _write(path, value):
    payload = _canonical(value)
    if len(payload) > 1024**2:
        raise ValueError('Qualification report exceeds frozen cap')
    with path.open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)


def _group_members(group):
    result = {}
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            values = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(values[2]) == group and values[0] not in ('Z', 'X'):
                result[int(path.name)] = {'start_ticks': int(values[19]),
                                         'rss_bytes': int(values[21]) * os.sysconf('SC_PAGE_SIZE')}
        except (FileNotFoundError, ProcessLookupError):
            continue
    return result


def _supervised(command, output, *, normal_deadline, hard_deadline,
                min_free_bytes=2 * 1024**3):
    """Observed one-worker group; bounded existing log drains, no model imports."""
    from palimpsest.evaluate import bounded_logs
    failure = []
    process = None
    peak = 0
    def failed(reason):
        if not failure:
            failure.append(reason)
    with bounded_logs(output, 1024**2, failed) as (stdout, stderr):
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr,
            env=dict(os.environ), cwd=ROOT, start_new_session=True)
        monitor_error = None
        try:
            while process.poll() is None:
                members = _group_members(process.pid)
                parent_rss = int(Path('/proc/self/statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
                rss = parent_rss + sum(row['rss_bytes'] for row in members.values())
                peak = max(peak, rss)
                if set(members) - {process.pid}:
                    failed('unexpected child process')
                elif rss > 6 * 1024**3:
                    failed('sampled RSS stop threshold')
                elif shutil.disk_usage(output).free < min_free_bytes:
                    failed('free-space floor')
                elif sum(path.stat().st_size for path in output.iterdir() if path.is_file()) > 128 * 1024**2:
                    failed('aggregate output cap')
                elif time.monotonic() >= normal_deadline:
                    failed('normal-return deadline')
                if failure:
                    break
                time.sleep(.05)
        except BaseException as error:
            monitor_error = error
            failed('process monitor error')
        if failure and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=max(.001, hard_deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            failed('hard deadline')
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=1)
        members = _group_members(process.pid)
        if members:
            failed('matching process-group survivors')
            os.killpg(process.pid, signal.SIGKILL)
        if monitor_error is not None:
            raise monitor_error
    survivors = sorted(_group_members(process.pid))
    if survivors:
        failed('matching process-group survivors after cleanup')
    return {'status': 'completed' if process.returncode == 0 and not failure else 'failed',
            'returncode': process.returncode, 'failure': failure[0] if failure else None,
            'matching_survivors': survivors, 'sampled_peak_rss_bytes': peak,
            'rss_sampling_seconds': .05, 'pid': process.pid}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', required=True)
    parser.add_argument('--freeze-sha256', required=True)
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args(argv)
    freeze = _freeze(args.freeze, args.freeze_sha256)
    for key, value in freeze['environment'].items():
        if os.environ.get(key) != value:
            raise ValueError('Frozen environment differs: ' + key)
    output = Path(freeze['output'])
    if args.worker:
        job = json.loads((output / 'attempt.json').read_bytes())
        if job['freeze_sha256'] != args.freeze_sha256:
            raise ValueError('Worker attempt freeze differs')
        _write(output / 'worker-started.json', {'pid': os.getpid(), 'started_monotonic': time.monotonic()})
        with ExitStack() as stack:
            inputs = _held_inputs(freeze, job['deadline'], stack)
            result = _qualify(freeze, inputs, job['deadline'])
        _write(output / 'worker-result.json', result)
        return
    started = time.monotonic()
    output.parent.mkdir(exist_ok=True)
    output.mkdir(parents=False, exist_ok=False)
    deadline = started + 600
    _write(output / 'attempt.json', {'freeze_sha256': args.freeze_sha256, 'started_monotonic': started,
                                   'deadline': deadline, 'parent_pid': os.getpid(), 'attempt': 1})
    try:
        with ExitStack() as stack:
            inputs = _held_inputs(freeze, deadline, stack)
            command = [sys.executable, '-m', 'scripts.qualify_memory_full_cell_v4',
                       '--freeze', str(Path(args.freeze).resolve()), '--freeze-sha256', args.freeze_sha256, '--worker']
            supervision = _supervised(command, output,
                normal_deadline=started + 650, hard_deadline=started + 660)
            _write(output / 'supervisor.json', supervision)
            if supervision['status'] != 'completed' or supervision['returncode'] != 0:
                raise RuntimeError('Qualification worker failed; no retry')
            if time.monotonic() >= deadline:
                raise TimeoutError('Internal qualification deadline exceeded')
            for held in inputs.values(): held.recheck()
            result = json.loads((output / 'worker-result.json').read_bytes())
            if result['positive_cells'] != 737 or len(result['negatives']) != 4:
                raise ValueError('Worker result is incomplete')
        if time.monotonic() >= deadline:
            raise TimeoutError('Final custody exceeded internal deadline')
        _write(output / 'close.json', {'status': 'passed', 'freeze_sha256': args.freeze_sha256,
                                     'elapsed_seconds': time.monotonic() - started, 'claims': freeze['claims']})
    except BaseException as error:
        _write(output / 'failure.json', {'status': 'failed', 'error_type': type(error).__name__,
                                       'message': str(error), 'claims': freeze['claims']})
        raise


if __name__ == '__main__':
    main()
