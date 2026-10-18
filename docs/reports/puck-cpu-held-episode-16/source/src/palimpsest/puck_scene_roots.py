"""Bounded, metadata-only custody of an explicitly declared search namespace.

Candidate names are hints, not repository validation, retained-schema coverage,
payload authentication, executable admission, or a complete machine inventory.
Held directory descriptors and repeated namespace observations detect drift;
they do not provide an atomic filesystem snapshot or a hostile-process sandbox.
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

MAX_CONTRACT_BYTES = 64 * 1024
MAX_SEARCH_ROOTS = 32
MAX_OPAQUE_SUBTREES = 1024
MAX_REASON_BYTES = 1024
MAX_DEPTH = 32
MAX_DIRECTORIES = 8192
MAX_ENTRIES = 65536
MAX_METADATA_BYTES = 64 * 1024 ** 2


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Root contract has duplicate JSON keys')
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError('Root contract has nonfinite JSON numbers')


def _absolute(value):
    if (type(value) is not str or not value.startswith('/') or value.startswith('//')
            or value != str(PurePosixPath(value))
            or any(part in ('.', '..') for part in value.split('/'))
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise ValueError('Root paths must be canonical absolute paths')
    try:
        value.encode('utf-8')
    except UnicodeError as error:
        raise ValueError('Root paths must be UTF-8 text') from error
    return value


def _under(path, root):
    return path != root and (root == '/' or path.startswith(root + '/'))


def _nonoverlapping(paths):
    for index, path in enumerate(paths):
        if any(path == other or _under(path, other) or _under(other, path)
               for other in paths[:index]):
            raise ValueError('Root contract paths overlap or repeat')


def _contract(raw, expected):
    if type(raw) is not bytes or len(raw) > MAX_CONTRACT_BYTES:
        raise ValueError('Root contract must be bounded raw bytes')
    if type(expected) is not str or not re.fullmatch('[0-9a-f]{64}', expected):
        raise ValueError('Root contract requires an external canonical SHA-256')
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError('Root contract SHA-256 mismatch')
    try:
        document = json.loads(raw.decode('utf-8'), object_pairs_hook=_pairs,
                              parse_constant=_nonfinite)
        canonical = _json(document)
    except (UnicodeError, json.JSONDecodeError, RecursionError, OverflowError) as error:
        raise ValueError('Root contract is not canonical strict JSON') from error
    if canonical != raw:
        raise ValueError('Root contract is not canonical strict JSON')
    if (type(document) is not dict
            or set(document) != {'id', 'version', 'search_roots', 'opaque_subtrees'}
            or document['id'] != 'puck-scene-root-search-v1'
            or type(document['version']) is not int or document['version'] != 1):
        raise ValueError('Root contract has an unsupported exact schema')
    roots, opaque = document['search_roots'], document['opaque_subtrees']
    if type(roots) is not list or not 1 <= len(roots) <= MAX_SEARCH_ROOTS:
        raise ValueError('Root contract search-root count exceeds its bound')
    roots = [_absolute(path) for path in roots]
    _nonoverlapping(roots)
    if any('.git' in PurePosixPath(root).parts[:-1] for root in roots):
        raise ValueError('Search roots cannot enter opaque Git control storage')
    if type(opaque) is not list or len(opaque) > MAX_OPAQUE_SUBTREES:
        raise ValueError('Root contract opaque count exceeds its bound')
    paths = []
    for row in opaque:
        if type(row) is not dict or set(row) != {'path', 'reason'}:
            raise ValueError('Root contract opaque row has unsupported keys')
        path = _absolute(row['path'])
        owners = [root for root in roots if _under(path, root)]
        if len(owners) != 1:
            raise ValueError('Opaque directories must be below exactly one search root')
        reason = row['reason']
        if (type(reason) is not str or not reason.strip()
                or any(ord(char) < 32 or ord(char) == 127 for char in reason)):
            raise ValueError('Opaque reason must be nonempty bounded text')
        try:
            if len(reason.encode('utf-8')) > MAX_REASON_BYTES:
                raise ValueError('Opaque reason exceeds its fixed bound')
        except UnicodeError as error:
            raise ValueError('Opaque reason must be UTF-8 text') from error
        # A declaration cannot force inspection below automatically opaque Git
        # storage. Refuse the conflicting scope rather than silently ignoring it.
        relative = PurePosixPath(path).relative_to(owners[0])
        if '.git' in relative.parts[:-1] or PurePosixPath(owners[0]).name == '.git':
            raise ValueError('Opaque declaration is below opaque Git control storage')
        paths.append(path)
    _nonoverlapping(paths)
    return document


def _edge(value):
    return value.st_dev, value.st_ino, value.st_mode


def _metadata(value):
    return (_edge(value) + (value.st_size, value.st_mtime_ns,
                           value.st_ctime_ns, value.st_nlink))


class HeldSceneInventoryRoots:
    """Single-use root-search custody context; no leaf open or Git invocation.

    ``deadline`` uses the absolute monotonic clock and covers discovery,
    snapshots, rechecks, and successful close. Opaque directory contents are
    deliberately outside observation; only their dev/inode/mode edges are held.
    """

    def __init__(self, contract_raw: bytes, *, expected_sha256: str, deadline: float):
        now = time.monotonic()
        if (type(deadline) not in (int, float) or not math.isfinite(deadline)
                or deadline <= now or deadline > now + 600):
            raise ValueError('Root discovery requires a finite deadline within ten minutes')
        self._contract = _contract(contract_raw, expected_sha256)
        self._deadline = deadline
        self._digest = expected_sha256
        self._started = self._closed = self._failed = False
        self._fds = []
        self._dirs = {}
        self._aliases = {}
        self._namespaces = {}
        self._opaque = {row['path'] for row in self._contract['opaque_subtrees']}
        self._budget = 0
        self._receipt = None

    def _clock(self):
        if time.monotonic() >= self._deadline:
            raise TimeoutError('Root discovery deadline exhausted')

    def _charge(self, value):
        self._budget += len(_json(value))
        if self._budget > MAX_METADATA_BYTES:
            raise ValueError('Root discovery metadata exceeds its fixed bound')

    def _directory(self, path, expected=None, *, opaque=False):
        """Hold each ancestor edge without resolving symlinks or reading names."""
        parts = PurePosixPath(path).parts
        parent = None
        current = ''
        for name in parts:
            self._clock()
            current = '/' if name == '/' else current.rstrip('/') + '/' + name
            if current not in self._dirs:
                if len(self._fds) >= MAX_DIRECTORIES:
                    raise ValueError('Root discovery directories exceed their fixed bound')
                fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                             dir_fd=parent)
                self._fds.append(fd)
                observed = os.fstat(fd)
                edge = _edge(observed)
                if not stat.S_ISDIR(observed.st_mode):
                    raise ValueError('Root discovery paths must be directories')
                if edge != _edge(os.stat(name, dir_fd=parent, follow_symlinks=False)):
                    raise RuntimeError('Root directory changed during open')
                alias = self._aliases.get(edge[:2])
                if alias is not None and alias != current:
                    raise ValueError('Root discovery refuses directory aliases')
                self._aliases[edge[:2]] = current
                self._dirs[current] = (fd, parent, name, edge)
                self._charge([current, edge])
            parent = self._dirs[current][0]
        if expected is not None:
            actual = _edge(os.fstat(parent)) if opaque else _metadata(os.fstat(parent))
            if actual != (expected[:3] if opaque else expected):
                raise RuntimeError('Root directory metadata changed during traversal')
        return parent

    def _listing(self, path, counts):
        """Bounded streaming metadata enumeration, omitting opaque contents."""
        self._clock()
        fd = self._dirs[path][0]
        before = _metadata(os.fstat(fd))
        entries = []
        with os.scandir(fd) as stream:
            for entry in stream:
                self._clock()
                counts[0] += 1
                if counts[0] > MAX_ENTRIES:
                    raise ValueError('Root discovery entries exceed their fixed bound')
                name = entry.name
                try:
                    name.encode('utf-8')
                except UnicodeError as error:
                    raise ValueError('Root entry names must be UTF-8 text') from error
                if any(ord(char) < 32 or ord(char) == 127 for char in name):
                    raise ValueError('Root entry names must be canonical text')
                observed = os.stat(name, dir_fd=fd, follow_symlinks=False)
                child = path.rstrip('/') + '/' + name
                is_directory = stat.S_ISDIR(observed.st_mode)
                if not is_directory and not stat.S_ISREG(observed.st_mode):
                    raise ValueError('Root traversal refuses symlinks and nonregular entries')
                identity = _metadata(observed)
                # Directory timestamps/size reflect deliberately unobserved
                # contents. They cannot authenticate opaque payload namespaces.
                opaque = is_directory and (child in self._opaque or name == '.git')
                digest_identity = _edge(observed) if opaque else identity
                row = [name, list(digest_identity)]
                counts[1] += len(_json(row))
                if counts[1] > MAX_METADATA_BYTES:
                    raise ValueError('Root discovery metadata exceeds its fixed bound')
                entries.append((name, identity, opaque, row))
        self._clock()
        after = _metadata(os.fstat(fd))
        if before != after:
            raise RuntimeError('Root namespace changed while listing directory')
        entries.sort(key=lambda item: item[0])
        digest = hashlib.sha256(_json([row[3] for row in entries])).hexdigest()
        return entries, (before, digest)

    def _discover(self):
        repositories, retained, git_storage = [], {}, []
        documents, unsupported_git = [], []
        for path in self._opaque:
            root = next(root for root in self._contract['search_roots'] if _under(path, root))
            if len(PurePosixPath(path).relative_to(root).parts) > MAX_DEPTH:
                raise ValueError('Root discovery opaque depth exceeds its fixed bound')
        for root in self._contract['search_roots']:
            self._directory(root)
        # Resolve every explicit exclusion before discovery; absent exclusions
        # are errors, even when nothing would otherwise reach their names.
        for path in sorted(self._opaque):
            self._directory(path)
        counts = [0, 0]
        pending = [(root, 0, None, root) for root in reversed(self._contract['search_roots'])]
        while pending:
            self._clock()
            path, depth, expected, root = pending.pop()
            if depth > MAX_DEPTH:
                raise ValueError('Root discovery depth exceeds its fixed bound')
            self._directory(path, expected)
            base = PurePosixPath(path).name
            if base == '.git':
                repositories.append({'path': str(PurePosixPath(path).parent),
                                     'marker_path': path, 'marker_kind': 'directory'})
                git_storage.append({'path': path, 'marker_kind': 'directory',
                                    'contents_authenticated': False})
                continue
            hints = set()
            if base in {'runs', 'registry', 'registries', 'evidence'} or base.endswith('-evidence'):
                hints.add(base)
            entries, namespace = self._listing(path, counts)
            self._namespaces[path] = namespace
            bare_markers = set()
            for name, identity, opaque, _ in entries:
                self._clock()
                child = path.rstrip('/') + '/' + name
                is_directory = stat.S_ISDIR(identity[2])
                if ((name == 'HEAD' and not is_directory)
                        or (name in {'objects', 'refs'} and is_directory)):
                    bare_markers.add(name)
                if name == '.git':
                    kind = 'directory' if is_directory else 'regular_file'
                    repositories.append({'path': path, 'marker_path': child, 'marker_kind': kind})
                    git_storage.append({'path': child, 'marker_kind': kind,
                                        'contents_authenticated': False})
                if is_directory:
                    if depth + 1 > MAX_DEPTH:
                        raise ValueError('Root discovery depth exceeds its fixed bound')
                    if opaque:
                        self._directory(child, identity, opaque=True)
                        if name in {'runs', 'registry', 'registries', 'evidence'} or name.endswith('-evidence'):
                            retained[child] = [name]
                    else:
                        pending.append((child, depth + 1, identity, root))
                elif (name in {'manifest.json', 'registry.json', 'reservation.json', 'index.json'}
                      or name.endswith('-manifest.json') or name.endswith('-registry.json')):
                    hints.add(name)
                if not is_directory and name.lower().endswith(('.json', '.md')):
                    # Candidate paths must be portable unambiguous descriptor
                    # paths; unrelated namespace names keep their prior rules.
                    if ':' in child or '\\' in child:
                        raise ValueError('Document candidate paths must be canonical absolute paths')
                    _absolute(child)
                    candidate = {
                        'path': child, 'search_root': root,
                        'relpath': str(PurePosixPath(child).relative_to(root)),
                        'size_bytes': identity[3], 'stat_identity': list(identity),
                    }
                    self._charge(candidate)
                    documents.append(candidate)
            if bare_markers == {'HEAD', 'objects', 'refs'}:
                candidate = {
                    'path': path, 'search_root': root, 'marker_kind': 'bare',
                    'reason': 'HEAD regular file plus objects and refs directories',
                    'contents_authenticated': False,
                }
                self._charge(candidate)
                unsupported_git.append(candidate)
            if hints:
                retained[path] = sorted(hints)
        self._budget += counts[1]
        self._receipt = {
            'id': 'puck-scene-root-inventory-receipt-v1', 'version': 1,
            'contract_sha256': self._digest,
            'search_roots': list(self._contract['search_roots']),
            'repository_candidates': sorted(repositories, key=lambda row: row['path']),
            'document_candidates': sorted(documents, key=lambda row: row['path']),
            'unsupported_git_candidates': sorted(unsupported_git, key=lambda row: row['path']),
            'retained_root_candidates': [{'path': path, 'hints': hints}
                                         for path, hints in sorted(retained.items())],
            'excluded_scope': [dict(row, contents_authenticated=False)
                               for row in self._contract['opaque_subtrees']],
            'git_control_storage': sorted(git_storage, key=lambda row: row['path']),
            'observed_directories': [
                {'path': path, 'namespace_sha256': namespace[1]}
                for path, namespace in sorted(self._namespaces.items())],
            'observed_entry_count': counts[0],
            'held_directory_count': len(self._fds),
            'inventory_complete': False, 'all_repositories_discovered': False,
            'retained_roots_discovered': False, 'executable': False,
            'native_authorized': False, 'collection_authorized': False,
            'qualification_claims': [], 'payload_reads': 0,
            'declared_scope_namespace_stable': True,
            'contents_authenticated': False,
            'candidate_hints_only': True,
            'namespace_stability_boundary': 'descriptor-held checks; no atomic snapshot or post-close proof',
        }
        self._charge(self._receipt)

    def _active(self):
        if not self._started or self._closed or self._failed:
            raise RuntimeError('Root inventory context is inactive or poisoned')

    def _recheck(self):
        self._clock()
        self._check_edges()
        counts = [0, 0]
        for path, expected in self._namespaces.items():
            _, actual = self._listing(path, counts)
            if actual != expected:
                raise RuntimeError('Root namespace metadata changed')
        self._check_edges()
        self._clock()

    def _check_edges(self):
        for fd, parent, name, identity in self._dirs.values():
            self._clock()
            if (_edge(os.fstat(fd)) != identity
                    or _edge(os.stat(name, dir_fd=parent, follow_symlinks=False)) != identity):
                raise RuntimeError('Root directory edge changed')

    def _close(self, primary=None):
        errors = []
        for fd in reversed(self._fds):
            try:
                os.close(fd)
            except BaseException as error:
                errors.append(error)
        self._fds.clear()
        self._closed = True
        if errors:
            message = 'Root descriptor cleanup failed: ' + '; '.join(str(error) for error in errors)
            if primary is not None:
                primary.add_note(message)
            else:
                self._failed = True
                raise RuntimeError(message) from errors[0]

    def __enter__(self):
        if self._started or self._closed or self._failed:
            error = RuntimeError('Root inventory context cannot be reused')
            self._failed = True
            self._close(error)
            raise error
        self._started = True
        try:
            self._clock()
            self._discover()
            self._recheck()
            return self
        except BaseException as error:
            self._failed = True
            self._close(error)
            raise

    def retained_metadata_size_bytes(self):
        """Count bounded discovery/state metadata without exposing descriptors."""
        try:
            self._active(); self._recheck()
            state = {'contract': self._contract, 'receipt': self._receipt,
                'directories': [[path, name, identity] for path, (_, _, name, identity) in sorted(self._dirs.items())],
                'namespaces': sorted(self._namespaces.items())}
            size = max(self._budget, len(_json(state)))
            if size > MAX_METADATA_BYTES:
                raise ValueError('Root retained metadata exceeds its fixed bound')
            self._recheck(); return size
        except BaseException as error:
            self._failed = True; self._close(error); raise

    def recheck(self):
        try:
            self._active()
            self._recheck()
        except BaseException as error:
            self._failed = True
            self._close(error)
            raise

    def snapshot(self):
        self.recheck()
        try:
            result = copy.deepcopy(self._receipt)
            self._recheck()
            self._clock()
            return result
        except BaseException as error:
            self._failed = True
            self._close(error)
            raise

    def __exit__(self, exc_type, exc, traceback):
        if self._closed:
            return False
        try:
            self._recheck()
        except BaseException as error:
            self._failed = True
            if exc is not None:
                exc.add_note('Root inventory final drift check failed: ' + str(error))
            else:
                self._close(error)
                raise
        if exc is not None:
            self._failed = True
        self._close(exc)
        try:
            self._clock()
        except BaseException as error:
            self._failed = True
            if exc is not None:
                exc.add_note('Root inventory final deadline check failed: ' + str(error))
            else:
                raise
        return False
