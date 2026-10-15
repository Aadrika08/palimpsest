"""Read-only, Linux-leased dependency bytes; no execution or qualification grant.

Package namespaces are completely censused, including inert cache bytes. Hard
links outside those roots are unknown names protected by the same inode lease.
System images rely explicitly on a trusted root owner, not hostile-root defense.
"""
from __future__ import annotations

import copy
from email.parser import BytesParser
import fcntl
import hashlib
import importlib.machinery
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import sys
import threading
import time

from .puck_execution_files import _HeldFileCore, _identity, _relative
from .puck_dependency_bindings import validate_profile

MiB = 1024 ** 2
MAX_REGISTRATION_BYTES = 16 * MiB
MAX_FILES = 32768
MAX_CENSUS_ENTRIES = 60000
MAX_FILE_BYTES = 2 * 1024 ** 3
MAX_TOTAL_BYTES = 16 * 1024 ** 3
MAX_METADATA_BYTES = 64 * MiB
_LEASE_OWNER = None
_NAME = re.compile(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', re.ASCII)
_DIST = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?', re.ASCII)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8')


def _sha(value):
    return type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None


def _absolute(value):
    if (type(value) is not str or not value.startswith('/') or value == '/'
            or str(Path(value)) != value or '\\' in value or ':' in value
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or any(p in ('', '.', '..') for p in value.split('/')[1:])):
        raise ValueError('Dependency path must be canonical absolute POSIX text')
    return value


def _fields(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError('Dependency registration has missing or unknown fields')


def _decode(raw, digest):
    if type(raw) is not bytes or len(raw) > MAX_REGISTRATION_BYTES or not _sha(digest):
        raise ValueError('Dependency registration bytes or SHA-256 are invalid')
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Dependency registration external SHA-256 differs')
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result: raise ValueError('Duplicate dependency JSON field')
            result[key] = value
        return result
    def bad(value): raise ValueError('Non-finite dependency JSON')
    try:
        result = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=bad)
    except (UnicodeError, RecursionError) as error:
        raise ValueError('Invalid dependency JSON encoding or depth') from error
    count = 0
    stack = [(result, 0)]
    while stack:
        value, depth = stack.pop(); count += 1
        if count > 524288 or depth > 32: raise ValueError('Dependency JSON tree exceeds bound')
        if type(value) is dict: stack.extend((v, depth + 1) for v in value.values())
        elif type(value) is list: stack.extend((v, depth + 1) for v in value)
    if _canonical(result) != raw: raise ValueError('Dependency registration must be canonical JSON')
    return result


class _DependencyFiles(_HeldFileCore):
    def __init__(self, root, entries, deadline, owner, mode, *, census=False):
        self._owner = owner
        self._protection = mode
        self._census = census
        self._namespace = None
        self._census_entries = 0
        self._hashed = set()
        super().__init__(root, entries, deadline,
                         limits=(MAX_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES))

    def _clock(self):
        # A lease break on any admitted package poisons every byte stream.
        # The core calls this on each bounded hash block, not only afterward.
        self._owner._check_signal()
        super()._clock()

    def _close(self):
        first = None
        leaves = {value[0] for value in self._files.values()}
        if self._protection == 'linux_read_lease':
            for fd in reversed(self._fds):
                if fd in leaves:
                    try: fcntl.fcntl(fd, fcntl.F_SETLEASE, fcntl.F_UNLCK)
                    except OSError as error:
                        if first is None: first = error
        try: super()._close()
        except OSError as error:
            if first is None: first = error
        if first is not None: raise first

    def _accept_leaf(self, state, entry):
        return stat.S_ISREG(state.st_mode) and state.st_nlink >= 1 and state.st_size == entry.size

    def _check_file(self, relative, *, copy_bytes=False):
        self._owner._check_signal()
        self._clock()
        entry = self._entries[relative]
        fd, parent, name, expected = self._files[relative]
        if (_identity(os.fstat(fd)) != expected or
                _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
            raise RuntimeError('Dependency file edge or metadata changed')
        if relative not in self._hashed:
            if self._protection == 'linux_read_lease':
                fcntl.fcntl(fd, fcntl.F_SETOWN, os.getpid())
                fcntl.fcntl(fd, fcntl.F_SETLEASE, fcntl.F_RDLCK)
            else:
                state = os.fstat(fd)
                # Effective-access checking includes ACLs; trusted-root status is
                # an explicit assumption, never a substitute for package leases.
                proc_path = '/proc/self/fd/' + str(fd)
                if os.geteuid() == 0 or state.st_uid != 0 or os.access(proc_path, os.W_OK, effective_ids=True):
                    raise ValueError('System image is not trusted-root-owned and read-only to this user')
            count, digest, _ = self._hash(fd, entry.size)
            if count != entry.size or digest != entry.sha256:
                raise ValueError('Dependency file SHA-256 or size differs')
            self._hashed.add(relative)
        if self._protection == 'linux_read_lease':
            if (fcntl.fcntl(fd, fcntl.F_GETLEASE) != fcntl.F_RDLCK or
                    fcntl.fcntl(fd, fcntl.F_GETOWN) != os.getpid()):
                raise RuntimeError('Dependency read lease broke or its owner changed')
        payload = None
        if copy_bytes:
            count, digest, payload = self._hash(fd, entry.size, copy_bytes=True)
            if count != entry.size or digest != entry.sha256:
                raise ValueError('Dependency copied bytes differ')
        if (_identity(os.fstat(fd)) != expected or
                _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
            raise RuntimeError('Dependency changed during byte read')
        self._owner._check_signal()
        return payload

    def _check_subtrees(self):
        if not self._census: return
        root_key = self.root.parts[1:]
        found = set(); namespace = []
        remaining = MAX_CENSUS_ENTRIES - sum(
            child._census_entries for child in self._owner._holders if child is not self)
        observed = 0
        def walk(key, relative):
            nonlocal observed
            if len(relative.split('/')) > 32:
                raise ValueError('Dependency namespace depth exceeds 32')
            directory = self._directory(key)
            names = []
            with os.scandir(directory) as items:
                for item in items:
                    self._clock()
                    if observed >= remaining:
                        raise ValueError('Dependency namespace census exceeds global bound')
                    observed += 1
                    names.append(item.name)
            names.sort()
            for name in names:
                self._clock()
                path = name if not relative else relative + '/' + name
                _relative(path)
                state = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if len(namespace) >= MAX_CENSUS_ENTRIES:
                    raise ValueError('Dependency namespace census exceeds global bound')
                namespace.append((path, _identity(state)))
                if stat.S_ISDIR(state.st_mode): walk((*key, name), path)
                elif stat.S_ISREG(state.st_mode): found.add(path)
                else: raise ValueError('Dependency namespace contains a symlink or nonregular entry')
        walk(root_key, '')
        self._census_entries = len(namespace)
        if sum(child._census_entries for child in self._owner._holders) > MAX_CENSUS_ENTRIES:
            raise ValueError('Dependency namespace census exceeds global bound')
        if found != set(self._entries): raise ValueError('Dependency namespace has extra or missing files')
        if self._namespace is None: self._namespace = namespace
        elif self._namespace != namespace: raise RuntimeError('Dependency namespace changed while held')


class HeldDependencyNamespace:
    """One-shot externally registered dependency custody, without public FDs.

    A single fresh main-thread SIGIO owner covers registration/package leases.
    Ceilings bound admitted bytes and serialized metadata, not RSS or hard WCET.
    """
    def __init__(self, registration_raw, *, expected_sha256, deadline, registration_path):
        self._state = 'new'; self._holders = []; self._registration_holder = None
        self._owner_pid = None; self._owner_thread = None; self._deferred_cleanup = False
        self._handler = None; self._break = False; self._census_count = 0
        self._deadline = deadline
        if (type(deadline) not in (int, float) or not math.isfinite(deadline)
                or not 0 < deadline - time.monotonic() <= 180):
            raise ValueError('Dependency deadline must be one future absolute deadline at most 180 seconds')
        self._raw = registration_raw
        self._sha256 = expected_sha256
        self._registration_path = _absolute(registration_path)
        self._registration = _decode(registration_raw, expected_sha256)
        self._validate()

    def _validate(self):
        reg = self._registration
        keys=('kind', 'version', 'roots', 'modules', 'namespaces', 'distributions')
        if type(reg) is dict and reg.get('version')==2: keys+=('import_profile',)
        _fields(reg, keys)
        if (type(reg['version']) is not int or reg['version'] not in (1,2)
                or reg['kind'] != 'puck-worker-dependencies-v'+str(reg['version'])):
            raise ValueError('Unknown dependency registration kind or version')
        for key in ('roots', 'modules', 'namespaces', 'distributions'):
            if type(reg[key]) is not list: raise ValueError('Dependency rows must be lists')
        if not 1 <= len(reg['roots']) <= 32: raise ValueError('Dependency root count exceeds bound')
        roots = []; total_files = total_bytes = 0
        for row in reg['roots']:
            _fields(row, ('root', 'kind', 'files')); root = _absolute(row['root'])
            if row['kind'] not in ('package', 'system_images'): raise ValueError('Unknown dependency root kind')
            if any(root == old or root.startswith(old + '/') or old.startswith(root + '/') for old in roots):
                raise ValueError('Dependency roots overlap')
            if self._registration_path == root or self._registration_path.startswith(root + '/'):
                raise ValueError('Dependency registration overlaps its namespace')
            roots.append(root)
            if type(row['files']) not in (list, tuple):
                raise ValueError('Dependency file descriptors must be an ordered collection')
            for entry in row['files']:
                if type(entry) is dict and type(entry.get('path')) is str and len(entry['path'].split('/')) > 32:
                    raise ValueError('Dependency file path depth exceeds 32')
            # Core construction validates every descriptor before any payload IO.
            _DependencyFiles(root, row['files'], self._deadline, self,
                'linux_read_lease' if row['kind'] == 'package' else 'trusted_root_readonly', census=row['kind'] == 'package')
            total_files += len(row['files']); total_bytes += sum(v['size_bytes'] for v in row['files'])
        if total_files > MAX_FILES or total_bytes > MAX_TOTAL_BYTES: raise ValueError('Dependency global input ceiling exceeded')
        attached_paths = [{v['path'] for v in row['files']} for row in reg['roots']]
        names = set()
        def attachment(row, field):
            index = row['root_index']
            if type(index) is not int or not 0 <= index < len(roots): raise ValueError('Dependency root index invalid')
            path = _relative(row[field])
            if path not in attached_paths[index]:
                raise ValueError('Dependency module or metadata is not attached to registered bytes')
            return index, path
        for row in reg['modules']:
            _fields(row, ('name', 'root_index', 'path', 'kind', 'is_package'))
            name = row['name']
            if type(name) is not str or not _NAME.fullmatch(name) or len(name) > 512 or name in names:
                raise ValueError('Dependency module name invalid or duplicate')
            if name.split('.')[0] in sys.stdlib_module_names: raise ValueError('Dependency cannot spoof a standard library module')
            names.add(name); index, path = attachment(row, 'path')
            if reg['roots'][index]['kind'] != 'package': raise ValueError('Dependency modules require a package root')
            if type(row['is_package']) is not bool or row['kind'] not in ('python', 'extension'):
                raise ValueError('Dependency module kind or package flag invalid')
            if row['kind'] == 'python':
                suffix = '/__init__.py' if row['is_package'] else '.py'
                if not path.endswith(suffix): raise ValueError('Dependency Python module suffix differs')
            elif not path.endswith(tuple(importlib.machinery.EXTENSION_SUFFIXES)):
                raise ValueError('Dependency extension requires a known native extension suffix')
        for row in reg['namespaces']:
            _fields(row, ('name', 'root_index', 'path')); name = row['name']
            if type(name) is not str or not _NAME.fullmatch(name) or len(name) > 512 or name in names:
                raise ValueError('Dependency namespace name invalid or duplicate')
            if name.split('.')[0] in sys.stdlib_module_names: raise ValueError('Dependency cannot spoof a standard library namespace')
            names.add(name)
            index = row['root_index']; path = _relative(row['path'])
            if type(index) is not int or not 0 <= index < len(roots) or reg['roots'][index]['kind'] != 'package':
                raise ValueError('Dependency namespace root invalid')
            if not any(v['path'].startswith(path + '/') for v in reg['roots'][index]['files']):
                raise ValueError('Dependency namespace has no attached leaves')
        packages = {v['name']: v for v in reg['modules'] if v['is_package']}
        packages.update({v['name']: v for v in reg['namespaces']})
        for row in reg['modules'] + reg['namespaces']:
            if '.' in row['name']:
                parent = packages.get(row['name'].rsplit('.', 1)[0])
                if parent is None or parent['root_index'] != row['root_index']:
                    raise ValueError('Dependency parent package map is missing or crosses roots')
                parent_path = parent['path'].rsplit('/', 1)[0] if parent.get('is_package') else parent['path']
                if not row['path'].startswith(parent_path + '/'):
                    raise ValueError('Dependency module is outside its declared package parent')
        distributions = set()
        for row in reg['distributions']:
            _fields(row, ('name', 'version', 'root_index', 'metadata_path')); attachment(row, 'metadata_path')
            if (type(row['name']) is not str or not _DIST.fullmatch(row['name']) or len(row['name']) > 512
                    or type(row['version']) is not str or not row['version'] or len(row['version']) > 512
                    or any(ord(c) < 33 or ord(c) == 127 for c in row['version'])):
                raise ValueError('Dependency distribution name or version invalid')
            normalized = re.sub(r'[-_.]+', '-', row['name']).lower()
            if normalized in distributions: raise ValueError('Duplicate dependency distribution')
            distributions.add(normalized)

        if reg['version']==2: validate_profile(reg['import_profile'],reg['modules'],reg['namespaces'])

    def _clock(self):
        if time.monotonic() >= self._deadline: raise TimeoutError('Dependency custody deadline exhausted')

    def _check_signal(self):
        self._check_owner()
        self._clock()
        if (_LEASE_OWNER is not self or self._break or signal.getsignal(signal.SIGIO) is not self._handler
                or signal.SIGIO in signal.pthread_sigmask(signal.SIG_BLOCK, [])):
            raise RuntimeError('Dependency lease notification owner, handler or signal mask changed')

    def _start_signal(self):
        global _LEASE_OWNER
        if (threading.current_thread() is not threading.main_thread() or _LEASE_OWNER is not None
                or signal.getsignal(signal.SIGIO) != signal.SIG_DFL
                or signal.SIGIO in signal.pthread_sigmask(signal.SIG_BLOCK, [])):
            raise RuntimeError('Dependency custody requires a fresh main-thread default unblocked SIGIO owner')
        self._owner_pid = os.getpid(); self._owner_thread = threading.get_ident()
        self._old_handler = signal.getsignal(signal.SIGIO)
        self._old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, [])
        def broken(signum, frame): self._break = True
        self._handler = broken
        _LEASE_OWNER = self
        signal.signal(signal.SIGIO, self._handler)

    def _close(self):
        global _LEASE_OWNER
        self._check_owner()
        errors = []
        for child in reversed(([self._registration_holder] if self._registration_holder else []) + self._holders):
            try:
                child._state = 'failed' if self._state == 'failed' else 'closed'
                child._close()
            except BaseException as error: errors.append(error)
        self._holders = []; self._registration_holder = None
        if _LEASE_OWNER is self:
            # Consume pending lease notifications while our handler still owns them.
            # No broad mask restoration: only SIGIO was reserved by this owner.
            signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGIO})
            while signal.SIGIO in signal.sigpending(): signal.sigwait({signal.SIGIO})
            signal.signal(signal.SIGIO, self._old_handler)
            signal.pthread_sigmask(
                signal.SIG_BLOCK if signal.SIGIO in self._old_mask else signal.SIG_UNBLOCK,
                {signal.SIGIO})
            _LEASE_OWNER = None
        if errors: raise errors[0]

    def _failed(self):
        self._state = 'failed'; self._close()

    def _is_owner(self):
        return (self._owner_pid is None or
                (os.getpid() == self._owner_pid and threading.get_ident() == self._owner_thread))

    def _check_owner(self):
        if not self._is_owner():
            raise RuntimeError('Dependency custody public operations require the original main thread and PID')

    def _poison(self, primary):
        if not self._is_owner():
            # Off-thread/fork misuse must never release another thread/process's
            # leases or install a signal handler. Original main-thread exit drains
            # these descriptors and restores notification ownership. A fork child
            # cannot perform that cleanup on behalf of its parent.
            self._state = 'failed'; self._deferred_cleanup = True
            return
        try: self._failed()
        except BaseException as cleanup:
            primary.add_note('Dependency cleanup also failed: ' + repr(cleanup))

    def _active(self):
        self._check_owner()
        if self._state != 'active': raise RuntimeError('Dependency custody is closed, failed or not entered')

    def __enter__(self):
        try:
            self._check_owner()
            if self._state != 'new': raise RuntimeError('Dependency custody can only be entered once')
            self._start_signal(); self._clock()
            path = Path(self._registration_path)
            descriptor = {'path': path.name, 'size_bytes': len(self._raw), 'sha256': self._sha256}
            self._registration_holder = _DependencyFiles(str(path.parent), [descriptor], self._deadline, self, 'linux_read_lease')
            self._registration_holder.__enter__()
            identities = {(v[3][0], v[3][1]) for v in self._registration_holder._files.values()}
            for row in self._registration['roots']:
                child = _DependencyFiles(row['root'], row['files'], self._deadline, self,
                    'linux_read_lease' if row['kind'] == 'package' else 'trusted_root_readonly', census=row['kind'] == 'package')
                self._holders.append(child); self._census_count = 0
                child.__enter__()
                for value in child._files.values():
                    identity = (value[3][0], value[3][1])
                    if identity in identities: raise ValueError('Dependency selected inode aliases cross roots or registration')
                    identities.add(identity)
            if len(_canonical(self._metadata())) + len(self._raw) > MAX_METADATA_BYTES:
                raise ValueError('Dependency serialized metadata exceeds 64 MiB')
            self._state = 'active'; self.recheck()
            for row in self._registration['distributions']:
                raw = self.read(row['root_index'], row['metadata_path'])
                raw.decode('utf-8')
                metadata = BytesParser().parsebytes(raw)
                if metadata.defects:
                    raise ValueError('Dependency distribution metadata is malformed')
                if (metadata.get_all('Name') != [row['name']] or metadata.get_all('Version') != [row['version']]):
                    raise ValueError('Dependency distribution metadata Name or Version differs')
            self.recheck(); return self
        except BaseException as error:
            self._poison(error); raise

    def _recheck(self):
        self._active(); self._check_signal(); self._census_count = 0
        self._registration_holder.recheck()
        for child in self._holders: child.recheck()
        self._check_signal()

    def recheck(self):
        try: self._recheck()
        except BaseException as error: self._poison(error); raise

    def require_absent_imports(self, names):
        """Prove finite exact import names absent from the held package forest."""
        try:
            self._recheck()
            if (type(names) is not tuple or not 1 <= len(names) <= 128 or any(
                    type(name) is not str or len(name) > 512 or not _NAME.fullmatch(name)
                    or name.split('.')[0] in sys.stdlib_module_names for name in names)):
                raise ValueError('Absent imports require a bounded tuple of exact nonstdlib names')
            if names != tuple(sorted(set(names))) or any(
                    name.startswith(parent + '.') for index, name in enumerate(names) for parent in names[:index]):
                raise ValueError('Absent imports must be sorted, unique and nonoverlapping')
            reg = self._registration
            declared = {row['name'] for row in reg['modules'] + reg['namespaces']}
            declared.update(row['name'] for row in reg.get('import_profile', {}).get('exports', []))
            packages = {row['name']:row for row in reg['modules'] if row['is_package']}
            packages.update({row['name']:row for row in reg['namespaces']})
            censuses = {index:{path for path, identity in child._namespace}
                for index, child in enumerate(self._holders) if reg['roots'][index]['kind'] == 'package'}
            suffixes = ('.py', '.pyc', *importlib.machinery.EXTENSION_SUFFIXES)
            for name in names:
                self._check_signal()
                if any(known == name or known.startswith(name + '.') for known in declared):
                    raise ValueError('Absent import overlaps a registered module, namespace or export: ' + name)
                candidates = {(index, name.replace('.', '/')) for index in censuses}
                parent_name, dot, leaf = name.rpartition('.')
                if dot:
                    parent = packages.get(parent_name)
                    if parent is None:
                        raise ValueError('Absent import parent is not a registered package or namespace: ' + name)
                    directory = parent['path'].rpartition('/')[0] if parent.get('is_package') else parent['path']
                    candidates.add((parent['root_index'], directory + '/' + leaf if directory else leaf))
                for index, stem in candidates:
                    self._check_signal()
                    paths = censuses[index]
                    directory, slash, leaf = stem.rpartition('/')
                    cache = (directory + '/' if slash else '') + '__pycache__/' + leaf + '.'
                    if (stem in paths or any(stem + suffix in paths for suffix in suffixes) or any(
                            path.startswith(cache) and path.endswith('.pyc') and '/' not in path[len(cache):]
                            for path in paths)):
                        raise ValueError('Absent import has a physical package namespace alternative: ' + name)
            self._check_signal()
        except BaseException as error: self._poison(error); raise

    def _target_recheck(self, child, path):
        self._active(); self._check_signal()
        # Per-import consumption checks only its held ancestor chain and leaf.
        # Full namespace/all-lease checks remain explicit at admission, native
        # initializer boundaries and terminal close; this is not an atomic
        # simultaneous forest observation on every Python import.
        parts = (*child.root.parts[1:], *path.split('/')[:-1])
        for length in range(len(parts) + 1):
            fd, parent, name, expected = child._dirs[parts[:length]]
            self._check_signal()
            if (_identity(os.fstat(fd)) != expected or
                    _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
                raise RuntimeError('Dependency target ancestor edge changed')
        child._check_file(path)
        self._check_signal()

    def read(self, root_index, path, max_bytes=4 * MiB):
        """Copy/hash a targeted held leaf; full forest checks use recheck()."""
        try:
            self._active(); self._check_signal()
            if type(root_index) is not int or not 0 <= root_index < len(self._holders):
                raise ValueError('Dependency read root index invalid')
            path = _relative(path)
            if type(max_bytes) is not int or not 0 <= max_bytes <= 4 * MiB:
                raise ValueError('Dependency copy cap must be an integer at most four MiB')
            child = self._holders[root_index]
            if path not in child._entries: raise ValueError('Dependency read path unregistered')
            if child._entries[path].size > max_bytes: raise ValueError('Dependency read exceeds copy ceiling')
            self._target_recheck(child, path)
            payload = child._check_file(path, copy_bytes=True)
            self._target_recheck(child, path)
            return payload
        except BaseException as error: self._poison(error); raise

    def _metadata(self):
        return {'registration_sha256': self._sha256, 'registration_bytes': len(self._raw),
            'registration': self._registration, 'roots': [
                {'root': str(child.root), 'protection': child._protection,
                 'directories': [[parts, value[2], value[3]] for parts, value in sorted(child._dirs.items())],
                 'files': [[path, value[2], value[3]] for path, value in sorted(child._files.items())],
                 'namespace': child._namespace}
                for child in [self._registration_holder] + self._holders]}

    def _metadata_size(self):
        size = len(_canonical(self._metadata())) + len(self._raw)
        if size > MAX_METADATA_BYTES:
            raise ValueError('Dependency serialized metadata exceeds 64 MiB')
        return size

    def retained_metadata_size_bytes(self):
        try:
            self._recheck(); size = self._metadata_size()
            self._recheck(); return size
        except BaseException as error: self._poison(error); raise

    def _records(self, kind):
        try:
            self._recheck(); size = self._metadata_size()
            result = copy.deepcopy(self._registration.get(kind,
                {'exports':[], 'module_changes':[], 'native_origins':[]}))
            if size + len(_canonical(result)) > MAX_METADATA_BYTES:
                raise ValueError('Dependency returned metadata exceeds global ceiling')
            self._recheck(); return result
        except BaseException as error: self._poison(error); raise

    def module_records(self): return self._records('modules')
    def namespace_records(self): return self._records('namespaces')
    def distribution_records(self): return self._records('distributions')
    def import_profile(self): return self._records('import_profile')

    def snapshot(self):
        try:
            self._recheck()
            receipt = {'kind': 'puck-worker-dependency-custody-v1', 'registration_sha256': self._sha256,
                'root_count': len(self._holders), 'file_count': sum(len(v._entries) for v in self._holders),
                'input_bytes': sum(v.size for h in self._holders for v in h._entries.values()),
                'registration_bytes': len(self._raw),
                'protection_modes': [v._protection for v in self._holders],
                'external_hardlink_names_covered': False, 'hostile_root_protection': False,
                'runtime_qualified': False, 'source_closure': False, 'collection_authorized': False,
                'reservation_authorized': False, 'executable': False, 'claims': []}
            if self._metadata_size() + len(_canonical(receipt)) > MAX_METADATA_BYTES:
                raise ValueError('Dependency receipt exceeds metadata bound')
            self._recheck(); return receipt
        except BaseException as error: self._poison(error); raise

    def __exit__(self, kind, error, traceback):
        try:
            self._check_owner()
        except BaseException as failure:
            self._poison(failure); raise
        if self._state != 'active':
            if self._deferred_cleanup:
                self._deferred_cleanup = False
                self._close()
            if kind is None: raise RuntimeError('Dependency custody failed before context exit')
            return False
        primary = None
        try:
            self._recheck()
        except BaseException as failure:
            primary = failure; self._state = 'failed'
            raise
        finally:
            if self._state == 'active': self._state = 'closed'
            try: self._close()
            except BaseException as cleanup:
                if primary is None: raise
                primary.add_note('Dependency cleanup also failed: ' + repr(cleanup))
        return False
