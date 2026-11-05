"""Authored qualification fixtures only; never real model/retained inputs."""
import copy
import hashlib
import importlib
import os
import json
import subprocess
import sys
from pathlib import Path
import time

import pytest
from palimpsest import memory
from test_memory_family_source_runtime_v2 import job, AuthoredEngine, runtime

ROOT = Path(__file__).resolve().parents[1]


def parent():
    return importlib.import_module('scripts.qualify_memory_family_source_v2')


def write_freeze(tmp_path, monkeypatch, *, complete=False):
    p = parent()
    value = job(tmp_path)
    value['parent_admission'] = None
    value['immutable']['python_alias'] = sys.executable
    # Tests run only software authored data and own a temporary HOME/lease.
    monkeypatch.setenv('HOME', str(tmp_path))
    allocation = copy.deepcopy(p.ALLOCATION)
    descriptor = {'path': str(tmp_path / 'not-opened'), 'size_bytes': 1, 'sha256': 'a'*64}
    freeze = {'schema': 'memory-family-source-freeze-v2', 'state': 'prepared',
        'job': value, 'allocation': allocation, 'environment': p._environment(value),
        'runtime_roots': [str(tmp_path / 'authored-install')],
        'namespace_projections': {name: copy.deepcopy(descriptor) if complete else None for name in p.LOGICAL_SOURCES},
        'runtime_cgroup': '/sys/fs/cgroup/authored' if complete else None,
        'lifetime_contract': copy.deepcopy(descriptor) if complete else None,
        'prior_cpu': {'project_seconds': 0, 'memory_seconds': 0},
        'peak_bytes': {'raw': 512*p.MiB, 'snapshot': 16*p.MiB, 'candidate': 32*p.MiB,
            'controls': 8*p.MiB, 'atomic': 8*p.MiB, 'headroom': 64*p.MiB}}
    path = tmp_path / 'freeze.json'
    path.write_bytes(memory.canonical_bytes(freeze))
    return freeze, path, hashlib.sha256(path.read_bytes()).hexdigest()


def _accounting():
    return {'status': 'completed', 'returncode': 0, 'errors': [],
        'accounting_complete': True, 'tree_drained': True,
        'subtree_cpu_seconds': .01, 'parent_cpu_seconds': .001}


def harness(tmp_path, monkeypatch, *, corrupt=None, owner_failure=False,
            accounting_defect=None, final_check=False):
    p = parent()
    freeze, path, digest = write_freeze(tmp_path, monkeypatch, complete=True)
    calls = []
    def budget(output):
        from palimpsest.storage import StorageBudget, StorageLimits
        return StorageBudget([output], StorageLimits(max_bytes=p.ALLOCATION['max_bytes'], min_free_bytes=0),
            headroom_bytes=p.ALLOCATION['headroom_bytes'])
    def runner(command, **kwargs):
        role = 'owner' if '-c' in command else 'audit'
        calls.append(role)
        if role == 'audit':
            # A separate real process executes the unchanged public raw auditor.
            # Native array fixtures can leave library threads in pytest. The
            # accountant itself must start in a fresh single-threaded process.
            serial = {k: str(v) if isinstance(v, Path) else v for k, v in kwargs.items() if k != 'monitor'}
            helper = 'import json,sys; from paper.studies.change_audit_v1.process import run_accounted; print(json.dumps(run_accounted(json.loads(sys.argv[1]), **json.loads(sys.argv[2]))))'
            child = subprocess.run([sys.executable, '-B', '-c', helper, json.dumps(command), json.dumps(serial)],
                cwd=ROOT, env=kwargs['env'], capture_output=True, text=True, timeout=30)
            assert child.returncode == 0, child.stderr
            return json.loads(child.stdout)
        value = p._read(Path(command[-3]), command[-2])
        storage = budget(Path(value['paths']['evidence_root']))
        monkeypatch.setattr(runtime(), '_capture', lambda engine: {'application': engine.application_state()})
        outcome = runtime()._run_admitted(value, storage,
            lambda *a, **kw: AuthoredEngine(value), lambda: None)
        if owner_failure:
            outcome['status'], outcome['report'] = 'failed', None
        p._write(Path(command[-1]), outcome, storage)
        Path(kwargs['stdout_path']).write_bytes(b'authored owner, no native runtime\n')
        Path(kwargs['stderr_path']).write_bytes(b'')
        if corrupt:
            corrupt(value)
        result = _accounting()
        if accounting_defect:
            result.update(accounting_defect)
        return result
    check_calls = []
    def admit(value, sha, lifetime):
        def recheck():
            check_calls.append(True)
            if final_check and len(check_calls) >= 4:
                raise ValueError('authored final closure recheck failure')
        return [recheck]
    result = p._execute(freeze, path, digest, _runner=runner, _admit=admit, _budget_factory=budget)
    return freeze, result, calls


def _inventory(path):
    return {str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*') if p.is_file()}


def test_verify_mode_cannot_launch(tmp_path, monkeypatch):
    p = parent()
    freeze, path, digest = write_freeze(tmp_path, monkeypatch)
    # Metadata test uses a temporary ROOT/runs output with no filesystem creation.
    fake_root = tmp_path / 'metadata-root'
    evidence = fake_root / 'runs/memory-family-source-v2-authored'
    old = freeze['job']['paths']['evidence_root']
    for key, value in freeze['job']['paths'].items():
        if value.startswith(old):
            freeze['job']['paths'][key] = value.replace(old, str(evidence), 1)
    monkeypatch.setattr(p, 'ROOT', fake_root)
    freeze['environment'] = p._environment(freeze['job'])
    path.write_bytes(memory.canonical_bytes(freeze))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(p, 'run_accounted', lambda *a, **k: pytest.fail('verify launched worker'))
    monkeypatch.setattr(runtime(), '_check_identity', lambda *a: pytest.fail('verify opened payload'))
    original_open = os.open
    def safe_open(name, *args, **kwargs):
        public_source = Path(name).suffix == '.py' and any(Path(name).is_relative_to(ROOT / folder) for folder in ('scripts', 'src', 'paper'))
        public_protocol = Path(name) == ROOT / 'docs/plans/memory-family-allocation-admission-v3-protocol.json'
        assert Path(name) == path or public_source or public_protocol, 'verification opened a runtime/catalog/GO payload'
        return original_open(name, *args, **kwargs)
    monkeypatch.setattr(os, 'open', safe_open)
    result = p.verify_freeze(path, digest)
    assert result['worker_invocations'] == 0 and result['payloads_opened'] is False
    assert result['execution_authorized'] is False and len(result['blockers']) == 5
    assert not evidence.exists()


def test_closed_or_changed_freeze_refuses_before_owner(tmp_path, monkeypatch):
    p = parent()
    freeze, path, digest = write_freeze(tmp_path, monkeypatch)
    monkeypatch.setattr(p, '_execute', lambda *a: pytest.fail('owner reached'))
    freeze['state'] = 'closed'
    path.write_bytes(memory.canonical_bytes(freeze))
    with pytest.raises(ValueError, match='Pinned'):
        p.execute_freeze(path, digest)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match='Closed'):
        p.execute_freeze(path, digest)
    assert not Path(freeze['job']['paths']['evidence_root']).exists()


@pytest.mark.parametrize('defect', [{'accounting_complete': False}, {'tree_drained': False},
    {'subtree_cpu_seconds': None}, {'parent_cpu_seconds': float('nan')},
    {'returncode': True}, {'returncode': 1}])
def test_unknown_cpu_or_non_drained_owner_prevents_raw_audit(tmp_path, monkeypatch, defect):
    freeze, result, calls = harness(tmp_path, monkeypatch, accounting_defect=defect)
    assert calls == ['owner'] and result['status'] == 'stopped'
    assert not (Path(freeze['job']['paths']['control_root']) / 'terminal-export.json').exists()
    assert not (Path(freeze['job']['paths']['owner']).parent / 'commit.json').exists()


def test_failed_owner_outcome_blocks_audit_even_with_raw_report(tmp_path, monkeypatch):
    freeze, result, calls = harness(tmp_path, monkeypatch, owner_failure=True)
    assert Path(freeze['job']['paths']['raw'], 'worker-report.json').exists()
    assert calls == ['owner'] and result['status'] == 'stopped'
    assert not (Path(freeze['job']['paths']['control_root']) / 'terminal-export.json').exists()


def test_duplicate_output_is_not_a_new_attempt(tmp_path, monkeypatch):
    freeze, result, calls = harness(tmp_path, monkeypatch)
    before = _inventory(Path(freeze['job']['paths']['evidence_root']))
    with pytest.raises(FileExistsError):
        parent()._execute(freeze, tmp_path / 'freeze.json', 'a'*64)
    assert _inventory(Path(freeze['job']['paths']['evidence_root'])) == before
    assert calls == ['owner', 'audit']


def test_deadline_covers_cleanup_and_final_receipt(tmp_path, monkeypatch):
    p = parent()
    with pytest.raises(TimeoutError):
        p._deadline(0)
    original_write = p._write
    def write(path, value, budget):
        original_write(path, value, budget)
        if path.name == 'parent-terminal.json':
            clock[0] = 901
    clock = [0]
    freeze, path, digest = write_freeze(tmp_path, monkeypatch, complete=True)
    monkeypatch.setattr(p, '_write', write)
    with pytest.raises(TimeoutError, match='deadline'):
        p._execute(freeze, path, digest, _clock=lambda: clock[0],
            _admit=lambda *a: (_ for _ in ()).throw(ValueError('authored admission failure')),
            _budget_factory=lambda out: __import__('palimpsest.storage', fromlist=['StorageBudget']).StorageBudget(
                [out], __import__('palimpsest.storage', fromlist=['StorageLimits']).StorageLimits(min_free_bytes=0)))
    terminal = p._read(Path(freeze['job']['paths']['control_root']) / 'parent-terminal.json')
    assert terminal['status'] == 'stopped' and terminal['parent_lifetime_reconciled'] is False


@pytest.mark.parametrize('failed', [False, True])
def test_raw_and_snapshot_remain_after_pass_or_failure(tmp_path, monkeypatch, failed):
    freeze, result, calls = harness(tmp_path, monkeypatch, owner_failure=failed)
    assert Path(freeze['job']['paths']['snapshot']).is_file()
    assert Path(freeze['job']['paths']['raw'], 'recording/events.jsonl').stat().st_size > 0
    if failed:
        assert result['status'] == 'stopped'
    else:
        assert result['status'] == 'preserved-awaiting-lifetime-reconciliation', (result, (Path(freeze['job']['paths']['control_root']) / 'audit.stderr').read_text())
        assert result['preservation']['original_row_commitments_equal'] is True
        assert result['preservation']['raw_inventory_unchanged'] is True
        assert result['actual_source_qualified'] is False
        assert result['parent_lifetime_reconciled'] is False
        assert Path(freeze['job']['paths']['owner']).parent.joinpath('commit.json').exists()
    assert result['qualification_claims'] is False and result['pruning_authorized'] is False


@pytest.mark.parametrize('defect', ['raw-hash', 'report', 'event-mapping', 'snapshot-prefix'])
def test_independent_auditor_rejects_corrupt_authored_source(tmp_path, monkeypatch, defect):
    def corrupt(value):
        raw = Path(value['paths']['raw'])
        if defect == 'raw-hash':
            path = next((raw / 'recording/chunks').glob('*.npz'))
            path.write_bytes(path.read_bytes() + b'corrupt')
        elif defect == 'report':
            path = raw / 'worker-report.json'
            report = parent()._read(path)
            report['total_ticks'] += 1
            path.write_bytes(memory.canonical_bytes(report))
        elif defect == 'event-mapping':
            path = raw / 'recording/events.jsonl'
            assert b'neural_policy_call' in path.read_bytes()
            path.write_bytes(path.read_bytes().replace(b'neural_policy_call', b'neural_policy_bad'))
        else:
            from palimpsest import snapshots
            path = Path(value['paths']['snapshot'])
            snapshot = snapshots.read_snapshot(path)
            snapshot['application']['event_prefix']['sha256'] = '0'*64
            # Re-serialize an authored test SNP; never any actual snapshot.
            # save_snapshot refuses replacement: build a separate authored temp
            # container, then overwrite the original solely to test corruption.
            altered = path.parent / 'authored-corrupt.snp'
            snapshots.save_snapshot(snapshot, altered)
            path.write_bytes(altered.read_bytes())
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            report_path = raw / 'worker-report.json'
            report = parent()._read(report_path)
            old_digest = report['snapshot_sha256']
            report['snapshot_sha256'] = digest
            report_path.write_bytes(memory.canonical_bytes(report))
            outcome_path = Path(value['paths']['control_root']) / 'owner-outcome.json'
            outcome = parent()._read(outcome_path)
            outcome['report'] = report
            outcome_path.write_bytes(memory.canonical_bytes(outcome))
            events = raw / 'recording/events.jsonl'
            events.write_bytes(events.read_bytes().replace(old_digest.encode(), digest.encode()))
    freeze, result, calls = harness(tmp_path, monkeypatch, corrupt=corrupt)
    assert result['status'] == 'stopped', result
    assert not (Path(freeze['job']['paths']['control_root']) / 'terminal-export.json').exists()
    assert not Path(freeze['job']['paths']['owner']).parent.joinpath('commit.json').exists()
    assert Path(freeze['job']['paths']['raw']).exists()
    assert Path(freeze['job']['paths']['snapshot']).exists()


def test_closure_final_recheck_prevents_export(tmp_path, monkeypatch):
    freeze, result, calls = harness(tmp_path, monkeypatch, final_check=True)
    assert result['status'] == 'stopped'
    assert not (Path(freeze['job']['paths']['control_root']) / 'terminal-export.json').exists()


def test_terminal_export_control_identity_corruption_prevents_seal(tmp_path, monkeypatch):
    p = parent()
    write = p._write
    def corrupt(path, value, budget):
        if path.name == 'terminal-export.json':
            value = copy.deepcopy(value)
            value['controls']['supervisor']['sha256'] = '0'*64
        return write(path, value, budget)
    monkeypatch.setattr(p, '_write', corrupt)
    freeze, result, calls = harness(tmp_path, monkeypatch)
    assert result['status'] == 'stopped', result
    assert not Path(freeze['job']['paths']['owner']).parent.joinpath('commit.json').exists()
    assert Path(freeze['job']['paths']['snapshot']).exists()


def test_parent_keeps_venv_alias_and_independent_audit_command(tmp_path, monkeypatch):
    freeze, result, calls = harness(tmp_path, monkeypatch)
    for item in result['jobs']:
        assert item['command'][0] == freeze['job']['immutable']['python_alias']
        assert item['command'][1] == '-B'
        assert item['environment']['PYTHONPYCACHEPREFIX'].endswith('/controls/unused-pycache')
    assert calls == ['owner', 'audit']


def test_postseal_final_read_failure_quarantines_without_deletion(tmp_path, monkeypatch):
    from scripts import memory_family_producer_v4 as producer
    read = producer.read_sealed_source
    monkeypatch.setattr(producer, 'read_sealed_source', lambda **kw: (_ for _ in ()).throw(ValueError('authored final read failure')))
    freeze, result, calls = harness(tmp_path, monkeypatch)
    assert result['status'] == 'stopped'
    source = Path(freeze['job']['paths']['owner']).parent
    assert (source / 'commit.json').is_file()  # Failed publication bytes remain.
    assert (source.parent / 'quarantine.json').is_file()
    descriptor = parent()._descriptor(Path(freeze['job']['paths']['control_root']) / 'terminal-export.json',
        Path(freeze['job']['paths']['evidence_root']))
    with pytest.raises(ValueError):
        read(evidence_root=freeze['job']['paths']['evidence_root'], registration=descriptor,
            case_id=freeze['job']['case']['case_id'], deadline=time.monotonic()+20)
    assert Path(freeze['job']['paths']['snapshot']).is_file()
    assert Path(freeze['job']['paths']['raw'], 'worker-report.json').is_file()


def test_inherited_memory_bound_is_required_not_sampled_rss(tmp_path, monkeypatch):
    p = parent()
    group = Path('/sys/fs/cgroup/authored-test-only')
    values = {'/proc/self/cgroup': '0::/authored-test-only\n',
        str(group / 'memory.max'): str(8*1024**3), str(group / 'memory.swap.max'): '0',
        str(group / 'cgroup.procs'): str(os.getpid())}
    original = Path.read_text
    monkeypatch.setattr(Path, 'read_text', lambda path, *a, **kw: values[str(path)] if str(path) in values else original(path,*a,**kw))
    p._enforcement({'runtime_cgroup': str(group)})
    values[str(group / 'memory.max')] = 'max'
    with pytest.raises((ValueError, PermissionError)):
        p._enforcement({'runtime_cgroup': str(group)})
    values[str(group / 'memory.max')] = str(8*1024**3)
    values[str(group / 'cgroup.procs')] += '\n999999'
    with pytest.raises(PermissionError):
        p._enforcement({'runtime_cgroup': str(group)})


def test_import_and_real_verify_cli_do_not_import_native_or_create_output(tmp_path, monkeypatch):
    p = parent()
    freeze, path, digest = write_freeze(tmp_path, monkeypatch)
    evidence = ROOT / 'runs' / ('memory-family-source-v2-authored-never-created-' + freeze['job']['run_id'])
    old = freeze['job']['paths']['evidence_root']
    for key, value in freeze['job']['paths'].items():
        if value.startswith(old):
            freeze['job']['paths'][key] = value.replace(old, str(evidence), 1)
    freeze['environment'] = p._environment(freeze['job'])
    path.write_bytes(memory.canonical_bytes(freeze))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    code = 'import scripts.qualify_memory_family_source_v2 as p,sys; assert not set(sys.modules)&{"torch","mujoco","palimpsest.engine"}; raise SystemExit(p.main(sys.argv[1:]))'
    process = subprocess.run([sys.executable, '-B', '-c', code, '--mode', 'verify',
        '--freeze', str(path), '--expected-freeze-sha256', digest], cwd=ROOT,
        env={**os.environ, 'PYTHONPATH': str(ROOT / 'src') + ':' + str(ROOT)}, text=True, capture_output=True)
    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)['execution_authorized'] is False
    assert not evidence.exists()
    rejected = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/qualify_memory_family_source_v2.py'),
        '--freeze', str(path), '--expected-freeze-sha256', digest, '--command', 'untrusted'],
        cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src') + ':' + str(ROOT)}, text=True, capture_output=True)
    assert rejected.returncode == 2 and 'unrecognized arguments' in rejected.stderr


def test_unresolved_canonical_namespace_refuses_before_runtime_or_export_reads(tmp_path, monkeypatch):
    from contextlib import ExitStack
    from scripts import memory_family_allocation_v3 as allocation
    freeze, path, digest = write_freeze(tmp_path, monkeypatch, complete=True)
    monkeypatch.setattr(os, 'open', lambda *a, **kw: pytest.fail('unresolved gate opened external input'))
    monkeypatch.setattr(runtime(), '_check_identity', lambda *a: pytest.fail('unresolved gate opened runtime payload'))
    with ExitStack() as lifetime, pytest.raises(allocation.AdmissionRefused, match='unresolved'):
        parent()._execute_admission(freeze, digest, lifetime)
    assert parent().LOGICAL_SOURCES == ('pre-heldout-development-history', 'training-namespace')
    assert not Path(freeze['job']['paths']['evidence_root']).exists()


def test_go_is_external_and_binds_exact_freeze_job_scope_no_retry(tmp_path, monkeypatch):
    p = parent()
    freeze, path, digest = write_freeze(tmp_path, monkeypatch)
    assert 'execution_authority' not in freeze  # No circular GO hash in freeze.
    go = {'schema': 'memory-family-source-exact-stage-go-v2',
        'stage': 'single-development-source-qualification', 'freeze_sha256': digest,
        'job_sha256': runtime().job_sha256(freeze['job']), 'decision': 'GO',
        'retry': False, 'approval_reference': 'AUTHORED FIXTURE ONLY; NO OPERATOR AUTHORITY'}
    go_path = tmp_path / 'authored-go.json'
    go_path.write_bytes(memory.canonical_bytes(go))
    go_sha = hashlib.sha256(go_path.read_bytes()).hexdigest()
    assert p._validate_go(go_path, go_sha, digest, freeze['job']) == go
    go['retry'] = True
    go_path.write_bytes(memory.canonical_bytes(go))
    with pytest.raises(ValueError, match='Pinned'):
        p._validate_go(go_path, go_sha, digest, freeze['job'])
    go_sha = hashlib.sha256(go_path.read_bytes()).hexdigest()
    with pytest.raises(PermissionError, match='scope'):
        p._validate_go(go_path, go_sha, digest, freeze['job'])
