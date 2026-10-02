"""Fixed MuJoCo 3.3.6/layout-5990 byte comparison, not a native serializer.

The caller supplies the reviewed hash-pinned v4 protocol. No native object is
loaded, modified, normalized or restored here; full input bytes remain evidence.
"""
import hashlib
import platform
import struct
import sys


def _admit(data, contract):
    abi = {'machine': 'x86_64', 'byte_order': 'little', 'pointer_bytes': 8,
           'int_bytes': 4, 'mjt_num_bytes': 8}
    if (contract['kind'] != 'mujoco-3.3.6-puck-5990-v4' or contract['abi'] != abi
            or platform.machine() != 'x86_64' or sys.byteorder != 'little'
            or (struct.calcsize('P'), struct.calcsize('i'), struct.calcsize('d')) != (8, 4, 8)
            or struct.calcsize('@65d13i0d') != 576):
        raise ValueError('Unsupported fixed construction format/ABI')
    if (type(data) is not bytes or len(data) != contract['data_bytes'] or len(data) != 347881
            or contract['model_bytes'] != 119898 or contract['data_version'] != 1
            or data[0] != 1):
        raise ValueError('Wrong fixed native container length/version')
    if hashlib.sha256(data[1:119899]).hexdigest() != contract['model_sha256']:
        raise ValueError('Embedded native model differs from reviewed pin')
    layout = contract['fields']
    if type(layout) is not list or len(layout) != 162:
        raise ValueError('Fixed 162-field layout required')
    fields, cursor = {}, 119899
    for row in layout:
        if (type(row) is not list or len(row) != 3 or type(row[0]) is not str
                or row[0] in fields or type(row[1]) is not int or type(row[2]) is not int):
            raise ValueError('Malformed fixed field layout')
        name, start, size = row
        if start != cursor+8 or size < 0 or start+size > len(data):
            raise ValueError('Noncontiguous/out-of-bounds fixed layout')
        if struct.unpack_from('<Q', data, cursor)[0] != size:
            raise ValueError('Native size-prefix mismatch: ' + name)
        fields[name] = (start, start+size)
        cursor = start+size
    if cursor != len(data):
        raise ValueError('Unexpected bytes after fixed field layout')

    def integers(name):
        start, end = fields[name]
        if (end-start) % 4 or end-start > 440:
            raise ValueError('Wrong fixed integer array size')
        return list(struct.unpack('<'+'i'*((end-start)//4), data[start:end]))

    expected = {'ncon': 6, 'ne': 0, 'nf': 0, 'nJ': 176, 'nA': 0,
                'nefc': 24, 'nisland': 1, 'nidof': 10}
    if contract['dimensions'] != expected or any(integers(k) != [v] for k, v in expected.items()):
        raise ValueError('Wrong fixed contact/solver/island dimensions')
    rownnz, rowadr = integers('iM_rownnz'), integers('iM_rowadr')
    active = 0
    if len(rownnz) != 10 or len(rowadr) != 10:
        raise ValueError('Wrong island row count')
    for count, address in zip(rownnz, rowadr):
        if count <= 0 or address != active or active+count > 110:
            raise ValueError('Invalid contiguous sparse extent')
        active += count
    frozen = contract['sparse_rows']
    if (active != 50 or frozen != {'rownnz': rownnz, 'rowadr': rowadr,
                                  'active_entries': active, 'allocated_entries': 110}):
        raise ValueError('Sparse extent differs from fixed construction rows')

    ranges = []
    start, end = fields['timer']
    if end-start != 15*16:
        raise ValueError('Wrong timer struct layout')
    ranges += [(start+i*16, start+i*16+8, 'timer.duration') for i in range(15)]
    start, end = fields['contact']
    if end-start != 6*576:
        raise ValueError('Wrong contact struct layout')
    ranges += [(start+i*576+572, start+(i+1)*576, 'contact.tail_padding') for i in range(6)]
    for name, item_bytes in [('iM_colind', 4), ('iM', 8), ('iLD', 8)]:
        start, end = fields[name]
        if end-start != 110*item_bytes:
            raise ValueError('Wrong sparse allocation capacity: ' + name)
        ranges.append((start+active*item_bytes, end, name+'.unused_tail'))
    ranges.sort()
    if (sum(end-start for start, end, _ in ranges) != 1344 or contract['excluded_bytes'] != 1344
            or any(a[1] > b[0] for a, b in zip(ranges, ranges[1:]))):
        raise ValueError('Fixed exclusions overlap or exceed declared extent')
    return ranges


def compare_native_data(left, right, contract):
    """Compare every byte except the three exact source-mapped region types."""
    ranges = _admit(left, contract)
    if ranges != _admit(right, contract):
        raise ValueError('Owner exclusion extents differ')
    cursor, differences, defined_hash = 0, 0, hashlib.sha256()
    excluded = []
    for start, end, reason in [*ranges, (len(left), len(left), 'end')]:
        if left[cursor:start] != right[cursor:start]:
            raise ValueError(f'Defined native bytes differ in [{cursor}, {start})')
        defined_hash.update(left[cursor:start])
        if reason != 'end':
            count = sum(a != b for a, b in zip(left[start:end], right[start:end]))
            differences += count
            excluded.append({'start': start, 'end': end, 'reason': reason, 'different_bytes': count})
        cursor = end
    return {'kind': contract['kind'], 'defined_native_bytes_equal': True,
            'raw_native_bytes_equal': left == right,
            'raw_sha256': [hashlib.sha256(raw).hexdigest() for raw in (left, right)],
            'defined_bytes_sha256': defined_hash.hexdigest(), 'compared_bytes': len(left)-1344,
            'excluded_bytes': 1344, 'different_excluded_bytes': differences, 'exclusions': excluded}
