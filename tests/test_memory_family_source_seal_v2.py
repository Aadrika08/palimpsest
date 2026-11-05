"""Authored public V2 source checks; no owner/model or actual source qualification."""
import importlib
import copy
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

import pytest

from palimpsest import artifacts, memory
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_raw_audit_v4 as audit
from test_memory_family_producer_v4 import fixture as source_fixture, request, inventory
from test_memory_family_numeric_preservation_v2 import numeric_values, mutate

ROOT = Path(__file__).parents[1]


def source_module():
    assert (ROOT / 'scripts/memory_family_source_seal_v2.py').is_file(), \
        'Public numeric source writer/reader is missing'
    return importlib.import_module('scripts.memory_family_source_seal_v2')


def fixture(root, *, metadata_bytes=0, control_bytes=0):
    import test_memory_family_raw_audit_v4 as raw_fixture
    original = raw_fixture._policy_row
    def authored(row, run_id, pixel_shift=0):
        event, arrays = original(row, run_id, pixel_shift)
        arrays.update(numeric_values(row['tick']))
        return event, arrays
    original_manifest = raw_fixture._manifest
    def manifest(*args, **kwargs):
        value = original_manifest(*args, **kwargs)
        if metadata_bytes:
            value['authored_padding'] = 'x' * metadata_bytes
        return value
    def controls(*args):
        return {'supervisor': {'closed':True, 'authored_padding':'x' * control_bytes}}
    with patch.object(raw_fixture, '_policy_row', authored), patch.object(raw_fixture, '_manifest', manifest):
        return source_fixture(root, control_factory=controls if control_bytes else None)


def test_public_numeric_source_roundtrip_retains_originals(tmp_path):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    original = inventory(sample['root'])
    raw_before = inventory(sample['raw'])
    snapshot = sample['snapshot'].stat()
    result = module.seal_numeric_source_v2(**request(sample))
    assert result['status'] == 'preserved-awaiting-lifetime-reconciliation'
    assert result['actual_source_qualified'] is False
    assert result['publication_outcome_verified'] is False
    assert result['independent_finalization_required'] is True
    reread = module.read_numeric_source_v2(**request(sample))
    assert reread['read']['preservation']['raw_comparison_performed'] is True
    assert reread['read']['preservation']['actual_source_qualified'] is False
    for row in reread['read']['rows']:
        for name, expected in numeric_values(row['tick']).items():
            assert row[name].dtype.str == expected.dtype.str
            assert row[name].shape == expected.shape
            assert row[name].tobytes() == expected.tobytes()
    assert inventory(sample['raw']) == raw_before
    assert sample['snapshot'].stat().st_ino == snapshot.st_ino
    assert sample['snapshot'].stat().st_nlink == 1
    assert inventory(sample['source']) == {p[len(str(sample['source'].relative_to(sample['root'])))+1:]: b
        for p, b in original.items() if p.startswith(str(sample['source'].relative_to(sample['root'])) + '/')}
    assert not (sample['source'] / 'commit.json').exists()
    for path, payload in original.items():
        assert (sample['root'] / path).read_bytes() == payload
    assert result['byte_ledger']['parent_terminal_max_bytes'] == 65536
    assert result['byte_ledger']['metadata_reserve_bytes'] > 0
    assert result['byte_ledger']['overhead_bytes'] <= 1048576
    assert result['byte_ledger']['registered_peak_upper_bound_bytes'] <= 640 * 1048576
    assert result['byte_ledger']['stage_peak_accounted'] is False
    with pytest.raises(PermissionError, match='pruning'):
        module.prune_raw_source(**request(sample))


def test_source_fixture_is_accepted_by_unchanged_public_raw_audit(tmp_path):
    sample = fixture(tmp_path / 'evidence')
    from scripts import memory_family_producer_v4 as producer
    receipt = audit.validate_raw_receipt(**producer._raw_request(sample['root'],
        sample['contract'], sample['contract']['case']['case_id'],
        sample['contract']['run_id'], time.monotonic() + 30))
    expected = artifacts._json((sample['root'] / sample['contract']['raw_audit']['path']).read_bytes())
    assert receipt == expected


def candidate(sample):
    return sample['root'] / 'numeric-v2' / sample['contract']['case']['case_id'] / sample['contract']['run_id']


def target_path(sample, target):
    return {
        'raw': next((sample['raw'] / 'recording/chunks').iterdir()),
        'control': sample['root'] / sample['contract']['controls']['cleanup']['path'],
        'snapshot': sample['snapshot'],
        'owner': sample['source'] / 'owner.json',
        'registration': sample['root'] / sample['registration']['path'],
        'worker': sample['raw'] / 'worker-report.json',
        'receipt': sample['root'] / sample['contract']['raw_audit']['path'],
    }[target]


def test_public_import_is_pure():
    result = subprocess.run([sys.executable, '-B', '-c',
        "import sys; import scripts.memory_family_source_seal_v2; "
        "assert not set(sys.modules)&{'torch','mujoco','palimpsest.engine','palimpsest.model'}"],
        cwd=ROOT, env={**os.environ, 'PYTHONPATH':'src:.'}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('target', ['raw', 'control', 'snapshot', 'owner', 'registration', 'worker', 'receipt'])
def test_change_and_restore_during_final_rename_is_refused(tmp_path, monkeypatch, target):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    raw_before = inventory(sample['raw'])
    path = target_path(sample, target)
    original_bytes = path.read_bytes()
    original = module._rename_noreplace
    def changed(fd):
        original(fd)
        path.write_bytes(original_bytes + b'changed')
        path.write_bytes(original_bytes)
    monkeypatch.setattr(module, '_rename_noreplace', changed)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.seal_numeric_source_v2(**request(sample))
    assert (candidate(sample) / 'quarantine.json').is_file()
    assert inventory(sample['raw']) == raw_before
    assert path.read_bytes() == original_bytes
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.read_numeric_source_v2(**request(sample))


@pytest.mark.parametrize('target', ['raw', 'control', 'snapshot', 'owner', 'registration', 'receipt'])
@pytest.mark.parametrize('kind', ['mutation', 'hardlink', 'symlink'])
def test_invalid_input_fails_before_candidate_writes(tmp_path, target, kind):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    path = target_path(sample, target)
    if kind == 'mutation':
        path.write_bytes(path.read_bytes() + b'changed')
    elif kind == 'hardlink':
        os.link(path, tmp_path / 'authored-alias')
    else:
        retained = tmp_path / 'authored-original'
        path.rename(retained)
        path.symlink_to(retained)
    before = inventory(sample['root'])
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.seal_numeric_source_v2(**request(sample))
    assert not candidate(sample).exists()
    assert inventory(sample['root']) == before


@pytest.mark.parametrize('location', ['run', 'ancestor-extra', 'numeric-symlink', 'source-extra', 'case-extra', 'raw-extra'])
def test_occupied_or_aliased_namespace_is_never_reused(tmp_path, location):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    output = candidate(sample)
    if location == 'run':
        output.mkdir(parents=True)
    elif location == 'ancestor-extra':
        (sample['root'] / 'numeric-v2/other-case').mkdir(parents=True)
    elif location == 'numeric-symlink':
        target = tmp_path / 'authored-other'
        target.mkdir()
        (sample['root'] / 'numeric-v2').symlink_to(target, target_is_directory=True)
    else:
        parent = {'source-extra': sample['source'], 'case-extra': sample['source'].parent,
                  'raw-extra': sample['raw']}[location]
        (parent / 'unknown').write_bytes(b'preserve')
    before = inventory(sample['root'])
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.seal_numeric_source_v2(**request(sample))
    assert inventory(sample['root']) == before


@pytest.mark.parametrize('point', ['numeric', 'conversion', 'prepared-marker', 'rename', 'after-rename', 'file-fsync', 'directory-fsync'])
def test_publication_failures_preserve_raw_and_partials(tmp_path, monkeypatch, point):
    import stat
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    raw_before = inventory(sample['raw'])
    write = module._write_file
    rename = module._rename_noreplace
    sync = os.fsync
    fired = []
    def failed_write(fd, name, payload):
        if (not fired and ((point == 'numeric' and name == '000000.npz')
                or (point == 'conversion' and name == 'conversion.json')
                or (point == 'prepared-marker' and name == '.commit.tmp'))):
            fired.append(True)
            # A genuine retained partial, not a fake successful receipt.
            write(fd, name, payload[:17])
            raise OSError('authored partial-write fault')
        return write(fd, name, payload)
    def failed_rename(fd):
        if point == 'rename':
            raise OSError('authored rename fault')
        rename(fd)
        if point == 'after-rename':
            raise OSError('authored late publication fault')
    def failed_sync(fd):
        directory = stat.S_ISDIR(os.fstat(fd).st_mode)
        if (not fired and candidate(sample).exists() and
                ((point == 'file-fsync' and not directory) or
                 (point == 'directory-fsync' and directory))):
            fired.append(True)
            raise OSError('authored fsync fault')
        return sync(fd)
    monkeypatch.setattr(module, '_write_file', failed_write)
    monkeypatch.setattr(module, '_rename_noreplace', failed_rename)
    monkeypatch.setattr(os, 'fsync', failed_sync)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.seal_numeric_source_v2(**request(sample))
    assert inventory(sample['raw']) == raw_before
    if candidate(sample).exists():
        assert ((candidate(sample) / 'quarantine.json').is_file()
                or not (candidate(sample) / 'commit.json').exists())
    before = inventory(sample['root'])
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.seal_numeric_source_v2(**request(sample))
    assert inventory(sample['root']) == before
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.read_numeric_source_v2(**request(sample))


@pytest.mark.parametrize('field', ['latency', 'step_latency', 'population_stats'])
def test_rehashed_numeric_candidate_must_match_raw(tmp_path, monkeypatch, field):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    original = module.numeric.convert_candidate
    def changed(*args, **kwargs):
        bundle = original(*args, **kwargs)
        def alter(values):
            values[field].reshape(-1)[0] += 1
        return mutate(bundle, 0, alter)
    monkeypatch.setattr(module.numeric, 'convert_candidate', changed)
    with pytest.raises(ValueError, match=field):
        module.seal_numeric_source_v2(**request(sample))
    assert not candidate(sample).exists()
    assert sample['raw'].is_dir()


def test_actual_disk_reread_detects_changed_candidate(tmp_path, monkeypatch):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    original = module._write_file
    def changed(fd, name, payload):
        original(fd, name, payload)
        if name == '.commit.tmp':
            path = candidate(sample) / 'numeric/000000.npz'
            path.write_bytes(path.read_bytes() + b'changed-on-disk')
    monkeypatch.setattr(module, '_write_file', changed)
    with pytest.raises((ValueError, RuntimeError)):
        module.seal_numeric_source_v2(**request(sample))
    assert not (candidate(sample) / 'commit.json').exists()
    assert (candidate(sample) / 'quarantine.json').is_file()


@pytest.mark.parametrize('target', ['raw', 'control', 'snapshot', 'owner', 'worker', 'receipt'])
def test_raw_backed_reader_retains_input_witnesses_until_return(tmp_path, monkeypatch, target):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    module.seal_numeric_source_v2(**request(sample))
    before = inventory(sample['root'])
    original = module._records
    path = target_path(sample, target)
    payload = path.read_bytes()
    def changed(*args, **kwargs):
        result = original(*args, **kwargs)
        path.write_bytes(payload + b'changed')
        path.write_bytes(payload)
        return result
    monkeypatch.setattr(module, '_records', changed)
    with pytest.raises((ValueError, RuntimeError)):
        module.read_numeric_source_v2(**request(sample))
    assert inventory(sample['root']) == before


@pytest.mark.parametrize('target', ['numeric/000000.npz', 'base/chunks/000000.npz', 'conversion.json', 'commit.json', 'unknown'])
def test_reader_rejects_changed_disk_or_unknown_members(tmp_path, target):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    module.seal_numeric_source_v2(**request(sample))
    path = candidate(sample) / target
    path.write_bytes((path.read_bytes() if path.exists() else b'') + b'changed')
    before = inventory(sample['root'])
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.read_numeric_source_v2(**request(sample))
    assert inventory(sample['root']) == before


@pytest.mark.parametrize('phase', ['before', 'after-marker'])
def test_deadline_never_returns_accepted_result(tmp_path, monkeypatch, phase):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    value = request(sample)
    if phase == 'before':
        value['deadline'] = time.monotonic() - 1
    else:
        original = module._rename_noreplace
        def renamed(fd):
            original(fd)
            raise TimeoutError('authored late deadline')
        monkeypatch.setattr(module, '_rename_noreplace', renamed)
    with pytest.raises(TimeoutError):
        module.seal_numeric_source_v2(**value)
    if phase == 'before':
        assert not candidate(sample).exists()
    else:
        assert (candidate(sample) / 'quarantine.json').is_file()


def test_late_descriptor_close_failure_is_quarantined(tmp_path, monkeypatch):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    original = os.close
    fired = []
    def close(fd):
        original(fd)
        if not fired and (candidate(sample) / 'commit.json').exists():
            fired.append(True)
            raise OSError('authored late descriptor close failure')
    monkeypatch.setattr(os, 'close', close)
    with pytest.raises((RuntimeError, OSError)):
        module.seal_numeric_source_v2(**request(sample))
    assert fired
    assert (candidate(sample) / 'quarantine.json').is_file()


def test_quarantine_failure_is_indeterminate_and_retains_evidence(tmp_path, monkeypatch):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    original = module._write_file
    def fail(fd, name, payload):
        if name in ('conversion.json', 'quarantine.json'):
            raise OSError('authored unavailable publication')
        return original(fd, name, payload)
    monkeypatch.setattr(module, '_write_file', fail)
    with pytest.raises(module.SealIndeterminate):
        module.seal_numeric_source_v2(**request(sample))
    assert sample['raw'].is_dir()
    assert not (candidate(sample) / 'commit.json').exists()
    assert (candidate(sample) / 'base').is_dir()


def test_ledger_accounts_unique_physical_paths_and_all_reserved_metadata(tmp_path):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    result = module.seal_numeric_source_v2(**request(sample))
    ledger = result['byte_ledger']
    raw = inventory(sample['raw'])
    bundle = {value['path']: (candidate(sample) / value['path']).read_bytes()
              for value in result['conversion']['inventory']}
    external = ledger['physical_domains']['registered_external']
    raw_prefix = str(sample['raw'].relative_to(sample['root'])) + '/'
    outside_raw = {value['path']: value['size_bytes'] for value in external
                   if not value['path'].startswith(raw_prefix)}
    assert ledger['raw_bytes'] == sum(map(len, raw.values()))
    assert ledger['bundle_bytes'] == sum(map(len, bundle.values()))
    assert ledger['metadata_reserve_bytes'] == sum(module.RESERVES.values())
    assert ledger['registered_peak_upper_bound_bytes'] == (sum(map(len, raw.values())) +
        sample['snapshot'].stat().st_size + sum(map(len, bundle.values())) +
        sum(outside_raw.values()) + sum(module.RESERVES.values()))
    actual_external = sum(value['size_bytes'] for value in external)
    assert ledger['external_overhead_bytes'] == actual_external + sum(module.RESERVES.values())
    assert ledger['recording_bytes'] == sum(map(len, bundle.values())) + ledger['external_overhead_bytes']
    assert len(external) == len({value['path'] for value in external})
    assert sum(p.name == 'initial.snp' for p in sample['root'].rglob('*')) == 1
    # Independent complete combined overhead boundary: all public external
    # metadata is supplied, never the codec's zero default.
    receipt = artifacts._json((sample['root'] / sample['contract']['raw_audit']['path']).read_bytes())
    base_overhead = ledger['overhead_bytes'] - ledger['external_overhead_bytes']
    at_limit = compact.MiB - base_overhead
    assert module.numeric.account_candidate(bundle, raw_audit_receipt=receipt,
        external_overhead_bytes=at_limit)['overhead_bytes'] == compact.MiB
    with pytest.raises(ValueError):
        module.numeric.account_candidate(bundle, raw_audit_receipt=receipt,
            external_overhead_bytes=at_limit + 1)


@pytest.mark.parametrize('kind', ['raw-metadata', 'controls'])
def test_valid_raw_that_cannot_fit_combined_metadata_is_retained_failure(tmp_path, kind):
    module = source_module()
    sample = fixture(tmp_path / 'evidence',
        metadata_bytes=900 * 1024 if kind == 'raw-metadata' else 0,
        control_bytes=900 * 1024 if kind == 'controls' else 0)
    from scripts import memory_family_producer_v4 as producer
    receipt = audit.validate_raw_receipt(**producer._raw_request(sample['root'],
        sample['contract'], sample['contract']['case']['case_id'],
        sample['contract']['run_id'], time.monotonic() + 30))
    assert receipt['raw_inventory']['total_bytes'] > 0
    before = inventory(sample['root'])
    with pytest.raises(ValueError, match='limits|overhead|bound|MiB'):
        module.seal_numeric_source_v2(**request(sample))
    assert not candidate(sample).exists()
    assert inventory(sample['root']) == before


@pytest.mark.parametrize('field', ['latency', 'step_latency', 'population_stats'])
def test_rehashed_published_numeric_bits_reach_raw_comparison(tmp_path, field):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    result = module.seal_numeric_source_v2(**request(sample))
    output = candidate(sample)
    bundle = {value['path']: (output / value['path']).read_bytes()
              for value in result['conversion']['inventory']}
    def alter(values):
        values[field].reshape(-1)[-1] += 1
    changed = mutate(bundle, 0, alter)
    for path in changed:
        if changed[path] != bundle[path]:
            (output / path).write_bytes(changed[path])
    conversion = copy.deepcopy(result['conversion'])
    conversion['inventory'] = [compact._descriptor(path, changed[path]) for path in sorted(changed)]
    payload = memory.canonical_bytes(conversion)
    (output / 'conversion.json').write_bytes(payload)
    marker = copy.deepcopy(result['marker'])
    marker['conversion'] = compact._descriptor(marker['candidate_path'] + '/conversion.json', payload)
    (output / 'commit.json').write_bytes(memory.canonical_bytes(marker))
    with pytest.raises(ValueError, match=field):
        module.read_numeric_source_v2(**request(sample))


@pytest.mark.parametrize('kind', ['replacement', 'change-and-restore'])
def test_candidate_file_witness_survives_final_rename(tmp_path, monkeypatch, kind):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    original = module._rename_noreplace
    def changed(fd):
        original(fd)
        path = candidate(sample) / 'numeric/000000.npz'
        payload = path.read_bytes()
        if kind == 'replacement':
            path.rename(tmp_path / 'retained-original.npz')
        else:
            path.write_bytes(payload + b'changed')
        path.write_bytes(payload)
    monkeypatch.setattr(module, '_rename_noreplace', changed)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.seal_numeric_source_v2(**request(sample))
    assert (candidate(sample) / 'quarantine.json').is_file()


def auxiliary(sample, payload=b'authored auxiliary control'):
    path = sample['root'] / 'auxiliary.json'
    path.write_bytes(payload)
    return compact._descriptor(path.name, payload)


def test_additional_controls_are_held_charged_and_bound_in_conversion(tmp_path):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    extra = auxiliary(sample)
    args = {**request(sample), 'additional_controls':[extra]}
    result = module.seal_numeric_source_v2(**args)
    assert result['conversion']['additional_controls'] == [extra]
    assert extra in result['byte_ledger']['physical_domains']['registered_external']
    assert module.read_numeric_source_v2(**args)['conversion'] == result['conversion']
    with pytest.raises(ValueError, match='differs'):
        module.read_numeric_source_v2(**request(sample))


def test_auxiliary_control_can_make_combined_overhead_ineligible(tmp_path):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    extra = auxiliary(sample, b'x' * (900 * 1024))
    before = inventory(sample['root'])
    with pytest.raises(ValueError, match='limits'):
        module.seal_numeric_source_v2(**request(sample), additional_controls=[extra])
    assert inventory(sample['root']) == before
    assert not candidate(sample).exists()


def test_auxiliary_control_change_and_restore_at_rename_is_refused(tmp_path, monkeypatch):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    extra = auxiliary(sample)
    path = sample['root'] / extra['path']
    payload = path.read_bytes()
    original = module._rename_noreplace
    def changed(fd):
        original(fd)
        path.write_bytes(payload + b'changed')
        path.write_bytes(payload)
    monkeypatch.setattr(module, '_rename_noreplace', changed)
    with pytest.raises((ValueError, RuntimeError)):
        module.seal_numeric_source_v2(**request(sample), additional_controls=[extra])
    assert (candidate(sample) / 'quarantine.json').is_file()


def test_duplicate_registered_physical_role_counts_once_but_real_copy_counts_twice(tmp_path):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    existing = copy.deepcopy(sample['contract']['controls']['job'])
    payload = (sample['root'] / existing['path']).read_bytes()
    extra = auxiliary(sample, payload)
    result = module.seal_numeric_source_v2(**request(sample),
        additional_controls=sorted([existing, extra], key=lambda value:value['path']))
    external = result['byte_ledger']['physical_domains']['registered_external']
    assert sum(value['path'] == existing['path'] for value in external) == 1
    assert extra in external
    assert existing['sha256'] == extra['sha256']
    assert existing['path'] != extra['path']


@pytest.mark.parametrize('kind', ['reordered', 'duplicate', 'unknown-key', 'float-size',
    'too-many', 'output-root', 'raw-root', 'case-root', 'hardlink', 'symlink'])
def test_invalid_additional_controls_fail_before_writes(tmp_path, kind):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    extra = auxiliary(sample)
    values = [extra]
    if kind == 'reordered':
        values = [sample['contract']['controls']['job'], extra]
    elif kind == 'duplicate':
        values = [extra, extra]
    elif kind == 'unknown-key':
        values = [{**extra, 'unknown':True}]
    elif kind == 'float-size':
        values = [{**extra, 'size_bytes':float(extra['size_bytes'])}]
    elif kind == 'too-many':
        values = [extra] * 129
    elif kind == 'output-root':
        values = [{**extra, 'path':'numeric-v2/unknown.json'}]
    elif kind == 'raw-root':
        values = [{**extra, 'path':'.pending/unknown.json'}]
    elif kind == 'case-root':
        values = [{**extra, 'path':'cases/unknown.json'}]
    elif kind == 'hardlink':
        os.link(sample['root'] / extra['path'], tmp_path / 'retained-aux-alias')
    else:
        path = sample['root'] / extra['path']
        retained = tmp_path / 'retained-aux-original'
        path.rename(retained)
        path.symlink_to(retained)
    before = inventory(sample['root'])
    with pytest.raises((ValueError, RuntimeError, OSError)):
        module.seal_numeric_source_v2(**request(sample), additional_controls=values)
    assert inventory(sample['root']) == before


def test_evidence_root_replacement_and_restore_is_refused(tmp_path, monkeypatch):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    original = module._rename_noreplace
    def changed(fd):
        original(fd)
        retained = tmp_path / 'moved-evidence'
        sample['root'].rename(retained)
        retained.rename(sample['root'])
    monkeypatch.setattr(module, '_rename_noreplace', changed)
    with pytest.raises((ValueError, RuntimeError)):
        module.seal_numeric_source_v2(**request(sample))
    assert (candidate(sample) / 'quarantine.json').is_file()


def test_unbounded_disk_inventory_is_refused_before_opening_payloads(tmp_path, monkeypatch):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    result = module.seal_numeric_source_v2(**request(sample))
    output = candidate(sample)
    conversion = copy.deepcopy(result['conversion'])
    conversion['inventory'] = [compact._descriptor(f'large-{i:03d}.npz', b'0') for i in range(128)]
    for value in conversion['inventory']:
        value['size_bytes'] = 32 * compact.MiB
    (output / 'conversion.json').write_bytes(memory.canonical_bytes(conversion))
    with pytest.raises(ValueError, match='aggregate predecode bound'):
        module.read_numeric_source_v2(**request(sample))


def test_indeterminate_writer_marker_never_proves_process_success(tmp_path, monkeypatch):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    before = inventory(sample['raw'])
    write = module._write_file
    rename = module._rename_noreplace
    def failed_write(fd, name, payload):
        if name == 'quarantine.json':
            raise OSError('authored all failure writes unavailable')
        return write(fd, name, payload)
    def failed_rename(fd):
        rename(fd)
        raise OSError('authored failed writer after rename')
    with monkeypatch.context() as changes:
        changes.setattr(module, '_write_file', failed_write)
        changes.setattr(module, '_rename_noreplace', failed_rename)
        with pytest.raises(module.SealIndeterminate):
            module.seal_numeric_source_v2(**request(sample))
    assert (candidate(sample) / 'commit.json').is_file()
    assert not (candidate(sample) / 'quarantine.json').exists()
    assert inventory(sample['raw']) == before
    proof = module.read_numeric_source_v2(**request(sample))
    assert proof['status'] == 'preserved-awaiting-lifetime-reconciliation'
    assert proof['actual_source_qualified'] is False
    assert proof['publication_outcome_verified'] is False
    assert proof['independent_finalization_required'] is True
    assert proof['preservation']['publication_outcome_verified'] is False
    assert proof['preservation']['lifetime_reconciled'] is False
    with pytest.raises(FileExistsError):
        module.seal_numeric_source_v2(**request(sample))


@pytest.mark.parametrize('field', ['snapshot_reference', 'snapshot_event_prefix'])
def test_rehashed_base_snapshot_metadata_must_match_held_original_snp(tmp_path, field):
    import hashlib
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    result = module.seal_numeric_source_v2(**request(sample))
    output = candidate(sample)
    bundle = {value['path']: (output / value['path']).read_bytes()
              for value in result['conversion']['inventory']}
    base = artifacts._json(bundle['base/manifest.json'])
    if field == 'snapshot_reference':
        base[field]['sha256'] = '0' * 64
    else:
        prefix = bundle['base/legacy-events.jsonl'].splitlines(keepends=True)[0]
        base[field] = {'size_bytes':len(prefix), 'event_count':1,
                       'sha256':hashlib.sha256(prefix).hexdigest()}
    bundle['base/manifest.json'] = memory.canonical_bytes(base)
    envelope = artifacts._json(bundle['numeric-v2.json'])
    envelope['base_manifest'] = compact._descriptor('base/manifest.json', bundle['base/manifest.json'])
    envelope['base_files'] = [compact._descriptor(path, bundle[path])
                              for path in sorted(bundle) if path.startswith('base/')]
    bundle['numeric-v2.json'] = memory.canonical_bytes(envelope)
    receipt = artifacts._json((sample['root'] / sample['contract']['raw_audit']['path']).read_bytes())
    raw = module.producer.legacy._read_run({'run_id':sample['contract']['run_id'],
        'run':sample['raw']}, time.monotonic() + 30)
    # The unchanged pure all-row proof has no source-SNP custody contract;
    # rebind all public metadata so only Task2's original-SNP check can stop it.
    read = module.numeric.prove_numeric_preservation(raw, bundle, receipt)
    conversion, payload, marker, marker_bytes = module._records(sample['registration'],
        sample['contract'], receipt, bundle, read, sample['contract']['case']['case_id'],
        sample['contract']['run_id'], [])
    for path, value in bundle.items():
        (output / path).write_bytes(value)
    (output / 'conversion.json').write_bytes(payload)
    (output / 'commit.json').write_bytes(marker_bytes)
    with pytest.raises(ValueError, match='snapshot reference or event prefix'):
        module.read_numeric_source_v2(**request(sample))


@pytest.mark.parametrize('split', ['held-out', 'test', None])
@pytest.mark.parametrize('entry', ['seal_numeric_source_v2', 'read_numeric_source_v2'])
def test_registration_preflight_rejects_nondevelopment_before_case_construction(tmp_path, monkeypatch, split, entry):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    contract = copy.deepcopy(sample['contract'])
    # Change only a string/None in authored development metadata. Never create
    # or validate a held-out case, or open any protected case namespace.
    contract['case']['split'] = split
    payload = memory.canonical_bytes(contract)
    (sample['root'] / sample['registration']['path']).write_bytes(payload)
    registration = compact._descriptor(sample['registration']['path'], payload)
    before = inventory(sample['root'])
    called = []
    def forbidden(*args, **kwargs):
        called.append(True)
        pytest.fail('Nondevelopment registration reached case construction')
    monkeypatch.setattr(module.producer.world, 'validate_case', forbidden)
    with pytest.raises(ValueError, match='development'):
        getattr(module, entry)(**{**request(sample), 'registration':registration})
    assert not called
    assert not candidate(sample).exists()
    assert inventory(sample['root']) == before


@pytest.mark.parametrize('prefix', ['.pending', 'cases', 'numeric-v2'])
@pytest.mark.parametrize('entry', ['seal_numeric_source_v2', 'read_numeric_source_v2'])
def test_registration_descriptor_root_is_refused_before_any_payload_open(tmp_path, monkeypatch, prefix, entry):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    declared = {'path':prefix + '/never-created.json', 'size_bytes':1, 'sha256':'0' * 64}
    def forbidden(*args, **kwargs):
        pytest.fail('Protected registration descriptor reached a payload opener')
    monkeypatch.setattr(module.compact, 'bound_payload', forbidden)
    with pytest.raises(ValueError, match='outside|Invalid relative'):
        getattr(module, entry)(**{**request(sample), 'registration':declared})
    assert not candidate(sample).exists()


@pytest.mark.parametrize('prefix', ['.pending', 'cases', 'numeric-v2'])
@pytest.mark.parametrize('role,entry', [('job','seal_numeric_source_v2'), ('audit','read_numeric_source_v2')])
def test_control_descriptor_roots_are_refused_before_control_payload_open(tmp_path, monkeypatch, prefix, role, entry):
    module = source_module()
    sample = fixture(tmp_path / 'evidence')
    contract = copy.deepcopy(sample['contract'])
    declared = {'path':prefix + '/never-created.json', 'size_bytes':1, 'sha256':'0' * 64}
    contract['controls'][role] = declared
    if role == 'audit':
        contract['raw_audit'] = declared
    payload = memory.canonical_bytes(contract)
    (sample['root'] / sample['registration']['path']).write_bytes(payload)
    registration = compact._descriptor(sample['registration']['path'], payload)
    original = module.compact.bound_payload
    allowed = {registration['path'], module._protocol()['path']}
    def only_metadata(root, descriptor, *args, **kwargs):
        if descriptor['path'] not in allowed:
            pytest.fail('Invalid control metadata allowed a control/source payload open')
        return original(root, descriptor, *args, **kwargs)
    monkeypatch.setattr(module.compact, 'bound_payload', only_metadata)
    def forbidden(*args, **kwargs):
        pytest.fail('Invalid control metadata reached case construction')
    monkeypatch.setattr(module.producer.world, 'validate_case', forbidden)
    with pytest.raises(ValueError, match='outside|Invalid relative'):
        getattr(module, entry)(**{**request(sample), 'registration':registration})
    assert not candidate(sample).exists()
