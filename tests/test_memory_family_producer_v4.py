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


def fixture(root, *, row=4, kind='change'):
    root.mkdir()
    sample = raw_fixture(root / 'fixture', include_source=True, row=row, kind=kind)
    case = sample['case']
    run_id = sample['source']['run_id']
    case_root = root / '.pending' / case['case_id']
    raw = case_root / '.raw' / run_id
    raw.parent.mkdir(parents=True)
    sample['source']['run_path'].rename(raw)
    source = case_root / 'source'
    (source / 'snapshots').mkdir(parents=True)
    snapshot = source / 'snapshots/initial.snp'
    sample['snapshot_path'].rename(snapshot)
    sample['source']['run_path'] = raw
    snapshot_descriptor = descriptor(
        f"cases/{case['case_id']}/source/snapshots/initial.snp",
        snapshot.read_bytes())
    sample['snapshot_descriptor'] = snapshot_descriptor
    sample['snapshot_path'] = snapshot
    sample['evidence_root'] = root
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
    owner_path = source / 'owner.json'
    owner_path.write_bytes(memory.canonical_bytes({
        'schema': 'memory-family-source-owner-v4', 'case_id': case['case_id'],
        'run_id': run_id, 'owner_source_sha256': request['source_identity_sha256'],
        'claims': copy.deepcopy(compact.PROTOCOL['claims']),
    }))
    controls = {}
    for role in ('job', 'supervisor', 'stdout', 'stderr', 'cleanup'):
        control = root / f'{role}.json'
        control.write_bytes(b'' if role in ('stdout', 'stderr') else memory.canonical_bytes({'closed': True}))
        controls[role] = descriptor(control.name, control.read_bytes())
    controls['audit'] = descriptor(Path(raw_receipt['path']).relative_to(root), Path(raw_receipt['path']).read_bytes())
    registration = {
        'schema': 'memory-family-source-finalization-registration-v4',
        'protocol_sha256': compact.PROTOCOL_SHA256, 'case': case, 'run_id': run_id,
        'owner_source_sha256': request['source_identity_sha256'],
        'snapshot': snapshot_descriptor,
        'raw_audit': descriptor(Path(raw_receipt['path']).relative_to(root),
                                Path(raw_receipt['path']).read_bytes()),
        'owner_record': descriptor(f"cases/{case['case_id']}/source/owner.json", owner_path.read_bytes()),
        'controls': controls,
    }
    registration['claims'] = copy.deepcopy(compact.PROTOCOL['claims'])
    registration_path = root / 'terminal-export.json'
    registration_path.write_bytes(memory.canonical_bytes(registration))
    return {'root': root, 'raw': raw, 'source': source, 'snapshot': snapshot,
            'registration': descriptor('terminal-export.json', registration_path.read_bytes()),
            'contract': registration, 'sample': sample}


def request(sample):
    return dict(evidence_root=sample['root'], registration=sample['registration'],
                case_id=sample['sample']['case']['case_id'], deadline=time.monotonic() + 30)


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
    owner_before = (sample['source'] / 'owner.json').read_bytes()
    result = module.seal_compact_source(**request(sample))
    assert inventory(sample['raw']) == raw_before
    assert sample['snapshot'].stat().st_ino == snapshot_before.st_ino
    assert sample['snapshot'].stat().st_nlink == 1
    assert result['claims'] == compact.PROTOCOL['claims']
    sealed = module.read_sealed_source(**request(sample))
    assert sealed['read']['legacy_events_bytes'] == raw_before['recording/events.jsonl']
    assert sealed['read']['legacy_manifest_bytes'] == raw_before['recording/manifest.json']
    assert (sample['source'] / 'worker-report.json').read_bytes() == raw_before['worker-report.json']
    assert (sample['source'] / 'owner.json').read_bytes() == owner_before
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


@pytest.mark.parametrize('field', ['reward', 'encoded_input', 'control', 'raw_output', 'pose'])
def test_rebound_numeric_candidate_still_requires_raw_equality(tmp_path, monkeypatch, field):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    original = compact.convert_synthetic
    from test_memory_family_compact_v4 import _mutate_chunk
    def changed(**kwargs):
        bundle = original(**kwargs)
        def mutate(arrays):
            arrays[field].flat[0] += 0.125
        return _mutate_chunk(bundle, 0, mutate)
    monkeypatch.setattr(compact, 'convert_synthetic', changed)
    before = inventory(sample['root'])
    with pytest.raises(ValueError, match='Raw-to-compact'):
        module.seal_compact_source(**request(sample))
    assert inventory(sample['root']) == before


def test_rebound_legacy_whitespace_is_not_raw_byte_equality(tmp_path, monkeypatch):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    original = compact.convert_synthetic
    def changed(**kwargs):
        bundle = original(**kwargs)
        bundle['legacy-events.jsonl'] = bundle['legacy-events.jsonl'].replace(b'\n', b' \n')
        manifest = artifacts._json(bundle['manifest.json'])
        manifest['legacy_events'] = descriptor('legacy-events.jsonl', bundle['legacy-events.jsonl'])
        # Keep the snapshot prefix byte-identical; tamper only after that prefix.
        original_events = kwargs['legacy_events_bytes']
        prefix_size = kwargs['snapshot_event_prefix']['size_bytes']
        bundle['legacy-events.jsonl'] = original_events[:prefix_size] + original_events[prefix_size:].replace(b'\n', b' \n')
        manifest['legacy_events'] = descriptor('legacy-events.jsonl', bundle['legacy-events.jsonl'])
        bundle['manifest.json'] = memory.canonical_bytes(manifest)
        return bundle
    monkeypatch.setattr(compact, 'convert_synthetic', changed)
    before = inventory(sample['root'])
    with pytest.raises(ValueError, match='Raw-to-compact'):
        module.seal_compact_source(**request(sample))
    assert inventory(sample['root']) == before


@pytest.mark.parametrize('target', ['raw', 'worker', 'snapshot', 'receipt', 'owner', 'control'])
def test_mutation_at_receipt_boundary_quarantines_and_keeps_raw(tmp_path, monkeypatch, target):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    original = module._write_file
    def mutate(directory, name, payload):
        original(directory, name, payload)
        if name == 'conversion.json':
            path = {
                'raw': sample['raw'] / 'recording/events.jsonl',
                'worker': sample['source'] / 'worker-report.json',
                'snapshot': sample['snapshot'],
                'receipt': sample['root'] / sample['contract']['raw_audit']['path'],
                'owner': sample['source'] / 'owner.json',
                'control': sample['root'] / sample['contract']['controls']['cleanup']['path'],
            }[target]
            path.write_bytes(path.read_bytes() + b'wrong')
    monkeypatch.setattr(module, '_write_file', mutate)
    with pytest.raises((ValueError, RuntimeError)):
        module.seal_compact_source(**request(sample))
    assert (sample['source'].parent / 'quarantine.json').exists()
    assert not (sample['source'] / 'commit.json').exists()
    assert sample['raw'].exists()


def test_support_boundary_accepts_equality_and_rejects_one_over(tmp_path):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    module.seal_compact_source(**request(sample))
    recording = sample['source'] / 'recording'
    bundle = {str(path.relative_to(recording)): path.read_bytes()
              for path in recording.rglob('*') if path.is_file()
              and path.name not in ('raw-audit.json', 'conversion.json')}
    raw = (recording / 'raw-audit.json').read_bytes()
    conversion = (recording / 'conversion.json').read_bytes()
    module._bounds(bundle, raw, conversion, 123, compact.MiB - 124, 1)
    with pytest.raises(ValueError, match='combined MiB'):
        module._bounds(bundle, raw, conversion, 123, compact.MiB - 123, 1)
    assert compact.PROTOCOL['source_finalization']['raw_report_uses_converter_scratch_entry'] is True
    assert compact.PROTOCOL['source_finalization']['numeric_disk_scratch'] is False


def test_canonical_snapshot_resolves_staging_and_final_without_extra_directory(tmp_path):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    case_id = sample['sample']['case']['case_id']
    expected = sample['root'] / 'cases' / case_id / 'source/snapshots/initial.snp'
    assert compact.source_snapshot_path(sample['root'], case_id, staged=True) == sample['snapshot']
    assert compact.source_snapshot_path(sample['root'], case_id, staged=False) == expected
    assert not (sample['root'] / '.pending/cases').exists()
    with compact.bound_payload(sample['root'], sample['contract']['snapshot'],
            compact.SNAPSHOT_MAX_BYTES, time.monotonic() + 30,
            source_case=case_id, staged=True):
        pass
    with pytest.raises(OSError):
        with compact.bound_payload(sample['root'], sample['contract']['snapshot'],
                compact.SNAPSHOT_MAX_BYTES, time.monotonic() + 30,
                source_case=case_id, staged=False):
            pass


@pytest.mark.parametrize('point', ['file-fsync', 'directory-fsync', 'final-directory-fsync', 'conversion', 'marker', 'after-marker'])
def test_publication_faults_are_quarantined(tmp_path, monkeypatch, point):
    import stat
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    original_write = module._write_file
    original_sync = os.fsync
    fired = []
    def write(directory, name, payload):
        if not fired and name == {'conversion': 'conversion.json', 'marker': '.commit.tmp'}.get(point):
            fired.append(True)
            raise OSError('synthetic publication fault')
        original_write(directory, name, payload)
        if point == 'after-marker' and name == '.commit.tmp':
            (sample['root'] / sample['contract']['controls']['cleanup']['path']).write_bytes(b'changed')
    def sync(fd):
        is_directory = stat.S_ISDIR(os.fstat(fd).st_mode)
        if not fired and ((point == 'file-fsync' and not is_directory)
                          or (point == 'directory-fsync' and is_directory)
                          or (point == 'final-directory-fsync' and is_directory
                              and (sample['source'] / '.commit.tmp').exists())):
            fired.append(True)
            raise OSError('synthetic durability fault')
        return original_sync(fd)
    monkeypatch.setattr(module, '_write_file', write)
    monkeypatch.setattr(os, 'fsync', sync)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.seal_compact_source(**request(sample))
    assert (sample['source'].parent / 'quarantine.json').exists()
    assert sample['raw'].exists()
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.read_sealed_source(**request(sample))


@pytest.mark.parametrize('field', ['marker', 'inventory', 'support'])
def test_rebound_seal_receipt_rejects_float_descriptor_sizes(tmp_path, field):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    module.seal_compact_source(**request(sample))
    conversion_path = sample['source'] / 'recording/conversion.json'
    marker_path = sample['source'] / 'commit.json'
    conversion = artifacts._json(conversion_path.read_bytes())
    marker = artifacts._json(marker_path.read_bytes())
    if field == 'marker':
        marker['conversion']['size_bytes'] = float(marker['conversion']['size_bytes'])
    else:
        conversion[field][0]['size_bytes'] = float(conversion[field][0]['size_bytes'])
        conversion_path.write_bytes(memory.canonical_bytes(conversion))
        marker['conversion'] = descriptor(marker['conversion']['path'], conversion_path.read_bytes())
    marker_path.write_bytes(memory.canonical_bytes(marker))
    with pytest.raises(ValueError):
        module.read_sealed_source(**request(sample))


@pytest.mark.parametrize('location', ['case', 'raw-parent'])
def test_refuses_unaccounted_staging_entries_before_writes(tmp_path, location):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    directory = sample['source'].parent if location == 'case' else sample['raw'].parent
    (directory / 'unregistered.tmp').write_bytes(b'leftover')
    before = inventory(sample['root'])
    with pytest.raises((ValueError, FileExistsError)):
        module.seal_compact_source(**request(sample))
    assert inventory(sample['root']) == before


def test_compact_overhead_accepts_exact_cap_and_rejects_one_byte_over(tmp_path):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    module.seal_compact_source(**request(sample))
    sealed = module.read_sealed_source(**request(sample))
    recording = sample['source'] / 'recording'
    bundle = {str(path.relative_to(recording)): path.read_bytes()
              for path in recording.rglob('*') if path.is_file()
              and path.name not in ('raw-audit.json', 'conversion.json')}
    raw = (recording / 'raw-audit.json').read_bytes()
    conversion = (recording / 'conversion.json').read_bytes()
    read = sealed['read']
    overhead = (sum(map(len, bundle.values())) - len(bundle['legacy-events.jsonl'])
                - len(read['rows']) * 19_534 - len(read['selected_frames']) * 98_304
                + len(raw) + len(conversion))
    at_limit = conversion + b'x' * (compact.MiB - overhead)
    module._bounds(bundle, raw, at_limit, 0, 0, 0)
    with pytest.raises(ValueError, match='frozen read limits'):
        module._bounds(bundle, raw, at_limit + b'x', 0, 0, 0)


def test_quarantine_publication_failure_remains_indeterminate(tmp_path, monkeypatch):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    def fail(*args, **kwargs):
        raise OSError('publication unavailable')
    monkeypatch.setattr(module, '_write_file', fail)
    with pytest.raises(module.SealIndeterminate):
        module.seal_compact_source(**request(sample))
    assert sample['raw'].exists()
    assert not (sample['source'] / 'commit.json').exists()
    before = inventory(sample['root'])
    with pytest.raises(FileExistsError):
        module.seal_compact_source(**request(sample))
    assert inventory(sample['root']) == before


@pytest.mark.parametrize('target', ['worker', 'marker', 'conversion', 'chunk'])
def test_read_keeps_output_identity_and_bytes_until_return(tmp_path, monkeypatch, target):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    module.seal_compact_source(**request(sample))
    path = {
        'worker': sample['source'] / 'worker-report.json',
        'marker': sample['source'] / 'commit.json',
        'conversion': sample['source'] / 'recording/conversion.json',
        'chunk': next((sample['source'] / 'recording/chunks').iterdir()),
    }[target]
    original = module._bounds
    def changed(*args, **kwargs):
        original(*args, **kwargs)
        path.write_bytes(path.read_bytes() + b'wrong')
    monkeypatch.setattr(module, '_bounds', changed)
    with pytest.raises((ValueError, RuntimeError)):
        module.read_sealed_source(**request(sample))


@pytest.mark.parametrize('location', ['source-extra', 'case-quarantine'])
def test_read_keeps_source_and_case_namespace_until_return(tmp_path, monkeypatch, location):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    module.seal_compact_source(**request(sample))
    original = module._bounds
    def changed(*args, **kwargs):
        original(*args, **kwargs)
        path = (sample['source'] / 'extra.tmp' if location == 'source-extra'
                else sample['source'].parent / 'quarantine.json')
        path.write_bytes(b'changed namespace')
    monkeypatch.setattr(module, '_bounds', changed)
    with pytest.raises((ValueError, RuntimeError)):
        module.read_sealed_source(**request(sample))


@pytest.mark.parametrize('target', ['worker', 'chunk', 'extra'])
def test_read_keeps_raw_inventory_until_return(tmp_path, monkeypatch, target):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    module.seal_compact_source(**request(sample))
    path = {
        'worker': sample['raw'] / 'worker-report.json',
        'chunk': next((sample['raw'] / 'recording/chunks').iterdir()),
        'extra': sample['raw'] / 'unregistered.tmp',
    }[target]
    original = module._bounds
    def changed(*args, **kwargs):
        original(*args, **kwargs)
        path.write_bytes((path.read_bytes() if path.exists() else b'') + b'wrong')
    monkeypatch.setattr(module, '_bounds', changed)
    with pytest.raises((ValueError, RuntimeError)):
        module.read_sealed_source(**request(sample))


def test_marker_sync_and_quarantine_failure_cannot_admit_source(tmp_path, monkeypatch):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    original_sync = os.fsync
    original_write = module._write_file
    def sync(fd):
        if Path(os.readlink(f'/proc/self/fd/{fd}')).name in ('commit.json', '.commit.tmp'):
            raise OSError('marker data sync failed')
        return original_sync(fd)
    def write(directory, name, payload):
        if name == 'quarantine.json':
            raise OSError('quarantine publication failed')
        return original_write(directory, name, payload)
    monkeypatch.setattr(os, 'fsync', sync)
    monkeypatch.setattr(module, '_write_file', write)
    with pytest.raises(module.SealIndeterminate):
        module.seal_compact_source(**request(sample))
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.read_sealed_source(**request(sample))


def test_postcommit_descriptor_teardown_cannot_reclassify_publication(tmp_path, monkeypatch):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    original = os.close
    def close(fd):
        original(fd)
        if (sample['source'] / 'commit.json').exists():
            raise OSError('synthetic postcommit descriptor close failure')
    monkeypatch.setattr(os, 'close', close)
    result = module.seal_compact_source(**request(sample))
    assert result['descriptor_teardown_errors']
    monkeypatch.setattr(os, 'close', original)
    assert module.read_sealed_source(**request(sample))['marker']['run_id'] == result['run_id']


@pytest.mark.parametrize('target', ['worker', 'chunk'])
def test_prepared_marker_does_not_skip_final_output_proof(tmp_path, monkeypatch, target):
    module = producer()
    sample = fixture(tmp_path / 'evidence')
    original = module._write_file
    def changed(directory, name, payload):
        original(directory, name, payload)
        if name == '.commit.tmp':
            path = (sample['source'] / 'worker-report.json' if target == 'worker'
                    else next((sample['source'] / 'recording/chunks').iterdir()))
            path.write_bytes(path.read_bytes() + b'wrong')
    monkeypatch.setattr(module, '_write_file', changed)
    with pytest.raises((ValueError, RuntimeError)):
        module.seal_compact_source(**request(sample))
    assert not (sample['source'] / 'commit.json').exists()


def test_final_rename_refuses_existing_marker_without_replacing_bytes(tmp_path):
    module = producer()
    (tmp_path / '.commit.tmp').write_bytes(b'candidate')
    (tmp_path / 'commit.json').write_bytes(b'existing')
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(FileExistsError):
            module._rename_noreplace(fd)
    finally:
        os.close(fd)
    assert (tmp_path / '.commit.tmp').read_bytes() == b'candidate'
    assert (tmp_path / 'commit.json').read_bytes() == b'existing'


def test_final_rename_refuses_unsupported_platform_without_mutation(tmp_path, monkeypatch):
    module = producer()
    (tmp_path / '.commit.tmp').write_bytes(b'candidate')
    before = inventory(tmp_path)
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    monkeypatch.setattr(module.sys, 'platform', 'unsupported')
    try:
        with pytest.raises(NotImplementedError):
            module._rename_noreplace(fd)
    finally:
        os.close(fd)
    assert inventory(tmp_path) == before
