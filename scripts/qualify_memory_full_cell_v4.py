"""One frozen historical full-model cell qualification; no physics or study."""
from __future__ import annotations

import argparse
from contextlib import ExitStack, suppress, contextmanager
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
import stat
import threading

ROOT = Path(__file__).resolve().parents[1]
RUNS = ('e91cf0a8efbe4712b01a0a469991fcb8', 'e0277617fcd64bc0b1314f723b45b30f',
        '4c41bdc2007940a9bbade1f65add77b9')
INDEX_SHA = 'b9e571a8fff0d9c1bc0a2d10b47355ad9cff96fc0e056d5f994789a95748e3a3'
META = 'docs/reports/memory-prerequisites-v3-evidence/'
SOURCE_FIXED = ('pyproject.toml', 'uv.lock', 'model_manifests/flynn-full-vision.json',
                'docs/plans/memory-family-compact-evidence-v4-protocol.json',
                'docs/plans/memory-full-cell-qualification-v4.md')
PYTHON = '/home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python'
ENVIRONMENT = {'CUDA_VISIBLE_DEVICES': '', 'MKL_NUM_THREADS': '1', 'MUJOCO_GL': 'egl',
               'NUMEXPR_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
               'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': 'src:.'}
LIMITS = {'internal_seconds': 600, 'normal_seconds': 650, 'hard_seconds': 660,
          'sampled_rss_bytes': 6 * 1024**3, 'sampling_seconds': .05,
          'min_free_bytes': 2 * 1024**3, 'output_bytes': 128 * 1024**2,
          'log_bytes': 1024**2, 'result_bytes': 1024**2, 'workload_processes': 3}


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
    with Path(path).open('rb') as stream:
        payload = stream.read(1024**2 + 1)
    if len(payload) > 1024**2 or hashlib.sha256(payload).hexdigest() != expected_sha:
        raise ValueError('Reviewed execution freeze differs')
    from palimpsest.artifacts import _json
    value = _json(payload)
    if payload != _canonical(value) or value['schema'] != 'memory-full-cell-qualification-v4':
        raise ValueError('Execution freeze is not canonical/recognized')
    if set(value) != {'schema', 'repo_root', 'run_ids', 'positive_cells', 'max_cells',
            'model_seed', 'native_owners', 'physics_steps', 'attempts', 'claims', 'inputs',
            'environment', 'output', 'model_edge', 'model_checkpoint', 'python_executable',
            'limits', 'supervisor'}:
        raise ValueError('Execution freeze fields differ')
    if any(type(value[key]) is not int for key in ('positive_cells', 'max_cells',
           'model_seed', 'native_owners', 'physics_steps', 'attempts')):
        raise ValueError('Execution freeze requires exact integer scope')
    if (value['repo_root'] != str(ROOT) or value['run_ids'] != list(RUNS)
            or value['positive_cells'] != 737 or value['max_cells'] != 1470
            or value['model_seed'] != 400 or value['native_owners'] != 0
            or value['physics_steps'] != 0 or value['attempts'] != 1
            or value['claims'] != {'family_admission': False, 'pruning_authorized': False,
                                  'qualification_claims': []}):
        raise ValueError('Execution freeze scope differs')
    if (any(type(value['claims'][key]) is not bool for key in ('family_admission', 'pruning_authorized'))
            or _canonical(value['limits']) != _canonical(LIMITS)
            or value['environment'] != ENVIRONMENT or value['python_executable'] != PYTHON
            or value['output'] != str(ROOT / 'runs/memory-full-cell-qualification-v4-attempt-01')
            or value['model_checkpoint'] != 'connectome_rnn_dagger_princeton_full_vision.pt'
            or value['model_edge'] != 'graph-49d19491c1df4b8f02af0e285b71dc171f47488a93ee5b91be8ee4e280bee9f1/drosophila adult connectome/connections_princeton.csv'
            or set(value['supervisor']) != {'path', 'sha256', 'argv'}
            or value['supervisor']['path'] != '/usr/bin/timeout'
            or value['supervisor']['argv'] != ['--signal=TERM', '--kill-after=10s', '650s']
            or type(value['supervisor']['sha256']) is not str
            or len(value['supervisor']['sha256']) != 64
            or any(c not in '0123456789abcdef' for c in value['supervisor']['sha256'])):
        raise ValueError('Execution freeze invocation or limits differ')
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


@contextmanager
def _publication_directory(path):
    """Hold every output-directory edge; mutable entries may change, names may not."""
    path = Path(path)
    if not path.is_absolute():
        raise ValueError('Qualification publication directory must be absolute')
    opened = []
    def identity(value):
        return value.st_dev, value.st_ino, value.st_mode
    def recheck():
        for fd, parent, name, expected in opened:
            if (identity(os.fstat(fd)) != expected
                    or identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
                raise RuntimeError('Qualification publication directory edge changed')
    try:
        parent = None
        for name in ('/', *path.parts[1:]):
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            expected = identity(os.fstat(fd))
            opened.append((fd, parent, name, expected))
            if identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected:
                raise RuntimeError('Qualification publication directory changed during open')
            parent = fd
        recheck()
        yield parent
        recheck()
    finally:
        for fd, _, _, _ in reversed(opened):
            os.close(fd)


def _reserve_output(freeze):
    output = Path(freeze['output'])
    for role, section in freeze['inputs'].items():
        root = Path(section['root'])
        protected = ([root] if role in ('raw', 'assets', 'runtime') else
                     [root / row['path'] for row in section.get('files', [])])
        if any(output == path or output in path.parents or path in output.parents for path in protected):
            raise ValueError('Qualification output overlaps protected input storage')
    if output.parent.name != 'runs':
        raise ValueError('Qualification output must have its registered runs parent')
    with _publication_directory(output.parent.parent) as repo:
        with suppress(FileExistsError):
            os.mkdir('runs', mode=0o700, dir_fd=repo)
        os.fsync(repo)
        with _publication_directory(output.parent) as runs:
            os.mkdir(output.name, mode=0o700, dir_fd=runs)
            os.fsync(runs)
            with _publication_directory(output) as own:
                os.mkdir('outer', mode=0o700, dir_fd=own)
                os.fsync(own)


def _write(path, value):
    payload = _canonical(value)
    if len(payload) > 1024**2:
        raise ValueError('Qualification report exceeds frozen cap')
    with _publication_directory(path.parent) as parent:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.fsync(parent)


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


def _output_bytes(root):
    """Bound the entire attempt namespace, including both pairs of logs."""
    total = count = directories_seen = 0
    with _publication_directory(root) as held:
        for directory, directories, files in os.walk(f'/proc/self/fd/{held}', followlinks=False):
            directories_seen += len(directories)
            if directories_seen > 2 or any((Path(directory) / name).is_symlink() for name in directories):
                raise ValueError('Qualification output namespace differs')
            for name in files:
                count += 1
                value = (Path(directory) / name).lstat()
                if count > 32 or not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
                    raise ValueError('Qualification output namespace differs')
                total += value.st_size
    return total


@contextmanager
def _owned_logs(output, failures):
    from palimpsest.evaluate import bounded_logs
    with _publication_directory(output) as held:
        with bounded_logs(Path(f'/proc/self/fd/{held}'), 1024**2, failures) as streams:
            yield streams


def _kill_owned_groups(state):
    # Kill the known group first, even if discovery of an in-flight launch fails.
    own_group = os.getpgrp()
    if state.get('group') and state['group'] != own_group:
        with suppress(ProcessLookupError):
            os.killpg(state['group'], signal.SIGKILL)
    # Popen can still be waiting for exec before returning its PID. Direct
    # children of this dedicated monitor are also its owned launches.
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            values = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(values[1]) == os.getpid():
                with suppress(ProcessLookupError):
                    if int(values[2]) == own_group:
                        os.kill(int(path.name), signal.SIGKILL)
                    else:
                        os.killpg(int(values[2]), signal.SIGKILL)
        except (OSError, ValueError):
            continue


@contextmanager
def _hard_guard(deadline, state):
    """Last operational kill clock, including outer monitor/publication stalls."""
    own_group = os.getpgrp()
    if own_group != os.getpid():
        raise ValueError('Hard guard requires a dedicated outer process group')
    stop = threading.Event()
    def expire():
        if stop.wait(max(0, deadline - time.monotonic())):
            return
        try:
            _kill_owned_groups(state)
        finally:
            os.killpg(own_group, signal.SIGKILL)
            os._exit(124)
    previous = signal.getsignal(signal.SIGTERM)
    def interrupted(signum, frame):
        raise InterruptedError('Qualification outside monitor was terminated')
    signal.signal(signal.SIGTERM, interrupted)
    guard = threading.Thread(target=expire, daemon=True)
    guard.start()
    try:
        yield
    except BaseException:
        _kill_owned_groups(state)
        raise
    finally:
        stop.set()
        signal.signal(signal.SIGTERM, previous)
        guard.join(timeout=.1)


def _supervised(command, output, *, normal_deadline, hard_deadline,
                min_free_bytes=2 * 1024**3, max_processes=1, output_root=None, guard_state=None):
    """Observed owned group; bounded existing log drains, no model imports."""
    if type(max_processes) is not int or not 1 <= max_processes <= 3:
        raise ValueError('Qualification process allowance differs')
    output_root = Path(output_root) if output_root is not None else output
    failure = []
    process = None
    peak = 0
    def failed(reason):
        if not failure:
            failure.append(reason)
    with _owned_logs(output, failed) as (stdout, stderr):
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr,
            env=dict(os.environ), cwd=ROOT, start_new_session=True)
        if guard_state is not None:
            guard_state['group'] = process.pid
        monitor_error = None
        try:
            while process.poll() is None:
                members = _group_members(process.pid)
                parent_rss = int(Path('/proc/self/statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
                rss = parent_rss + sum(row['rss_bytes'] for row in members.values())
                peak = max(peak, rss)
                if len(members) > max_processes:
                    failed('unexpected child process')
                elif rss > 6 * 1024**3:
                    failed('sampled RSS stop threshold')
                elif shutil.disk_usage(output).free < min_free_bytes:
                    failed('free-space floor')
                elif _output_bytes(output_root) > 128 * 1024**2:
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
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=max(.001, hard_deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            failed('hard deadline')
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=1)
        members = _group_members(process.pid)
        if members:
            failed('matching process-group survivors')
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
        if monitor_error is not None:
            raise monitor_error
    survivors = sorted(_group_members(process.pid))
    if survivors:
        failed('matching process-group survivors after cleanup')
    elif guard_state is not None:
        guard_state['group'] = None
    if _output_bytes(output_root) > 128 * 1024**2:
        failed('aggregate output cap')
    if shutil.disk_usage(output_root).free < min_free_bytes:
        failed('free-space floor')
    # poll() can first observe an already-exited leader, and bounded log drainage
    # can itself overrun. Successful exit status does not establish timely return.
    finished = time.monotonic()
    if finished >= hard_deadline:
        failed('hard deadline')
    elif finished >= normal_deadline:
        failed('normal-return deadline')
    return {'status': 'completed' if process.returncode == 0 and not failure else 'failed',
            'returncode': process.returncode, 'failure': failure[0] if failure else None,
            'matching_survivors': survivors, 'sampled_peak_rss_bytes': peak,
            'rss_sampling_seconds': .05, 'pid': process.pid,
            'finished_monotonic': finished}


def _read_control(path):
    from palimpsest.artifacts import _json
    from scripts.memory_family_replay_custody_v4 import _identity
    with _publication_directory(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 1024**2:
                raise ValueError('Qualification control is not a bounded regular file')
            raw = stream.read(1024**2 + 1)
            if (_identity(before) != _identity(os.fstat(stream.fileno()))
                    or _identity(before) != _identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False))):
                raise RuntimeError('Qualification control changed during read')
    if len(raw) > 1024**2:
        raise ValueError('Qualification control exceeds its cap')
    return _json(raw)


def _require_parent_origin(job):
    group = os.getpgrp()
    if (type(job.get('supervisor_pid')) is not int or job['supervisor_pid'] <= 0
            or os.getppid() != group or group == os.getpid()):
        raise ValueError('Qualification parent lacks its owned timeout group')
    stat = Path(f'/proc/{group}/stat').read_text().rsplit(')', 1)[1].split()
    if (int(stat[1]) != job['supervisor_pid']
            or Path(f'/proc/{group}/exe').resolve() != Path('/usr/bin/timeout')):
        raise ValueError('Qualification parent timeout origin differs')


def _run_worker(command, output, deadline):
    failures = []
    with _owned_logs(output, failures.append) as (stdout, stderr):
        # Inherit the timeout-owned group. The outer supervisor owns final cleanup,
        # including descendants that outlive their immediate parent.
        completed = subprocess.run(command, stdout=stdout, stderr=stderr,
            cwd=ROOT, env=dict(os.environ), start_new_session=False,
            timeout=max(.001, deadline - time.monotonic()), check=False)
    if failures or completed.returncode != 0:
        raise RuntimeError('Qualification worker or log drainage failed; no retry')
    if time.monotonic() >= deadline:
        raise TimeoutError('Qualification worker exceeded internal deadline')


def _parent(freeze, args, job):
    output = Path(freeze['output'])
    deadline, started = job['deadline'], job['started_monotonic']
    try:
        _require_parent_origin(job)
        _write(output / 'parent-started.json', {'pid': os.getpid(), 'group': os.getpgrp(),
               'started_monotonic': time.monotonic()})
        with ExitStack() as stack:
            inputs = _held_inputs(freeze, deadline, stack)
            command = [sys.executable, '-m', 'scripts.qualify_memory_full_cell_v4',
                '--freeze', str(Path(args.freeze).resolve()), '--freeze-sha256', args.freeze_sha256, '--worker']
            _run_worker(command, output, deadline)
            for held in inputs.values(): held.recheck()
            result = _read_control(output / 'worker-result.json')
            if (type(result.get('positive_cells')) is not int or result['positive_cells'] != 737
                    or len(result.get('negatives', [])) != 4
                    or any(row.get('rejected') is not True for row in result['negatives'])):
                raise ValueError('Worker result is incomplete')
        if time.monotonic() >= deadline:
            raise TimeoutError('Final custody exceeded internal deadline')
        _write(output / 'close.json', {'status': 'passed', 'freeze_sha256': args.freeze_sha256,
            'elapsed_seconds': time.monotonic() - started, 'claims': freeze['claims']})
        if time.monotonic() >= deadline:
            raise TimeoutError('Close publication exceeded internal deadline')
    except BaseException as error:
        _write(output / 'failure.json', {'status': 'failed', 'error_type': type(error).__name__,
            'message': str(error), 'claims': freeze['claims']})
        raise


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--freeze', required=True)
    parser.add_argument('--freeze-sha256', required=True)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--worker', action='store_true')
    modes.add_argument('--parent', action='store_true')
    args = parser.parse_args(argv)
    freeze = _freeze(args.freeze, args.freeze_sha256)
    if sys.executable != freeze['python_executable']:
        raise ValueError('Frozen invocation interpreter differs')
    for key, value in freeze['environment'].items():
        if os.environ.get(key) != value:
            raise ValueError('Frozen environment differs: ' + key)
    output = Path(freeze['output'])
    if args.parent or args.worker:
        job = _read_control(output / 'attempt.json')
        if job['freeze_sha256'] != args.freeze_sha256:
            raise ValueError('Attempt freeze differs')
        if args.parent:
            return _parent(freeze, args, job)
        parent = _read_control(output / 'parent-started.json')
        if os.getppid() != parent['pid'] or os.getpgrp() != parent['group']:
            raise ValueError('Qualification worker process origin differs')
        _write(output / 'worker-started.json', {'pid': os.getpid(), 'group': os.getpgrp(),
                                             'started_monotonic': time.monotonic()})
        with ExitStack() as stack:
            inputs = _held_inputs(freeze, job['deadline'], stack)
            result = _qualify(freeze, inputs, job['deadline'])
        _write(output / 'worker-result.json', result)
        if time.monotonic() >= job['deadline']:
            raise TimeoutError('Worker publication exceeded internal deadline')
        return
    # The outside monitor reserves once and never imports the numerical stack.
    # Its clocks include startup, custody, inference, final checks and close fsync.
    if os.getpgrp() != os.getpid():
        os.setsid()
    started = time.monotonic()
    guard_state = {"group": None}
    with _hard_guard(started + 660, guard_state):
        _reserve_output(freeze)
        deadline = started + 600
        _write(output / 'attempt.json', {'freeze_sha256': args.freeze_sha256,
            'started_monotonic': started, 'deadline': deadline,
            'supervisor_pid': os.getpid(), 'attempt': 1})
        try:
            tool = freeze['supervisor']
            with Path(tool['path']).open('rb') as stream:
                payload = stream.read(1024**2 + 1)
            if len(payload) > 1024**2 or hashlib.sha256(payload).hexdigest() != tool['sha256']:
                raise ValueError('Frozen timeout executable differs')
            command = [tool['path'], *tool['argv'], sys.executable,
                '-m', 'scripts.qualify_memory_full_cell_v4', '--freeze', str(Path(args.freeze).resolve()),
                '--freeze-sha256', args.freeze_sha256, '--parent']
            supervision = _supervised(command, output / 'outer', normal_deadline=started + 650,
                hard_deadline=started + 660, max_processes=3,
                output_root=output, guard_state=guard_state)
            _write(output / 'supervisor.json', supervision)
            if (supervision['status'] != 'completed' or supervision['returncode'] != 0
                    or supervision['matching_survivors'] or (output / 'failure.json').exists()):
                raise RuntimeError('Whole-parent qualification failed; no retry')
            close = _read_control(output / 'close.json')
            if close['status'] != 'passed' or close['freeze_sha256'] != args.freeze_sha256:
                raise ValueError('Qualification parent close differs')
            _write(output / 'terminal.json', {'status': 'passed', 'freeze_sha256': args.freeze_sha256,
                'elapsed_seconds': time.monotonic() - started, 'claims': freeze['claims']})
            # This receipt is outside the timed workload group. Refuse slow fsync;
            # external observed exit 0 is also required before accepting an attempt.
            if time.monotonic() >= started + 650:
                raise TimeoutError('Terminal publication exceeded normal-return boundary')
        except BaseException as error:
            _write(output / 'outer-failure.json', {'status': 'failed', 'error_type': type(error).__name__,
                'message': str(error), 'claims': freeze['claims']})
            raise


if __name__ == '__main__':
    main()
