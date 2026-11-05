import copy
from pathlib import Path
import pytest
from paper.studies.authority_replay_v1 import overhead as o
from paper.studies.authority_replay_v1.null_writer import NullWriter


@pytest.mark.parametrize('field', ['actions_sha256', 'tick_count', 'final_state_sha256'])
def test_whole_seed_exclusion(field):
    rows = [dict(seed=0, condition=c, status='completed', metrics={}, actions_sha256='a', tick_count=220,
                 final_state_sha256='f') for c in o.CONDITIONS]
    rows[-1][field] = 'different'
    assert not o.match_seed(rows)
    assert all(r['timing_eligible'] is False for r in rows)


def test_match_and_nonfinite():
    rows = [dict(seed=0, condition=c, status='completed', metrics={'wall_seconds': 1.}, actions_sha256='a',
                 tick_count=220, final_state_sha256='f') for c in o.CONDITIONS]
    assert o.match_seed(rows)
    rows[0]['metrics']['wall_seconds'] = float('nan')
    with pytest.raises(ValueError, match='finite'):
        o.match_seed(rows)


def test_rotation():
    assert [o.condition_order(i) for i in range(4)] == [o.CONDITIONS[i:] + o.CONDITIONS[:i] for i in range(4)]


@pytest.mark.parametrize('condition', o.CONDITIONS)
def test_writer_dispatch(tmp_path, condition, monkeypatch):
    from collections import namedtuple
    disk = namedtuple("disk", "total used free")
    monkeypatch.setattr(o.shutil, "disk_usage", lambda _: disk(100 * o.GiB, 0, 100 * o.GiB))
    writer = o.make_writer(condition, tmp_path / condition, {})
    try:
        assert isinstance(writer, NullWriter) == (condition == 'null')
        assert (writer.background_stats() is not None) == condition.startswith('background')
        assert (writer.storage_budget is not None) == (condition == 'background_storage')
    finally:
        writer.close()


class FakeEngine:
    def __init__(self):
        self.total_tick = 0
        self.last_transition = {}
        self.writer = type('Writer', (), {'flush': lambda s: None, 'background_stats': lambda s: None})()
    def advance(self):
        self.total_tick += 1
        self.last_transition = {'action': [self.total_tick, 0], 'latency': .01, 'step_latency': .02}


@pytest.mark.parametrize('terminal_tick,phase', [(10, 'terminated'), (199, 'terminated'), (199, 'truncated')])
def test_sustained_window_explicit_same_seed_reset(terminal_tick, phase, monkeypatch):
    clock = [0.]
    monkeypatch.setattr(o.time, 'perf_counter', lambda: clock[0])
    class Episodic(FakeEngine):
        def __init__(self):
            super().__init__()
            self.phase, self.episode, self.revision, self.seed = 'paused', 0, 0, 1
            self.commands, self.queued = [], None
            self.last_outcome = {'reason': 'goal' if phase == 'terminated' else 'time_limit'}
        def submit(self, command):
            self.commands.append(command)
            self.queued = command
            return {'status': 'queued'}
        def advance(self):
            command = self.queued
            if command['kind'] == 'reset':
                assert command['payload'] == {'seed': 1}
                self.episode += 1
                self.phase = 'paused'
                clock[0] += 3.
                return
            assert self.phase == 'paused'
            super().advance()
            clock[0] += 1.
            if self.total_tick == terminal_tick:
                self.phase = phase
    engine = Episodic()
    result = o.measure_ticks(engine)
    assert result['tick_count'] == 220
    assert len({c['id'] for c in engine.commands}) == len(engine.commands)
    assert result['reset_counts'] == {'warmup': int(terminal_tick < 20), 'measured': int(terminal_tick >= 20)}
    assert result['metrics']['reset_seconds'] == (3. if terminal_tick >= 20 else 0.)
    assert result['metrics']['wall_seconds'] == (203. if terminal_tick >= 20 else 200.)
    assert result['reset_events'][0]['reason'] in ('goal', 'time_limit')


@pytest.mark.parametrize('phase', ['failed', 'stopped'])
def test_failed_or_stopped_engine_never_reset(phase):
    engine = FakeEngine()
    engine.phase = phase
    engine.submit = lambda command: pytest.fail('failed/stopped engine must not receive reset or step')
    with pytest.raises(ValueError, match='failed|stopped'):
        o._step(engine)


@pytest.mark.parametrize('error_type,message', [('StorageLimitError', 'quota exceeded'),
    ('RuntimeError', 'Recording quota exceeded before publication'), ('OSError', 'disk full')])
def test_swallowed_storage_error_keeps_resource_boundary(error_type, message):
    engine = FakeEngine()
    def failed_advance():
        engine.phase = 'failed'
        engine.last_outcome = {'reason': 'runtime_failure', 'type': error_type, 'message': message}
    engine.advance = failed_advance
    with pytest.raises(o.ResourceBoundaryError, match=message):
        o._step(engine)


def test_exact_tick_window():
    engine = FakeEngine()
    result = o.measure_ticks(engine)
    assert engine.total_tick == result['tick_count'] == 220
    assert result['measured_tick_count'] == 200
    assert result['metrics']['policy_seconds'] == pytest.approx(2.)
    assert result['metrics']['physics_seconds'] == pytest.approx(4.)
    assert result['metrics']['wall_seconds_per_tick'] == result['metrics']['wall_seconds'] / 200


def test_null_writer_lifecycle(tmp_path):
    writer = NullWriter(tmp_path / 'null', {'run_id': 'null'})
    writer.event('anything', value=1)
    writer.tick(0, 0, action=[0, 1])
    writer.flush()
    writer.finish({'total_tick': 1}, status='completed')
    writer.close()
    assert writer.manifest['status'] == 'completed'
    assert list(writer.path.iterdir()) == [writer.path / 'events.jsonl']
    assert (writer.path / 'events.jsonl').read_bytes() == b''
    with pytest.raises(ValueError):
        writer.tick(0, 1, action=[0, 1])


def test_operations_reject_null_source_before_runtime(tmp_path):
    (tmp_path / 'manifest.json').write_text('{"status":"completed"}')
    with pytest.raises(ValueError, match='retained.*replay|full.writer'):
        o.run_operation_cost_unit(0, tmp_path, output=tmp_path / 'dest')


def test_failed_condition_excludes_whole_seed():
    rows = [dict(seed=0, condition=c, status='completed', metrics={}, actions_sha256='a', tick_count=220,
                 final_state_sha256='f') for c in o.CONDITIONS]
    rows[-1]['status'] = 'timeout'
    assert not o.match_seed(rows)
    assert all(not r['timing_eligible'] for r in rows)
    with pytest.raises(ValueError, match='four distinct'):
        o.match_seed(rows[:-1])


def test_source_requires_explicit_replay_provenance(tmp_path):
    run = tmp_path / ('a' * 32)
    recording = run / 'recording'
    recording.mkdir(parents=True)
    (recording / 'manifest.json').write_text('{"status":"completed"}')
    snapshot = run / 'prefix.snp'
    snapshot.write_bytes(b'source fixture')
    row = {'kind': 'replay', 'status': 'completed', 'seed': 0,
           'source': {'seed': 0, 'condition': 'background_storage', 'recording_writer': 'background',
                      'storage_accounting': True, 'prefix_ticks': 8, 'source_ticks': 100, 'run_path': str(run), 'snapshot_path': str(snapshot)}}
    source = tmp_path / 'row.json'
    import json
    source.write_text(json.dumps(row))
    assert o._source(0, source)[2] == recording
    row['source']['condition'] = 'null'
    source.write_text(json.dumps(row))
    with pytest.raises(ValueError, match='full-writer'):
        o._source(0, source)


def test_execution_fixture_real_writers(tmp_path, monkeypatch):
    from palimpsest.engine import Engine
    from palimpsest import records
    import numpy as np
    from collections import namedtuple
    disk = namedtuple('disk', 'total used free')
    monkeypatch.setattr(o.shutil, 'disk_usage', lambda _: disk(100 * o.GiB, 0, 100 * o.GiB))
    class Fixture(FakeEngine):
        def __init__(self, writer):
            super().__init__()
            self.writer = writer
            self.env = type('Env', (), {'_render_camera': lambda s: None})()
        def advance(self):
            super().advance()
            self.env._render_camera()
            self.writer.tick(0, self.total_tick - 1, action=np.asarray(self.last_transition['action']))
        def close(self):
            self.writer.finish({'total_tick': self.total_tick})
            self.writer.close()
    def opened(repo, assets, output, **kwargs):
        return Fixture(records.RunWriter(output, {}, max_bytes=kwargs['max_bytes']))
    monkeypatch.setattr(Engine, 'open', opened)
    monkeypatch.setattr(o, '_final_digest', lambda e, **kwargs: str(e.total_tick))
    rows = []
    for condition in o.CONDITIONS:
        output = tmp_path / condition
        output.mkdir()
        result = o._execution(0, condition, output, tmp_path, tmp_path, tmp_path)
        rows.append({'seed': 0, 'condition': condition, 'status': 'completed', **result})
        assert result['tick_count'] == 220
        assert result['metrics']['open_seconds'] >= 0
        assert result['metrics']['close_seconds'] >= 0
        assert result['metrics']['camera_seconds'] >= 0
        assert (result['metrics']['bytes_per_tick'] == 0) == (condition == 'null')
    assert o.match_seed(rows)
    assert rows[-1]['metrics']['storage_recount_count'] >= 0


def test_expired_global_deadline_prevents_process_start(tmp_path, monkeypatch):
    from collections import namedtuple
    disk = namedtuple('disk', 'total used free')
    monkeypatch.setattr(o.shutil, 'disk_usage', lambda _: disk(100 * o.GiB, 0, 100 * o.GiB))
    def forbidden(*args, **kwargs):
        pytest.fail('expired campaign must not launch a child')
    monkeypatch.setattr(o.subprocess, 'Popen', forbidden)
    row = o.run_execution_overhead_unit(0, 'null', output=tmp_path / 'unit', assets=tmp_path,
                                         campaign_root=tmp_path, campaign_deadline_epoch=1.)
    assert row['status'] == 'failed'
    assert 'deadline' in row['error']['message']
    assert row['timing_eligible'] is False


def test_unit_must_be_below_shared_campaign_root(tmp_path):
    row = o.run_execution_overhead_unit(0, 'null', output=tmp_path / 'unit', assets=tmp_path,
                                         campaign_root=tmp_path / 'different')
    assert row['status'] == 'failed'
    assert 'below campaign root' in row['error']['message']


def test_persisted_campaign_clock_cannot_extend(tmp_path, monkeypatch):
    monkeypatch.setattr(o.time, 'time', lambda: 100.)
    identity = {'commit': 'fixture'}
    assert o.campaign_deadline(tmp_path, identity) == 14500.
    monkeypatch.setattr(o.time, 'time', lambda: 1000.)
    assert o.campaign_deadline(tmp_path, identity, 99999.) == 14500.
    assert o.campaign_deadline(tmp_path, identity, 2000.) == 2000.
    with pytest.raises(ValueError, match='identity drift'):
        o.campaign_deadline(tmp_path, {'commit': 'different'})


@pytest.mark.parametrize('rng_field', ['environment', 'spaces', 'python', 'numpy', 'torch_cpu'])
def test_rng_divergence_excludes_entire_seed(monkeypatch, rng_field):
    from palimpsest import snapshots
    state = {'rng': {name: [1, 2, 3] for name in ['environment', 'spaces', 'python', 'numpy', 'torch_cpu']},
             'application': {'source_run_id': 'recorder', 'event_prefix': {}, 'tick': 220}, 'policy': [4, 5]}
    native = _native_fixture()
    state.update({key: native[key] for key in ('native_data', 'native_sha256')})
    monkeypatch.setattr(snapshots, 'capture', lambda *args, **kwargs: copy.deepcopy(state))
    engine = type('Engine', (), {'env': None, 'observation': None, 'policy': None, 'application_state': lambda _: {}})()
    original = o._final_digest(engine)
    state['rng'][rng_field][-1] += 1
    divergent = o._final_digest(engine)
    rows = [dict(seed=0, condition=c, status='completed', metrics={}, actions_sha256='a', tick_count=220,
                 final_state_sha256=divergent if i == 3 else original) for i, c in enumerate(o.CONDITIONS)]
    assert not o.match_seed(rows)
    assert all(r['timing_eligible'] is False for r in rows)


@pytest.mark.parametrize('boundary', ['unit_bytes', 'campaign_bytes', 'free_space', 'campaign_deadline', 'unit_timeout'])
def test_fast_successful_child_must_pass_final_boundaries(tmp_path, monkeypatch, boundary):
    import io
    import json
    from collections import namedtuple
    disk = namedtuple('disk', 'total used free')
    launched = False
    output = tmp_path / 'unit'
    def size(path):
        if launched and boundary == 'unit_bytes' and Path(path) == output:
            return 512 * o.MiB + 1
        if launched and boundary == 'campaign_bytes' and Path(path) == tmp_path:
            return 16 * o.GiB + 1
        return 0
    def free(path):
        return disk(100 * o.GiB, 0, 5 * o.GiB if launched and boundary == 'free_space' else 100 * o.GiB)
    class FastChild:
        def __init__(self, *args, **kwargs):
            nonlocal launched
            launched = True
            self.args, self.returncode = args, 0
            self.stdout, self.stderr = io.BytesIO(), io.BytesIO()
            (output / 'worker-result.json').write_text(json.dumps({'metrics': {'wall_seconds': 1.}}))
        def poll(self):
            return 0
    monkeypatch.setattr(o, '_size', size)
    monkeypatch.setattr(o.shutil, 'disk_usage', free)
    monkeypatch.setattr(o.subprocess, 'Popen', FastChild)
    monkeypatch.setattr(o.time, 'time', lambda: 2000. if launched and boundary == 'campaign_deadline' else 1000.)
    times = iter([0., 901. if boundary == 'unit_timeout' else 1.])
    monkeypatch.setattr(o.time, 'monotonic', lambda: next(times))
    row = o.run_execution_overhead_unit(0, 'null', output=output, assets=tmp_path,
                                         campaign_root=tmp_path, campaign_deadline_epoch=None if boundary == 'unit_timeout' else 1500.)
    assert launched
    assert row['status'] in ('failed', 'timeout')
    assert row['timing_eligible'] is False
    assert row.get('error')
    if boundary in ('unit_bytes', 'campaign_bytes', 'free_space'):
        assert row['error']['resource_limit'] == boundary


def test_cap_specific_failure_stops_remaining_declared_units(tmp_path, monkeypatch):
    from paper.studies.authority_replay_v1.common import read_rows
    calls = []
    identity = {'commit': 'fixture-only'}
    def failed(seed, condition, **kwargs):
        calls.append((seed, condition))
        return {'schema_version': 1, 'study_id': 'authority_replay_v1', 'kind': 'execution_overhead',
                'seed': seed, 'condition': condition, 'condition_ordinal': o.condition_order(seed).index(condition),
                'unit_id': f'overhead/{seed}/{condition}', 'identity': identity, 'status': 'failed',
                'timing_eligible': False, 'metrics': {},
                'error': {'type': 'ResourceBoundaryError', 'resource_limit': 'unit_bytes', 'message': 'unit output cap crossed'}}
    monkeypatch.setattr(o, 'run_execution_overhead_unit', failed)
    monkeypatch.setattr(o, 'campaign_identity', lambda *args: identity)
    output = tmp_path / 'overhead'
    monkeypatch.setattr(o.sys, 'argv', ['overhead.py', '--kind', 'execution', '--protocol',
                        str(o.REPO / 'paper/studies/authority_replay_v1/protocol.json'), '--assets', str(tmp_path),
                        '--output', str(output), '--campaign-root', str(tmp_path)])
    assert o.main() == 1
    rows = read_rows(output / 'rows.jsonl')
    assert len(calls) == 1
    assert len(rows) == 40
    assert all(row['status'] == 'incomplete' for row in rows[1:])
    assert all(not row['timing_eligible'] for row in rows)


def test_ordinary_valueerror_continues_all_conditions_and_seeds(tmp_path, monkeypatch):
    from paper.studies.authority_replay_v1.common import read_rows
    identity, calls = {'commit': 'fixture'}, []
    def failed(seed, condition, **kwargs):
        calls.append((seed, condition))
        return {'schema_version': 1, 'study_id': 'authority_replay_v1', 'kind': 'execution_overhead',
                'seed': seed, 'condition': condition, 'unit_id': f'overhead/{seed}/{condition}',
                'identity': identity, 'status': 'failed', 'timing_eligible': False, 'metrics': {},
                'error': {'type': 'ValueError', 'message': 'scientific disagreement'}}
    monkeypatch.setattr(o, 'run_execution_overhead_unit', failed)
    monkeypatch.setattr(o, 'campaign_identity', lambda *args: identity)
    output = tmp_path / 'overhead'
    monkeypatch.setattr(o.sys, 'argv', ['overhead.py', '--kind', 'execution', '--protocol',
                        str(o.REPO / 'paper/studies/authority_replay_v1/protocol.json'), '--assets', str(tmp_path),
                        '--output', str(output), '--campaign-root', str(tmp_path)])
    assert o.main() == 1
    assert len(calls) == 40
    assert all(r['status'] == 'failed' for r in read_rows(output / 'rows.jsonl'))


@pytest.mark.parametrize('boundary', [False, True])
def test_worker_structured_error_retains_original_type(tmp_path, monkeypatch, boundary):
    import io
    import json
    output = tmp_path / 'unit'
    monkeypatch.setattr(o.shutil, 'disk_usage', lambda _: type('Disk', (), {'free': 100 * o.GiB})())
    class FailedChild:
        def __init__(self, *args, **kwargs):
            self.args, self.returncode = args, 1
            self.stdout, self.stderr = io.BytesIO(), io.BytesIO()
            (output / 'worker-error.json').write_text(json.dumps({'error_type': 'StorageLimitError' if boundary else 'ValueError',
                'message': 'fixture failure', 'resource_boundary': boundary, **({'resource_limit': 'worker_resource'} if boundary else {})}))
        def poll(self):
            return 1
    monkeypatch.setattr(o.subprocess, 'Popen', FailedChild)
    row = o.run_execution_overhead_unit(0, 'null', output=output, assets=tmp_path, campaign_root=tmp_path)
    assert row['status'] == 'failed'
    assert row['error']['type'] == ('StorageLimitError' if boundary else 'ValueError')
    assert bool(row['error'].get('resource_limit')) == boundary
    assert row['metrics']['output_bytes'] > 0


def test_unclassified_native_crash_stops_admission(tmp_path, monkeypatch):
    import io
    output = tmp_path / 'unit'
    monkeypatch.setattr(o.shutil, 'disk_usage', lambda _: type('Disk', (), {'free': 100 * o.GiB})())
    class CrashedChild:
        def __init__(self, *args, **kwargs):
            self.args, self.returncode = args, -9
            self.stdout, self.stderr = io.BytesIO(), io.BytesIO()
        def poll(self):
            return -9
    monkeypatch.setattr(o.subprocess, 'Popen', CrashedChild)
    row = o.run_execution_overhead_unit(0, 'null', output=output, assets=tmp_path, campaign_root=tmp_path)
    assert row['status'] == 'failed'
    assert row['error']['type'] == 'WorkerProcessError'
    assert row['error']['resource_limit'] == 'unclassified_worker_failure'


def test_direct_writer_quota_and_chained_resource_errors_stop():
    assert o._is_resource_failure(RuntimeError('Recording quota exceeded before publication'))
    assert o._is_resource_failure(RuntimeError('Background recording write failed'))
    assert not o._is_resource_failure(ValueError('scientific mismatch'))
    error = RuntimeError('wrapped writer error')
    error.__cause__ = OSError(28, 'disk full')
    assert o._is_resource_failure(error)


def test_development_diagnostics_preserve_complete_normalized_state(tmp_path, monkeypatch):
    from palimpsest import snapshots
    import json
    state = {'rng': {'python': [1, 2, 3], 'environment': {'state': 5}},
             'application': {'source_run_id': 'recorder', 'event_prefix': {}, 'tick': 220}, 'policy': [4, 5]}
    native = _native_fixture(timer=3.)
    state.update({key: native[key] for key in ('native_data', 'native_sha256')})
    monkeypatch.setattr(snapshots, 'capture', lambda *args, **kwargs: copy.deepcopy(state))
    engine = type('Engine', (), {'env': None, 'observation': None, 'policy': None, 'application_state': lambda _: {}})()
    expected = o._final_digest(engine)
    snapshot = tmp_path / 'final-normalized.snp'
    metadata = {}
    actual = o._final_digest(engine, diagnostics=(snapshot, None), metadata=metadata)
    restored = snapshots.read_snapshot(snapshot)
    assert restored['rng'] == state['rng']
    assert restored['policy'] == state['policy']
    assert restored['application'] == {'tick': 220}
    assert actual == expected == snapshots.state_digest(restored)
    digests = json.loads((tmp_path / 'final-component-digests.json').read_text())
    assert digests['rng']['environment'] == snapshots.state_digest(state['rng']['environment'])
    assert set(digests['components']) == set(restored)
    raw = snapshots.read_snapshot(tmp_path / 'final-raw.snp')
    assert raw['application'] == state['application']
    assert raw['native_data'] == state['native_data']
    assert metadata['raw_native_sha256'] != metadata['matched_native_sha256']
    assert metadata['final_state_normalization']['native_fields'] == ['timer.duration']
    assert raw['rng'] == restored['rng']


def _native_fixture(timer=0., native_cache=0.):
    import hashlib
    import mujoco
    import numpy as np
    model = mujoco.MjModel.from_xml_string('<mujoco><worldbody><body><joint type="slide"/><geom type="sphere" size=".1" mass="1"/></body></worldbody></mujoco>')
    data = mujoco.MjData(model)
    data.timer.duration[:] = timer
    data.qacc[0] = native_cache
    native = data.__getstate__()
    return {'native_data': native, 'native_sha256': hashlib.sha256(native).hexdigest(),
            'integration': np.array([0., 0.]), 'policy': np.array([1., 2.]), 'rng': {'python': [1, 2, 3]},
            'application': {'source_run_id': 'recorder', 'event_prefix': {}, 'tick': 220}}


def test_timer_durations_only_normalize_on_private_native_copy(monkeypatch):
    from palimpsest import snapshots
    state = _native_fixture(timer=1.)
    before = copy.deepcopy(state)
    monkeypatch.setattr(snapshots, 'capture', lambda *args, **kwargs: copy.deepcopy(state))
    engine = type('Engine', (), {'env': None, 'observation': None, 'policy': None, 'application_state': lambda _: {}})()
    first = o._final_digest(engine)
    state = _native_fixture(timer=2.)
    assert before['native_data'] != state['native_data']
    assert o._final_digest(engine) == first
    assert state['native_data'] == _native_fixture(timer=2.)['native_data']


@pytest.mark.parametrize('field', ['integration', 'policy', 'rng', 'native_cache'])
def test_non_timer_continuation_state_remains_in_match(monkeypatch, field):
    from palimpsest import snapshots
    state = _native_fixture(timer=1.)
    monkeypatch.setattr(snapshots, 'capture', lambda *args, **kwargs: copy.deepcopy(state))
    engine = type('Engine', (), {'env': None, 'observation': None, 'policy': None, 'application_state': lambda _: {}})()
    first = o._final_digest(engine)
    if field in ('integration', 'policy'):
        state[field][0] += 1
    elif field == 'rng':
        state['rng']['python'][0] += 1
    else:
        state = _native_fixture(timer=1., native_cache=1.)
    assert o._final_digest(engine) != first


def test_planned_operations_cli_uses_actual_repeatability_seed_paths(tmp_path, monkeypatch):
    from paper.studies.authority_replay_v1.common import read_rows
    sources = tmp_path / 'replay'
    output = tmp_path / 'operations'
    identity = {'commit': 'fixture-only'}
    calls = []
    def completed(seed, source, **kwargs):
        calls.append((seed, source))
        return {'schema_version': 1, 'study_id': 'authority_replay_v1', 'kind': 'operation_cost', 'seed': seed,
                'unit_id': f'operation_cost/{seed}', 'identity': identity, 'status': 'completed',
                'timing_eligible': True, 'metrics': {}}
    monkeypatch.setattr(o, 'run_operation_cost_unit', completed)
    monkeypatch.setattr(o, 'campaign_identity', lambda *args: identity)
    monkeypatch.setattr(o.sys, 'argv', ['overhead.py', '--kind', 'operations', '--protocol',
                        str(o.REPO / 'paper/studies/authority_replay_v1/protocol.json'), '--assets', str(tmp_path),
                        '--output', str(output), '--replay-root', str(sources)])
    assert o.main() == 0
    assert calls == [(seed, sources / f'seed-{seed}' / 'row.json') for seed in range(5)]
    assert len(read_rows(output / 'rows.jsonl')) == 5


def _operation_source_fixture(tmp_path):
    import json
    owner = tmp_path / ('a' * 32)
    recording = owner / 'recording'
    recording.mkdir(parents=True)
    manifest = {'status': 'completed', 'run_id': owner.name, 'controller': 'flynn', 'profile': 'flynn',
                'requested_device': 'cpu', 'seed': 0, 'texture': 'checker',
                'scenario': {'id': 'vision-ablation', 'controller': 'flynn', 'texture': 'checker'}}
    (recording / 'manifest.json').write_text(json.dumps(manifest))
    meta = {'run_path': str(owner), 'snapshot_path': str(owner / 'prefix.snp'), 'seed': 0,
            'condition': 'background_storage', 'recording_writer': 'background', 'storage_accounting': True,
            'prefix_ticks': 8, 'source_ticks': 100}
    retained = {'identity': {'torch': {'CUDA_VISIBLE_DEVICES': '', 'CUBLAS_WORKSPACE_CONFIG': None,
                                      'NVIDIA_TF32_OVERRIDE': None},
                             'renderer': {'requested_backend': 'egl', 'requested_egl_device': None}},
                'application': {'source_run_id': owner.name, 'controller': 'flynn', 'scenario': 'vision-ablation',
                               'texture': 'checker', 'seed': 0, 'total_tick': 8, 'phase': 'paused',
                               'eyes': {'left': False, 'right': True}}}
    return recording, manifest, meta, retained


def test_operation_capture_owner_uses_exact_retained_source_profile(tmp_path, monkeypatch):
    for name in ('CUDA_VISIBLE_DEVICES', 'CUBLAS_WORKSPACE_CONFIG', 'NVIDIA_TF32_OVERRIDE', 'MUJOCO_GL', 'MUJOCO_EGL_DEVICE_ID'):
        if name in o.os.environ:
            monkeypatch.setenv(name, o.os.environ[name])
        else:
            monkeypatch.delenv(name, raising=False)
    from palimpsest.engine import Engine
    from palimpsest import snapshots
    recording, manifest, meta, retained = _operation_source_fixture(tmp_path)
    monkeypatch.setattr(o, '_source', lambda *args: ({}, meta, recording))
    monkeypatch.setattr(o, '_budget', lambda *args: None)
    monkeypatch.setattr(snapshots, 'read_snapshot', lambda *args: retained)
    def opened(repo, assets, output, **config):
        assert {key: config[key] for key in ('controller', 'scenario', 'texture', 'seed', 'device')} == {
            'controller': 'flynn', 'scenario': 'vision-ablation', 'texture': 'checker', 'seed': 0, 'device': 'cpu'}
        raise RuntimeError('fixture stops after compatible owner config')
    monkeypatch.setattr(Engine, 'open', opened)
    with pytest.raises(RuntimeError, match='fixture stops'):
        o._operation(0, tmp_path / 'source-row.json', tmp_path / 'output', tmp_path, tmp_path, tmp_path)


@pytest.mark.parametrize('field,value', [('scenario', 'sparse-navigation'), ('controller', 'manual'),
                                        ('texture', 'realistic'), ('seed', 1), ('source_run_id', 'b' * 32)])
def test_operation_rejects_incompatible_snapshot_before_owner(tmp_path, monkeypatch, field, value):
    from palimpsest.engine import Engine
    from palimpsest import snapshots
    recording, manifest, meta, retained = _operation_source_fixture(tmp_path)
    retained['application'][field] = value
    monkeypatch.setattr(o, '_source', lambda *args: ({}, meta, recording))
    monkeypatch.setattr(o, '_budget', lambda *args: None)
    monkeypatch.setattr(snapshots, 'read_snapshot', lambda *args: retained)
    monkeypatch.setattr(Engine, 'open', lambda *args, **kwargs: pytest.fail('incompatible source must refuse before owner open'))
    with pytest.raises(ValueError, match='source.*config|snapshot.*config|snapshot.*identity'):
        o._operation(0, tmp_path / 'source-row.json', tmp_path / 'output', tmp_path, tmp_path, tmp_path)


@pytest.mark.parametrize('field,value', [('seed', 1), ('profile', 'manual'), ('requested_device', 'cuda'),
                                        ('controller', 'manual'), ('texture', 'realistic')])
def test_operation_config_rejects_inconsistent_manifest_profile(tmp_path, field, value):
    import json
    recording, manifest, meta, retained = _operation_source_fixture(tmp_path)
    manifest[field] = value
    (recording / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='source config mismatch'):
        o._operation_config(0, meta, recording, retained)


def test_campaign_budget_loads_amended_protocol(tmp_path, monkeypatch):
    monkeypatch.setattr(o.shutil, 'disk_usage', lambda _: type('Disk', (), {'free': 100 * o.GiB})())
    budget = o._budget(tmp_path / 'unit', tmp_path)
    assert budget.campaign_budget.limits.max_bytes == 12 * o.GiB


def test_operation_binds_retained_cpu_environment_before_owner_open(tmp_path, monkeypatch):
    from palimpsest.engine import Engine
    from palimpsest import snapshots
    recording, manifest, meta, retained = _operation_source_fixture(tmp_path)
    retained['identity'] = {'torch': {'CUDA_VISIBLE_DEVICES': '', 'CUBLAS_WORKSPACE_CONFIG': None,
                                    'NVIDIA_TF32_OVERRIDE': None},
                            'renderer': {'requested_backend': 'egl', 'requested_egl_device': None}}
    inherited = {'CUDA_VISIBLE_DEVICES': '7', 'CUBLAS_WORKSPACE_CONFIG': 'unexpected',
                 'NVIDIA_TF32_OVERRIDE': '1', 'MUJOCO_GL': 'osmesa', 'MUJOCO_EGL_DEVICE_ID': '9'}
    for key, value in inherited.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(o, '_source', lambda *args: ({}, meta, recording))
    monkeypatch.setattr(o, '_budget', lambda *args: None)
    monkeypatch.setattr(snapshots, 'read_snapshot', lambda *args: retained)
    def opened(*args, **kwargs):
        assert {key: o.os.environ.get(key) for key in inherited} == {
            'CUDA_VISIBLE_DEVICES': '', 'CUBLAS_WORKSPACE_CONFIG': None, 'NVIDIA_TF32_OVERRIDE': None,
            'MUJOCO_GL': 'egl', 'MUJOCO_EGL_DEVICE_ID': None}
        raise RuntimeError('fixture stops after compatible CPU environment')
    monkeypatch.setattr(Engine, 'open', opened)
    with pytest.raises(RuntimeError, match='compatible CPU environment'):
        o._operation(0, tmp_path / 'source-row.json', tmp_path / 'output', tmp_path, tmp_path, tmp_path)


def test_size_tolerates_atomic_publication_rename(tmp_path, monkeypatch):
    (tmp_path / 'stable').write_bytes(b'123')
    temporary = tmp_path / 'temporary'
    temporary.write_bytes(b'12345')
    original = Path.lstat
    def lstat(path, *args, **kwargs):
        if path == temporary:
            temporary.unlink(missing_ok=True)
            raise FileNotFoundError('publication rename')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'lstat', lstat)
    assert o._size(tmp_path) == 3
