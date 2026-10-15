"""Fresh stdlib worker with held local-source imports; no numerical authority.

The fixed seed authenticates these bytes before compile. CPython's stdlib/ELF
dependencies are an explicit trusted boundary, not qualified by this program.
This is a trusted-source contract, not a sandbox against admitted Python.
"""
import copy
import hashlib
import importlib.abc
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import time
import types

MiB = 1024**2
BOOTSTRAP = 'scripts/puck_worker_bootstrap.py'
HOLDER = 'src/palimpsest/puck_execution_files.py'
ENTRY = 'palimpsest.puck_worker_preflight'
QUALIFICATION_ENTRY = 'palimpsest.puck_runtime_qualification'
RUNTIME_PIN = {'path': 'python3.11', 'size_bytes': 21662864,
    'sha256': '572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a'}
_PREFIXES = ('src/palimpsest', 'scripts', 'upstream/fly-gym')
_FIELDS = {'kind', 'version', 'source_root', 'source_files', 'modules', 'namespaces',
           'runtime', 'environment', 'cwd', 'argv_prefix', 'qualification_claims', 'executable'}

# The small seed is itself part of the exact kernel-observed frozen argv. Never
# execute pathname-loaded local source first and then claim its hash was enough.
SEED = '''import os,sys,stat,hashlib
p,h=sys.argv[1:3]
def identity(s): return (s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
f=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
try:
 s=os.fstat(f)
 if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or not 0<s.st_size<=1048576: raise ValueError('Bootstrap file refused')
 with os.fdopen(os.dup(f),'rb') as q: r=q.read(1048577)
 if len(r)!=s.st_size or hashlib.sha256(r).hexdigest()!=h or identity(os.fstat(f))!=identity(s): raise ValueError('Bootstrap bytes differ')
 exec(compile(r,p,'exec'),{'__name__':'__main__','__file__':p,'__bootstrap_raw__':r,'__bootstrap_fd__':f})
finally: os.close(f)
'''


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _hash(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('Exact lowercase SHA256 required')
    return value


def _path(value, absolute=True):
    if (type(value) is not str or not value or len(value.encode()) > 4096
            or any(ord(c) < 32 or ord(c) == 127 for c in value) or '\\' in value or ':' in value):
        raise ValueError('Bounded canonical POSIX path required')
    path = PurePosixPath(value)
    if (path.is_absolute() != absolute or path.as_posix() != value
            or any(part in ('.', '..') for part in value.split('/'))):
        raise ValueError('Canonical path without traversal required')
    return value


def command(python, bootstrap_path, bootstrap_sha256, registration_path, registration_sha256):
    args = [_path(python), '-I', '-B', '-S', '-c', SEED, _path(bootstrap_path),
            _hash(bootstrap_sha256), _path(registration_path), _hash(registration_sha256)]
    if any(len(arg.encode()) > 4096 for arg in args):
        raise ValueError('Existing argv element ceiling exceeded')
    return args


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink)


def _decode(raw):
    def pairs(rows):
        result = {}
        for key, value in rows:
            if key in result: raise ValueError('Duplicate registration key')
            result[key] = value
        return result
    def constant(_): raise ValueError('Nonfinite registration value')
    try:
        value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
        raise ValueError('Invalid worker registration') from error
    pending = [(value, 0)]; count = 0
    while pending:
        node, depth = pending.pop(); count += 1
        if count > 65536 or depth > 32: raise ValueError('Registration node/depth ceiling exceeded')
        if type(node) is dict: pending.extend((v, depth+1) for v in node.values())
        elif type(node) is list: pending.extend((v, depth+1) for v in node)
    if type(value) is not dict or canonical(value) != raw:
        raise ValueError('Canonical registration object required')
    return value


def _read_initial(path, expected, maximum=MiB):
    """Authenticated copy before a source-supplied holder can be compiled.

    Absolute ancestor edges are nofollow; the full later holder supplies lifetime
    custody. An externally expected digest binds the initial code bytes.
    """
    _path(path); _hash(expected); fds = []
    try:
        fd = os.open('/', os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW); fds.append(fd)
        parts = PurePosixPath(path).parts[1:]
        if len(parts) > 32: raise ValueError('Initial path depth ceiling exceeded')
        for part in parts[:-1]:
            fd = os.open(part, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=fd); fds.append(fd)
        leaf = os.open(parts[-1], os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK, dir_fd=fd); fds.append(leaf)
        before = os.fstat(leaf)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= maximum:
            raise ValueError('Initial authenticated file refused')
        with os.fdopen(os.dup(leaf), 'rb') as stream: payload = stream.read(maximum+1)
        if len(payload) != before.st_size or digest(payload) != expected or _identity(os.fstat(leaf)) != _identity(before):
            raise ValueError('Initial authenticated bytes differ')
        return payload
    finally:
        for fd in reversed(fds): os.close(fd)


def _name(name):
    if (type(name) is not str or len(name) > 4096
            or any(not part.isidentifier() for part in name.split('.'))
            or name.split('.')[0] in sys.stdlib_module_names):
        raise ValueError('Explicit non-stdlib local module name required')
    return name


def _parse(raw, expected):
    if type(raw) is not bytes or not 0 < len(raw) <= MiB or digest(raw) != _hash(expected):
        raise ValueError('Externally pinned bounded worker registration required')
    reg = _decode(raw)
    if (type(reg.get('version')) is not int or reg['version'] not in (1, 2, 3)
            or set(reg) != (_FIELDS if reg['version'] == 1 else
                _FIELDS | {'dependencies'} | ({'qualification'} if reg['version']==3 else set()))
            or reg['kind'] != 'puck-worker-source-bootstrap-v'+str(reg['version'])
            or reg['qualification_claims'] != [] or reg['executable'] is not False):
        raise ValueError('Exact source-only bootstrap registration required')
    if reg['version'] >= 2:
        dep = reg['dependencies']
        if type(dep) is not dict or set(dep) != {'path', 'size_bytes', 'sha256'}:
            raise ValueError('Exact dependency registration reference required')
        _path(dep['path']); _hash(dep['sha256'])
        if type(dep['size_bytes']) is not int or not 0 < dep['size_bytes'] <= 16*MiB:
            raise ValueError('Dependency registration reference ceiling exceeded')
    if reg['version']==3:
        q=reg['qualification']
        if (type(q) is not dict or set(q)!= {'kind','version','expected_versions','stdlib_cache_aliases','negative_imports'}
                or type(q['version']) is not int or q['version'] not in (1,2,3)
                or q['kind']!='puck-held-runtime-import-qualification-v'+str(q['version'])
                or type(q['expected_versions']) is not dict
                or set(q['expected_versions'])!=({'numpy','torch','torchvision','mujoco'}
                    if q['version']==3 else {'numpy','torch','mujoco'})
                or any(type(v) is not str or not 1<=len(v)<=128 for v in q['expected_versions'].values())
                or type(q['stdlib_cache_aliases']) is not dict
                or q['stdlib_cache_aliases']!={'__mp_main__':'__main__'}):
            raise ValueError('Exact fixed runtime qualification descriptor required')
        negatives=q['negative_imports']
        if q['version']==1:
            if negatives!=['org']:raise ValueError('Exact legacy qualification denial required')
        else:
            if (type(negatives) is not list or not 1<=len(negatives)<=128 or any(
                    type(name) is not str or len(name)>512 or not name.isascii()
                    or name in ('__main__','__mp_main__','_puck_held_file_bootstrap')
                    for name in negatives)):
                raise ValueError('Bounded expected missing import declaration required')
            for name in negatives:_name(name)
            if negatives!=sorted(set(negatives)) or any(
                    name.startswith(parent+'.') for index,name in enumerate(negatives) for parent in negatives[:index]):
                raise ValueError('Expected missing imports must be sorted, unique and nonoverlapping')
    _path(reg['source_root']); _path(reg['cwd'])
    files = reg['source_files']
    if type(files) is not list or not 1 <= len(files) <= 512:
        raise ValueError('Bounded source roster required')
    paths = []; total = 0
    for row in files:
        if type(row) is not dict or set(row) != {'path', 'size_bytes', 'sha256'}:
            raise ValueError('Exact source descriptor required')
        paths.append(_path(row['path'], False)); _hash(row['sha256'])
        if type(row['size_bytes']) is not int or not 0 <= row['size_bytes'] <= MiB:
            raise ValueError('Source file ceiling exceeded')
        total += row['size_bytes']
    if paths != sorted(set(paths)) or not {BOOTSTRAP, HOLDER} <= set(paths) or total > 64*MiB:
        raise ValueError('Exact sorted source identity/ceiling required')
    for key in ('modules', 'namespaces'):
        if type(reg[key]) is not list or len(reg[key]) > 512:
            raise ValueError('Bounded source import mappings required')
    modules = {}; namespaces = {}; mapped_paths = set()
    for row in reg['modules']:
        if type(row) is not dict or set(row) != {'name', 'path'}:
            raise ValueError('Exact Python source module mapping required')
        name = _name(row['name']); path = _path(row['path'], False)
        if name in modules or path in mapped_paths or path not in paths or not path.endswith('.py') or path == BOOTSTRAP:
            raise ValueError('Duplicate or unattached source module mapping')
        modules[name] = path; mapped_paths.add(path)
    for row in reg['namespaces']:
        if type(row) is not dict or set(row) != {'name', 'path'}:
            raise ValueError('Exact namespace mapping required')
        name = _name(row['name']); path = _path(row['path'], False)
        if name in modules or name in namespaces: raise ValueError('Duplicate import namespace')
        namespaces[name] = path
    expected = {p for p in paths if p.endswith('.py')} - {BOOTSTRAP}
    if mapped_paths != expected or ENTRY not in modules or (reg['version']==3 and QUALIFICATION_ENTRY not in modules):
        raise ValueError('Complete Python module mapping required')
    for name in modules.keys() | namespaces.keys():
        parent = name.rpartition('.')[0]
        if parent and parent not in namespaces and (parent not in modules or not modules[parent].endswith('/__init__.py')):
            raise ValueError('Unregistered package parent')
    if reg['version']==3 and reg['qualification']['version']>=2:
        local_tops={name.split('.')[0] for name in modules.keys()|namespaces.keys()}
        if any(name.split('.')[0] in local_tops for name in reg['qualification']['negative_imports']):
            raise ValueError('Expected missing import overlaps authenticated local source')
    runtime = reg['runtime']
    if type(runtime) is not dict or set(runtime) != {'root', 'files', 'python_version'}:
        raise ValueError('Exact interpreter registration required')
    _path(runtime['root'])
    if canonical(runtime['files']) != canonical([RUNTIME_PIN]) or runtime['python_version'] != '3.11.15':
        raise ValueError('Original interpreter pin/version required')
    if total + RUNTIME_PIN['size_bytes'] > 80*MiB:
        raise ValueError('Existing aggregate input ceiling exceeded')
    env = reg['environment']
    if (type(env) is not dict or len(env) > 128 or any(type(k) is not str or not k or '=' in k
            or type(v) is not str or '\x00' in k+v or len((k+v).encode()) > 4096 for k, v in env.items())):
        raise ValueError('Bounded exact environment required')
    args = reg['argv_prefix']
    if (type(args) is not list or not 1 <= len(args) < 128
            or any(type(arg) is not str or not arg or '\x00' in arg or len(arg.encode()) > 4096 for arg in args)):
        raise ValueError('Bounded exact invocation prefix required')
    return reg, modules, namespaces


def _process(pid):
    with open('/proc/'+str(pid)+'/stat', 'rb') as stream: raw = stream.read(4097)
    if len(raw) > 4096: raise ValueError('Bounded process identity required')
    end = raw.rfind(b')'); fields = raw[end+2:].split()
    if end < 0 or len(fields) < 20: raise ValueError('Malformed process identity')
    return {'pid': pid, 'parent_pid': int(fields[1]), 'pgid': int(fields[2]),
            'sid': int(fields[3]), 'start_tick': int(fields[19])}


class _SourceLoader(importlib.abc.Loader):
    def __init__(self, owner, name, path): self.owner, self.name, self.path = owner, name, path
    def create_module(self, spec): return None
    def exec_module(self, module):
        self.owner._loading.add(self.name)
        try:
            self.owner.recheck()
            if self.path is None:
                module.__file__ = None
                module.__path__ = []
                self.owner._capture(self.name, module, self.owner._namespaces[self.name], None)
                self.owner.recheck()
                return
            payload = self.owner._source.read(self.path, MiB)
            filename = str(self.owner._source.root/self.path)
            module.__file__ = filename
            if self.path.endswith('/__init__.py'): module.__path__ = []
            exec(compile(payload, filename, 'exec', dont_inherit=True), module.__dict__)
            self.owner._capture(self.name, module, self.path, digest(payload))
            self.owner.recheck()
        except BaseException as error:
            self.owner._fail(error); raise
        finally:
            self.owner._loading.discard(self.name)


class _SourceFinder(importlib.abc.MetaPathFinder):
    def __init__(self, owner): self.owner = owner
    def find_spec(self, fullname, path=None, target=None):
        expected_denial=False
        try:
            self.owner._import_recheck()
            if (self.owner._reg['version']==3 and
                    fullname in self.owner._negative_imports):
                # V1 preserves the original exact org denial. V2/V3 additionally
                # verifies finite absence in the live held package namespace.
                if self.owner._missing_policy_version>=2:
                    if self.owner._dependencies is None:
                        raise RuntimeError('Expected missing import requires admitted dependency custody')
                    self.owner._dependencies.provider.require_absent_imports((fullname,))
                self.owner._denied_imports.add(fullname); expected_denial=True
                raise ModuleNotFoundError('Explicit qualification import denial: '+fullname,name=fullname)
            if fullname in self.owner._modules:
                source = self.owner._modules[fullname]
                loader = _SourceLoader(self.owner, fullname, source)
                return importlib.util.spec_from_loader(fullname, loader,
                    origin=str(self.owner._source.root/source), is_package=source.endswith('/__init__.py'))
            if fullname in self.owner._namespaces:
                return importlib.util.spec_from_loader(fullname, _SourceLoader(self.owner, fullname, None),
                    origin=str(self.owner._source.root/self.owner._namespaces[fullname]), is_package=True)
            if self.owner._dependencies is not None:
                spec = self.owner._dependencies.find_spec(fullname)
                if spec is not None: return spec
            if fullname.split('.')[0] not in sys.stdlib_module_names:
                raise ImportError('Unregistered local or external dependency import: '+fullname)
            return None
        except BaseException as error:
            if not expected_denial: self.owner._fail(error)
            raise

    def find_distributions(self, context):
        if self.owner._dependencies is None: return iter(())
        try: return self.owner._dependencies.find_distributions(context)
        except BaseException as error:
            self.owner._fail(error); raise


class HeldWorkerBootstrap:
    """Fresh process source custody only; later dependency admission is required."""
    def __init__(self, registration_raw, *, expected_sha256, deadline, registration_path):
        if type(deadline) not in (int, float) or not math.isfinite(deadline) or not time.monotonic() < deadline <= time.monotonic()+180:
            raise ValueError('Bounded worker deadline required')
        self._reg, self._modules, self._namespaces = _parse(registration_raw, expected_sha256)
        self._raw = registration_raw; self._sha = expected_sha256; self._deadline = deadline
        self._registration_path = _path(registration_path)
        self._state = 'new'; self._first_failure = None; self._children = []; self._loaded = {}; self._bindings = []
        self._classes = []
        self._loading = set()
        self._finder = None; self._meta_path = None; self._source = None; self._runtime = None
        self._early_runtime_fds = []
        self._dependencies = None; self._dependency_dispatch = None
        self._main_module=sys.modules.get('__main__'); self._denied_imports=set()
        q=self._reg.get('qualification',{})
        self._missing_policy_version=q.get('version',0)
        self._negative_imports=tuple(q.get('negative_imports',()))

    def _clock(self):
        if time.monotonic() >= self._deadline: raise TimeoutError('Fresh worker deadline exhausted')

    def _close(self, error=None):
        if self._meta_path is not None: sys.meta_path[:] = self._meta_path
        for child in reversed(self._children):
            try: child.__exit__(type(error) if error else None, error, None)
            except BaseException as close_error:
                if error is None: error = close_error
                else: error.add_note('Bootstrap holder close: '+str(close_error))
        self._children.clear(); self._state = 'failed' if error else 'closed'
        while self._early_runtime_fds:
            try: os.close(self._early_runtime_fds.pop())
            except OSError as close_error:
                if error is None: error = close_error; self._state = 'failed'
                else: error.add_note('Early interpreter descriptor close: '+str(close_error))
        if error is not None: return error

    def _fail(self, error):
        if self._first_failure is None: self._first_failure=error
        self._close(error)

    def _enter(self, holder):
        self._children.append(holder); return holder.__enter__()

    def _bind_initial_interpreter(self):
        # This must precede compiling the source-supplied holder implementation.
        # Stream the original image, preserving the existing small-copy ceiling.
        path = str(Path(self._reg['runtime']['root'])/RUNTIME_PIN['path'])
        parts = PurePosixPath(path).parts[1:]
        if len(parts) > 32: raise ValueError('Interpreter path depth ceiling exceeded')
        fd = os.open('/', os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        self._early_runtime_fds.append(fd)
        for part in parts[:-1]:
            self._clock()
            fd = os.open(part, os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW, dir_fd=fd)
            self._early_runtime_fds.append(fd)
        leaf = os.open(parts[-1], os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK, dir_fd=fd)
        self._early_runtime_fds.append(leaf); before = os.fstat(leaf)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or before.st_size != RUNTIME_PIN['size_bytes']):
            raise ValueError('Initial interpreter type/size differs')
        if _identity(os.stat('/proc/self/exe')) != _identity(before):
            raise RuntimeError('Running interpreter object differs')
        hasher = hashlib.sha256(); size = 0
        while True:
            self._clock(); chunk = os.read(leaf, MiB)
            if not chunk: break
            size += len(chunk)
            if size > RUNTIME_PIN['size_bytes']: raise ValueError('Interpreter grew beyond fixed size')
            hasher.update(chunk)
        if (size != RUNTIME_PIN['size_bytes'] or hasher.hexdigest() != RUNTIME_PIN['sha256']
                or _identity(os.fstat(leaf)) != _identity(before)):
            raise ValueError('Initial interpreter bytes differ')
        self._early_image = _identity(before)

    def __enter__(self):
        if self._state != 'new': raise RuntimeError('Fresh worker bootstrap is one-shot')
        try:
            self._clock()
            flags = sys.flags
            if not (flags.isolated and flags.no_site and flags.dont_write_bytecode and not flags.optimize):
                raise ValueError('Fresh isolated no-site no-bytecode worker required')
            expected = self._reg['argv_prefix']+[self._sha]
            bootstrap_path = str(Path(self._reg['source_root'])/BOOTSTRAP)
            descriptors = {r['path']: r for r in self._reg['source_files']}
            if expected != command(sys.executable, bootstrap_path, descriptors[BOOTSTRAP]['sha256'], self._registration_path, self._sha):
                raise ValueError('Frozen worker command differs')
            with open('/proc/self/cmdline', 'rb') as stream: cmdline = stream.read(MiB+1)
            if len(cmdline) > MiB or cmdline != b'\0'.join(os.fsencode(v) for v in expected)+b'\0' or sys.orig_argv != expected:
                raise ValueError('Actual kernel/Python invocation differs')
            if dict(os.environ) != self._reg['environment'] or os.getcwd() != self._reg['cwd']:
                raise ValueError('Actual worker environment/cwd differs')
            if sys.version_info[:3] != (3, 11, 15): raise ValueError('Measured Python version differs')
            if (globals().get('__bootstrap_raw__') is None or digest(__bootstrap_raw__) != descriptors[BOOTSTRAP]['sha256']):
                raise ValueError('Bootstrap was not compiled from seeded authenticated bytes')
            allowed = set(sys.stdlib_module_names)|{'__main__'}
            if any(name.split('.')[0] not in allowed for name in sys.modules):
                raise ValueError('Foreign or local source was preloaded before bootstrap')
            self._bind_initial_interpreter()
            payload = _read_initial(str(Path(self._reg['source_root'])/HOLDER), descriptors[HOLDER]['sha256'])
            helper = types.ModuleType('_puck_held_file_bootstrap'); sys.modules[helper.__name__] = helper
            helper.__file__ = str(Path(self._reg['source_root'])/HOLDER)
            helper.__spec__ = importlib.util.spec_from_loader(helper.__name__, None, origin=helper.__file__)
            helper.__package__ = ''
            exec(compile(payload, helper.__file__, 'exec', dont_inherit=True), helper.__dict__)
            self._capture(helper.__name__, helper, HOLDER, digest(payload))
            Holder = helper.HeldCollectionFiles
            self._source = self._enter(Holder(self._reg['source_root'], self._reg['source_files'], self._deadline))
            self._registration = self._enter(Holder(str(Path(self._registration_path).parent),
                [{'path':Path(self._registration_path).name, 'size_bytes':len(self._raw), 'sha256':self._sha}], self._deadline))
            self._runtime = self._enter(Holder(self._reg['runtime']['root'], self._reg['runtime']['files'], self._deadline))
            seed = os.fstat(__bootstrap_fd__)
            held_seed = os.fstat(self._source._files[BOOTSTRAP][0])
            if _identity(seed) != _identity(held_seed): raise ValueError('Seeded bootstrap object differs from held source')
            self._image = _identity(os.fstat(self._runtime._files[RUNTIME_PIN['path']][0]))
            if self._image != self._early_image: raise RuntimeError('Held interpreter differs from initial running object')
            self._census()
            self._process = _process(os.getpid()); self._parent = _process(os.getppid())
            if self._process['pgid'] != os.getpid() or self._process['sid'] != os.getpid():
                raise ValueError('Dedicated worker session/group required')
            self._meta_path = list(sys.meta_path); self._finder = _SourceFinder(self)
            sys.meta_path.insert(0, self._finder); self._state = 'active'
            if self._reg['version'] >= 2:
                from palimpsest.puck_dependency_imports import DependencyImports, HeldDependencyNamespace
                dep = self._reg['dependencies']
                raw = _read_initial(dep['path'], dep['sha256'], maximum=16*MiB)
                if len(raw) != dep['size_bytes']:
                    raise ValueError('Dependency registration reference size differs')
                provider = self._enter(HeldDependencyNamespace(raw, expected_sha256=dep['sha256'],
                    deadline=self._deadline, registration_path=dep['path']))
                self._dependencies = DependencyImports(provider, self._import_recheck, self.recheck, self._fail,
                    self._modules.keys() | self._namespaces.keys(),
                    [self._reg['source_root'], self._reg['runtime']['root']])
                self._dependency_dispatch=(self._dependencies,DependencyImports)
                if (self._missing_policy_version==3 and
                        provider.snapshot().get('native_identity')!='tmpfs-raw-dev-inode-v1'):
                    raise ValueError('Four-import qualification requires admitted v3 tmpfs dependency custody')
                if self._missing_policy_version>=2:
                    provider.require_absent_imports(self._negative_imports)
            self.recheck(); return self
        except BaseException as error: self._fail(error); raise

    def _census(self):
        found = set(); count = 0
        def walk(relative, depth):
            nonlocal count
            self._clock()
            if depth > 32: raise ValueError('Source census depth exceeded')
            key = (*self._source.root.parts[1:], *relative.split('/'))
            fd = self._source._directory(key)
            with os.scandir(fd) as entries:
                for entry in entries:
                    self._clock(); count += 1
                    if count > 4096: raise ValueError('Source census count exceeded')
                    path = relative+'/'+entry.name
                    if entry.name == '__pycache__' or entry.name.endswith('.pyc'):
                        raise ValueError('Bytecode source alternative refused')
                    _path(path, False); value = os.stat(entry.name, dir_fd=fd, follow_symlinks=False)
                    if stat.S_ISDIR(value.st_mode): walk(path, depth+1)
                    elif stat.S_ISREG(value.st_mode):
                        if path.endswith(('.py', '.xml')): found.add(path)
                    else: raise ValueError('Linked/nonregular source alternative refused')
        for prefix in _PREFIXES: walk(prefix, 0)
        expected = {r['path'] for r in self._reg['source_files'] if r['path'].endswith(('.py', '.xml'))}
        if found != expected: raise ValueError('Complete Python/XML source census differs')
        for path in self._namespaces.values():
            if path+'/__init__.py' in expected:
                raise ValueError('Namespace with an initializer must bind that source')
            key = (*self._source.root.parts[1:], *path.split('/'))
            if key not in self._source._dirs:
                raise ValueError('Namespace is outside observed held source directories')

    def _capture(self, name, module, path, sha256):
        spec = module.__spec__
        self._loaded[name] = (module, module.__file__, module.__loader__, spec,
            spec.origin, spec.loader, module.__package__, tuple(getattr(module, '__path__', ())),
            spec.name, tuple(spec.submodule_search_locations or ()), path, sha256)
        def bind(owner, key, slot):
            functions = ([slot] if type(slot) is types.FunctionType else
                [slot.__func__] if isinstance(slot, (staticmethod, classmethod)) else
                [fn for fn in (slot.fget, slot.fset, slot.fdel) if fn is not None] if isinstance(slot, property) else [])
            if functions:
                self._bindings.append((owner, key, slot, tuple((fn, fn.__code__) for fn in functions
                    if type(fn) is types.FunctionType)))
                if len(self._bindings) > 65536: raise ValueError('Loaded function binding ceiling exceeded')
        for key, value in list(vars(module).items()):
            bind(module, key, value)
            if isinstance(value, type):
                self._classes.append((module, key, value, type(value), value.__bases__, tuple(vars(value))))
                if len(self._classes) > 65536: raise ValueError('Loaded class binding ceiling exceeded')
                if value.__module__ == name:
                    for member, slot in list(vars(value).items()): bind(value, member, slot)

    def recheck(self):
        return self._check(full=True)

    def _import_recheck(self):
        # Imported local code stays bound. External consumption uses its held
        # leaf/ancestor/lease guards; full source hashes and forest checks occur
        # at public admission, local import, native and terminal boundaries.
        return self._check(full=self._dependencies is None)

    def _check(self, *, full):
        try:
            if self._state != 'active':
                raise RuntimeError('Bootstrap inactive or poisoned') from self._first_failure
            self._clock()
            if sys.meta_path != [self._finder, *self._meta_path]: raise RuntimeError('Source import dispatch changed')
            for name, binding in self._loaded.items():
                module, filename, loader, spec, origin, spec_loader, package, search, spec_name, spec_search, _, _ = binding
                if (sys.modules.get(name) is not module or module.__file__ != filename or module.__loader__ is not loader
                        or module.__spec__ is not spec or spec.origin != origin or spec.loader is not spec_loader
                        or module.__package__ != package or tuple(getattr(module, '__path__', ())) != search
                        or spec.name != spec_name or tuple(spec.submodule_search_locations or ()) != spec_search):
                    raise RuntimeError('Authenticated loaded module dispatch changed')
            for owner, key, slot, functions in self._bindings:
                if vars(owner).get(key) is not slot or any(fn.__code__ is not code for fn, code in functions):
                    raise RuntimeError('Authenticated function code binding changed')
            for owner, key, cls, metaclass, bases, keys in self._classes:
                if (vars(owner).get(key) is not cls or type(cls) is not metaclass
                        or cls.__bases__ != bases or tuple(vars(cls)) != keys):
                    raise RuntimeError('Authenticated class binding changed')
            # Bind support dispatch before calling any dependency reconciliation.
            exported=set()
            if self._dependencies is not None:
                receiver,cls=self._dependency_dispatch
                if self._dependencies is not receiver or type(receiver) is not cls:
                    raise RuntimeError('Authenticated dependency receiver dispatch changed')
                exported=cls.recheck(receiver)
            aliases=set()
            if self._reg['version']==3:
                q=self._reg['qualification']
                if (q['version']!=self._missing_policy_version
                        or tuple(q['negative_imports'])!=self._negative_imports):
                    raise RuntimeError('Expected missing import declaration changed')
                if sys.modules.get('__main__') is not self._main_module:
                    raise RuntimeError('Runtime qualification main alias target changed')
                if '__mp_main__' in sys.modules:
                    if sys.modules['__mp_main__'] is not self._main_module:
                        raise RuntimeError('Runtime qualification stdlib alias identity changed')
                    aliases.add('__mp_main__')
            for name in sys.modules:
                if (name.split('.')[0] not in sys.stdlib_module_names and
                        name not in {'__main__', '_puck_held_file_bootstrap'}|aliases|self._loaded.keys()|self._loading
                        | (self._dependencies.loaded.keys() | self._dependencies.loading | exported if self._dependencies else set())):
                    raise RuntimeError('Unregistered module cache entry: '+name)
            # Check support dispatch before invoking its guard methods.
            for child in self._children:
                if full: child.recheck()
                elif child is self._dependencies.provider: child._active(); child._check_signal()
                else:
                    child._active(); child._check_dirs()
                    for fd, parent, name, expected in child._files.values():
                        if (_identity(os.fstat(fd)) != expected or
                                _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
                            raise RuntimeError('Held source/runtime file metadata changed')
            if self._dependencies is not None:
                cls.recheck(receiver)
                if full: self._dependencies.images()
            if _identity(os.stat('/proc/self/exe')) != self._image: raise RuntimeError('Running interpreter object differs')
            if _process(os.getpid()) != self._process or _process(os.getppid()) != self._parent:
                raise RuntimeError('Worker or parent identity changed')
            if dict(os.environ) != self._reg['environment'] or os.getcwd() != self._reg['cwd']:
                raise RuntimeError('Worker environment/cwd changed')
            self._clock()
        except BaseException as error: self._fail(error); raise

    def snapshot(self):
        try:
            self.recheck()
            result = {'kind':'puck-worker-source-bootstrap-receipt-v1', 'version':1,
                'registration_sha256':self._sha, 'python_version':'.'.join(map(str, sys.version_info[:3])),
                'process':self._process, 'parent':self._parent, 'interpreter_object_bound':True,
                'environment_sha256':digest(canonical(self._reg['environment'])),
                'loaded_modules':[{'name':name, 'path':binding[-2], 'sha256':binding[-1]}
                    for name, binding in sorted(self._loaded.items())],
                'trusted_boundary':['CPython stdlib', 'interpreter ELF dependencies'],
                'runtime_qualified':False, 'dependencies_qualified':False, 'native_authorized':False,
                'collection_authorized':False, 'executable':False, 'qualification_claims':[]}
            if self._dependencies is not None: result['dependencies'] = self._dependencies.snapshot()
            if self._reg['version']==3:
                result['stdlib_cache_aliases']=({'__mp_main__':'__main__'} if '__mp_main__' in sys.modules else {})
                result['denied_imports']=sorted(self._denied_imports)
                if self._missing_policy_version>=2:
                    result['expected_missing_imports']=list(self._negative_imports)
            if len(canonical(result)) > MiB: raise ValueError('Bootstrap receipt ceiling exceeded')
            self.recheck(); return copy.deepcopy(result)
        except BaseException as error: self._fail(error); raise

    def invoke(self):
        try:
            self.recheck()
            qualification=self._reg['version']==3
            module = __import__(QUALIFICATION_ENTRY if qualification else ENTRY,
                fromlist=['qualify' if qualification else 'preflight'])
            self.recheck(); result = module.qualify(self) if qualification else module.preflight(self); self.recheck()
            if type(result) is not dict or len(canonical(result)) > 64*1024:
                raise ValueError('Bounded source-preflight result required')
            # Result data cannot overwrite receipt identity or authority fields.
            receipt = self.snapshot(); receipt['entry_result'] = copy.deepcopy(result)
            return receipt
        except BaseException as error:
            self._fail(error)
            if error is not self._first_failure:
                raise error from self._first_failure
            raise

    def __exit__(self, exc_type, exc, tb):
        if exc is not None:
            self._fail(exc); return False
        if self._state != 'active': raise RuntimeError('Failed bootstrap cannot close successfully')
        self.recheck(); error = self._close()
        if error is not None: raise error
        self._clock()


def main():
    if len(sys.argv) != 5: raise ValueError('Exact seeded bootstrap arguments required')
    registration_path, expected = sys.argv[3:5]
    payload = _read_initial(registration_path, expected)
    with HeldWorkerBootstrap(payload, expected_sha256=expected,
            deadline=time.monotonic()+180, registration_path=registration_path) as admission:
        receipt = admission.invoke()
    # Terminal transport after successful final recheck/close. Parent must bind
    # this to independently observed identity, exit, drained descendants and
    # durable publication; stdout alone is not an owner grant.
    print(canonical(receipt).decode(), flush=True)


if __name__ == '__main__': main()
