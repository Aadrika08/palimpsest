"""Matched recording ablations. Execution rows require a four-condition seed gate.

No model is run by --self-check. Scientific runs are sequential fresh processes;
operation costs consume explicit retained replay row metadata, never null output.
"""
from __future__ import annotations
import argparse
import copy
import gc
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import subprocess
import sys
import time
import threading
import uuid
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / 'src'))
from paper.studies.authority_replay_v1.common import (
    OVERHEAD_CONDITIONS, append_row, campaign_identity, declared_units, load_protocol,
    prepare_output_root, require, sha256_file, validate_finite,
)
from paper.studies.authority_replay_v1.null_writer import NullWriter

# The protocol is frozen and validated before any driver launch.
RESOURCES = load_protocol(REPO / 'paper/studies/authority_replay_v1/protocol.json').resources
CONDITIONS = OVERHEAD_CONDITIONS
MiB, GiB = 1024**2, 1024**3


def condition_order(seed):
    require(type(seed) is int and seed in range(10), 'undeclared overhead seed')
    rotation = seed % 4
    return CONDITIONS[rotation:] + CONDITIONS[:rotation]


def match_seed(rows):
    """Retain all rows, but exclude the entire seed if any condition differs/fails."""
    for row in rows:
        validate_finite(row)
    require(len(rows) == 4 and {r['condition'] for r in rows} == set(CONDITIONS)
            and len({r['seed'] for r in rows}) == 1, 'gate requires four distinct conditions for one seed')
    matched = all(r.get('status') == 'completed' for r in rows)
    for key in ('actions_sha256', 'tick_count', 'final_state_sha256'):
        matched = matched and rows[0].get(key) is not None and all(r.get(key) == rows[0][key] for r in rows)
    matched = bool(matched and rows[0].get('tick_count') == 220)
    for row in rows:
        row.update(timing_eligible=matched, matched_seed=matched,
                   timing_exclusion=None if matched else 'whole-seed action/tick/final-state gate failed')
    return matched


def make_writer(condition, path, manifest, max_bytes=512 * MiB, *, storage_budget=None):
    require(condition in CONDITIONS, 'undeclared writer condition')
    if condition == 'null':
        return NullWriter(path, manifest, max_bytes=max_bytes)
    from palimpsest.records import RunWriter
    from palimpsest.storage import StorageBudget, StorageLimits
    budget = storage_budget
    if condition == 'background_storage' and budget is None:
        budget = StorageBudget((Path(path).parent,), StorageLimits(max_bytes=512 * MiB, min_free_bytes=6 * GiB), headroom_bytes=16 * MiB, recount_seconds=.25)
    writer = RunWriter(path, manifest, max_bytes=max_bytes,
                       storage_budget=budget if condition == 'background_storage' else None)
    if condition.startswith('background'):
        writer.start_background(max_items=16)
    return writer


def host_covariates():
    def read(path):
        try:
            return Path(path).read_text().strip()
        except OSError:
            return None
    info = read('/proc/meminfo') or ''
    available = next((int(line.split()[1]) * 1024 for line in info.splitlines() if line.startswith('MemAvailable:')), None)
    cpu = read('/proc/cpuinfo') or ''
    model = next((line.split(':', 1)[1].strip() for line in cpu.splitlines() if line.startswith('model name')), None)
    competing = []
    for process in Path('/proc').iterdir():
        if process.name.isdigit() and int(process.name) != os.getpid():
            value = read(process / 'cmdline')
            if value and 'palimpsest' in value:
                competing.append({'pid': int(process.name), 'cmdline': value.replace('\x00', ' ')[:1024]})
    return {'load_averages': list(os.getloadavg()), 'available_memory_bytes': available, 'cpu_model': model,
            'cpu_governor': read('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor'),
            'competing_palimpsest_processes': competing, 'cache_policy': 'warm-cache; no OS page-cache flush; same-host'}


def _resources():
    return {'peak_rss_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            'descriptor_count': len(list(Path('/proc/self/fd').iterdir())),
            'thread_count': len(list(Path('/proc/self/task').iterdir()))}


def _step(engine):
    tick = engine.total_tick
    if hasattr(engine, 'submit'):
        receipt = engine.submit({'id': f'benchmark-step-{tick}', 'kind': 'step', 'expected_state': engine.phase,
                                'expected_episode': engine.episode, 'expected_revision': engine.revision})
        require(receipt.get('status') != 'rejected', 'benchmark step rejected')
    engine.advance()
    require(engine.total_tick == tick + 1, f'engine did not complete tick {tick}')


def measure_ticks(engine, *, camera_counter=None, budget=None):
    """Twenty warm-up ticks then 200 measured, including final writer drain."""
    import numpy as np
    actions = hashlib.sha256()
    def advance():
        _step(engine)
        action = np.asarray(engine.last_transition['action'])
        actions.update(str(action.dtype).encode() + str(action.shape).encode() + action.tobytes())
    for _ in range(20):
        advance()
    engine.writer.flush()
    recorded_before = _size(engine.writer.path) if hasattr(engine.writer, 'path') else 0
    camera_start = 0. if camera_counter is None else camera_counter['seconds']
    budgets = [] if budget is None else [budget, budget.campaign_budget]
    recount_start = sum(b.recount_wall_seconds for b in budgets)
    recount_count_start = sum(b.recounts for b in budgets)
    backpressure_start = (engine.writer.background_stats() or {}).get('backpressure_seconds', 0.)
    samples = [_resources()]
    policy = physics = 0.
    started = time.perf_counter()
    for index in range(200):
        advance()
        policy += float(engine.last_transition['latency'])
        physics += float(engine.last_transition['step_latency'])
        if index % 20 == 19:
            samples.append(_resources())
    engine.writer.flush()
    wall = time.perf_counter() - started
    metrics = {'wall_seconds': wall, 'wall_seconds_per_tick': wall / 200,
               'policy_seconds': policy, 'physics_seconds': physics,
               'bytes_per_tick': (_size(engine.writer.path) - recorded_before) / 200 if hasattr(engine.writer, 'path') else 0.,
               'camera_seconds': None if camera_counter is None else camera_counter['seconds'] - camera_start,
               'writer_backpressure_seconds': (engine.writer.background_stats() or {}).get('backpressure_seconds', 0.) - backpressure_start,
               'storage_recount_seconds': sum(b.recount_wall_seconds for b in budgets) - recount_start,
               'storage_recount_count': sum(b.recounts for b in budgets) - recount_count_start,
               **{key: max(sample[key] for sample in samples) for key in samples[0]}}
    result = {'actions_sha256': actions.hexdigest(), 'tick_count': engine.total_tick,
              'measured_tick_count': 200, 'warmup_tick_count': 20, 'metrics': metrics,
              'resource_samples': samples}
    validate_finite(result)
    return result


def _json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def _size(root):
    return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file() and not p.is_symlink())


def _hashes(root):
    return {str(p.relative_to(root)): sha256_file(p) for p in sorted(Path(root).rglob('*')) if p.is_file()}


def _budget(output, campaign_root):
    from palimpsest.storage import StorageBudget, StorageLimits
    class TimedBudget(StorageBudget):
        recount_wall_seconds = 0.
        def usage(self):
            start = time.perf_counter()
            try:
                return super().usage()
            finally:
                self.recount_wall_seconds += time.perf_counter() - start
    # Both caps apply before each write. Root accounting includes sibling studies.
    campaign = TimedBudget((campaign_root,), StorageLimits(max_bytes=RESOURCES['campaign_max_output_bytes'], min_free_bytes=6 * GiB), headroom_bytes=16 * MiB, recount_seconds=.25)
    unit = TimedBudget((output,), StorageLimits(max_bytes=512 * MiB, min_free_bytes=6 * GiB), headroom_bytes=16 * MiB, recount_seconds=.25)
    original = unit.check
    def check(additional_bytes, *, path):
        campaign.check(additional_bytes, path=path)
        return original(additional_bytes, path=path)
    unit.check = check
    unit.campaign_budget = campaign
    return unit


def _final_digest(engine, *, diagnostics=None, metadata=None):
    import mujoco
    from palimpsest.snapshots import capture, save_snapshot, state_digest
    original = capture(engine.env, engine.observation, policy=engine.policy, application=engine.application_state())
    state = copy.deepcopy(original)
    # Recorder identity is not part of matched continuation state.
    for key in ('source_run_id', 'event_prefix'):
        state['application'].pop(key)
    raw_final_digest = state_digest(state)
    # Only elapsed wall-clock telemetry is canonicalized, on a PRIVATE decoder.
    # All native physical/solver/cache state and seeded RNG remain in the digest.
    native = mujoco.MjData.__new__(mujoco.MjData)
    native.__setstate__(state['native_data'])
    native.timer.duration[:] = 0.
    state['native_data'] = native.__getstate__()
    state['native_sha256'] = hashlib.sha256(state['native_data']).hexdigest()
    details = {'raw_snapshot_state_sha256': state_digest(original),
               'raw_final_state_sha256': raw_final_digest,
               'raw_native_sha256': hashlib.sha256(original['native_data']).hexdigest(),
               'matched_native_sha256': state['native_sha256'],
               'final_state_normalization': {'recorder_fields': ['application.source_run_id', 'application.event_prefix'],
                   'native_fields': ['timer.duration'], 'mujoco_version': mujoco.__version__,
                   'mechanism': 'Zero elapsed timer durations on a private decoded MjData copy only; retain all other fields and RNG.'}}
    if diagnostics is not None:
        target, budget = diagnostics
        raw_target = Path(target).parent / 'final-raw.snp'
        save_snapshot(original, raw_target, storage_budget=budget)
        save_snapshot(state, target, storage_budget=budget)
        details.update(raw_snapshot_path=str(raw_target), matched_snapshot_path=str(target))
        _json(Path(target).parent / 'final-component-digests.json',
              {'development_only': os.environ.get('PALIMPSEST_OVERHEAD_DEVELOPMENT_DIAGNOSTICS') == '1',
               'components': {key: state_digest(value) for key, value in state.items()},
               'raw_components': {key: state_digest(value) for key, value in original.items()},
               'rng': {key: state_digest(value) for key, value in state['rng'].items()}, **details})
    if metadata is not None:
        metadata.update(details)
    return state_digest(state)


def _execution(seed, condition, output, repo, assets, campaign_root):
    from palimpsest import records
    from palimpsest.engine import Engine
    original = records.RunWriter
    budget = _budget(output, campaign_root) if condition == 'background_storage' else None
    def factory(path, manifest, max_bytes=None, storage_budget=None):
        if condition == 'null':
            return NullWriter(path, manifest, max_bytes=max_bytes)
        writer = original(path, manifest, max_bytes=max_bytes, storage_budget=budget)
        if condition.startswith('background'):
            writer.start_background(max_items=16)
        return writer
    started = time.perf_counter()
    with patch.object(records, 'RunWriter', factory):
        engine = Engine.open(repo, assets, output / 'recording', controller='flynn', device='cpu', seed=seed,
                             scenario='sparse-navigation', run_id='00000000000000000000000000000001', max_bytes=480 * MiB)
    opened = time.perf_counter() - started
    camera = {'seconds': 0.}
    # Render timing is nested inside env.step; never subtract it from physics.
    render = getattr(engine.env, '_render_camera', None)
    if render is not None:
        def timed_render(*args, **kwargs):
            start = time.perf_counter()
            try:
                return render(*args, **kwargs)
            finally:
                camera['seconds'] += time.perf_counter() - start
        engine.env._render_camera = timed_render
    try:
        result = measure_ticks(engine, camera_counter=camera if render else None, budget=budget)
        final_metadata = {}
        result['final_state_sha256'] = _final_digest(engine,
            diagnostics=(output / 'final-normalized.snp', _budget(output, campaign_root)), metadata=final_metadata)
        result.update(final_metadata)
        result['development_diagnostics'] = os.environ.get('PALIMPSEST_OVERHEAD_DEVELOPMENT_DIAGNOSTICS') == '1'
        result['metrics']['open_seconds'] = opened
        result['camera_timing_scope'] = 'env._render_camera; nested in physics_seconds' if render else 'unavailable: env._render_camera absent'
    finally:
        closing = time.perf_counter()
        engine.close()
        close_seconds = time.perf_counter() - closing
    result['metrics']['close_seconds'] = close_seconds
    result['metrics']['output_bytes'] = _size(output)
    return result


def _source(seed, source):
    row = json.loads(Path(source).read_text()) if Path(source).is_file() else {}
    meta = row.get('source', {})
    require(row.get('kind') == 'replay' and row.get('status') == 'completed' and row.get('seed') == seed
            and meta.get('seed') == seed and meta.get('condition') == 'background_storage'
            and meta.get('recording_writer') == 'background' and meta.get('storage_accounting') is True
            and meta.get('prefix_ticks') == 8 and meta.get('source_ticks') == 100,
            'operation costs require retained replay full-writer background_storage source row')
    path = Path(meta['run_path']) / 'recording'
    require((path / 'manifest.json').is_file() and Path(meta['snapshot_path']).is_file(), 'retained replay source missing')
    manifest = json.loads((path / 'manifest.json').read_text())
    require(manifest.get('status') == 'completed' and not manifest.get('benchmark_null_writer'), 'full-writer source must be completed')
    return row, meta, path


def _operation_config(seed, meta, recording, retained):
    """Bind the fresh capture owner to the retained manifest and prefix snapshot."""
    manifest = json.loads((recording / 'manifest.json').read_text())
    profile = manifest.get('scenario')
    require(isinstance(profile, dict), 'retained source config requires a scenario profile')
    config = {'controller': manifest.get('controller'), 'scenario': profile.get('id'),
              'texture': manifest.get('texture'), 'seed': manifest.get('seed'),
              'device': manifest.get('requested_device')}
    require(config['controller'] == 'flynn' and config['device'] == 'cpu'
            and type(config['seed']) is int and config['seed'] == seed == meta['seed']
            and isinstance(config['scenario'], str) and bool(config['scenario'])
            and isinstance(config['texture'], str) and bool(config['texture'])
            and profile.get('controller') == config['controller']
            and profile.get('texture') == config['texture']
            and manifest.get('profile') == config['controller'], 'retained source config mismatch')
    application = retained.get('application', {})
    require(all(application.get(key) == config[key] for key in ('controller', 'scenario', 'texture', 'seed'))
            and type(application.get('seed')) is int
            and application.get('total_tick') == meta['prefix_ticks']
            and application.get('phase') == 'paused', 'retained snapshot config differs from source config')
    require(application.get('source_run_id') == manifest.get('run_id') == recording.parent.name,
            'retained snapshot source identity mismatch')
    return config


def _bind_operation_environment(retained):
    """Recreate recorded CPU/render environment before constructing any owner."""
    identity = retained.get('identity', {})
    torch_profile, renderer = identity.get('torch'), identity.get('renderer')
    require(isinstance(torch_profile, dict) and isinstance(renderer, dict), 'retained source runtime environment missing')
    names = {'CUDA_VISIBLE_DEVICES': (torch_profile, 'CUDA_VISIBLE_DEVICES'),
             'CUBLAS_WORKSPACE_CONFIG': (torch_profile, 'CUBLAS_WORKSPACE_CONFIG'),
             'NVIDIA_TF32_OVERRIDE': (torch_profile, 'NVIDIA_TF32_OVERRIDE'),
             'MUJOCO_GL': (renderer, 'requested_backend'),
             'MUJOCO_EGL_DEVICE_ID': (renderer, 'requested_egl_device')}
    environment = {}
    for name, (profile, field) in names.items():
        require(field in profile and (profile[field] is None or isinstance(profile[field], str)),
                f'invalid retained source runtime environment: {name}')
        environment[name] = profile[field]
    for name, value in environment.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value
    return environment


def _operation(seed, source, output, repo, assets, campaign_root):
    from palimpsest.engine import Engine
    from palimpsest.snapshots import capture, read_snapshot, save_snapshot
    from palimpsest.records import iter_ticks
    from palimpsest.replay import replay_run
    row, meta, recording = _source(seed, source)
    before = _hashes(recording.parent)
    budget = _budget(output, campaign_root)
    metrics = {}
    def timed(name, fn):
        start = time.perf_counter()
        result = fn()
        metrics[name] = time.perf_counter() - start
        return result
    retained = read_snapshot(Path(meta['snapshot_path']))
    capture_config = _operation_config(seed, meta, recording, retained)
    capture_environment = _bind_operation_environment(retained)
    engine = Engine.open(repo, assets, output / 'capture-owner', **capture_config,
                         max_bytes=64 * MiB, storage_budget=budget)
    try:
        def restore_tick():
            engine.restore_branch(retained)
            _step(engine)
        timed('restore_first_tick_seconds', restore_tick)
        snapshot = timed('capture_seconds', lambda: capture(engine.env, engine.observation, policy=engine.policy,
                                                           application=engine.application_state()))
        target = output / 'captured.snp'
        timed('save_seconds', lambda: save_snapshot(snapshot, target, storage_budget=budget))
        timed('read_seconds', lambda: read_snapshot(target))
    finally:
        engine.close()
    del engine
    gc.collect()
    ticks = timed('playback_seconds', lambda: sum(1 for _ in iter_ticks(recording)))
    reports = {}
    for mode in ('actions', 'policy'):
        destination = output / uuid.uuid4().hex
        destination.mkdir()
        reports[mode] = timed('action_replay_seconds' if mode == 'actions' else 'policy_replay_seconds',
            lambda mode=mode: replay_run(recording.parent, destination, mode=mode, repo_root=repo, asset_root=assets,
                                         storage_budget=budget, recording_max_bytes=64 * MiB))
        require(reports[mode].get('status') == 'passed', f'{mode} replay did not match retained source')
        gc.collect()
    require(before == _hashes(recording.parent), 'retained replay source changed')
    return {'metrics': metrics, 'source': meta, 'capture_owner_config': capture_config, 'capture_owner_environment': capture_environment, 'source_row_sha256': sha256_file(Path(source)),
            'source_hashes_before': before, 'source_hashes_after': _hashes(recording.parent),
            'playback_tick_count': ticks, 'replay_reports': reports,
            'operation_scopes': {'playback_seconds': 'validated stored tick-stream iteration; no policy/physics/rendering',
                                 'restore_first_tick_seconds': 'prefix restore plus one actual policy/physics tick; open excluded',
                                 'action_replay_seconds': 'production action replay including open/close',
                                 'policy_replay_seconds': 'production policy replay including open/close'}}


class ResourceBoundaryError(ValueError):
    def __init__(self, limit, message):
        super().__init__(message)
        self.resource_limit = limit


def _resource_boundary(condition, limit, message):
    if not condition:
        raise ResourceBoundaryError(limit, message)


def _validate_output_resources(output, campaign_root):
    _resource_boundary(_size(output) <= 512 * MiB, 'unit_bytes', 'unit output cap crossed')
    _resource_boundary(_size(campaign_root) <= RESOURCES['campaign_max_output_bytes'], 'campaign_bytes', 'campaign output cap crossed')
    _resource_boundary(shutil.disk_usage(output).free >= 6 * GiB, 'free_space', 'free-space reserve crossed')


def _unit(kind, seed, output, identity, repo, assets, campaign_root, *, condition=None, source=None, campaign_deadline_epoch=None):
    require(type(seed) is int and seed in range(10 if kind == 'execution_overhead' else 5), 'undeclared seed')
    if condition is not None:
        require(condition in CONDITIONS, 'undeclared condition')
    if source is not None:
        source_row, _, _ = _source(seed, source)
        require(identity is None or source_row.get('identity') == identity, 'retained replay campaign identity mismatch')
    descriptor = {'unit_id': f'overhead/{seed}/{condition}' if condition else f'operation_cost/{seed}', 'kind': kind, 'seed': seed}
    if condition:
        descriptor.update(condition=condition, condition_ordinal=condition_order(seed).index(condition))
    row = {'schema_version': 1, 'study_id': 'authority_replay_v1', **descriptor, 'identity': identity or {},
           'status': 'incomplete', 'metrics': {}, 'timing_eligible': False,
           'execution_path': 'cpu-flynn-runtime', 'covariates': host_covariates()}
    prepare_output_root(output)
    campaign_root = Path(campaign_root)
    try:
        require(Path(output).resolve().is_relative_to(campaign_root.resolve()), 'unit must be below campaign root')
        _resource_boundary(shutil.disk_usage(output).free - 512 * MiB >= 6 * GiB, 'free_space', 'free-space reserve prevents unit admission')
        _resource_boundary(_size(campaign_root) + 512 * MiB <= RESOURCES['campaign_max_output_bytes'], 'campaign_bytes', 'campaign output cap prevents unit admission')
        require(campaign_deadline_epoch is None or time.time() < campaign_deadline_epoch, 'campaign deadline prevents unit admission')
        timeout = min(900., max(0., campaign_deadline_epoch - time.time())) if campaign_deadline_epoch else 900.
        config = {'kind': kind, 'seed': seed, 'condition': condition, 'source': str(source) if source else None,
                  'output': str(Path(output).resolve()), 'repo': str(Path(repo).resolve()), 'assets': str(Path(assets).resolve()),
                  'campaign_root': str(campaign_root.resolve())}
        _json(output / 'worker-config.json', config)
        with (output / 'stdout.log').open('wb') as stdout, (output / 'stderr.log').open('wb') as stderr:
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--worker', str(output / 'worker-config.json')],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            overflow = threading.Event()
            def spool(pipe, log):
                retained = 0
                while data := pipe.read(65536):
                    remaining = max(0, MiB - retained)
                    log.write(data[:remaining])
                    retained += min(remaining, len(data))
                    if len(data) > remaining:
                        overflow.set()
                pipe.close()
            drains = [threading.Thread(target=spool, args=(pipe, log), daemon=True)
                      for pipe, log in ((child.stdout, stdout), (child.stderr, stderr))]
            for drain in drains:
                drain.start()
            start = time.monotonic()
            try:
                while child.poll() is None:
                    if time.monotonic() - start >= timeout:
                        raise subprocess.TimeoutExpired(child.args, timeout)
                    require(not overflow.is_set(), 'native log cap crossed')
                    _validate_output_resources(output, campaign_root)
                    time.sleep(.1)
            finally:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                for drain in drains:
                    drain.join()
        require(not overflow.is_set(), 'native log cap crossed')
        require(child.returncode == 0, f'worker failed ({child.returncode}); see stderr.log')
        result = json.loads((output / 'worker-result.json').read_text())
        # A fast child can exit between monitor polls; final acceptance includes
        # drained logs and the retained result, not just observed running state.
        _validate_output_resources(output, campaign_root)
        if time.monotonic() - start >= timeout or (campaign_deadline_epoch is not None and time.time() >= campaign_deadline_epoch):
            raise subprocess.TimeoutExpired(child.args, timeout)
        row.update(result, status='completed')
        if kind == 'operation_cost':
            row['timing_eligible'] = True
    except subprocess.TimeoutExpired as exc:
        row.update(status='timeout', error={'type': type(exc).__name__, 'message': str(exc)})
    except Exception as exc:
        error = {'type': type(exc).__name__, 'message': str(exc)}
        if isinstance(exc, ResourceBoundaryError):
            error['resource_limit'] = exc.resource_limit
        row.update(status='failed', error=error)
    row['metrics']['output_bytes'] = _size(output)
    validate_finite(row)
    return row


def run_execution_overhead_unit(seed, condition, *, output, identity=None, repo=REPO, assets=None, campaign_root=None, campaign_deadline_epoch=None):
    return _unit('execution_overhead', seed, Path(output), identity, repo, assets,
                 campaign_root or Path(output).parent, condition=condition, campaign_deadline_epoch=campaign_deadline_epoch)


def run_operation_cost_unit(seed, source, *, output, identity=None, repo=REPO, assets=None, campaign_root=None, campaign_deadline_epoch=None):
    return _unit('operation_cost', seed, Path(output), identity, repo, assets,
                 campaign_root or Path(output).parent, source=Path(source), campaign_deadline_epoch=campaign_deadline_epoch)


def campaign_deadline(root, identity, override=None):
    """Persist/reuse the shared four-hour clock; overrides can only shorten it."""
    path = Path(root) / 'campaign-clock.json'
    try:
        with path.open('x') as stream:
            now = time.time()
            json.dump({'identity': identity, 'started_unix': now, 'deadline_unix': now + 14400}, stream)
            stream.write('\n')
    except FileExistsError:
        pass
    clock = json.loads(path.read_text())
    validate_finite(clock)
    require(clock['identity'] == identity, 'shared campaign clock identity drift')
    require(type(clock['started_unix']) in (int, float) and type(clock['deadline_unix']) in (int, float)
            and 0 < clock['deadline_unix'] - clock['started_unix'] <= 14400, 'invalid shared campaign clock')
    if override is not None:
        validate_finite(override)
    return min(clock['deadline_unix'], override) if override is not None else clock['deadline_unix']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=['execution', 'operation', 'operations'])
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--assets', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--sources', '--replay-root', dest='sources', type=Path, help='Replay root containing seed-{seed}/row.json')
    parser.add_argument('--campaign-root', type=Path, help='Shared aggregate raw-output root')
    parser.add_argument('--campaign-deadline-epoch', type=float, help='Absolute global campaign deadline; shared manifest deadline also honored')
    parser.add_argument('--self-check', action='store_true')
    parser.add_argument('--worker', type=Path)
    args = parser.parse_args()
    if args.kind == 'operations':
        args.kind = 'operation'
    if args.worker:
        config = json.loads(args.worker.read_text())
        call = _execution if config['kind'] == 'execution_overhead' else _operation
        result = call(config['seed'], config['condition'] if call is _execution else Path(config['source']),
                      Path(config['output']), Path(config['repo']), Path(config['assets']), Path(config['campaign_root']))
        _json(Path(config['output']) / 'worker-result.json', result)
        return 0
    if not args.protocol:
        parser.error('--protocol required')
    protocol = load_protocol(args.protocol)
    if args.self_check:
        print('PASS: overhead protocol/static contract; no model executed')
        return 0
    if not (args.kind and args.assets and args.output) or args.kind == 'operation' and not args.sources:
        parser.error('--kind --assets --output required; operation also requires --sources')
    identity = campaign_identity(REPO, args.protocol, args.assets)
    prepare_output_root(args.output)
    campaign_root = args.campaign_root or args.output.parent
    _json(args.output / 'identity.json', identity)
    _json(args.output / 'invocation.json', {'argv': sys.argv, 'python': sys.version, 'executable': sys.executable,
                                          'environment': {k: os.environ.get(k) for k in ('PYTHONPATH', 'MUJOCO_GL', 'OMP_NUM_THREADS')}})
    deadline = campaign_deadline(campaign_root, identity, args.campaign_deadline_epoch)
    stopped = None
    kind = 'execution_overhead' if args.kind == 'execution' else 'operation_cost'
    units = [u for u in declared_units(protocol) if u['kind'] == kind]
    successful = True
    for seed in getattr(protocol, kind)['seeds']:
        rows = []
        for unit in [u for u in units if u['seed'] == seed]:
            if time.time() >= deadline:
                stopped = 'campaign wall-clock cap reached'
            if stopped:
                row = {'schema_version': 1, 'study_id': protocol.study_id, **unit, 'identity': identity,
                       'status': 'incomplete', 'metrics': {}, 'reason': stopped, 'timing_eligible': False}
            else:
                kwargs = dict(output=args.output / unit['unit_id'].replace('/', '__'), identity=identity,
                              assets=args.assets, campaign_root=campaign_root, campaign_deadline_epoch=deadline)
                try:
                    if kind == 'execution_overhead':
                        row = run_execution_overhead_unit(seed, unit['condition'], **kwargs)
                    else:
                        row = run_operation_cost_unit(seed, args.sources / f'seed-{seed}' / 'row.json', **kwargs)
                except (OSError, ValueError, KeyError) as exc:
                    row = {'schema_version': 1, 'study_id': protocol.study_id, **unit, 'identity': identity,
                           'status': 'refused', 'metrics': {}, 'timing_eligible': False,
                           'error': {'type': type(exc).__name__, 'message': str(exc)}}
                try:
                    require(campaign_identity(REPO, args.protocol, args.assets) == identity, 'source identity drift')
                except Exception as exc:
                    row.update(status='failed', timing_eligible=False, error={'type': 'SourceMutation', 'message': str(exc)})
                    stopped = str(exc)
                if row['status'] == 'timeout' or row.get('error', {}).get('type') == 'ValueError' or row.get('error', {}).get('resource_limit'):
                    stopped = 'unit hard cap or admission failure; no further units'
            rows.append(row)
        if kind == 'execution_overhead':
            match_seed(rows)
        successful = successful and all(r['status'] == 'completed' and r.get('timing_eligible') is True for r in rows)
        for row in rows:
            append_row(args.output / 'rows.jsonl', row)
            _json(args.output / f"{row['unit_id'].replace('/', '__')}.json", row)
    return int(not successful)


if __name__ == '__main__':
    raise SystemExit(main())
