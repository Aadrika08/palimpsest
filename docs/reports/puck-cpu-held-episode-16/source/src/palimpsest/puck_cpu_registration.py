"""Byte-only CPU copy planning and prospective held-profile attachment.

No payload is opened or discovered. The parent authenticates accepted receipts,
observation bindings and the live directory census; the copier verifies current
bytes. Constructor validation here grants no tmpfs or execution authority.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import PurePosixPath
import re
import stat
import time

from .puck_dependency_files import (HeldDependencyNamespace, MAX_REGISTRATION_BYTES,
    MAX_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES, MAX_CENSUS_ENTRIES, MAX_METADATA_BYTES,
    _absolute, _canonical, _sha)
from .puck_execution_files import _relative
from .puck_native_identity import TMPFS_IDENTITY_POLICY

_ROLES = ('inventory', 'layout', 'candidate', 'native')
NATIVE_V5 = 'puck-cpu-characterization-native-metadata-v5'
# v6 adds the held episode's explicitly declared dlopen-only leaves (GLVND, EGL,
# Mesa/llvmpipe, LLVM, glfw) and the one GLVND EGL vendor JSON staged under control.
NATIVE_V6 = 'puck-cpu-characterization-native-metadata-v6'
_V6_KEYS = {'kind', 'status', 'root_scope', 'errors', 'oversized_native_files', 'required_missing_names',
            'native_files', 'aliases', 'dynamic_leaves', 'egl_vendor', 'provenance', 'limitations'}
_V6_LEAF_BYTES = 256 * 1024**2
_V6_FILES = 256
EGL_VENDOR_CONTROL = '/puck/control/egl-vendor.json'
# The original interpreter baseline's /usr/lib images, never declared as dynamic leaves.
_BASELINE_LIBRARIES = frozenset('/usr/lib/' + name for name in ('ld-linux-x86-64.so.2', 'libc.so.6', 'libdl.so.2',
                                 'libm.so.6', 'libpthread.so.0', 'librt.so.1', 'libutil.so.1'))
EPISODE_CANDIDATE = 'puck-cpu-episode-import-profile-candidate-v2'
_EGL_VENDOR_DIRECTORY = '/usr/share/glvnd/egl_vendor.d/'
_SONAME = re.compile(r'lib[A-Za-z0-9_+-]+(\.[A-Za-z0-9_+-]+)*\.so(\.[0-9]+)*')
_EMPTY_PROFILE = dict(exports=[], module_changes=[], native_origins=[])
_COLLISIONS = ('destination_regular_directory_path_conflicts',
    'destination_regular_path_collisions_including_entrypoint_wrappers',
    'source_file_ancestor_conflicts', 'source_regular_directory_path_conflicts',
    'source_regular_path_collisions')


def _clock(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError('CPU byte planning deadline exhausted')


def _deadline(value):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or not 0 < value - time.monotonic() <= 180):
        raise ValueError('CPU byte planning requires one future deadline at most 180 seconds')


def _decode(raw, deadline):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result:
                raise ValueError('Duplicate CPU planning JSON field')
            result[key] = value
        return result
    def bad(_):
        raise ValueError('Nonfinite CPU planning JSON value')
    try:
        result = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=bad)
    except (UnicodeError, RecursionError, ValueError) as error:
        raise ValueError('Invalid CPU planning JSON') from error
    stack = [(result, 0)]; count = 0
    while stack:
        _clock(deadline)
        item, depth = stack.pop(); count += 1
        if depth > 32 or count > 524288:
            raise ValueError('CPU planning JSON tree exceeds bound')
        if type(item) is float and not math.isfinite(item):
            raise ValueError('Nonfinite CPU planning JSON number')
        if type(item) is dict:
            stack.extend((v, depth + 1) for v in item.values())
        elif type(item) is list:
            stack.extend((v, depth + 1) for v in item)
    if type(result) is not dict:
        raise ValueError('CPU planning input must be an object')
    return result


def _authenticate(raws, pins, deadline):
    if type(pins) is not dict or set(pins) != set(raws):
        raise ValueError('CPU planning input pin roles differ')
    total = 0
    for role, raw in raws.items():
        _clock(deadline)
        pin = pins[role]
        if (type(pin) is not dict or set(pin) != {'size_bytes', 'sha256'}
                or type(pin['size_bytes']) is not int
                or not 0 < pin['size_bytes'] <= MAX_REGISTRATION_BYTES
                or not _sha(pin['sha256']) or type(raw) is not bytes
                or len(raw) != pin['size_bytes'] or hashlib.sha256(raw).hexdigest() != pin['sha256']):
            raise ValueError('CPU planning '+role+' pin differs')
        total += len(raw)
    if total > MAX_METADATA_BYTES:
        raise ValueError('CPU planning input metadata ceiling exceeded')
    # Authenticate the entire closure before decoding or planning any member.
    return {role:_decode(raw, deadline) for role, raw in raws.items()}


def _path(value):
    path = _relative(value)
    if len(path.encode('utf-8')) > 4096 or len(path.split('/')) > 32:
        raise ValueError('CPU planning relative path exceeds bound')
    return path


def _descriptors(rows, deadline, *, absolute=False, leaf_limit=MAX_FILE_BYTES):
    if type(rows) is not list or not 1 <= len(rows) <= MAX_FILES:
        raise ValueError('CPU planning file count exceeds bound')
    paths = []
    for row in rows:
        _clock(deadline)
        if type(row) is not dict or set(row) != {'path', 'size_bytes', 'sha256'}:
            raise ValueError('CPU planning descriptor fields differ')
        path = _absolute(row['path']) if absolute else _path(row['path'])
        if (len(path.encode('utf-8')) > 4096 or type(row['size_bytes']) is not int
                or not 0 <= row['size_bytes'] <= leaf_limit or not _sha(row['sha256'])):
            raise ValueError('CPU planning descriptor size or hash differs')
        paths.append(path)
    if paths != sorted(set(paths)) or sum(r['size_bytes'] for r in rows) > MAX_TOTAL_BYTES:
        raise ValueError('CPU planning descriptors are duplicated, unsorted or oversized')
    return {row['path']:row for row in rows}


def _site(inventory, layout, deadline):
    if (set(inventory) != {'kind','entries','file_count','directory_count','total_bytes'}
            or inventory['kind'] != 'puck-cpu-installed-files-v1'):
        raise ValueError('CPU installed inventory schema differs')
    files = _descriptors(inventory['entries'], deadline)
    directories = layout.get('predicted_destination_directories')
    if (layout.get('kind') != 'palimpsest-cpu-wheel-install-layout-v1'
            or type(layout.get('version')) is not int or layout['version'] != 1
            or type(directories) is not list or len(directories) > MAX_CENSUS_ENTRIES
            or any(type(p) is not str for p in directories)
            or directories != sorted(set(directories))):
        raise ValueError('CPU installed layout schema differs')
    for key, expected in (('file_count',len(files)), ('directory_count',len(directories)),
                          ('total_bytes',sum(r['size_bytes'] for r in files.values()))):
        if type(inventory[key]) is not int or inventory[key] != expected:
            raise ValueError('CPU inventory measured totals differ')
    if len(files) + len(directories) > MAX_CENSUS_ENTRIES:
        raise ValueError('CPU inventory namespace ceiling exceeded')
    children = {'':set()}
    for directory in directories:
        children[_path(directory)] = set()
    for path in [*directories, *files]:
        _clock(deadline)
        parent, _, name = path.rpartition('/')
        if parent not in children or (path in files and path in children):
            raise ValueError('CPU inventory has missing ancestry or file/directory collisions')
        children[parent].add(name)
    empty = sorted(p for p in directories if not children[p])
    if layout.get('predicted_empty_destination_directories') != empty:
        raise ValueError('CPU empty-directory layout differs')
    collisions = layout.get('collisions')
    flags = ('case_sensitive_linux_paths','destination_directory_coownership_is_allowed')
    if (type(collisions) is not dict or set(collisions) != set((*flags,*_COLLISIONS))
            or any(collisions[k] is not True for k in flags)
            or any(collisions[k] != [] for k in _COLLISIONS)):
        raise ValueError('CPU layout retains collisions or unknown collision policy')
    wheels = layout.get('wheels')
    if type(wheels) is not list or not 1 <= len(wheels) <= MAX_FILES:
        raise ValueError('CPU distribution layout differs')
    distributions = []; metadata_paths = set()
    for wheel in wheels:
        _clock(deadline)
        if type(wheel) is not dict:
            raise ValueError('CPU wheel metadata row differs')
        path = _path(wheel.get('metadata_path'))
        if (not path.endswith('.dist-info/METADATA') or path not in files or path in metadata_paths
                or wheel.get('metadata_sha256') != files[path]['sha256']):
            raise ValueError('CPU distribution METADATA pin differs from inventory')
        metadata_paths.add(path)
        distributions.append(dict(name=wheel.get('name'),version=wheel.get('version'),root_index=0,metadata_path=path))
    if metadata_paths != {p for p in files if p.endswith('.dist-info/METADATA')}:
        raise ValueError('CPU layout omits installed distribution metadata')
    return copy.deepcopy(inventory['entries']), distributions


def _native(native, deadline):
    v6 = native.get('kind') == NATIVE_V6
    if ((native.get('kind') != NATIVE_V5 and not v6)
            or native.get('status') != 'COMPLETE'
            or native.get('root_scope') != ('installed_shared_objects_interpreter_and_declared_dynamic_leaves' if v6
                                            else 'installed_shared_objects_and_interpreter')
            or any(native.get(k) != [] for k in ('errors','oversized_native_files','required_missing_names'))
            or (v6 and set(native) != _V6_KEYS)):
        raise ValueError('CPU native metadata is incomplete')
    files = _descriptors(native.get('native_files'), deadline, absolute=True,
                         leaf_limit=_V6_LEAF_BYTES if v6 else 64*1024**2)
    if len(files) > (_V6_FILES if v6 else 128):
        raise ValueError('CPU native metadata file ceiling exceeded')
    groups = {1:[], 2:[]}
    for path, row in files.items():
        if not (path.startswith('/usr/lib/') or path in ('/usr/bin/ldconfig','/etc/ld.so.cache')):
            raise ValueError('CPU native metadata path is outside its fixed selection')
        index = 1 if path.startswith('/usr/') else 2
        groups[index].append(dict(row,path=path[len('/usr/') if index == 1 else len('/etc/'):]))
    aliases = native.get('aliases')
    if type(aliases) is not list or len(aliases) > 256:
        raise ValueError('CPU native alias bound differs')
    seen = set()
    for row in aliases:
        _clock(deadline)
        if type(row) is not list or len(row) != 2:
            raise ValueError('CPU native alias row differs')
        path = _absolute(row[0]); target = row[1]
        if type(target) is not str:
            raise ValueError('CPU native alias target differs')
        _absolute(target) if target.startswith('/') else _path(target)
        if path in seen or path in files or any(p.startswith(path+'/') for p in files):
            raise ValueError('CPU native alias duplicates or redirects a selected regular path')
        seen.add(path)
    if v6:
        _dynamic(native, files)
    return groups


def _resolve(native, path):
    # Follow only declared single-directory aliases, as the namespace binds them.
    aliases = {row[0]: row[1] for row in native['aliases']}
    for _ in range(4):
        if path not in aliases:
            return path
        target = aliases[path]
        path = target if target.startswith('/') else str(PurePosixPath(path).parent/target)
    raise ValueError('CPU native alias chain is too long')


def _dynamic(native, files):
    limitations = native['limitations']
    if (type(native['provenance']) is not dict or type(limitations) is not list or not 1 <= len(limitations) <= 64
            or any(type(text) is not str or not 0 < len(text) <= 1024 for text in limitations)):
        raise ValueError('CPU native metadata v6 provenance and limitations are required')
    leaves = native['dynamic_leaves']
    if (type(leaves) is not list or not 1 <= len(leaves) <= _V6_FILES or leaves != sorted(set(leaves))
            or any(type(path) is not str or not path.startswith('/usr/lib/') or path not in files for path in leaves)):
        raise ValueError('CPU native dynamic leaves must be sorted declared /usr/lib regular files')
    if set(leaves) & _BASELINE_LIBRARIES:
        raise ValueError('A CPU native dynamic leaf cannot be an original baseline path')
    vendor = native['egl_vendor']
    if (type(vendor) is not dict or set(vendor) != {'path', 'size_bytes', 'sha256', 'library_path'}
            or type(vendor['path']) is not str or not vendor['path'].startswith(_EGL_VENDOR_DIRECTORY)
            or '/' in vendor['path'][len(_EGL_VENDOR_DIRECTORY):] or not vendor['path'].endswith('.json')
            or type(vendor['size_bytes']) is not int or not 0 < vendor['size_bytes'] <= 64*1024
            or not _sha(vendor['sha256'])
            or type(vendor['library_path']) is not str or _SONAME.fullmatch(vendor['library_path']) is None):
        raise ValueError('CPU native EGL vendor declaration differs')
    _absolute(vendor['path'])
    if _resolve(native, '/usr/lib/' + vendor['library_path']) not in leaves:
        raise ValueError('CPU native EGL vendor library is not a declared dynamic leaf')


def native_leaf_row(path, deadline, maximum=_V6_LEAF_BYTES):
    """Current size and SHA-256 of one host native leaf, up to the v6 leaf bound.

    The legacy builder helper stops at 64 MiB; v6 declares larger leaves (libLLVM).
    """
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise ValueError('Native leaf is not a bounded regular file')
        digest = hashlib.sha256(); count = 0
        while True:
            _clock(deadline)
            raw = os.read(fd, 1024 * 1024)
            if not raw:
                break
            count += len(raw); digest.update(raw)
            if count > maximum:
                raise ValueError('Native leaf grew beyond its bound')
        after = os.fstat(fd)
        if count != before.st_size or (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError('Native leaf changed while hashed')
        return dict(size_bytes=count, sha256=digest.hexdigest())
    finally:
        os.close(fd)


def egl_vendor_control(native, raw):
    """Exact pinned host vendor JSON bytes for the staged control copy; nothing is discovered."""
    if type(native) is not dict or native.get('kind') != NATIVE_V6:
        raise ValueError('EGL vendor staging requires native metadata v6')
    _dynamic(native, {row['path']: row for row in native.get('native_files', []) if type(row) is dict})
    vendor = native['egl_vendor']
    if type(raw) is not bytes or len(raw) != vendor['size_bytes'] or hashlib.sha256(raw).hexdigest() != vendor['sha256']:
        raise ValueError('EGL vendor JSON bytes differ from their pin')
    try:
        value = json.loads(raw.decode('utf-8'))
    except (UnicodeError, ValueError) as error:
        raise ValueError('EGL vendor JSON is malformed') from error
    if (type(value) is not dict or set(value) != {'file_format_version', 'ICD'}
            or type(value['file_format_version']) is not str or type(value['ICD']) is not dict
            or value['ICD'] != {'library_path': vendor['library_path']}):
        raise ValueError('EGL vendor JSON must name only the declared library')
    return raw


def _candidate(candidate, deadline):
    # v2 is the held episode candidate: numpy, torch, mujoco and gymnasium, no torchvision.
    episode = candidate.get('kind') == EPISODE_CANDIDATE
    if (candidate.get('kind') not in ('puck-cpu-observed-import-profile-candidate-v1', EPISODE_CANDIDATE)
            or type(candidate.get('version')) is not int or candidate['version'] != (2 if episode else 1)
            or any(candidate.get(k) is not False for k in ('native_phase_qualified','held_runtime_qualified',
                'native_authorized','collection_authorized','study_authorized','executable'))
            or candidate.get('qualification_claims') != []):
        raise ValueError('CPU candidate schema or data-only authority differs')
    profile = candidate.get('import_profile')
    versions = candidate.get('expected_versions')
    if (type(profile) is not dict or profile.get('kind') != 'puck-producer-import-profile-v2'
            or type(profile.get('version')) is not int or profile['version'] != 2
            or type(versions) is not dict
            or set(versions) != {'numpy','torch','gymnasium' if episode else 'torchvision','mujoco'}
            or any(type(v) is not str or not 1 <= len(v) <= 128
                   or any(ord(c) < 33 or ord(c) == 127 for c in v) for v in versions.values())):
        raise ValueError('CPU candidate requires its explicit enhanced profile and four version strings')
    extra = candidate.get('additional_package_inputs')
    if (type(extra) is not list or len(extra) != 1 or type(extra[0]) is not dict
            or set(extra[0]) != {'root','files'}):
        raise ValueError('CPU candidate requires one generated package root')
    _path(extra[0]['root'])
    _descriptors(extra[0]['files'], deadline)
    return copy.deepcopy(extra[0]['files'])


def _schema(registration, deadline):
    _clock(deadline)
    raw = _canonical(registration)
    if len(raw) > MAX_REGISTRATION_BYTES:
        raise ValueError('CPU registration serialized byte ceiling exceeded')
    HeldDependencyNamespace(raw, expected_sha256=hashlib.sha256(raw).hexdigest(), deadline=deadline,
                            registration_path='/.puck-cpu-schema-only.json')
    _clock(deadline)


def _attach(staged, candidate, deadline):
    generated = _candidate(candidate, deadline)
    if (staged.get('kind') != 'puck-worker-dependencies-v3' or type(staged.get('version')) is not int
            or staged['version'] != 3 or staged.get('native_identity') != TMPFS_IDENTITY_POLICY
            or type(staged.get('roots')) is not list or len(staged['roots']) != 4
            or any(type(r) is not dict or r.get('kind') != 'package' for r in staged['roots'])):
        raise ValueError('CPU candidate attachment requires four package roots under dependency-v3')
    if staged['roots'][3].get('files') != generated:
        raise ValueError('CPU generated package bytes differ from candidate')
    result = copy.deepcopy(staged)
    result.update(modules=copy.deepcopy(candidate.get('module_paths')),
                  namespaces=copy.deepcopy(candidate.get('namespaces')),
                  import_profile=copy.deepcopy(candidate.get('import_profile')))
    _schema(result, deadline)
    return result


def build_cpu_source_registration(inventory_raw, layout_raw, candidate_raw, native_raw, *,
                                  expected_pins, site_root, generated_root, deadline) -> dict:
    """Plan four ordered source roots without opening any registered payload."""
    _deadline(deadline)
    data = _authenticate(dict(zip(_ROLES,(inventory_raw,layout_raw,candidate_raw,native_raw))),expected_pins,deadline)
    site_root = _absolute(site_root); generated_root = _absolute(generated_root)
    files, distributions = _site(data['inventory'],data['layout'],deadline)
    native = _native(data['native'],deadline); generated = _candidate(data['candidate'],deadline)
    result = dict(kind='puck-worker-dependencies-v2',version=2,
        roots=[dict(root=site_root,kind='package',files=files),
               dict(root='/usr',kind='system_images',files=native[1]),
               dict(root='/etc',kind='system_images',files=native[2]),
               dict(root=generated_root,kind='package',files=generated)],
        modules=[],namespaces=[],distributions=distributions,import_profile=copy.deepcopy(_EMPTY_PROFILE))
    _schema(result,deadline)
    prospective = copy.deepcopy(result)
    prospective.update(kind='puck-worker-dependencies-v3',version=3,native_identity=TMPFS_IDENTITY_POLICY)
    for root in prospective['roots']:
        root['kind'] = 'package'
    _attach(prospective,data['candidate'],deadline)
    return result


def attach_cpu_candidate(staged_v3, candidate_raw, *, expected_sha256, deadline) -> dict:
    """Attach prospective import rows; caller retains actual staged-byte custody."""
    _deadline(deadline)
    candidate = _authenticate({'candidate':candidate_raw},
        {'candidate':dict(size_bytes=len(candidate_raw) if type(candidate_raw) is bytes else 0,
                          sha256=expected_sha256)},deadline)['candidate']
    if type(staged_v3) is not dict:
        raise ValueError('CPU staged registration must be an object')
    _schema(staged_v3,deadline)
    roots = staged_v3.get('roots')
    if type(roots) is not list or len(roots) != 4:
        raise ValueError('CPU staged registration requires four ordered roots')
    parent = PurePosixPath(roots[0]['root']).parent
    if [r['root'] for r in roots] != [str(parent/('root-'+str(i).zfill(4))) for i in range(4)]:
        raise ValueError('CPU staged root order differs from copier output')
    return _attach(staged_v3,candidate,deadline)
