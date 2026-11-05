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
    freeze = {'schema': 'memory-family-source-freeze-v3', 'state': 'prepared',
        'numeric_profile': p._descriptor(ROOT / 'docs/plans/memory-family-numeric-compact-v2-protocol.json', ROOT),
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
            accounting_defect=None, final_check=False, controlled_home=False):
    p = parent()
    freeze, path, digest = write_freeze(tmp_path, monkeypatch, complete=True)
    if controlled_home:
        monkeypatch.setenv('HOME', freeze['environment']['HOME'])
    import test_memory_family_raw_audit_v4 as authored_raw
    from test_memory_family_numeric_preservation_v2 import numeric_values
    original_policy = authored_raw._policy_row
    def full_numeric(row, run_id, pixel_shift=0):
        event, arrays = original_policy(row, run_id, pixel_shift)
        arrays.update(numeric_values(row['tick']))
        return event, arrays
    monkeypatch.setattr(authored_raw, '_policy_row', full_numeric)
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
            contract = {k: str(v) if isinstance(v, Path) else v for k, v in kwargs['monitor'].keywords.items()
                if k not in ('budget', 'clock')}
            helper = ('import json,sys,os; from functools import partial; '
                'from palimpsest.storage import StorageBudget,StorageLimits; '
                'from scripts import qualify_memory_family_source_v2 as p; '
                'kw=json.loads(sys.argv[2]); m=json.loads(sys.argv[3]); m["parent_pid"]=os.getpid(); '
                'm["budget"]=StorageBudget([m["output"]],StorageLimits(max_bytes=p.ALLOCATION["max_bytes"],min_free_bytes=0),headroom_bytes=p.ALLOCATION["headroom_bytes"]); '
                'kw["monitor"]=partial(p._monitor_stage,**m); '
                'print(json.dumps(p.run_accounted(json.loads(sys.argv[1]), **kw)))')
            child = subprocess.run([sys.executable, '-B', '-c', helper, json.dumps(command), json.dumps(serial), json.dumps(contract)],
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
        public_protocol = Path(name) in {ROOT / 'docs/plans/memory-family-allocation-admission-v3-protocol.json', ROOT / 'docs/plans/memory-family-numeric-compact-v2-protocol.json'}
        assert Path(name) == path or public_source or public_protocol, 'verification opened a runtime/catalog/GO payload'
        return original_open(name, *args, **kwargs)
    monkeypatch.setattr(os, 'open', safe_open)
    result = p.verify_freeze(path, digest)
    assert result['worker_invocations'] == 0 and result['payloads_opened'] is False
    assert result['execution_authorized'] is False and len(result['blockers']) == 7
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
        assert numeric_candidate(freeze).joinpath('commit.json').exists()
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
    assert not numeric_candidate(freeze).joinpath('commit.json').exists()
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
    assert not numeric_candidate(freeze).joinpath('commit.json').exists()
    assert Path(freeze['job']['paths']['snapshot']).exists()


def test_parent_keeps_venv_alias_and_independent_audit_command(tmp_path, monkeypatch):
    freeze, result, calls = harness(tmp_path, monkeypatch)
    for item in result['jobs']:
        assert item['command'][0] == freeze['job']['immutable']['python_alias']
        assert item['command'][1] == '-B'
        assert item['environment']['PYTHONPYCACHEPREFIX'].endswith('/controls/unused-pycache')
    assert calls == ['owner', 'audit']


def test_postseal_final_read_failure_quarantines_without_deletion(tmp_path, monkeypatch):
    from scripts import memory_family_source_seal_v2 as producer
    read = producer.read_numeric_source_v2
    monkeypatch.setattr(producer, 'read_numeric_source_v2', lambda **kw: (_ for _ in ()).throw(ValueError('authored final read failure')))
    freeze, result, calls = harness(tmp_path, monkeypatch)
    assert result['status'] == 'stopped'
    source = numeric_candidate(freeze)
    assert (source / 'commit.json').is_file()  # Failed publication bytes remain.
    assert (source / 'quarantine.json').is_file()
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


def test_real_accountant_monitor_uses_supervisor_domain_after_parent_prior_cpu(tmp_path, monkeypatch):
    freeze, path, digest = write_freeze(tmp_path, monkeypatch, complete=True)
    helper = r'''
import json, os, sys, time
from pathlib import Path
from palimpsest.storage import StorageBudget, StorageLimits
from scripts import qualify_memory_family_source_v2 as p
freeze_path, sha = sys.argv[1:]
value = p._read(freeze_path, sha)
# Positive parent CPU predating the fork must not be subtracted in its child.
burn = time.process_time() + .15
while time.process_time() < burn:
    pass
def budget(output):
    return StorageBudget([output], StorageLimits(max_bytes=p.ALLOCATION['max_bytes'], min_free_bytes=0), headroom_bytes=p.ALLOCATION['headroom_bytes'])
def runner(command, **kwargs):
    monitor = kwargs['monitor']
    sample_path = Path(value['job']['paths']['control_root']) / 'authored-monitor-samples.jsonl'
    def observed(sample):
        result = monitor(sample)
        with sample_path.open('a') as stream:
            stream.write(json.dumps(sample)+'\n')
        return result
    kwargs['monitor'] = observed
    # Fixed authored stdlib worker; no native owner or model is launched.
    return p.run_accounted([sys.executable, '-B', '-c', 'import time; end=time.process_time()+.08\nwhile time.process_time()<end: pass'], **kwargs)
result = p._execute(value, Path(freeze_path), sha, _runner=runner,
    _admit=lambda *a: [], _budget_factory=budget)
print(json.dumps(result))
'''
    child = subprocess.run([sys.executable, '-B', '-c', helper, str(path), digest],
        cwd=ROOT, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')+':'+str(ROOT)},
        capture_output=True, text=True, timeout=30)
    assert child.returncode == 0, child.stderr
    result = json.loads(child.stdout)
    assert result['jobs'][0]['accounting']['status'] == 'completed', result
    assert result['jobs'][0]['accounting']['errors'] == []
    samples = Path(freeze['job']['paths']['control_root']) / 'authored-monitor-samples.jsonl'
    observed = [json.loads(line) for line in samples.read_text().splitlines()]
    assert any(row['sampled_worker_cpu_seconds'] > 0 for row in observed)
    assert result['status'] == 'stopped'  # Authored worker intentionally has no source outcome.


@pytest.mark.parametrize('role', ['owner-supervisor.json', 'job.json', 'cleanup.json'])
def test_rewritten_control_cannot_be_rebound_into_export(tmp_path, monkeypatch, role):
    p = parent()
    original = p._write
    def rewrite(path, value, budget):
        original(path, value, budget)
        if path.name == role or (role == 'job.json' and path.name == 'owner-supervisor.json'):
            target = path.parent / role
            if role == 'job.json' and path.name == 'job.json':
                return  # Corrupt only after the owner consumed its original job.
            control = p._read(target)
            control['schema' if role != 'owner-supervisor.json' else 'accounting'] = 'AUTHORED REWRITTEN CONTROL'
            target.write_bytes(memory.canonical_bytes(control))
    monkeypatch.setattr(p, '_write', rewrite)
    freeze, result, calls = harness(tmp_path, monkeypatch)
    assert result['status'] == 'stopped', result
    assert not numeric_candidate(freeze).joinpath('commit.json').exists()
    assert not (Path(freeze['job']['paths']['control_root']) / 'terminal-export.json').exists()


def test_held_input_exit_failure_is_quarantined_before_terminal(tmp_path, monkeypatch):
    p = parent()
    execute = p._execute
    def intercepted(value, path, sha, **kwargs):
        admit = kwargs['_admit']
        def with_exit_failure(value, sha, lifetime):
            checks = admit(value, sha, lifetime)
            def exit_failure():
                raise ValueError('AUTHORED HELD INPUT TEARDOWN FAILURE')
            lifetime.callback(exit_failure)
            return checks
        kwargs['_admit'] = with_exit_failure
        return execute(value, path, sha, **kwargs)
    monkeypatch.setattr(p, '_execute', intercepted)
    freeze, result, calls = harness(tmp_path, monkeypatch)
    assert result['status'] == 'stopped'
    assert 'TEARDOWN' in result['teardown_error']['message']
    control = Path(freeze['job']['paths']['control_root'])
    assert p._read(control / 'parent-terminal.json')['status'] == 'stopped'
    source = numeric_candidate(freeze)
    assert (source / 'commit.json').exists() and (source / 'quarantine.json').exists()


@pytest.mark.parametrize('defect', ['alias-target', 'alias-replaced', 'added-module', 'added-empty-namespace'])
def test_prepared_runtime_rechecks_alias_and_complete_import_namespace(tmp_path, defect):
    p = parent()
    prefix = tmp_path / 'authored-prefix'
    prefix.mkdir()
    module = prefix / 'authored.py'
    module.write_text('AUTHORED_SOURCE = True\n')
    elf = tmp_path / 'authored-elf'
    elf.write_bytes(b'authored nonexecutable ELF placeholder')
    alias = tmp_path / 'authored-python'
    alias.symlink_to(elf)
    value = {'job': {'immutable': {'python_alias': str(alias), 'python_elf': {'path': str(elf)},
        'owner_source': {'path': str(module)}, 'closure': []}}, 'runtime_roots': [str(prefix)]}
    recheck = p._bind_runtime_namespace(value)
    recheck()
    if defect == 'alias-target':
        other = tmp_path / 'authored-other-elf'
        other.write_bytes(b'authored other executable placeholder')
        alias.unlink()
        alias.symlink_to(other)
    elif defect == 'alias-replaced':
        alias.unlink()
        alias.symlink_to(elf)
    elif defect == 'added-module':
        (prefix / 'new_import.py').write_text('AUTHORED_ADDITION = True\n')
    else:
        (prefix / 'new_namespace').mkdir()
    with pytest.raises(ValueError, match='alias|namespace'):
        recheck()


@pytest.mark.parametrize('role', ['owner-supervisor.json', 'job.json'])
def test_controls_remain_bound_after_creation_until_export(tmp_path, monkeypatch, role):
    p = parent()
    original = p._write
    def rewrite_after_validated_controls(path, value, budget):
        original(path, value, budget)
        if path.name == 'cleanup.json':
            target = path.parent / role
            changed = p._read(target)
            changed['schema' if role == 'job.json' else 'accounting'] = 'AUTHORED LATE REBIND'
            target.write_bytes(memory.canonical_bytes(changed))
            # Rehashing these bytes would produce a valid descriptor for the
            # wrong controls. Creation-time pin must remain authoritative.
            assert p._descriptor(target, target.parent)['sha256'] == hashlib.sha256(target.read_bytes()).hexdigest()
    monkeypatch.setattr(p, '_write', rewrite_after_validated_controls)
    freeze, result, calls = harness(tmp_path, monkeypatch)
    assert result['status'] == 'stopped'
    assert not (Path(freeze['job']['paths']['control_root']) / 'terminal-export.json').exists()
    assert not numeric_candidate(freeze).joinpath('commit.json').exists()


def test_original_freeze_teardown_drift_is_caught_under_lease(tmp_path, monkeypatch):
    p = parent()
    # A custom authored context is sufficient to place the mutation at this exact
    # boundary; the parent must then close/check all remaining held descriptors.
    execute = p._execute
    def intercepted(value, path, sha, **kwargs):
        admit = kwargs['_admit']
        def delayed_mutation(value, sha, lifetime):
            checks = admit(value, sha, lifetime)
            lifetime.callback(lambda: path.write_bytes(path.read_bytes()+b' '))
            return checks
        kwargs['_admit'] = delayed_mutation
        return execute(value, path, sha, **kwargs)
    monkeypatch.setattr(p, '_execute', intercepted)
    freeze, result, calls = harness(tmp_path, monkeypatch)
    assert result['status'] == 'stopped'
    assert result['teardown_error']['type'] == 'ValueError'
    assert p._read(Path(freeze['job']['paths']['control_root'])/'parent-terminal.json')['status'] == 'stopped'
    source = numeric_candidate(freeze)
    assert (source/'quarantine.json').exists()


def numeric_candidate(freeze):
    job = freeze['job']
    return Path(job['paths']['evidence_root']) / 'numeric-v2' / job['case']['case_id'] / job['run_id']

def test_parent_calls_real_public_numeric_writer_and_rereader(tmp_path, monkeypatch):
    from scripts import memory_family_source_seal_v2 as public
    from test_memory_family_numeric_preservation_v2 import numeric_values
    seen = []
    for name in ('seal_numeric_source_v2', 'read_numeric_source_v2'):
        original = getattr(public, name)
        def observe(*args, _name=name, _original=original, **kwargs):
            result = _original(*args, **kwargs)
            seen.append((_name, result, copy.deepcopy(kwargs['additional_controls'])))
            return result
        monkeypatch.setattr(public, name, observe)
    freeze, result, calls = harness(tmp_path, monkeypatch)
    assert result['status'] == 'preserved-awaiting-lifetime-reconciliation', result
    assert [row[0] for row in seen] == ['seal_numeric_source_v2', 'read_numeric_source_v2']
    assert calls == ['owner', 'audit']
    assert seen[0][2] == seen[1][2]
    for row in seen[1][1]['read']['rows']:
        for name, expected in numeric_values(row['tick']).items():
            assert row[name].dtype.str == expected.dtype.str
            assert row[name].shape == expected.shape
            assert row[name].tobytes() == expected.tobytes()
    assert result['schema'] == 'memory-family-source-parent-result-v3'
    assert result['actual_source_qualified'] is False
    assert result['parent_lifetime_reconciled'] is False
    assert result['output_accounting']['scoped_storage_verified'] is True
    assert result['output_accounting']['stage_peak_accounted'] is False
    assert seen[1][1]['byte_ledger']['stage_peak_accounted'] is False
    assert not Path(freeze['job']['paths']['owner']).parent.joinpath('commit.json').exists()
    assert len(list(Path(freeze['job']['paths']['evidence_root']).rglob('*.snp'))) == 1
    paths = [d['path'] for d in seen[0][2]]
    for name in ('freeze.json','owner-launch.json','audit-launch.json','audit-supervisor.json',
                 'owner-outcome.json','audit.stdout','audit.stderr','terminal-export.json'):
        assert str(Path(freeze['job']['paths']['control_root']).relative_to(freeze['job']['paths']['evidence_root']) / name) in paths

@pytest.mark.parametrize('defect', ['missing', 'wrong', 'mutated', 'old-schema'])
def test_numeric_profile_is_mandatory_before_any_output_or_admission(tmp_path, monkeypatch, defect):
    p = parent()
    freeze, path, digest = write_freeze(tmp_path, monkeypatch)
    if defect == 'missing':
        freeze.pop('numeric_profile')
    elif defect == 'wrong':
        freeze['numeric_profile']['path'] = 'docs/plans/memory-family-compact-v4-protocol.json'
    elif defect == 'mutated':
        freeze['numeric_profile']['sha256'] = '0'*64
    else:
        freeze['schema'] = 'memory-family-source-freeze-v2'
    path.write_bytes(memory.canonical_bytes(freeze))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    with pytest.raises((ValueError, KeyError)):
        p._execute(freeze, path, digest, _admit=lambda *a: pytest.fail('profile gate reached owner admission'))
    assert not Path(freeze['job']['paths']['evidence_root']).exists()

def test_parent_terminal_enforces_public_64k_bound_before_write(tmp_path):
    from palimpsest.storage import StorageBudget, StorageLimits
    target = tmp_path / 'parent-terminal.json'
    with pytest.raises(ValueError, match='64|65536|terminal'):
        parent()._write(target, {'authored': 'x'*65536}, StorageBudget([tmp_path], StorageLimits(min_free_bytes=0)))
    assert not target.exists()


def test_parent_censuses_ancillary_control_prefix_and_zero_leases(tmp_path, monkeypatch):
    from scripts import memory_family_source_seal_v2 as public
    observed = []
    original = public.seal_numeric_source_v2
    def seal(**kwargs):
        observed.extend(kwargs['additional_controls'])
        return original(**kwargs)
    monkeypatch.setattr(public, 'seal_numeric_source_v2', seal)
    def ancillary(job):
        prefix = Path(job['paths']['evidence_root']) / 'controls'
        (prefix / 'matplotlib').mkdir(exist_ok=True)
        (prefix / 'matplotlib/fontlist.json').write_bytes(b'{"authored":true}')
        lease = prefix / 'home/.cache/palimpsest/writer.lock'
        lease.parent.mkdir(parents=True)
        lease.write_bytes(b'')
    freeze, result, calls = harness(tmp_path, monkeypatch, corrupt=ancillary)
    assert result['status'] == 'preserved-awaiting-lifetime-reconciliation', result
    assert any(d['path'] == 'controls/matplotlib/fontlist.json' for d in observed)
    assert not any('/.cache/' in d['path'] for d in observed)
    leases = result['output_accounting']['zero_byte_ephemeral_leases']
    assert any(d['path'] == 'controls/home/.cache/palimpsest/writer.lock' for d in leases)
    assert any(d['path'] == '.palimpsest-storage.lock' for d in leases)
    output = Path(freeze['job']['paths']['evidence_root'])
    total = sum(p.stat().st_size for p in output.rglob('*') if p.is_file())
    terminal = Path(freeze['job']['paths']['control_root']) / 'parent-terminal.json'
    assert total == result['output_accounting']['serialized_bytes_before_terminal'] + terminal.stat().st_size

@pytest.mark.parametrize('kind', ['oversize', 'compound-overhead', 'nonzero-lease', 'aliased-lease', 'controlled-nonzero-lease', 'unregistered-output', 'unregistered-empty'])
def test_parent_complete_census_refuses_unaccounted_or_oversize_outputs(tmp_path, monkeypatch, kind):
    def ancillary(job):
        output = Path(job['paths']['evidence_root'])
        target = output / 'controls/auxiliary.json'
        if kind == 'oversize':
            target.write_bytes(b'x' * (1024**2 + 1))
        elif kind == 'compound-overhead':
            target.write_bytes(b'x' * (950*1024))
        elif kind == 'nonzero-lease':
            (output / '.palimpsest-storage.lock').write_bytes(b'not zero')
        elif kind == 'aliased-lease':
            os.link(output / '.palimpsest-storage.lock', output / 'controls/lease-alias')
        elif kind == 'controlled-nonzero-lease':
            (Path(job['paths']['evidence_root']) / 'controls/home/.cache/palimpsest/writer.lock').write_bytes(b'not zero')
        elif kind == 'unregistered-output':
            (output / 'unlisted.json').write_bytes(b'authored')
        else:
            (output / 'unlisted-empty').mkdir()
    freeze, result, calls = harness(tmp_path, monkeypatch, corrupt=ancillary,
        controlled_home=kind == 'controlled-nonzero-lease')
    assert result['status'] == 'stopped', result
    assert not (numeric_candidate(freeze) / 'commit.json').exists()
    assert Path(freeze['job']['paths']['snapshot']).is_file()
    assert Path(freeze['job']['paths']['raw'], 'worker-report.json').is_file()

@pytest.mark.parametrize('kind', ['unlisted', 'change-and-restore', 'raw-change-and-restore'])
def test_control_census_stays_held_across_real_numeric_publication(tmp_path, monkeypatch, kind):
    from scripts import memory_family_source_seal_v2 as public
    original = public.seal_numeric_source_v2
    def seal(**kwargs):
        result = original(**kwargs)
        control = Path(kwargs['evidence_root']) / 'controls'
        if kind == 'unlisted':
            (control / 'unlisted-after-census.json').write_bytes(b'authored late addition')
        else:
            path = (next((Path(kwargs['evidence_root']) / '.pending').rglob('chunks/*.npz'))
                    if kind == 'raw-change-and-restore' else control / 'auxiliary.json')
            payload = path.read_bytes()
            path.write_bytes(payload + b'changed')
            path.write_bytes(payload)
        return result
    monkeypatch.setattr(public, 'seal_numeric_source_v2', seal)
    def ancillary(job):
        (Path(job['paths']['evidence_root']) / 'controls/auxiliary.json').write_bytes(b'authored auxiliary metadata')
    freeze, result, calls = harness(tmp_path, monkeypatch, corrupt=ancillary)
    assert result['status'] == 'stopped', result
    assert (numeric_candidate(freeze) / 'commit.json').is_file()
    assert (numeric_candidate(freeze) / 'quarantine.json').is_file()

@pytest.mark.parametrize('kind', ['oversize-before-write', 'mutated-after-write', 'unlisted-after-write'])
def test_terminal_failure_quarantines_numeric_candidate(tmp_path, monkeypatch, kind):
    p = parent()
    original = p._write
    terminals = []
    def write(path, value, budget):
        if path.name == 'parent-terminal.json':
            terminals.append(path)
            if kind == 'oversize-before-write':
                value = {**value, 'authored_padding': 'x'*65536}
        original(path, value, budget)
        if path.name == 'parent-terminal.json':
            if kind == 'mutated-after-write':
                with path.open('ab') as stream:
                    stream.write(b' '*65536)
            elif kind == 'unlisted-after-write':
                (path.parents[1] / 'late.json').write_bytes(b'authored late metadata')
    monkeypatch.setattr(p, '_write', write)
    with pytest.raises(ValueError, match='65536|census'):
        harness(tmp_path, monkeypatch)
    output = terminals[0].parents[2]
    assert len(list((output / 'numeric-v2').rglob('quarantine.json'))) == 1
    assert len(list(output.rglob('initial.snp'))) == 1
    if kind == 'oversize-before-write':
        assert not terminals[0].exists()


def test_indeterminate_public_writer_is_stopped_and_never_resumed_by_reader(tmp_path, monkeypatch):
    from scripts import memory_family_source_seal_v2 as public
    rename = public._rename_noreplace
    def failed_after_rename(fd):
        rename(fd)
        raise OSError('authored failure after actual numeric marker rename')
    monkeypatch.setattr(public, '_rename_noreplace', failed_after_rename)
    monkeypatch.setattr(public, '_quarantine', lambda *a: (_ for _ in ()).throw(OSError('authored unavailable public quarantine')))
    monkeypatch.setattr(public, 'read_numeric_source_v2', lambda **kw: pytest.fail('failed writer was resumed by reader'))
    freeze, result, calls = harness(tmp_path, monkeypatch)
    assert result['status'] == 'stopped'
    assert result['error']['type'] == 'SealIndeterminate'
    assert result['actual_source_qualified'] is False
    assert (numeric_candidate(freeze) / 'commit.json').exists()
    assert (numeric_candidate(freeze) / 'quarantine.json').exists()


def test_writer_lease_teardown_error_is_not_a_successful_parent(tmp_path, monkeypatch):
    from contextlib import contextmanager
    p = parent()
    execute = p._execute
    paths = []
    def intercepted(value, path, sha, **kwargs):
        factory = kwargs['_budget_factory']
        paths.append(numeric_candidate(value))
        def budget(output):
            result = factory(output)
            lock = result.lock
            @contextmanager
            def failed_exit():
                with lock():
                    yield result
                raise OSError('AUTHORED WRITER LEASE TEARDOWN FAILURE')
            result.lock = failed_exit
            return result
        kwargs['_budget_factory'] = budget
        return execute(value, path, sha, **kwargs)
    monkeypatch.setattr(p, '_execute', intercepted)
    with pytest.raises(OSError, match='WRITER LEASE'):
        harness(tmp_path, monkeypatch)
    assert (paths[0] / 'commit.json').exists()
    assert (paths[0] / 'quarantine.json').exists()


@pytest.mark.parametrize('late', [False, True])
def test_actual_new_profile_file_bytes_are_checked_and_held(tmp_path, monkeypatch, late):
    p = parent()
    public_root = tmp_path / 'authored-public-metadata'
    profile = public_root / p.NUMERIC_PROFILE
    profile.parent.mkdir(parents=True)
    profile.write_bytes((ROOT / p.NUMERIC_PROFILE).read_bytes())
    monkeypatch.setattr(p, 'PUBLIC_ROOT', public_root)
    if not late:
        freeze, path, digest = write_freeze(tmp_path, monkeypatch)
        profile.write_bytes(profile.read_bytes() + b' ')
        with pytest.raises(ValueError, match='Pinned'):
            p._execute(freeze, path, digest, _admit=lambda *a: pytest.fail('profile drift reached owner'))
        assert not Path(freeze['job']['paths']['evidence_root']).exists()
    else:
        from scripts import memory_family_source_seal_v2 as public
        original = public.read_numeric_source_v2
        def read(**kwargs):
            result = original(**kwargs)
            payload = profile.read_bytes()
            profile.write_bytes(payload + b' ')
            profile.write_bytes(payload)
            return result
        monkeypatch.setattr(public, 'read_numeric_source_v2', read)
        freeze, result, calls = harness(tmp_path, monkeypatch)
        assert result['status'] == 'stopped'
        assert result['teardown_error']['type'] == 'ValueError'
        assert (numeric_candidate(freeze) / 'quarantine.json').exists()


def test_fresh_controlled_home_bootstraps_before_parent_lease(tmp_path, monkeypatch):
    freeze, result, calls = harness(tmp_path, monkeypatch, controlled_home=True)
    assert result['status'] == 'preserved-awaiting-lifetime-reconciliation', result
    assert calls == ['owner', 'audit']
    output = Path(freeze['job']['paths']['evidence_root'])
    assert Path(freeze['environment']['HOME']).is_relative_to(output)
    assert Path(freeze['environment']['MPLCONFIGDIR']).is_dir()
    leases = result['output_accounting']['zero_byte_ephemeral_leases']
    assert {d['path'] for d in leases} == {'.palimpsest-storage.lock',
        'controls/home/.cache/palimpsest/writer.lock'}
    assert all(d['size_bytes'] == 0 for d in leases)
    assert result['actual_source_qualified'] is False
    assert result['parent_lifetime_reconciled'] is False
