"""The matrix must exercise real interfaces, preserve input identity, and retain refusals."""
import dataclasses
import importlib
import json
import os
from pathlib import Path
import sys

import pytest

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO))
from paper.studies.authority_replay_v1.common import declared_units, load_protocol, sha256_file

PROTOCOL = load_protocol(REPO / 'paper/studies/authority_replay_v1/protocol.json')
CASES = {case.id: case for case in PROTOCOL.fault_cases}
IDENTITY = {'commit': 'a' * 40, 'protocol_sha256': PROTOCOL._content_sha256,
            'runtime_source_sha256': {'src/palimpsest/engine.py': 'b' * 64},
            'asset_manifest_sha256': {'model_manifests/flynn-full-vision.json': 'c' * 64},
            'asset_sha256': {'checkpoint': 'd' * 64}}
FIXTURES = [u for u in declared_units(PROTOCOL) if u['kind'] == 'fault' and CASES[u['case_id']].path != 'runtime']
RUNTIME = [u for u in declared_units(PROTOCOL) if u['kind'] == 'fault' and CASES[u['case_id']].path == 'runtime' and u['seed'] == 0]


def module():
    return importlib.import_module('paper.studies.authority_replay_v1.fault_matrix')


def narrow(unit):
    return dataclasses.replace(CASES[unit['case_id']], seeds=[] if unit['seed'] is None else [unit['seed']],
                               variants=[unit['variant']], conditions=[unit['condition']])


def assert_row(row, unit, root):
    assert all(row[k] == v for k, v in unit.items())
    assert row['identity'] == IDENTITY
    assert row['status'] == 'completed', row
    assert row['metrics']['elapsed_seconds'] >= 0
    assert row['retained_prefix_valid'] is True
    assert row['silent_acceptance'] is False
    assert row['benign_false_rejection'] is False
    assert (root / 'trace.json').is_file()
    trace = json.loads((root / 'trace.json').read_text())
    assert row['baseline_outcome']['accepted'] == module().naive_accepts(unit['case_id'], trace)
    assert row['source_hashes_before'] == row['source_hashes_after']
    if unit['condition'] == 'benign_control':
        assert not row['explicit_detection'] and not row['correct_recovery']
    else:
        assert row[CASES[unit['case_id']].expected_outcome] is True, row


@pytest.mark.parametrize('unit', FIXTURES, ids=lambda u: u['unit_id'])
def test_every_fixture_fault_and_benign_control_uses_production_interfaces(tmp_path, unit):
    row = module().run_fault_case(narrow(unit), tmp_path / 'unit', IDENTITY)
    assert_row(row, unit, tmp_path / 'unit')
    assert row['execution_path'] == 'fixture-production-interfaces'
    if unit['case_id'] == 'P1':
        assert row['trace']['child_returncode'] == 23
        assert row['trace']['terminal_success'] is False
        assert row['trace']['published_ticks'] == (64 if unit['variant'] == 'before_terminal_manifest' else 32)
        assert row['trace']['direct_writer_accepted'] is True
        assert row['trace']['direct_writer_ticks'] == 64
        direct_ticks = [json.loads(line) for line in (tmp_path / 'unit/direct-writer.jsonl').read_text().splitlines()]
        assert [t['tick'] for t in direct_ticks] == list(range(64))
    if unit['case_id'] == 'E1':
        assert row['trace']['used_bytes'] <= row['trace']['cap_bytes']
        assert row['trace']['required_bytes'] == row['trace']['cap_bytes'] + 1
    if unit['case_id'] == 'E2':
        assert row['trace']['accepted_items'] == row['trace']['retained_items']
        assert row['trace']['stats']['backpressure_events'] >= 1
        assert row['trace']['stats']['max_queued_items'] <= row['trace']['queue_bound']
    if unit['case_id'] == 'E3':
        assert row['trace']['failure_calls'] == 1
        assert row['trace']['closed'] is True
        assert row['trace']['late_rejected'] is True


@pytest.mark.simulation
@pytest.mark.assets
@pytest.mark.parametrize('unit', RUNTIME, ids=lambda u: u['unit_id'])
def test_every_runtime_fault_uses_full_flynn_and_real_semantics(tmp_path, unit):
    if os.environ.get('PALIMPSEST_SIMULATION_TESTS') != '1':
        pytest.skip('actual FLYNN integration is opt in')
    row = module().run_fault_case(narrow(unit), tmp_path / 'unit', IDENTITY)
    assert_row(row, unit, tmp_path / 'unit')
    assert row['execution_path'] == 'cpu-flynn-runtime'
    assert row['trace']['controller'] == 'flynn'
    assert row['trace']['policy_loaded'] is True
    assert row['trace']['policy_invocations'] > 0
    if unit['case_id'].startswith('R'):
        assert row['trace']['claimed_mode'] == 'policy'
        assert row['trace']['replay_inference_executed'] is False
        assert row['trace']['replay_policy_invocations'] == 0
    if unit['case_id'].startswith('D'):
        assert row['trace']['replay_ticks'] == 0
        assert row['trace']['replay_policy_invocations'] == 0
        assert row['trace']['copied_target_sha256_before'] != row['trace']['copied_target_sha256_after']
    if unit['case_id'] == 'D2':
        assert row['trace']['asset_schema_before'] == row['trace']['asset_schema_after']
        assert row['trace']['shape_matches'] is True and row['trace']['load_succeeded'] is True
    if unit['case_id'] == 'S2':
        assert row['trace']['destination_unchanged'] is True
    if unit['case_id'] == 'B1':
        assert len(set(row['trace']['owner_pids'])) == 3


@pytest.mark.parametrize('case_id,trace,accepted', [
    ('A1', {'request_accepted': True}, True), ('A1', {'request_accepted': False}, False),
    ('A2', {'request_parsed': True}, True), ('A3', {'accepted_requests': 1}, False),
    ('R1', {'viewable': True}, True), ('R2', {'trajectory_matches': False, 'final_state_matches': False}, False),
    ('S1', {'pose_restored': True, 'continued': True}, True),
    ('S2', {'snapshot_readable': True, 'process_progress': False}, False),
    ('D1', {'initial_setup_succeeded': True}, True), ('D2', {'shape_matches': True}, True),
    ('C1', {'start_hash_matches': True}, True), ('C2', {'exit_hash_matches': False}, False),
    ('C3', {'protected_content_unchanged': True}, True),
    ('P1', {'output_exists': True}, True), ('B1', {'pose_copies_completed': True}, True),
    ('B2', {'reset_pose_copy_completed': True}, True), ('E1', {'write_attempted': True}, True),
    ('E2', {'producer_returned': True}, True), ('E3', {'output_exists': False, 'process_continued': False}, False),
])
def test_naive_predicate_is_computed_from_same_observed_trace(case_id, trace, accepted):
    assert module().naive_accepts(case_id, trace) is accepted


def test_refusal_is_not_successful_recovery():
    classify = module().classify_outcome
    refused = classify({'semantic_outcome': 'refused', 'semantic_invalid': True}, 'fault')
    assert refused == {'silent_acceptance': False, 'explicit_detection': True,
                       'correct_recovery': False, 'benign_false_rejection': False}
    recovered = classify({'semantic_outcome': 'recovered', 'semantic_invalid': True}, 'fault')
    assert recovered['correct_recovery'] and not recovered['explicit_detection']
    assert classify({'semantic_outcome': 'refused', 'semantic_invalid': False}, 'benign')['benign_false_rejection']
    assert classify({'semantic_outcome': 'accepted', 'semantic_invalid': True}, 'fault')['silent_acceptance']


def test_first_divergence_uses_frozen_policy_and_deterministic_order():
    import numpy as np
    compare = module().first_divergence
    left = [{'z': np.array([0.], np.float32), 'a': np.array([1], np.int32)}]
    right = [{'z': np.array([1.], np.float32), 'a': np.array([2], np.int32)}]
    assert compare(left, right) == {'field': 'a', 'tick': 0, 'reason': 'value'}
    assert compare([{'x': np.array([float('nan'), 1.], np.float32)}],
                   [{'x': np.array([float('nan'), 1.0000001], np.float32)}]) is None
    assert compare([{'x': np.array([float('nan')], np.float32)}],
                   [{'x': np.array([0.], np.float32)}])['field'] == 'x'


@pytest.mark.parametrize('variant', ['graph', 'mapping', 'checkpoint'])
def test_asset_substitution_is_independently_parseable_and_preserves_observed_schema(tmp_path, variant):
    if variant == 'checkpoint':
        import torch
        target = tmp_path / 'checkpoint.pt'
        torch.save({'weight': torch.tensor([[1., 2.]], dtype=torch.float32),
                    'ids': torch.tensor([2, 3], dtype=torch.int64)}, target)
    else:
        target = tmp_path / 'asset.csv'
        target.write_text('pre_root_id,post_root_id,neuropil,syn_count,nt_type\n1,2,ME_L,12,GABA\n'
                          if variant == 'graph' else 'root_id,flow,super_class\n1,efferent,descending\n')
    before = sha256_file(target)
    observed = module()._substitute_same_shape(target, variant)
    assert sha256_file(target) != before
    assert observed['asset_schema_before'] == observed['asset_schema_after']
    assert observed['shape_matches'] is True and observed['load_succeeded'] is True
    assert module()._asset_schema(target, variant) == observed['asset_schema_after']


def test_output_is_exclusive_and_multiunit_case_is_refused(tmp_path):
    root = tmp_path / 'out'
    root.mkdir()
    (root / 'untouched').write_text('original')
    with pytest.raises(ValueError, match='empty|non-empty'):
        module().run_fault_case(CASES['C1'], root, IDENTITY)
    assert (root / 'untouched').read_text() == 'original'
    with pytest.raises(ValueError, match='single|narrow'):
        module().run_fault_case(CASES['A1'], tmp_path / 'multi', IDENTITY)


def test_fixture_source_is_copied_and_original_hash_rechecked(tmp_path, monkeypatch):
    source = tmp_path / 'source.txt'
    source.write_text('never mutate this fixture')
    before = sha256_file(source)
    monkeypatch.setattr(module(), 'FIXTURE_SOURCE', source)
    row = module().run_fault_case(CASES['C1'], tmp_path / 'out', IDENTITY)
    assert sha256_file(source) == before
    assert row['source_hashes_before'] == row['source_hashes_after'] == {str(source): before}


def test_fixture_dry_campaign_preserves_declared_denominator_and_analyzer_accepts(tmp_path):
    from paper.studies.authority_replay_v1.analyze import summarize
    output = tmp_path / 'dry'
    rows = module().run_campaign(PROTOCOL, output, IDENTITY, fixture_only=True)
    faults = [r for r in rows if r['kind'] == 'fault']
    assert len(faults) == 50
    assert {r['unit_id'] for r in faults} == {u['unit_id'] for u in declared_units(PROTOCOL) if u['kind'] == 'fault'}
    for row in faults:
        if CASES[row['case_id']].path == 'runtime':
            assert row['status'] == 'incomplete' and row['dry_run'] is True
        else:
            assert row['status'] == 'completed', row
    summary = summarize(PROTOCOL, rows)
    assert summary['declared_units'] == len(declared_units(PROTOCOL))
    assert summary['by_kind']['fault']['denominator'] == 50


def test_unit_admission_preserves_six_gib_reserve(tmp_path, monkeypatch):
    import collections
    disk = collections.namedtuple('disk', 'total used free')
    monkeypatch.setattr(module().shutil, 'disk_usage', lambda path: disk(20 * 1024**3, 15 * 1024**3, 5 * 1024**3))
    with pytest.raises(ValueError, match='free-space reserve'):
        module().run_fault_case(CASES['C1'], tmp_path / 'out', IDENTITY)


def test_campaign_retains_failed_units_and_stops_after_timeout(tmp_path, monkeypatch):
    import dataclasses
    calls = []
    def timed_out(case, output, identity):
        calls.append(case.id)
        return {'schema_version': 1, 'study_id': PROTOCOL.study_id, **module()._descriptor(case),
                'identity': identity, 'status': 'timeout', 'metrics': {'output_bytes': 0}}
    monkeypatch.setattr(module(), 'run_fault_case', timed_out)
    rows = module().run_campaign(PROTOCOL, tmp_path / 'campaign', IDENTITY, fixture_only=True)
    assert calls == ['C1']
    assert next(r for r in rows if r.get('case_id') == 'C1')['status'] == 'timeout'
    assert all(r['status'] == 'incomplete' for r in rows if r.get('case_id') != 'C1')
    assert len(rows) == len(declared_units(PROTOCOL))


def test_campaign_rechecks_frozen_identity_and_preserves_drift_failure(tmp_path, monkeypatch):
    checks, calls = [], []
    def identity_check(*args):
        checks.append(True)
        return IDENTITY if len(checks) == 1 else {**IDENTITY, 'commit': 'f' * 40}
    def completed(case, output, identity):
        calls.append(case.id)
        return {'schema_version': 1, 'study_id': PROTOCOL.study_id, **module()._descriptor(case),
                'identity': identity, 'status': 'completed', 'metrics': {'output_bytes': 0}}
    monkeypatch.setattr(module(), 'campaign_identity', identity_check)
    monkeypatch.setattr(module(), 'run_fault_case', completed)
    rows = module().run_campaign(PROTOCOL, tmp_path / 'campaign', IDENTITY)
    assert calls == ['A1']
    assert rows[0]['status'] == 'failed'
    assert rows[0]['error']['type'] == 'SourceMutation'
    assert all(r['status'] == 'incomplete' for r in rows[1:])


def test_campaign_keeps_denominator_when_unit_admission_refuses(tmp_path, monkeypatch):
    monkeypatch.setattr(module(), 'campaign_identity', lambda *args: IDENTITY)
    def refuse(*args):
        raise ValueError('filesystem free-space reserve insufficient for unit admission')
    monkeypatch.setattr(module(), 'run_fault_case', refuse)
    rows = module().run_campaign(PROTOCOL, tmp_path / 'campaign', IDENTITY)
    assert len(rows) == 50
    assert all(r['status'] == 'incomplete' for r in rows)
    assert 'free-space reserve' in rows[0]['reason']


def test_campaign_counts_other_drivers_in_shared_root(tmp_path, monkeypatch):
    root = tmp_path / 'paper-authority-replay-v1'
    root.mkdir()
    (root / 'other-driver.bin').write_bytes(b'x' * 2048)
    limited = dataclasses.replace(PROTOCOL, resources={**PROTOCOL.resources, 'campaign_max_output_bytes': 1024})
    monkeypatch.setattr(module(), 'campaign_identity', lambda *args: IDENTITY)
    monkeypatch.setattr(module(), 'run_fault_case', lambda *args: pytest.fail('shared cap must prevent execution'))
    rows = module().run_campaign(limited, root / 'faults', IDENTITY, campaign_root=root)
    assert len(rows) == 50 and all(r['status'] == 'incomplete' for r in rows)
    assert 'output cap' in rows[0]['reason']


def test_campaign_preserves_a_shared_cap_crossing_as_a_failed_unit(tmp_path, monkeypatch):
    root = tmp_path / 'campaign'
    root.mkdir()
    limited = dataclasses.replace(PROTOCOL, resources={**PROTOCOL.resources,
        'campaign_max_output_bytes': 65536, 'ordinary_unit_max_output_bytes': 1})
    monkeypatch.setattr(module(), 'campaign_identity', lambda *args: IDENTITY)
    calls = []
    def cross(case, output, identity):
        calls.append(case.id)
        (root / 'other-driver.bin').write_bytes(b'x' * 65537)
        return {'schema_version': 1, 'study_id': PROTOCOL.study_id, **module()._descriptor(case),
                'identity': identity, 'status': 'completed', 'metrics': {'output_bytes': 0}}
    monkeypatch.setattr(module(), 'run_fault_case', cross)
    rows = module().run_campaign(limited, root / 'faults', IDENTITY, campaign_root=root)
    assert calls == ['A1'] and rows[0]['status'] == 'failed'
    assert rows[0]['error']['type'] == 'CampaignOutputCap'
    assert all(r['status'] == 'incomplete' for r in rows[1:])


def test_campaign_shared_deadline_stops_before_any_unit(tmp_path, monkeypatch):
    import time
    monkeypatch.setattr(module(), 'campaign_identity', lambda *args: IDENTITY)
    monkeypatch.setattr(module(), 'run_fault_case', lambda *args: pytest.fail('expired deadline must prevent execution'))
    rows = module().run_campaign(PROTOCOL, tmp_path / 'faults', IDENTITY,
                                 campaign_deadline_epoch=time.time() - 1)
    assert len(rows) == 50 and all(r['status'] == 'incomplete' for r in rows)
    assert 'wall-clock' in rows[0]['reason']


def test_standard_campaign_subroots_share_parent_accounting(tmp_path):
    root = tmp_path / 'paper-authority-replay-v1'
    assert module()._campaign_resource_root(root / 'faults', None) == root.resolve()
    assert module()._campaign_resource_root(tmp_path / 'isolated-dry', None) == (tmp_path / 'isolated-dry').resolve()


def test_runtime_child_wait_is_bounded_by_shared_deadline(tmp_path, monkeypatch):
    import subprocess
    import time
    monkeypatch.setattr(module(), 'CAMPAIGN_DEADLINE_EPOCH', time.time() + .25)
    start = time.monotonic()
    with (tmp_path / 'stdout').open('w') as stdout, (tmp_path / 'stderr').open('w') as stderr:
        with pytest.raises(subprocess.TimeoutExpired):
            module()._runtime_process([sys.executable, '-c', 'import time; time.sleep(30)'], stdout, stderr, 30)
    assert time.monotonic() - start < 3


def test_persisted_campaign_clock_cannot_be_extended_and_binds_identity(tmp_path):
    import time
    root = tmp_path / 'campaign'
    root.mkdir()
    now = time.time()
    clock = {'identity': IDENTITY, 'started_unix': now - 100, 'deadline_unix': now - 1}
    (root / 'campaign-clock.json').write_text(json.dumps(clock))
    assert module()._campaign_deadline(root, IDENTITY, 14400, now + 1000) == clock['deadline_unix']
    assert module()._campaign_deadline(root, IDENTITY, 14400, now - 10) == now - 10
    with pytest.raises(ValueError, match='identity drift'):
        module()._campaign_deadline(root, {**IDENTITY, 'commit': 'f' * 40}, 14400, None)


def test_campaign_base_is_shared_readonly_and_drift_copies_are_private(tmp_path, monkeypatch):
    campaign = tmp_path / 'campaign'
    campaign.mkdir()
    monkeypatch.setattr(module(), 'CAMPAIGN_ROOT', campaign)
    copies = []
    def copy_runtime(root):
        copies.append(root)
        repo, assets = root / 'copied-repo', root / 'copied-assets'
        (repo / 'src/palimpsest').mkdir(parents=True)
        (repo / 'src/palimpsest/engine.py').write_text('original source')
        assets.mkdir()
        (assets / 'checkpoint').write_bytes(b'original asset')
        return repo, assets
    monkeypatch.setattr(module(), '_copy_runtime', copy_runtime)
    def unit(name):
        root = campaign / name
        root.mkdir()
        return root
    first = module()._runtime_inputs(narrow(RUNTIME[0]), unit('first'))
    second = module()._runtime_inputs(narrow(RUNTIME[1]), unit('second'))
    assert first == second and len(copies) == 1
    assert first[0].stat().st_mode & 0o222 == 0
    source_unit = {'case_id': 'D1', 'seed': 0, 'variant': 'source', 'condition': 'fault'}
    source_repo, source_assets = module()._runtime_inputs(narrow(source_unit), unit('drift-source'))
    assert source_repo != first[0] and source_assets == first[1]
    asset_unit = {'case_id': 'D2', 'seed': 0, 'variant': 'checkpoint', 'condition': 'fault'}
    asset_repo, private_assets = module()._runtime_inputs(narrow(asset_unit), unit('drift-asset'))
    assert asset_repo == first[0] and private_assets != first[1]
    target = private_assets / 'checkpoint'
    target.chmod(0o600)
    target.write_bytes(b'changed asset')
    assert (first[1] / 'checkpoint').read_bytes() == b'original asset'


def test_runtime_timeout_kills_the_entire_owner_process_group(tmp_path):
    import subprocess
    import time
    pid_file = tmp_path / 'descendant.pid'
    code = "import subprocess,sys,time; from pathlib import Path; child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)']); Path(sys.argv[1]).write_text(str(child.pid)); time.sleep(30)"
    with (tmp_path / 'stdout').open('w') as stdout, (tmp_path / 'stderr').open('w') as stderr:
        with pytest.raises(subprocess.TimeoutExpired):
            module()._runtime_process([sys.executable, '-c', code, str(pid_file)], stdout, stderr, 1.0)
    pid = int(pid_file.read_text())
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        stat = Path(f'/proc/{pid}/stat')
        if not stat.exists() or stat.read_text().split()[2] == 'Z':
            break
        time.sleep(.01)
    else:
        pytest.fail('timed-out runtime left a live descendant owner')


@pytest.mark.simulation
@pytest.mark.assets
def test_actual_flynn_can_execute_against_readonly_campaign_base(tmp_path, monkeypatch):
    if os.environ.get('PALIMPSEST_SIMULATION_TESTS') != '1':
        pytest.skip('actual FLYNN integration is opt in')
    root = tmp_path / 'implementation-verification'
    root.mkdir()
    monkeypatch.setattr(module(), 'CAMPAIGN_ROOT', root)
    unit = next(u for u in RUNTIME if u['case_id'] == 'A1')
    row = module().run_fault_case(narrow(unit), root / 'unit', IDENTITY)
    assert_row(row, unit, root / 'unit')
    assert row['shared_base_unchanged'] is True
    assert row['shared_base_identity_before'] == row['shared_base_identity_after']
