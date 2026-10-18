"""Bounded read-only discovery of one named repository's Git document closure.

Git's object store is trusted for immutable object semantics, with document
payloads additionally verified against their Git OIDs. This is operational
source custody, not a hostile-process sandbox, a complete inventory of all
repositories/retained roots, or scene/native/bootstrap admission. The external
Git binary, transport and full runtime still require the owner's exact freeze.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import subprocess
import time

MAX_REFS = MAX_COMMITS = MAX_BLOBS = 4096
MAX_DOCUMENT_BYTES = 4 * 1024 ** 2
MAX_METADATA_BYTES = 64 * 1024 ** 2
MAX_COMMAND_STDOUT = 8 * 1024 ** 2
MAX_COMMAND_STDERR = 64 * 1024
MAX_NAMESPACE_ENTRIES = 16384
MAX_TREE_ENTRIES = 65536
MAX_TREES = 65536
MAX_WORKTREES = 4096


def _clock(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError('Git source discovery deadline exhausted')


def _group_alive(pgid):
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False


def _signal_group(pgid, sig):
    try:
        os.killpg(pgid, sig)
    except ProcessLookupError:
        pass


def _bounded_command(argv, *, cwd, env, deadline,
                     stdout_cap=MAX_COMMAND_STDOUT, stderr_cap=MAX_COMMAND_STDERR):
    """Capped pipes, bounded kill/direct-leader reap/owned-PG absence observation.

    Cleanup has a fixed one-second allowance on failure; successful completion
    must still precede the caller's absolute deadline. No shell or unbounded
    communicate/read is used. A leader exiting with survivors is a failure.
    """
    _clock(deadline)
    process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    selector = selectors.DefaultSelector()
    result = {'stdout': bytearray(), 'stderr': bytearray()}
    caps = {'stdout': stdout_cap, 'stderr': stderr_cap}
    failed = None
    try:
        for name, stream in (('stdout', process.stdout), ('stderr', process.stderr)):
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        while selector.get_map() or process.poll() is None:
            _clock(deadline)
            if process.poll() is not None and _group_alive(process.pid):
                raise RuntimeError('Git command leader exited with surviving process group')
            for key, _ in selector.select(min(.05, max(0, deadline - time.monotonic()))):
                name = key.data
                block = os.read(key.fileobj.fileno(), min(65536, caps[name] + 1 - len(result[name])))
                if not block:
                    selector.unregister(key.fileobj)
                    continue
                result[name].extend(block)
                if len(result[name]) > caps[name]:
                    raise ValueError('Git command ' + name + ' exceeds its fixed cap')
        if _group_alive(process.pid):
            raise RuntimeError('Git command left surviving process-group members')
        _clock(deadline)
        if process.returncode != 0:
            raise ValueError('Git command failed: ' + bytes(result['stderr']).decode('utf-8', 'replace')[:512])
        return bytes(result['stdout'])
    except BaseException as error:
        failed = error
        raise
    finally:
        cleanup_end = time.monotonic() + 1
        cleanup_errors = []
        cleanup_needed = False
        try:
            cleanup_needed = process.poll() is None or _group_alive(process.pid)
            if cleanup_needed:
                _signal_group(process.pid, signal.SIGTERM)
                # Bounded drain protects against a child blocked writing a full pipe.
                until = min(cleanup_end, time.monotonic() + .1)
                while time.monotonic() < until and process.poll() is None:
                    for key, _ in selector.select(min(.01, max(0, until - time.monotonic()))):
                        try: block = os.read(key.fileobj.fileno(), 65536)
                        except BlockingIOError: continue
                        if not block: selector.unregister(key.fileobj)
        except BaseException as error: cleanup_errors.append(error)
        try:
            if cleanup_needed or process.poll() is None or _group_alive(process.pid):
                _signal_group(process.pid, signal.SIGKILL)
        except BaseException as error: cleanup_errors.append(error)
        try: process.wait(timeout=max(0, cleanup_end - time.monotonic()))
        except BaseException as error: cleanup_errors.append(error)
        # Observe the owned PG after KILL as well as the direct leader's reap.
        # Grandchildren can be reparented; this is absence observation, never
        # a claim that this process reaped them or prevents hostile escape.
        try:
            alive = _group_alive(process.pid)
            while alive and time.monotonic() < cleanup_end:
                timeout = min(.01, max(0, cleanup_end - time.monotonic()))
                if selector.get_map():
                    for key, _ in selector.select(timeout):
                        try: block = os.read(key.fileobj.fileno(), 65536)
                        except BlockingIOError: continue
                        if not block: selector.unregister(key.fileobj)
                elif timeout:
                    time.sleep(timeout)
                alive = _group_alive(process.pid)
            if alive:
                cleanup_errors.append(RuntimeError('owned process group remains observable after KILL'))
        except BaseException as error: cleanup_errors.append(error)
        for stream in (process.stdout, process.stderr):
            try: stream.close()
            except BaseException as error: cleanup_errors.append(error)
        try: selector.close()
        except BaseException as error: cleanup_errors.append(error)
        if cleanup_errors:
            message = 'Git command cleanup failed: ' + '; '.join(str(error) for error in cleanup_errors)
            if failed is not None:
                failed.add_note(message)
            else:
                raise RuntimeError(message) from cleanup_errors[0]
        if failed is None:
            _clock(deadline)


def _absolute(value):
    raw = os.fspath(value)
    if (type(raw) is not str or not raw.startswith('/') or raw.startswith('//') or raw != str(Path(raw))
            or any(part in ('.', '..') for part in raw.split('/'))
            or any(ord(char) < 32 or ord(char) == 127 for char in raw)):
        raise ValueError('Git source paths must be canonical absolute paths')
    return raw


def _relative(value):
    if (not value or value.startswith('/') or '\\' in value or ':' in value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Tracked Git path is not canonical relative POSIX text')
    return value


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink)


def _directory_identity(value):
    # Ancestor directories may contain unrelated active work. The complete Git
    # namespace and worktree roots separately use full metadata identities.
    return value.st_dev, value.st_ino, value.st_mode


class _HeldNamespace:
    def __init__(self, deadline):
        self.deadline = deadline
        self.dirs, self.files, self.namespace = {}, {}, {}

    def directory(self, path, *, exact=False):
        _clock(self.deadline)
        path = _absolute(path)
        if path not in self.dirs:
            if path == '/': parent, name = None, '/'
            else: parent, name = self.directory(str(Path(path).parent)), Path(path).name
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            observed = os.fstat(fd)
            self.dirs[path] = (fd, parent, name, _directory_identity(observed))
            if _identity(observed) != _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)):
                raise RuntimeError('Git directory changed during open')
        if exact:
            self._remember(path, _identity(os.fstat(self.dirs[path][0])))
        return self.dirs[path][0]

    def _remember(self, path, identity):
        if path in self.namespace and self.namespace[path] != identity:
            raise RuntimeError('Git source metadata changed')
        self.namespace[path] = identity
        if len(self.namespace) > MAX_NAMESPACE_ENTRIES:
            raise ValueError('Git namespace exceeds its fixed entry cap')

    def file(self, path):
        _clock(self.deadline)
        path = _absolute(path)
        if path not in self.files:
            parent = self.directory(str(Path(path).parent))
            name = Path(path).name
            fd = os.open(name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=parent)
            self.files[path] = (fd, parent, name, _identity(os.fstat(fd)))
            observed = os.fstat(fd)
            if not stat.S_ISREG(observed.st_mode):
                raise ValueError('Git source entries must be regular files or directories')
            if _identity(observed) != _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)):
                raise RuntimeError('Git file changed during open')
        self._remember(path, self.files[path][3])
        return self.files[path][0]

    def walk(self, root):
        """Hold every common-directory edge, with finite depth/count/work."""
        found = {}
        pending = [(root, 0)]
        while pending:
            path, depth = pending.pop()
            if depth > 64:
                raise ValueError('Git namespace exceeds its fixed depth cap')
            fd = self.directory(path, exact=True)
            found[path] = _identity(os.fstat(fd))
            with os.scandir(fd) as entries:
                for entry in entries:
                    _clock(self.deadline)
                    if len(found) + len(pending) >= MAX_NAMESPACE_ENTRIES:
                        raise ValueError('Git namespace exceeds its fixed entry cap')
                    child = path + '/' + _relative(entry.name)
                    observed = entry.stat(follow_symlinks=False)
                    if stat.S_ISDIR(observed.st_mode): pending.append((child, depth + 1))
                    elif stat.S_ISREG(observed.st_mode):
                        self.file(child)
                        found[child] = _identity(observed)
                        if found[child] != self.files[child][3]:
                            raise RuntimeError('Git namespace file changed during enumeration')
                    else: raise ValueError('Git namespace contains a symlink or special entry')
        return found

    def check(self):
        for fd, parent, name, expected in self.dirs.values():
            _clock(self.deadline)
            if (_directory_identity(os.fstat(fd)) != expected
                    or _directory_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
                raise RuntimeError('Git source directory edge changed')
        for fd, parent, name, expected in self.files.values():
            _clock(self.deadline)
            if (_identity(os.fstat(fd)) != expected
                    or _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
                raise RuntimeError('Git source file identity changed')
        for path, expected in self.namespace.items():
            _clock(self.deadline)
            if _identity(os.lstat(path)) != expected:
                raise RuntimeError('Git namespace identity changed')

    def close(self, *, final_check=False):
        first = None
        for fd, _, _, _ in reversed(list(self.files.values())):
            try: os.close(fd)
            except OSError as error: first = first or error
        self.files.clear()
        if final_check:
            try:
                for path, expected in self.namespace.items():
                    _clock(self.deadline)
                    if _identity(os.lstat(path)) != expected:
                        raise RuntimeError('Git source changed through descriptor close')
                for path, (fd, parent, name, expected) in self.dirs.items():
                    if (_directory_identity(os.fstat(fd)) != expected
                            or _directory_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
                        raise RuntimeError('Git directory changed through descriptor close')
            except BaseException as error: first = first or error
        identities = {path: row[3] for path, row in self.dirs.items()}
        for fd, _, _, _ in reversed(list(self.dirs.values())):
            try: os.close(fd)
            except OSError as error: first = first or error
        self.dirs.clear()
        if final_check and first is None:
            try:
                for path, expected in identities.items():
                    _clock(self.deadline)
                    if _directory_identity(os.lstat(path)) != expected:
                        raise RuntimeError('Git ancestor changed after descriptor close')
                for path, expected in self.namespace.items():
                    _clock(self.deadline)
                    if _identity(os.lstat(path)) != expected:
                        raise RuntimeError('Git source changed after descriptor close')
            except BaseException as error: first = error
        if first is not None: raise first


class HeldGitSceneSources:
    """One-shot custody of discovered Git sources; all failure paths poison it.

    ``snapshot()`` returns detached descriptor evidence without opening document
    payloads. Only explicit ``read_blob(oid)`` exposes discovered JSON/Markdown
    bytes and records their observed SHA-256; this requires the consumer's
    separately authorized catalog/projection boundary. ``recheck()`` rediscovers refs,
    fresh advertisements, worktrees and complete reachable document closure.
    Keep the context open through the consumer's final source decision.
    """
    def __init__(self, repo, *, remote, expected_remote_url, deadline):
        self.repo = _absolute(repo)
        if (type(remote) is not str or not remote or remote.startswith('-')
                or any(char not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-' for char in remote)):
            raise ValueError('Git remote must be a canonical configured remote name')
        if (type(expected_remote_url) is not str or not expected_remote_url
                or any(ord(char) < 32 or ord(char) == 127 for char in expected_remote_url)):
            raise ValueError('Git remote URL requires exact nonempty text')
        if (type(deadline) not in (int, float) or not math.isfinite(deadline)
                or deadline > time.monotonic() + 600):
            raise ValueError('Git deadline must be finite and within ten minutes')
        _clock(deadline)
        self.remote, self.expected_remote_url, self.deadline = remote, expected_remote_url, deadline
        self._state, self._held, self._evidence, self._blobs = 'new', _HeldNamespace(deadline), None, {}
        self._read_records = {}
        self._git_dir = self._common = self._format = None
        self._namespace = None
        self._env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        self._env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1',
                         GIT_NO_REPLACE_OBJECTS='1', GIT_NO_LAZY_FETCH='1',
                         GIT_OPTIONAL_LOCKS='0', LC_ALL='C')

    def _active(self):
        if self._state != 'active':
            raise RuntimeError('Git source custody is closed, failed or not entered')
        _clock(self.deadline)

    def _git(self, *args, stdout_cap=MAX_COMMAND_STDOUT):
        return _bounded_command(['/usr/bin/git', '--no-optional-locks',
            '-c', 'core.fsmonitor=false', '-c', 'core.commitGraph=false',
            '-c', 'gc.auto=0', '-c', 'protocol.ext.allow=never',
            '-C', self.repo, *args], cwd=self.repo, env=self._env,
            deadline=self.deadline, stdout_cap=stdout_cap)

    def _text(self, *args):
        return self._git(*args).decode('utf-8', 'strict').rstrip('\n')

    def _oid(self, value):
        size = 40 if self._format == 'sha1' else 64
        if (len(value) != size or any(char not in '0123456789abcdef' for char in value)):
            raise ValueError('Git returned a malformed object identity')
        return value

    def _ref(self, value):
        if (not value.startswith(('refs/heads/', 'refs/tags/', 'refs/remotes/', 'refs/pull/'))
                or any(char in value for char in ' ~^:?*[\\') or '@{' in value
                or any(part.startswith('.') or part.endswith(('.', '.lock')) for part in value.split('/'))):
            raise ValueError('Git returned a noncanonical or unregistered reference')
        return _relative(value)

    def _refs(self, advertised=False):
        if advertised:
            output = self._text('ls-remote', '--refs', self.remote,
                'refs/heads/*', 'refs/tags/*', 'refs/pull/*')
        else:
            output = self._text('for-each-ref', '--format=%(objectname)%09%(refname)',
                'refs/heads/', 'refs/tags/', 'refs/remotes/')
        rows = []
        for line in output.splitlines():
            fields = line.split('\t')
            if len(fields) != 2: raise ValueError('Git reference output is malformed')
            oid, name = self._oid(fields[0]), self._ref(fields[1])
            if advertised and name.startswith('refs/remotes/'):
                raise ValueError('Advertisement contains an unregistered prefix')
            rows.append((name, oid))
            if len(rows) > MAX_REFS: raise ValueError('Git references exceed the fixed bound')
        if len({row[0] for row in rows}) != len(rows):
            raise ValueError('Git reference names are duplicated')
        return sorted(rows)

    def _worktrees(self, local_refs):
        output = self._git('worktree', 'list', '--porcelain', '-z')
        rows, fields = [], {}
        for raw in output.split(b'\0'):
            if not raw:
                if fields:
                    rows.append(fields); fields = {}
                continue
            text = raw.decode('utf-8', 'strict')
            name, separator, value = text.partition(' ')
            if name not in ('worktree', 'HEAD', 'branch', 'detached', 'locked', 'prunable', 'bare') or name in fields:
                raise ValueError('Git worktree output has duplicated or unknown fields')
            fields[name] = value if separator else True
        if fields: rows.append(fields)
        if not rows or len(rows) > MAX_WORKTREES:
            raise ValueError('Registered worktree count exceeds its fixed bound')
        result, admin_targets = [], set()
        branch_oids = dict(local_refs)
        for row in rows:
            if ('worktree' not in row or 'HEAD' not in row or 'prunable' in row or 'bare' in row
                    or ('branch' in row) == ('detached' in row)):
                raise ValueError('Registered worktree is missing, ambiguous or unreadable')
            path = _absolute(row['worktree'])
            self._held.directory(path, exact=True)
            pointer = path + '/.git'
            info = os.lstat(pointer)
            if stat.S_ISDIR(info.st_mode):
                self._held.directory(pointer, exact=True)
                if pointer != self._common:
                    raise ValueError('Registered worktree has an unrelated Git directory')
                target = self._common
            elif stat.S_ISREG(info.st_mode):
                fd = self._held.file(pointer)
                if info.st_size > 4096: raise ValueError('Git worktree pointer exceeds its bound')
                os.lseek(fd, 0, os.SEEK_SET)
                value = os.read(fd, 4097).decode('utf-8', 'strict')
                if not value.startswith('gitdir: ') or not value.endswith('\n'):
                    raise ValueError('Git worktree pointer is malformed')
                target = _absolute(value[8:-1])
                if not target.startswith(self._common + '/worktrees/') or target not in self._namespace:
                    raise ValueError('Git worktree points outside the held common namespace')
                self._held.directory(target, exact=True)
                reciprocal = self._metadata_bytes(target + '/gitdir', 4096).decode('utf-8', 'strict')
                if not reciprocal.endswith('\n') or _absolute(reciprocal[:-1]) != pointer:
                    raise ValueError('Linked worktree admin pointer lacks its exact reciprocal Git pointer')
            else: raise ValueError('Registered worktree pointer is a symlink or special file')
            if target in admin_targets:
                raise ValueError('Registered worktrees alias the same Git admin target')
            admin_targets.add(target)
            head = self._metadata_bytes(target + '/HEAD', 4096).decode('utf-8', 'strict')
            if 'branch' in row:
                branch = self._ref(row['branch'])
                if (not branch.startswith('refs/heads/') or head != 'ref: ' + branch + '\n'
                        or branch_oids.get(branch) != row['HEAD']):
                    raise ValueError('Registered worktree admin HEAD or branch identity differs')
            elif not head.endswith('\n') or self._oid(head[:-1]) != row['HEAD']:
                raise ValueError('Detached worktree admin HEAD identity differs')
            if self._text('cat-file', '-t', self._oid(row['HEAD'])) != 'commit':
                raise ValueError('Registered worktree HEAD is not a commit object')
            result.append({'path': path, 'head': self._oid(row['HEAD']),
                'detached': 'detached' in row,
                'branch': self._ref(row['branch']) if 'branch' in row else None,
                'locked': row.get('locked')})
        if len({row['path'] for row in result}) != len(result):
            raise ValueError('Registered worktree paths are duplicated')
        if self.repo not in {row['path'] for row in result}:
            raise ValueError('Selected repository is not a registered worktree')
        return sorted(result, key=lambda row: row['path'])

    def _commit_root(self, oid):
        kind = self._text('cat-file', '-t', oid)
        if kind not in ('commit', 'tag'):
            raise ValueError('Git source reference is not a commit or commit tag')
        peeled = self._oid(self._text('rev-parse', '--verify', oid + '^{commit}'))
        if self._text('cat-file', '-t', peeled) != 'commit':
            raise ValueError('Git source reference does not peel to a commit')
        return peeled

    def _blob_descriptor(self, oid):
        if self._text('cat-file', '-t', oid) != 'blob':
            raise ValueError('Tracked Git document does not name a blob object')
        size_text = self._text('cat-file', '-s', oid)
        if not size_text.isascii() or not size_text.isdigit():
            raise ValueError('Git document size is malformed')
        size = int(size_text)
        if size > MAX_DOCUMENT_BYTES:
            raise ValueError('Tracked document exceeds four MiB')
        return {'oid': oid, 'size_bytes': size, 'object_type': 'blob'}

    def _blob(self, oid):
        descriptor = self._blob_descriptor(oid)
        if descriptor != self._blobs[oid]:
            raise RuntimeError('Git document descriptor changed while held')
        payload = self._git('cat-file', 'blob', oid, stdout_cap=MAX_DOCUMENT_BYTES)
        digest = hashlib.new(self._format)
        digest.update(b'blob ' + str(len(payload)).encode('ascii') + b'\0' + payload)
        if len(payload) != descriptor['size_bytes'] or digest.hexdigest() != oid:
            raise ValueError('Git document bytes do not match their immutable object identity')
        return payload

    def _metadata_bytes(self, path, maximum):
        fd = self._held.file(path)
        self._held.check()
        size = os.fstat(fd).st_size
        if size > maximum: raise ValueError('Git control metadata exceeds its fixed byte cap')
        os.lseek(fd, 0, os.SEEK_SET)
        payload = bytearray()
        while True:
            _clock(self.deadline)
            block = os.read(fd, min(65536, maximum + 1 - len(payload)))
            if not block: break
            payload.extend(block)
            if len(payload) > maximum:
                raise ValueError('Git control metadata exceeds its fixed byte cap')
        if len(payload) != size: raise RuntimeError('Git control metadata size changed')
        self._held.check()
        return bytes(payload)

    def _locate_namespace(self):
        """Anchor Git's known control roots before running Git or reading config."""
        pointer = self.repo + '/.git'
        mode = os.lstat(pointer).st_mode
        if stat.S_ISDIR(mode):
            self._git_dir = pointer
        elif stat.S_ISREG(mode):
            value = self._metadata_bytes(pointer, 4096).decode('utf-8', 'strict')
            if not value.startswith('gitdir: ') or not value.endswith('\n'):
                raise ValueError('Selected worktree Git pointer is malformed')
            self._git_dir = _absolute(value[8:-1])
        else:
            raise ValueError('Selected Git pointer is not a regular file or directory')
        self._held.directory(self._git_dir, exact=True)
        commondir = self._git_dir + '/commondir'
        if os.path.lexists(commondir):
            value = self._metadata_bytes(commondir, 4096).decode('utf-8', 'strict')
            if not value.endswith('\n'):
                raise ValueError('Git common-directory pointer is malformed')
            value = value[:-1]
            if value == '../..' and Path(self._git_dir).parent.name == 'worktrees':
                self._common = str(Path(self._git_dir).parent.parent)
            else:
                self._common = _absolute(value)
        else:
            self._common = self._git_dir
        self._namespace = self._held.walk(self._common)
        for path in self._namespace:
            if path == self._common + '/config' or path.endswith('/config.worktree'):
                text = self._metadata_bytes(path, 1024 ** 2).decode('utf-8', 'strict')
                if '\ufeff' in text:
                    raise ValueError('Git config BOM ambiguity lies outside canonical source custody')
                if '\0' in text or re.search(r'^\s*\[\s*include(?:if)?(?:\s|\])', text, re.M | re.I):
                    raise ValueError('Git config include or NUL ambiguity lies outside held source custody')

    def _discover(self):
        if self._text('remote', 'get-url', '--all', self.remote) != self.expected_remote_url:
            raise ValueError('Git remote URL differs from its registered exact URL')
        local, advertised = self._refs(), self._refs(advertised=True)
        if len(local) + len(advertised) > MAX_REFS:
            raise ValueError('Combined Git reference count exceeds the fixed bound')
        worktrees = self._worktrees(local)
        roots = sorted({oid for _, oid in local + advertised} | {row['head'] for row in worktrees})
        if not roots: raise ValueError('Git source discovery has no commit roots')
        roots = sorted({self._commit_root(oid) for oid in roots})
        output = self._text('rev-list', '--parents', *roots, '--')
        parents = {}
        for line in output.splitlines():
            fields = [self._oid(value) for value in line.split(' ')]
            if not fields or fields[0] in parents:
                raise ValueError('Git commit closure contains duplicate or malformed commits')
            parents[fields[0]] = fields[1:]
            if len(parents) > MAX_COMMITS:
                raise ValueError('Git commit closure exceeds the fixed bound')
        if not set(roots) <= set(parents) or any(parent not in parents for row in parents.values() for parent in row):
            raise ValueError('Git commit history is incomplete')
        pairs = {}
        output = self._text('rev-list', '--format=%H %T', '--no-commit-header', *roots, '--')
        for line in output.splitlines():
            fields = line.split(' ')
            if len(fields) != 2: raise ValueError('Git root tree output is malformed')
            commit, tree = map(self._oid, fields)
            if commit in pairs: raise ValueError('Git root tree commits are duplicated')
            pairs[commit] = tree
        if set(pairs) != set(parents): raise ValueError('Git root trees omit reachable commits')
        trees, by_tree, blobs, documents = set(), {}, {}, []
        used = 0
        for root_tree in sorted(set(pairs.values())):
            rows, names = [], set()
            output = self._git('ls-tree', '-r', '-t', '-z', '--full-tree', root_tree)
            trees.add(root_tree)
            for record in output.split(b'\0'):
                if not record: continue
                header, separator, raw_path = record.partition(b'\t')
                fields = header.decode('ascii', 'strict').split(' ')
                if not separator or len(fields) != 3:
                    raise ValueError('Git tree entry is malformed')
                mode, kind, oid = fields[0], fields[1], self._oid(fields[2])
                path = _relative(raw_path.decode('utf-8', 'strict'))
                if path in names: raise ValueError('Git tree entry names are duplicated')
                names.add(path)
                if len(names) > MAX_TREE_ENTRIES:
                    raise ValueError('Git tree entries exceed the fixed bound')
                if (mode, kind) not in {('040000', 'tree'), ('100644', 'blob'),
                        ('100755', 'blob'), ('120000', 'blob'), ('160000', 'commit')}:
                    raise ValueError('Git tree entry has unknown object type or mode')
                if kind == 'tree': trees.add(oid)
                if len(trees) > MAX_TREES:
                    raise ValueError('Git tree closure exceeds the fixed bound')
                if not path.lower().endswith(('.json', '.md')): continue
                if kind != 'blob' or mode not in ('100644', '100755'):
                    raise ValueError('Tracked document is a symlink or nonregular object')
                if oid not in blobs:
                    if len(blobs) >= MAX_BLOBS:
                        raise ValueError('Unique Git documents exceed the fixed bound')
                    blobs[oid] = self._blob_descriptor(oid)
                rows.append({'path': path, 'oid': oid, 'mode': mode})
                used += len(record) + 128
                if used > MAX_METADATA_BYTES:
                    raise ValueError('Retained Git source metadata exceeds 64 MiB')
            by_tree[root_tree] = rows
        for commit, tree in sorted(pairs.items()):
            for row in by_tree[tree]:
                item = dict(row, commit=commit, root_tree=tree)
                documents.append(item)
                used += len(json.dumps(item).encode('utf-8'))
                if used > MAX_METADATA_BYTES:
                    raise ValueError('Retained Git source metadata exceeds 64 MiB')
        evidence = {'schema': 'held-git-scene-sources-v1', 'repo': self.repo,
            'common_git_dir': self._common, 'object_format': self._format,
            'remote': self.remote, 'remote_url': self.expected_remote_url,
            'local_refs': local, 'advertised_refs': advertised,
            'worktrees': worktrees, 'commit_roots': roots,
            'commits': sorted(parents), 'commit_parents': sorted(parents.items()),
            'root_trees': sorted(pairs.items()), 'trees': sorted(trees),
            'documents': documents,
            'blobs': [descriptor for oid, descriptor in sorted(blobs.items())],
            'inventory_complete': False, 'native_execution': False,
            'bootstrap_admission': False, 'scene_admission': False,
            'executable': False, 'collection_admission': False, 'qualification_claims': [],
            'all_repositories_discovered': False, 'retained_roots_discovered': False}
        retained_size = len(json.dumps(evidence).encode('utf-8'))
        retained_size += len(json.dumps(self._held.namespace).encode('utf-8'))
        retained_size += len(json.dumps(self._read_records).encode('utf-8'))
        if retained_size > MAX_METADATA_BYTES:
            raise ValueError('Retained Git descriptor metadata exceeds 64 MiB')
        return evidence, blobs

    def __enter__(self):
        if self._state != 'new': raise RuntimeError('Git source custody is one-shot')
        self._state = 'opening'
        try:
            self._held.directory(self.repo, exact=True)
            # Hold the selected worktree's .git pointer before trusting Git's
            # interpretation of it, and reject ancestor/link ambiguity.
            self._locate_namespace()
            if self._text('rev-parse', '--is-bare-repository') != 'false':
                raise ValueError('A registered nonbare worktree is required')
            if (_absolute(self._text('rev-parse', '--absolute-git-dir')) != self._git_dir
                    or _absolute(self._text('rev-parse', '--path-format=absolute', '--git-common-dir')) != self._common):
                raise ValueError('Git root interpretation differs from held control roots')
            if (self._common + '/shallow' in self._namespace
                    or self._common + '/info/grafts' in self._namespace
                    or self._common + '/objects/info/alternates' in self._namespace
                    or self._common + '/objects/info/http-alternates' in self._namespace
                    or any(path.startswith(self._common + '/refs/replace/') for path in self._namespace)):
                raise ValueError('Shallow, grafted, alternate or replacement Git sources are ambiguous')
            if self._text('rev-parse', '--is-shallow-repository') != 'false':
                raise ValueError('Shallow Git sources are forbidden')
            if self._text('for-each-ref', '--format=%(refname)', 'refs/replace/'):
                raise ValueError('Replacement Git references are forbidden')
            self._format = self._text('rev-parse', '--show-object-format=storage')
            if self._format not in ('sha1', 'sha256'):
                raise ValueError('Git object format is unsupported')
            self._evidence, self._blobs = self._discover()
            self._held.check()
            if self._held.walk(self._common) != self._namespace:
                raise RuntimeError('Git common namespace changed during source discovery')
            self._state = 'active'
            self.recheck()
            return self
        except BaseException:
            self._state = 'failed'; self._held.close(); raise

    def _recheck(self):
        self._active()
        self._held.check()
        if self._held.walk(self._common) != self._namespace:
            raise RuntimeError('Git common namespace changed while held')
        evidence, blobs = self._discover()
        if evidence != self._evidence or blobs != self._blobs:
            raise RuntimeError('Git source refs, advertisement, worktrees or closure changed')
        self._held.check()
        _clock(self.deadline)

    def recheck(self):
        try: self._recheck()
        except BaseException:
            self._state = 'failed'; self._held.close(); raise

    def snapshot(self):
        try:
            self._active()
            self._held.check()
            result = copy.deepcopy(self._evidence)
            result['read_records'] = copy.deepcopy([row for oid, row in sorted(self._read_records.items())])
            self._held.check()
            _clock(self.deadline)
            return result
        except BaseException:
            self._state = 'failed'; self._held.close(); raise

    def read_blob(self, oid):
        try:
            self._active()
            if type(oid) is not str or oid not in self._blobs:
                raise ValueError('Git document was not discovered and retained')
            self._recheck()
            payload = self._blob(oid)
            self._recheck()
            self._read_records[oid] = {'oid': oid, 'size_bytes': len(payload),
                                       'sha256': hashlib.sha256(payload).hexdigest()}
            retained_size = len(json.dumps(self._evidence).encode('utf-8'))
            retained_size += len(json.dumps(self._held.namespace).encode('utf-8'))
            retained_size += len(json.dumps(self._read_records).encode('utf-8'))
            if retained_size > MAX_METADATA_BYTES:
                raise ValueError('Retained Git descriptor/read metadata exceeds 64 MiB')
            self._held.check()
            _clock(self.deadline)
            return payload
        except BaseException:
            self._state = 'failed'; self._held.close(); raise

    def read_document(self, commit, path, *, expected_oid):
        """Read one authenticated historical attachment as a detached byte view.

        The held commit/tree/path/mode/OID occurrence, not a current-worktree
        pathname or caller-supplied attachment, selects the document. Raw bytes
        are a consumer context only; they are never inserted into the receipt.
        """
        try:
            self._active()
            if any(type(value) is not str for value in (commit, path, expected_oid)):
                raise ValueError('Git document attachment requires exact text fields')
            self._oid(commit)
            self._oid(expected_oid)
            _relative(path)
            matches = [row for row in self._evidence['documents']
                       if row['commit'] == commit and row['path'] == path]
            if len(matches) != 1 or matches[0]['oid'] != expected_oid:
                raise ValueError('Git document attachment was not discovered with its exact OID')
            descriptor = dict(matches[0])
            payload = self.read_blob(expected_oid)
            result = dict(descriptor, repo=self.repo, object_format=self._format,
                          size_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest(),
                          raw=payload)
            self._held.check()
            _clock(self.deadline)
            return result
        except BaseException as error:
            self._state = 'failed'
            try:
                self._held.close()
            except BaseException as cleanup_error:
                error.add_note('Git document attachment cleanup failed: ' + repr(cleanup_error))
            raise

    def retained_metadata_size_bytes(self):
        """Count bounded retained descriptor/read metadata without payload reads."""
        try:
            self._active()
            self._held.check()
            retained_size = len(json.dumps(self._evidence).encode('utf-8'))
            retained_size += len(json.dumps(self._held.namespace).encode('utf-8'))
            retained_size += len(json.dumps(self._read_records).encode('utf-8'))
            if retained_size > MAX_METADATA_BYTES:
                raise ValueError('Retained Git descriptor/read metadata exceeds 64 MiB')
            self._held.check()
            _clock(self.deadline)
            return retained_size
        except BaseException as error:
            self._state = 'failed'
            try:
                self._held.close()
            except BaseException as cleanup_error:
                error.add_note('Git metadata budget cleanup failed: ' + repr(cleanup_error))
            raise

    def __exit__(self, exc_type, exc, traceback):
        if self._state != 'active':
            self._held.close()
            self._blobs.clear()
            if exc_type is None:
                raise RuntimeError('Git source custody failed before context exit')
            return False
        try:
            self._recheck()
            self._held.close(final_check=True)
            _clock(self.deadline)
            self._state = 'closed'
        except BaseException as final_error:
            self._state = 'failed'
            try:
                self._held.close()
            except BaseException as cleanup_error:
                final_error.add_note('Git source final cleanup failed: ' + repr(cleanup_error))
            if exc is not None:
                exc.add_note('Git source final custody check failed: ' + repr(final_error))
                for note in getattr(final_error, '__notes__', ()):
                    exc.add_note(note)
                return False
            raise
        finally:
            self._blobs.clear()
        return False
