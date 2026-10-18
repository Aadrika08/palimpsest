"""Completed-owner doubles only; no native owners, physics or retained study decode."""
import copy
import importlib
import json
import os
from pathlib import Path
import time

import numpy as np
import pytest

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from palimpsest.snapshots import save_snapshot
from palimpsest.storage import StorageBudget


def auditor():
    assert importlib.util.find_spec('scripts.memory_restore_v2_audit'), 'Fresh v2 auditor is not implemented'
    return importlib.import_module('scripts.memory_restore_v2_audit')


def completed_pair(tmp_path, monkeypatch):
    a = auditor(); repo = tmp_path/'repo'; (repo/'scripts').mkdir(parents=True)
    audit_source = repo/'scripts/memory_restore_v2_audit.py'; audit_source.write_text('frozen fixture auditor\n')
    monkeypatch.setattr(a, '__file__', str(audit_source))
    monkeypatch.setattr(p, '__file__', str(repo/'scripts/memory_decision_pilot.py'))
    driver = repo/'scripts/memory_restore_diagnostic.py'; driver.write_text('frozen fixture driver\n')
    monkeypatch.setattr(d, '__file__', str(driver))
    comparator = repo/'scripts/memory_restore_offline_readout.py'; comparator.write_text('frozen fixture comparator\n')
    publication = repo/'docs/reports/restore-qualification-v2-evidence'; publication.mkdir(parents=True)
    launcher = publication/'execute-restore-v2.py'; launcher.write_text('frozen fixture launcher\n')
    contract = repo/'docs/plans/restore-qualification-v2.md'; contract.parent.mkdir(parents=True)
    contract.write_text('frozen fixture scope\n')
    monkeypatch.setattr(p, 'source_identity', lambda *args: {})
    root = repo/'runs/restore-v2-pair-fixture'; stage = root/'stage'; (stage/'jobs').mkdir(parents=True)
    initial = {'integration': np.array([1., 2.]), 'native_data': b'software fixture',
        'application': {'source_run_id': 'source', 'event_prefix': {},
            'memory': {'u': {}, 'selector': {}, 'm': {'facts': []}},
            'receipts': {'old': {'received_run_id': 'source', 'applied_tick': 1}}}}
    original = repo/'old/source.snp'; original.parent.mkdir(); save_snapshot(initial, original)
    source = stage/'source/snapshots/initial.snp'; source.parent.mkdir(parents=True)
    source.write_bytes(original.read_bytes())
    reference = {'path': str(original), 'bytes': original.stat().st_size,
        'sha256': p.file_hash(original), 'invariant': p.condition_digest(initial)}
    copied = {'snapshot_path': str(source), 'snapshot_sha256': reference['sha256'],
        'invariant': reference['invariant'], 'original_source': reference}
    plan = {'repo': str(repo), 'assets': str(repo/'assets'), 'history_root': str(repo/'histories'),
        'output': str(stage), 'phase_root': str(root), 'source_identity': {},
        'protocol_sha256': p.TRAVEL_PROTOCOL_SHA256}
    attempts, cleanup, posts = [], [], []
    for index, spec in enumerate(p.travel_specs('travel-feasibility', d.PROFILE)[-2:]):
        job = p.make_job('travel-feasibility', spec, plan, 'repeat', source=copied)
        run = Path(job['output']); (run/'snapshots').mkdir(parents=True)
        save_snapshot(initial, run/'snapshots/initial.snp')
        final = copy.deepcopy(initial); final['native_data'] += bytes([index]); posts.append(final)
        owner = {'run_id': job['run_id'], 'pid': 9000+index, 'pgid': 9000+index, 'starttime': 1}
        (run/'owner.json').write_text(json.dumps(owner))
        (stage/'jobs'/(job['run_id']+'.json')).write_text(json.dumps(job))
        supervision_root = stage/'supervision'/job['run_id']; supervision_root.mkdir(parents=True)
        supervised = {'status': 'completed', 'returncode': 0, 'timeout_seconds': 160,
            'output': str(supervision_root), 'elapsed_seconds': 1.}
        (supervision_root/'supervisor.json').write_text(json.dumps(supervised))
        report = {'job_id': spec['id'], 'run_id': job['run_id'], 'run': str(run), 'status': 'recorded',
            'raw_audit_pass': True, 'invariants_preserved': True, 'continuation_ticks': 5,
            'trace_digest': p.trace_digest([{'tick': n} for n in range(5)]), 'wall_seconds': 1.,
            'snapshot_path': str(run/'snapshots/initial.snp'), 'snapshot_sha256': p.file_hash(run/'snapshots/initial.snp'),
            'invariant': reference['invariant'],
            **p.publish_repeat_state(final, {'old'}, run, p.phase_budget(root)), 'supervision': supervised}
        (run/'worker-report.json').write_text(json.dumps(report)); attempts.append(report)
        cleanup.append({'owner': owner, 'path': str(run/'owner.json'), 'status': 'already-exited'})
    registration = {'schema': 'memory-restore-registration-v2', 'mode': 'restore-v2',
        **{key: plan[key] for key in ('repo', 'assets', 'history_root', 'source_identity')},
        'output': str(root), 'seconds_caps': [600, 300], 'state_contract': 'restore-reproducibility-v2-candidate',
        'expected_specs': p.travel_specs('travel-feasibility', d.PROFILE)[-2:], 'source_snapshot': reference,
        'auditor_path': str(audit_source), 'auditor_sha256': p.file_hash(audit_source),
        'control_root': str(repo/'.superpowers/sdd/restore-qualification-v2'),
        'publication_root': str(publication), 'runtime': d.runtime_v2_identity(),
        'comparator_path': str(comparator), 'comparator_sha256': p.file_hash(comparator),
        'launcher_path': str(launcher), 'launcher_sha256': p.file_hash(launcher),
        'diagnostic_driver_sha256': p.file_hash(driver), 'contract': str(contract),
        'contract_sha256': p.file_hash(contract), 'history_inputs': {}, 'prior_output': str(original.parent),
        'prior_inventory': p.hash_ledger(original.parent),
        'preserved_sets': [{'root': str(original.parent), 'files': p.hash_ledger(original.parent)}],
        'protected_roots': [str(original.parent), str(original)],
        'profile_sha256': d.PROFILE, 'protocol_sha256': p.TRAVEL_PROTOCOL_SHA256}
    regpath = repo/'registration.json'; regpath.write_text(json.dumps(registration))
    (root/'registration.json').write_text(json.dumps(registration))
    (root/'source-copy.json').write_text(json.dumps(copied))
    now = time.monotonic()
    comparison = d.compare_states(*posts, {'old'}, {'old'})
    candidate = {'equal': True, 'contract_id': registration['state_contract'],
        'left_digest': 'a'*64, 'right_digest': 'a'*64}
    receipt = {'schema': 'memory-restore-execution-v2', 'mode': 'restore-v2',
        'output': str(root), 'registration_sha256': p.file_hash(regpath),
        'state_contract': registration['state_contract'], 'source_identity': {},
        'process_namespace': os.readlink('/proc/self/ns/pid'), 'seconds_caps': [600, 300],
        'started_monotonic': now-2, 'owner_deadline_monotonic': now+598,
        'global_deadline_monotonic': now+898, 'readout_started_monotonic': now-1,
        'readout_deadline_monotonic': now+299, 'status': 'narrow-restore-provisional-pass',
        'attempted': attempts, 'cleanup': cleanup, 'comparison': comparison,
        'restore_pair_matches': False, 'candidate_comparison': candidate,
        'candidate_restore_pair_matches': True, 'source_and_prior_evidence_unchanged': True,
        'narrow_restore_passed': False, 'native_prerequisites_passed': False,
        'qualification_claims': [], 'paired_pilot': 'unattempted-by-scope', 'held_out_used': False,
        'artifact_index': p.hash_ledger(root)}
    (root/'execution.json').write_text(json.dumps(receipt))
    monkeypatch.setattr(p, 'audit_run', lambda job, *args: p.read_json(Path(job['output'])/'worker-report.json'))
    monkeypatch.setattr(p, 'read_raw', lambda *args: {'rows': [{'tick': n} for n in range(5)]})
    monkeypatch.setattr(d, 'owner_exited', lambda owner: True)
    monkeypatch.setattr(a.o, 'compare_reproducibility_states', lambda *args: candidate)
    monkeypatch.setattr(p, 'launch_owner', lambda *args, **kwargs: pytest.fail('native owner launch forbidden'))
    monkeypatch.setattr(d, 'cleanup_owners', lambda *args: pytest.fail('auditor must observe, not kill owners'))
    return a, regpath, root, receipt


def test_fresh_audit_independently_closes_candidate_without_promoting_other_gates(tmp_path, monkeypatch):
    a, regpath, root, before = completed_pair(tmp_path, monkeypatch)
    assert a.audit(regpath) == 0
    close = p.read_json(root/'scientific-close.json')
    assert close['narrow_restore_passed'] is True and close['trace_equal'] is True
    assert close['restore_pair_matches'] is False and close['candidate_restore_pair_matches'] is True
    assert close['native_prerequisites_passed'] is False and close['qualification_claims'] == []
    assert close['paired_pilot'] == 'unattempted-by-scope' and close['physics_steps'] == 0
    assert p.read_json(root/'execution.json') == before  # Driver remains provisional.
    assert len(close['allocated_jobs']) == len(close['started_owners']) == 2
    with pytest.raises(FileExistsError):
        a.audit(regpath)


@pytest.mark.parametrize('failure', ['namespace', 'active-owner', 'extra-job', 'supervision',
    'raw-count', 'trace', 'invariant', 'candidate', 'post-checksum', 'changed-input', 'changed-raw',
    'auditor-pin', 'expired-readout', 'driver-failure', 'late-close', 'storage-close', 'failed-invalidation'])
def test_failed_fresh_readback_never_leaves_a_passing_close(tmp_path, monkeypatch, failure):
    a, regpath, root, receipt = completed_pair(tmp_path, monkeypatch)
    if failure == 'namespace':
        receipt['process_namespace'] = 'pid:[different]'
    elif failure == 'driver-failure':
        receipt['status'] = 'narrow-restore-failure'
    elif failure == 'active-owner':
        monkeypatch.setattr(d, 'owner_exited', lambda owner: False)
    elif failure == 'extra-job':
        job = next((root/'stage/jobs').glob('*.json'))
        (job.parent/('f'*32+'.json')).write_bytes(job.read_bytes())
    elif failure == 'supervision':
        supervision = root/'stage/supervision'/receipt['attempted'][0]['run_id']/'supervisor.json'
        supervision.write_text(json.dumps({**receipt['attempted'][0]['supervision'], 'returncode': 1}))
    elif failure == 'raw-count':
        monkeypatch.setattr(p, 'read_raw', lambda *args: {'rows': [{}]*4})
    elif failure in ('trace', 'invariant'):
        original = p.audit_run
        def bad_report(job, *args):
            report = original(job, *args)
            if job['spec']['id'] == 'restore-2':
                report['trace_digest' if failure == 'trace' else 'invariants_preserved'] = ('b'*64 if failure == 'trace' else False)
            return report
        monkeypatch.setattr(p, 'audit_run', bad_report)
    elif failure == 'candidate':
        monkeypatch.setattr(a.o, 'compare_reproducibility_states', lambda *args: {**receipt['candidate_comparison'], 'equal': False})
    elif failure == 'changed-raw':
        def changed_raw(*args):
            report = Path(receipt['attempted'][0]['run'])/'worker-report.json'
            report.write_text(report.read_text()+'\n')
            return receipt['candidate_comparison']
        monkeypatch.setattr(a.o, 'compare_reproducibility_states', changed_raw)
    elif failure == 'auditor-pin':
        Path(p.read_json(regpath)['auditor_path']).write_text('changed auditor source\n')
    elif failure == 'expired-readout':
        now = time.monotonic()
        receipt.update(started_monotonic=now-902, owner_deadline_monotonic=now-302,
            global_deadline_monotonic=now-2, readout_started_monotonic=now-301,
            readout_deadline_monotonic=now-2)
    elif failure == 'post-checksum':
        Path(receipt['attempted'][0]['post_snapshot_path']).write_bytes(b'corrupt')
    elif failure == 'changed-input':
        calls = []
        def changed(reg, deadline=None):
            calls.append(True)
            if len(calls) > 1:
                raise ValueError('Registered source changed at close')
        monkeypatch.setattr(d, 'recheck_v2_inputs', changed)
    elif failure in ('late-close', 'storage-close', 'failed-invalidation'):
        original = a.replace_control; published = []
        def publish(path, value, storage):
            if failure == 'failed-invalidation' and published and not value.get('narrow_restore_passed'):
                raise OSError('Invalidation could not publish')
            original(path, value, storage)
            if value.get('narrow_restore_passed'):
                published.append(True)
        monkeypatch.setattr(a, 'replace_control', publish)
        if failure in ('late-close', 'failed-invalidation'):
            original_time = time.monotonic
            monkeypatch.setattr(a.time, 'monotonic', lambda: original_time()+(1000 if published else 0))
        else:
            original_check = StorageBudget.check
            def check(self, size, *, path):
                if published and size == 0:
                    raise OSError('Storage recount refused')
                return original_check(self, size, path=path)
            monkeypatch.setattr(StorageBudget, 'check', check)
    (root/'execution.json').write_text(json.dumps(receipt))
    assert a.audit(regpath) == 1
    if failure == 'failed-invalidation':
        assert not (root/'scientific-close.json').exists()
        assert p.read_json(root/'scientific-close.invalidated.json')['narrow_restore_passed'] is True
        return
    close = p.read_json(root/'scientific-close.json')
    assert close['narrow_restore_passed'] is False
    assert close['native_prerequisites_passed'] is False and close['qualification_claims'] == []
    assert close['error']
    if failure == 'driver-failure':
        assert len(close['allocated_jobs']) == len(close['started_owners']) == len(close['owners']) == 2
        assert all(row['disposition'] == 'started-incomplete' for row in close['owners'])
