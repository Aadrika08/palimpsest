"""Staged read-only pair admission; synthetic temporary evidence only."""
import copy
import hashlib

import pytest

from palimpsest import artifacts, memory
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_oracle_admission_v4 as pair
from test_memory_family_oracle_admission_v4 import (
    CONDITIONS, _fixture, _request, _tree_hashes, _write,
)


def stage(sample):
    root, case_id = sample['root'], sample['case']['case_id']
    base = f'cases/{case_id}'
    for operation, relative in (
        ('source', f'{base}/source/recording/conversion.json'),
        ('condition', f"{base}/conditions/{sample['condition']}/recording/conversion.json"),
    ):
        descriptor = sample[f'{operation}_conversion_descriptor']
        sample[f'{operation}_conversion_descriptor'] = _write(
            root, relative, (root / descriptor['path']).read_bytes())
        (root / descriptor['path']).unlink()
    if sample['prior_own_receipt'] is not None:
        descriptor = sample['prior_own_receipt']
        prior = artifacts._json((root / descriptor['path']).read_bytes())
        prior['source_receipt']['conversion'] = sample['source_conversion_descriptor']
        sample['prior_own_receipt'] = _write(root, descriptor['path'], prior)
    marker = {
        'schema': 'memory-family-compact-source-commit-v1',
        'protocol_sha256': compact.PROTOCOL_SHA256,
        'case_id': case_id, 'run_id': sample['source_run_id'],
        'conversion': sample['source_conversion_descriptor'],
        'claims': copy.deepcopy(compact.PROTOCOL['claims']),
    }
    sample['source_commit'] = _write(root, f'{base}/source/commit.json', marker)
    pending = root / '.pending'
    pending.mkdir()
    (root / base).rename(pending / case_id)
    sample['snapshot_path'] = pending / case_id / 'source/snapshots/initial.snp'
    return sample


def admit(sample):
    assert hasattr(pair, 'admit_staged_compact_pair'), 'Staged compact pair entry point missing'
    return pair.admit_staged_compact_pair(
        **_request(sample), source_commit=sample['source_commit'])


@pytest.mark.parametrize('condition', CONDITIONS)
def test_staged_pairs_preserve_portable_receipts_and_never_mutate_inputs(tmp_path, condition):
    prior = donor = None
    if condition == 'oracle':
        donor = _fixture(tmp_path / 'donor')
        prior = pair.admit_compact_pair(**_request(donor))
    sample = stage(_fixture(tmp_path / condition, condition,
                            prior_own_result=prior, source_fixture=donor))
    before = _tree_hashes(sample['root'])
    result = admit(sample)
    assert result['condition'] == condition
    assert result['snapshot_reference']['path'].startswith(f"cases/{sample['case']['case_id']}/")
    assert result['source_receipt']['conversion'] == sample['source_conversion_descriptor']
    assert result['claims'] == compact.PROTOCOL['claims']
    assert _tree_hashes(sample['root']) == before
    assert not (sample['root'] / '.pending/cases').exists()
    with pytest.raises((ValueError, OSError)):
        pair.admit_compact_pair(**_request(sample))


def test_staged_admission_accepts_audited_natural_failure(tmp_path):
    sample = stage(_fixture(tmp_path / 'failed', natural_failure=True))
    result = admit(sample)
    assert result['oracle_result']['status'] == 'compact-pair-pass'
    assert artifacts._json(sample['condition_bundle']['legacy-manifest.json'])['status'] == 'failed'


@pytest.mark.parametrize('defect', ['missing', 'wrong-run', 'wrong-case', 'wrong-conversion',
                                   'numeric-alias', 'quarantine', 'temporary', 'final-alias'])
def test_staged_admission_rejects_missing_or_mixed_source_commit(tmp_path, defect):
    sample = stage(_fixture(tmp_path / defect))
    root = sample['root']
    case = root / '.pending' / sample['case']['case_id']
    marker = case / 'source/commit.json'
    if defect == 'missing':
        marker.unlink()
    elif defect in ('quarantine', 'temporary'):
        (case / ('quarantine.json' if defect == 'quarantine' else 'source/.commit.tmp')).write_bytes(b'failure')
    elif defect == 'final-alias':
        final = root / 'cases' / sample['case']['case_id']
        final.parent.mkdir(exist_ok=True)
        final.symlink_to(case, target_is_directory=True)
    else:
        value = artifacts._json(marker.read_bytes())
        if defect == 'wrong-run':
            value['run_id'] = 'f' * 32
        elif defect == 'wrong-case':
            value['case_id'] = 'another-case'
        elif defect == 'wrong-conversion':
            value['conversion']['sha256'] = 'f' * 64
        else:
            value['conversion']['size_bytes'] = float(value['conversion']['size_bytes'])
        marker.write_bytes(memory.canonical_bytes(value))
        sample['source_commit'] = {
            **sample['source_commit'], 'size_bytes': len(marker.read_bytes()),
            'sha256': hashlib.sha256(marker.read_bytes()).hexdigest(),
        }
    before = _tree_hashes(root)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        admit(sample)
    assert _tree_hashes(root) == before


def test_marker_and_ancestor_remain_bound_through_full_pair_proof(tmp_path, monkeypatch):
    sample = stage(_fixture(tmp_path / 'drift'))
    original = pair._condition_identity
    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        marker = sample['root'] / '.pending' / sample['case']['case_id'] / 'source/commit.json'
        marker.write_bytes(marker.read_bytes() + b' ')
        return result
    monkeypatch.setattr(pair, '_condition_identity', mutate)
    with pytest.raises((ValueError, RuntimeError)):
        admit(sample)
