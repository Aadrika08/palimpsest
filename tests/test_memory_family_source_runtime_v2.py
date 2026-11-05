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
