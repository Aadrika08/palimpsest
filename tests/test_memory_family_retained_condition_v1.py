"""Authored retained evidence only; no model qualification or real raw pruning."""
import copy
import os
import shutil
import subprocess
import sys

import pytest

from palimpsest import artifacts, memory
from scripts import memory_condition_replay_admission_v1 as qualification
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_condition_seal_v4 as seal
from scripts import memory_family_retained_condition_v1 as retained
from test_memory_condition_replay_admission_v1 import receipt
from test_memory_family_condition_close_v4 import (
    authored_replay, descriptor, fixture, rebind, request, tree, write,
)


def seal_authored(sample, monkeypatch):
    sample['contract']['qualification'] = write(sample['root'],
        sample['contract']['qualification']['path'], receipt())
    rebind(sample)
    authored_replay(monkeypatch, sample)
    seal.seal_compact_condition(**request(sample))
    sample['condition_commit'] = descriptor(
        sample['contract']['owner_record']['path'].replace('owner.json', 'commit.json'),
        (sample['path'] / 'commit.json').read_bytes())


def sealed(root, monkeypatch, *, natural_failure=False, condition='own'):
    extra = {}
    if condition == 'oracle':
        own = fixture(root)
        seal_authored(own, monkeypatch)
        extra = {'source': own['source'], 'prior_own': own}
    sample = fixture(root, natural_failure=natural_failure, condition=condition, **extra)
    seal_authored(sample, monkeypatch)
    # Remove only these temporary authored recordings to construct a retained fixture.
    shutil.rmtree(sample['path'].parents[1] / '.raw')
    return sample


def retained_request(sample):
    return {**request(sample), 'condition_commit': sample['condition_commit']}


@pytest.mark.parametrize('natural_failure', [False, True])
def test_retained_reader_uses_receipts_without_raw_or_model(tmp_path, monkeypatch, natural_failure):
    sample = sealed(tmp_path / 'evidence', monkeypatch, natural_failure=natural_failure)
    before = tree(sample['root'])
    def forbidden(*args, **kwargs):
        pytest.fail('Retained reading attempted raw or model execution')
    monkeypatch.setattr(seal, '_raw', forbidden)
    monkeypatch.setattr(seal, '_qualified_replay', forbidden)
    monkeypatch.setattr(seal, '_production_replay', forbidden)
    monkeypatch.setattr(qualification, '_load_policy', forbidden)
    monkeypatch.setattr(seal.audit, 'validate_raw_receipt', forbidden)
    monkeypatch.setattr(seal.legacy, '_read_run', forbidden)
    result = retained.read_retained_sealed_condition(**retained_request(sample))
    assert result['run_id'] == sample['contract']['run_id']
    assert result['raw_replay_performed'] is False
    assert result['model_replay_performed'] is False
    assert result['replay_evidence'] == 'retained-attestation'
    assert result['claims'] == compact.PROTOCOL['claims']
    assert result['read']['trace_digest'] == result['conversion']['compact_trace_digest']
    assert tree(sample['root']) == before


@pytest.mark.parametrize('condition', compact.PROTOCOL['analysis_contract']['conditions'][1:])
def test_other_conditions_and_oracle_read_retained_without_raw(tmp_path, monkeypatch, condition):
    sample = sealed(tmp_path / 'evidence', monkeypatch, condition=condition)
    def forbidden(*args, **kwargs):
        pytest.fail('Retained condition attempted raw or model execution')
    monkeypatch.setattr(seal, '_raw', forbidden)
    monkeypatch.setattr(seal, '_qualified_replay', forbidden)
    monkeypatch.setattr(seal, '_production_replay', forbidden)
    before = tree(sample['root'])
    result = retained.read_retained_sealed_condition(**retained_request(sample))
    assert result['condition'] == condition
    assert result['model_replay_performed'] is False
    assert tree(sample['root']) == before


@pytest.mark.parametrize('defect', ['missing', 'cross-case'])
def test_oracle_rejects_missing_or_cross_case_prior_own(tmp_path, monkeypatch, defect):
    sample = sealed(tmp_path / 'evidence', monkeypatch, condition='oracle')
    prior = sample['contract']['prior_own_receipt']
    case_id = sample['contract']['case']['case_id']
    path = sample['root'] / '.pending' / case_id / 'conditions/own/pair-admission.json'
    if defect == 'missing':
        path.unlink()
    else:
        value = artifacts._json(path.read_bytes())
        value['case_id'] = 'different-case'
        path.write_bytes(memory.canonical_bytes(value))
        # Rebinding registration alone cannot turn another case into an oracle donor.
        sample['contract']['prior_own_receipt'] = descriptor(prior['path'], path.read_bytes())
        rebind(sample)
    with pytest.raises((ValueError, OSError, RuntimeError)):
        retained.read_retained_sealed_condition(**retained_request(sample))


def test_unqualified_reader_refuses_before_protected_access(tmp_path, monkeypatch):
    sample = sealed(tmp_path / 'evidence', monkeypatch)
    monkeypatch.setattr(seal, '_require_qualification_pin', qualification.require_qualification_pin)
    def forbidden(*args, **kwargs):
        pytest.fail('Unqualified retained reader reached protected evidence')
    monkeypatch.setattr(seal, '_load_source', forbidden)
    monkeypatch.setattr(seal, '_Anchor', forbidden)
    monkeypatch.setattr(seal, '_raw', forbidden)
    before = tree(sample['root'])
    with pytest.raises(PermissionError, match='qualification'):
        retained.read_retained_sealed_condition(**retained_request(sample))
    assert tree(sample['root']) == before


def test_import_does_not_load_model_or_simulator():
    result = subprocess.run([sys.executable, '-B', '-c',
        'import sys; import scripts.memory_family_retained_condition_v1; '
        "assert not set(sys.modules) & {'torch','mujoco','palimpsest.engine','palimpsest.model'}"],
        cwd=compact.ROOT, env={**os.environ, 'PYTHONPATH': 'src:.'},
        text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('defect', [
    'commit-hash', 'commit-path', 'missing-commit', 'temporary-marker',
    'raw-residue', 'extra-case', 'extra-condition', 'local-snapshot', 'quarantine',
    'final-alias', 'worker', 'raw-copy', 'raw-receipt', 'compact', 'source-snapshot',
    'qualification', 'history', 'conversion', 'pair', 'commit-hardlink',
    'chunk-symlink', 'replay-trace', 'replay-count', 'replay-hidden',
    'marker-qualification', 'marker-source', 'marker-claims',
])
def test_rejects_changed_or_unaccounted_retained_evidence(tmp_path, monkeypatch, defect):
    sample = sealed(tmp_path / 'evidence', monkeypatch)
    root, path = sample['root'], sample['path']
    case_path = path.parents[1]
    kwargs = retained_request(sample)
    if defect == 'commit-hash':
        kwargs['condition_commit']['sha256'] = '0' * 64
    elif defect == 'commit-path':
        kwargs['condition_commit']['path'] = kwargs['condition_commit']['path'].replace('/own/', '/oracle/')
    elif defect == 'missing-commit':
        (path / 'commit.json').unlink()
    elif defect == 'temporary-marker':
        (path / '.commit.tmp').write_bytes(b'x')
    elif defect == 'raw-residue':
        (case_path / '.raw' / sample['contract']['run_id']).mkdir(parents=True)
    elif defect in ('extra-case', 'quarantine'):
        (case_path / ('unexpected' if defect == 'extra-case' else 'quarantine.json')).write_bytes(b'x')
    elif defect in ('extra-condition', 'local-snapshot'):
        (path / ('unexpected' if defect == 'extra-condition' else 'initial.snp')).write_bytes(b'x')
    elif defect == 'final-alias':
        (root / 'cases' / sample['contract']['case']['case_id']).mkdir(parents=True)
    elif defect == 'commit-hardlink':
        os.link(path / 'commit.json', root / 'alias')
    elif defect == 'chunk-symlink':
        chunk = path / 'recording/chunks/000000.npz'
        chunk.rename(root / 'chunk.npz')
        chunk.symlink_to(root / 'chunk.npz')
    elif defect in ('worker', 'raw-copy', 'raw-receipt', 'compact',
                    'source-snapshot', 'qualification', 'history'):
        target = {
            'worker': path / 'worker-report.json',
            'raw-copy': path / 'recording/raw-audit.json',
            'raw-receipt': root / sample['contract']['raw_audit']['path'],
            'compact': path / 'recording/chunks/000000.npz',
            'source-snapshot': sample['source']['snapshot'],
            'qualification': root / sample['contract']['qualification']['path'],
            'history': root / sample['contract']['history_bundles']['own']['path'],
        }[defect]
        target.write_bytes(target.read_bytes() + b'x')
    elif defect in ('conversion', 'pair'):
        target = path / ('recording/conversion.json' if defect == 'conversion' else 'pair-admission.json')
        value = artifacts._json(target.read_bytes())
        if defect == 'conversion':
            value['inventory'][0]['sha256'] = '0' * 64
        else:
            value['oracle_result']['proof_sha256'] = '0' * 64
        target.write_bytes(memory.canonical_bytes(value))
    else:
        target = path / 'commit.json'
        value = artifacts._json(target.read_bytes())
        if defect == 'replay-trace':
            value['cell_replay']['trace_digest'] = '0' * 64
        elif defect == 'replay-count':
            value['cell_replay']['rows_checked'] = True
        elif defect == 'replay-hidden':
            value['cell_replay']['final_hidden_sha256'] = 'forged'
        elif defect == 'marker-qualification':
            value['qualification']['sha256'] = '0' * 64
        elif defect == 'marker-source':
            value['source_run_id'] = 'f' * 32
        else:
            value['claims']['cell_replay_verified'] = True
        target.write_bytes(memory.canonical_bytes(value))
        # Even an independently rebound expected marker cannot admit inconsistent evidence.
        kwargs['condition_commit'] = descriptor(kwargs['condition_commit']['path'], target.read_bytes())
    before = tree(root)
    with pytest.raises((ValueError, OSError, RuntimeError)):
        retained.read_retained_sealed_condition(**kwargs)
    assert tree(root) == before


def test_empty_raw_parent_is_allowed_without_removal(tmp_path, monkeypatch):
    sample = sealed(tmp_path / 'evidence', monkeypatch)
    (sample['path'].parents[1] / '.raw').mkdir()
    before = tree(sample['root'])
    assert retained.read_retained_sealed_condition(**retained_request(sample))['raw_replay_performed'] is False
    assert (sample['path'].parents[1] / '.raw').is_dir()
    assert tree(sample['root']) == before


@pytest.mark.parametrize('target', ['qualification', 'snapshot', 'chunk', 'condition-directory', 'case-entry'])
def test_custody_detects_mutation_after_pair_validation(tmp_path, monkeypatch, target):
    sample = sealed(tmp_path / 'evidence', monkeypatch)
    original = retained.pair.admit_staged_compact_pair
    def changed(**values):
        result = original(**values)
        if target == 'condition-directory':
            sample['path'].rename(sample['path'].with_name('replaced'))
            sample['path'].mkdir()
        elif target == 'case-entry':
            (sample['path'].parents[1] / 'unexpected').mkdir()
        else:
            path = {'qualification': sample['root'] / 'qualification.json',
                    'snapshot': sample['source']['snapshot'],
                    'chunk': sample['path'] / 'recording/chunks/000000.npz'}[target]
            path.write_bytes(path.read_bytes() + b'x')
        return result
    monkeypatch.setattr(retained.pair, 'admit_staged_compact_pair', changed)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        retained.read_retained_sealed_condition(**retained_request(sample))


def test_primary_error_survives_failed_custody_teardown(tmp_path, monkeypatch):
    sample = sealed(tmp_path / 'evidence', monkeypatch)
    primary = RuntimeError('authored primary failure')
    def changed(**values):
        path = sample['path'] / 'worker-report.json'
        path.write_bytes(path.read_bytes() + b'x')
        raise primary
    monkeypatch.setattr(retained.pair, 'admit_staged_compact_pair', changed)
    with pytest.raises(RuntimeError) as caught:
        retained.read_retained_sealed_condition(**retained_request(sample))
    assert caught.value is primary
    assert any('teardown also failed' in note for note in primary.__notes__)


def test_caller_mutation_cannot_rebind_expected_commit(tmp_path, monkeypatch):
    sample = sealed(tmp_path / 'evidence', monkeypatch)
    expected = copy.deepcopy(sample['condition_commit'])
    original = seal._registration
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        sample['condition_commit']['sha256'] = '0' * 64
        return result
    monkeypatch.setattr(seal, '_registration', changed)
    result = retained.read_retained_sealed_condition(**retained_request(sample))
    assert descriptor(expected['path'], memory.canonical_bytes(result['marker'])) == expected


@pytest.mark.parametrize('deadline', [None, True, float('nan'), float('inf'), -1])
def test_invalid_deadline_refuses_before_input_access(monkeypatch, deadline):
    def forbidden(*args, **kwargs):
        pytest.fail('Invalid deadline reached input access')
    monkeypatch.setattr(seal, '_bind', forbidden)
    with pytest.raises((ValueError, TimeoutError)):
        retained.read_retained_sealed_condition('/absent', {}, case_id='unused',
            condition='own', condition_commit={}, deadline=deadline)
