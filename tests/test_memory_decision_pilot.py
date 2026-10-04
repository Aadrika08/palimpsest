"""Pilot safeguards: failure accounting and prerequisites are real decisions."""
import importlib
from pathlib import Path
import tempfile

import pytest


def runner():
    try:
        module = importlib.import_module('scripts.memory_decision_pilot')
    except ModuleNotFoundError:
        module = None
    assert module is not None, 'The bounded memory-v2 pilot runner is required'
    return module


def test_failure_receives_full_cap_even_when_it_stops_early():
    module = runner()
    assert module.capped_score({'goal': False, 'continuation_ticks': 7}) == 900
    assert module.capped_score({'goal': True, 'continuation_ticks': 37}) == 37
    with pytest.raises(ValueError):
        module.capped_score({'goal': True, 'continuation_ticks': 901})


def test_mandatory_prerequisite_failure_stops_later_launch():
    module = runner()
    assert module.prerequisite_pass('open-route', {'acquired': True, 'goal': True})
    assert not module.prerequisite_pass('open-route', {'acquired': False, 'goal': True})
    assert not module.prerequisite_pass('retreat', {'acquired': True, 'goal': True, 'retreat_completed': False})
    assert not module.prerequisite_pass('restore', {'invariants_preserved': True, 'repeat_matches': False})


def test_allocation_refuses_owner_and_cleanup_that_do_not_fit():
    module = runner()
    assert module.admit_time(100., 241., 130., 10.)
    assert not module.admit_time(100., 239., 130., 10.)


def test_output_cannot_overwrite_assets_or_existing_evidence():
    module = runner()
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        assets = root/'assets'
        assets.mkdir()
        with pytest.raises(ValueError):
            module.safe_output(assets/'nested', [assets])
        with pytest.raises(ValueError):
            module.safe_output(root, [assets])
        with pytest.raises(ValueError):
            module.safe_output(assets, [])
        assert module.safe_output(root/'new', [assets]) == root/'new'


def test_condition_invariants_exclude_only_u_selector_and_recorder_identity():
    module = runner()
    snapshot = {'application': {'memory': {'version': 3, 'm': {'value': 1},
                'e': {}, 'u': {'recipe': 'one'}, 'selector': {'condition': 'own'},
                'supervisor': {'phase': 'await_decision', 'route_id': None}},
                'source_run_id': 'old', 'event_prefix': {}, 'total_tick': 50},
                'native_data': b'physical', 'rng': [5]}
    import copy
    changed = copy.deepcopy(snapshot)
    changed['application']['memory']['u'] = {'recipe': 'two'}
    changed['application']['memory']['selector'] = {'condition': 'no-U'}
    changed['application']['source_run_id'] = 'new'
    assert module.condition_digest(snapshot) == module.condition_digest(changed)
    changed['application']['memory']['supervisor']['route_id'] = 'route-a'
    assert module.condition_digest(snapshot) != module.condition_digest(changed)


def test_pilot_pairs_require_sham_identity_and_no_postevent_sample_before_commit():
    module = runner()
    records = [{'condition': condition, 'goal': True, 'continuation_ticks': 80,
                'path_length': 4., 'trace_digest': 'same' if condition in ('own', 'sham') else condition,
                'route_commits': [{'route_id': 'route-a', 'tick': 12}],
                'post_event_samples': [], 'event_tick': 10}
               for condition in ('own', 'swapped', 'no-U', 'sham')]
    assert module.audit_pair(records)['own_sham_identical']
    records[3]['trace_digest'] = 'different'
    assert not module.audit_pair(records)['own_sham_identical']
    records[0]['post_event_samples'] = [11]
    assert not module.audit_pair(records)['commitment_before_fresh_sample']


def test_scores_refuse_boolean_nonfinite_and_negative_counts():
    module = runner()
    for ticks in (True, -1, 3.5, float('nan')):
        with pytest.raises(ValueError):
            module.capped_score({'goal': True, 'continuation_ticks': ticks})


def test_digest_keeps_revision_rng_initial_memory_and_supervisor():
    import copy
    module = runner()
    value = {'application': {'revision': 7, 'source_run_id': 'one', 'event_prefix': {},
             'memory': {'version': 3, 'initial_m': {}, 'u': {}, 'selector': {},
                        'supervisor': {'phase': 'await_decision'}}}, 'rng': {'seed': 8}}
    for path in ('revision', 'version', 'rng'):
        changed = copy.deepcopy(value)
        if path == 'rng':
            changed['rng']['seed'] = 9
        elif path == 'version':
            changed['application']['memory']['version'] = 2
        else:
            changed['application'][path] += 1
        assert module.condition_digest(value) != module.condition_digest(changed)


def test_output_refuses_symlink_aliases_even_if_destination_absent(tmp_path):
    module = runner()
    (tmp_path/'source').mkdir()
    (tmp_path/'alias').symlink_to(tmp_path/'source', target_is_directory=True)
    with pytest.raises(ValueError):
        module.safe_output(tmp_path/'alias'/'new', [])


def test_stage_cap_cannot_transfer_time_or_admit_nonfinite_values():
    module = runner()
    assert module.stage_cap('feasibility', None) == 1800
    assert module.stage_cap('pilot', 30) == 30
    for name, seconds in (('pilot', 4201), ('feasibility', 1801), ('pilot', 0), ('pilot', float('nan'))):
        with pytest.raises(ValueError):
            module.stage_cap(name, seconds)


def test_pair_audit_missing_condition_cannot_pass():
    module = runner()
    with pytest.raises(ValueError):
        module.audit_pair([{'condition': 'own'}])


def test_fixed_owner_counts_and_no_holdout_admission():
    module = runner()
    feasible = module.feasibility_specs()
    pilot = module.pilot_specs()
    assert len(feasible) == 8
    assert [x['operation'] for x in feasible].count('full') == 4
    assert [x['operation'] for x in feasible].count('prefix') == 2
    assert [x['operation'] for x in feasible].count('repeat') == 2
    assert len(pilot) == 6
    assert [x['kind'] for x in pilot].count('change') == 4
    assert [x['kind'] for x in pilot].count('null') == 1
    assert [x['kind'] for x in pilot].count('no-event') == 1
    assert {(x['regime'], x['mirrored']) for x in pilot if x['kind'] == 'change'} == {
        ('local_cue', False), ('local_cue', True), ('paired_cue', False), ('paired_cue', True)}


def test_raw_reader_exhausts_published_ticks_beyond_legacy_600(tmp_path):
    import numpy as np
    from palimpsest.records import RunWriter
    module = runner()
    root = tmp_path/'run'
    writer = RunWriter(root/'recording', {'run_id': 'a'*32}, max_bytes=1024**2)
    for tick in range(610):
        writer.tick(0, tick, pose=np.array([0., 0., 0.]))
    writer.finish({}, status='completed')
    data = module.read_raw(root)
    assert len(data['rows']) == 610
    assert data['rows'][-1]['tick'] == 609
    chunk = root/'recording/chunks/000019.npz'
    chunk.write_bytes(chunk.read_bytes()+b'corrupt')
    with pytest.raises(ValueError, match='checksum'):
        module.read_raw(root)


def test_phase_storage_budget_has_fixed_global_caps(tmp_path):
    module = runner()
    budget = module.phase_budget(tmp_path)
    assert budget.limits.max_bytes == 8*1024**3
    assert budget.limits.min_free_bytes == 2*1024**3
    assert budget.headroom_bytes == 64*1024**2


def test_worker_invalid_job_rejected_before_native_import_or_writer(tmp_path):
    module = runner()
    with pytest.raises(ValueError):
        module.worker({'operation': 'unknown', 'output': str(tmp_path/'unexpected')})
    assert not (tmp_path/'unexpected').exists()


def test_snapshot_size_guard_refuses_before_underlying_publication(tmp_path):
    module = runner()
    class Budget:
        def check(self, *args, **kwargs):
            pytest.fail('Oversized snapshot must not reach publication budget')
    with pytest.raises(ValueError, match='16 MiB'):
        module.SnapshotBudget(Budget()).check(16*1024**2+1, path=tmp_path/'initial.snp')


def test_policy_audit_returns_original_actions_and_refuses_private_input():
    import numpy as np
    from types import SimpleNamespace
    module = runner()
    answer = {'action': np.array([.2, .3], np.float32),
              'encoded_input': np.zeros(4813, np.float32), 'raw_output': np.zeros(2, np.float32)}
    seen = []
    policy = SimpleNamespace(act=lambda obs: answer)
    engine = SimpleNamespace(policy=policy, _event=lambda kind, **kw: seen.append((kind, kw)))
    module.audit_policy(engine)
    observation = {'cam_left': np.zeros((1, 1, 3), np.uint8), 'cam_right': np.zeros((1, 1, 3), np.uint8),
        'sensors': {'collision': False, 'collision_angle': None, 'wind_direction': [1., 0.]}}
    assert policy.act(observation) is answer
    assert seen[0][0] == 'neural_policy_call'
    with pytest.raises(ValueError, match='undeclared'):
        policy.act({**observation, 'ground_truth_route': 'south'})


def test_repeat_digest_binds_cameras_actions_raw_and_neural_state():
    import copy
    import numpy as np
    module = runner()
    rows = [{'episode': 0, 'tick': 32, 'pose': np.zeros(3), 'action': np.zeros(2, np.float32),
        'encoded_input': np.zeros(4813, np.float32), 'raw_output': np.zeros(2, np.float32),
        'cam_left': np.zeros((1, 1, 3), np.uint8), 'latency': np.array(1.)}]
    changed = copy.deepcopy(rows)
    changed[0]['latency'] = np.array(2.)
    assert module.trace_digest(rows) == module.trace_digest(changed)
    for key in ('action', 'raw_output', 'cam_left'):
        changed = copy.deepcopy(rows)
        changed[0][key].flat[0] = 1
        assert module.trace_digest(rows) != module.trace_digest(changed)


def test_failed_native_prerequisite_records_remaining_as_unattempted(tmp_path, monkeypatch):
    module = runner()
    calls = []
    storage = module.phase_budget(tmp_path)
    plan = {'output': str(tmp_path/'stage'), 'phase_root': str(tmp_path),
            'geometry_valid': True, 'geometry': [], 'source_identity': {},
            'repo': str(tmp_path), 'assets': str(tmp_path/'assets'), 'history_root': str(tmp_path/'histories')}
    def failed(*args, **kwargs):
        calls.append(args[1]['id'])
        return {'job_id': args[1]['id'], 'status': 'failed', 'acquired': False, 'goal': False,
                'continuation_ticks': 0, 'capped_ticks': 900, 'error': {'type': 'Fixture', 'message': 'native refusal'}}
    monkeypatch.setattr(module, 'launch_owner', failed)
    result = module.execute_stage('feasibility', plan, storage, 10**20)
    assert calls == ['south-no-event']
    assert not result['mandatory_pass']
    assert len(result['attempted']) == 1
    assert len(result['unattempted']) == 7


def test_invalid_geometry_does_not_launch_any_owner(tmp_path, monkeypatch):
    module = runner()
    monkeypatch.setattr(module, 'launch_owner', lambda *a, **kw: pytest.fail('Invalid geometry must stop native progress'))
    plan = {'output': str(tmp_path/'stage'), 'phase_root': str(tmp_path),
            'geometry_valid': False, 'geometry': [], 'source_identity': {}}
    result = module.execute_stage('feasibility', plan, module.phase_budget(tmp_path), 10**20)
    assert result['attempted'] == []
    assert len(result['unattempted']) == 8
    assert not result['mandatory_pass']


def test_commitment_audit_uses_actual_observed_and_string_categories():
    import copy
    module = runner()
    commitment = {'route_id': 'route-z', 'inputs': [
        {'route_id': 'route-a', 'estimate': 'open', 'status': 'uncertain', 'category': 'uncertain', 'cost': 3.},
        {'route_id': 'route-z', 'estimate': 'open', 'status': 'observed', 'category': 'open', 'cost': 4.}]}
    module.audit_commitment(commitment)
    wrong = copy.deepcopy(commitment)
    wrong['route_id'] = 'route-a'
    with pytest.raises(ValueError, match='policy'):
        module.audit_commitment(wrong)
    wrong = copy.deepcopy(commitment)
    wrong['inputs'][0]['category'] = 'open'
    with pytest.raises(ValueError, match='input'):
        module.audit_commitment(wrong)


def test_real_fsm_commitment_contract_matches_runner_audit():
    from palimpsest import memory
    world = pytest.importorskip('palimpsest.memory_decision_world')
    decision = pytest.importorskip('palimpsest.memory_decision')
    module = runner()
    case = world.make_case(400, 'local_cue', 'change')
    state = decision.initialize(case)
    # This is a pure categorical selection fixture; it cannot qualify a prefix.
    state['m'] = memory.seed_m(case['facts'], [])
    audit = []
    decision._choose(state, 12, audit)
    commitment = next(a for a in audit if a['kind'] == 'memory_commitment')
    module.audit_commitment(commitment)
    assert commitment['inputs'][0]['status'] == 'unknown'


def test_repeat_state_normalizes_only_new_destination_receipt_identity():
    import copy
    module = runner()
    def value(run_id):
        return {'application': {'source_run_id': run_id, 'event_prefix': {},
            'memory': {'u': {}, 'selector': {}, 'version': 3}, 'receipts': {
                'old': {'received_run_id': 'source', 'applied_run_id': 'source', 'applied_tick': 5},
                'new': {'received_run_id': run_id, 'applied_run_id': run_id, 'applied_tick': 12}}}}
    one, two = value('one'), value('two')
    assert module.condition_digest(one) != module.condition_digest(two)
    assert module.repeat_post_digest(one, {'old'}) == module.repeat_post_digest(two, {'old'})
    changed = copy.deepcopy(two)
    changed['application']['receipts']['new']['applied_tick'] = 13
    assert module.repeat_post_digest(one, {'old'}) != module.repeat_post_digest(changed, {'old'})
    changed = copy.deepcopy(two)
    changed['application']['receipts']['old']['received_run_id'] = 'other-source'
    assert module.repeat_post_digest(one, {'old'}) != module.repeat_post_digest(changed, {'old'})
    changed = copy.deepcopy(two)
    changed['application']['receipts']['new']['applied_run_id'] = 'wrong-recorder'
    with pytest.raises(ValueError, match='recorder'):
        module.repeat_post_digest(changed, {'old'})


def test_production_worker_uses_cpu_policy_prefix_configures_only_at_boundary(tmp_path, monkeypatch):
    """Run production orchestration with a synthetic engine, never native/model jobs."""
    import copy
    from types import SimpleNamespace
    from palimpsest import engine as engine_module, replay, snapshots
    module = runner()
    engines = []
    class FakeEngine:
        def __init__(self):
            self.controller, self.phase, self.episode, self.episode_step = 'flynn', 'paused', 0, 0
            self.policy = SimpleNamespace(act=lambda obs: None)
            self.env, self.observation, self.teacher = object(), {}, None
            self.writer = SimpleNamespace(manifest={})
            self.memory = {'version': 3, 'u': {}, 'selector': {}, 'supervisor': {'phase': 'acquire'}}
            self.world_task_state, self.last_outcome = {}, None
            self.closed, self.configured, self.armed = False, False, False
            self.commands = []
        def _event(self, *a, **kw):
            pass
        def submit(self, command):
            assert command['kind'] == 'step'
            assert 'action' not in command and 'payload' not in command
            self.commands.append(command)
            return {'status': 'queued'}
        def advance(self):
            self.episode_step += 1
            if self.episode_step == 2:
                self.memory['supervisor']['phase'] = 'await_decision'
            if self.armed:
                self.memory['supervisor']['phase'] = 'goal'
                self.phase = 'terminated'
            return {'phase': self.phase}
        def configure_memory_selector(self, config, u=None):
            assert self.memory['supervisor']['phase'] == 'await_decision'
            self.configured = True
            self.memory['u'], self.memory['selector'] = u, config
        def arm_memory_decision(self):
            assert self.configured
            self.armed = True
        def close(self):
            self.closed = True
    def open_engine(*args, **kwargs):
        assert kwargs['controller'] == 'flynn' and kwargs['device'] == 'cpu'
        assert kwargs['scenario'] == 'memory-decision-v2'
        engine = FakeEngine()
        engines.append(engine)
        return engine
    native = {}
    def capture(engine):
        return {'application': {'memory': copy.deepcopy(engine.memory), 'source_run_id': 'a'*32,
                               'event_prefix': {}, 'receipts': {}}, 'rng': [4]}
    def register(engine, run, budget):
        (run/'snapshots').mkdir()
        (run/'snapshots/initial.snp').write_bytes(b'synthetic snapshot')
        native.update(capture(engine))
    job = {'stage': 'feasibility', 'operation': 'full', 'condition': None, 'repo': str(tmp_path),
        'assets': str(tmp_path/'assets'), 'history_root': str(tmp_path/'histories'),
        'source_identity': {}, 'output': str(tmp_path/'run'), 'phase_root': str(tmp_path),
        'run_id': 'a'*32, 'spec': {'id': 'synthetic', 'regime': 'local_cue'}, 'case': {'seed': 400},
        'snapshot_path': None}
    monkeypatch.setattr(module, 'validate_job', lambda raw: copy.deepcopy(raw))
    monkeypatch.setattr(module, 'source_identity', lambda *a: {})
    monkeypatch.setattr(module, 'common_helpers', lambda: SimpleNamespace(load_histories=lambda root: {}))
    monkeypatch.setattr(module, 'selector_for', lambda *a: {'condition': 'no-U'})
    monkeypatch.setattr(module, 'u_for', lambda *a: {'synthetic': True})
    monkeypatch.setattr(module, 'capture_engine', capture)
    monkeypatch.setattr(engine_module.Engine, 'open', open_engine)
    monkeypatch.setattr(replay, '_register_initial', register)
    monkeypatch.setattr(snapshots, 'read_snapshot', lambda path: copy.deepcopy(native))
    assert module.worker(job) == 0
    report = module.read_json(tmp_path/'run/worker-report.json')
    assert report['acquired'] and report['goal']
    assert report['continuation_ticks'] == 1 and report['capped_ticks'] == 1
    assert engines[0].closed and engines[0].configured and engines[0].armed
    assert len(engines[0].commands) == 3
    assert module.read_json(tmp_path/'run/owner.json')['run_id'] == 'a'*32


def test_manifest_uses_actual_full_private_profile_contract():
    profiles = pytest.importorskip('palimpsest.profiles')
    if not hasattr(profiles, 'validate_decision'):
        pytest.skip('Runtime integration is validated after the sibling lane is installed')
    module = runner()
    job = {'run_id': 'b'*32, 'operation': 'condition'}
    manifest = {'run_id': job['run_id'], 'controller': 'flynn', 'requested_device': 'cpu',
        'scenario': profiles.validate_decision('memory-decision-v2', 'checker', 'flynn'),
        'recording_max_bytes': 384*1024**2, 'memory_decision_pilot_job': job}
    assert module.native_manifest_matches(job, manifest)
    assert not module.native_manifest_matches(job, {**manifest, 'scenario': 'memory-decision-v2'})
    assert not module.native_manifest_matches(job, {**manifest, 'recording_max_bytes': 512*1024**2})


def test_pre_event_failure_is_scored_without_fabricated_gate_execution():
    module = runner()
    case = {'kind': 'change'}
    state = {'event_tick': 51, 'last_tick': 50, 'gate_result': 'pending'}
    failure = {'final_phase': 'failed', 'goal': False}
    assert module.gate_evidence(case, 'condition', state, [], failure)
    assert module.capped_score({'goal': False, 'continuation_ticks': 0}) == 900
    with pytest.raises(ValueError, match='unexecuted'):
        module.gate_evidence(case, 'condition', state, [], {'final_phase': 'paused', 'goal': False})
    with pytest.raises(ValueError, match='closure'):
        module.gate_evidence(case, 'condition', {**state, 'last_tick': 51}, [], failure)
    assert not module.gate_evidence(case, 'condition',
        {**state, 'last_tick': 51, 'gate_result': 'closed'}, [{'tick': 51}], failure)
