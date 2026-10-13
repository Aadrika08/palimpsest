"""Synthetic source-close contract; no owner, retained data or model is opened."""
import copy
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from palimpsest import artifacts, memory
from scripts import memory_family_compact_v4 as compact
from test_memory_family_raw_audit_v4 import _fixture as raw_fixture, _request

ROOT = Path(__file__).parents[1]


def producer():
    assert (ROOT / 'scripts/memory_family_producer_v4.py').is_file(), \
        'Source-only compact producer is missing'
    return importlib.import_module('scripts.memory_family_producer_v4')


def descriptor(path, payload):
    return {'path': str(path), 'size_bytes': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest()}


def inventory(root):
    return {str(path.relative_to(root)): path.read_bytes()
            for path in root.rglob('*') if path.is_file()}


def fixture(root):
    root.mkdir()
    sample = raw_fixture(root / 'fixture', include_source=True)
    case = sample['case']
    run_id = sample['source']['run_id']
    case_root = root / '.pending' / case['case_id']
    raw = case_root / '.raw' / run_id
    raw.parent.mkdir(parents=True)
    sample['source']['run_path'].rename(raw)
    source = case_root / 'source'
    (source / 'snapshots').mkdir(parents=True)
    snapshot = source / 'snapshots/initial.snp'
    (raw / 'snapshots/initial.snp').rename(snapshot)
    (raw / 'snapshots').rmdir()
    sample['source']['run_path'] = raw
    snapshot_descriptor = descriptor(
        f"cases/{case['case_id']}/source/snapshots/initial.snp",
        snapshot.read_bytes())
    sample['snapshot_descriptor'] = snapshot_descriptor
    request = _request(sample, 'source')
    # Receipts live outside the raw run and are published by a separate process.
    request.update(evidence_root=root, snapshot_reference=snapshot_descriptor)
    command = [
        sys.executable, str(ROOT / 'scripts/memory_family_raw_audit_v4.py'),
        '--run', str(raw), '--receipt-root', str(sample['receipts']),
        '--run-id', run_id, '--case-id', case['case_id'], '--operation', 'source',
        '--source-identity-sha256', request['source_identity_sha256'],
        '--evidence-root', str(root), '--source-snapshot',
        json.dumps(snapshot_descriptor), '--deadline-seconds', '30',
    ]
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    assert result.returncode == 0, result.stderr
    raw_receipt = artifacts._json(result.stdout.encode())
    owner_path = root / 'owner.json'
    owner_path.write_bytes(memory.canonical_bytes({
        'schema': 'memory-family-source-owner-v4', 'case_id': case['case_id'],
        'run_id': run_id, 'owner_source_sha256': request['source_identity_sha256'],
        'claims': copy.deepcopy(compact.PROTOCOL['claims']),
    }))
    control = root / 'control.json'
    control.write_bytes(memory.canonical_bytes({'closed': True}))
    registration = {
        'schema': 'memory-family-source-finalization-registration-v4',
        'protocol_sha256': compact.PROTOCOL_SHA256, 'case': case, 'run_id': run_id,
        'owner_source_sha256': request['source_identity_sha256'],
        'snapshot': snapshot_descriptor,
        'raw_audit': descriptor(Path(raw_receipt['path']).relative_to(root),
                                Path(raw_receipt['path']).read_bytes()),
        'owner_record': descriptor('owner.json', owner_path.read_bytes()),
        'controls': [descriptor('control.json', control.read_bytes())],
        'claims': copy.deepcopy(compact.PROTOCOL['claims']),
    }
    registration_path = root / 'registration.json'
    registration_path.write_bytes(memory.canonical_bytes(registration))
    return {'root': root, 'raw': raw, 'source': source, 'snapshot': snapshot,
            'registration': descriptor('registration.json', registration_path.read_bytes()),
            'contract': registration, 'sample': sample}


def request(sample):
    return dict(evidence_root=sample['root'], registration=sample['registration'],
                deadline=time.monotonic() + 30)


def test_source_finalizer_exists_and_import_is_pure():
    module = producer()
    result = subprocess.run([
        sys.executable, '-c',
        "import sys; import scripts.memory_family_producer_v4; "
        "assert not set(sys.modules)&{'torch','mujoco','palimpsest.engine','palimpsest.model'}",
    ], cwd=ROOT, env={**os.environ, 'PYTHONPATH': 'src:.'},
        text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert callable(module.seal_compact_source)


def test_seals_exact_source_without_copying_snapshot_or_deleting_raw(tmp_path):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    raw_before = inventory(sample['raw'])
    snapshot_before = sample['snapshot'].stat()
    result = module.seal_compact_source(**request(sample))
    assert inventory(sample['raw']) == raw_before
    assert sample['snapshot'].stat().st_ino == snapshot_before.st_ino
    assert sample['snapshot'].stat().st_nlink == 1
    assert result['claims'] == compact.PROTOCOL['claims']
    sealed = module.read_sealed_source(**request(sample))
    assert sealed['read']['legacy_events_bytes'] == raw_before['recording/events.jsonl']
    assert sealed['read']['legacy_manifest_bytes'] == raw_before['recording/manifest.json']
    assert (sample['source'] / 'worker-report.json').read_bytes() == raw_before['worker-report.json']
    assert (sample['source'] / 'owner.json').read_bytes() == (sample['root'] / 'owner.json').read_bytes()
    before = inventory(sample['root'])
    with pytest.raises((FileExistsError, ValueError)):
        module.seal_compact_source(**request(sample))
    assert inventory(sample['root']) == before
    with pytest.raises(PermissionError, match='pruning'):
        module.prune_raw_source(**request(sample))
    assert inventory(sample['root']) == before


@pytest.mark.parametrize('defect', ['receipt-missing', 'snapshot-mutation',
                                   'snapshot-hardlink', 'snapshot-symlink', 'raw-extra'])
def test_refuses_invalid_input_without_output_mutation(tmp_path, defect):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    if defect == 'receipt-missing':
        (sample['root'] / sample['contract']['raw_audit']['path']).unlink()
    elif defect == 'snapshot-mutation':
        sample['snapshot'].write_bytes(b'wrong')
    elif defect == 'snapshot-hardlink':
        os.link(sample['snapshot'], sample['root'] / 'alias.snp')
    elif defect == 'snapshot-symlink':
        target = sample['root'] / 'target.snp'
        sample['snapshot'].rename(target)
        sample['snapshot'].symlink_to(target)
    else:
        (sample['raw'] / 'unregistered.tmp').write_bytes(b'bad')
    before = inventory(sample['root'])
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.seal_compact_source(**request(sample))
    assert inventory(sample['root']) == before


def test_unsealed_source_and_postwrite_failure_are_not_readable(tmp_path, monkeypatch):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    with pytest.raises((ValueError, OSError)):
        module.read_sealed_source(**request(sample))
    original = module._write_file
    calls = []
    def fail_after_one(*args, **kwargs):
        original(*args, **kwargs)
        calls.append(1)
        if len(calls) == 1:
            raise OSError('synthetic write failure')
    monkeypatch.setattr(module, '_write_file', fail_after_one)
    with pytest.raises(OSError, match='synthetic'):
        module.seal_compact_source(**request(sample))
    assert (sample['source'].parent / 'quarantine.json').is_file()
    assert not (sample['source'] / 'commit.json').exists()
    before = inventory(sample['root'])
    with pytest.raises((ValueError, FileExistsError)):
        module.seal_compact_source(**request(sample))
    assert inventory(sample['root']) == before
