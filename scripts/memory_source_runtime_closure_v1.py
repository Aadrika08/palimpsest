"""Prospective, unqualified source-runtime bytes and finite accounting bindings.

No imports, preparation, collector authority or execution admission are provided.
"""
from __future__ import annotations

from collections.abc import Callable
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
import time
from types import MappingProxyType

from palimpsest.puck_execution_files import _HeldFileCore, _identity

MiB = 1024**2
GiB = 1024**3
PROFILE = MappingProxyType({
    'profile_id': 'memory-source-runtime-profile-v1-proposed',
    'roots_min': 1, 'roots_max': 16, 'standalones_max': 1024,
    'files_min': 1, 'files_max': 32768, 'census_entries_max': 60000,
    'input_bytes_max': 16*GiB, 'file_bytes_min': 0, 'file_bytes_max': 2*GiB,
    'root_bytes_max': 16*GiB,
    'manifest_bytes_min': 1, 'manifest_bytes_max': 16*MiB, 'manifest_nodes_max': 1000000,
    'recipe_bytes_min': 1, 'recipe_bytes_max': 64*1024, 'recipe_nodes_max': 8192,
    'ledger_bytes_min': 1, 'ledger_bytes_max': 256*1024, 'ledger_nodes_max': 32768,
    'charge_reference_bytes_max': 8192, 'charge_reference_nodes_max': 64,
    'json_depth_max': 32, 'path_bytes_max': 4096, 'component_bytes_max': 255,
    'relative_depth_max': 32, 'string_bytes_max': 1024,
    'operations_max': 1024, 'retained_files_max': 1024,
    'retained_file_bytes_max': MiB, 'retained_bytes_max': 16*MiB,
    'required_sources_max': 64,
})


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


PROFILE_SHA256 = hashlib.sha256(_canonical(dict(PROFILE))).hexdigest()
POLICY = 'retained-unqualified-v1'
PROJECT_NS = 86400*10**9
MEMORY_NS = 43200*10**9


def _keys(value, keys):
    if type(value) is not dict or set(value) != set(keys.split()):
        raise ValueError('Missing or unknown record fields')


def _int(value, maximum, minimum=0):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError('Integer is outside its bound')
    return value


def _text(value, maximum=None):
    if type(value) is not str:
        raise ValueError('Expected Unicode string')
    try:
        size = len(value.encode('utf-8'))
    except UnicodeError as error:
        raise ValueError('Invalid Unicode') from error
    if size > (PROFILE['string_bytes_max'] if maximum is None else maximum):
        raise ValueError('String exceeds its byte bound')
    return value


def _path(value, *, absolute=True):
    _text(value, PROFILE['path_bytes_max'])
    if not value or value.startswith('/') != absolute:
        raise ValueError('Path has wrong absolute/relative form')
    parts = value[1:].split('/') if absolute else value.split('/')
    if (any(p in ('', '.', '..') for p in parts) or '\\' in value or ':' in value
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError('Path is not canonical POSIX')
    if not absolute and len(parts) > PROFILE['relative_depth_max']:
        raise ValueError('Relative path is too deep')
    for part in parts:
        _text(part, PROFILE['component_bytes_max'])
    return value


def _digest(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('Expected lowercase SHA-256')
    return value


def _uuid(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{32}', value) is None:
        raise ValueError('Expected canonical UUID hex')
    return value


def _descriptor(value, *, absolute=True, maximum=None, minimum=0):
    _keys(value, 'path size_bytes sha256')
    return dict(path=_path(value['path'], absolute=absolute),
                size_bytes=_int(value['size_bytes'], PROFILE['file_bytes_max'] if maximum is None else maximum, minimum),
                sha256=_digest(value['sha256']))


def _list(value, maximum):
    if type(value) is not list or len(value) > maximum:
        raise ValueError('List exceeds its bound')
    return value


def _sorted(rows, key=lambda x: x):
    names = [key(row) for row in rows]
    if names != sorted(set(names)):
        raise ValueError('Inventory must be sorted and distinct')
    return rows


def _profile(value):
    if (value['profile_id'] != PROFILE['profile_id'] or value['profile_sha256'] != PROFILE_SHA256
            or value['load_policy'] != POLICY):
        raise ValueError('Prospective profile or unqualified policy differs')


def _structure(value, nodes):
    stack = [(iter((value,)), 0)]; count = 0
    while stack:
        iterator, depth = stack[-1]
        try: item = next(iterator)
        except StopIteration:
            stack.pop(); continue
        count += 1
        if count > nodes or depth > PROFILE['json_depth_max']:
            raise ValueError('JSON structure bound exceeded')
        if type(item) in (dict,list):
            if len(item) > nodes-count: raise ValueError('JSON structure bound exceeded')
            if type(item) is dict:
                for key in item: _text(key)
                children = iter(item.values())
            else: children = iter(item)
            stack.append((children,depth+1))
        elif type(item) is str:
            _text(item, PROFILE['path_bytes_max'])
        elif item is None or type(item) in (bool,int):
            pass
        elif type(item) is float and math.isfinite(item):
            pass
        else:
            raise ValueError('Unsupported/nonfinite JSON value')


def _bounded_encoding(value, kind):
    _structure(value, PROFILE[kind+'_nodes_max'])
    payload = bytearray()
    encoder = json.JSONEncoder(sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    for chunk in encoder.iterencode(value):
        raw = chunk.encode('utf-8')
        if len(payload)+len(raw) > PROFILE[kind+'_bytes_max']: raise ValueError('JSON byte bound exceeded')
        payload.extend(raw)
    return bytes(payload)


def _preflight(raw, maximum, nodes):
    if type(raw) is not bytes or not 1 <= len(raw) <= maximum:
        raise ValueError('JSON byte bound exceeded')
    # Bound nesting and value tokens before allocating parsed containers. Keys
    # are excluded from node counts, matching the post-parse value walk.
    depth = 0; count = 0; pos = 0
    while pos < len(raw):
        char = raw[pos]
        if char == 34:
            pos += 1
            while pos < len(raw):
                if raw[pos] == 92: pos += 2; continue
                if raw[pos] == 34: break
                pos += 1
            if pos >= len(raw): raise ValueError('Unterminated JSON string')
            end = pos+1
            while end < len(raw) and raw[end] in b' \t\n\r': end += 1
            if end == len(raw) or raw[end] != 58: count += 1
        elif char in (123, 91):
            count += 1; depth += 1
            if depth > PROFILE['json_depth_max']+1: raise ValueError('JSON nesting bound exceeded')
        elif char in (125, 93): depth -= 1
        elif char not in b' \t\n\r,:':
            count += 1
            while pos+1 < len(raw) and raw[pos+1] not in b' \t\n\r,:]}': pos += 1
        if count > nodes: raise ValueError('JSON node bound exceeded')
        pos += 1


def _json(raw, descriptor, kind):
    _preflight(raw, PROFILE[kind+'_bytes_max'], PROFILE[kind+'_nodes_max'])
    if len(raw) != descriptor['size_bytes'] or hashlib.sha256(raw).hexdigest() != descriptor['sha256']:
        raise ValueError('Actual JSON byte binding differs')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def bad(value): raise ValueError('Nonfinite JSON')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=bad)
        _structure(value, PROFILE[kind+'_nodes_max'])
        if _canonical(value) != raw: raise ValueError('JSON bytes are not canonical')
    except (UnicodeError, RecursionError, OverflowError) as error:
        raise ValueError('Invalid JSON encoding or structure') from error
    return value


def validate_runtime_reference(value: dict) -> dict:
    _structure(value, PROFILE['charge_reference_nodes_max'])
    _keys(value, 'schema profile_id profile_sha256 load_policy recipe manifest ledger')
    if value['schema'] != 'memory-source-runtime-reference-v1': raise ValueError('Reference schema differs')
    _profile(value)
    result = dict(value)
    for kind in ('recipe', 'manifest', 'ledger'):
        result[kind] = _descriptor(value[kind], maximum=PROFILE[kind+'_bytes_max'], minimum=1)
    paths = [result[k]['path'] for k in ('recipe','manifest','ledger')]
    if any(_overlap(a,b) for i,a in enumerate(paths) for b in paths[i+1:]):
        raise ValueError('Metadata descriptors overlap')
    return result


def _within(path, root):
    return path == root or path.startswith(root+'/')


def _overlap(a, b):
    return _within(a,b) or _within(b,a)


def _disjoint_files(paths):
    seen = set()
    for path in sorted(paths):
        if path in seen: raise ValueError('Regular file paths overlap')
        parent = path.rpartition('/')[0]
        while parent:
            if parent in seen: raise ValueError('Regular file paths overlap')
            parent = parent.rpartition('/')[0]
        seen.add(path)


def _pins(value):
    _keys(value, 'python_alias python_elf owner_source pyvenv_config required_sources')
    result = {'python_alias': _path(value['python_alias'])}
    for key in ('python_elf','owner_source','pyvenv_config'):
        result[key] = _descriptor(value[key])
    result['required_sources'] = _sorted([_descriptor(v) for v in _list(value['required_sources'], PROFILE['required_sources_max'])], lambda r:r['path'])
    return result


def validate_runtime_pin_requirements(value: dict) -> dict:
    """Copy the complete independent pin expectations without IO or custody."""
    return _pins(value)


def _runtime_records(manifest):
    records = {root['root']+'/'+row['path']: dict(row, path=root['root']+'/'+row['path'])
               for root in manifest['roots'] for row in root['files']}
    records.update((row['path'], row) for row in manifest['standalones'])
    return records


def _validate_manifest(raw: bytes, reference: dict, *, required_roots: tuple[str, ...],
                              required_pins: dict, output_root: str) -> dict:
    ref = validate_runtime_reference(reference)
    value = _json(raw, ref['manifest'], 'manifest')
    _keys(value, 'schema preparation_id profile_id profile_sha256 load_policy recipe roots standalones pins')
    if value['schema'] != 'memory-source-runtime-manifest-v1': raise ValueError('Manifest schema differs')
    _uuid(value['preparation_id']); _profile(value)
    if _descriptor(value['recipe'], maximum=PROFILE['recipe_bytes_max'], minimum=1) != ref['recipe']:
        raise ValueError('Manifest recipe pin differs')
    roots = _list(value['roots'], PROFILE['roots_max'])
    if len(roots) < PROFILE['roots_min']: raise ValueError('No complete roots')
    count = len(roots); file_count = 0; input_bytes = 0
    for root in roots:
        _keys(root, 'root kind files directories'); _path(root['root'])
        if root['kind'] != 'complete': raise ValueError('Root is not complete')
        files = _sorted([_descriptor(v, absolute=False) for v in _list(root['files'], PROFILE['files_max'])], lambda r:r['path'])
        dirs = _sorted([_path(v, absolute=False) for v in _list(root['directories'], PROFILE['census_entries_max'])])
        children = {'': {}}
        children.update((d,{}) for d in dirs)
        for directory in dirs:
            _path(root['root']+'/'+directory)
            parent, _, name = directory.rpartition('/')
            if parent not in children: raise ValueError('Directory ancestor missing')
            children[parent][name] = 'directory'
        for row in files:
            _path(root['root']+'/'+row['path'])
            parent, _, name = row['path'].rpartition('/')
            if parent not in children or name in children[parent]: raise ValueError('File/directory topology differs')
            children[parent][name] = 'file'
        root_bytes = sum(r['size_bytes'] for r in files)
        _int(root_bytes, PROFILE['root_bytes_max'])
        input_bytes += root_bytes; file_count += len(files); count += len(files)+len(dirs)
        root['files'] = files; root['directories'] = dirs
    _sorted(roots, lambda r:r['root'])
    paths = [r['root'] for r in roots]
    for i, path in enumerate(paths):
        if any(_overlap(path, other) for other in paths[i+1:]): raise ValueError('Complete roots overlap')
    standalones = _sorted([_descriptor(v) for v in _list(value['standalones'], PROFILE['standalones_max'])], lambda r:r['path'])
    _disjoint_files([row['path'] for row in standalones])
    for row in standalones:
        if any(_overlap(row['path'], root) for root in paths): raise ValueError('Standalone overlaps complete root')
    value['standalones'] = standalones
    count += len(standalones); file_count += len(standalones)
    input_bytes += sum(r['size_bytes'] for r in standalones)
    _int(count, PROFILE['census_entries_max']); _int(file_count, PROFILE['files_max'], PROFILE['files_min'])
    _int(input_bytes, PROFILE['input_bytes_max'])
    if type(required_roots) is not tuple or not required_roots:
        raise ValueError('Executing layout must supply required roots')
    required = sorted(set(_path(v) for v in required_roots))
    outer = [p for p in required if not any(p != q and _within(p,q) for q in required)]
    if not all(any(_within(p,root) for root in paths) for p in outer):
        raise ValueError('Required complete root coverage differs')
    output = _path(output_root) if output_root is not None else None
    metadata = [ref[k]['path'] for k in ('recipe','manifest','ledger')]
    runtime = _runtime_records(value)
    if output is not None and any(_overlap(output,p) for p in paths+list(runtime)):
        raise ValueError('Runtime overlaps output')
    if any(_overlap(p,root) for p in metadata for root in paths+list(runtime)):
        raise ValueError('Runtime overlaps metadata')
    if output is not None and any(_overlap(output,p) for p in metadata): raise ValueError('Metadata overlaps output')
    pins = _pins(value['pins'])
    if pins != _pins(required_pins): raise ValueError('Required semantic pins differ')
    for row in [pins[k] for k in ('python_elf','owner_source','pyvenv_config')]+pins['required_sources']:
        if runtime.get(row['path']) != row: raise ValueError('Pin is not the identical runtime record')
    value['pins'] = pins
    return copy.deepcopy(value)


def validate_runtime_manifest(raw: bytes, reference: dict, *, required_roots: tuple[str, ...],
                              required_pins: dict, output_root: str) -> dict:
    return _validate_manifest(raw, reference, required_roots=required_roots,
                              required_pins=required_pins, output_root=_path(output_root))


def _bound_manifest(manifest, reference):
    _keys(manifest, 'schema preparation_id profile_id profile_sha256 load_policy recipe roots standalones pins')
    roots = _list(manifest['roots'], PROFILE['roots_max'])
    for root in roots: _keys(root, 'root kind files directories')
    return _validate_manifest(_bounded_encoding(manifest, 'manifest'), reference,
        required_roots=tuple(root['root'] for root in roots), required_pins=manifest['pins'], output_root=None)


def validate_preparation_recipe(raw: bytes, reference: dict, manifest: dict) -> dict:
    ref = validate_runtime_reference(reference)
    return _validate_recipe(raw, ref, _bound_manifest(manifest, ref))


def _validate_recipe(raw: bytes, reference: dict, manifest: dict) -> dict:
    ref = validate_runtime_reference(reference)
    value = _json(raw, ref['recipe'], 'recipe')
    _keys(value, 'schema preparation_id profile_id profile_sha256 load_policy intended_roots intended_standalones method')
    if value['schema'] != 'memory-source-runtime-recipe-v1': raise ValueError('Recipe schema differs')
    _uuid(value['preparation_id']); _profile(value)
    roots = _sorted([_path(p) for p in _list(value['intended_roots'], PROFILE['roots_max'])])
    standalones = _sorted([_path(p) for p in _list(value['intended_standalones'], PROFILE['standalones_max'])])
    if (value['preparation_id'] != manifest['preparation_id'] or manifest['recipe'] != ref['recipe']
            or roots != [r['root'] for r in manifest['roots']]
            or standalones != [r['path'] for r in manifest['standalones']]
            or value['method'] != 'externally-prepared-complete-runtime-input'):
        raise ValueError('Recipe intended preparation differs')
    return copy.deepcopy(value)


def _cpu(value):
    _keys(value, 'project_cpu_ns memory_cpu_ns')
    project = _int(value['project_cpu_ns'], PROJECT_NS)
    memory = _int(value['memory_cpu_ns'], MEMORY_NS)
    if memory > project: raise ValueError('Memory CPU exceeds project CPU')
    return project, memory


def _charge(value):
    _structure(value, PROFILE['charge_reference_nodes_max'])
    _keys(value, 'evidence project_cpu_ns memory_cpu_ns')
    _descriptor(value['evidence'], maximum=PROFILE['retained_file_bytes_max'])
    _cpu({k:value[k] for k in ('project_cpu_ns','memory_cpu_ns')})
    _bounded_encoding(value, 'charge_reference')
    return copy.deepcopy(value)


def _upward_seconds(ns):
    result = ns/10**9
    numerator, denominator = result.as_integer_ratio()
    if numerator*10**9 < ns*denominator: result = math.nextafter(result, math.inf)
    return result


def _prior(charge, prior_charge_reference, prior_cpu):
    if (prior_charge_reference is None) != (prior_cpu is None):
        raise ValueError('Prior charge and CPU must be supplied together')
    if prior_charge_reference is None: return
    if _charge(prior_charge_reference) != charge: raise ValueError('Prior cumulative charge differs')
    _keys(prior_cpu, 'project_seconds memory_seconds')
    for lane in ('project','memory'):
        value = prior_cpu[lane+'_seconds']
        if (type(value) is not float or not math.isfinite(value) or value < 0
                or (value == 0 and math.copysign(1,value) < 0)
                or value != _upward_seconds(charge[lane+'_cpu_ns'])):
            raise ValueError('Prior CPU must be exact upward binary64 seconds')
        limit = PROJECT_NS if lane == 'project' else MEMORY_NS
        if charge[lane+'_cpu_ns']+1800*10**9 > limit:
            raise ValueError('Prior integer CPU leaves insufficient fixed allocation')


def validate_preparation_ledger(raw: bytes, reference: dict, manifest: dict, recipe: dict, *,
                                prior_charge_reference: dict | None = None,
                                prior_cpu: dict | None = None) -> dict:
    ref = validate_runtime_reference(reference)
    # Supplied normalized records must still be bound to their actual canonical bytes.
    manifest = _bound_manifest(manifest, ref)
    checked_recipe = _validate_recipe(_bounded_encoding(recipe, 'recipe'), ref, manifest)
    value = _json(raw, ref['ledger'], 'ledger')
    _keys(value, 'schema preparation_id state recipe manifest baseline operations retained_files runtime_input_bytes external_record_bytes totals cumulative_charge_reference')
    if (value['schema'] != 'memory-source-runtime-preparation-ledger-v1' or value['state'] != 'completed'
            or _uuid(value['preparation_id']) != checked_recipe['preparation_id']):
        raise ValueError('Ledger is not the declared completed preparation')
    for kind in ('recipe','manifest'):
        if _descriptor(value[kind], maximum=PROFILE[kind+'_bytes_max'], minimum=1) != ref[kind]:
            raise ValueError('Ledger input binding differs')
    baseline = value['baseline']; _keys(baseline, 'accounting_id project_cpu_ns memory_cpu_ns evidence')
    _uuid(baseline['accounting_id'])
    project, memory = _cpu({k:baseline[k] for k in ('project_cpu_ns','memory_cpu_ns')})
    base_evidence = _descriptor(baseline['evidence'], maximum=PROFILE['retained_file_bytes_max'])
    seen_evidence = {base_evidence['path']}
    required_evidence = [base_evidence]
    operations = _list(value['operations'], PROFILE['operations_max'])
    _sorted(operations, lambda r: _uuid(r['operation_id']) if type(r) is dict and 'operation_id' in r else '')
    for operation in operations:
        _keys(operation, 'operation_id outcome memory_cpu_ns evidence'); _uuid(operation['operation_id'])
        if operation['operation_id'] == baseline['accounting_id']: raise ValueError('Baseline execution reused')
        if operation['outcome'] not in ('completed','failed'): raise ValueError('Incomplete operation accounting')
        cpu = _int(operation['memory_cpu_ns'], MEMORY_NS)
        row = _descriptor(operation['evidence'], maximum=PROFILE['retained_file_bytes_max'])
        if row['path'] in seen_evidence: raise ValueError('Execution evidence reused under distinct IDs')
        seen_evidence.add(row['path']); required_evidence.append(row)
        project += cpu; memory += cpu
    totals = _cpu(value['totals'])
    if totals != (project,memory): raise ValueError('Preparation CPU sums differ')
    charge = _charge(value['cumulative_charge_reference'])
    if (charge['project_cpu_ns'],charge['memory_cpu_ns']) != totals: raise ValueError('Cumulative integer totals differ')
    required_evidence.append(charge['evidence'])
    retained = _sorted([_descriptor(v, maximum=PROFILE['retained_file_bytes_max'])
                       for v in _list(value['retained_files'], PROFILE['retained_files_max'])], lambda r:r['path'])
    retained_map = {r['path']:r for r in retained}
    if any(retained_map.get(r['path']) != r for r in required_evidence): raise ValueError('Accounting evidence is not retained')
    if sum(r['size_bytes'] for r in retained) > PROFILE['retained_bytes_max']: raise ValueError('Retained evidence byte cap')
    runtime = _runtime_records(manifest)
    excluded = list(runtime)+[r['root'] for r in manifest['roots']]+[ref[k]['path'] for k in ('recipe','manifest','ledger')]
    for row in retained:
        if any(_overlap(row['path'], p) for p in excluded): raise ValueError('Evidence overlaps runtime or metadata')
    all_paths = list(runtime)+[r['path'] for r in retained]+[ref[k]['path'] for k in ('recipe','manifest','ledger')]
    _disjoint_files(all_paths)
    runtime_bytes = sum(r['size_bytes'] for r in runtime.values())
    external_records = ref['recipe']['size_bytes']+ref['manifest']['size_bytes']+sum(r['size_bytes'] for r in retained)
    if (_int(value['runtime_input_bytes'], PROFILE['input_bytes_max']) != runtime_bytes
            or _int(value['external_record_bytes'], 33*MiB) != external_records):
        raise ValueError('Physical byte inventory sums differ')
    _prior(charge, prior_charge_reference, prior_cpu)
    return dict(runtime_input_bytes=runtime_bytes,
                external_input_bytes=runtime_bytes+external_records+ref['ledger']['size_bytes'],
                project_cpu_ns=project, memory_cpu_ns=memory, accounting_authority_qualified=False)


class _SourceNamespaceFiles(_HeldFileCore):
    """Local source adapter: exact selected trees, edge-only ancestors."""

    def __init__(self, entries, roots, deadline, check):
        self._budget_check = check
        self._selected = tuple(tuple(_path(r['root']).split('/')[1:]) for r in roots)
        self._children = {}
        for root in roots:
            prefix = tuple(root['root'].split('/')[1:])
            topology = {'': {}}
            for directory in root['directories']:
                topology[directory] = {}
            for directory in root['directories']:
                parent, _, name = directory.rpartition('/')
                topology[parent][name] = 'directory'
            for row in root['files']:
                parent, _, name = row['path'].rpartition('/')
                topology[parent][name] = 'file'
            for relative, children in topology.items():
                key = prefix+tuple(relative.split('/')) if relative else prefix
                self._children[key] = children
        rows = [dict(_descriptor(row), path=row['path'][1:]) for row in entries]
        # Runtime and metadata/evidence have independent pure-schema caps; this
        # adapter's internal aggregate must hold both without reusing Puck's cap.
        super().__init__('/', sorted(rows,key=lambda r:r['path']), deadline,
                         limits=(PROFILE['files_max']+PROFILE['retained_files_max']+3,
                                 PROFILE['file_bytes_max'],
                                 PROFILE['input_bytes_max']+PROFILE['retained_bytes_max']+
                                 sum(PROFILE[k+'_bytes_max'] for k in ('recipe','manifest','ledger'))))

    def _clock(self):
        self._budget_check()
        super()._clock()

    def _edge(self, key, identity):
        return identity if any(key[:len(p)] == p for p in self._selected) else identity[:3]

    def _directory(self, key):
        if key in self._dirs: return self._dirs[key][0]
        self._clock()
        if not key:
            parent, name = None, '/'
            fd = os.open('/', os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        else:
            parent, name = self._directory(key[:-1]), key[-1]
            fd = os.open(name, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=parent)
        self._fds.append(fd)
        before = _identity(os.fstat(fd))
        if self._edge(key,before) != self._edge(key,_identity(os.stat(name,dir_fd=parent,follow_symlinks=False))):
            raise RuntimeError('Source directory edge changed during open')
        self._dirs[key] = (fd,parent,name,before)
        return fd

    def _check_dirs(self):
        for key,(fd,parent,name,expected) in self._dirs.items():
            self._clock(); wanted = self._edge(key,expected)
            if (self._edge(key,_identity(os.fstat(fd))) != wanted
                    or self._edge(key,_identity(os.stat(name,dir_fd=parent,follow_symlinks=False))) != wanted):
                raise RuntimeError('Source directory identity changed')

    def _check_subtrees(self):
        for key, expected in self._children.items():
            self._clock(); directory = self._directory(key)
            scan = os.open('.', os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=directory)
            names = set()
            try:
                with os.scandir(scan) as iterator:
                    for item in iterator:
                        self._clock()
                        if item.name not in expected or item.name in names:
                            raise ValueError('Source namespace has an unexpected entry')
                        names.add(item.name)
                        state = item.stat(follow_symlinks=False)
                        matches = (stat.S_ISDIR(state.st_mode) if expected[item.name] == 'directory'
                                   else stat.S_ISREG(state.st_mode) and state.st_nlink == 1)
                        if not matches: raise ValueError('Source namespace entry type differs')
            finally:
                os.close(scan)
            if names != set(expected): raise ValueError('Source namespace lacks an entry')

    def _read_metadata(self, path):
        self._active()
        try:
            relative = path[1:]
            self._clock(); self._check_dirs()
            data = self._check_file(relative, copy_bytes=True)
            self._check_dirs(); self._clock()
            return data
        except BaseException:
            self._failed()
            raise


def _alias_identity(pins, check):
    # This exception authenticates the explicitly pinned executable alias only.
    alias = Path(pins['python_alias'])
    check()
    if alias.resolve(strict=True) != Path(pins['python_elf']['path']):
        raise ValueError('Python alias target differs from frozen file')
    chain = []; seen = set(); current = alias
    while True:
        check()
        if current in seen or len(seen) > 40: raise ValueError('Python alias chain is cyclic or too long')
        seen.add(current); row = current.lstat()
        link = os.readlink(current) if stat.S_ISLNK(row.st_mode) else None
        chain.append((str(current), row.st_dev, row.st_ino, row.st_mode,
                      row.st_mtime_ns, row.st_ctime_ns, link))
        if link is None: break
        current = Path(os.path.normpath(link if os.path.isabs(link) else current.parent/link))
    return chain


class RuntimeHandle:
    """One-shot current-byte custody; no import or execution capability."""

    def __init__(self, reference, *, required_roots, required_pins, output_root, deadline, check):
        self._reference = validate_runtime_reference(reference)
        if type(required_roots) is not tuple or not required_roots: raise ValueError('Required roots missing')
        self._required_roots = tuple(_path(r) for r in required_roots)
        self._required_pins = _pins(required_pins)
        self._output_root = _path(output_root)
        if type(deadline) not in (int,float) or not math.isfinite(deadline): raise ValueError('Deadline must be finite')
        if not callable(check): raise ValueError('Budget callback required')
        self._deadline = deadline; self._check = check
        self._state = 'new'; self._holders = []; self._checked = False

    @property
    def deadline(self):
        return self._deadline

    def _clock(self):
        self._check()
        if time.monotonic() >= self._deadline: raise TimeoutError('Runtime custody deadline exhausted')

    def _active(self):
        if self._state != 'active': raise RuntimeError('Runtime custody is closed, failed or not entered')

    def _release(self):
        first = None
        while self._holders:
            held = self._holders.pop()
            held._state = 'failed' if self._state == 'failed' else 'closed'
            try: held._close()
            except BaseException as error:
                if first is None: first = error
        if first is not None:
            self._state = 'failed'; self._checked = False
            raise first

    def _poison(self):
        self._state = 'failed'; self._checked = False
        self._release()

    def _acquire(self, entries, roots):
        held = _SourceNamespaceFiles(entries, roots, self._deadline, self._clock)
        self._holders.append(held)
        held.__enter__()
        return held

    def _aliases(self):
        seen = set()
        for held in self._holders:
            for fd, _, _, expected in held._files.values():
                self._clock()
                identity = _identity(os.fstat(fd))
                if identity != expected or identity[:2] in seen:
                    raise ValueError('Global runtime/metadata inode alias or mutation')
                seen.add(identity[:2])

    def __enter__(self):
        if self._state != 'new': raise RuntimeError('Runtime custody can only be entered once')
        try:
            self._clock()
            ref = self._reference
            metadata = self._acquire([ref[k] for k in ('recipe','manifest','ledger')], [])
            manifest_raw = metadata._read_metadata(ref['manifest']['path'])
            self._manifest = validate_runtime_manifest(manifest_raw, ref,
                required_roots=self._required_roots, required_pins=self._required_pins, output_root=self._output_root)
            self._clock()
            self._recipe = validate_preparation_recipe(metadata._read_metadata(ref['recipe']['path']), ref, self._manifest)
            self._ledger_raw = metadata._read_metadata(ref['ledger']['path'])
            self._accounting = validate_preparation_ledger(self._ledger_raw, ref, self._manifest, self._recipe)
            self._ledger = _json(self._ledger_raw, ref['ledger'], 'ledger')
            evidence = self._ledger['retained_files']
            if any(_overlap(r['path'],self._output_root) for r in evidence):
                raise ValueError('Evidence overlaps output')
            self._records = _runtime_records(self._manifest)
            self._alias = _alias_identity(self._manifest['pins'],self._clock)
            self._acquire(list(self._records.values())+evidence, self._manifest['roots'])
            self._aliases()
            self._state = 'active'; self.recheck()
            return self
        except BaseException:
            self._poison()
            raise

    def recheck(self) -> None:
        self._active()
        try:
            self._clock()
            for held in self._holders: held.recheck()
            self._aliases()
            if _alias_identity(self._manifest['pins'],self._clock) != self._alias:
                raise RuntimeError('Python alias chain changed while held')
            self._clock(); self._checked = True
        except BaseException:
            self._poison()
            raise

    def descriptor(self, path: str) -> dict:
        self._active()
        try:
            self.recheck(); path = _path(path)
            if path not in self._records: raise ValueError('Path is not a selected runtime file')
            result = dict(self._records[path]); self.recheck()
            return result
        except BaseException:
            self._poison()
            raise

    def summary(self) -> dict:
        self._active()
        try:
            self.recheck()
            result = dict(schema='memory-source-runtime-current-bytes-v1',
                manifest_sha256=self._reference['manifest']['sha256'], profile_sha256=PROFILE_SHA256,
                load_policy=POLICY, root_count=len(self._manifest['roots']), file_count=len(self._records),
                directory_count=sum(1+len(r['directories']) for r in self._manifest['roots']),
                input_bytes=self._accounting['runtime_input_bytes'], current_bytes_checked=self._checked,
                runtime_qualified=False, source_qualified=False, execution_authorized=False)
            if len(_canonical(result)) > 2048: raise ValueError('Summary byte bound')
            self.recheck()
            return result
        except BaseException:
            self._poison()
            raise

    def accounting(self, *, prior_charge_reference: dict, prior_cpu: dict) -> dict:
        self._active()
        try:
            if type(prior_charge_reference) is not dict or type(prior_cpu) is not dict:
                raise ValueError('Required prior charge and CPU must be dictionaries')
            self.recheck()
            result = validate_preparation_ledger(self._ledger_raw, self._reference, self._manifest,
                self._recipe, prior_charge_reference=prior_charge_reference, prior_cpu=prior_cpu)
            if len(_canonical(result)) > 2048: raise ValueError('Accounting summary byte bound')
            self.recheck()
            return result
        except BaseException:
            self._poison()
            raise

    def __exit__(self, kind, error, traceback):
        if self._state != 'active':
            if kind is None: raise RuntimeError('Runtime custody failed before context exit')
            return False
        try:
            self.recheck()
            self._state = 'closed'
        except BaseException:
            self._poison()
            raise
        finally:
            self._release()
        return False


def hold_runtime_manifest(reference: dict, *, required_roots: tuple[str, ...], required_pins: dict,
                          output_root: str, deadline: float, check: Callable[[], None]) -> RuntimeHandle:
    return RuntimeHandle(reference, required_roots=required_roots, required_pins=required_pins,
                         output_root=output_root, deadline=deadline, check=check)
