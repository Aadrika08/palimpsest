"""Pure composite numeric codec; source custody/admission is a separate caller.

The V1 base is immutable. Three mandatory arrays supplement every partition.
Declared provenance and stored-byte equality grant no qualification authority.
"""
from __future__ import annotations

import copy
import hashlib
import io
import math
from pathlib import Path
import zipfile

from palimpsest import artifacts, memory
from scripts import memory_family_compact_v4 as compact

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / 'docs/plans/memory-family-numeric-compact-v2-protocol.json'
NUMERIC_FIELDS = {'latency': ('<f8', ()), 'step_latency': ('<f8', ()),
                  'population_stats': ('<f8', (3, 4))}
DENSE_BYTES_PER_ROW = 19_646
ENVELOPE_FIELDS = {
    'schema', 'recording_format', 'protocol', 'base_protocol', 'run_id', 'case_id',
    'operation', 'condition', 'row_count', 'chunk_count', 'first_tick', 'last_tick',
    'base_manifest', 'base_files', 'numeric_index', 'raw_audit', 'source_identity',
    'population', 'claims',
}
ENTRY_FIELDS = {'index', 'base_chunk', 'companion', 'arrays'}
IDENTITY_FIELDS = ('run_id', 'case_id', 'operation', 'condition', 'row_count',
                   'chunk_count', 'first_tick', 'last_tick')
BASE_PROTOCOL = compact._descriptor(
    compact.PROTOCOL_PATH.relative_to(ROOT).as_posix(), compact.PROTOCOL_BYTES)


def _schema():
    return {name: {'dtype': dtype, 'shape': list(shape)}
            for name, (dtype, shape) in NUMERIC_FIELDS.items()}


def validate_protocol(value):
    if type(value) is not dict or memory.canonical_bytes(value) != PROTOCOL_BYTES:
        raise ValueError('Numeric protocol differs from the frozen contract')
    if (value['schema'] != 'memory-family-numeric-compact-protocol-v2'
            or value['recording_format'] != 'palimpsest-family-numeric-compact-v2'
            or value['base_protocol'] != BASE_PROTOCOL
            or value['row'] != {'bytes_per_tick': DENSE_BYTES_PER_ROW,
                               'additional_bytes_per_tick': 112, 'additional_fields': _schema()}
            or value['schemas'] != {'envelope_keys': sorted(ENVELOPE_FIELDS),
                                   'index_keys': ['chunks', 'schema'],
                                   'entry_keys': sorted(ENTRY_FIELDS)}
            or memory.canonical_bytes(value['claims'])
            != memory.canonical_bytes(compact.PROTOCOL['claims'])):
        raise ValueError('Invalid numeric protocol semantics')
    return copy.deepcopy(value)


def validate_limits(operation, *, row_count, total_bytes, overhead_bytes):
    """One combined overhead envelope; SNP has its own enclosing-stage domain."""
    compact.validate_read_limits(operation, row_count=row_count,
        total_bytes=total_bytes, overhead_bytes=overhead_bytes)


def _receipt(receipt):
    # The unchanged reader checks receipt schema/identity; this binds its exact
    # canonical declaration, not publication or truth of its raw provenance.
    compact._fields(receipt, compact.PROTOCOL['schemas']['raw_audit']['exact_keys'],
                    'Numeric raw-audit declaration')
    source = receipt['source_identity']
    compact._fields(source, compact.PROTOCOL['raw_audit']['nested_schemas']
                    ['source_identity']['exact_keys'], 'Numeric source identity')
    compact._digest(source['owner_source_sha256'], 'owner source identity')
    expected = {'schema': 'memory-family-raw-audit-source-v1',
                'protocol': BASE_PROTOCOL,
                'owner_source_sha256': source['owner_source_sha256'],
                'behavior_sources': compact.PROTOCOL['behavior_sources'],
                'behavior_sources_sha256': memory.sha256(compact.PROTOCOL['behavior_sources'])}
    if memory.canonical_bytes(source) != memory.canonical_bytes(expected):
        raise ValueError('Numeric source provenance differs')
    payload = memory.canonical_bytes(receipt)
    if len(payload) > compact.PROTOCOL['raw_audit']['receipt_max_bytes']:
        raise ValueError('Raw-audit declaration exceeds its canonical byte bound')
    return compact._descriptor('raw-audit.json', payload)


def _numeric_array(value, dtype, shape, label):
    import numpy as np
    # Do not infer a dtype by accepting Python lists/scalars or cast any input.
    if not isinstance(value, (np.ndarray, np.generic)):
        raise ValueError(f'Invalid numeric {label}')
    if (value.dtype.str != dtype or value.shape != shape
            or not np.isfinite(value).all()):
        raise ValueError(f'Invalid numeric {label}')
    return value


def _eligible_rows(rows, base):
    if type(rows) is not list or len(rows) != len(base['rows']):
        raise ValueError('Numeric raw row count differs')
    for raw, row in zip(rows, base['rows']):
        compact._fields(raw, compact.RAW_FIELDS, 'Numeric raw row')
        if (type(raw['episode']) is not int or type(raw['tick']) is not int
                or (raw['episode'], raw['tick']) != (row['episode'], row['tick'])):
            raise ValueError('Numeric raw row interval differs')
        for name, (dtype, shape) in NUMERIC_FIELDS.items():
            _numeric_array(raw[name], dtype, shape, f'{name} at tick {row["tick"]}')


def extract_base_bundle(bundle):
    """Extract explicit V1 bytes; callers must still validate the V2 envelope."""
    if type(bundle) is not dict or any(
            type(path) is not str or type(payload) is not bytes
            for path, payload in bundle.items()):
        raise ValueError('Invalid numeric bundle')
    return {path[len('base/'):]: payload for path, payload in bundle.items()
            if path.startswith('base/')}


def convert_candidate(base_bundle, raw_rows, *, raw_audit_receipt):
    """Encode decoded eligible rows, without publication or source authority."""
    import numpy as np
    base = compact.read_compact(base_bundle, raw_audit_receipt=raw_audit_receipt)
    _eligible_rows(raw_rows, base)
    raw_descriptor = _receipt(raw_audit_receipt)
    bundle = {f'base/{path}': payload for path, payload in base_bundle.items()}
    base_index = compact._canonical(base_bundle['chunk-index.json'], 'Base chunk index')
    entries, cursor = [], 0
    for entry in base_index['chunks']:
        count = entry['count']
        path = f'numeric/{entry["index"]:06d}.npz'
        payload = compact._npz({name: np.stack([row[name] for row in
            raw_rows[cursor:cursor + count]]) for name in NUMERIC_FIELDS})
        bundle[path] = payload
        entries.append({'index': entry['index'], 'base_chunk': copy.deepcopy(entry),
                        'companion': compact._descriptor(path, payload), 'arrays': _schema()})
        cursor += count
    index = {'schema': 'memory-family-numeric-chunk-index-v2', 'chunks': entries}
    bundle['numeric-index.json'] = memory.canonical_bytes(index)
    manifest = {
        'schema': 'memory-family-numeric-manifest-v2',
        'recording_format': PROTOCOL['recording_format'],
        'protocol': compact._descriptor(PROTOCOL_PATH.relative_to(ROOT).as_posix(), PROTOCOL_BYTES),
        'base_protocol': copy.deepcopy(BASE_PROTOCOL),
        **{name: base['manifest'][name] for name in IDENTITY_FIELDS},
        'base_manifest': compact._descriptor('base/manifest.json', base_bundle['manifest.json']),
        'base_files': [compact._descriptor(f'base/{path}', base_bundle[path])
                       for path in sorted(base_bundle)],
        'numeric_index': compact._descriptor('numeric-index.json', bundle['numeric-index.json']),
        'raw_audit': raw_descriptor,
        'source_identity': copy.deepcopy(raw_audit_receipt['source_identity']),
        'population': copy.deepcopy(PROTOCOL['population']),
        'claims': copy.deepcopy(PROTOCOL['claims']),
    }
    bundle['numeric-v2.json'] = memory.canonical_bytes(manifest)
    read_numeric_compact(bundle, raw_audit_receipt=raw_audit_receipt)
    return bundle


def _read_numeric_npz(payload, count):
    import numpy as np
    # Validate declared dimensions before NumPy can allocate from an NPY header.
    if (type(payload) is not bytes or type(count) is not int
            or not 1 <= count <= compact.CHUNK_ROWS):
        raise ValueError('Invalid numeric companion size/count')
    maximum = count * 112 + 4096
    if len(payload) > maximum:
        raise ValueError('Invalid numeric companion size/count')
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            expected = {f'{name}.npy' for name in NUMERIC_FIELDS}
            if (len(members) != len(expected)
                    or {member.filename for member in members} != expected
                    or archive.comment
                    or any(member.compress_type != zipfile.ZIP_STORED
                           or member.comment or member.flag_bits for member in members)):
                raise ValueError('Invalid numeric companion archive metadata')
            for member in members:
                dtype, shape = NUMERIC_FIELDS[member.filename[:-4]]
                expected_size = 128 + count * math.prod(shape) * np.dtype(dtype).itemsize
                if member.file_size != expected_size:
                    raise ValueError('Invalid numeric companion NPY size')
                stream = io.BytesIO(archive.read(member))
                if np.lib.format.read_magic(stream) != (1, 0):
                    raise ValueError('Invalid numeric companion NPY version')
                actual_shape, fortran, actual_dtype = np.lib.format.read_array_header_1_0(stream)
                if (actual_shape != (count, *shape) or fortran
                        or actual_dtype.str != dtype or stream.tell() != 128):
                    raise ValueError('Invalid numeric companion NPY schema')
        result = compact._read_npz(payload, NUMERIC_FIELDS, count, 'numeric companion')
        if compact._npz(result) != payload:
            raise ValueError('Invalid noncanonical numeric companion serialization')
        return result
    except (OSError, ValueError, zipfile.BadZipFile, EOFError, TypeError, AttributeError) as error:
        if isinstance(error, ValueError) and str(error).startswith('Invalid '):
            raise
        raise ValueError('Invalid numeric companion archive') from error


def _scope(*, compared=False, rows=0):
    return {'raw_comparison_performed': compared, 'rows_checked': rows,
            'actual_source_qualified': False, 'condition_qualified': False,
            'model_replay_performed': False, 'physics_replay_performed': False,
            'full_pixel_replay': False, 'stage_peak_accounted': False,
            'evidence': ('stored-fields-compared-to-supplied-raw' if compared
                         else 'declared-provenance-codec-only')}


def _ledger(bundle, base, external_overhead_bytes):
    if type(external_overhead_bytes) is not int or external_overhead_bytes < 0:
        raise ValueError('Invalid external combined overhead bytes')
    dense = len(base['rows']) * DENSE_BYTES_PER_ROW
    pixels = len(base['selected_frames']) * 98_304
    events = len(base['legacy_events_bytes'])
    total = sum(map(len, bundle.values())) + external_overhead_bytes
    overhead = total - dense - pixels - events
    validate_limits(base['manifest']['operation'], row_count=len(base['rows']),
                    total_bytes=total, overhead_bytes=overhead)
    return {'recording_bytes': total, 'bundle_bytes': total - external_overhead_bytes,
            'dense_bytes': dense, 'selected_pixel_bytes': pixels, 'event_bytes': events,
            'overhead_bytes': overhead, 'external_overhead_bytes': external_overhead_bytes,
            'stage_peak_accounted': False, 'snapshot_accounted': False}


def read_numeric_compact(bundle, *, raw_audit_receipt):
    """Strictly read every partition; no fallback or raw truth authentication."""
    base_bundle = extract_base_bundle(bundle)
    if 'numeric-v2.json' not in bundle or 'numeric-index.json' not in bundle:
        raise ValueError('Numeric V2 envelope/companions are mandatory')
    if len(bundle['numeric-v2.json']) > compact.MiB or len(bundle['numeric-index.json']) > compact.MiB:
        raise ValueError('Numeric metadata exceeds its bound')
    manifest = compact._canonical(bundle['numeric-v2.json'], 'Numeric manifest')
    compact._fields(manifest, ENVELOPE_FIELDS, 'Numeric manifest')
    expected_protocol = compact._descriptor(PROTOCOL_PATH.relative_to(ROOT).as_posix(), PROTOCOL_BYTES)
    if (manifest['schema'] != 'memory-family-numeric-manifest-v2'
            or manifest['recording_format'] != PROTOCOL['recording_format']
            or manifest['protocol'] != expected_protocol
            or manifest['base_protocol'] != BASE_PROTOCOL
            or memory.canonical_bytes(manifest['population']) != memory.canonical_bytes(PROTOCOL['population'])
            or memory.canonical_bytes(manifest['claims']) != memory.canonical_bytes(PROTOCOL['claims'])
            or manifest['raw_audit'] != _receipt(raw_audit_receipt)
            or memory.canonical_bytes(manifest['source_identity'])
            != memory.canonical_bytes(raw_audit_receipt['source_identity'])):
        raise ValueError('Numeric envelope contract/provenance differs')
    base = compact.read_compact(base_bundle, raw_audit_receipt=raw_audit_receipt)
    for name in ('row_count', 'chunk_count', 'event_count'):
        if (type(raw_audit_receipt[name]) is not int
                or raw_audit_receipt[name] != base['manifest'][name]):
            raise ValueError(f'Numeric raw-audit count differs: {name}')
    for name in IDENTITY_FIELDS:
        if (type(manifest[name]) is not type(base['manifest'][name])
                or manifest[name] != base['manifest'][name]):
            raise ValueError(f'Numeric base identity differs: {name}')
    compact._check_descriptor(manifest['base_manifest'], 'base/manifest.json', base_bundle['manifest.json'])
    expected_files = [compact._descriptor(f'base/{path}', base_bundle[path]) for path in sorted(base_bundle)]
    if memory.canonical_bytes(manifest['base_files']) != memory.canonical_bytes(expected_files):
        raise ValueError('Numeric base file descriptors differ')
    compact._check_descriptor(manifest['numeric_index'], 'numeric-index.json', bundle['numeric-index.json'])
    index = compact._canonical(bundle['numeric-index.json'], 'Numeric index')
    compact._fields(index, {'schema', 'chunks'}, 'Numeric index')
    if (index['schema'] != 'memory-family-numeric-chunk-index-v2'
            or type(index['chunks']) is not list or len(index['chunks']) != manifest['chunk_count']):
        raise ValueError('Numeric chunk ledger differs')
    expected_paths = {'numeric-v2.json', 'numeric-index.json',
                      *(f'base/{path}' for path in base_bundle),
                      *(f'numeric/{i:06d}.npz' for i in range(manifest['chunk_count']))}
    if set(bundle) != expected_paths:
        raise ValueError('Numeric companions/files are not bijective')
    base_index = compact._canonical(base_bundle['chunk-index.json'], 'Base chunk index')
    rows, cursor = [], 0
    for position, (entry, old) in enumerate(zip(index['chunks'], base_index['chunks'])):
        compact._fields(entry, ENTRY_FIELDS, 'Numeric chunk entry')
        if (type(entry['index']) is not int or entry['index'] != position
                or memory.canonical_bytes(entry['base_chunk']) != memory.canonical_bytes(old)
                or memory.canonical_bytes(entry['arrays']) != memory.canonical_bytes(_schema())):
            raise ValueError('Numeric chunk correspondence differs')
        path = f'numeric/{position:06d}.npz'
        compact._check_descriptor(entry['companion'], path, bundle[path])
        arrays = _read_numeric_npz(bundle[path], old['count'])
        for offset in range(old['count']):
            rows.append({**base['rows'][cursor + offset],
                         **{name: array[offset].copy() for name, array in arrays.items()}})
        cursor += old['count']
    ledger = _ledger(bundle, base, 0)
    return {**base, 'base_manifest': base['manifest'], 'manifest': copy.deepcopy(manifest),
            'rows': rows, 'byte_ledger': ledger, 'preservation': _scope()}


def account_candidate(bundle, *, raw_audit_receipt, external_overhead_bytes=0):
    """Charge actual bundle bytes plus explicitly supplied unique external costs.

    The public source caller must supply all receipts/support/control/markers and
    atomic metadata; raw and the sole SNP belong to its separate stage ledger.
    """
    read = read_numeric_compact(bundle, raw_audit_receipt=raw_audit_receipt)
    base = {**read, 'manifest': read['base_manifest']}
    return _ledger(bundle, base, external_overhead_bytes)


def prove_numeric_preservation(raw_data, bundle, receipt):
    """Preserve every V1 proof and compare each new field at every supplied tick."""
    from scripts import memory_family_producer_v4 as producer
    # First retain the complete legacy independent commitments/oracle/byte proof.
    producer._prove(raw_data, extract_base_bundle(bundle), receipt)
    read = read_numeric_compact(bundle, raw_audit_receipt=receipt)
    _eligible_rows(raw_data['rows'], read)
    for raw, restored in zip(raw_data['rows'], read['rows']):
        for name in NUMERIC_FIELDS:
            left, right = raw[name], restored[name]
            if (left.dtype.str != right.dtype.str or left.shape != right.shape
                    or left.tobytes() != right.tobytes()):
                raise ValueError(f'Raw-to-numeric value differs: {name} at tick {raw["tick"]}')
    read['preservation'] = _scope(compared=True, rows=len(read['rows']))
    return read


PROTOCOL_BYTES = artifacts._read(PROTOCOL_PATH, compact.MiB)
PROTOCOL = compact._canonical(PROTOCOL_BYTES, 'Numeric protocol')
PROTOCOL_SHA256 = hashlib.sha256(PROTOCOL_BYTES).hexdigest()
validate_protocol(PROTOCOL)
