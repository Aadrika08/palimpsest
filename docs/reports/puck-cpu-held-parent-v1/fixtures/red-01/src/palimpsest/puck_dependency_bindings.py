"""Finite producer-bound import identities, never a namespace allowlist.

Initialization executes trusted held package/native code. These seals detect
later dispatch changes; they are not isolation from malicious in-process code.
Framework __getattr__/__getattribute__ hooks are bypassed for metadata checks.
"""
from __future__ import annotations

import importlib.machinery
import re
import sys
import types

MAX_PROFILE_ROWS = 1024
MAX_CLASS_SLOTS = 4096
MAX_CODE_OBJECTS = 65536
_IDENTIFIER = re.compile(r'[A-Za-z_]\w*', re.ASCII)
_NAME = re.compile(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*', re.ASCII)
_MISSING = object()


def _fields(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError('Dependency import profile binding fields differ')


def _name(value):
    if type(value) is not str or len(value)>512 or not _NAME.fullmatch(value):
        raise ValueError('Dependency import profile requires a finite module name')
    return value


def _attributes(value):
    if (type(value) is not list or not 1<=len(value)<=8 or any(
            type(v) is not str or len(v)>256 or not _IDENTIFIER.fullmatch(v)
            or v.startswith('__') for v in value)):
        raise ValueError('Dependency profile requires bounded raw attribute paths')


def _profile_groups(profile, *, allow_native_cache=False):
    groups=('exports','module_changes','native_origins')
    extended=type(profile) is dict and 'kind' in profile
    if extended:
        _fields(profile, (*groups,'kind','version','native_cache'))
        if (not allow_native_cache or profile['kind']!='puck-producer-import-profile-v2'
                or type(profile['version']) is not int or profile['version']!=2):
            raise ValueError('Explicit v3 native cache import profile required')
        groups+=('native_cache',)
    else:
        _fields(profile, groups)
    if any(type(profile[k]) is not list for k in groups):
        raise ValueError('Dependency import profile rows must be lists')
    if sum(len(profile[k]) for k in groups)>MAX_PROFILE_ROWS:
        raise ValueError('Dependency import profile row ceiling exceeded')
    return groups


def validate_profile(profile, modules, namespaces, *, allow_native_cache=False):
    """Validate before payload IO; physical producer records are already checked."""
    _profile_groups(profile, allow_native_cache=allow_native_cache)
    physical={v['name']:v for v in modules}
    names=set(physical)|{v['name'] for v in namespaces}
    def producer(row):
        name=_name(row['producer'])
        if name not in physical: raise ValueError('Dependency binding producer is not registered physical source')
        _attributes(row['attributes'])
        return physical[name]
    def class_binding(row, *, base=False):
        if type(row) is not dict: raise ValueError('Dependency class binding must be declared')
        kind=row.get('kind')
        if kind=='direct':
            _fields(row, ('kind','producer','attributes'))
            if producer(row)['kind']!='python':
                raise ValueError('Dependency class anchor requires registered Python source')
        elif kind=='factory' and not base:
            _fields(row, ('kind','producer','attributes','nested','bases'))
            if producer(row)['kind']!='python': raise ValueError('Dependency factory must bind Python source')
            nested=row['nested']
            if type(nested) is not str or len(nested)>256 or not _IDENTIFIER.fullmatch(nested):
                raise ValueError('Dependency factory nested class name invalid')
            if type(row['bases']) is not list or not 1<=len(row['bases'])<=8:
                raise ValueError('Dependency factory base bindings invalid')
            for item in row['bases']: class_binding(item, base=True)
        else: raise ValueError('Unknown dependency class binding kind')
    exports=set()
    for row in profile['exports']:
        _fields(row, ('name','producer','phase','attributes','class_binding'))
        name=_name(row['name']); source=producer(row)
        if (name in names or name in exports or name.split('.')[0] in sys.stdlib_module_names
                or name.split('.')[0]!=row['producer'].split('.')[0]):
            raise ValueError('Dependency export binding name overlaps or spoofs another namespace')
        exports.add(name)
        if row['phase'] not in ('native_create','module_exec') or (
                row['phase']=='native_create' and source['kind']!='extension'):
            raise ValueError('Dependency export binding phase differs from producer kind')
        if row['class_binding'] is not None: class_binding(row['class_binding'])
    changed=set()
    for row in profile['module_changes']:
        _fields(row, ('name','kind','class_binding')); name=_name(row['name'])
        if name not in physical or physical[name]['kind']!='python' or name in changed:
            raise ValueError('Dependency module-change binding must name one physical Python module')
        if row['kind'] not in ('replace','reclassify'): raise ValueError('Unknown dependency module-change kind')
        changed.add(name); class_binding(row['class_binding'])
    native=set()
    for row in profile['native_origins']:
        _fields(row, ('name','policy')); name=_name(row['name'])
        if name not in physical or physical[name]['kind']!='extension' or name in native:
            raise ValueError('Dependency native origin binding must name one extension')
        if row['policy'] not in ('exact-file-fd-v1','held-directory-observed-v1'):
            raise ValueError('Unknown dependency native origin profile')
        native.add(name)

    if len(profile.get('native_cache',[]))>128:
        raise ValueError('Native cache name count exceeds the physical-absence proof bound')
    cached=set()
    for row in profile.get('native_cache', []):
        _fields(row, ('name','producer','phase','delegate_attributes'))
        name=_name(row['name']); source=_name(row['producer'])
        if ('.' in name or name in names or name in exports or name in cached
                or name.split('.')[0] in sys.stdlib_module_names
                or name in ('__main__','__mp_main__','_puck_held_file_bootstrap')):
            raise ValueError('Native cache name overlaps or spoofs another namespace')
        if source not in physical or physical[source]['kind']!='extension':
            raise ValueError('Native cache creator must be a registered extension')
        if row['phase'] not in ('native_create','module_exec'):
            raise ValueError('Native cache creation phase is invalid')
        attributes=row['delegate_attributes']
        if (type(attributes) is not list or len(attributes)>MAX_CLASS_SLOTS or any(
                type(v) is not str or len(v)>256 or not _IDENTIFIER.fullmatch(v)
                or v.startswith('__') for v in attributes)
                or attributes!=sorted(set(attributes))):
            raise ValueError('Native cache dispatch keys must be finite, sorted and distinct')
        cached.add(name)


def module_dict(module):
    if not isinstance(module, types.ModuleType):
        raise RuntimeError('Dependency binding is not a module object')
    return types.ModuleType.__dict__['__dict__'].__get__(module)


def _namespace(value):
    if isinstance(value, types.ModuleType): return module_dict(value)
    if type(value) is type: return type.__getattribute__(value, '__dict__')
    raise RuntimeError('Dependency attribute binding crosses a non-module/class object')


def _resolve(module, attributes):
    value=module
    for key in attributes:
        namespace=_namespace(value)
        if key not in namespace: raise RuntimeError('Dependency producer attribute binding is missing')
        value=namespace[key]
    return value


def _codes(code):
    result=[]; seen=set(); stack=[code]
    while stack:
        item=stack.pop()
        if id(item) in seen: continue
        seen.add(id(item)); result.append(item)
        if len(result)>MAX_CODE_OBJECTS: raise ValueError('Dependency compiled code ceiling exceeded')
        stack.extend(v for v in item.co_consts if type(v) is types.CodeType)
    return tuple(result)


def _functions(slot):
    if type(slot) is types.FunctionType: return (slot,)
    if type(slot) in (staticmethod,classmethod): return (slot.__func__,)
    if type(slot) is property: return tuple(v for v in (slot.fget,slot.fset,slot.fdel) if v is not None)
    return ()


def require_instance_dispatch(instance, expected_class):
    """Reject a changed receiver or an instance shadow of authenticated methods."""
    if type(instance) is not expected_class:
        raise RuntimeError('Authenticated dependency instance dispatch type changed')
    namespace=object.__getattribute__(instance,'__dict__')
    for cls in expected_class.__mro__:
        for key,slot in vars(cls).items():
            if key in namespace and type(slot) in (types.FunctionType,staticmethod,classmethod,property):
                raise RuntimeError('Authenticated dependency instance dispatch shadow changed')


class _ClassSeal:
    def __init__(self, cls):
        if type(cls) is not type or not issubclass(cls,types.ModuleType):
            raise RuntimeError('Dependency class binding requires a plain ModuleType subclass')
        self.cls=cls; self.rows=[]
        for base in cls.__mro__:
            if base in (types.ModuleType,object): continue
            if type(base) is not type: raise RuntimeError('Dependency class metaclass is unsupported')
            items=tuple(type.__getattribute__(base,'__dict__').items())
            if len(items)+sum(len(v[2]) for v in self.rows)>MAX_CLASS_SLOTS:
                raise ValueError('Dependency class binding slot ceiling exceeded')
            functions=tuple((fn,fn.__code__) for _,slot in items for fn in _functions(slot))
            self.rows.append((base,base.__bases__,items,functions))
    def recheck(self):
        require_instance_dispatch(self,_ClassSeal)
        for cls,bases,items,functions in self.rows:
            current=type.__getattribute__(cls,'__dict__')
            if (cls.__bases__!=bases or tuple(current)!=tuple(k for k,_ in items)
                    or any(current[k] is not value for k,value in items)
                    or any(fn.__code__ is not code for fn,code in functions)):
                raise RuntimeError('Held dependency class/code binding changed')


class ModuleSeal:
    def __init__(self, module, *, virtual=False, expected_name=None):
        self.module=module; self.cls=type(module); self.virtual=virtual
        self.expected_name=expected_name
        self.state=self._state()
        # Capture direct dispatch-reference edges created by the trusted producer.
        # New data attributes remain possible; existing module/class/function
        # delegates cannot switch objects after this phase closes.
        self.delegates=tuple((key,value) for key,value in module_dict(module).items()
            if virtual and isinstance(value,(types.ModuleType,type,types.FunctionType,types.BuiltinFunctionType)))
        if len(self.delegates)>MAX_CLASS_SLOTS:
            raise ValueError('Dependency delegate binding ceiling exceeded')
    def _state(self):
        raw=module_dict(self.module)
        spec=raw.get('__spec__')
        if spec is None:
            if not self.virtual: raise RuntimeError('Held dependency module lacks its spec')
            spec_state=None
        else:
            if type(spec) is not importlib.machinery.ModuleSpec:
                raise RuntimeError('Held dependency spec type changed')
            d=vars(spec)
            if self.expected_name is not None and d.get('name')!=self.expected_name:
                raise RuntimeError('Held dependency physical spec name differs')
            spec_state=(spec,d.get('name'),d.get('loader'),d.get('origin'),
                        tuple(d.get('submodule_search_locations') or ()))
        path=raw.get('__path__',())
        if type(path) not in (list,tuple) or len(path)>128 or any(type(v) is not str for v in path):
            raise RuntimeError('Held dependency search path binding invalid')
        return (type(self.module),raw.get('__name__'),raw.get('__loader__'),spec_state,
                raw.get('__file__'),raw.get('__package__'),tuple(path))
    def recheck(self):
        require_instance_dispatch(self,ModuleSeal)
        raw=module_dict(self.module)
        if any(raw.get(key,_MISSING) is not value for key,value in self.delegates):
            raise RuntimeError('Held dependency delegate binding changed')
        current=self._state(); expected=self.state
        spec,old_spec=current[3],expected[3]
        spec_changed=((spec is None)!=(old_spec is None) or
            (spec is not None and old_spec is not None and
             (spec[0] is not old_spec[0] or spec[2] is not old_spec[2]
              or (spec[1],spec[3],spec[4])!=(old_spec[1],old_spec[3],old_spec[4]))))
        if (current[0] is not expected[0] or current[2] is not expected[2] or spec_changed
                or (current[1],*current[4:])!=(expected[1],*expected[4:])):
            raise RuntimeError('Held dependency module dispatch changed')


class ExportBindings:
    def __init__(self, profile):
        self.profile=profile; self.producers={}; self.code={}; self.prepared={}; self.active={}
        self.changes={v['name']:v for v in profile['module_changes']}
        self.class_seals=[]; self.anchors=[]; self.originals={}
        self.native_cache={v['name']:v for v in profile.get('native_cache',[])}
        self.cache_seals={}; self.cache_closed=set(); self.phase_stack=[]; self.cache_phases=set()
        if any(name in sys.modules for name in self.native_cache):
            raise RuntimeError('Native cache entry is preexisting before native initialization')
    def open_phase(self, name, phase):
        require_instance_dispatch(self,ExportBindings)
        if not self.native_cache: return
        if len(self.phase_stack)>=MAX_PROFILE_ROWS:
            raise ValueError('Native cache initializer nesting exceeds bound')
        key=(name,phase)
        if any((r['producer'],r['phase'])==key for r in self.native_cache.values()):
            if key in self.cache_phases: raise RuntimeError('Native cache creator phase repeated')
            self.cache_phases.add(key)
        self.phase_stack.append(key)
    def _cache_recheck(self):
        current_phase=self.phase_stack[-1] if self.phase_stack else None
        for name,row in self.native_cache.items():
            value=sys.modules.get(name,_MISSING)
            previous=self.cache_seals.get(name)
            if previous is None and value is _MISSING: continue
            if previous is not None and value is not previous.module:
                raise RuntimeError('Native cache object identity changed or disappeared')
            if previous is None and current_phase!=(row['producer'],row['phase']):
                raise RuntimeError('Native cache entry appeared outside its creator phase')
            if type(value) is not types.ModuleType:
                raise RuntimeError('Native cache object must be a plain module')
            raw=module_dict(value)
            if (raw.get('__name__')!=name or any(raw.get(k) is not None
                    for k in ('__spec__','__file__','__loader__')) or '__path__' in raw):
                raise RuntimeError('Native cache module metadata differs')
            if previous is None:
                previous=ModuleSeal(value,virtual=True,expected_name=name)
                self.cache_seals[name]=previous
            ModuleSeal.recheck(previous)
            # Compare all dispatch keys, including additions not in the first
            # seal. Data values may change; dispatch references may not escape
            # their finite declaration or the initial creator close.
            observed=ModuleSeal(value,virtual=True,expected_name=name)
            keys={key for key,_ in observed.delegates}
            expected=set(row['delegate_attributes'])
            if not keys<=expected or (name in self.cache_closed and keys!=expected):
                raise RuntimeError('Native cache dispatch keys differ from the finite declaration')
            if name in self.cache_closed and any(
                    module_dict(value).get(key,_MISSING) is not delegate
                    for key,delegate in previous.delegates):
                raise RuntimeError('Native cache dispatch reference changed')
    def close_phase(self, name, phase):
        require_instance_dispatch(self,ExportBindings)
        if not self.native_cache: return
        key=(name,phase)
        if not self.phase_stack or self.phase_stack[-1]!=key:
            raise RuntimeError('Native cache initializer phase stack differs')
        # Screen while this initializer is still innermost: popping first would
        # misattribute a nested creator's new object to its outer caller.
        ExportBindings._cache_recheck(self)
        for cache,row in self.native_cache.items():
            if (row['producer'],row['phase'])!=key: continue
            seal=self.cache_seals.get(cache)
            if seal is None: raise RuntimeError('Native cache creator did not publish required entry')
            ModuleSeal.recheck(seal)
            complete=ModuleSeal(seal.module,virtual=True,expected_name=cache)
            if {k for k,_ in complete.delegates}!=set(row['delegate_attributes']):
                raise RuntimeError('Native cache dispatch keys are incomplete at creator close')
            # Existing metadata/references were proved unchanged above. Capture
            # only the additional declared delegates produced by nested imports.
            self.cache_seals[cache]=complete; self.cache_closed.add(cache)
        self.phase_stack.pop()
        ExportBindings._cache_recheck(self)
    def require_complete(self):
        require_instance_dispatch(self,ExportBindings)
        ExportBindings._cache_recheck(self)
        if self.phase_stack or set(self.cache_seals)!=set(self.native_cache) or self.cache_closed!=set(self.native_cache):
            raise RuntimeError('Native cache terminal completion is incomplete')
    def begin(self, name, module, code=None):
        require_instance_dispatch(self,ExportBindings)
        if name in self.producers and self.producers[name] is not module:
            raise RuntimeError('Dependency producer cannot be reinitialized')
        self.producers[name]=module
        if code is not None: self.code[name]=_codes(code)
    def _anchor(self, record):
        producer=self.producers.get(record['producer'])
        if producer is None: raise RuntimeError('Dependency class producer has not initialized')
        value=_resolve(producer,record['attributes'])
        self.anchors.append((producer,tuple(record['attributes']),value))
        return producer,value
    def bind_class(self, cls, record):
        if record is None:
            if cls is not types.ModuleType: raise RuntimeError('Undeclared dependency module subclass')
            return
        producer,value=self._anchor(record)
        if record['kind']=='direct':
            if cls is not value: raise RuntimeError('Dependency module class differs from producer binding')
        else:
            if (type(value) is not types.FunctionType or value.__globals__ is not module_dict(producer)
                    or not any(value.__code__ is code for code in self.code.get(record['producer'],()))):
                raise RuntimeError('Dependency class factory is not held compiled source')
            expected=value.__code__.co_qualname+'.<locals>.'+record['nested']
            nested=[c for c in _codes(value.__code__) if c.co_qualname==expected]
            bases=tuple(self._anchor(v)[1] for v in record['bases'])
            if (type(cls) is not type or cls.__qualname__!=expected or cls.__bases__!=bases
                    or cls.__module__!=record['producer'] or len(nested)!=1):
                raise RuntimeError('Dependency generated class factory/base binding differs')
            allowed=_codes(nested[0])
            if any(fn.__globals__ is not module_dict(producer) or not any(fn.__code__ is code for code in allowed)
                   for slot in type.__getattribute__(cls,'__dict__').values() for fn in _functions(slot)):
                raise RuntimeError('Dependency generated class methods differ from held factory code')
            self.anchors.append((value,None,value.__code__))
        self.class_seals.append(_ClassSeal(cls))
    def complete(self, name, phase):
        require_instance_dispatch(self,ExportBindings)
        producer=self.producers[name]
        for row in self.profile['exports']:
            if row['producer']!=name or row['phase']!=phase: continue
            if row['name'] in self.prepared: raise RuntimeError('Dependency export phase repeated')
            value=_resolve(producer,row['attributes'])
            self.bind_class(type(value),row['class_binding'])
            self.prepared[row['name']]=(row,ModuleSeal(value,virtual=True))
        ExportBindings.recheck(self)
    def finish_module(self, name, original):
        require_instance_dispatch(self,ExportBindings)
        current=sys.modules.get(name)
        change=self.changes.get(name)
        if change is None:
            if current is not original or type(original) is not types.ModuleType:
                raise RuntimeError('Undeclared dependency module replacement or reclassification')
        else:
            if (current is original)!=(change['kind']=='reclassify'):
                raise RuntimeError('Dependency module transition kind differs')
            self.bind_class(type(current),change['class_binding'])
            if current is not original:
                self.originals[name]=ModuleSeal(original,expected_name=name)
        return current,ModuleSeal(current,virtual=change is not None,expected_name=name)
    def recheck(self):
        require_instance_dispatch(self,ExportBindings)
        for seal in self.originals.values(): ModuleSeal.recheck(seal)
        for producer,path,value in self.anchors:
            if (producer.__code__ is not value if path is None else _resolve(producer,path) is not value):
                raise RuntimeError('Held dependency producer/class anchor changed')
        for seal in self.class_seals: _ClassSeal.recheck(seal)
        for name,(row,seal) in self.prepared.items():
            if _resolve(self.producers[row['producer']],row['attributes']) is not seal.module:
                raise RuntimeError('Held dependency export producer edge changed')
            ModuleSeal.recheck(seal)
            current=sys.modules.get(name,_MISSING)
            if current is not _MISSING:
                if current is not seal.module: raise RuntimeError('Held dependency export cache object changed')
                self.active[name]=seal.module
            elif name in self.active: raise RuntimeError('Held dependency export cache entry disappeared')
        ExportBindings._cache_recheck(self)
        return set(self.active)|set(self.cache_seals)
