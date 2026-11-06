"""Canonical bootstrap source units on retained authored bytes, never native qualification."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
from types import ModuleType, SimpleNamespace
import uuid

import numpy as np
import pytest

from palimpsest import assets, flynn, memory_decision, memory_decision_world as world
from palimpsest.engine import Engine
from palimpsest.held_provenance import (
    HeldProvenance, SIMULATION_DISTRIBUTIONS, UPSTREAM_PIN, held_provenance,
)
from palimpsest.records import RunWriter

MODE = 'canonical-prepared-vnext-v1'
RUN_ID = 'bc47d679-7b20-4ac9-b630-27e4c7b05691'
SOURCE_MANIFEST = Path(__file__).resolve().parents[1] / 'model_manifests/flynn-full-vision.json'


def held_inputs(**changes):
    """Authored registration-shaped pins; no claim of external admission."""
    values = dict(
        interpreter=dict(path='/authored/python', size_bytes=1, sha256='1'*64, python_version='3.11.1'),
        upstream=dict(path='/authored/upstream', commit=UPSTREAM_PIN,
                      files=[dict(path='authored.py', size_bytes=1, sha256='2'*64)]),
        distributions=[dict(name=name, version='0.0.1', root_index=0,
                            metadata_path=name + '.dist-info/METADATA')
                       for name in SIMULATION_DISTRIBUTIONS],
        palimpsest_version='0.1.0', lock_sha256='3'*64, environment={'MUJOCO_GL': 'egl'})
    values.update(changes)
    return values


def held(**changes):
    return held_provenance(**held_inputs(**changes))


class TextSubclass(str):
    pass


class BoundaryFailure(RuntimeError):
    pass


class Environment:
    """Array/joint protocol for the real world guards; no native model or stepping."""
    def __init__(self, trace):
        self.trace = trace
        self.n_obstacles, self.arena, self.frame_skip = 20, 7., 1
        self.obstacle_ids = list(range(20))
        self.obstacle_x_joint_ids = list(range(0, 40, 2))
        self.obstacle_y_joint_ids = list(range(1, 40, 2))
        self.goal_site_id = 0
        self.model = SimpleNamespace(
            opt=SimpleNamespace(timestep=.02), site_size=np.array([[.25, 0., 0.]]),
            geom_type=np.full(20, 5), geom_size=np.tile([.4, 1., 0.], (20, 1)),
            jnt_range=np.tile([-.0005, .0005], (40, 1)),
            jnt_qposadr=np.arange(40), jnt_dofadr=np.arange(40), site_pos=np.zeros((1, 3)))
        self.data = SimpleNamespace(qpos=np.zeros(40), qvel=np.zeros(40), geom_xpos=np.zeros((20, 3)))
        self._obstacle_xy, self._goal_xy = np.zeros((20, 2)), np.zeros(2)
        self._last_action = np.ones(2)
        self.planner = SimpleNamespace()
        self.renderer = SimpleNamespace(close=lambda: trace.append(('renderer.close',)))
        self.closed = False
        self.pose = np.zeros(3)

    def reset(self, *, seed):
        self.trace.append(('env.reset', seed))
        return self._get_obs(), {}

    def _get_obs(self):
        return {'cam_left': np.zeros((2, 2, 3), dtype=np.uint8),
                'cam_right': np.zeros((2, 2, 3), dtype=np.uint8)}

    def place_robot(self, x, y, yaw, qpos, qvel):
        self.trace.append(('place_robot', x, y, yaw))
        self.pose[:] = x, y, yaw

    def _base_xy(self):
        return self.pose[:2]

    def _base_yaw(self):
        return self.pose[2]

    def _reset_exploration(self):
        self.trace.append(('reset_exploration',))

    def close(self):
        self.closed = True
        self.trace.append(('env.close',))


@pytest.fixture
def route(tmp_path_factory, monkeypatch):
    # Unique invocation basetemp and descendants are deliberately retained.
    home = tmp_path_factory.getbasetemp() / uuid.uuid4().hex
    repo, root = home / 'repo', home / 'assets'
    repo.mkdir(parents=True)
    root.mkdir()
    manifest = json.loads(SOURCE_MANIFEST.read_text())
    paths, trace, constructed = {}, [], []

    def put(role, path, raw):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        paths[role] = path
        return dict(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))

    for item, role in zip(manifest['files'], ('archive', 'checkpoint')):
        item.update(put(role, root / item['path'], ('authored ' + role + '\n').encode()))
    graph = manifest['graph']
    archive_hash = manifest['files'][0]['sha256']
    directory = root / ('graph-' + archive_hash)
    edge = directory / graph['edge_identity']['archive_member']
    graph['edge_identity'].update(put('edge', edge, b'pre,post\n1,2\n'))
    graph['edge_identity']['derived_from_archive_sha256'] = archive_hash
    for i, item in enumerate(graph['mapping_files']):
        raw = f'cell,type\n{i},authored\n'.encode()
        item.update(put('source'+str(i), repo / item['source_path'], raw))
        item['archive_identity'] = put('mapping'+str(i), edge.parent / item['path'], raw.replace(b'\n', b'\r\n'))
    put('manifest', repo / 'model_manifests/flynn-full-vision.json', json.dumps(manifest).encode())
    metadata = dict(archive_sha256=archive_hash, edge_path=graph['edge_identity']['archive_member'],
                    edge_sha256=graph['edge_identity']['sha256'], upstream_commit=assets.UPSTREAM_COMMIT,
                    mapping_files=copy.deepcopy(graph['mapping_files']), provenance_limit=manifest['provenance_limit'])
    put('metadata', directory / 'palimpsest-prepared.json', json.dumps(metadata).encode())
    put('lock', repo / 'uv.lock', b'# authored lock\n')
    put('source', repo / 'src/palimpsest/authored.py', b'# authored provenance source\n')
    output = home / 'run'
    case = world.make_family_case('development', 0, 0, 'change')
    record = held()
    policy = SimpleNamespace(device='cpu', provenance={'unit_boundary': 'inert policy; unqualified'},
                             reset=lambda: trace.append(('policy.reset',)))
    stage = SimpleNamespace(fail=None, close_error=False)

    def denied(*args, **kwargs):
        raise AssertionError('Forbidden acquisition, preparation, doctor, or real allocation')

    for name in ('prepare_graph', 'verify_assets', 'fetch_assets', 'urlopen'):
        monkeypatch.setattr(assets, name, denied)
    # Do not even import the ambient doctor in canonical mode.
    monkeypatch.setitem(sys.modules, 'palimpsest.doctor', None)
    torch = ModuleType('torch')
    def manual_seed(seed):
        trace.append(('torch.seed', seed))
        if stage.fail == 'allocation':
            raise BoundaryFailure('allocation boundary')
    torch.manual_seed = manual_seed
    torch.set_num_threads = lambda count: trace.append(('torch.threads', count))
    monkeypatch.setitem(sys.modules, 'torch', torch)
    monkeypatch.setattr(random, 'seed', lambda seed: trace.append(('random.seed', seed)))
    monkeypatch.setattr(np.random, 'seed', lambda seed: trace.append(('numpy.seed', seed)))
    native = ModuleType('mujoco')
    def forward(model, data):
        trace.append(('mj_forward',))
        data.geom_xpos[:, :2] = data.qpos.reshape(20, 2)
    native.mj_forward = forward
    monkeypatch.setitem(sys.modules, 'mujoco', native)

    def make_env(unused, count, *, texture_mode):
        trace.append(('make_env', unused, count, texture_mode))
        env = Environment(trace)
        constructed.append(env)
        if stage.fail == 'configure':
            env.model.geom_type[0] = 0
        if stage.fail == 'init':
            env.model.opt.timestep = .03
        if stage.fail == 'episode':
            env.data.qvel = np.r_[env.data.qvel, np.nan]  # Outside configured joints; real episode JSON refuses it.
        if stage.fail == 'close' or stage.close_error:
            def close_error():
                trace.append(('renderer.close',))
                raise BoundaryFailure('renderer close boundary')
            env.renderer.close = close_error
        return env

    def upstream(root_arg, name):
        trace.append(('import_upstream', root_arg, name))
        assert root_arg == repo and name == 'run_connectome_rnn_checkpoint'
        return SimpleNamespace(_make_env=make_env)

    def load_policy(*args):
        trace.append(('load_policy', *args))
        if stage.fail == 'policy':
            raise BoundaryFailure('policy boundary')
        if stage.fail == 'provenance':
            paths['lock'].rename(paths['lock'].with_suffix('.retained'))
        return policy

    monkeypatch.setattr(flynn, 'import_upstream', upstream)
    monkeypatch.setattr(flynn, 'load_policy', load_policy)
    real_resolver = assets.resolve_prepared_assets_readonly
    def resolve(repo_arg, asset_arg):
        trace.append(('resolve', repo_arg, asset_arg))
        return real_resolver(repo_arg, asset_arg)
    monkeypatch.setattr(assets, 'resolve_prepared_assets_readonly', resolve)

    def opened(**changes):
        options = dict(controller='flynn', device='cpu', seed=case['seed'], scenario='memory-decision-v2',
                       texture='checker', run_id=RUN_ID, memory_case=case, diagnostics=record,
                       source_bootstrap_mode=MODE)
        repo_arg, asset_arg = changes.pop('repo_root', repo), changes.pop('asset_root', root)
        options.update(changes)
        return Engine.open(repo_arg, asset_arg, output, **options)

    return SimpleNamespace(home=home, repo=repo, root=root, output=output, paths=paths, case=case,
                           record=record, policy=policy, stage=stage, trace=trace, envs=constructed, open=opened)


def events(route):
    return [json.loads(line) for line in (route.output / 'events.jsonl').read_text().splitlines()]


def test_canonical_open_traverses_shared_constructor_world_and_writer(route):
    before = {name: path.read_bytes() for name, path in route.paths.items()}
    engine = route.open()
    try:
        assert type(engine) is Engine and type(engine.writer) is RunWriter
        assert engine.writer._background is None
        assert engine.run_id == engine.writer.manifest['run_id'] == RUN_ID
        assert (engine.phase, engine.total_tick, engine.episode, engine.episode_step) == ('paused', 0, 0, 0)
        assert engine.memory['version'] == 3
        memory_decision.validate_state(engine.memory)
        assert engine.world_task_state == world.initial_state(route.case)
        assert engine.world()['obstacles'] == [[*xy, .4] for xy in world.PROFILE['obstacles']]
        assert engine.writer.manifest['scenario']['version'] == 3
        assert engine.writer.manifest['source_bootstrap_epoch'] == MODE
        assert not any(key.lstrip('_').startswith('memory_terminal_vnext_')
                       for key in vars(engine) | engine.writer.manifest)
        assert [row['kind'] for row in events(route)] == [
            'diagnostics', 'policy_loaded', 'environment', 'engine_opened', 'episode_started']
        assert events(route)[0]['report'] == route.record.report()
        assert events(route)[1]['provenance'] == route.policy.provenance
        assert events(route)[2]['upstream_commit'] == assets.UPSTREAM_COMMIT
        assert events(route)[2]['source_sha256'] == {
            'src/palimpsest/authored.py': hashlib.sha256(b'# authored provenance source\n').hexdigest()}
        assert events(route)[2]['lock_sha256'] == hashlib.sha256(b'# authored lock\n').hexdigest()
        assert all(row['run_id'] == RUN_ID for row in events(route))
        assert [row['sequence'] for row in events(route)] == list(range(5))
        seed = route.case['seed']
        assert route.trace == [
            ('resolve', route.repo, route.root), ('random.seed', seed), ('numpy.seed', seed),
            ('torch.seed', seed), ('torch.threads', 1),
            ('import_upstream', route.repo, 'run_connectome_rnn_checkpoint'),
            ('make_env', None, 20, 'checker'),
            ('load_policy', route.repo, route.paths['edge'], route.paths['checkpoint'], 'cpu', seed),
            ('env.reset', seed), ('place_robot', *world.START_POSE), ('mj_forward',),
            ('reset_exploration',), ('policy.reset',)]
    finally:
        engine.close()
    assert route.envs[0].closed and engine.writer._events.closed
    final = json.loads((route.output / 'manifest.json').read_text())
    assert final['status'] == 'completed' and final['run_id'] == RUN_ID
    assert final['recorded_ticks'] == 0 and final['recorded_events'] == 5
    assert {name: path.read_bytes() for name, path in route.paths.items()} == before


@pytest.mark.parametrize('mode', ['', 'canonical-prepared-vnext-v2', False, 1, [], {}, b'canonical-prepared-vnext-v1', TextSubclass(MODE)])
def test_unknown_mode_refuses_before_payload_output_or_allocation(route, mode):
    with pytest.raises(ValueError, match='source_bootstrap_mode'):
        route.open(source_bootstrap_mode=mode)
    assert route.trace == [] and not route.output.exists()


@pytest.mark.parametrize('changes,reason', [
    ({'scenario': 'reproduction'}, 'canonical prepared'),
    ({'texture': 'realistic'}, 'canonical prepared'),
    ({'controller': 'manual'}, 'canonical prepared'),
    ({'controller': 'teacher'}, 'canonical prepared'),
    ({'controller': 'male-original'}, 'canonical prepared'),
    ({'controller': 'male-control'}, 'canonical prepared'),
    ({'controller': 'unknown'}, 'unknown controller'),
    ({'device': 'cuda'}, 'canonical prepared'),
    ({'device': 'gpu'}, 'unknown controller'),
    ({'restore_snapshot': {}}, 'fresh'),
    ({'replace_controller': True}, 'fresh'),
    ({'replace_controller': 0}, 'fresh'),
    ({'replace_controller': None}, 'fresh'),
    ({'memory_u': {}}, 'fresh'),
    ({'research_binding': object()}, 'fresh'),
    ({'expected_policy_identity': {}}, 'policy identity'),
    ({'seed': True}, 'seed must'),
    ({'seed': -1}, 'seed must'),
    ({'seed': 2**31}, 'seed must'),
    ({'seed': 0}, 'seed differs'),
])
def test_incompatible_options_refuse_before_resolver_and_allocation(route, changes, reason):
    with pytest.raises(ValueError, match=reason):
        route.open(**changes)
    assert route.trace == [] and not route.output.exists()


@pytest.mark.parametrize('kind', ['none', 'list', 'string', 'object', 'empty', 'version-bool',
                                  'version-float', 'version2', 'tampered', 'profile', 'incomplete-v3', 'dict-subclass'])
def test_case_type_version_and_real_frozen_profile_guards(route, kind):
    case = copy.deepcopy(route.case)
    if kind == 'none': case = None
    elif kind == 'list': case = [1]
    elif kind == 'string': case = 'case'
    elif kind == 'object': case = object()
    elif kind == 'empty': case = {}
    elif kind == 'version-bool': case['version'] = True
    elif kind == 'version-float': case['version'] = 3.
    elif kind == 'version2': case = world.make_case(0, 'local_cue', 'change')
    elif kind == 'profile': case['profile_sha256'] = 'a'*64
    elif kind == 'incomplete-v3': case = {'version': 3}
    elif kind == 'dict-subclass': case = type('CaseSubclass', (dict,), {})(case)
    else: case['start_pose'][0] += .1
    with pytest.raises(ValueError):
        route.open(memory_case=case)
    assert route.trace == [] and not route.output.exists()


@pytest.mark.parametrize('run_id', [None, RUN_ID.replace('-', ''), RUN_ID.upper(), '{'+RUN_ID+'}',
                                    'bad', '', 123, uuid.UUID(RUN_ID), True, TextSubclass(RUN_ID)])
def test_noncanonical_uuid_never_normalizes_or_creates_output(route, run_id):
    with pytest.raises(ValueError, match='canonical.*run_id'):
        route.open(run_id=run_id)
    assert route.trace == [] and not route.output.exists()


@pytest.mark.parametrize('which', ['repo_root', 'asset_root'])
@pytest.mark.parametrize('spelling', ['relative', 'dot', 'dotdot', 'repeat', 'trailing', 'bytes'])
def test_original_root_spellings_refuse_before_resolver(route, which, spelling):
    original = str(route.repo if which == 'repo_root' else route.root)
    value = {'relative': 'relative', 'dot': original + '/.', 'dotdot': original + '/../'+Path(original).name,
             'repeat': original.replace('/repo', '//repo').replace('/assets', '//assets'),
             'trailing': original+'/', 'bytes': original.encode()}[spelling]
    with pytest.raises(ValueError, match='canonical absolute'):
        route.open(**{which: value})
    assert route.trace == [] and not route.output.exists()


@pytest.mark.parametrize('which', ['repo_root', 'asset_root'])
@pytest.mark.parametrize('spelling', ['symlink', 'ancestor-symlink'])
def test_resolver_sees_original_symlink_spelling_before_any_engine_resolution(route, which, spelling):
    original = route.repo if which == 'repo_root' else route.root
    link = route.home / 'link'
    link.symlink_to(original if spelling == 'symlink' else route.home, target_is_directory=True)
    argument = link if spelling == 'symlink' else link / original.name
    with pytest.raises(ValueError, match='not a real directory'):
        route.open(**{which: argument})
    expected = ('resolve', argument if which == 'repo_root' else route.repo,
                argument if which == 'asset_root' else route.root)
    assert route.trace == [expected] and not route.output.exists()


@pytest.mark.parametrize('kind', ['none', 'dict', 'duck', 'foreign', 'subclass', 'string'])
def test_exact_held_type_required_without_doctor(route, kind):
    if kind == 'none': record = None
    elif kind == 'dict': record = route.record.report()
    elif kind == 'duck': record = SimpleNamespace(report=route.record.report)
    elif kind == 'foreign':
        spec = importlib.util.spec_from_file_location('_foreign_bootstrap_held',
                                                     Path(__file__).resolve().parents[1] / 'src/palimpsest/held_provenance.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # A genuine factory record from another package identity is still foreign.
        record = module.held_provenance(**held_inputs())
    elif kind == 'subclass':
        class Subclass(HeldProvenance):
            pass
        record = object.__new__(Subclass)
    else: record = 'None'
    with pytest.raises(ValueError, match='held provenance'):
        route.open(diagnostics=record)
    assert route.trace == [] and not route.output.exists()


@pytest.mark.parametrize('failed', ['python', 'upstream', 'dependency'])
def test_genuine_failed_held_report_refuses_before_any_payload_read(route, failed):
    changes = {'python': {'interpreter': dict(path='/authored/python', size_bytes=1,
                         sha256='1'*64, python_version='3.12.1')},
               'upstream': {'upstream': dict(path='/authored/upstream', commit='a'*40,
                          files=[dict(path='authored.py', size_bytes=1, sha256='2'*64)])},
               'dependency': {'distributions': []}}[failed]
    with pytest.raises(RuntimeError, match='runtime diagnostics failed'):
        route.open(diagnostics=held(**changes))
    assert route.trace == [] and not route.output.exists()


@pytest.mark.parametrize('role,change,reason', [
    ('checkpoint', 'corrupt', 'different prepared asset'),
    ('edge', 'missing', 'No such file'),
    ('metadata', 'corrupt', 'Expecting value'),
    ('mapping0', 'corrupt', 'mapping'),
    ('archive', 'symlink', 'unsafe file type'),
])
def test_real_resolver_failure_has_no_preparer_fallback_or_allocation(route, role, change, reason):
    path = route.paths[role]
    if change == 'corrupt': path.write_bytes(b'corrupt')
    else:
        retained = path.with_name(path.name + '.retained')
        path.rename(retained)
        if change == 'symlink': path.symlink_to(retained)
    with pytest.raises((OSError, ValueError), match=reason):
        route.open()
    assert route.trace == [('resolve', route.repo, route.root)] and not route.output.exists()


@pytest.mark.parametrize('stage,error,reason,allocated', [
    ('allocation', BoundaryFailure, 'allocation boundary', False),
    ('configure', ValueError, 'cylinder type/radius', True),
    ('policy', BoundaryFailure, 'policy boundary', True),
    ('provenance', FileNotFoundError, 'uv.lock', True),
    ('init', ValueError, '0.02-second', True),
    ('episode', ValueError, 'Out of range float', True),
])
def test_failures_after_writer_creation_keep_failed_manifest_and_close_resources(route, stage, error, reason, allocated):
    route.stage.fail = stage
    with pytest.raises(error, match=reason) as caught:
        route.open()
    assert_failed_writer_closed(caught.value)
    rows = events(route)
    assert rows[0]['kind'] == 'diagnostics' and rows[0]['report'] == route.record.report()
    assert ('torch.seed', route.case['seed']) in route.trace
    if stage in ('policy', 'provenance', 'init', 'episode'):
        assert any(row[0] == 'load_policy' for row in route.trace)
    if stage == 'episode':
        assert ('env.reset', route.case['seed']) in route.trace
        assert ('mj_forward',) in route.trace and ('policy.reset',) in route.trace
        assert rows[-1]['kind'] == 'engine_opened'
    manifest = json.loads((route.output / 'manifest.json').read_text())
    assert manifest['status'] == 'failed' and manifest['run_id'] == RUN_ID
    assert manifest['error']['type'] == error.__name__
    assert bool(route.envs) == allocated
    if allocated:
        assert route.envs[0].closed and route.trace[-2:] == [('renderer.close',), ('env.close',)]
    # The event stream was closed by the real writer; no late continuation is possible.
    assert all(row['run_id'] == RUN_ID for row in rows)


def test_real_writer_diagnostics_event_error_still_finishes_and_closes(route):
    class Budget:
        calls = 0
        def check(self, count, *, path):
            self.calls += 1
            if self.calls == 2:
                raise TypeError('authored diagnostics storage callback failure')
    budget = Budget()
    with pytest.raises(TypeError, match='diagnostics storage callback') as caught:
        route.open(storage_budget=budget)
    assert_failed_writer_closed(caught.value)
    manifest = json.loads((route.output / 'manifest.json').read_text())
    assert budget.calls == 3 and manifest['status'] == 'failed'
    assert manifest['recorded_events'] == 0 and manifest['error']['type'] == 'TypeError'
    assert route.trace == [('resolve', route.repo, route.root)] and not route.envs


def test_close_error_preserves_failed_recording_and_environment_cleanup(route):
    route.stage.fail = 'close'
    engine = route.open()
    with pytest.raises(BoundaryFailure, match='renderer close boundary'):
        engine.close()
    assert route.envs[0].closed and engine._closed and engine.writer._events.closed
    manifest = json.loads((route.output / 'manifest.json').read_text())
    assert manifest['status'] == 'failed' and manifest['run_id'] == RUN_ID


@pytest.mark.parametrize('mode', ['omitted', None])
@pytest.mark.parametrize('diagnostics', ['doctor', 'held'])
def test_legacy_default_keeps_preparation_hex_ids_and_diagnostics(route, monkeypatch, mode, diagnostics):
    def verify(repo, root):
        route.trace.append(('verify_assets', repo, root))
        return {'ok': True}
    def prepare(repo, root):
        route.trace.append(('prepare_graph', repo, root))
        return route.paths['edge']
    monkeypatch.setattr(assets, 'verify_assets', verify)
    monkeypatch.setattr(assets, 'prepare_graph', prepare)
    doctor = ModuleType('palimpsest.doctor')
    def diagnose(repo, root):
        route.trace.append(('diagnose', repo, root))
        return {'checks': [{'name': 'upstream', 'status': 'ok'}]}
    doctor.diagnose = diagnose
    monkeypatch.setitem(sys.modules, 'palimpsest.doctor', doctor)
    options = dict(controller='flynn', seed=route.case['seed'], scenario='memory-decision-v2',
                   memory_case=route.case, run_id=RUN_ID)
    if mode != 'omitted': options['source_bootstrap_mode'] = mode
    if diagnostics == 'held': options['diagnostics'] = route.record
    engine = Engine.open(route.repo, route.root, route.output, **options)
    try:
        assert engine.run_id == uuid.UUID(RUN_ID).hex
        assert 'source_bootstrap_epoch' not in engine.writer.manifest
        assert not any(row[0] == 'resolve' for row in route.trace)
        assert ('verify_assets', route.repo, route.root) in route.trace
        assert ('prepare_graph', route.repo, route.root) in route.trace
        assert (('diagnose', route.repo, route.root) in route.trace) == (diagnostics == 'doctor')
        assert events(route)[0]['report'] == (route.record.report() if diagnostics == 'held'
                                            else {'checks': [{'name': 'upstream', 'status': 'ok'}]})
    finally:
        engine.close()


def test_legacy_failed_held_report_keeps_post_writer_diagnostics(route):
    with pytest.raises(RuntimeError, match='runtime diagnostics failed'):
        route.open(source_bootstrap_mode=None, diagnostics=held(distributions=[]))
    assert route.trace == []
    assert events(route)[0]['report'] == held(distributions=[]).report()
    assert json.loads((route.output / 'manifest.json').read_text())['status'] == 'failed'


def assert_failed_writer_closed(error):
    # Inspect the actual unwound open frame; never replace the writer or its methods.
    traceback = error.__traceback__
    while traceback is not None:
        frame = traceback.tb_frame
        if frame.f_code is Engine.open.__func__.__code__:
            writer = frame.f_locals['writer']
            assert type(writer) is RunWriter and writer._events.closed
            with pytest.raises(ValueError) as closed_file:
                writer._events.fileno()
            observation = {
                'error_type': type(error).__name__, 'error_message': str(error),
                'context_type': type(error.__context__).__name__ if error.__context__ else None,
                'context_message': str(error.__context__) if error.__context__ else None,
                'manifest_status': json.loads((writer.path / 'manifest.json').read_text())['status'],
                'events_stream_closed': writer._events.closed, 'writer_broken': writer._broken,
                'closed_fileno_error': str(closed_file.value),
                'environment_closed': frame.f_locals['env'].closed if frame.f_locals['env'] else None,
            }
            (writer.path.parent / 'failure-observation.json').write_text(json.dumps(observation, indent=2) + '\n')
            return
        traceback = traceback.tb_next
    raise AssertionError('Failure did not traverse actual Engine.open')


def test_open_failure_with_renderer_close_error_still_closes_env_and_real_writer(route):
    route.stage.fail, route.stage.close_error = 'policy', True
    with pytest.raises(BoundaryFailure, match='renderer close boundary') as caught:
        route.open()
    assert_failed_writer_closed(caught.value)
    assert route.envs[0].closed
    manifest = json.loads((route.output / 'manifest.json').read_text())
    assert manifest['status'] == 'failed' and manifest['error']['message'] == 'policy boundary'
    assert route.trace[-2:] == [('renderer.close',), ('env.close',)]


@pytest.mark.parametrize('controller', ['manual', 'teacher'])
@pytest.mark.parametrize('run_id', [None, RUN_ID.replace('-', '')])
def test_legacy_ordinary_controllers_and_generated_or_hex_ids(route, monkeypatch, controller, run_id):
    doctor = ModuleType('palimpsest.doctor')
    doctor.diagnose = lambda root, assets: {'checks': [{'name': 'python', 'status': 'ok'}]}
    monkeypatch.setitem(sys.modules, 'palimpsest.doctor', doctor)
    def made():
        env = Environment(route.trace)
        route.envs.append(env)
        return env
    def manual(**options):
        assert options['n_obstacles'] == 20 and options['texture_mode'] == 'checker'
        assert options['render_mode'] is None
        route.trace.append(('manual_constructor',))
        return made()
    def upstream(root, name):
        assert root == route.repo
        if controller == 'manual':
            assert name == 'environment.mujoco_two_cam_env_random_obstacles'
            return SimpleNamespace(MuJoCoTwoCamEnv=manual)
        assert name == 'run_connectome_rnn_checkpoint'
        return SimpleNamespace(_make_env=lambda unused, count, **kwargs: made(),
                               PlannerAnalyticTeacher=lambda **kwargs: SimpleNamespace(device='cpu'))
    monkeypatch.setattr(flynn, 'import_upstream', upstream)
    engine = Engine.open(route.repo, route.root, route.output, controller=controller, run_id=run_id)
    try:
        assert len(engine.run_id) == 32 and uuid.UUID(engine.run_id).hex == engine.run_id
        if run_id is not None:
            assert engine.run_id == run_id
        assert 'source_bootstrap_epoch' not in engine.writer.manifest
        assert engine.memory is None and engine.controller == controller
        assert ('torch.threads', 2) in route.trace
        assert not any(row[0] in ('resolve', 'load_policy') for row in route.trace)
        assert [row['kind'] for row in events(route)] == [
            'diagnostics', 'environment', 'engine_opened', 'episode_started']
    finally:
        engine.close()
    assert engine.writer._events.closed and route.envs[0].closed


def test_writer_constructor_validation_retains_ordinary_no_cleanup_policy(route):
    with pytest.raises(ValueError, match='max_bytes must be a positive integer'):
        route.open(max_bytes=0)
    assert route.trace == [('resolve', route.repo, route.root)]
    assert not route.output.exists() and not route.envs


def test_real_writer_broken_budget_keeps_original_failure_semantics(route):
    class Budget:
        calls = 0
        def check(self, count, *, path):
            self.calls += 1
            if self.calls == 2:
                raise RuntimeError('authored storage quota refusal')
    with pytest.raises(ValueError, match='writer is closed or finished') as caught:
        route.open(storage_budget=Budget())
    assert_failed_writer_closed(caught.value)
    assert isinstance(caught.value.__context__, RuntimeError)
    assert str(caught.value.__context__) == 'authored storage quota refusal'
    # Existing broken writers cannot publish a terminal manifest; preserve the prefix.
    manifest = json.loads((route.output / 'manifest.json').read_text())
    assert manifest['status'] == 'running' and manifest['run_id'] == RUN_ID
    assert events(route) == [] and not route.envs
    assert route.trace == [('resolve', route.repo, route.root)]
