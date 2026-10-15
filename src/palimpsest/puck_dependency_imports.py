"""Registered dependency imports from held bytes, without numerical authority.

Native map observations cover persistent file images only. Pre-existing images,
stdlib native images, transient mappings and anonymous/JIT code are unqualified.
"""
from __future__ import annotations

import importlib.abc
import importlib.machinery
import importlib.metadata
import importlib.resources.abc
import importlib.util
import io
import os
from pathlib import PurePosixPath
import re
import sys

from .puck_dependency_files import HeldDependencyNamespace
from .puck_dependency_bindings import ExportBindings, module_dict
from .puck_native_origins import native_load_path, require_native_target


def _normalized(name):
    return re.sub(r'[-_.]+', '-', name).lower()


def _maps():
    with open('/proc/self/maps', 'rb') as stream:
        raw = stream.read(4*1024**2+1)
    lines = raw.splitlines()
    if len(raw) > 4*1024**2 or len(lines) > 65536:
        raise ValueError('Native image observation ceiling exceeded')
    result = {}
    for line in lines:
        fields = line.split(None, 5)
        if len(fields) < 5:
            raise ValueError('Malformed native image observation')
        inode = int(fields[4])
        if not inode:
            continue
        if len(fields) != 6:
            raise ValueError('File image lacks a pathname')
        path = os.fsdecode(fields[5])
        if not path.startswith('/') or '\\' in path or path.endswith(' (deleted)'):
            raise ValueError('Ambiguous native image pathname')
        major, minor = (int(v, 16) for v in fields[3].split(b':'))
        key = (os.makedev(major, minor), inode)
        result.setdefault(key, set()).add(path)
    return result


class _Resource(importlib.resources.abc.Traversable):
    def __init__(self, owner, index, path):
        self.owner, self.index, self.path = owner, index, path
    @property
    def name(self): return PurePosixPath(self.path).name
    def is_file(self): return self.path in self.owner.files[self.index]
    def is_dir(self): return any(p.startswith(self.path+'/') for p in self.owner.files[self.index])
    def iterdir(self):
        self.owner.guard()
        if not self.is_dir(): raise NotADirectoryError(self.path)
        prefix = self.path+'/'
        names = sorted({p[len(prefix):].split('/')[0] for p in self.owner.files[self.index] if p.startswith(prefix)})
        return iter(_Resource(self.owner, self.index, prefix+n) for n in names)
    def joinpath(self, *descendants):
        path = self.path
        for value in descendants:
            if (type(value) is not str or not value or value.startswith('/') or '\\' in value
                    or any(p in ('', '.', '..') for p in value.split('/'))):
                raise ValueError('Registered resource path required')
            path += '/'+value
        return _Resource(self.owner, self.index, path)
    def open(self, mode='r', *args, **kwargs):
        if mode not in ('r', 'rb'): raise ValueError('Resources are read-only')
        self.owner.guard()
        payload = self.owner.provider.read(self.index, self.path)
        self.owner.guard()
        binary = io.BytesIO(payload)
        return binary if mode == 'rb' else io.TextIOWrapper(binary, *args, **kwargs)


class _Reader(importlib.resources.abc.TraversableResources):
    def __init__(self, owner, row): self.owner, self.row = owner, row
    def files(self):
        directory = (self.row['path'].rsplit('/', 1)[0]
                     if self.row.get('is_package') else self.row['path'])
        return _Resource(self.owner, self.row['root_index'], directory)


class _Distribution(importlib.metadata.Distribution):
    def __init__(self, owner, row): self.owner, self.row = owner, row
    def read_text(self, filename):
        directory = self.row['metadata_path'].rsplit('/', 1)[0]
        if type(filename) is not str or '/' in filename or filename in ('', '.', '..'):
            raise ValueError('Registered distribution metadata leaf required')
        path = directory+'/'+filename
        if path not in self.owner.files[self.row['root_index']]: return None
        self.owner.guard()
        raw = self.owner.provider.read(self.row['root_index'], path)
        self.owner.guard()
        return raw.decode('utf-8')
    def locate_file(self, path):
        text = str(path)
        if text not in self.owner.files[self.row['root_index']]:
            raise ValueError('Unregistered distribution file')
        self.owner.guard()
        return self.owner.provider._holders[self.row['root_index']].root/text


class _Loader(importlib.abc.Loader):
    def __init__(self, owner, row): self.owner, self.row = owner, row
    def create_module(self, spec):
        if self.row.get('kind') != 'extension': return None
        owner = self.owner
        owner.loading.add(spec.name)
        try:
            owner.full_guard()
            policy=owner.native_origins.get(spec.name,'exact-file-fd-v1')
            self.native = importlib.machinery.ExtensionFileLoader(spec.name,
                native_load_path(owner.provider,self.row,policy))
            # CPython create_dynamic consumes spec.origin, not just loader.path.
            spec.origin = self.native.path
            module = self.native.create_module(spec)
            owner.bindings.begin(spec.name,module)
            owner.bindings.complete(spec.name,'native_create')
            owner.full_guard(); owner.images()
            require_native_target(owner.provider,self.row,policy,owner._observed)
            return module
        except BaseException as error:
            owner.fail(error); raise
        finally: owner.loading.discard(spec.name)
    def exec_module(self, module):
        owner = self.owner; name = self.row['name']
        owner.loading.add(name)
        try:
            owner.guard()
            if self.row.get('kind') == 'extension':
                owner.full_guard(); self.native.exec_module(module); owner.full_guard()
            elif self.row.get('kind') == 'python':
                payload = owner.provider.read(self.row['root_index'], self.row['path'])
                module.__file__ = self.get_filename(name)
                if self.row['is_package']: module.__path__ = []
                code=compile(payload, module.__file__, 'exec', dont_inherit=True)
                owner.bindings.begin(name,module,code)
                exec(code,module_dict(module))
            else:
                module.__file__ = None; module.__path__ = []
            if self.row.get('kind')!='python': owner.bindings.begin(name,module)
            owner.bindings.complete(name,'module_exec')
            owner.capture(name, module)
            owner.guard(); owner.images()
        except BaseException as error:
            owner.fail(error); raise
        finally: owner.loading.discard(name)
    def get_filename(self, fullname):
        return str(self.owner.provider._holders[self.row['root_index']].root/self.row['path'])
    def get_resource_reader(self, fullname):
        return _Reader(self.owner, self.row) if self.row.get('is_package', True) else None
    def get_source(self, fullname):
        if self.row.get('kind') != 'python': return None
        self.owner.guard()
        raw = self.owner.provider.read(self.row['root_index'], self.row['path'])
        self.owner.guard()
        return importlib.util.decode_source(raw)
    def get_data(self, path):
        root = str(self.owner.provider._holders[self.row['root_index']].root)+'/'
        if not path.startswith(root): raise ValueError('Unregistered loader data path')
        relative = path[len(root):]
        if relative not in self.owner.files[self.row['root_index']]: raise ValueError('Unregistered loader data path')
        self.owner.guard(); raw = self.owner.provider.read(self.row['root_index'], relative)
        self.owner.guard(); return raw


class DependencyImports:
    def __init__(self, provider, guard, full_guard, fail, local_names, local_roots):
        self.provider, self.guard, self.full_guard, self.fail = provider, guard, full_guard, fail
        self.modules = {r['name']:r for r in provider.module_records()}
        self.namespaces = {r['name']:r for r in provider.namespace_records()}
        self.distributions = provider.distribution_records()
        profile=provider.import_profile()
        self.bindings=ExportBindings(profile)
        self.native_origins={v['name']:v['policy'] for v in profile['native_origins']}
        if {v['name'] for v in profile['exports']} & set(local_names):
            raise ValueError('Dependency export and source import mappings overlap')
        if (self.modules.keys() | self.namespaces.keys()) & set(local_names):
            raise ValueError('Dependency and source import mappings overlap')
        roots = [str(v.root) for v in provider._holders]
        if any(a == b or a.startswith(b+'/') or b.startswith(a+'/') for a in roots for b in local_roots):
            raise ValueError('Dependency and source/runtime roots overlap')
        self.files = [set(h._entries) for h in provider._holders]
        self.loading = set(); self.loaded = {}
        self.baseline = _maps()
        self.held = {(v[3][0], v[3][1]) for h in provider._holders for v in h._files.values()}
        self._observed = {}
    def find_spec(self, fullname):
        row = self.modules.get(fullname) or self.namespaces.get(fullname)
        if row is None: return None
        loader = _Loader(self, row)
        return importlib.util.spec_from_loader(fullname, loader, origin=loader.get_filename(fullname),
            is_package=row.get('is_package', True))
    def find_distributions(self, context):
        self.guard()
        name = context.name
        return iter(_Distribution(self, row) for row in self.distributions
                    if name is None or _normalized(name) == _normalized(row['name']))
    def capture(self, name, module):
        current,seal=self.bindings.finish_module(name,module)
        self.loaded[name]=(current,seal)
    def recheck(self):
        self.provider._active(); self.provider._check_signal()
        active=self.bindings.recheck()
        for name,(module,seal) in self.loaded.items():
            if sys.modules.get(name) is not module:
                raise RuntimeError('Held dependency module dispatch changed')
            seal.recheck()
        return active
    def images(self):
        observed = _maps()
        for key, paths in observed.items():
            if key in self.baseline or key in self.held: continue
            # Standard-library extension trust is explicitly unqualified. Bind the
            # observed object to that pathname; do not allow similarly named files.
            for path in paths:
                prefix = sys.base_prefix+'/lib/python3.11/lib-dynload/'
                if not path.startswith(prefix) or '/' in path[len(prefix):]:
                    raise RuntimeError('Unregistered native file image: '+path)
                state = os.stat(path, follow_symlinks=False)
                if (state.st_dev, state.st_ino) != key:
                    raise RuntimeError('Standard-library native image identity differs')
        self._observed = observed
        return {'held_file_images':[{'device':dev,'inode':ino,'paths':sorted(paths)}
                    for (dev,ino),paths in sorted(observed.items()) if (dev,ino) in self.held],
                'baseline_file_images':len(self.baseline), 'transient_images_covered':False,
                'anonymous_code_qualified':False, 'native_closure_qualified':False}
    def snapshot(self):
        self.recheck()
        receipt = self.provider.snapshot()
        receipt['loaded_modules'] = [{'name':name, 'path':(self.modules.get(name) or self.namespaces[name])['path']}
                                      for name in sorted(self.loaded)]
        receipt['exported_modules']=[{'name':name,'producer':self.bindings.prepared[name][0]['producer']}
                                     for name in sorted(self.bindings.active)]
        receipt['native_origin_policies']=dict(self.native_origins)
        receipt['images'] = self.images()
        return receipt
