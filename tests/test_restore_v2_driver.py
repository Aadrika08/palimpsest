"""Fresh-mode software checks; completed-owner doubles never launch physics."""
import copy
import json
import os
from pathlib import Path

import pytest

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from test_memory_restore_diagnostic import post_state


def registration(repo):
    evidence = repo/'docs/reports/restore-qualification-v2-evidence'
    return {'schema': 'memory-restore-registration-v2', 'mode': 'restore-v2',
        'state_contract': 'restore-reproducibility-v2-candidate',
        'repo': str(repo), 'assets': str(repo/'assets'), 'history_root': str(repo/'histories'),
        'profile_sha256': d.PROFILE, 'protocol_sha256': p.TRAVEL_PROTOCOL_SHA256,
        'seconds_caps': [600, 300], 'implementation_commit': '0'*40,
        'output': str(repo/'runs/restore-v2-pair-fixture'), 'source_identity': {},
        'source_snapshot': {'path': str(repo/'old/source.snp'), 'sha256': 'a'*64,
                            'bytes': 100, 'invariant': 'b'*64},
        'prior_output': str(repo/'old'), 'prior_inventory': [],
        'preserved_sets': [{'root': str(repo/'old'), 'files': []}],
        'protected_roots': [str(repo/'old'), str(repo/'old/source.snp')],
        'control_root': str(repo/'.superpowers/sdd/restore-qualification-v2'),
        'publication_root': str(evidence),
        'comparator_path': str(repo/'scripts/memory_restore_offline_readout.py'),
        'comparator_sha256': 'c'*64,
        'auditor_path': str(repo/'scripts/memory_restore_v2_audit.py'), 'auditor_sha256': 'd'*64,
        'launcher_path': str(evidence/'execute-restore-v2.py'), 'launcher_sha256': 'e'*64,
        'runtime': {'fixture': True},
        'expected_specs': p.travel_specs('travel-feasibility', d.PROFILE)[-2:]}


@pytest.mark.parametrize('outcome', ['pass', 'trace', 'invariant', 'candidate', 'readout', 'late'])
def test_fresh_main_preserves_legacy_and_never_publishes_terminal_pass(tmp_path, monkeypatch, outcome):
    repo = tmp_path/'repo'; (repo/'scripts').mkdir(parents=True)
    monkeypatch.setattr(d, '__file__', str(repo/'scripts/memory_restore_diagnostic.py'))
    reg = registration(repo); output = Path(reg['output'])
    regfile = tmp_path/'registration.json'; regfile.write_text(json.dumps(reg))
    monkeypatch.setattr(d.subprocess, 'check_output',
        lambda command, **kwargs: '0'*40+'\n' if 'rev-parse' in command else b'')
    checks = []
    def recheck(registration, deadline=None):
        checks.append(True)
        if len(checks) == 2 and outcome == 'readout':
            raise ValueError('frozen source changed')
    monkeypatch.setattr(d, 'recheck_v2_inputs', recheck, raising=False)
    monkeypatch.setattr(p, 'preflight', lambda *a, **kw: {'output': str(output/'stage')})
    from contextlib import nullcontext
    from palimpsest.storage import StorageBudget
    monkeypatch.setattr(StorageBudget, 'lock', lambda self: nullcontext())
    monkeypatch.setattr(d, 'copy_source', lambda *a: {})
    monkeypatch.setattr(d, 'run_pair', lambda *a: [])
    monkeypatch.setattr(d, 'cleanup_owners', lambda root: [])
    rows = [{'job_id': 'restore-'+str(index+1), 'run_id': str(index),
        'raw_audit_pass': True, 'matching_owner_exited': True,
        'retained_post_state_audited': True, 'raw_rows': 5,
        'audit': {'trace_digest': 'different' if outcome == 'trace' and index else 'same',
                  'invariants_preserved': outcome != 'invariant'}} for index in range(2)]
    monkeypatch.setattr(d, 'audit_owners', lambda *a: rows)
    monkeypatch.setattr(d, 'audit_post_state', lambda *a: (post_state(), {'old'}))
    from scripts import memory_restore_offline_readout as comparator
    candidate = {'equal': outcome != 'candidate', 'contract_id': reg['state_contract'],
                 'left_digest': '1'*64, 'right_digest': '1'*64, 'differing_components': []}
    monkeypatch.setattr(comparator, 'compare_reproducibility_states', lambda *a: copy.deepcopy(candidate))
    expired = []
    if outcome == 'late':
        real_time = d.time.monotonic
        monkeypatch.setattr(d.time, 'monotonic', lambda: real_time()+(10000 if expired else 0))
        real_replace = d.replace_control
        def replace(path, value, storage):
            real_replace(path, value, storage)
            if value.get('status') == 'narrow-restore-provisional-pass':
                expired.append(True)
        monkeypatch.setattr(d, 'replace_control', replace)
    assert d.main(['--registration', str(regfile)]) == (0 if outcome == 'pass' else 1)
    receipt = p.read_json(output/'execution.json')
    assert receipt['schema'] == 'memory-restore-execution-v2'
    assert receipt['narrow_restore_passed'] is False
    assert receipt['native_prerequisites_passed'] is False
    assert receipt['qualification_claims'] == []
    assert receipt['process_namespace'] == os.readlink('/proc/self/ns/pid')
    assert not (output/'scientific-close.json').exists()
    if outcome not in ('readout', 'late'):
        assert receipt['comparison']['equal'] is True
        assert receipt['restore_pair_matches'] is (outcome not in ('trace', 'invariant'))
        assert receipt['candidate_comparison']['equal'] is (outcome != 'candidate')
        assert receipt['candidate_restore_pair_matches'] is (outcome == 'pass')
        assert receipt['total_new_controls'] == 10


@pytest.mark.parametrize('schema,mode', [('memory-restore-registration-v1','restore-v2'),
                                       ('memory-restore-registration-v2','diagnose'),
                                       ('memory-restore-registration-v2','qualify')])
def test_cross_schema_refused_before_any_allocation(tmp_path, monkeypatch, schema, mode):
    reg = registration(tmp_path); reg.update(schema=schema, mode=mode)
    path = tmp_path/'registration.json'; path.write_text(json.dumps(reg))
    monkeypatch.setattr(p, 'preflight', lambda *a, **kw: pytest.fail('allocated'))
    with pytest.raises(ValueError, match='registration'):
        d.main(['--registration', str(path)])
    assert not Path(reg['output']).exists()


@pytest.mark.parametrize('change', ['contract', 'comparator', 'runtime', 'source-overlap', 'control-overlap'])
def test_v2_binding_refusal_precedes_native_allocation(tmp_path, monkeypatch, change):
    reg = registration(tmp_path)
    if change == 'contract': reg['state_contract'] = 'other'
    elif change == 'comparator': reg.pop('comparator_sha256')
    elif change == 'runtime': reg.pop('runtime')
    elif change == 'source-overlap': reg['output'] = reg['prior_output']+'/new'
    else: reg['output'] = reg['control_root']+'/new'
    path = tmp_path/'registration.json'; path.write_text(json.dumps(reg))
    monkeypatch.setattr(d, '__file__', str(tmp_path/'scripts/memory_restore_diagnostic.py'))
    monkeypatch.setattr(p, 'preflight', lambda *a, **kw: pytest.fail('allocated'))
    with pytest.raises(ValueError):
        d.main(['--registration', str(path)])
    assert not Path(reg['output']).exists()


def test_v2_budget_counts_publication_and_controls(tmp_path):
    reg = registration(tmp_path); root = Path(reg['publication_root']); root.mkdir(parents=True)
    (root/'material').write_bytes(b'12345')
    control = Path(reg['control_root']); control.mkdir(parents=True)
    (control/'launched.json').write_bytes(b'1234567')
    output = Path(reg['output']); output.mkdir(parents=True)
    (output/'recording').write_bytes(b'123456789')
    assert d.restore_v2_budget(reg).usage()['used_bytes'] == 21


def test_changed_runtime_or_comparator_is_refused_before_source_read(tmp_path, monkeypatch):
    reg = registration(tmp_path)
    monkeypatch.setattr(d, 'runtime_v2_identity', lambda: {'fixture': False}, raising=False)
    monkeypatch.setattr(d, 'recheck_inputs', lambda *a: pytest.fail('source read before pin check'))
    with pytest.raises(ValueError, match='runtime'):
        d.recheck_v2_inputs(reg)


def test_wrong_comparator_pin_refused_before_source_read(tmp_path, monkeypatch):
    reg = registration(tmp_path)
    path = Path(reg['comparator_path']); path.parent.mkdir()
    path.write_bytes(b'changed comparator')
    monkeypatch.setattr(d, 'runtime_v2_identity', lambda: reg['runtime'])
    monkeypatch.setattr(d, 'recheck_inputs', lambda *a: pytest.fail('source read before pin check'))
    with pytest.raises(ValueError, match='comparator changed'):
        d.recheck_v2_inputs(reg)
