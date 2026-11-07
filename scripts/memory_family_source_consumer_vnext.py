"""Fixed private AUTHORED source custody; no actual admission or Engine API.

All producer declarations remain authored premises. This module only decodes
and checks bounded files/values while holding their original descriptor edges.
Opaque native bytes are never restored. A lease is one source and one slot.
"""
from __future__ import annotations

import copy
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
import hashlib
import io
import math
import os
from pathlib import Path
import re
import stat
import struct
import threading
import time
import zipfile

import numpy as np

from palimpsest import artifacts, memory, snapshots
from palimpsest import memory_decision_world as world, memory_transition_vnext as transition
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_numeric_preservation_v2 as numeric
from scripts import memory_family_replay_custody_v4 as custody
from scripts import memory_family_terminal_audit_vnext as audit
from scripts import memory_family_terminal_numeric_vnext as codec

_MIB = 1024 ** 2
_TOKEN = object()
_CLAIMS = dict.fromkeys(('actual_acceptance', 'source_qualified', 'model_qualified',
    'allocation_authorized', 'publication_authorized', 'go_authorized'), False)
_REQUIREMENTS = sorted(('src/palimpsest/memory_transition_vnext.py', 'src/palimpsest/snapshots.py',
    'scripts/memory_family_replay_custody_v4.py', 'scripts/memory_family_compact_v4.py',
    'scripts/memory_family_numeric_preservation_v2.py', 'scripts/memory_family_terminal_audit_vnext.py',
    'scripts/memory_family_terminal_numeric_vnext.py'))
_RAW_SCHEMA = {'episode': ('<i8', ()), 'tick': ('<i8', ()), **codec.RAW_ARRAYS}
_ADMISSION_FIELDS = ('schema profile source_closure producer_registration source_commit source_raw_audit '
    'source_snapshot source_numeric_conversion source_numeric_commit case_id case_sha256 source_run_id '
    'condition_slot namespace inventory claims').split()


def _require(value, message):
    if not value:
        raise ValueError(message)


def _same(left, right):
    _require(memory.canonical_bytes(left) == memory.canonical_bytes(right), 'Authored source binding differs')


def _fields(value, fields):
    compact._fields(value, fields, 'Authored source')


def _integer(value, low, high):
    _require(type(value) is int and low <= value <= high, 'Invalid authored exact integer')
    return value


def _schema(middle):
    return f'memory-source-authored-{middle}-vnext-v1'


def _json(payload, *, canonical=True, depth=32):
    value = artifacts._json(payload)
    def bound(node, level=0):
        _require(level <= depth, 'Authored JSON nesting exceeds bound')
        if type(node) is dict:
            for child in node.values(): bound(child, level+1)
        elif type(node) is list:
            for child in node: bound(child, level+1)
    bound(value)
    if canonical:
        _same_bytes = memory.canonical_bytes(value)
        _require(_same_bytes == payload, 'Authored JSON bytes are not canonical')
    return value


def _record(payload, middle, fields):
    value = _json(payload)
    _fields(value, fields)
    _same(value['schema'], _schema(middle))
    _same(value['claims'], _CLAIMS)
    return value


def _npz_cap(schema, count):
    # np.savez uses a 20-byte ZIP64 local extra and a 128-byte NPY1 header.
    # Compute from the fixed schema, never from the incoming NPY header.
    return 22 + sum(128 + count * math.prod(shape) * np.dtype(dtype).itemsize
        + 30 + 20 + 46 + 2 * len((name+'.npy').encode('ascii'))
        for name, (dtype, shape) in schema.items())


def _enter(stack, manager, failures):
    value = manager.__enter__()
    def leave(kind, error, traceback):
        try:
            manager.__exit__(kind, error, traceback)
        except BaseException as failure:
            failures.append(failure)
        return False
    stack.push(leave)
    return value


def _bounded_payload(files, path, maximum, check):
    check()
    owned = files.fd_path(path)
    value = bytearray()
    with owned.open('rb') as stream:
        while True:
            block = stream.read(min(_MIB, maximum + 1 - len(value)))
            if not block: break
            value.extend(block)
            _require(len(value) <= maximum, 'Authored payload exceeds fixed pre-read cap')
    check()
    return bytes(value)


def _snapshot_preflight(path):
    """Bound archive expansion and exact typed metadata before the SNP decoder."""
    with path.open('rb') as stream:
        stream.seek(0, os.SEEK_END)
        physical = stream.tell()
        _require(22 <= physical <= 16*_MIB, 'Authored SNP physical bound exceeded')
        stream.seek(-22, os.SEEK_END)
        end = struct.unpack('<4s4H2LH', stream.read(22))
        _require(end[0] == b'PK\x05\x06' and end[1] == end[2] == end[7] == 0
            and end[3] == end[4] and end[5]+end[6]+22 == physical,
            'Authored SNP trailing or noncanonical ZIP end')
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        names = [m.filename for m in members]
        _require(1 <= len(members) <= 8192 and len(set(names)) == len(names)
            and not archive.comment and sum(m.file_size for m in members) <= 16*_MIB,
            'Authored SNP archive expansion or entry bound exceeded')
        _require('metadata.json' in names and archive.getinfo('metadata.json').file_size <= 8*_MIB,
            'Missing or oversized authored SNP metadata')
        for member in members:
            _require(member.compress_type == zipfile.ZIP_STORED and not member.flag_bits
                and not member.comment, 'Invalid authored SNP ZIP metadata')
        state_names = set(names) - {'metadata.json'}
        indices = []
        for name in state_names:
            match = re.fullmatch(r'state/(0|[1-9][0-9]*)\.(npy|bin)', name, re.ASCII)
            _require(match is not None, 'Invalid authored SNP member path')
            indices.append(int(match.group(1)))
        _require(sorted(indices) == list(range(len(state_names))), 'Noncontiguous authored SNP members')
        metadata = _json(archive.read('metadata.json'), canonical=False, depth=64)
        _fields(metadata, ('format', 'schema_version', 'container'))
        _same(metadata['format'], 'palimpsest.snapshot')
        _integer(metadata['schema_version'], snapshots.SCHEMA_VERSION, snapshots.SCHEMA_VERSION)
        used = set()
        nodes = 0
        def walk(node, depth=0):
            nonlocal nodes
            nodes += 1
            _require(depth <= 64 and nodes <= 512*1024, 'Authored SNP typed metadata bound exceeded')
            if type(node) is not dict:
                _require(node is None or type(node) in (str, int, bool, float), 'Invalid authored SNP node')
                return
            kind = node.get('kind')
            if kind in ('array', 'scalar', 'bytes'):
                _fields(node, ('kind', 'entry', 'size', 'sha256'))
                name = node['entry']
                _require(type(name) is str and name in state_names and name not in used,
                    'Invalid or duplicate authored SNP entry reference')
                _require(name.endswith('.bin' if kind=='bytes' else '.npy'), 'Authored SNP entry kind differs')
                _integer(node['size'], 0, 16*_MIB)
                _require(archive.getinfo(name).file_size == node['size'], 'Authored SNP entry size differs')
                memory._digest(node['sha256'])
                used.add(name)
            elif kind in ('dict', 'list', 'tuple', 'set'):
                _fields(node, ('kind', 'items'))
                _require(type(node['items']) is list, 'Invalid authored SNP items')
                if kind == 'dict':
                    keys = set()
                    for pair in node['items']:
                        _require(type(pair) is list and len(pair)==2 and type(pair[0]) is str
                            and pair[0] not in keys, 'Invalid authored SNP dictionary')
                        keys.add(pair[0]); walk(pair[1], depth+1)
                else:
                    for child in node['items']: walk(child, depth+1)
            else:
                raise ValueError('Unknown authored SNP typed node')
        walk(metadata['container'])
        _require(used == state_names, 'Authored SNP references are not bijective')


def _decoded_snapshot(value):
    size = nodes = 0
    def bound(node, depth=0):
        nonlocal size, nodes
        nodes += 1
        _require(depth <= 64 and nodes <= 512*1024, 'Authored SNP typed value bound exceeded')
        if type(node) is np.ndarray or type(node) in (np.bool_, np.uint8, np.int8, np.int16,
                np.uint16, np.int32, np.uint32, np.int64, np.uint64, np.float32, np.float64):
            _require(node.dtype.kind in 'buif' and node.dtype.fields is None and node.ndim <= 8
                and np.isfinite(node).all(), 'Invalid authored SNP array')
            size += node.nbytes + 64
        elif type(node) in (str, bytes): size += len(node.encode() if type(node) is str else node)+8
        elif type(node) is dict:
            for key, child in node.items():
                _require(type(key) is str, 'Invalid authored SNP key')
                bound(key, depth+1); bound(child, depth+1)
        elif type(node) in (list, tuple, set):
            size += 8
            for child in node: bound(child, depth+1)
        elif node is None or type(node) in (bool, int, float):
            _require(not (type(node) is float and not math.isfinite(node))
                and not (type(node) is int and node.bit_length()>256), 'Invalid authored SNP scalar')
            size += 16
        else: raise ValueError('Unsupported authored SNP value')
        _require(size <= 16*_MIB, 'Authored SNP typed bytes exceed bound')
    bound(value)
    _fields(value, ('schema', 'application', 'native_data', 'native_sha256', 'claims'))
    _same(value['schema'], _schema('snapshot')); _same(value['claims'], _CLAIMS)
    _require(type(value['native_data']) is bytes and bool(value['native_data'])
        and hashlib.sha256(value['native_data']).hexdigest() == value['native_sha256'],
        'Invalid authored opaque native bytes')
    return value


@dataclass(frozen=True)
class _DecodedSource:
    case: dict
    application: dict
    world: dict
    m: dict
    snapshot_reference: dict
    events: list
    rows: list
    snapshot: dict


class HeldSourceVnext:
    """A permanently bound private lease; returned copies are detached data."""
    __slots__ = ('_stack', '_files', '_deadline', '_thread', '_admission', '_context',
        '_source', '_binding', '_checks', '_state')

    def __init__(self, _token, *, stack, files, deadline, owner_thread, admission, context, source):
        _require(_token is _TOKEN and type(stack) is ExitStack and type(files) is custody.HeldReplayFiles
            and type(source) is _DecodedSource, 'Fixed private authored constructor required')
        self._stack, self._files = stack, files
        self._deadline, self._thread = deadline, owner_thread
        self._admission = copy.deepcopy(admission)
        self._context = transition.validate_context_vnext(context)
        self._source = copy.deepcopy(source)
        self._binding = self._fingerprint()
        self._checks = ()
        self._state = 'active'

    def _fingerprint(self):
        return snapshots.state_digest({'admission': self._admission, 'context': self._context,
            'source': {name: getattr(self._source, name) for name in _DecodedSource.__dataclass_fields__}})

    def recheck(self):
        try:
            if self._state != 'active': raise RuntimeError('Authored source is poisoned or closed')
            if threading.get_ident() != self._thread: raise RuntimeError('Authored source belongs to its creating thread')
            if time.monotonic() >= self._deadline: raise TimeoutError('Authored source lease expired')
            self._files.recheck()
            for check in self._checks: check()
            if self._fingerprint() != self._binding:
                raise RuntimeError('Authored immutable Context/source binding changed')
        except BaseException:
            if self._state != 'closed': self._state = 'poisoned'
            raise

    def _get(self, name):
        self.recheck()
        return copy.deepcopy(self._context if name=='context' else getattr(self._source, name))

    @property
    def context(self): return self._get('context')
    @property
    def case(self): return self._get('case')
    @property
    def source_application(self): return self._get('application')
    @property
    def source_world(self): return self._get('world')
    @property
    def source_m(self): return self._get('m')
    @property
    def source_snapshot_reference(self): return self._get('snapshot_reference')
    @property
    def _source_events(self): return self._get('events')
    @property
    def _source_rows(self): return self._get('rows')
    @property
    def _source_snapshot(self): return self._get('snapshot')


def _topology(root):
    expected = {'': {'inputs', 'outputs'}, 'outputs': {'condition'},
        'outputs/condition': {'work', 'atomic', 'quarantine'},
        **{f'outputs/condition/{name}': set() for name in ('work', 'atomic', 'quarantine')}}
    for relative, names in expected.items():
        path = root / relative
        _require(stat.S_ISDIR(path.lstat().st_mode), 'Authored output directory is not plain')
        with os.scandir(path) as entries:
            _require({e.name for e in entries} == names, 'Authored initial root/output topology differs')


@contextmanager
def _held_output_edges(root, namespace, deadline, failures):
    """Fixed output ancestors, with child-mutable precreated branch edges only."""
    fds, ancestors, branches = [], [], []
    def clock():
        if time.monotonic() >= deadline:
            raise TimeoutError('Authored output custody deadline exhausted')
    def edge(state):
        return state.st_dev, state.st_ino, state.st_mode, state.st_uid, state.st_gid
    def open_dir(name, parent=None, *, branch=False):
        clock()
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        fds.append(fd)
        identity = edge if branch else custody._identity
        state = os.fstat(fd)
        expected = identity(state)
        _require(expected == identity(os.stat(name, dir_fd=parent, follow_symlinks=False)),
            'Authored output directory edge changed while opening')
        (branches if branch else ancestors).append((fd,parent,name,expected))
        return fd, state
    def check():
        for rows, identity in ((ancestors,custody._identity),(branches,edge)):
            for fd,parent,name,expected in rows:
                clock()
                if (identity(os.fstat(fd)) != expected or
                        identity(os.stat(name,dir_fd=parent,follow_symlinks=False)) != expected):
                    raise RuntimeError('Authored output ancestor or branch edge changed')
        clock()
    try:
        root_fd,state = open_dir(str(root))
        _require(state.st_dev == namespace['device'] and state.st_ino == namespace['inode']
            and state.st_uid == namespace['uid'], 'Authored output root namespace differs')
        outputs,_ = open_dir('outputs',root_fd)
        condition,_ = open_dir('condition',outputs)
        for name in ('work','atomic','quarantine'): open_dir(name,condition,branch=True)
        check()
        yield check
    finally:
        while fds:
            try: os.close(fds.pop())
            except BaseException as error: failures.append(error)


@contextmanager
def _open_authored_source_vnext(root, admission, *, case_id, deadline):
    """The sole factory. All physical paths are derived from fixed records."""
    entered = time.monotonic()
    _require(type(deadline) in (int, float) and math.isfinite(deadline)
        and entered < deadline <= entered+300, 'Invalid authored source deadline')
    _require(type(root) is str and root.startswith(f'/var/tmp/palimpsest-AUTHORED-source-vnext-{os.geteuid()}-'),
        'Invalid authored namespace')
    suffix = root[len(f'/var/tmp/palimpsest-AUTHORED-source-vnext-{os.geteuid()}-'):]
    transition._uuid(suffix)
    _require(type(case_id) is str and compact._PATH_COMPONENT.fullmatch(case_id) is not None,
        'Invalid authored case path')
    root = Path(root)
    stack, failures, checks = ExitStack(), [], []
    primary = holder = None
    try:
        roster, metadata = {}, {}
        metadata_bytes = 0
        def add(role, d, path, maximum):
            transition.validate_descriptor_vnext(d, max_bytes=maximum)
            _require(d['path']==path and d['size_bytes']>0, 'Authored role path or size differs')
            row = {'role': role, 'descriptor': copy.deepcopy(d), 'max_bytes': maximum}
            if role in roster: _same(roster[role], row)
            else:
                _require(path not in {x['descriptor']['path'] for x in roster.values()}, 'Conflicting authored role path')
                roster[role] = row
            return d
        def meta(role, d, path, middle, fields, maximum=_MIB):
            nonlocal metadata_bytes
            add(role, d, path, maximum)
            metadata_bytes += d['size_bytes']
            _require(metadata_bytes <= _MIB, 'Combined authored metadata exceeds one MiB')
            _, payload, check = _enter(stack, compact.bound_payload(root, d, maximum, deadline), failures)
            checks.append(check)
            # The sole inherited profile has pinned original, noncanonical bytes.
            value = _record(payload, middle, fields) if middle else _json(payload, canonical=False)
            metadata[role] = value
            return value
        a = meta('admission', admission, 'inputs/registrations/admission.json', 'admission', _ADMISSION_FIELDS)
        _same(a['case_id'], case_id)
        _fields(a['namespace'], ('schema', 'root', 'uid', 'device', 'inode'))
        state = root.lstat()
        _require(stat.S_ISDIR(state.st_mode) and state.st_uid==os.geteuid(), 'Authored root owner/type differs')
        _same(a['namespace'], {'schema': _schema('namespace'), 'root': str(root), 'uid': os.geteuid(),
            'device': state.st_dev, 'inode': state.st_ino})
        for key in ('uid','device','inode'): _integer(a['namespace'][key], 0, 2**128)
        transition._uuid(a['source_run_id'])
        s = a['source_run_id']
        common = {k: a[k] for k in ('profile','source_closure')}
        meta('profile', a['profile'], 'inputs/meta/profile.json', None, None)
        pin = codec.PROTOCOL['terminal_profile']
        _require(a['profile']['size_bytes']==pin['size_bytes'] and a['profile']['sha256']==pin['sha256'],
            'Authored charged terminal profile copy differs')
        closure = meta('source_closure', a['source_closure'], 'inputs/meta/source-closure.json', 'software-closure',
            ('schema','profile','requirements','claims'))
        _same(closure['profile'], a['profile'])
        _require(type(closure['requirements']) is list and len(closure['requirements'])==7,
            'Authored closure requirement roster differs')
        for d in closure['requirements']:
            transition.validate_descriptor_vnext(d)
            _require(d['size_bytes']>0, 'Empty authored closure subject')
        _same([d['path'] for d in closure['requirements']], _REQUIREMENTS)
        producer = meta('producer_registration', a['producer_registration'], 'inputs/registrations/producer.json',
            'producer-registration', ('schema profile source_closure case source_run_id owner_record worker_report '
                'raw_manifest raw_events raw_audit snapshot claims').split())
        case = world.validate_case(producer['case'])
        _require(case['version']==3 and case['split']=='development', 'Authored source requires development case3')
        ident = {'case_id': case_id, 'source_run_id': s}
        _same(case['case_id'], case_id); _same(memory.sha256(case), a['case_sha256'])
        for k,v in {**common,'source_run_id':s}.items(): _same(producer[k],v)
        b = 'inputs/cases/' + case_id
        snp = add('source_snapshot', producer['snapshot'], b+'/source/snapshots/initial.snp', 16*_MIB)
        _same(snp, a['source_snapshot']); _same(producer['raw_audit'], a['source_raw_audit'])
        _same(a['source_commit'], a['source_numeric_commit'])
        owner = meta('owner_record', producer['owner_record'], b+'/source/owner.json', 'owner',
            ('schema','case_id','source_run_id','snapshot','claims'))
        report = meta('worker_report', producer['worker_report'], b+'/raw/owner-report.json', 'owner-report',
            ('schema','case_id','source_run_id','snapshot','total_ticks','world_state','claims'))
        manifest = meta('raw_manifest', producer['raw_manifest'], b+'/raw/manifest.json', 'raw-manifest',
            ('schema','case_id','source_run_id','row_count','event_count','chunks','claims'))
        n = _integer(manifest['row_count'], 1, 1200)
        p = (n+31)//32
        e = _integer(manifest['event_count'], 1, 50000)
        _integer(report['total_ticks'], n, n)
        for rec in (owner, report, manifest):
            for k,v in ident.items(): _same(rec[k],v)
        for rec in (owner,report): _same(rec['snapshot'], snp)
        add('raw_events', producer['raw_events'], b+'/raw/events.jsonl', 7*_MIB)
        _require(type(manifest['chunks']) is list and len(manifest['chunks'])==p, 'Authored raw partitions differ')
        for i, row in enumerate(manifest['chunks']):
            _fields(row, ('index','start','count','descriptor'))
            for k,v in {'index': i, 'start':32*i, 'count':min(32,n-32*i)}.items(): _integer(row[k],v,v)
            add(f'raw_chunk:{i}', row['descriptor'], f'{b}/raw/chunks/{i:06d}.npz',
                min(512*_MIB,_npz_cap(_RAW_SCHEMA,row['count'])))
        raw_audit = meta('source_raw_audit', a['source_raw_audit'], 'inputs/controls/raw-audit.json', 'raw-audit',
            ('schema profile source_closure case_id case_sha256 source_run_id owner_record worker_report raw_manifest '
                'raw_events snapshot row_count chunk_count event_count recording_bytes camera_sequence_sha256 '
                'row_sequence_sha256 trace_digest claims').split())
        conversion = meta('source_numeric_conversion', a['source_numeric_conversion'], b+'/numeric/conversion.json',
            'numeric-conversion', ('schema profile source_closure case_id source_run_id producer_registration raw_audit '
                'snapshot index audit_frames inventory row_count trace_digest claims').split(), 65536)
        commit = meta('source_numeric_commit', a['source_numeric_commit'], b+'/numeric/commit.json', 'retention-commit',
            ('schema profile source_closure case_id source_run_id conversion status claims').split(), 16384)
        for rec in (raw_audit,conversion,commit):
            for k,v in {**common, **ident}.items(): _same(rec[k],v)
        _same(commit['conversion'], a['source_numeric_conversion']); _same(commit['status'], 'AUTHORED-RETENTION-ONLY')
        for k,v in {'producer_registration':a['producer_registration'], 'raw_audit':a['source_raw_audit'],
                'snapshot':snp,'row_count':n}.items(): _same(conversion[k],v)
        index = meta('numeric_index', conversion['index'], b+'/numeric/index.json', 'numeric-index',
            ('schema','case_id','source_run_id','row_count','chunks','claims'))
        for k,v in {**ident,'row_count':n}.items(): _same(index[k],v)
        _require(type(index['chunks']) is list and len(index['chunks'])==p, 'Authored numeric partitions differ')
        for i,row in enumerate(index['chunks']):
            _fields(row, ('index','start','count','raw','base','extra'))
            for k in ('index','start','count'): _same(row[k],manifest['chunks'][i][k])
            _same(row['raw'],manifest['chunks'][i]['descriptor'])
            for role, schema in (('base',codec.BASE_ARRAYS),('extra',numeric.NUMERIC_FIELDS)):
                add(f'numeric_{role}:{i}', row[role], f'{b}/numeric/{role}/{i:06d}.npz',
                    min(32*_MIB,_npz_cap(schema,row['count'])))
        ticks = compact.audit_ticks(range(n),event_tick=None,decision_tick=None)
        add('audit_frames', conversion['audit_frames'], b+'/numeric/audit-frames.npz',
            min(32*_MIB,_npz_cap(compact.FRAME_FIELDS,len(ticks))))
        _same(conversion['inventory'], sorted([conversion['index'], conversion['audit_frames'],
            *(row[k] for row in index['chunks'] for k in ('base','extra'))],key=lambda d:d['path']))
        _same(a['inventory'], sorted([row for role,row in roster.items() if role!='admission'],
            key=lambda row:row['descriptor']['path']))
        _require(len(roster)==14+3*p, 'Authored physical roster count differs')
        raw_roles = ['raw_manifest','raw_events','worker_report',*(f'raw_chunk:{i}' for i in range(p))]
        raw_bytes = sum(roster[role]['descriptor']['size_bytes'] for role in raw_roles)
        numeric_bytes = sum(row['descriptor']['size_bytes'] for role,row in roster.items()
            if role=='audit_frames' or role.startswith(('numeric_base:', 'numeric_extra:')))
        _require(raw_bytes<=512*_MIB and len(raw_roles)<=42
            and numeric_bytes+producer['raw_events']['size_bytes']+metadata_bytes<=32*_MIB
            and sum(row['descriptor']['size_bytes'] for row in roster.values())<=640*_MIB,
            'Authored aggregate byte/leaf ceiling exceeded')
        for k,v in {**{k:producer[k] for k in ('owner_record','worker_report','raw_manifest','raw_events')},
                'snapshot':snp, 'case_sha256':memory.sha256(case), 'row_count':n,'chunk_count':p,
                'event_count':e,'recording_bytes':raw_bytes}.items(): _same(raw_audit[k],v)
        files = _enter(stack, custody.HeldReplayFiles(root,
            sorted([row['descriptor'] for row in roster.values()],key=lambda d:d['path']),
            deadline,exact_subtrees=('inputs',)),failures)
        def check():
            if time.monotonic()>=deadline: raise TimeoutError('Authored source lease expired')
            files.recheck()
            for c in checks: c()
        check(); _topology(root); check()
        output_check = _enter(stack, _held_output_edges(root,a['namespace'],deadline,failures),failures)
        checks.append(output_check)
        check()
        _require(files.read(admission['path'],_MIB)==memory.canonical_bytes(a), 'Bootstrap/strong admission differs')
        event_bytes = _bounded_payload(files,producer['raw_events']['path'],7*_MIB,check)
        events = []
        for line in event_bytes.splitlines(keepends=True):
            _require(len(line)<=_MIB and len(events)<50000, 'Authored event line/count exceeds bound')
            event = _json(line,canonical=False)
            _require(audit._writer(event)==line, 'Authored event bytes differ from exact writer')
            events.append(event)
        _require(len(events)==e, 'Authored event count differs')
        audit._events(events,s)
        chunks = [event for event in events if event['kind']=='chunk']
        _require(len(chunks)==p, 'Authored chunk event count differs')
        for i,event in enumerate(chunks):
            for k,v in {'episode':0,'start':32*i,'count':min(32,n-32*i),
                    'path':f'chunks/{i:06d}.npz','sha256':manifest['chunks'][i]['descriptor']['sha256']}.items():
                _same(event.get(k),v)
        check()
        snp_path = files.fd_path(snp['path'])
        _snapshot_preflight(snp_path); check()
        snapshot = _decoded_snapshot(snapshots.read_snapshot(files.fd_path(snp['path']))); check()
        application = snapshot['application']
        rows = []
        for i, row in enumerate(manifest['chunks']):
            role = f'raw_chunk:{i}'
            cap = roster[role]['max_bytes']
            payload = _bounded_payload(files,row['descriptor']['path'],cap,check)
            _require(len(payload)==cap, 'Authored raw NPZ exact byte length differs')
            arrays = codec._read_arrays(payload,_RAW_SCHEMA,row['count'],cap,'authored raw'); check()
            for offset in range(row['count']):
                rows.append({name: int(array[offset]) if name in ('episode','tick') else array[offset].copy()
                    for name,array in arrays.items()})
        audit._decoded_rows(rows,1200,512*_MIB)
        projected = compact._project_rows(rows,'source'); check()
        hashes = {'camera_sequence_sha256':compact._sequence_hash(projected,compact.DIGEST_FIELDS[:-1]),
            'row_sequence_sha256':compact._sequence_hash(projected,('row_digest',)),
            'trace_digest':compact._trace_digest(projected)}
        for k,v in hashes.items(): _same(raw_audit[k],v)
        _same(conversion['trace_digest'],hashes['trace_digest'])
        check()
        for i,row in enumerate(index['chunks']):
            for role,schema in (('base',codec.BASE_ARRAYS),('extra',numeric.NUMERIC_FIELDS)):
                cap=roster[f'numeric_{role}:{i}']['max_bytes']
                payload=_bounded_payload(files,row[role]['path'],cap,check)
                _require(len(payload)==cap,'Authored numeric NPZ exact byte length differs')
                arrays=codec._read_arrays(payload,schema,row['count'],cap,'authored '+role); check()
                for offset in range(row['count']):
                    source_row=(projected if role=='base' else rows)[row['start']+offset]
                    for name,array in arrays.items():
                        _require(array[offset].tobytes()==source_row[name].tobytes(),
                            'Authored numeric/raw array value differs')
        cap=roster['audit_frames']['max_bytes']
        payload=_bounded_payload(files,conversion['audit_frames']['path'],cap,check)
        _require(len(payload)==cap,'Authored frames NPZ exact byte length differs')
        frames=codec._read_arrays(payload,compact.FRAME_FIELDS,len(ticks),cap,'authored frames'); check()
        _require(frames['tick'].tolist()==list(ticks),'Authored audit ticks differ')
        for offset,tick in enumerate(ticks):
            for name in ('raw_cam_left','raw_cam_right'):
                _require(frames[name][offset].tobytes()==rows[tick][name].tobytes(),'Authored audit frame differs')
        slot=a['condition_slot']
        _fields(slot,('run_id','condition','resources','condition_resources_sha256','schedule'))
        _fields(slot['resources'],('selector','u'))
        _same(slot['condition_resources_sha256'],memory.sha256(slot['resources']))
        c={'schema':transition.CONTEXT_SCHEMA, **common, 'source_registration':admission,
            'source_commit':a['source_commit'],'source_raw_audit':a['source_raw_audit'],'source_snapshot':snp,
            'source_application_sha256':memory.sha256(application),'source_m_sha256':memory.sha256(application['memory']['m']),
            'source_world_sha256':memory.sha256(application['world_task_state']),'source_run_id':s,
            'case_id':case_id,'case_sha256':memory.sha256(case),'kind':case['kind'],
            **{k:slot[k] for k in ('run_id','condition','condition_resources_sha256','schedule')},
            'source_invariant_sha256':transition.terminal_condition_invariant_vnext(application)}
        c=transition.validate_context_vnext(c)
        check()
        decoded_case,source_memory,source_world,_=audit._source(application,events,rows,c)
        _same(decoded_case,case); _same(source_world,report['world_state'])
        check()
        configured=transition.configure_terminal_condition_vnext(source_memory,slot['resources']['selector'],slot['resources']['u'],context=c)
        _same(transition.terminal_source_view_vnext(source_memory),
            transition.terminal_source_view_vnext(configured,context=c))
        check()
        source=_DecodedSource(case,application,source_world,source_memory['m'],
            {'kind':'source','source_run_id':s,'source_receipt_sha256':None,**snp},events,rows,snapshot)
        holder=HeldSourceVnext(_TOKEN,stack=stack,files=files,deadline=deadline,
            owner_thread=threading.get_ident(),admission=admission,context=c,source=source)
        holder._checks=tuple(checks)
        holder.recheck()
        yield holder
    except BaseException as error:
        primary=error
        raise
    finally:
        if holder is not None:
            try: holder.recheck()
            except BaseException as error: failures.append(error)
            holder._state='closed'
        stack.__exit__(type(primary) if primary else None,primary,primary.__traceback__ if primary else None)
        if failures:
            if primary is not None:
                for failure in failures:
                    primary.add_note(f'Authored teardown failure: {type(failure).__name__}: {failure}')
            else:
                error=RuntimeError('Authored source teardown infrastructure refusal')
                for failure in failures:
                    error.add_note(f'{type(failure).__name__}: {failure}')
                raise error from failures[0]
