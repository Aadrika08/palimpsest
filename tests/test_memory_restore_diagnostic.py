"""Software fixtures only; no native study owner or experiment is launched."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import memory_decision_pilot as p
from palimpsest.snapshots import read_snapshot, state_digest


def post_state(destination='destination'):
    return {'integration': np.array([1., 2.]), 'native_data': b'opaque native',
            'application': {'source_run_id': destination, 'event_prefix': {'tick': 3},
                'memory': {'u': {}, 'selector': {}, 'm': {'facts': []}},
                'receipts': {'old': {'received_run_id': 'source', 'applied_tick': 1},
                    'new': {'received_run_id': destination, 'applied_run_id': destination,
                            'applied_tick': 7}}}}


def test_retained_state_is_exact_digest_input_and_cannot_overwrite(tmp_path):
    snapshot = post_state(); before = state_digest(snapshot)
    storage = p.phase_budget(tmp_path)
    run = tmp_path/'run'; (run/'snapshots').mkdir(parents=True)
    receipt = p.publish_repeat_state(snapshot, {'old'}, run, storage)
    retained = read_snapshot(receipt['post_snapshot_path'])
    assert state_digest(retained) == before == state_digest(snapshot)
    assert receipt['post_snapshot_sha256'] == p.file_hash(receipt['post_snapshot_path'])
    assert receipt['post_state_digest'] == p.repeat_post_digest(snapshot, {'old'})
    assert receipt['repeat_source_receipt_ids'] == ['old']
    assert receipt['post_state_components']['integration'] == state_digest(snapshot['integration'])
    with pytest.raises(FileExistsError):
        p.publish_repeat_state(snapshot, {'old'}, run, storage)


def test_component_state_preserves_existing_normalization_and_detects_changes():
    one, two = post_state('one'), post_state('two')
    assert state_digest(p.repeat_post_state(one, {'old'})) == p.repeat_post_digest(one, {'old'})
    assert state_digest(p.repeat_post_state(one, {'old'})) == state_digest(p.repeat_post_state(two, {'old'}))
    changed = copy.deepcopy(two); changed['integration'][0] += 1
    assert p.repeat_post_digest(changed, {'old'}) != p.repeat_post_digest(one, {'old'})
    changed = copy.deepcopy(two); changed['application']['receipts']['new']['applied_run_id'] = 'wrong'
    with pytest.raises(ValueError, match='recorder'):
        p.repeat_post_state(changed, {'old'})


def test_repeat_retention_refuses_other_operations_before_any_write(tmp_path, monkeypatch):
    monkeypatch.setattr(p, 'validate_job', lambda raw: raw)
    with pytest.raises(ValueError, match='repeat'):
        p.worker({'operation': 'prefix'}, retain_repeat_state=True)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('retain', [False, True])
def test_worker_publishes_original_final_capture_only_when_opted_in(tmp_path, monkeypatch, retain):
    from palimpsest import engine as engine_module, replay, snapshots
    initial = post_state('source')
    initial['application']['receipts'].pop('new')
    initial['application']['memory']['supervisor'] = {'phase': 'await_decision'}
    source = tmp_path/'source.snp'; source.write_bytes(b'source')
    captures = []

    class Engine:
        controller, phase, episode, episode_step = 'flynn', 'paused', 0, 727
        env, observation, teacher = object(), {}, None
        policy = SimpleNamespace(act=lambda observation: None)
        writer = SimpleNamespace(manifest={})
        memory = copy.deepcopy(initial['application']['memory'])
        world_task_state, last_outcome = {}, None

        def arm_memory_decision(self):
            pass

        def close(self):
            self.phase = 'closed'

    engine = Engine()
    def capture(value):
        snapshot = copy.deepcopy(initial)
        snapshot['application']['source_run_id'] = 'destination'
        snapshot['integration'][0] = value.episode_step
        snapshot['application']['receipts'] = {'old': initial['application']['receipts']['old']}
        captures.append(snapshot)
        return snapshot

    initial['integration'][0] = 727
    job = {'stage': 'feasibility', 'operation': 'repeat', 'condition': None,
        'repo': str(tmp_path), 'assets': str(tmp_path/'assets'),
        'history_root': str(tmp_path/'histories'), 'source_identity': {},
        'output': str(tmp_path/'run'), 'phase_root': str(tmp_path), 'run_id': 'a'*32,
        'spec': {'id': 'restore-1', 'regime': 'local_cue'}, 'case': {'seed': 400},
        'snapshot_path': str(source), 'snapshot_sha256': p.file_hash(source),
        'expected_invariant': p.condition_digest(initial), 'protocol_sha256': p.PROTOCOL_SHA256}
    monkeypatch.setattr(p, 'validate_job', lambda raw: copy.deepcopy(raw))
    monkeypatch.setattr(p, 'source_identity', lambda *args: {})
    monkeypatch.setattr(p, 'common_helpers', lambda: SimpleNamespace(load_histories=lambda root: {}))
    monkeypatch.setattr(p, 'capture_engine', capture)
    monkeypatch.setattr(p, 'audit_policy', lambda value: None)
    monkeypatch.setattr(p, 'policy_step', lambda value: setattr(value, 'episode_step', value.episode_step+1))
    monkeypatch.setattr(engine_module.Engine, 'open', lambda *args, **kwargs: engine)
    def register(value, run, storage):
        (run/'snapshots').mkdir(); (run/'snapshots/initial.snp').write_bytes(b'initial')
    monkeypatch.setattr(replay, '_register_initial', register)
    original_read = snapshots.read_snapshot
    monkeypatch.setattr(snapshots, 'read_snapshot', lambda path: copy.deepcopy(initial)
                        if Path(path).name != 'post-repeat.snp' else original_read(path))
    assert p.worker(job, retain_repeat_state=retain) == 0
    report = p.read_json(tmp_path/'run/worker-report.json')
    assert len(captures) == 2  # Existing invariant check and the single post-step capture.
    assert report['continuation_ticks'] == 5
    assert report['post_state_digest'] == p.repeat_post_digest(captures[-1], set(initial['application']['receipts']))
    path = tmp_path/'run/snapshots/post-repeat.snp'
    assert path.exists() is retain
    if retain:
        assert state_digest(original_read(path)) == state_digest(captures[-1])
    else:
        assert 'post_snapshot_path' not in report


def diagnostic():
    import importlib
    return importlib.import_module('scripts.memory_restore_diagnostic')


def test_compare_localizes_typed_components_without_mutating_or_normalizing_more():
    d = diagnostic(); one = post_state('one'); two = post_state('two')
    before = state_digest(two)
    result = d.compare_states(one, two, {'old'}, {'old'})
    assert result['equal'] and result['differences'] == []
    assert state_digest(two) == before
    two['integration'][0] += 1
    result = d.compare_states(one, two, {'old'}, {'old'})
    assert not result['equal']
    assert result['differing_components'] == ['integration']
    assert result['differences'][0]['path'] == '/integration'
    assert result['differences'][0]['different_elements'] == 1
    assert result['differences'][0]['max_abs_difference'] == 1.


def test_compare_preserves_native_bytes_and_extra_application_fields():
    d = diagnostic(); one = post_state('one'); two = post_state('two')
    two['native_data'] = b'opaque Native'
    two['application']['new_state'] = 17
    result = d.compare_states(one, two, {'old'}, {'old'})
    assert result['differing_components'] == ['application', 'native_data']
    by_path = {row['path']: row for row in result['differences']}
    assert by_path['/native_data']['different_bytes'] == 1
    assert by_path['/application/new_state']['reason'] == 'missing-key'


def test_stage_local_source_copy_checks_hash_invariant_and_no_overwrite(tmp_path):
    from palimpsest.snapshots import save_snapshot
    d = diagnostic(); source = tmp_path/'source.snp'; save_snapshot(post_state(), source)
    ref = {'path': str(source), 'sha256': p.file_hash(source),
           'bytes': source.stat().st_size, 'invariant': p.condition_digest(post_state())}
    dest = tmp_path/'stage/source/snapshots/initial.snp'
    receipt = d.copy_source(ref, dest, p.phase_budget(tmp_path))
    assert receipt['snapshot_sha256'] == ref['sha256']
    assert receipt['snapshot_path'] == str(dest)
    with pytest.raises(FileExistsError):
        d.copy_source(ref, dest, p.phase_budget(tmp_path))
    with pytest.raises(ValueError, match='checksum'):
        d.copy_source({**ref, 'sha256': '0'*64}, tmp_path/'bad.snp', p.phase_budget(tmp_path))
    with pytest.raises(ValueError, match='invariant'):
        d.copy_source({**ref, 'invariant': '0'*64}, tmp_path/'bad.snp', p.phase_budget(tmp_path))
    assert not (tmp_path/'bad.snp').exists()


def test_audit_post_state_refuses_missing_corrupt_or_worker_digest_mismatch(tmp_path):
    d = diagnostic(); run = tmp_path/'run'; (run/'snapshots').mkdir(parents=True)
    receipt = p.publish_repeat_state(post_state(), {'old'}, run, p.phase_budget(tmp_path))
    # Auditors derive IDs from the registered initial snapshot, not worker claims.
    from palimpsest.snapshots import save_snapshot
    initial = post_state(); initial['application']['receipts'].pop('new')
    save_snapshot(initial, run/'snapshots/initial.snp')
    receipt['snapshot_path'] = str(run/'snapshots/initial.snp')
    snapshot, ids = d.audit_post_state(run, receipt)
    assert ids == {'old'} and state_digest(snapshot) == state_digest(post_state())
    with pytest.raises(ValueError, match='digest'):
        d.audit_post_state(run, {**receipt, 'post_state_digest': '0'*64})
    with pytest.raises(ValueError, match='receipt'):
        d.audit_post_state(run, {**receipt, 'repeat_source_receipt_ids': ['made-up']})
    path = Path(receipt['post_snapshot_path']); path.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='checksum'):
        d.audit_post_state(run, receipt)
    path.unlink()
    with pytest.raises(ValueError, match='missing'):
        d.audit_post_state(run, receipt)


def test_unscored_started_owner_is_accounted_and_missing_owner_cannot_pass(tmp_path, monkeypatch):
    d = diagnostic()
    stage = tmp_path/'stage'; (stage/'jobs').mkdir(parents=True)
    run = stage/'runs'/('a'*32)
    run.mkdir(parents=True)
    job = {'run_id': 'a'*32, 'output': str(run), 'operation': 'repeat', 'spec': {'id': 'restore-1'}}
    (stage/'jobs'/('a'*32+'.json')).write_text(json.dumps(job))
    monkeypatch.setattr(p, 'validate_job', lambda value: value)
    monkeypatch.setattr(p, 'audit_run', lambda *args: (_ for _ in ()).throw(ValueError('partial recording')))
    rows = d.audit_owners(stage, {}, None)
    assert rows[0]['disposition'] == 'allocated-unstarted'
    (run/'owner.json').write_text(json.dumps({'pid': 999, 'starttime': 1, 'pgid': 999, 'run_id': 'a'*32}))
    monkeypatch.setattr(d, 'owner_exited', lambda value: True)
    rows = d.audit_owners(stage, {}, None)
    assert rows[0]['disposition'] == 'started-incomplete'
    assert rows[0]['matching_owner_exited'] is True
    assert rows[0]['raw_audit_pass'] is False


def test_diagnostic_budget_stops_before_new_job_allocation(tmp_path, monkeypatch):
    d = diagnostic(); plan = {'output': str(tmp_path), 'selected_profile_sha256':
        '7faba0a56d129ea051d5c28a019964034b546923dbe49cedb3a605af84437ec3'}
    monkeypatch.setattr(p, 'launch_owner', lambda *args, **kwargs: pytest.fail('expired owner admitted'))
    with pytest.raises(TimeoutError):
        d.run_pair(plan, p.phase_budget(tmp_path), 0., {})


def test_retention_storage_refusal_keeps_no_payload(tmp_path, monkeypatch):
    storage = p.phase_budget(tmp_path)
    run = tmp_path/'run'; (run/'snapshots').mkdir(parents=True)
    monkeypatch.setattr(storage, 'check', lambda *args, **kwargs: (_ for _ in ()).throw(OSError('storage refused')))
    with pytest.raises(OSError, match='refused'):
        p.publish_repeat_state(post_state(), {'old'}, run, storage)
    assert not (run/'snapshots/post-repeat.snp').exists()


def test_comparison_never_hides_signed_zero_or_dtype_changes():
    d = diagnostic(); one = post_state('one'); two = post_state('two')
    one['integration'] = np.array([0.], dtype=np.float64)
    two['integration'] = np.array([-0.], dtype=np.float64)
    result = d.compare_states(one, two, {'old'}, {'old'})
    assert not result['equal'] and result['differences'][0]['different_elements'] == 1
    two['integration'] = np.array([0.], dtype=np.float32)
    result = d.compare_states(one, two, {'old'}, {'old'})
    assert not result['equal']
    assert result['differences'][0]['right_dtype'] != result['differences'][0]['left_dtype']


def test_worker_option_rejects_public_stages_and_launch_rejects_nonrepeat(tmp_path):
    with pytest.raises(SystemExit):
        p.main(['--stage', 'preflight', '--retain-repeat-state'])
    with pytest.raises(ValueError, match='repeat'):
        p.launch_owner('travel-feasibility', {'operation': 'prefix'}, {},
                       p.phase_budget(tmp_path), 0, retain_repeat_state=True)
    assert not list(tmp_path.iterdir())


def test_offline_native_decode_exposes_changed_field_without_stepping():
    mujoco = pytest.importorskip('mujoco')
    d = diagnostic()
    model = mujoco.MjModel.from_xml_string('<mujoco><worldbody><body><freejoint/><geom size="0.1" mass="1"/></body></worldbody></mujoco>')
    left = mujoco.MjData(model)
    right = mujoco.MjData.__new__(mujoco.MjData); right.__setstate__(left.__getstate__())
    right.qpos[0] = .25
    one, two = {'native_data': left.__getstate__()}, {'native_data': right.__getstate__()}
    before = one['native_data']
    result = d.compare_native_states(one, two)
    assert 'qpos' in result['differing_components']
    assert not result['equal'] and one['native_data'] == before
    assert result['decoded_field_count'][0] > 100
    assert result['physics_steps'] == 0
    assert left.time == right.time == 0.


def test_launcher_keeps_checkout_clean_until_child_admission(tmp_path, monkeypatch):
    import importlib.util
    import subprocess
    path = Path(__file__).resolve().parents[1]/'docs/reports/memory-restore-diagnostic-evidence/execute-diagnostic.py'
    spec = importlib.util.spec_from_file_location('restore_launcher_test', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    evidence = tmp_path/'docs/reports/memory-restore-diagnostic-evidence'; evidence.mkdir(parents=True)
    workspace = tmp_path/'.superpowers/sdd/memory-restore-diagnostic'; workspace.mkdir(parents=True)
    (tmp_path/'.gitignore').write_text('.superpowers/\n')
    (evidence/'registration.json').write_text(json.dumps({'repo': str(tmp_path),
        'output': str(tmp_path/'runs/diagnostic'), 'python': '/not-executed/python'}))
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    subprocess.run(['git','-C',str(tmp_path),'add','.'],check=True)
    subprocess.run(['git','-C',str(tmp_path),'-c','user.name=Fixture','-c','user.email=fixture@example.test',
                    'commit','-qm','fixture'],check=True)
    monkeypatch.setattr(module, '__file__', str(evidence/'execute-diagnostic.py'))
    actual_run = subprocess.run
    native_calls = []
    def run(command, **kwargs):
        if command[0] != 'timeout':
            return actual_run(command, **kwargs)
        native_calls.append(command)
        # This is a real clean-check across the parent→child admission boundary.
        assert subprocess.check_output(['git','status','--porcelain'],cwd=tmp_path) == b''
        kwargs['stdout'].write('stubbed process; no native owner\n')
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(module.subprocess, 'run', run)
    assert module.main() == 0
    assert len(native_calls) == 1
    assert (evidence/'native-invocation.log').read_text() == 'stubbed process; no native owner\n'
    assert (workspace/'diagnostic-launched.json').exists()
    with pytest.raises(ValueError, match='clean'):
        module.main()
    assert len(native_calls) == 1
