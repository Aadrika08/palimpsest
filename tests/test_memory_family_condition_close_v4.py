"""Authored condition-close orchestration; never production model qualification."""
from contextlib import contextmanager
import copy
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest

from palimpsest import artifacts, memory, snapshots
from palimpsest.records import RunWriter
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_producer_v4 as producer
from scripts import memory_family_raw_audit_v4 as audit
from test_memory_family_producer_v4 import fixture as source_fixture, request as source_request
from test_memory_family_oracle_v3 import evidence
from test_memory_family_oracle_admission_v4 import _histories, _condition_values, _condition_events
from test_memory_family_raw_audit_v4 import _manifest, _emit_trace, _finish, _report

ROOT = Path(__file__).parents[1]
NAME = 'scripts.memory_family_condition_seal_v4'


def module():
    assert importlib.util.find_spec(NAME) is not None, 'Condition seal is missing'
    return importlib.import_module(NAME)


def descriptor(path, payload):
    return {'path': str(path), 'size_bytes': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest()}


def write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value if type(value) is bytes else memory.canonical_bytes(value)
    path.write_bytes(payload)
    return descriptor(relative, payload)


def tree(root):
    return {p.relative_to(root).as_posix(): p.read_bytes()
            for p in root.rglob('*') if p.is_file()}


def fixture(root, *, natural_failure=False):
    """Real independent raw audit/converter/pair; only cell/model seams are authored."""
    source = source_fixture(root)
    producer.seal_compact_source(**source_request(source))
    case = source['sample']['case']
    case_id = case['case_id']
    case_path = root / '.pending' / case_id
    condition = 'own'
    run_id = source['sample']['condition']['run_id']
    raw = case_path / '.raw' / run_id
    # The original fixture's raw own selector predates v4 history descriptors.
    # Build a new authored trace with v4's exact mapping before either raw audit.
    sample = evidence(row=4)
    application = snapshots.read_snapshot(source['snapshot'])['application']
    histories = _histories(root, case)
    selector, u, _ = _condition_values(condition, case, histories, application)
    events, schedule, condition_world, last_outcome = _condition_events(
        sample, condition, run_id, selector, u, application,
        natural_failure=natural_failure)
    writer = RunWriter(raw / 'recording', _manifest(
        audit, case, run_id, 'condition', condition, source['contract']['snapshot']['sha256'],
        parent_run_id=source['contract']['run_id'],
        parent_event_prefix=application['event_prefix']),
        max_bytes=audit.RAW_LIMITS['condition']['recording_max_bytes'])
    _emit_trace(writer, events, sample['post_rows'])
    total = sample['post_world_state']['last_tick'] + 1
    _finish(writer, total, condition_world,
            'failed' if natural_failure else 'paused', last_outcome)
    _report(raw / 'worker-report.json', run_id=run_id, case=case,
        operation='condition', condition=condition,
        snapshot_sha256=source['contract']['snapshot']['sha256'],
        source_snapshot_sha256=source['contract']['snapshot']['sha256'],
        total_ticks=total, world_state=condition_world,
        final_phase='failed' if natural_failure else 'paused')
    receipts = root / 'condition-audits'
    receipts.mkdir()
    command = [sys.executable, str(ROOT / 'scripts/memory_family_raw_audit_v4.py'),
        '--run', str(raw), '--receipt-root', str(receipts), '--run-id', run_id,
        '--case-id', case_id, '--operation', 'condition', '--condition', condition,
        '--source-run-id', source['contract']['run_id'],
        '--source-snapshot-sha256', source['contract']['snapshot']['sha256'],
        '--source-identity-sha256', source['contract']['owner_source_sha256'],
        '--deadline-seconds', '30']
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    assert result.returncode == 0, result.stderr
    receipt = artifacts._json(result.stdout.encode())
    raw_audit = descriptor(Path(receipt['path']).relative_to(root),
                           Path(receipt['path']).read_bytes())
    path = case_path / 'conditions' / condition
    path.mkdir(parents=True)
    owner = {'schema': 'memory-family-condition-owner-v1', 'case_id': case_id,
        'run_id': run_id, 'condition': condition,
        'source_run_id': source['contract']['run_id'],
        'owner_source_sha256': source['contract']['owner_source_sha256'],
        'claims': copy.deepcopy(compact.PROTOCOL['claims'])}
    owner_descriptor = write(root,
        f'.pending/{case_id}/conditions/{condition}/owner.json', owner)
    owner_descriptor['path'] = f'cases/{case_id}/conditions/{condition}/owner.json'
    controls = {role: write(root, f'condition-controls/{role}.json',
        b'' if role in ('stdout', 'stderr') else {'closed': True})
        for role in ('job', 'supervisor', 'stdout', 'stderr', 'cleanup')}
    controls['audit'] = raw_audit
    qualification = write(root, 'qualification.json', {'authored': True})
    extension = ROOT / module().EXTENSION_PATH
    contract = {'schema': 'memory-family-condition-finalization-registration-v1',
        'protocol_sha256': compact.PROTOCOL_SHA256,
        'extension_sha256': hashlib.sha256(extension.read_bytes()).hexdigest(),
        'case': case, 'run_id': run_id, 'condition': condition,
        'source_run_id': source['contract']['run_id'],
        'owner_source_sha256': source['contract']['owner_source_sha256'],
        'source': {'registration': source['registration'],
            'commit': descriptor(f'cases/{case_id}/source/commit.json',
                (source['source'] / 'commit.json').read_bytes()),
            'snapshot': source['contract']['snapshot']},
        'raw_audit': raw_audit, 'owner_record': owner_descriptor,
        'controls': controls,
        'history_bundles': {role: value['descriptor'] for role, value in histories.items()},
        'prior_own_receipt': None, 'qualification': qualification,
        'claims': copy.deepcopy(compact.PROTOCOL['claims'])}
    registration = write(root, 'condition-terminal-export.json', contract)
    return {'root': root, 'source': source, 'path': path, 'raw': raw,
            'contract': contract, 'registration': registration, 'schedule': schedule}


def request(sample):
    return {'evidence_root': sample['root'], 'registration': sample['registration'],
        'case_id': sample['contract']['case']['case_id'], 'condition': 'own',
        'deadline': time.monotonic() + 30}


def authored_replay(monkeypatch, sample):
    """Only orchestration is proved: no production model or qualification exists."""
    m = module()
    calls = []
    @contextmanager
    def qualified(root, value, *, deadline):
        assert value == sample['contract']['qualification']
        class Session:
            policy = object()
            descriptor = value
            def recheck(self):
                calls.append('recheck')
        yield Session()
    def replay(**values):
        calls.append('production-replay')
        read = compact.read_compact(values['bundle'], raw_audit_receipt=values['raw_audit_receipt'])
        manifest = read['manifest']
        return {'schema': 'memory-family-cell-replay-v4',
            'protocol_sha256': compact.PROTOCOL_SHA256,
            'case_id': manifest['case_id'], 'run_id': manifest['run_id'],
            'operation': 'condition', 'trace_digest': read['trace_digest'],
            'source_snapshot_reference': copy.deepcopy(read['snapshot_reference']),
            'rows_checked': manifest['row_count'], 'raw_output_equal': True,
            'action_equal': True, 'source_endpoint_verified': False,
            'initial_hidden_sha256': 'a' * 64, 'final_hidden_sha256': 'b' * 64,
            'claims': copy.deepcopy(compact.PROTOCOL['claims'])}
    monkeypatch.setattr(m, '_qualified_replay', qualified)
    monkeypatch.setattr(m, '_require_qualification_pin', lambda value: None)
    monkeypatch.setattr(m, '_production_replay', replay)
    return calls


def test_condition_entrypoint_exists_and_import_is_pure():
    m = module()
    assert callable(m.seal_compact_condition)
    result = subprocess.run([sys.executable, '-B', '-c',
        "import sys; import scripts.memory_family_condition_seal_v4; "
        "assert not set(sys.modules)&{'torch','mujoco','palimpsest.engine','palimpsest.model'}"],
        cwd=ROOT, env={**os.environ, 'PYTHONPATH': 'src:.'}, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


def test_real_raw_conversion_pair_seals_with_authored_cell_seams(tmp_path, monkeypatch):
    sample = fixture(tmp_path / 'case')
    calls = authored_replay(monkeypatch, sample)
    raw = tree(sample['raw'])
    result = module().seal_compact_condition(**request(sample))
    assert result['condition'] == 'own'
    assert tree(sample['raw']) == raw
    marker = artifacts._json((sample['path'] / 'commit.json').read_bytes())
    assert marker['cell_replay']['rows_checked'] > 0
    assert marker['claims'] == compact.PROTOCOL['claims']
    assert not list(sample['path'].rglob('*.snp'))
    assert not list(sample['path'].rglob('replay.json'))
    assert len(tree(sample['path'])) <= 41
    before = tree(sample['root'])
    sealed = module().read_sealed_condition(**request(sample))
    assert sealed['marker'] == marker
    assert tree(sample['root']) == before
    assert calls.count('production-replay') == 2
    with pytest.raises((ValueError, FileExistsError)):
        module().seal_compact_condition(**request(sample))


def rebind(sample):
    sample['registration'] = write(sample['root'], 'condition-terminal-export.json', sample['contract'])


def test_default_missing_qualification_refuses_before_source_raw_or_output(tmp_path, monkeypatch):
    sample = fixture(tmp_path / 'case')
    m = module()
    def forbidden(*args, **kwargs):
        pytest.fail('Unqualified public entry reached source or raw consumption')
    monkeypatch.setattr(m, '_load_source', forbidden)
    monkeypatch.setattr(m, '_raw', forbidden)
    before = tree(sample['root'])
    with pytest.raises(PermissionError, match='qualification'):
        m.seal_compact_condition(**request(sample))
    assert tree(sample['root']) == before


@pytest.mark.parametrize('defect', ['case', 'condition', 'run', 'source-run', 'source-snapshot',
                                  'source-commit', 'owner', 'prior-own', 'claims'])
def test_rejects_cross_bound_registration_and_retains_raw(tmp_path, monkeypatch, defect):
    sample = fixture(tmp_path / 'case')
    authored_replay(monkeypatch, sample)
    c = sample['contract']
    if defect == 'case': c['case']['case_id'] = 'another-case'
    elif defect == 'condition': c['condition'] = 'swapped'
    elif defect == 'run': c['run_id'] = 'f' * 32
    elif defect == 'source-run': c['source_run_id'] = 'f' * 32
    elif defect == 'source-snapshot': c['source']['snapshot']['sha256'] = 'f' * 64
    elif defect == 'source-commit': c['source']['commit']['sha256'] = 'f' * 64
    elif defect == 'owner': c['owner_record']['sha256'] = 'f' * 64
    elif defect == 'prior-own': c['prior_own_receipt'] = c['raw_audit']
    else: c['claims']['cell_replay_verified'] = True
    rebind(sample)
    raw = tree(sample['raw'])
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module().seal_compact_condition(**request(sample))
    assert tree(sample['raw']) == raw
    assert not (sample['path'] / 'commit.json').exists()


@pytest.mark.parametrize('defect', ['raises', 'wrong-run', 'wrong-count', 'numeric-count', 'wrong-trace'])
def test_replay_failure_or_wrong_identity_quarantines(tmp_path, monkeypatch, defect):
    sample = fixture(tmp_path / 'case')
    authored_replay(monkeypatch, sample)
    m = module()
    replay = m._production_replay
    def broken(**values):
        if defect == 'raises': raise ValueError('authored cell mismatch')
        result = replay(**values)
        field = {'wrong-run': 'run_id', 'wrong-count': 'rows_checked',
                 'numeric-count': 'rows_checked', 'wrong-trace': 'trace_digest'}[defect]
        result[field] = (float(result[field]) if defect == 'numeric-count'
                         else result[field] + 1 if defect == 'wrong-count' else 'f' * len(result[field]))
        return result
    monkeypatch.setattr(m, '_production_replay', broken)
    raw = tree(sample['raw'])
    with pytest.raises(ValueError): m.seal_compact_condition(**request(sample))
    assert tree(sample['raw']) == raw
    assert not (sample['path'] / 'commit.json').exists()
    assert (sample['path'].parents[1] / 'quarantine.json').exists()


def test_replay_primary_survives_composite_held_output_teardown_failure(tmp_path, monkeypatch):
    sample = fixture(tmp_path / 'case')
    authored_replay(monkeypatch, sample)
    m = module()
    def broken(**values):
        path = sample['path'] / 'recording/legacy-events.jsonl'
        path.write_bytes(path.read_bytes() + b' ')
        raise LookupError('authored primary replay failure')
    monkeypatch.setattr(m, '_production_replay', broken)
    with pytest.raises(LookupError, match='authored primary replay failure') as result:
        m.seal_compact_condition(**request(sample))
    assert any('teardown' in note.lower() for note in getattr(result.value, '__notes__', ()))
    quarantine = artifacts._json((sample['path'].parents[1] / 'quarantine.json').read_bytes())
    assert quarantine['error_type'] == 'LookupError'
    assert not (sample['path'] / 'commit.json').exists()


def test_caller_descriptor_mutation_cannot_rebind_validated_registration(tmp_path, monkeypatch):
    sample = fixture(tmp_path / 'case')
    authored_replay(monkeypatch, sample)
    m = module()
    original = copy.deepcopy(sample['registration'])
    def mutate_caller(value):
        sample['registration']['sha256'] = 'f' * 64
    monkeypatch.setattr(m, '_require_qualification_pin', mutate_caller)
    result = m.seal_compact_condition(**request(sample))
    assert result['conversion']['registration'] == original
    assert sample['registration']['sha256'] == 'f' * 64


@pytest.mark.parametrize('target', ['raw', 'source-marker', 'source-snapshot', 'history', 'candidate'])
def test_mutation_during_internal_replay_cannot_publish(tmp_path, monkeypatch, target):
    sample = fixture(tmp_path / 'case')
    authored_replay(monkeypatch, sample)
    m = module()
    replay = m._production_replay
    paths = {'raw': sample['raw'] / 'recording/events.jsonl',
        'source-marker': sample['source']['source'] / 'commit.json',
        'source-snapshot': sample['source']['snapshot'],
        'history': sample['root'] / sample['contract']['history_bundles']['own']['path'],
        'candidate': sample['path'] / 'recording/legacy-events.jsonl'}
    def mutate(**values):
        result = replay(**values)
        path = paths[target]
        path.write_bytes(path.read_bytes() + b' ')
        return result
    monkeypatch.setattr(m, '_production_replay', mutate)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        m.seal_compact_condition(**request(sample))
    assert not (sample['path'] / 'commit.json').exists()
    assert (sample['path'].parents[1] / 'quarantine.json').exists()


@pytest.mark.parametrize('target', ['recording', 'chunks'])
def test_named_output_directory_replacement_is_quarantined(tmp_path, monkeypatch, target):
    sample = fixture(tmp_path / 'case')
    scratch = sample['root'] / 'precreated-scratch'
    scratch.mkdir()
    authored_replay(monkeypatch, sample)
    m = module()
    replay = m._production_replay
    original = sample['path'] / 'recording'
    if target == 'chunks':
        original /= 'chunks'
    def replace(**values):
        result = replay(**values)
        detached = scratch / 'detached'
        original.rename(detached)
        shutil.copytree(detached, original)
        return result
    monkeypatch.setattr(m, '_production_replay', replace)
    raw = tree(sample['raw'])
    with pytest.raises((ValueError, RuntimeError, OSError)):
        m.seal_compact_condition(**request(sample))
    assert (sample['path'].parents[1] / 'quarantine.json').exists()
    assert tree(sample['raw']) == raw


def test_postcommit_context_validation_retains_marker_and_quarantines(tmp_path, monkeypatch):
    sample = fixture(tmp_path / 'case')
    authored_replay(monkeypatch, sample)
    m = module()
    original = m._qualified_replay
    @contextmanager
    def failing(*args, **kwargs):
        with original(*args, **kwargs) as session:
            yield session
            raise RuntimeError('authored late custody failure')
    monkeypatch.setattr(m, '_qualified_replay', failing)
    raw = tree(sample['raw'])
    with pytest.raises(m.SealIndeterminate):
        m.seal_compact_condition(**request(sample))
    assert (sample['path'] / 'commit.json').exists()
    assert (sample['path'].parents[1] / 'quarantine.json').exists()
    assert tree(sample['raw']) == raw
    with pytest.raises((ValueError, RuntimeError)):
        m.read_sealed_condition(**request(sample))


def test_postcommit_anchor_close_failure_is_quarantined(tmp_path, monkeypatch):
    sample = fixture(tmp_path / 'case')
    authored_replay(monkeypatch, sample)
    m = module()
    original_close = m.os.close
    original_finish = m._Anchor.close
    armed = [False]
    fired = [False]
    def finish(anchor):
        armed[0] = (sample['path'] / 'commit.json').exists()
        return original_finish(anchor)
    def fail_once(fd):
        if armed[0] and not fired[0]:
            fired[0] = True
            original_close(fd)
            raise OSError('authored close failure after actual close')
        return original_close(fd)
    monkeypatch.setattr(m._Anchor, 'close', finish)
    monkeypatch.setattr(m.os, 'close', fail_once)
    with pytest.raises(m.SealIndeterminate):
        m.seal_compact_condition(**request(sample))
    assert fired[0]
    assert (sample['path'] / 'commit.json').exists()
    assert (sample['path'].parents[1] / 'quarantine.json').exists()


@pytest.mark.parametrize('point', ['conversion', 'pair', 'temporary', 'rename', 'quarantine'])
def test_publication_faults_never_admit_or_delete_raw(tmp_path, monkeypatch, point):
    sample = fixture(tmp_path / 'case')
    authored_replay(monkeypatch, sample)
    m = module()
    original = producer._write_file
    def write_fault(directory, name, payload):
        target = {'conversion': 'conversion.json', 'pair': 'pair-admission.json',
                  'temporary': '.commit.tmp', 'quarantine': 'quarantine.json'}.get(point)
        if name == target:
            raise OSError('authored publication failure')
        return original(directory, name, payload)
    monkeypatch.setattr(producer, '_write_file', write_fault)
    if point == 'rename':
        monkeypatch.setattr(producer, '_rename_noreplace', lambda fd: (_ for _ in ()).throw(FileExistsError()))
    if point == 'quarantine':
        monkeypatch.setattr(m, '_production_replay', lambda **values: (_ for _ in ()).throw(ValueError('cell')))
    raw = tree(sample['raw'])
    with pytest.raises((ValueError, RuntimeError, OSError)):
        m.seal_compact_condition(**request(sample))
    assert tree(sample['raw']) == raw
    assert not (sample['path'] / 'commit.json').exists()
    with pytest.raises((ValueError, RuntimeError, OSError)):
        m.read_sealed_condition(**request(sample))
