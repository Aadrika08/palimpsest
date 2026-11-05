"""Authored codec checks only; no actual source/condition/model authority."""
import copy
import hashlib
import importlib
import io
import os
from pathlib import Path
import subprocess
import sys
import time
import zipfile
from unittest.mock import patch

import numpy as np
import pytest

from palimpsest import artifacts, memory
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_raw_audit_v4 as audit
from test_memory_family_compact_v4 import _legacy, _row, _snapshot_reference, CASE_ID

ROOT = Path(__file__).parents[1]
FIELDS = ('latency', 'step_latency', 'population_stats')
PROTOCOL_PATH = ROOT / 'docs/plans/memory-family-numeric-compact-v2-protocol.json'


def codec():
    assert (ROOT / 'scripts/memory_family_numeric_preservation_v2.py').is_file(), \
        'Strict numeric V2 codec is missing'
    return importlib.import_module('scripts.memory_family_numeric_preservation_v2')


def numeric_values(tick):
    return {
        'latency': np.array(-0.0 if tick % 2 else tick / 1000, '<f8'),
        'step_latency': np.array(-0.0 if tick % 3 else tick / 500, '<f8'),
        'population_stats': np.array([
            [0.0, -0.0, 0.0, -0.0],
            [2.0, .25 + tick, -.5, 1.0],
            [3.0, .5 + tick, -.75, 2.0],
        ], '<f8'),
    }


def declared_receipt(rows, run_id, case_id, operation, events):
    """Declared fixture provenance, not an independently published receipt."""
    schemas = compact.PROTOCOL['raw_audit']['nested_schemas']
    value = {name: None for name in compact.PROTOCOL['schemas']['raw_audit']['exact_keys']}
    for name in ('raw_inventory', 'terminal_state', 'policy_result', 'oracle_result'):
        value[name] = {key: None for key in schemas[name]['exact_keys']}
    projection, cameras, sequence = audit._audit_rows(rows, operation)
    value.update(schema='memory-family-raw-audit-v4',
                 protocol_sha256=compact.PROTOCOL_SHA256,
                 run_id=run_id, case_id=case_id, operation=operation,
                 condition=None if operation == 'source' else 'own',
                 row_count=len(rows), chunk_count=(len(rows) + 31) // 32,
                 event_count=len(events), claims=copy.deepcopy(compact.PROTOCOL['claims']),
                 source_identity=audit.canonical_source_identity('a' * 64),
                 camera_sequence_sha256=cameras, row_sequence_sha256=sequence)
    value['raw_inventory'].update(schema='authored-fixture-only', files=[], file_count=0,
        recording_bytes=0, support_bytes=0, total_bytes=0, tree_sha256='b' * 64)
    value['terminal_state'].update(manifest_status='completed', final_phase='paused',
        total_ticks=rows[-1]['tick'] + 1, last_tick=rows[-1]['tick'],
        natural_failure=False, replacement=False)
    value['policy_result']['call_count'] = len(rows)
    value['oracle_result']['rows_sha256'] = memory.sha256(projection)
    if operation == 'source':
        value['snapshot_reference'] = {
            'path': f'cases/{case_id}/source/snapshots/initial.snp',
            'size_bytes': 1234, 'sha256': 'c' * 64}
    return value


def fixture(count=33, operation='condition'):
    rows = []
    for offset in range(count):
        # Reuse only legacy authored row creation, retaining its file unchanged.
        row = _row(offset % 240)
        row['tick'] = offset if operation == 'source' else offset + 7
        row.update(numeric_values(row['tick']))
        row['pose'] = np.array([row['tick'], .5, -.25], '<f8')
        row['next_pose'] = np.array([row['tick'] + 1, .5, -.25], '<f8')
        rows.append(row)
    run_id = '00000000000000000000000000000701'
    legacy_manifest, legacy_events, events = _legacy(rows, run_id)
    receipt = declared_receipt(rows, run_id, CASE_ID, operation, events)
    source = operation == 'source'
    snapshot = (_snapshot_reference('00000000000000000000000000000700') if not source else {
        **_snapshot_reference(run_id), 'kind': 'source',
        'source_receipt_sha256': None})
    prefix = ({'size_bytes': len(legacy_events),
               'sha256': hashlib.sha256(legacy_events).hexdigest(),
               'event_count': len(events)} if source else None)
    base = compact.convert_synthetic(run_id=run_id, case_id=CASE_ID,
        operation=operation, condition=None if source else 'own', rows=rows,
        legacy_manifest_bytes=legacy_manifest, legacy_events_bytes=legacy_events,
        snapshot_reference=snapshot, event_tick=None if source else 7,
        decision_tick=None if source else 8, snapshot_event_prefix=prefix,
        raw_audit_receipt=receipt)
    return rows, base, receipt


def descriptor(path, payload):
    return {'path': path, 'size_bytes': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest()}


def rebind(bundle, index):
    changed = dict(bundle)
    changed['numeric-index.json'] = memory.canonical_bytes(index)
    manifest = artifacts._json(changed['numeric-v2.json'])
    manifest['numeric_index'] = descriptor('numeric-index.json', changed['numeric-index.json'])
    changed['numeric-v2.json'] = memory.canonical_bytes(manifest)
    return changed


def mutate(bundle, partition, change):
    changed = dict(bundle)
    index = artifacts._json(changed['numeric-index.json'])
    path = index['chunks'][partition]['companion']['path']
    with np.load(io.BytesIO(changed[path]), allow_pickle=False) as archive:
        values = {name: archive[name].copy() for name in archive.files}
    change(values)
    stream = io.BytesIO()
    np.savez(stream, **values)
    changed[path] = stream.getvalue()
    index['chunks'][partition]['companion'] = descriptor(path, changed[path])
    return rebind(changed, index)


@pytest.mark.parametrize('count', [1, 31, 32, 33])
@pytest.mark.parametrize('operation', ['source', 'condition'])
def test_exact_roundtrip_and_partial_partition(count, operation):
    module = codec()
    rows, base, receipt = fixture(count, operation)
    original = dict(base)
    candidate = module.convert_candidate(base, rows, raw_audit_receipt=receipt)
    read = module.read_numeric_compact(candidate, raw_audit_receipt=receipt)
    assert base == original == module.extract_base_bundle(candidate)
    assert read['base_manifest'] == compact.read_compact(base, raw_audit_receipt=receipt)['manifest']
    assert len(read['rows']) == count
    for raw, restored in zip(rows, read['rows']):
        for name in (*compact.RETAINED, *FIELDS):
            assert restored[name].dtype.str == raw[name].dtype.str
            assert restored[name].shape == raw[name].shape
            assert restored[name].tobytes() == raw[name].tobytes()
    index = artifacts._json(candidate['numeric-index.json'])
    base_index = artifacts._json(base['chunk-index.json'])
    for entry, original_entry in zip(index['chunks'], base_index['chunks']):
        assert entry['base_chunk'] == original_entry
        with np.load(io.BytesIO(candidate[entry['companion']['path']])) as archive:
            assert archive.files == list(FIELDS)
    assert read['preservation']['raw_comparison_performed'] is False
    assert read['preservation']['actual_source_qualified'] is False
    assert read['preservation']['condition_qualified'] is False
    assert read['preservation']['model_replay_performed'] is False
    assert read['preservation']['stage_peak_accounted'] is False
    assert read['legacy_manifest_bytes'] == base['legacy-manifest.json']
    assert read['legacy_events_bytes'] == base['legacy-events.jsonl']


def test_protocol_canonical_exact_base_and_population_provenance():
    module = codec()
    payload = PROTOCOL_PATH.read_bytes()
    assert payload == memory.canonical_bytes(artifacts._json(payload)) == module.PROTOCOL_BYTES
    assert module.PROTOCOL['base_protocol'] == descriptor(
        str(compact.PROTOCOL_PATH.relative_to(ROOT)), compact.PROTOCOL_BYTES)
    assert module.PROTOCOL['row']['bytes_per_tick'] == 19646
    assert module.PROTOCOL['population']['rows'] == ['visual_left', 'visual_right', 'descending']
    assert module.PROTOCOL['population']['columns'] == ['count', 'mean', 'min', 'max']
    assert module.PROTOCOL['claims'] == compact.PROTOCOL['claims']
    assert module.validate_protocol(copy.deepcopy(module.PROTOCOL)) == module.PROTOCOL
    changed = copy.deepcopy(module.PROTOCOL)
    changed['row']['bytes_per_tick'] += 1
    with pytest.raises(ValueError):
        module.validate_protocol(changed)


@pytest.mark.parametrize('field', FIELDS)
@pytest.mark.parametrize('defect', ['shape', 'dtype', 'big-endian', 'object', 'nan', 'inf'])
def test_converter_refuses_numeric_domain_without_coercion(field, defect):
    module = codec()
    rows, base, receipt = fixture(1)
    value = rows[0][field]
    if defect == 'shape': value = value.reshape(-1) if field != 'population_stats' else value[:1]
    if defect == 'dtype': value = value.astype('<f4')
    if defect == 'big-endian': value = value.astype('>f8')
    if defect == 'object': value = value.astype(object)
    if defect in ('nan', 'inf'):
        value = value.copy()
        value.flat[0] = np.nan if defect == 'nan' else np.inf
    rows[0][field] = value
    with pytest.raises(ValueError, match=field):
        module.convert_candidate(base, rows, raw_audit_receipt=receipt)


@pytest.mark.parametrize('shape', [(0, 4), (1, 4), (4, 4), (4, 3)])
def test_population_other_domains_are_ineligible(shape):
    module = codec()
    rows, base, receipt = fixture(1)
    rows[0]['population_stats'] = np.zeros(shape, '<f8')
    with pytest.raises(ValueError, match='population_stats'):
        module.convert_candidate(base, rows, raw_audit_receipt=receipt)


@pytest.mark.parametrize('defect', ['missing-companion', 'orphan', 'reordered', 'extra-key',
    'wrong-schema', 'wrong-protocol', 'wrong-provenance', 'boolean-count', 'wrong-partition',
    'wrong-base-descriptor', 'noncanonical', 'duplicate-json', 'receipt', 'base-only', 'v2-to-v1'])
def test_envelope_exact_schema_and_bijection(defect):
    module = codec()
    rows, base, receipt = fixture()
    changed = module.convert_candidate(base, rows, raw_audit_receipt=receipt)
    index = artifacts._json(changed['numeric-index.json'])
    manifest = artifacts._json(changed['numeric-v2.json'])
    if defect == 'missing-companion': del changed['numeric/000001.npz']
    elif defect == 'orphan': changed['numeric/000002.npz'] = changed['numeric/000000.npz']
    elif defect == 'reordered':
        index['chunks'].reverse(); changed = rebind(changed, index)
    elif defect == 'wrong-partition':
        index['chunks'][1]['base_chunk']['start'] += 1; changed = rebind(changed, index)
    elif defect == 'extra-key': manifest['unknown'] = 1
    elif defect == 'wrong-schema': manifest['schema'] = 'memory-family-compact-manifest-v1'
    elif defect == 'wrong-protocol': manifest['protocol']['sha256'] = 'f' * 64
    elif defect == 'wrong-provenance': manifest['population']['rows'].reverse()
    elif defect == 'boolean-count': manifest['row_count'] = True
    elif defect == 'wrong-base-descriptor': manifest['base_files'][0]['sha256'] = 'f' * 64
    elif defect == 'noncanonical': changed['numeric-v2.json'] += b'\n'
    elif defect == 'duplicate-json':
        changed['numeric-v2.json'] = b'{"schema":1,"schema":2}'
    elif defect == 'receipt': receipt = copy.deepcopy(receipt); receipt['terminal_state']['total_ticks'] += 1
    elif defect == 'base-only': changed = base
    elif defect == 'v2-to-v1':
        with pytest.raises(ValueError): compact.read_compact(changed, raw_audit_receipt=receipt)
        return
    if defect in {'extra-key', 'wrong-schema', 'wrong-protocol', 'wrong-provenance', 'boolean-count', 'wrong-base-descriptor'}:
        changed['numeric-v2.json'] = memory.canonical_bytes(manifest)
    with pytest.raises(ValueError):
        module.read_numeric_compact(changed, raw_audit_receipt=receipt)


@pytest.mark.parametrize('defect', ['missing', 'extra', 'duplicate', 'compressed', 'badzip',
    'badheader', 'dtype', 'endian', 'nonfinite', 'shape', 'zip-comment', 'trailing-bytes'])
def test_rehashed_companion_archive_corruption(defect):
    module = codec()
    rows, base, receipt = fixture(1)
    changed = module.convert_candidate(base, rows, raw_audit_receipt=receipt)
    index = artifacts._json(changed['numeric-index.json'])
    path = 'numeric/000000.npz'
    if defect in {'dtype', 'endian', 'nonfinite', 'shape'}:
        def change(values):
            if defect == 'dtype': values['latency'] = values['latency'].astype('<f4')
            if defect == 'endian': values['latency'] = values['latency'].astype('>f8')
            if defect == 'nonfinite': values['latency'][0] = np.inf
            if defect == 'shape': values['population_stats'] = values['population_stats'][:, :1]
        changed = mutate(changed, 0, change)
    else:
        with zipfile.ZipFile(io.BytesIO(changed[path])) as archive:
            members = [(name, archive.read(name)) for name in archive.namelist()]
        if defect == 'missing': members.pop()
        if defect == 'extra': members.append(('extra.npy', members[0][1]))
        if defect == 'duplicate': members.append(members[0])
        if defect == 'badheader': members[0] = (members[0][0], b'not-npy')
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED if defect == 'compressed' else zipfile.ZIP_STORED) as archive:
            for i, (name, payload) in enumerate(members):
                if defect == 'duplicate' and i == len(members) - 1:
                    with pytest.warns(UserWarning, match='Duplicate name'):
                        archive.writestr(name, payload)
                else:
                    archive.writestr(name, payload)
            if defect == 'zip-comment': archive.comment = b'hidden metadata'
        changed[path] = stream.getvalue()
        if defect == 'badzip': changed[path] = b'not-zip'
        if defect == 'trailing-bytes': changed[path] += b'unaccounted suffix'
        index['chunks'][0]['companion'] = descriptor(path, changed[path])
        changed = rebind(changed, index)
    with pytest.raises(ValueError):
        module.read_numeric_compact(changed, raw_audit_receipt=receipt)


@pytest.fixture(scope='module')
def public_raw(tmp_path_factory):
    """Change test data creation only; public auditor/guards/pins stay unchanged."""
    import test_memory_family_raw_audit_v4 as raw_fixture
    root = tmp_path_factory.mktemp('numeric-public-raw')
    original = raw_fixture._policy_row
    def authored(row, run_id, pixel_shift=0):
        event, arrays = original(row, run_id, pixel_shift)
        arrays.update(numeric_values(row['tick']))
        return event, arrays
    with patch.object(raw_fixture, '_policy_row', authored):
        sample = raw_fixture._fixture(root, include_source=True)
    request = raw_fixture._request(sample, 'source')
    result = audit.audit_raw_run(**request)
    receipt = artifacts._json(Path(result['path']).read_bytes())
    data = raw_fixture.admission._read_run(
        {'run': sample['source']['run_path'], 'run_id': sample['source']['run_id']},
        time.monotonic() + 30)
    snapshot = {'kind': 'source', 'source_run_id': sample['source']['run_id'],
        'source_receipt_sha256': None, **request['snapshot_reference']}
    prefix = receipt['oracle_result']['source_application_sha256']
    assert prefix is not None
    from palimpsest import snapshots
    application = snapshots.read_snapshot(sample['snapshot_path'])['application']
    base = compact.convert_synthetic(run_id=sample['source']['run_id'],
        case_id=sample['case']['case_id'], operation='source', condition=None,
        rows=data['rows'], legacy_manifest_bytes=(data['run'] / 'recording/manifest.json').read_bytes(),
        legacy_events_bytes=(data['run'] / 'recording/events.jsonl').read_bytes(),
        snapshot_reference=snapshot, snapshot_event_prefix=application['event_prefix'],
        raw_audit_receipt=receipt)
    return data, base, receipt


def test_unchanged_public_raw_receipt_and_all_row_proof(public_raw):
    module = codec()
    data, base, receipt = public_raw
    candidate = module.convert_candidate(base, data['rows'], raw_audit_receipt=receipt)
    result = module.prove_numeric_preservation(data, candidate, receipt)
    assert result['preservation']['raw_comparison_performed'] is True
    assert result['preservation']['rows_checked'] == len(data['rows'])
    assert result['preservation']['actual_source_qualified'] is False
    assert result['trace_digest'] == compact.read_compact(base, raw_audit_receipt=receipt)['trace_digest']


@pytest.mark.parametrize('field', FIELDS)
@pytest.mark.parametrize('position', ['early-nonsampled', 'final'])
def test_rehashed_numeric_bits_fail_at_exact_field_tick(public_raw, field, position):
    module = codec()
    data, base, receipt = public_raw
    candidate = module.convert_candidate(base, data['rows'], raw_audit_receipt=receipt)
    selected = compact.read_compact(base, raw_audit_receipt=receipt)['selected_frames']
    offset = (next(i for i, row in enumerate(data['rows']) if row['tick'] not in selected)
              if position == 'early-nonsampled' else len(data['rows']) - 1)
    def change(values):
        values[field].view('<u8').reshape(len(values[field]), -1)[offset % 32, 0] ^= np.uint64(1)
    changed = mutate(candidate, offset // 32, change)
    # Rehashed format is valid: only raw equality can detect loss.
    module.read_numeric_compact(changed, raw_audit_receipt=receipt)
    tick = data['rows'][offset]['tick']
    with pytest.raises(ValueError, match=rf'{field}.*tick {tick}'):
        module.prove_numeric_preservation(data, changed, receipt)


@pytest.mark.parametrize('axis', [1, 2])
def test_population_row_and_column_permutation_fail_raw_proof(public_raw, axis):
    module = codec()
    data, base, receipt = public_raw
    candidate = module.convert_candidate(base, data['rows'], raw_audit_receipt=receipt)
    def change(values):
        values['population_stats'] = np.flip(values['population_stats'], axis=axis).copy()
    changed = mutate(candidate, 0, change)
    with pytest.raises(ValueError, match='population_stats.*tick 0'):
        module.prove_numeric_preservation(data, changed, receipt)


def test_old_base_proof_is_not_bypassed(public_raw):
    module = codec()
    data, base, receipt = public_raw
    from test_memory_family_compact_v4 import _mutate_chunk
    altered = _mutate_chunk(base, 0, lambda values: values['reward'].__setitem__(0, 2.0))
    candidate = module.convert_candidate(altered, data['rows'], raw_audit_receipt=receipt)
    with pytest.raises(ValueError, match='Raw-to-compact retained value differs: reward'):
        module.prove_numeric_preservation(data, candidate, receipt)


def test_actual_serialized_byte_accounting_and_external_combined_bound():
    module = codec()
    rows, base, receipt = fixture()
    candidate = module.convert_candidate(base, rows, raw_audit_receipt=receipt)
    dense, pixels = 0, 0
    for path, payload in candidate.items():
        if path.endswith('.npz'):
            with np.load(io.BytesIO(payload), allow_pickle=False) as archive:
                if path == 'base/audit-frames.npz':
                    pixels += sum(archive[name].nbytes for name in ('raw_cam_left', 'raw_cam_right'))
                else:
                    dense += sum(archive[name].nbytes for name in archive.files)
    total = sum(map(len, candidate.values()))
    events = len(base['legacy-events.jsonl'])
    overhead = total - events - dense - pixels
    ledger = module.account_candidate(candidate, raw_audit_receipt=receipt)
    assert ledger['dense_bytes'] == dense == len(rows) * 19646
    assert ledger['selected_pixel_bytes'] == pixels
    assert ledger['overhead_bytes'] == overhead
    assert ledger['recording_bytes'] == total
    extra = 1024**2 - overhead
    assert module.account_candidate(candidate, raw_audit_receipt=receipt,
        external_overhead_bytes=extra)['overhead_bytes'] == 1024**2
    with pytest.raises(ValueError, match='limit|overhead'):
        module.account_candidate(candidate, raw_audit_receipt=receipt, external_overhead_bytes=extra + 1)
    assert ledger['stage_peak_accounted'] is False
    assert ledger['snapshot_accounted'] is False


@pytest.mark.parametrize('operation,maximum', [('source', 1200), ('condition', 900)])
def test_limits_exact_ceiling_and_single_byte_over(operation, maximum):
    module = codec()
    ceiling = (32 if operation == 'source' else 25) * 1024**2
    module.validate_limits(operation, row_count=maximum, total_bytes=ceiling, overhead_bytes=1024**2)
    for total, overhead, rows in [(ceiling + 1, 1024**2, maximum),
            (ceiling, 1024**2 + 1, maximum), (ceiling, 0, maximum + 1),
            (ceiling, 0, 0), (True, 0, maximum)]:
        with pytest.raises(ValueError):
            module.validate_limits(operation, row_count=rows, total_bytes=total, overhead_bytes=overhead)


def test_import_has_no_model_or_native_side_effect():
    codec()
    code = "import sys; import scripts.memory_family_numeric_preservation_v2; assert not set(sys.modules)&{'torch','mujoco','palimpsest.engine','palimpsest.model'}"
    result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT,
        env={**os.environ, 'PYTHONPATH': 'src:scripts:tests:.'}, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('count', range(1, 33))
def test_each_partial_companion_matches_independent_zip_npy_size_model(count):
    module = codec()
    rows, base, receipt = fixture(count)
    candidate = module.convert_candidate(base, rows, raw_audit_receipt=receipt)
    payload = candidate['numeric/000000.npz']
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = archive.infolist()
        npy_overhead = 0
        for member in members:
            stream = io.BytesIO(archive.read(member))
            assert np.lib.format.read_magic(stream) == (1, 0)
            shape, fortran, dtype = np.lib.format.read_array_header_1_0(stream)
            assert fortran is False
            assert shape[0] == count
            assert dtype.str == '<f8'
            assert stream.tell() == 128
            npy_overhead += stream.tell()
        zip_overhead = len(payload) - sum(member.file_size for member in members)
        assert zip_overhead == 3 * (30 + 20 + 46) + 2 * sum(
            len(member.filename.encode('ascii')) for member in members) + 22 == 404
        assert npy_overhead == 384
        assert len(payload) == count * 112 + 788


@pytest.mark.parametrize('operation,count', [('source', 1200), ('condition', 900)])
def test_complete_operation_maximum_has_every_row_and_actual_serialized_ledger(operation, count):
    module = codec()
    rows, base, receipt = fixture(count, operation)
    candidate = module.convert_candidate(base, rows, raw_audit_receipt=receipt)
    read = module.read_numeric_compact(candidate, raw_audit_receipt=receipt)
    assert len(read['rows']) == count
    assert read['manifest']['chunk_count'] == (count + 31) // 32
    for original, restored in zip(rows, read['rows']):
        for field in FIELDS:
            assert original[field].tobytes() == restored[field].tobytes()
    ledger = read['byte_ledger']
    assert ledger['bundle_bytes'] == sum(map(len, candidate.values()))
    assert ledger['dense_bytes'] == count * 19646
    assert ledger['overhead_bytes'] <= 1024**2
    assert ledger['recording_bytes'] <= (32 if operation == 'source' else 25) * 1024**2


@pytest.mark.parametrize('target', ['manifest', 'index', 'entry', 'array', 'descriptor'])
@pytest.mark.parametrize('change', ['missing', 'extra'])
def test_nested_exact_schema_fields(target, change):
    module = codec()
    rows, base, receipt = fixture(1)
    candidate = module.convert_candidate(base, rows, raw_audit_receipt=receipt)
    index = artifacts._json(candidate['numeric-index.json'])
    manifest = artifacts._json(candidate['numeric-v2.json'])
    node = {'manifest': manifest, 'index': index, 'entry': index['chunks'][0],
            'array': index['chunks'][0]['arrays']['latency'],
            'descriptor': index['chunks'][0]['companion']}[target]
    if change == 'extra':
        node['unknown'] = 0
    else:
        node.pop(next(iter(node)))
    changed = rebind(candidate, index)
    if target == 'manifest': changed['numeric-v2.json'] = memory.canonical_bytes(manifest)
    with pytest.raises(ValueError):
        module.read_numeric_compact(changed, raw_audit_receipt=receipt)


@pytest.mark.parametrize('field', FIELDS)
def test_sign_of_zero_is_preserved_and_not_equated_in_raw_proof(public_raw, field):
    module = codec()
    data, base, receipt = public_raw
    candidate = module.convert_candidate(base, data['rows'], raw_audit_receipt=receipt)
    offset = (next(i for i, row in enumerate(data['rows']) if np.signbit(row[field]).any())
              if field != 'population_stats' else 0)
    def change(values):
        flat = values[field].reshape(len(values[field]), -1)[offset % 32]
        negative_zero = next(i for i, item in enumerate(flat) if item == 0 and np.signbit(item))
        flat[negative_zero] = 0.0
    changed = mutate(candidate, offset // 32, change)
    with pytest.raises(ValueError, match=rf'{field}.*tick {data["rows"][offset]["tick"]}'):
        module.prove_numeric_preservation(data, changed, receipt)


def test_valid_v1_metadata_can_exhaust_combined_v2_budget_without_padding_conversion_json():
    module = codec()
    rows, base, receipt = fixture(1)
    original_manifest = artifacts._json(base['legacy-manifest.json'])
    # Fill a legitimate copied legacy manifest, preserving all canonical fields.
    original_manifest['authored_metadata'] = ''
    old_manifest = artifacts._json(base['manifest.json'])
    def rebuild(padding):
        result = dict(base)
        value = dict(original_manifest, authored_metadata='x' * padding)
        result['legacy-manifest.json'] = memory.canonical_bytes(value) + b'\n'
        bound = copy.deepcopy(old_manifest)
        bound['legacy_manifest'] = descriptor('legacy-manifest.json', result['legacy-manifest.json'])
        result['manifest.json'] = memory.canonical_bytes(bound)
        return result
    test_base = rebuild(0)
    read = compact.read_compact(test_base, raw_audit_receipt=receipt)
    overhead = sum(map(len, test_base.values())) - len(test_base['legacy-events.jsonl']) \
        - 19534 - len(read['selected_frames']) * 98304
    test_base = rebuild(1024**2 - overhead - 2048)
    compact.read_compact(test_base, raw_audit_receipt=receipt)
    with pytest.raises(ValueError, match='limit'):
        module.convert_candidate(test_base, rows, raw_audit_receipt=receipt)


def test_untrusted_npy_dimensions_refuse_before_allocation_under_small_process_limit():
    codec()
    code = '''
import io, resource
import numpy as np
from scripts import memory_family_compact_v4 as c
from scripts import memory_family_numeric_preservation_v2 as n
values = {'latency': np.zeros(1, '<f8'), 'step_latency': np.zeros(1, '<f8'),
          'population_stats': np.zeros((1,3,4), '<f8')}
payload = c._npz(values)
import zipfile
out = io.BytesIO()
with zipfile.ZipFile(io.BytesIO(payload)) as src, zipfile.ZipFile(out, 'w') as dst:
    for member in src.infolist():
        content = src.read(member)
        if member.filename == 'latency.npy':
            stream = io.BytesIO()
            np.lib.format.write_array_header_1_0(stream, {
                'descr': '<f8', 'fortran_order': False, 'shape': (1000000000,)})
            content = stream.getvalue()
        dst.writestr(member.filename, content)
resource.setrlimit(resource.RLIMIT_AS, (256*1024**2, 256*1024**2))
try:
    n._read_numeric_npz(out.getvalue(), 1)
except ValueError:
    print('bounded-format-refusal')
else:
    raise AssertionError('untrusted dimensions accepted')
'''
    result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT,
        env={**os.environ, 'PYTHONPATH': 'src:scripts:tests:.',
             'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1'},
        capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'bounded-format-refusal'


@pytest.mark.parametrize('field', ['row_count', 'chunk_count', 'event_count'])
@pytest.mark.parametrize('wrong', [True, 999])
def test_rehashed_receipt_counts_must_match_the_exact_base(field, wrong):
    module = codec()
    rows, base, receipt = fixture(1)
    candidate = module.convert_candidate(base, rows, raw_audit_receipt=receipt)
    receipt = copy.deepcopy(receipt)
    receipt[field] = wrong
    manifest = artifacts._json(candidate['numeric-v2.json'])
    manifest['raw_audit'] = descriptor('raw-audit.json', memory.canonical_bytes(receipt))
    candidate['numeric-v2.json'] = memory.canonical_bytes(manifest)
    with pytest.raises(ValueError, match='count'):
        module.read_numeric_compact(candidate, raw_audit_receipt=receipt)


def test_numpy_timing_scalars_are_exact_but_python_values_are_not_coerced():
    module = codec()
    rows, base, receipt = fixture(1)
    rows[0]['latency'] = np.float64(-0.0)
    rows[0]['step_latency'] = np.float64(-0.0)
    candidate = module.convert_candidate(base, rows, raw_audit_receipt=receipt)
    read = module.read_numeric_compact(candidate, raw_audit_receipt=receipt)
    assert read['rows'][0]['latency'].tobytes() == np.float64(-0.0).tobytes()
    for field in FIELDS:
        invalid = [dict(rows[0])]
        invalid[0][field] = rows[0][field].tolist()
        with pytest.raises(ValueError, match=field):
            module.convert_candidate(base, invalid, raw_audit_receipt=receipt)


def test_raw_audit_declaration_has_its_original_canonical_byte_bound():
    module = codec()
    rows, base, receipt = fixture(1)
    receipt['policy_result']['bindings_sha256'] = 'f' * (1024**2 + 1)
    with pytest.raises(ValueError, match='[Rr]aw-audit.*bound'):
        module.convert_candidate(base, rows, raw_audit_receipt=receipt)
