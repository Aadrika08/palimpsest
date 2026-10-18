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
_PUBLISH_PHASE = 'module_exec_publish'


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
        # module_aliases is optional; profiles without it keep their exact v2 shape.
        aliased=('module_aliases',) if 'module_aliases' in profile else ()
        _fields(profile, (*groups,'kind','version','native_cache',*aliased))
        if (not allow_native_cache or profile['kind']!='puck-producer-import-profile-v2'
                or type(profile['version']) is not int or profile['version']!=2):
            raise ValueError('Explicit v3 native cache import profile required')
        groups+=('native_cache',*aliased)
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
        publishing=type(row) is dict and row.get('phase')==_PUBLISH_PHASE
        _fields(row, ('name','producer','phase','attributes','class_binding')+
                (('delegate_attributes',) if publishing else ()))
        name=_name(row['name']); source=producer(row)
        if (name in names or name in exports or name.split('.')[0] in sys.stdlib_module_names
                or name.split('.')[0]!=row['producer'].split('.')[0]):
            raise ValueError('Dependency export binding name overlaps or spoofs another namespace')
        exports.add(name)
        if publishing:
            if (not allow_native_cache or profile.get('kind')!='puck-producer-import-profile-v2'
                    or source['kind']!='python' or row['class_binding'] is not None):
                raise ValueError('Published dependency export requires explicit v3 Python producer binding')
            attributes=row['delegate_attributes']
            if (type(attributes) is not list or len(attributes)>MAX_CLASS_SLOTS or any(
                    type(v) is not str or len(v)>256 or not _IDENTIFIER.fullmatch(v)
                    or v.startswith('__') for v in attributes)
                    or attributes!=sorted(set(attributes))):
                raise ValueError('Published dependency export dispatch keys must be finite, sorted and distinct')
        elif row['phase'] not in ('native_create','module_exec') or (
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
        # late_delegates is optional; rows without it keep the closed-at-creator contract.
        _fields(row, ('name','producer','phase','delegate_attributes')+(('late_delegates',) if 'late_delegates' in row else ()))
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
        if 'late_delegates' in row:
            late=row['late_delegates']
            if type(late) is not list or not 1<=len(late)<=64:
                raise ValueError('Native cache late delegates must be a finite nonempty list')
            keys=[]
            for item in late:
                _fields(item,('attribute','producers'))
                key=item['attribute'];producers=item['producers']
                if (type(key) is not str or len(key)>256 or not _IDENTIFIER.fullmatch(key) or key.startswith('__')
                        or key in attributes):
                    raise ValueError('Native cache late delegate key is invalid or already a creator key')
                if type(producers) is not list or not 1<=len(producers)<=16:
                    raise ValueError('Native cache late delegate requires finite declared producers')
                pairs=[]
                for producer in producers:
                    _fields(producer,('producer','phase'))
                    if (_name(producer['producer']) not in physical or physical[producer['producer']]['kind']!='extension'
                            or producer['phase'] not in ('native_create','module_exec')):
                        raise ValueError('Native cache late delegate producer must be a registered extension phase')
                    pairs.append((producer['producer'],producer['phase']))
                if pairs!=sorted(set(pairs)):
                    raise ValueError('Native cache late delegate producers must be sorted and distinct')
                keys.append(key)
            if keys!=sorted(set(keys)):
                raise ValueError('Native cache late delegate keys must be sorted and distinct')
        cached.add(name)
    if 'module_aliases' in profile:
        rows=profile['module_aliases']
        if not 1<=len(rows)<=16:
            raise ValueError('Dependency module aliases must be a finite nonempty list')
        aliased=[]
        for row in rows:
            _fields(row, ('name','target'))
            name=_name(row['name']); target=_name(row['target'])
            if ('.' in name or name in names or name in exports or name in cached or name in aliased
                    or name in sys.stdlib_module_names or name in ('__main__','__mp_main__','_puck_held_file_bootstrap')):
                raise ValueError('Dependency module alias overlaps or spoofs another namespace')
            # Only an extension registering itself under its own compiled bare name.
            if target not in physical or physical[target]['kind']!='extension' or target.rsplit('.',1)[-1]!=name:
                raise ValueError('Dependency module alias must be its extension\'s own compiled bare name')
            aliased.append(name)
        if aliased!=sorted(set(aliased)):
            raise ValueError('Dependency module aliases must be sorted and distinct')


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
    for index,key in enumerate(attributes):
        namespace=_namespace(value)
        if key not in namespace:
            raise RuntimeError('Dependency producer attribute binding is missing: '
                               f'component {key!r} at index {index}')
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
        # Declared later producers per (cache, key), and each key's reference sealed at its producer's close.
        self.late={(v['name'],item['attribute']):{(p['producer'],p['phase']) for p in item['producers']}
                   for v in profile.get('native_cache',[]) for item in v.get('late_delegates',[])}
        # A late key first seen while a declared producer is innermost stays pending (its reference
        # fixed) through nested phases, and is sealed at that producer's own close.
        self.late_seals={}; self.late_pending={}
        self.published={r['name']:r for r in profile['exports'] if r['phase']==_PUBLISH_PHASE}
        self.publication_closed=set(); self.publication_phases=set()
        self.aliases={v['name']:v['target'] for v in profile.get('module_aliases',[])}; self.alias_seals={}
        if any(name in sys.modules for name in self.aliases):
            raise RuntimeError('Dependency module alias is preexisting before its extension initialization')
        if any(name in sys.modules for name in self.native_cache):
            raise RuntimeError('Native cache entry is preexisting before native initialization')
        if any(name in sys.modules for name in self.published):
            raise RuntimeError('Published dependency export is preexisting before producer initialization')
    def open_phase(self, name, phase):
        require_instance_dispatch(self,ExportBindings)
        if not self.native_cache and not self.published and not self.aliases: return
        if len(self.phase_stack)>=MAX_PROFILE_ROWS:
            raise ValueError('Native cache initializer nesting exceeds bound')
        key=(name,phase)
        if phase=='module_exec' and any(r['producer']==name for r in self.published.values()):
            if key in self.publication_phases:
                raise RuntimeError('Published dependency export creator phase repeated')
            self.publication_phases.add(key)
        if any((r['producer'],r['phase'])==key for r in self.native_cache.values()):
            if key in self.cache_phases: raise RuntimeError('Native cache creator phase repeated')
            self.cache_phases.add(key)
        if any(key in producers for producers in self.late.values()):
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
            late={item['attribute'] for item in row.get('late_delegates',[])}
            if not keys<=expected|late or (name in self.cache_closed and keys-late!=expected):
                raise RuntimeError('Native cache dispatch keys differ from the finite declaration')
            if name in self.cache_closed and any(
                    module_dict(value).get(key,_MISSING) is not delegate
                    for key,delegate in previous.delegates):
                raise RuntimeError('Native cache dispatch reference changed')
            for key in late:
                fixed=self.late_seals.get((name,key),_MISSING)
                if fixed is _MISSING and (name,key) in self.late_pending:fixed=self.late_pending[(name,key)][1]
                present=module_dict(value).get(key,_MISSING)
                if fixed is not _MISSING:
                    if present is not fixed:raise RuntimeError('Native cache late delegate changed or disappeared')
                elif present is not _MISSING:
                    if name not in self.cache_closed or current_phase not in self.late[(name,key)]:
                        raise RuntimeError('Native cache late delegate appeared outside its declared producer')
                    self.late_pending[(name,key)]=(current_phase,present)
        ExportBindings._alias_recheck(self,current_phase)
    def _alias_recheck(self, current_phase):
        for name,target in self.aliases.items():
            value=sys.modules.get(name,_MISSING); sealed=self.alias_seals.get(name)
            if sealed is not None:
                if value is not sealed: raise RuntimeError('Dependency module alias changed or disappeared')
                continue
            if value is _MISSING: continue
            if (current_phase!=(target,'module_exec') or type(value) is not types.ModuleType
                    or value is not sys.modules.get(target)):
                raise RuntimeError('Dependency module alias appeared outside its own extension exec')
            self.alias_seals[name]=value
    def _publication_recheck(self):
        current_phase=self.phase_stack[-1] if self.phase_stack else None
        for name,row in self.published.items():
            value=sys.modules.get(name,_MISSING)
            previous=self.prepared.get(name)
            if value is _MISSING:
                if previous is not None:
                    raise RuntimeError('Published dependency export cache entry disappeared')
                continue
            if previous is None and current_phase!=(row['producer'],'module_exec'):
                raise RuntimeError('Published dependency export appeared outside its creator phase')
            if type(value) is not types.ModuleType:
                raise RuntimeError('Published dependency export must be a plain module')
            raw=module_dict(value)
            if type(raw.get('__name__')) is not str or raw['__name__']!=name or '__path__' in raw:
                raise RuntimeError('Published dependency export metadata differs')
            producer=self.producers.get(row['producer'])
            if producer is None or _resolve(producer,row['attributes']) is not value:
                raise RuntimeError('Published dependency export raw producer edge differs')
            if previous is not None:
                if value is not previous[1].module:
                    raise RuntimeError('Published dependency export cache object changed')
                ModuleSeal.recheck(previous[1])
            observed=ModuleSeal(value,virtual=True,expected_name=name)
            keys={key for key,_ in observed.delegates}; declared=set(row['delegate_attributes'])
            if not keys<=declared or (name in self.publication_closed and keys!=declared):
                raise RuntimeError('Published dependency export dispatch keys differ')
            if (previous is not None and keys-{key for key,_ in previous[1].delegates}
                    and current_phase!=(row['producer'],'module_exec')):
                raise RuntimeError('Published dependency export dispatch appeared outside its creator phase')
            # Seal every observed addition while retaining all earlier references.
            self.prepared[name]=(row,observed)
    def close_phase(self, name, phase):
        require_instance_dispatch(self,ExportBindings)
        if not self.native_cache and not self.published and not self.aliases: return
        key=(name,phase)
        if not self.phase_stack or self.phase_stack[-1]!=key:
            raise RuntimeError('Native cache initializer phase stack differs')
        # Screen while this initializer is still innermost: popping first would
        # misattribute a nested creator's new object to its outer caller.
        ExportBindings._cache_recheck(self)
        ExportBindings._publication_recheck(self)
        if phase=='module_exec':
            for export,row in self.published.items():
                if row['producer']!=name: continue
                previous=self.prepared.get(export)
                if previous is None:
                    raise RuntimeError('Published dependency export creator did not publish required entry')
                if {key for key,_ in previous[1].delegates}!=set(row['delegate_attributes']):
                    raise RuntimeError('Published dependency export dispatch keys incomplete at creator close')
                self.publication_closed.add(export)
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
        # Seal each pending late key at the close of the producer phase that added it.
        for item,(owner,delegate) in list(self.late_pending.items()):
            if owner==key:self.late_seals[item]=delegate;del self.late_pending[item]
        self.phase_stack.pop()
        ExportBindings._cache_recheck(self)
        ExportBindings._publication_recheck(self)
    def require_complete(self):
        require_instance_dispatch(self,ExportBindings)
        ExportBindings._cache_recheck(self)
        ExportBindings._publication_recheck(self)
        if self.published and (self.phase_stack or self.publication_closed!=set(self.published)):
            raise RuntimeError('Published dependency export terminal completion is incomplete')
        if (self.phase_stack or set(self.cache_seals)!=set(self.native_cache) or self.cache_closed!=set(self.native_cache)
                or set(self.late_seals)!=set(self.late)):
            raise RuntimeError('Native cache terminal completion is incomplete')
        if set(self.alias_seals)!=set(self.aliases):
            raise RuntimeError('Dependency module alias terminal completion is incomplete')
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
            try:
                value=_resolve(producer,row['attributes'])
            except RuntimeError as error:
                raise RuntimeError('Dependency export binding resolution failed: '
                    f'producer={name!r}; phase={phase!r}; export={row["name"]!r}; '
                    f'attributes={row["attributes"]!r}') from error
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
        ExportBindings._publication_recheck(self)
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
        return set(self.active)|set(self.cache_seals)|set(self.alias_seals)
