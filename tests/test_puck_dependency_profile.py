"""Finite import declarations exercised through real authored fresh workers."""
import json

import pytest
from test_puck_worker_dependencies import dependency_fixture
from test_puck_worker_bootstrap import descriptor


def direct(producer, *attributes):
    return {'kind':'direct', 'producer':producer, 'attributes':list(attributes)}


def upgrade(deps):
    deps.update(kind='puck-worker-dependencies-v2', version=2,
                import_profile={'exports':[], 'module_changes':[], 'native_origins':[]})
    return deps['import_profile']


def add_source(deps, root, name, code):
    relative = name.replace('.', '/')+'.py'
    path = root/relative; path.parent.mkdir(parents=True, exist_ok=True); path.write_text(code)
    deps['roots'][0]['files'].append(descriptor(path, relative))
    deps['roots'][0]['files'].sort(key=lambda row:row['path'])
    deps['modules'].append({'name':name, 'root_index':0, 'path':relative,
                            'kind':'python', 'is_package':False})


def fixture_profile(deps, root):
    profile = upgrade(deps)
    add_source(deps, root, 'fixture_dep.producer',
        'import types\n'
        'class Namespace(types.ModuleType):\n'
        '    def __getattribute__(self, name):\n'
        '        if name in ("__spec__", "__file__", "__path__", "__dict__"): raise AssertionError("HOOK")\n'
        '        return super().__getattribute__(name)\n'
        '    def answer(self): return 47\n'
        'namespace=Namespace("fixture_dep.virtual")\n'
        'nested=types.ModuleType("fixture_dep.nested")\n'
        'nested.actual_attribute=types.ModuleType("fixture_dep.cache_name")\n')
    profile['exports'] = [
        {'name':'fixture_dep.virtual', 'producer':'fixture_dep.producer', 'phase':'module_exec',
         'attributes':['namespace'], 'class_binding':direct('fixture_dep.producer','Namespace')},
        {'name':'fixture_dep.cache_name', 'producer':'fixture_dep.producer', 'phase':'module_exec',
         'attributes':['nested','actual_attribute'], 'class_binding':None}]
    return profile


def test_declared_export_is_prepared_before_later_cache_publication_without_hooks(tmp_path):
    body = ('import fixture_dep.producer as p\nimport sys\n'
        'sys.modules["fixture_dep.virtual"]=p.namespace\n'
        'sys.modules["fixture_dep.cache_name"]=p.nested.actual_attribute\n'
        'import fixture_dep.virtual\nreturn {"answer":p.namespace.answer()}')
    result,_=dependency_fixture(tmp_path, body, mutate=fixture_profile)
    assert result.returncode==0, result.stderr
    receipt=json.loads(result.stdout)
    assert receipt['entry_result']=={'answer':47}
    assert {v['name'] for v in receipt['dependencies']['exported_modules']}=={
        'fixture_dep.virtual','fixture_dep.cache_name'}
    assert receipt['dependencies_qualified'] is receipt['collection_authorized'] is False


@pytest.mark.parametrize('change', ['object','edge','class','code','missing','metadata','unknown','unprepared'])
def test_export_declarations_never_allow_wrong_objects_or_later_drift(tmp_path, change):
    actions={
        'object':'sys.modules["fixture_dep.virtual"]=types.ModuleType("fixture_dep.virtual")',
        'edge':'p.namespace=types.ModuleType("fixture_dep.virtual")',
        'class':'p.namespace.__class__=types.ModuleType',
        'code':'p.Namespace.answer.__code__=(lambda _: 99).__code__',
        'missing':'del sys.modules["fixture_dep.virtual"]',
        'metadata':'types.ModuleType.__dict__["__dict__"].__get__(p.namespace)["__file__"]="foreign"',
        'unknown':'sys.modules["fixture_dep.unknown"]=types.ModuleType("fixture_dep.unknown")',
        'unprepared':'sys.modules["fixture_dep.virtual"]=types.ModuleType("fixture_dep.virtual")'}
    prefix=('import sys,types\n' if change=='unprepared' else
        'import fixture_dep.producer as p\nimport sys,types\n'
        'sys.modules["fixture_dep.virtual"]=p.namespace\n'
        'admission.recheck()\n')
    result,_=dependency_fixture(tmp_path,prefix+actions[change]+'\nreturn {}',mutate=fixture_profile)
    assert result.returncode!=0 and result.stdout==''
    assert 'HOOK' not in result.stderr
    assert ('dependency' in result.stderr.lower() or 'Unregistered module cache entry' in result.stderr), result.stderr


@pytest.mark.parametrize('kind', ['replace','reclassify'])
def test_explicit_module_transition_uses_original_producer_class(tmp_path, kind):
    def mutate(deps,root):
        profile=upgrade(deps)
        code=('import sys,types\nclass Wrapper(types.ModuleType):\n'
              '    def answer(self): return 51\n')
        code+=('sys.modules[__name__]=Wrapper(__name__)\n' if kind=='replace' else
               'sys.modules[__name__].__class__=Wrapper\n')
        # Replacement before nested import is the real backends pattern.
        code+='import fixture_dep.child\n'
        add_source(deps,root,'fixture_dep.wrapper',code)
        add_source(deps,root,'fixture_dep.child','value=1\n')
        profile['module_changes']=[{'name':'fixture_dep.wrapper','kind':kind,
            'class_binding':direct('fixture_dep.wrapper','Wrapper')}]
    result,_=dependency_fixture(tmp_path,'import fixture_dep.wrapper as w\nreturn {"answer":w.answer()}',mutate=mutate)
    assert result.returncode==0, result.stderr
    assert json.loads(result.stdout)['entry_result']=={'answer':51}


def generated_profile(deps,root):
    profile=upgrade(deps)
    add_source(deps,root,'fixture_dep.factory',
        'import types\nclass ConfigModule(types.ModuleType): pass\n'
        'def install(module):\n'
        '    class Instance(ConfigModule):\n'
        '        def answer(self): return 53\n'
        '    module.__class__=Instance\n')
    for name in ('one','two'):
        add_source(deps,root,'fixture_dep.'+name,
            'import sys\nfrom fixture_dep.factory import install\ninstall(sys.modules[__name__])\n')
        profile['module_changes'].append({'name':'fixture_dep.'+name,'kind':'reclassify',
            'class_binding':{'kind':'factory','producer':'fixture_dep.factory','attributes':['install'],
                'nested':'Instance','bases':[direct('fixture_dep.factory','ConfigModule')]}})
    return profile


def test_generated_classes_bind_each_invocation_to_held_factory_code_and_base(tmp_path):
    body=('import fixture_dep.one as a,fixture_dep.two as b\n'
          'return {"distinct":type(a) is not type(b),"answer":a.answer()+b.answer()}')
    result,_=dependency_fixture(tmp_path,body,mutate=generated_profile)
    assert result.returncode==0, result.stderr
    assert json.loads(result.stdout)['entry_result']=={'distinct':True,'answer':106}


@pytest.mark.parametrize('defect',['extra','wildcard','duplicate','unknown-producer','phase','class-producer',
                                  'class-path','module-overlap','native-python','bound','factory-nested'])
def test_malformed_profiles_fail_before_dependency_body(tmp_path, defect):
    def mutate(deps,root):
        p=fixture_profile(deps,root)
        if defect=='extra':p['extra']=True
        elif defect=='wildcard':p['exports'][0]['name']='fixture_dep.*'
        elif defect=='duplicate':p['exports'].append(dict(p['exports'][0]))
        elif defect=='unknown-producer':p['exports'][0]['producer']='absent'
        elif defect=='phase':p['exports'][0]['phase']='native_create'
        elif defect=='class-producer':p['exports'][0]['class_binding']['producer']='absent'
        elif defect=='class-path':p['exports'][0]['attributes']=['__dict__','namespace']
        elif defect=='module-overlap':p['exports'][0]['name']='fixture_dep'
        elif defect=='native-python':p['native_origins']=[{'name':'fixture_dep','policy':'held-directory-observed-v1'}]
        elif defect=='bound':p['exports']=[dict(p['exports'][0],name='fixture_dep.v'+str(i)) for i in range(1025)]
        else:
            p=generated_profile(deps,root);p['module_changes'][0]['class_binding']['nested']='../bad'
    result,_=dependency_fixture(tmp_path,'raise AssertionError("ENTRY_RAN")',mutate=mutate)
    assert result.returncode!=0 and result.stdout==''
    assert 'ENTRY_RAN' not in result.stderr
    assert 'profile' in result.stderr.lower() or 'binding' in result.stderr.lower(), result.stderr


def test_explicit_origin_policy_works_in_complete_worker_without_changing_v1(tmp_path):
    def mutate(deps,root):
        p=upgrade(deps)
        p['native_origins']=[{'name':'fixture_dep._native','policy':'held-directory-observed-v1'}]
    result,_=dependency_fixture(tmp_path,'from fixture_dep import _native\nreturn {"answer":_native.answer()}',
                                native=True,native_link='held-relative',mutate=mutate)
    assert result.returncode==0, result.stderr
    receipt=json.loads(result.stdout)
    assert receipt['entry_result']=={'answer':47}
    assert receipt['dependencies']['native_origin_policies']=={
        'fixture_dep._native':'held-directory-observed-v1'}
    assert receipt['native_authorized'] is receipt['dependencies_qualified'] is False
