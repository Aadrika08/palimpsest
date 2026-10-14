"""Retained-only validation on temporary synthetic evidence; no real deletion."""
import os
import shutil
import time

import pytest

from scripts import memory_family_producer_v4 as producer
from scripts import memory_family_compact_v4 as compact
from test_memory_family_producer_v4 import fixture, request, descriptor, inventory


def sealed(tmp_path, *, remove_raw=True):
    sample = fixture(tmp_path / 'evidence')
    producer.seal_compact_source(**request(sample))
    if remove_raw:
        # Only the fake raw tree generated inside this test's tmp_path.
        shutil.rmtree(sample['raw'])
    return sample


def retained_request(sample, **extra):
    marker = sample['source'] / 'commit.json'
    return {**request(sample), 'source_commit': descriptor(
        f"cases/{sample['contract']['case']['case_id']}/source/commit.json",
        marker.read_bytes()), **extra}


def reader():
    result = getattr(producer, 'read_retained_sealed_source', None)
    assert callable(result), 'Retained-only sealed source reader is missing'
    return result


def test_retained_reader_checks_source_after_fake_raw_removal(tmp_path, monkeypatch):
    call = reader()
    sample = sealed(tmp_path)
    before = inventory(sample['root'])
    def forbidden(*args, **kwargs):
        pytest.fail('Retained reader attempted raw replay')
    monkeypatch.setattr(producer.audit, 'validate_raw_receipt', forbidden)
    monkeypatch.setattr(producer.legacy, '_read_run', forbidden)
    monkeypatch.setattr(producer, '_prove', forbidden)
    monkeypatch.setattr(producer, '_bind_raw_inventory', forbidden)
    result = call(**retained_request(sample))
    assert result['marker']['run_id'] == sample['contract']['run_id']
    assert result['raw_replay_performed'] is False
    assert result['claims'] == compact.PROTOCOL['claims']
    assert result['read']['trace_digest'] == result['conversion']['compact_trace_digest']
    assert inventory(sample['root']) == before
    with pytest.raises((ValueError, FileNotFoundError)):
        producer.read_sealed_source(**request(sample))
    with pytest.raises(PermissionError):
        producer.prune_raw_source(**request(sample))


@pytest.mark.parametrize('parent', ['absent', 'empty', 'condition'])
def test_exact_raw_parent_options(tmp_path, parent):
    call = reader()
    sample = sealed(tmp_path)
    raw_parent = sample['raw'].parent
    extra = {}
    if parent == 'absent':
        raw_parent.rmdir()
    elif parent == 'condition':
        (raw_parent / 'condition-owner').mkdir()
        extra['condition_run_id'] = 'condition-owner'
    assert call(**retained_request(sample, **extra))['raw_replay_performed'] is False


@pytest.mark.parametrize('defect', ['source-raw', 'unknown-raw', 'wrong-raw',
    'source-id', 'raw-symlink', 'unknown-case', 'condition-file', 'unknown-condition',
    'quarantine', 'temp-marker', 'snapshot-hardlink', 'snapshot-symlink',
    'worker', 'compact', 'raw-copy', 'owner', 'source-commit', 'deadline'])
def test_retained_reader_rejects_unaccounted_or_changed_evidence(tmp_path, defect):
    call = reader()
    sample = sealed(tmp_path, remove_raw=defect != 'source-raw')
    kwargs = retained_request(sample)
    case = sample['source'].parent
    if defect == 'unknown-raw':
        (sample['raw'].parent / 'unknown-owner').mkdir()
    elif defect == 'wrong-raw':
        (sample['raw'].parent / 'unknown-owner').mkdir()
        kwargs['condition_run_id'] = 'condition-owner'
    elif defect == 'source-id':
        kwargs['condition_run_id'] = sample['contract']['run_id']
    elif defect == 'raw-symlink':
        (sample['raw'].parent / 'condition-owner').symlink_to(sample['source'], target_is_directory=True)
        kwargs['condition_run_id'] = 'condition-owner'
    elif defect in ('unknown-case', 'quarantine'):
        (case / ('quarantine.json' if defect == 'quarantine' else 'unknown')).write_bytes(b'x')
    elif defect in ('condition-file', 'unknown-condition'):
        conditions = case / 'conditions'
        conditions.mkdir()
        if defect == 'condition-file':
            (conditions / compact.PROTOCOL['analysis_contract']['conditions'][0]).write_bytes(b'x')
        else:
            (conditions / 'unknown-condition').mkdir()
    elif defect == 'temp-marker':
        (sample['source'] / '.commit.tmp').write_bytes(b'x')
    elif defect == 'snapshot-hardlink':
        os.link(sample['snapshot'], sample['root'] / 'snapshot-alias')
    elif defect == 'snapshot-symlink':
        snapshot_bytes = sample['snapshot'].read_bytes()
        sample['snapshot'].unlink()
        target = sample['root'] / 'target.snp'
        target.write_bytes(snapshot_bytes)
        sample['snapshot'].symlink_to(target)
    elif defect in ('worker', 'compact', 'raw-copy', 'owner'):
        path = {'worker': 'worker-report.json', 'owner': 'owner.json',
                'compact': 'recording/chunks/000000.npz',
                'raw-copy': 'recording/raw-audit.json'}[defect]
        target = sample['source'] / path
        target.write_bytes(target.read_bytes() + b'x')
    elif defect == 'source-commit':
        kwargs['source_commit']['sha256'] = '0' * 64
    elif defect == 'deadline':
        kwargs['deadline'] = time.monotonic() - 1
    with pytest.raises((ValueError, OSError, RuntimeError, TimeoutError)):
        call(**kwargs)


def test_retained_reader_holds_namespace_until_return(tmp_path, monkeypatch):
    call = reader()
    sample = sealed(tmp_path)
    original = producer._bounds
    def changed(*args, **kwargs):
        original(*args, **kwargs)
        (sample['source'].parent / 'unexpected').mkdir()
    monkeypatch.setattr(producer, '_bounds', changed)
    with pytest.raises((RuntimeError, ValueError)):
        call(**retained_request(sample))


def test_known_condition_namespace_is_only_inspected_as_names(tmp_path):
    call = reader()
    sample = sealed(tmp_path)
    conditions = sample['source'].parent / 'conditions'
    conditions.mkdir()
    (conditions / compact.PROTOCOL['analysis_contract']['conditions'][0]).mkdir()
    assert call(**retained_request(sample))['raw_replay_performed'] is False
