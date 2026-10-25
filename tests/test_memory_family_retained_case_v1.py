"""Whole-case authored retained fixtures; no genuine qualification or study."""
import copy
import math
import importlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest

from palimpsest import artifacts, memory
from scripts import memory_condition_replay_admission_v1 as qualification
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_condition_seal_v4 as seal
from scripts import memory_family_retained_condition_v1 as retained
from test_memory_family_condition_close_v4 import fixture, tree
from test_memory_family_oracle_v3 import evidence
from test_memory_family_retained_condition_v1 import seal_authored

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = compact.PROTOCOL['analysis_contract']['conditions']
NAME = 'scripts.memory_family_retained_case_v1'


def module():
    return importlib.import_module(NAME)


def build_case(root, *, natural_failure=True, row=0, kind='change'):
    samples = {}
    with pytest.MonkeyPatch.context() as patch:
        for condition in CONDITIONS:
            own = samples.get('own')
            sample = fixture(root, row=row, kind=kind, condition=condition,
                natural_failure=natural_failure,
                source=None if own is None else own['source'],
                prior_own=own if condition == 'oracle' else None)
            seal_authored(sample, patch)
            samples[condition] = sample
    own = samples['own']
    case = own['contract']['case']
    # Only this temporary authored raw tree is removed to model retained evidence.
    shutil.rmtree(root / '.pending' / case['case_id'] / '.raw')
    return {'evidence_root': root,
        'registrations': {c: s['registration'] for c, s in samples.items()},
        'condition_commits': {c: s['condition_commit'] for c, s in samples.items()},
        'case_slot': {'case_id': case['case_id'], 'case_sha256': case['case_sha256'],
            'source_run_id': own['contract']['source_run_id'],
            'condition_run_ids': {c: s['contract']['run_id'] for c, s in samples.items()}}}


@pytest.fixture(scope='module')
def authored_case(tmp_path_factory):
    return build_case(tmp_path_factory.mktemp('retained-case-template') / 'evidence')


@pytest.fixture
def sample(authored_case, tmp_path, monkeypatch):
    value = copy.deepcopy(authored_case)
    value['evidence_root'] = tmp_path / 'evidence'
    shutil.copytree(authored_case['evidence_root'], value['evidence_root'])
    # Public qualification remains empty; this is an explicitly authored seam.
    monkeypatch.setattr(seal, '_require_qualification_pin', lambda value: None)
    return value


def request(sample):
    return {**sample, 'deadline': time.monotonic() + 90}


def case_path(sample):
    return sample['evidence_root'] / '.pending' / sample['case_slot']['case_id']


def contract(sample, condition='own'):
    path = sample['evidence_root'] / sample['registrations'][condition]['path']
    return artifacts._json(path.read_bytes())


def forbidden(*args, **kwargs):
    pytest.fail('Retained case reached raw/model or forbidden protected evidence')


def forbid_replay(monkeypatch):
    for name in ('_raw', '_qualified_replay', '_production_replay'):
        monkeypatch.setattr(seal, name, forbidden)
    monkeypatch.setattr(qualification, '_load_policy', forbidden)
    monkeypatch.setattr(seal.audit, 'validate_raw_receipt', forbidden)
    monkeypatch.setattr(seal.legacy, '_read_run', forbidden)


def test_import_is_pure():
    result = subprocess.run([sys.executable, '-B', '-c',
        f"import sys; import {NAME}; assert not set(sys.modules)&"
        "{'torch','mujoco','palimpsest.engine','palimpsest.model'}"],
        cwd=ROOT, env={**os.environ, 'PYTHONPATH': 'src:.'},
        text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_nine_natural_failures_are_derived_without_replay_and_account_short_tree(sample, monkeypatch):
    forbid_replay(monkeypatch)
    before = tree(sample['evidence_root'])
    handles = len(os.listdir('/proc/self/fd'))
    result = module().read_retained_staged_case(**request(sample))
    assert len(os.listdir('/proc/self/fd')) == handles
    assert tree(sample['evidence_root']) == before
    assert result['condition_order'] == CONDITIONS
    assert result['execution_order_verified'] is False
    assert result['raw_replay_performed'] is result['model_replay_performed'] is False
    assert result['replay_evidence'] == 'retained-attestation'
    assert result['claims'] == compact.PROTOCOL['claims']
    cells = result['retained_cells']
    assert [c['condition'] for c in cells] == CONDITIONS
    authored_rows = evidence(row=0)['post_rows']
    expected_path = sum(math.hypot(float(r['next_pose'][0]) - float(r['pose'][0]),
                                   float(r['next_pose'][1]) - float(r['pose'][1]))
                        for r in authored_rows)
    expected_keys = set('family_id case_id kind condition run_id goal continuation_ticks path_length outcome trace_digest invariant capped_ticks'.split())
    for cell in cells:
        assert set(cell) == expected_keys
        assert cell['run_id'] == sample['case_slot']['condition_run_ids'][cell['condition']]
        assert cell['case_id'] == sample['case_slot']['case_id']
        assert cell['goal'] is False and cell['capped_ticks'] == 900
        assert cell['outcome']['type'] == 'CueUnavailable'
        assert cell['continuation_ticks'] == len(authored_rows)
        assert cell['path_length'] == pytest.approx(expected_path, rel=0, abs=1e-12)
        manifest = artifacts._json((case_path(sample) / 'conditions' / cell['condition'] /
                                    'recording/manifest.json').read_bytes())
        assert cell['trace_digest'] == manifest['trace_digest']
    assert len({c['invariant'] for c in cells}) == 1
    own, sham = cells[0], next(c for c in cells if c['condition'] == 'sham')
    for key in ('trace_digest', 'goal', 'continuation_ticks', 'path_length', 'outcome'):
        assert own[key] == sham[key]
    root = case_path(sample)
    files = [p for p in root.rglob('*') if p.is_file()]
    directories = [root, *(p for p in root.rglob('*') if p.is_dir())]
    assert result['file_count'] == len(files)
    assert result['directory_count'] == len(directories) == 33
    assert result['total_bytes'] == sum(p.stat().st_size for p in files)
    assert len(files) + len(directories) < 454
    assert not any((root / name).exists() for name in ('manifest.json', 'close.json', 'commit.json', '.raw'))


def test_empty_trust_refuses_before_protected_reads(sample, monkeypatch):
    monkeypatch.setattr(seal, '_require_qualification_pin', qualification.require_qualification_pin)
    monkeypatch.setattr(seal, '_load_source', forbidden)
    monkeypatch.setattr(seal, '_Anchor', forbidden)
    monkeypatch.setattr(retained, 'read_retained_sealed_condition', forbidden)
    before = tree(sample['evidence_root'])
    with pytest.raises(PermissionError, match='qualification'):
        module().read_retained_staged_case(**request(sample))
    assert tree(sample['evidence_root']) == before


@pytest.mark.parametrize('defect', ['missing-registration', 'missing-commit', 'duplicate-run',
    'wrong-case', 'wrong-case-sha', 'wrong-source', 'wrong-run', 'wrong-snapshot', 'wrong-commit'])
def test_rejects_incomplete_or_cross_bound_case(sample, defect):
    if defect == 'missing-registration': sample['registrations'].pop('oracle')
    elif defect == 'missing-commit': sample['condition_commits'].pop('oracle')
    elif defect == 'duplicate-run':
        sample['case_slot']['condition_run_ids']['oracle'] = sample['case_slot']['condition_run_ids']['own']
    elif defect == 'wrong-case': sample['case_slot']['case_id'] = 'another-case'
    elif defect == 'wrong-case-sha': sample['case_slot']['case_sha256'] = 'f' * 64
    elif defect == 'wrong-source': sample['case_slot']['source_run_id'] = 'e' * 32
    elif defect == 'wrong-run': sample['case_slot']['condition_run_ids']['oracle'] = 'e' * 32
    elif defect == 'wrong-commit': sample['condition_commits']['own']['sha256'] = 'f' * 64
    else:
        path = case_path(sample) / 'source/snapshots/initial.snp'
        payload = bytearray(path.read_bytes()); payload[-1] ^= 1; path.write_bytes(payload)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module().read_retained_staged_case(**request(sample))


@pytest.mark.parametrize('defect', ['raw-empty', 'raw-residue', 'extra', 'final-alias'])
def test_rejects_unpublished_namespace_residue(sample, defect):
    root = case_path(sample)
    if defect.startswith('raw'):
        (root / '.raw').mkdir()
        if defect == 'raw-residue': (root / '.raw/residue').write_bytes(b'x')
    elif defect == 'extra': (root / 'extra.json').write_bytes(b'{}')
    else: (sample['evidence_root'] / 'cases' / root.name).mkdir(parents=True)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module().read_retained_staged_case(**request(sample))


@pytest.mark.parametrize('target', ['chunk', 'qualification', 'history'])
def test_last_reader_cannot_hide_mutation_of_earlier_inputs(sample, monkeypatch, target):
    original = retained.read_retained_sealed_condition
    seen = []
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        seen.append(kwargs['condition'])
        if len(seen) == 9:
            own = contract(sample)
            if target == 'chunk': path = next((case_path(sample) / 'conditions/own/recording/chunks').iterdir())
            else:
                descriptor = own['qualification'] if target == 'qualification' else own['history_bundles']['own']
                path = sample['evidence_root'] / descriptor['path']
            payload = bytearray(path.read_bytes()); payload[-1] ^= 1; path.write_bytes(payload)
        return result
    monkeypatch.setattr(retained, 'read_retained_sealed_condition', changed)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module().read_retained_staged_case(**request(sample))
    assert seen == CONDITIONS


def test_primary_body_error_survives_outer_custody_teardown(sample, monkeypatch):
    primary = LookupError('authored whole-case primary')
    original = retained.read_retained_sealed_condition
    seen = []
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        seen.append(kwargs['condition'])
        if len(seen) == 9:
            path = case_path(sample) / 'conditions/own/worker-report.json'
            path.write_bytes(path.read_bytes() + b'x')
            raise primary
        return result
    monkeypatch.setattr(retained, 'read_retained_sealed_condition', changed)
    handles = len(os.listdir('/proc/self/fd'))
    with pytest.raises(LookupError) as caught:
        module().read_retained_staged_case(**request(sample))
    assert caught.value is primary
    assert len(os.listdir('/proc/self/fd')) == handles
    assert any('teardown' in note.lower() for note in getattr(primary, '__notes__', ()))


def test_paused_conditions_cannot_be_scored(tmp_path, monkeypatch):
    sample = build_case(tmp_path / 'paused', natural_failure=False)
    monkeypatch.setattr(seal, '_require_qualification_pin', lambda value: None)
    with pytest.raises(ValueError, match='terminal|paused|outcome|failure'):
        module().read_retained_staged_case(**request(sample))


def test_registered_row_four_order_refuses_before_protected_reads(tmp_path, monkeypatch):
    sample = build_case(tmp_path / 'incompatible-order', row=4)
    monkeypatch.setattr(seal, '_require_qualification_pin', lambda value: None)
    monkeypatch.setattr(seal, '_load_source', forbidden)
    monkeypatch.setattr(seal, '_Anchor', forbidden)
    monkeypatch.setattr(retained, 'read_retained_sealed_condition', forbidden)
    before = tree(sample['evidence_root'])
    with pytest.raises(ValueError, match='order|oracle|own'):
        module().read_retained_staged_case(**request(sample))
    assert tree(sample['evidence_root']) == before


def projection_sample(reason, *, radius=0.25, distance=0.125):
    """Small decoded input for outcome arithmetic, not receipt admission."""
    authored = evidence(row=0)
    case = authored['case']
    x, y = case['goal_xy']
    rows = [{'pose': [x - 1, y, 0], 'next_pose': [x - 0.5, y, 0]},
            {'pose': [x - 0.5, y, 0], 'next_pose': [x - distance, y, 0]}]
    result = {'condition': 'own', 'run_id': 'a' * 32, 'read': {
        'rows': rows, 'trace_digest': 'b' * 64,
        'legacy_manifest_bytes': memory.canonical_bytes({'last_outcome': {'reason': reason}})}}
    snapshot = {'application': authored['source_application'],
        'identity': {'environment_profile': {'values': {'goal_radius': radius}}}}
    return result, case, snapshot


@pytest.mark.parametrize('reason,goal,score', [('goal', True, 2),
    ('stalled', False, 900), ('time_limit', False, 900)])
def test_retained_outcome_projection_uses_actual_rows_and_frozen_cap(reason, goal, score):
    values = projection_sample(reason)
    cell = module()._cell(*values)
    assert cell['goal'] is goal
    assert cell['continuation_ticks'] == 2 and cell['capped_ticks'] == score
    assert cell['path_length'] == 0.875
    assert cell['outcome'] == {'reason': reason}
    assert 'policy_binding_pass' not in cell


@pytest.mark.parametrize('defect', ['missing-geometry', 'at-radius', 'outside-radius',
    'nan-radius', 'boolean-radius', 'zero-radius', 'infrastructure'])
def test_retained_goal_geometry_and_infrastructure_are_not_accepted(defect):
    result, case, snapshot = projection_sample('goal',
        radius={'nan-radius': math.nan, 'boolean-radius': True, 'zero-radius': 0}.get(defect, 0.25),
        distance={'at-radius': 0.25, 'outside-radius': 0.5}.get(defect, 0.125))
    if defect == 'missing-geometry':
        snapshot.pop('identity')
    elif defect == 'infrastructure':
        result['read']['legacy_manifest_bytes'] = memory.canonical_bytes({
            'last_outcome': {'reason': 'runtime_failure', 'type': 'ImportError'}})
    with pytest.raises(ValueError, match='geometry|infrastructure'):
        module()._cell(result, case, snapshot)


def test_case_rejects_own_sham_outcome_disagreement(sample, monkeypatch):
    original = module()._cell
    def changed(result, case, snapshot):
        cell = original(result, case, snapshot)
        if cell['condition'] == 'sham':
            cell['trace_digest'] = 'f' * 64
        return cell
    monkeypatch.setattr(module(), '_cell', changed)
    with pytest.raises(ValueError, match='equality'):
        module().read_retained_staged_case(**request(sample))


def test_no_event_case_requires_all_nine_outcomes_equal(tmp_path, monkeypatch):
    sample = build_case(tmp_path / 'no-event', kind='no-event')
    monkeypatch.setattr(seal, '_require_qualification_pin', lambda value: None)
    result = module().read_retained_staged_case(**request(sample))
    assert {cell['kind'] for cell in result['retained_cells']} == {'no-event'}
    original = module()._cell
    def changed(result, case, snapshot):
        cell = original(result, case, snapshot)
        if cell['condition'] == 'swapped':
            cell['path_length'] += 1
        return cell
    monkeypatch.setattr(module(), '_cell', changed)
    with pytest.raises(ValueError, match='equality'):
        module().read_retained_staged_case(**request(sample))
