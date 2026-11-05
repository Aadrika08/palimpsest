"""Authored source-owner checks; no native owner or retained payload is read."""
import copy
import importlib
from pathlib import Path
import uuid

import pytest

from palimpsest import memory, memory_decision_world as world


def runtime():
    return importlib.import_module('scripts.memory_family_source_runtime_v2')


def job(tmp_path):
    module = runtime()
    case = world.make_family_case('development', 0, 0, 'change')
    evidence = tmp_path / 'evidence'
    source = evidence / '.pending' / case['case_id']
    run_id = uuid.uuid4().hex
    control = evidence / 'controls' / run_id
    descriptor = lambda path: {'path': str(path), 'size_bytes': 1, 'sha256': 'a' * 64}
    value = {
        'schema': 'memory-family-source-job-v2', 'operation': 'source', 'condition': None,
        'split': 'development', 'block': 0, 'row': 0, 'kind': 'change', 'case': case,
        'run_id': run_id, 'protocol_sha256': module.PROTOCOL_SHA256,
        'source_identity_sha256': 'a' * 64,
        'immutable': {'python_alias': str(tmp_path / 'venv/bin/python'),
                      'python_elf': descriptor(tmp_path / 'python-elf'),
                      'owner_source': descriptor(Path(module.__file__)),
                      'closure': [descriptor(tmp_path / 'assets/model')]},
        'paths': {'repo': str(module.REPO_ROOT), 'assets': str(tmp_path / 'assets'),
                  'evidence_root': str(evidence), 'control_root': str(control),
                  'raw': str(source / '.raw' / run_id),
                  'snapshot': str(source / 'source/snapshots/initial.snp'),
                  'owner': str(source / 'source/owner.json'),
                  'error': str(control / (run_id + '.error.json'))},
        'limits': copy.deepcopy(module.LIMITS), 'parent_admission': None,
    }
    value['parent_admission'] = {
        'schema': 'memory-family-source-parent-admission-v2', 'admitted': True,
        'run_id': run_id, 'job_sha256': module.job_sha256(value),
        'allocation_sha256': 'b' * 64, 'deadline_monotonic': 999999999999.0}
    return value


def rebind(value):
    value['parent_admission']['job_sha256'] = runtime().job_sha256(value)
    return value


def refused_before_effects(monkeypatch, value):
    module = runtime()
    calls = []
    monkeypatch.setattr(module, '_check_identity', lambda value: pytest.fail('identity read before metadata acceptance'))
    monkeypatch.setattr(module, '_load_engine', lambda: calls.append('loader'))
    monkeypatch.setattr(module, '_write_json', lambda *a: calls.append('writer'))
    with pytest.raises((ValueError, PermissionError)):
        module.run_source(value)
    assert calls == []
    assert not Path(value['paths']['evidence_root']).exists()


def test_admission_precedes_model_import_and_output(tmp_path, monkeypatch):
    value = job(tmp_path)
    value['parent_admission'] = None
    refused_before_effects(monkeypatch, value)


@pytest.mark.parametrize('defect', ['heldout', 'seed', 'row', 'boolean'])
def test_rejects_heldout_or_changed_generator_case(tmp_path, monkeypatch, defect):
    value = job(tmp_path)
    if defect == 'heldout':
        value['case'] = world.make_family_case('held-out', 0, 0, 'change')
    elif defect == 'seed':
        value['case']['seed'] += 1
    elif defect == 'row':
        value['row'] = 1
    else:
        value['block'] = False
    refused_before_effects(monkeypatch, rebind(value))


@pytest.mark.parametrize('defect', ['history', 'asset', 'input-output', 'duplicate'])
def test_rejects_history_or_asset_alias(tmp_path, monkeypatch, defect):
    value = job(tmp_path)
    if defect == 'history':
        value['history'] = str(tmp_path / 'history')
    elif defect == 'asset':
        value['paths']['assets'] = value['paths']['evidence_root']
    elif defect == 'input-output':
        value['immutable']['closure'][0]['path'] = value['paths']['snapshot']
    else:
        value['immutable']['closure'].append(copy.deepcopy(value['immutable']['closure'][0]))
    refused_before_effects(monkeypatch, rebind(value))


@pytest.mark.parametrize('field', ['raw', 'snapshot', 'owner', 'error', 'control_root'])
def test_rejects_wrong_snapshot_raw_or_control_path(tmp_path, monkeypatch, field):
    value = job(tmp_path)
    value['paths'][field] = str(Path(value['paths']['raw']) / 'incorrect')
    refused_before_effects(monkeypatch, rebind(value))


@pytest.mark.parametrize('change', [{'operation': 'condition'}, {'condition': 'own'}, {'retry': 1}])
def test_no_condition_or_retry_entrypoint(tmp_path, monkeypatch, change):
    value = job(tmp_path)
    value.update(change)
    refused_before_effects(monkeypatch, rebind(value))


class AuthoredEngine:
    """Software-only control intervals; real recording and policy instrumentation."""
    def __init__(self, value, *, acquire=True, close_error=False):
        from types import SimpleNamespace
        from palimpsest import memory_decision as decision
        from palimpsest.records import RunWriter
        from test_memory_family_oracle_v3 import evidence
        from test_memory_family_raw_audit_v4 import _manifest
        from scripts import memory_family_raw_audit_v4 as audit
        self.job = value
        self.sample = evidence(row=0)
        old_id = self.sample['bindings']['source']['run_id']
        for event in self.sample['source_events']:
            if event.get('run_id') == old_id:
                event['run_id'] = value['run_id']
        self.sample['source_application']['source_run_id'] = value['run_id']
        manifest = _manifest(audit, value['case'], value['run_id'], 'source', None, None)
        self.writer = RunWriter(Path(value['paths']['raw']) / 'recording', manifest,
                                max_bytes=runtime().LIMITS['recording_max_bytes'])
        self.phase, self.controller, self.episode = 'paused', 'flynn', 0
        self.episode_step = self.total_tick = 0
        self.memory = decision.initialize(value['case'])
        self.eyes = {'left': True, 'right': True}
        self.world_task_state = world.initial_state(value['case'])
        self.last_outcome = None
        self.acquire, self.close_error, self.calls = acquire, close_error, 0
        self.policy = SimpleNamespace(device='cpu', act=self.act)
        self.teacher, self.env, self.observation = None, None, None

    def act(self, observation):
        self.calls += 1
        return {key: self.arrays[key] for key in ('action', 'encoded_input', 'raw_output')}

    def _event(self, kind, **values):
        self.writer.event(kind, run_id=self.job['run_id'], episode=0,
                          episode_step=self.episode_step, tick=self.total_tick, **values)

    def submit(self, command):
        assert command['kind'] == 'step'
        return {'status': 'queued'}

    def advance(self):
        from test_memory_family_raw_audit_v4 import _emit, _policy_row
        if not self.acquire:
            self.calls += 1
            self.episode_step += 1
            self.total_tick += 1
            return
        row = self.sample['source_rows'][self.episode_step]
        for event in self.sample['source_events']:
            if event['episode_step'] == self.episode_step:
                _emit(self.writer, event)
        policy, self.arrays = _policy_row(row, self.job['run_id'])
        self._event('memory_cue', bearing=[1.0, 0.0])
        self.policy.act({'cam_left': self.arrays['cam_left'],
                         'cam_right': self.arrays['cam_right'], 'sensors': policy['sensors']})
        self.writer.tick(0, self.episode_step, **self.arrays)
        self.episode_step += 1
        self.total_tick += 1
        if self.episode_step == len(self.sample['source_rows']):
            self.memory = copy.deepcopy(self.sample['source_application']['memory'])
            self.world_task_state = copy.deepcopy(self.sample['source_application']['world_task_state'])
            _emit(self.writer, self.sample['source_events'][-1])

    def application_state(self):
        from test_memory_family_raw_audit_v4 import _prefix
        self.writer.flush()
        application = copy.deepcopy(self.sample['source_application'])
        application['event_prefix'] = _prefix(self.writer)
        return application

    def close(self):
        # Mirror Engine.close: terminal world_state must already be in manifest.
        self.writer.finish({'run_id': self.job['run_id'], 'parent_run_id': None,
            'parent_event_prefix': None, 'final_phase': self.phase,
            'last_outcome': self.last_outcome, 'total_tick': self.total_tick,
            'close_reason': 'operator_closed'}, status='completed')
        self.writer.close()
        if self.close_error:
            raise RuntimeError('authored close failure')


def owner(tmp_path, monkeypatch, *, acquire=True, close_error=False, identity_error=False):
    from palimpsest.storage import StorageBudget, StorageLimits
    value = job(tmp_path)
    storage = StorageBudget([value['paths']['evidence_root']],
        StorageLimits(max_bytes=runtime().LIMITS['max_bytes'], min_free_bytes=0,
                      max_runs=1, max_snapshots=1))
    engines, captures, checks = [], [], []

    def open_engine(*args, **kwargs):
        assert kwargs['controller'] == 'flynn' and kwargs['device'] == 'cpu'
        assert kwargs['texture'] == 'checker' and 'restore_snapshot' not in kwargs
        engine = AuthoredEngine(value, acquire=acquire, close_error=close_error)
        engines.append(engine)
        return engine

    def capture(engine):
        captures.append((engine.episode_step, engine.calls, engine.phase))
        return {'application': engine.application_state()}

    def identity():
        checks.append(True)
        if identity_error and len(checks) > (2 if identity_error == 'late' else 1):
            raise ValueError('authored final identity failure')

    monkeypatch.setattr(runtime(), '_capture', capture)
    result = runtime()._run_admitted(value, storage, open_engine, identity)
    return value, result, engines, captures


def test_acquired_source_emits_exact_v4_manifest_and_report(tmp_path, monkeypatch):
    import hashlib
    import time
    from palimpsest import artifacts
    from scripts import memory_family_raw_audit_v4 as audit
    from scripts import memory_family_oracle_admission_v3 as admission
    value, result, engines, captures = owner(tmp_path, monkeypatch)
    assert result['status'] == 'recorded'
    report = result['report']
    assert set(report) == admission.REPORT_FIELDS
    run = Path(value['paths']['raw'])
    data = admission._read_run({'run': run, 'run_id': value['run_id']}, time.monotonic() + 20)
    admission._manifest(data, value['case'], audit.PROTOCOL_SHA256,
        value['source_identity_sha256'], operation='source', condition=None,
        source_snapshot_sha256=None)
    assert 'historical_lineage' not in data['manifest']
    path = Path(value['paths']['snapshot'])
    reference = {'path': f"cases/{value['case']['case_id']}/source/snapshots/initial.snp",
        'size_bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    audit_root = Path(value['paths']['control_root']) / 'audit'
    audit_root.mkdir()
    receipt = audit.audit_raw_run(run, audit_root,
        run_id=value['run_id'], case_id=value['case']['case_id'], operation='source',
        condition=None, source_run_id=None, source_snapshot_sha256=None,
        source_identity_sha256=value['source_identity_sha256'], deadline=time.monotonic() + 20,
        evidence_root=value['paths']['evidence_root'], snapshot_reference=reference)
    assert receipt['receipt']['oracle_result']['status'] == 'source-boundary-pass'
    assert artifacts._json((run / 'worker-report.json').read_bytes()) == report
    assert not (run / 'snapshots').exists()


def test_snapshot_is_captured_once_at_acquired_boundary(tmp_path, monkeypatch):
    from palimpsest import artifacts, snapshots
    value, result, engines, captures = owner(tmp_path, monkeypatch)
    assert result['status'] == 'recorded'
    engine = engines[0]
    assert captures == [(len(engine.sample['source_rows']), engine.calls, 'paused')]
    events = artifacts._events(Path(value['paths']['raw']))
    registrations = [row for row in events if row['kind'] == 'snapshot_registered']
    assert len(registrations) == 1
    assert registrations[0]['initial'] is True and registrations[0]['filename'] == 'initial.snp'
    snapshot = snapshots.read_snapshot(value['paths']['snapshot'])
    from scripts.memory_family_raw_audit_v4 import _prefix
    assert _prefix(snapshot['application'], Path(value['paths']['raw']) / 'recording/events.jsonl')
    assert len(list(Path(value['paths']['evidence_root']).rglob('*.snp'))) == 1
    assert not list(Path(value['paths']['evidence_root']).rglob('index.json'))


def test_source_limit_without_acquisition_is_unscored_failure(tmp_path, monkeypatch):
    value, result, engines, captures = owner(tmp_path, monkeypatch, acquire=False)
    assert result['status'] == 'failed' and result['report'] is None
    assert engines[0].calls == 1200 and captures == []
    assert not Path(value['paths']['snapshot']).exists()
    assert not (Path(value['paths']['raw']) / 'worker-report.json').exists()
    assert Path(result['error_path']).is_file()
    assert 'score' not in result and 'capped_ticks' not in result


@pytest.mark.parametrize('defect', ['close', 'identity'])
def test_close_or_identity_failure_prevents_export(tmp_path, monkeypatch, defect):
    value, result, engines, captures = owner(tmp_path, monkeypatch,
        close_error=defect == 'close', identity_error=defect == 'identity')
    assert result['status'] == 'failed' and result['report'] is None
    assert not (Path(value['paths']['raw']) / 'worker-report.json').exists()
    assert Path(value['paths']['snapshot']).is_file()
    assert Path(result['error_path']).is_file()


def test_no_policy_calls_after_acquired_boundary(tmp_path, monkeypatch):
    value, result, engines, captures = owner(tmp_path, monkeypatch)
    assert result['status'] == 'recorded'
    assert engines[0].calls == result['report']['total_ticks'] == captures[0][1]


def test_valid_job_is_pure_metadata_and_detached(tmp_path, monkeypatch):
    import builtins
    value = job(tmp_path)
    monkeypatch.setattr(builtins, 'open', lambda *a, **k: pytest.fail('payload read'))
    monkeypatch.setattr(Path, 'open', lambda *a, **k: pytest.fail('payload read'))
    admitted = runtime().validate_source_job(value)
    assert admitted == value and admitted is not value
    admitted['case']['seed'] += 1
    assert admitted != value


@pytest.mark.parametrize('field,value', [
    ('limit', True), ('size', -1), ('size', True), ('size', 1.0),
    ('deadline', float('nan')), ('deadline', float('inf')), ('deadline', True),
    ('deadline', -1), ('deadline', 0), ('run', 'ABCDEF'), ('unknown', []),
])
def test_rejects_signed_scalar_nonfinite_or_unknown_metadata(tmp_path, monkeypatch, field, value):
    candidate = job(tmp_path)
    if field == 'limit':
        candidate['limits']['source_steps'] = value
    elif field == 'size':
        candidate['immutable']['closure'][0]['size_bytes'] = value
    elif field == 'deadline':
        candidate['parent_admission']['deadline_monotonic'] = value
    elif field == 'run':
        candidate['run_id'] = value
    else:
        candidate[field] = value
    if field != 'deadline':
        rebind(candidate)
    refused_before_effects(monkeypatch, candidate)


def test_late_identity_failure_retains_raw_report_but_failed_outcome(tmp_path, monkeypatch):
    value, result, engines, captures = owner(tmp_path, monkeypatch, identity_error='late')
    assert result['status'] == 'failed' and result['report'] is None
    assert (Path(value['paths']['raw']) / 'worker-report.json').is_file()
    assert Path(result['error_path']).is_file()
    assert Path(value['paths']['snapshot']).is_file()


def test_exact_source_owner_record_passes_unchanged_schema(tmp_path, monkeypatch):
    from scripts import memory_family_producer_v4 as source
    value, result, engines, captures = owner(tmp_path, monkeypatch)
    payload = Path(value['paths']['owner']).read_bytes()
    parsed = source._canonical(payload, {'schema', 'case_id', 'run_id',
                                         'owner_source_sha256', 'claims'}, 'Source owner record')
    assert parsed == {'schema': 'memory-family-source-owner-v4',
        'case_id': value['case']['case_id'], 'run_id': value['run_id'],
        'owner_source_sha256': value['source_identity_sha256'],
        'claims': runtime().PROTOCOL['claims']}


def test_boundary_mismatch_is_rejected_before_snapshot_publication(tmp_path, monkeypatch):
    # owner() installs its own authored capture; intercept registration instead.
    register = runtime()._register_snapshot

    def corrupt(engine, value, storage):
        original_capture = runtime()._capture
        def capture(target):
            result = original_capture(target)
            result['application']['total_tick'] = True
            return result
        monkeypatch.setattr(runtime(), '_capture', capture)
        return register(engine, value, storage)

    monkeypatch.setattr(runtime(), '_register_snapshot', corrupt)
    value, result, engines, captures = owner(tmp_path, monkeypatch)
    assert result['status'] == 'failed'
    assert not Path(value['paths']['snapshot']).exists()


def test_invalid_prefix_is_rejected_by_unchanged_raw_audit(tmp_path, monkeypatch):
    import hashlib
    import time
    from palimpsest import snapshots
    from scripts import memory_family_raw_audit_v4 as audit
    original = runtime()._register_snapshot

    def corrupt(engine, value, storage):
        capture = runtime()._capture
        def changed(target):
            snapshot = capture(target)
            snapshot['application']['event_prefix']['sha256'] = '0' * 64
            return snapshot
        monkeypatch.setattr(runtime(), '_capture', changed)
        return original(engine, value, storage)

    monkeypatch.setattr(runtime(), '_register_snapshot', corrupt)
    value, result, engines, captures = owner(tmp_path, monkeypatch)
    assert result['status'] == 'recorded'
    path = Path(value['paths']['snapshot'])
    descriptor = {'path': f"cases/{value['case']['case_id']}/source/snapshots/initial.snp",
        'size_bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    audit_root = Path(value['paths']['control_root']) / 'audit'
    audit_root.mkdir()
    with pytest.raises(ValueError, match='prefix differs'):
        audit.audit_raw_run(value['paths']['raw'], audit_root,
            run_id=value['run_id'], case_id=value['case']['case_id'], operation='source',
            condition=None, source_run_id=None, source_snapshot_sha256=None,
            source_identity_sha256=value['source_identity_sha256'], deadline=time.monotonic() + 20,
            evidence_root=value['paths']['evidence_root'], snapshot_reference=descriptor)
    assert list(audit_root.iterdir()) == []
    assert snapshots.read_snapshot(path)['application']['event_prefix']['sha256'] == '0' * 64


def test_report_writer_failure_retains_raw_and_snp(tmp_path, monkeypatch):
    original = runtime()._write_json
    def write(path, value, storage):
        if Path(path).name == 'worker-report.json':
            raise OSError('authored report storage failure')
        return original(path, value, storage)
    monkeypatch.setattr(runtime(), '_write_json', write)
    value, result, engines, captures = owner(tmp_path, monkeypatch)
    assert result['status'] == 'failed' and result['report'] is None
    assert Path(value['paths']['snapshot']).is_file()
    assert (Path(value['paths']['raw']) / 'recording/manifest.json').is_file()
    assert Path(result['error_path']).is_file()


def test_public_existing_output_rejection_precedes_loader(tmp_path, monkeypatch):
    value = job(tmp_path)
    Path(value['paths']['snapshot']).parent.mkdir(parents=True)
    Path(value['paths']['snapshot']).write_bytes(b'authored preserved source')
    monkeypatch.setattr(runtime(), '_check_identity', lambda job: None)
    monkeypatch.setattr(runtime(), '_load_engine', lambda: pytest.fail('engine loader'))
    with pytest.raises(FileExistsError):
        runtime().run_source(value)
    assert Path(value['paths']['snapshot']).read_bytes() == b'authored preserved source'
    assert not Path(value['paths']['raw']).exists()


def test_final_identity_time_is_inside_owner_deadline(tmp_path, monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(runtime().time, 'monotonic', lambda: clock[0])
    original_write = runtime()._write_json
    def write(path, value, storage):
        original_write(path, value, storage)
        if Path(path).name == 'worker-report.json':
            # The final identity recheck consumes the remaining admitted time.
            clock[0] = 1359.0
    monkeypatch.setattr(runtime(), '_write_json', write)
    value = job(tmp_path)
    from palimpsest.storage import StorageBudget, StorageLimits
    storage = StorageBudget([value['paths']['evidence_root']],
        StorageLimits(max_bytes=runtime().LIMITS['max_bytes'], min_free_bytes=0))
    monkeypatch.setattr(runtime(), '_capture', lambda engine: {'application': engine.application_state()})
    calls = []
    def identity():
        calls.append(True)
        if len(calls) == 3:
            clock[0] = 1361.0
    result = runtime()._run_admitted(value, storage, lambda *a, **k: AuthoredEngine(value), identity)
    assert result['status'] == 'failed'
    assert Path(result['error_path']).is_file()


@pytest.mark.parametrize('path', ['//tmp/alias', '/tmp/../alias', '/tmp//alias', 'relative'])
def test_noncanonical_paths_refused(tmp_path, monkeypatch, path):
    value = job(tmp_path)
    value['immutable']['closure'][0]['path'] = path
    refused_before_effects(monkeypatch, rebind(value))


def test_import_and_metadata_validation_do_not_import_native_modules(tmp_path):
    import json
    import subprocess
    import sys
    value = job(tmp_path)
    code = ('import json,sys;'
            'from scripts.memory_family_source_runtime_v2 import validate_source_job;'
            'validate_source_job(json.loads(sys.stdin.read()));'
            "assert not set(sys.modules)&{'torch','mujoco','palimpsest.engine','palimpsest.flynn'}")
    result = subprocess.run([sys.executable, '-B', '-c', code], input=json.dumps(value),
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('defect', ['content', 'hardlink', 'symlink', 'alias'])
def test_authored_immutable_identity_checks_reject_drift_and_aliases(tmp_path, defect):
    import hashlib
    import os
    value = job(tmp_path)
    assets = Path(value['paths']['assets'])
    assets.mkdir()
    data = assets / 'authored-input'
    data.write_bytes(b'authored software input')
    elf = tmp_path / 'authored-interpreter'
    elf.write_bytes(b'authored interpreter identity only; never executed')
    alias = Path(value['immutable']['python_alias'])
    alias.parent.mkdir(parents=True)
    alias.symlink_to(elf)
    def descriptor(path):
        payload = path.read_bytes()
        return {'path': str(path), 'size_bytes': len(payload),
                'sha256': hashlib.sha256(payload).hexdigest()}
    value['immutable']['python_elf'] = descriptor(elf)
    value['immutable']['owner_source'] = descriptor(Path(runtime().__file__))
    value['immutable']['closure'] = [descriptor(data)]
    runtime()._check_identity(value)
    if defect == 'content':
        data.write_bytes(b'changed authored input')
    elif defect == 'hardlink':
        os.link(data, assets / 'authored-hardlink')
    elif defect == 'symlink':
        saved = data.with_suffix('.saved')
        data.rename(saved)
        data.symlink_to(saved)
    else:
        alias.rename(alias.with_suffix('.saved'))
        alias.symlink_to(data)
    with pytest.raises((ValueError, RuntimeError)):
        runtime()._check_identity(value)


def test_source_template_is_metadata_only_and_cannot_authorize_owner(tmp_path, monkeypatch):
    module = runtime()
    value = job(tmp_path)
    value['parent_admission'] = None
    monkeypatch.setattr(module, '_check_identity', lambda *a: pytest.fail('template opened payload'))
    assert module.validate_source_template(value) == value
    with pytest.raises(PermissionError, match='Missing'):
        module.validate_source_job(value)
    with pytest.raises(PermissionError, match='null'):
        module.validate_source_template(job(tmp_path))
    assert not Path(value['paths']['evidence_root']).exists()


def reference_job(tmp_path):
    """Independent metadata only: these pins do not describe installed bytes."""
    from scripts import memory_source_runtime_closure_v1 as closure
    value = job(tmp_path)
    value['schema'] = 'memory-family-source-job-v3'
    immutable = value['immutable']
    del immutable['closure']
    descriptor = lambda path: dict(path=str(path), size_bytes=0, sha256='a'*64)
    immutable['runtime_manifest'] = dict(
        schema='memory-source-runtime-reference-v1',
        profile_id='memory-source-runtime-profile-v1-proposed',
        profile_sha256=closure.PROFILE_SHA256, load_policy='retained-unqualified-v1',
        **{key: dict(descriptor(tmp_path / (key+'.json')), size_bytes=1)
           for key in ('recipe', 'manifest', 'ledger')})
    immutable['runtime_requirements'] = dict(
        roots=sorted([str(runtime().REPO_ROOT/name) for name in
                      ('src', 'scripts', 'paper/studies/change_audit_v1')]
                     + [str(tmp_path/'venv'), str(tmp_path/'base')]),
        pyvenv_config=descriptor(tmp_path/'venv/pyvenv.cfg'),
        required_sources=[descriptor(runtime().REPO_ROOT/'scripts'/name) for name in sorted([
            'memory_family_source_runtime_v2.py', 'qualify_memory_family_source_v2.py',
            'memory_source_runtime_closure_v1.py', 'memory_family_source_seal_v2.py',
            'memory_family_numeric_preservation_v2.py', 'memory_directory_census_v1.py'])])
    # The repeated owner pin must describe identical physical input bytes.
    immutable['owner_source']['size_bytes'] = 0
    value['parent_admission'].update(
        schema='memory-family-source-parent-admission-v3', deadline_monotonic=1200.0,
        runtime_deadline_monotonic=1800.0,
        runtime_manifest_sha256=immutable['runtime_manifest']['manifest']['sha256'],
        runtime_profile_sha256=closure.PROFILE_SHA256)
    return rebind(value)


def test_v2_job_rejects_reference_and_v3_rejects_closure(tmp_path):
    module = runtime()
    for version in (2, 3):
        value = reference_job(tmp_path)
        if version == 2:
            value['schema'] = 'memory-family-source-job-v2'
        else:
            value['immutable']['closure'] = []
        value['parent_admission'] = None
        with pytest.raises(ValueError): module.validate_source_template(value)
    value = reference_job(tmp_path); value['parent_admission'] = None
    assert module.validate_source_template(value) == value


def test_v3_template_never_constructs_holder_or_reads_pins(tmp_path, monkeypatch):
    import builtins
    import hashlib
    from scripts import memory_source_runtime_closure_v1 as closure
    value = reference_job(tmp_path); value['parent_admission'] = None
    def forbidden(*a, **k): pytest.fail('V3 template touched payload or loader')
    monkeypatch.setattr(closure, 'hold_runtime_manifest', forbidden)
    monkeypatch.setattr(closure, 'RuntimeHandle', forbidden)
    monkeypatch.setattr(runtime(), '_check_identity', forbidden)
    monkeypatch.setattr(runtime(), '_load_engine', forbidden)
    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(Path, 'resolve', forbidden)
    monkeypatch.setattr(hashlib, 'file_digest', forbidden)
    assert runtime().validate_source_template(value) == value
    assert not Path(value['paths']['evidence_root']).exists()


def test_v3_requirements_are_exact_independent_metadata(tmp_path):
    value = reference_job(tmp_path); value['parent_admission'] = None
    module = runtime()
    roots, pins = module._runtime_requirements(value)
    assert roots == tuple(value['immutable']['runtime_requirements']['roots'])
    assert pins['pyvenv_config']['size_bytes'] == pins['required_sources'][0]['size_bytes'] == 0
    assert module.validate_source_template(value) == value
    pins['required_sources'][0]['sha256'] = '0'*64
    assert value['immutable']['runtime_requirements']['required_sources'][0]['sha256'] == 'a'*64
    for defect in ('missing', 'extra', 'relative', 'overlap', 'unsorted', '17', 'config',
                   'duplicate', '65', 'contradiction', 'bool', 'bad-path', 'huge-file'):
        bad = copy.deepcopy(value); req = bad['immutable']['runtime_requirements']
        if defect == 'missing': del req['pyvenv_config']
        elif defect == 'extra': req['extra'] = 0
        elif defect == 'relative': req['roots'] = ['relative']
        elif defect == 'overlap': req['roots'] = ['/authored', '/authored/child']
        elif defect == 'unsorted': req['roots'] = ['/z', '/a']
        elif defect == '17': req['roots'] = [f'/r{i:02}' for i in range(17)]
        elif defect == 'config': req['pyvenv_config']['path'] = '/wrong/pyvenv.cfg'
        elif defect == 'duplicate': req['required_sources'] *= 2
        elif defect == '65': req['required_sources'] = [dict(req['pyvenv_config'], path=f'/s{i:02}') for i in range(65)]
        elif defect == 'contradiction':
            next(row for row in req['required_sources'] if row['path'] == bad['immutable']['owner_source']['path'])['size_bytes'] = 1
        elif defect == 'bool': req['pyvenv_config']['size_bytes'] = False
        elif defect == 'bad-path': req['roots'] = ['/a\\b']
        else: req['pyvenv_config']['size_bytes'] = 2**31+1
        with pytest.raises(ValueError): module.validate_source_template(bad)
    # Returned collections do not change if the caller changes its job.
    roots, pins = module._runtime_requirements(value)
    value['immutable']['runtime_requirements']['roots'][0] = '/changed'
    value['immutable']['runtime_requirements']['pyvenv_config']['sha256'] = '0'*64
    assert '/changed' not in roots and pins['pyvenv_config']['sha256'] == 'a'*64


def test_v3_admission_binds_manifest_profile_and_deadlines(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime().time, 'monotonic', lambda: 1000.0)
    value = reference_job(tmp_path)
    assert runtime().validate_source_job(value) == value
    for key, bad in [('runtime_manifest_sha256', '0'*64), ('runtime_profile_sha256', '0'*64),
                     ('deadline_monotonic', 1361.0), ('deadline_monotonic', 1801.0),
                     ('runtime_deadline_monotonic', 1901.0), ('runtime_deadline_monotonic', 1199.0),
                     ('runtime_deadline_monotonic', True), ('runtime_deadline_monotonic', 999.0),
                     ('runtime_deadline_monotonic', float('nan')),
                     ('deadline_monotonic', True), ('deadline_monotonic', float('inf'))]:
        candidate = copy.deepcopy(value); candidate['parent_admission'][key] = bad
        with pytest.raises((ValueError, PermissionError)): runtime().validate_source_job(candidate)


def test_v2_admission_schema_cannot_admit_v3(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime().time, 'monotonic', lambda: 1000.0)
    value = reference_job(tmp_path)
    value['parent_admission'] = job(tmp_path)['parent_admission']
    rebind(value)
    with pytest.raises((ValueError, PermissionError)): runtime().validate_source_job(value)
    value = job(tmp_path); value['parent_admission'] = reference_job(tmp_path)['parent_admission']
    rebind(value)
    with pytest.raises((ValueError, PermissionError)): runtime().validate_source_job(value)


def test_public_v3_owner_refuses_before_payload_or_loader(tmp_path, monkeypatch):
    import builtins
    from scripts import memory_source_runtime_closure_v1 as closure
    monkeypatch.setattr(runtime().time, 'monotonic', lambda: 1000.0)
    value = reference_job(tmp_path)
    def forbidden(*a, **k): pytest.fail('public V3 crossed retained-unqualified gate')
    for name in ('_check_identity', '_load_engine', '_storage', '_safe_path', '_write_json'):
        monkeypatch.setattr(runtime(), name, forbidden)
    monkeypatch.setattr(closure, 'hold_runtime_manifest', forbidden)
    monkeypatch.setattr(closure, 'RuntimeHandle', forbidden)
    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr(Path, 'open', forbidden)
    with pytest.raises(PermissionError, match='retained-unqualified'):
        runtime().run_source(value)
    assert not Path(value['paths']['evidence_root']).exists()


@pytest.mark.parametrize('target', ['root', 'pin', 'alias', 'recipe', 'manifest', 'ledger', 'asset'])
def test_v3_rejects_output_overlap_with_every_declared_input(tmp_path, target):
    value = reference_job(tmp_path); value['parent_admission'] = None
    immutable = value['immutable']; output = value['paths']['evidence_root']
    if target == 'root': immutable['runtime_requirements']['roots'] = [output]
    elif target == 'pin': immutable['python_elf']['path'] = output+'/elf'
    elif target == 'alias':
        immutable['python_alias'] = output+'/bin/python'
        immutable['runtime_requirements']['pyvenv_config']['path'] = output+'/pyvenv.cfg'
    elif target == 'asset': value['paths']['assets'] = output+'/assets'
    else: immutable['runtime_manifest'][target]['path'] = output+'/'+target
    with pytest.raises(ValueError): runtime().validate_source_template(value)


def test_v3_complete_admitted_job_envelope_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime().time, 'monotonic', lambda: 1000.0)
    value = reference_job(tmp_path)
    # A structurally valid long assets path leaves the hash-excluded envelope legal,
    # while the complete admitted representation is one byte beyond its cap.
    # Repeated lexical root components create bounded canonical paths/strings.
    req = value['immutable']['runtime_requirements']
    req['required_sources'] = [dict(path='/'+'/'.join(['x'*236]*16)+f'/s{i:02}',
                                    size_bytes=0, sha256='a'*64) for i in range(64)]
    base_size = len(memory.canonical_bytes(value))
    padding = 256*1024+1-base_size
    assert 0 < padding < 4096
    length = len(value['paths']['assets']) + padding
    parts = []
    while length > 256:
        parts.append('a'*250); length -= 251
    parts.append('a'*(length-1))
    value['paths']['assets'] = '/' + '/'.join(parts)
    rebind(value)
    assert len(memory.canonical_bytes(value)) == 256*1024+1
    runtime().job_sha256(value)
    with pytest.raises(ValueError, match='256 KiB'): runtime().validate_source_job(value)


def private_owner_inputs(tmp_path, monkeypatch, *, acquire=True, close_error=False,
                         fail_recheck=False):
    """Process-local authored handle and engine; no installed file is visited."""
    from palimpsest.storage import StorageBudget, StorageLimits
    module = runtime()
    clock = [1000.0]
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    value = reference_job(tmp_path)
    monkeypatch.setattr(module.sys, 'executable', value['immutable']['python_alias'])
    monkeypatch.setattr(module.sys, 'prefix', str(tmp_path/'venv'))
    monkeypatch.setattr(module.sys, 'base_prefix', str(tmp_path/'base'))
    # Only these existing post-gate symlink identity lookups are substituted.
    resolve = Path.resolve
    def authored_resolve(path, *a, **k):
        if str(path) in (value['immutable']['python_alias'], '/proc/self/exe'):
            return Path(value['immutable']['python_elf']['path'])
        return resolve(path, *a, **k)
    monkeypatch.setattr(Path, 'resolve', authored_resolve)
    Path(value['paths']['assets']).mkdir()
    storage = StorageBudget([value['paths']['evidence_root']],
        StorageLimits(max_bytes=module.LIMITS['max_bytes'], min_free_bytes=0,
                      max_runs=1, max_snapshots=1))
    events, contexts, factories, open_calls = [], [], [], []

    class AuthoredHandle:
        active = False
        def __enter__(self):
            assert not self.active
            self.active = True
            events.append('enter'); self.check()
            return self
        def recheck(self):
            assert self.active, 'identity callback used released handle'
            events.append('recheck'); self.check()
            if fail_recheck and 'report' in events:
                raise RuntimeError('authored custody drift')
        def descriptor(self, path):
            self.recheck()
            rows = [self.pins[k] for k in ('python_elf', 'owner_source', 'pyvenv_config')]
            rows += self.pins['required_sources']
            return copy.deepcopy(next(row for row in rows if row['path'] == path))
        def __exit__(self, *exc):
            try:
                self.recheck()
                events.append('release')
                if close_error:
                    raise RuntimeError('authored handle close failure')
            finally:
                self.active = False
            return False

    def factory(reference, **kwargs):
        factories.append((copy.deepcopy(reference), copy.deepcopy({k:v for k,v in kwargs.items() if k != 'check'})))
        held = AuthoredHandle(); held.pins = kwargs['required_pins']; held.check = kwargs['check']
        contexts.append(held)
        return held

    def loader():
        assert contexts[-1].active
        events.append('loader')
        def opener(*args, **kwargs):
            assert contexts[-1].active
            open_calls.append((args, kwargs))
            events.append('engine')
            return AuthoredEngine(value, acquire=acquire)
        return opener

    original_write = module._write_json
    def write(path, payload, budget):
        assert contexts[-1].active
        if Path(path).name == 'worker-report.json': events.append('report')
        if str(path) == value['paths']['error']: events.append('failure')
        return original_write(path, payload, budget)
    monkeypatch.setattr(module, '_write_json', write)
    monkeypatch.setattr(module, '_capture', lambda engine: {'application': engine.application_state()})
    monkeypatch.setattr(module, '_load_engine', lambda: pytest.fail('real engine factory reached'))
    monkeypatch.setattr(module, '_check_identity', lambda *a: pytest.fail('V2 closure identity reached'))
    return value, storage, factory, loader, events, contexts, factories, open_calls, clock


def test_private_v3_owner_acquires_its_own_handle(tmp_path, monkeypatch):
    value, storage, factory, loader, events, contexts, calls, opened, clock = private_owner_inputs(tmp_path, monkeypatch)
    charged = []
    outcome = runtime()._run_reference_admitted(value, storage, check=lambda: charged.append(True),
        runtime_handle_factory=factory, engine_loader=loader)
    assert outcome['status'] == 'recorded' and outcome['schema'] == 'memory-family-source-owner-outcome-v3'
    assert len(contexts) == 1 and contexts[0].active is False
    assert events.index('enter') < events.index('loader') < events.index('engine')
    assert events.count('loader') == 1 and events.count('recheck') >= 4
    assert len(charged) >= 4
    assert not Path(value['paths']['error']).exists()


@pytest.mark.parametrize('source_count', [6, 64])
def test_private_v3_immutable_pins_checked_once_and_callbacks_have_constant_cost(tmp_path, monkeypatch, source_count):
    module = runtime()
    value, storage, factory, loader, events, contexts, calls, opened, clock = private_owner_inputs(tmp_path, monkeypatch)
    sources = value['immutable']['runtime_requirements']['required_sources']
    sources.extend(dict(path=str(tmp_path/f'extra-source-{i:02d}.py'), size_bytes=0, sha256='b'*64)
                   for i in range(source_count-len(sources)))
    sources.sort(key=lambda row: row['path']); rebind(value)
    lookups, accessor_costs, layout_calls, callback_costs, before_loader = [], [], [], [], []
    original_factory, original_layout = factory, module._check_reference_layout

    def factory(*args, **kwargs):
        held = original_factory(*args, **kwargs)
        rows = [held.pins[k] for k in ('python_elf', 'owner_source', 'pyvenv_config')]
        rows += held.pins['required_sources']
        held._records = {row['path']: copy.deepcopy(row) for row in rows}
        # Execute the actual accessor against an authored, no-IO holder proxy.
        def active():
            assert held.active
        def poison():
            pytest.fail('unexpected accessor poisoning in valid authored pins')
        held._active, held._poison = active, poison
        def descriptor(path):
            assert 'enter' in events
            before_loader.append('loader' not in events)
            before = events.count('recheck')
            result = module.closure.RuntimeHandle.descriptor(held, path)
            accessor_costs.append(events.count('recheck')-before)
            lookups.append(path)
            return result
        held.descriptor = descriptor
        return held

    def layout(*args):
        layout_calls.append(True)
        return original_layout(*args)

    repetitions = 7
    def core(job, budget, opener, identity):
        assert callable(opener) and events.count('loader') == 1
        for _ in range(repetitions):
            before = (events.count('recheck'), len(lookups), len(layout_calls))
            identity()
            callback_costs.append((events.count('recheck')-before[0],
                len(lookups)-before[1], len(layout_calls)-before[2]))
        return {'status': 'recorded'}

    monkeypatch.setattr(module, '_check_reference_layout', layout)
    monkeypatch.setattr(module, '_run_admitted', core)
    result = module._run_reference_admitted(value, storage, check=lambda: None,
        runtime_handle_factory=factory, engine_loader=loader)
    assert result['status'] == 'recorded'
    pins = module._runtime_requirements(value)[1]
    expected = [pins[k]['path'] for k in ('python_elf','owner_source','pyvenv_config')]
    expected += [row['path'] for row in pins['required_sources']]
    assert callback_costs == [(1, 0, 1)]*repetitions
    assert lookups == expected and all(before_loader)
    assert accessor_costs == [2]*(3+source_count)
    assert len(layout_calls) == repetitions+4  # Pre-entry plus every lifecycle identity.
    assert events[-1] == 'release' and not contexts[0].active
    assert opened == []  # The stub core never opens even an authored engine.


def test_private_v3_owner_passes_complete_independent_requirements(tmp_path, monkeypatch):
    value, storage, factory, loader, events, contexts, calls, opened, clock = private_owner_inputs(tmp_path, monkeypatch)
    runtime()._run_reference_admitted(value, storage, check=lambda: None,
        runtime_handle_factory=factory, engine_loader=loader)
    reference, kwargs = calls[0]
    immutable = value['immutable']; req = immutable['runtime_requirements']
    assert reference == immutable['runtime_manifest']
    assert kwargs == dict(required_roots=tuple(req['roots']),
        required_pins=dict(python_alias=immutable['python_alias'], python_elf=immutable['python_elf'],
            owner_source=immutable['owner_source'], pyvenv_config=req['pyvenv_config'],
            required_sources=req['required_sources']),
        output_root=value['paths']['evidence_root'], deadline=1800.0)


@pytest.mark.parametrize('defect', ['helper', 'config', 'prefix', 'alias', 'elf', 'held-pin'])
def test_private_v3_missing_live_layout_refuses_before_engine_loader(tmp_path, monkeypatch, defect):
    value, storage, factory, loader, events, contexts, calls, opened, clock = private_owner_inputs(tmp_path, monkeypatch)
    req = value['immutable']['runtime_requirements']
    if defect == 'helper':
        req['required_sources'] = [row for row in req['required_sources'] if not row['path'].endswith('memory_directory_census_v1.py')]
    elif defect == 'config': req['pyvenv_config']['path'] = str(tmp_path/'wrong.cfg')
    elif defect == 'prefix':
        req['roots'] = [root for root in req['roots'] if root != str(tmp_path/'base')]
    elif defect == 'alias': monkeypatch.setattr(runtime().sys, 'executable', '/authored/other-alias')
    elif defect == 'elf':
        original = Path.resolve
        monkeypatch.setattr(Path, 'resolve', lambda path, *a, **k:
            Path('/authored/other-elf') if str(path) == '/proc/self/exe' else original(path, *a, **k))
    else:
        original_factory = factory
        def factory(*a, **k):
            held = original_factory(*a, **k)
            descriptor = held.descriptor
            held.descriptor = lambda path: dict(descriptor(path), sha256='0'*64)
            return held
    rebind(value)
    with pytest.raises((ValueError, PermissionError)):
        runtime()._run_reference_admitted(value, storage, check=lambda: None,
            runtime_handle_factory=factory, engine_loader=loader)
    assert 'loader' not in events and opened == []
    assert not Path(value['paths']['evidence_root']).exists()


@pytest.mark.parametrize('name', [
    'memory_family_source_runtime_v2.py', 'qualify_memory_family_source_v2.py',
    'memory_source_runtime_closure_v1.py', 'memory_family_source_seal_v2.py',
    'memory_family_numeric_preservation_v2.py', 'memory_directory_census_v1.py'])
def test_private_v3_requires_each_named_live_source(tmp_path, monkeypatch, name):
    value, storage, factory, loader, events, contexts, calls, opened, clock = private_owner_inputs(tmp_path, monkeypatch)
    req = value['immutable']['runtime_requirements']
    req['required_sources'] = [row for row in req['required_sources'] if Path(row['path']).name != name]
    rebind(value)
    with pytest.raises(ValueError, match='sources'):
        runtime()._run_reference_admitted(value, storage, check=lambda: None,
            runtime_handle_factory=factory, engine_loader=loader)
    assert not calls and not opened


@pytest.mark.parametrize('root', ['src', 'scripts', 'paper/studies/change_audit_v1', 'venv', 'base'])
def test_private_v3_requires_every_live_prefix(tmp_path, monkeypatch, root):
    value, storage, factory, loader, events, contexts, calls, opened, clock = private_owner_inputs(tmp_path, monkeypatch)
    omitted = tmp_path/root if root in ('venv', 'base') else runtime().REPO_ROOT/root
    req = value['immutable']['runtime_requirements']
    req['roots'].remove(str(omitted)); rebind(value)
    with pytest.raises(ValueError, match='roots'):
        runtime()._run_reference_admitted(value, storage, check=lambda: None,
            runtime_handle_factory=factory, engine_loader=loader)
    assert not calls and not opened


def test_owner_source_deadline_includes_handle_teardown(tmp_path, monkeypatch):
    value, storage, factory, loader, events, contexts, calls, opened, clock = private_owner_inputs(tmp_path, monkeypatch)
    original_factory = factory
    def factory(*a, **k):
        held = original_factory(*a, **k)
        recheck = held.recheck
        def delayed():
            if 'report' in events:
                clock[0] = 1200.0
            recheck()
        held.recheck = delayed
        return held
    with pytest.raises(TimeoutError):
        runtime()._run_reference_admitted(value, storage, check=lambda: None,
            runtime_handle_factory=factory, engine_loader=loader)
    assert contexts[0].active is False
    assert (Path(value['paths']['raw'])/'worker-report.json').is_file()
    assert Path(value['paths']['error']).is_file()


@pytest.mark.parametrize('path', ['/authored/a:b', '/authored/a\\b', '/authored/a\x01b',
                                '/authored/'+'é'*128, '/authored/'+'a'*256])
def test_v3_asset_paths_obey_canonical_posix_byte_bounds(tmp_path, path):
    value = reference_job(tmp_path); value['parent_admission'] = None
    value['paths']['assets'] = path
    with pytest.raises(ValueError): runtime().validate_source_template(value)


def test_private_v3_engine_loader_returns_opener(tmp_path, monkeypatch):
    value, storage, factory, loader, events, contexts, calls, opened, clock = private_owner_inputs(tmp_path, monkeypatch)
    outcome = runtime()._run_reference_admitted(value, storage, check=lambda: None,
        runtime_handle_factory=factory, engine_loader=loader)
    assert outcome['status'] == 'recorded'
    args, kwargs = opened[0]
    assert args == (value['paths']['repo'], value['paths']['assets'], Path(value['paths']['raw'])/'recording')
    assert kwargs == dict(controller='flynn', device='cpu', texture='checker', seed=value['case']['seed'],
        scenario=world.SCENARIO, memory_case=value['case'], run_id=value['run_id'],
        max_bytes=512*1024**2, storage_budget=storage)


def test_owner_uses_parent_runtime_deadline_without_reset(tmp_path, monkeypatch):
    value, storage, factory, loader, events, contexts, calls, opened, clock = private_owner_inputs(tmp_path, monkeypatch)
    # Simulate admission earlier in the same parent window, not a new interval.
    clock[0] = 1199.0
    original = factory
    def delayed(*args, **kwargs):
        assert kwargs['deadline'] == 1800.0
        held = original(*args, **kwargs)
        clock[0] = 1200.0
        return held
    with pytest.raises(TimeoutError):
        runtime()._run_reference_admitted(value, storage, check=lambda: None,
            runtime_handle_factory=delayed, engine_loader=loader)
    assert calls[0][1]['deadline'] == 1800.0 and 'loader' not in events
    assert not Path(value['paths']['evidence_root']).exists()


def test_owner_final_checks_run_before_handle_release(tmp_path, monkeypatch):
    value, storage, factory, loader, events, contexts, calls, opened, clock = private_owner_inputs(tmp_path, monkeypatch)
    runtime()._run_reference_admitted(value, storage, check=lambda: None,
        runtime_handle_factory=factory, engine_loader=loader)
    assert 'recheck' in events[events.index('report')+1:events.index('release')]
    assert events[-1] == 'release'


@pytest.mark.parametrize('defect', ['drift', 'close-recorded', 'close-failed'])
def test_owner_custody_failure_prevents_recorded_outcome(tmp_path, monkeypatch, defect):
    value, storage, factory, loader, events, contexts, calls, opened, clock = private_owner_inputs(
        tmp_path, monkeypatch, acquire=defect != 'close-failed', close_error=defect != 'drift',
        fail_recheck=defect == 'drift')
    first_failure = []
    original = runtime()._write_json
    def write(path, payload, budget):
        original(path, payload, budget)
        if str(path) == value['paths']['error']:
            first_failure.append(Path(path).read_bytes())
    monkeypatch.setattr(runtime(), '_write_json', write)
    with pytest.raises(RuntimeError, match='authored (custody drift|handle close failure)'):
        runtime()._run_reference_admitted(value, storage, check=lambda: None,
            runtime_handle_factory=factory, engine_loader=loader)
    assert contexts[0].active is False
    if defect != 'close-recorded':
        assert len(first_failure) == 1
        assert Path(value['paths']['error']).read_bytes() == first_failure[0]
        assert b'"schema":"memory-family-source-owner-failure-v3"' in first_failure[0]
    else:
        assert (Path(value['paths']['raw'])/'worker-report.json').is_file()
        assert not Path(value['paths']['error']).exists()
    assert Path(value['paths']['raw']).exists()


@pytest.mark.parametrize('version', [2, 3])
@pytest.mark.parametrize('acquire', [True, False])
def test_owner_outcome_and_failure_versions_selected_before_write(tmp_path, monkeypatch, version, acquire):
    if version == 2:
        value, result, engines, captures = owner(tmp_path, monkeypatch, acquire=acquire)
    else:
        value, storage, factory, loader, events, contexts, calls, opened, clock = private_owner_inputs(
            tmp_path, monkeypatch, acquire=acquire)
        result = runtime()._run_reference_admitted(value, storage, check=lambda: None,
            runtime_handle_factory=factory, engine_loader=loader)
    assert result['schema'] == f'memory-family-source-owner-outcome-v{version}'
    assert result['status'] == ('recorded' if acquire else 'failed')
    if not acquire:
        # The complete first-write canonical V2 bytes retain their old schema/fields.
        golden = memory.canonical_bytes(dict(schema=f'memory-family-source-owner-failure-v{version}',
            run_id=value['run_id'], job_sha256=runtime().job_sha256(value), status='failed',
            error=dict(type='ValueError', message='Source step limit/termination without acquired boundary is unscored'),
            qualification_claims=False))
        assert Path(value['paths']['error']).read_bytes() == golden


def test_unknown_core_job_schema_refuses_before_any_write(tmp_path, monkeypatch):
    value = job(tmp_path); value['schema'] = 'unknown'
    monkeypatch.setattr(runtime(), '_write_json', lambda *a: pytest.fail('unknown schema wrote failure'))
    with pytest.raises(ValueError, match='schema'):
        runtime()._run_admitted(value, None, lambda *a: pytest.fail('loader'), lambda: None)
    assert not Path(value['paths']['evidence_root']).exists()
