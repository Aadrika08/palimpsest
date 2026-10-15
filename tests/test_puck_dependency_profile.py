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


@pytest.mark.parametrize('phase,success',[('native_create',True),('module_exec',False)])
def test_native_export_is_bound_before_create_module_guard(tmp_path,phase,success):
    import subprocess,sysconfig
    from test_puck_worker_bootstrap import descriptor
    def mutate(deps,root):
        p=upgrade(deps)
        c=root/'native.c'
        source=c.read_text().replace('return PyModule_Create(&mod);',
            'PyObject* m=PyModule_Create(&mod);'
            'PyObject* child=PyModule_New("fixture_dep.native_child");'
            'if(!m || !child) return NULL;'
            'if(PyDict_SetItemString(PyImport_GetModuleDict(),"fixture_dep.native_child",child)<0) return NULL;'
            'if(PyModule_AddObject(m,"actual_export",child)<0) return NULL;return m;')
        c.write_text(source)
        native=next(v for v in deps['modules'] if v['kind']=='extension')
        subprocess.run(['cc','-shared','-fPIC','-I'+sysconfig.get_paths()['include'],str(c),
                        '-o',str(root/native['path'])],check=True,capture_output=True,timeout=15)
        deps['roots'][0]['files']=[descriptor(root/v['path'],v['path']) for v in deps['roots'][0]['files']]
        p['exports']=[{'name':'fixture_dep.native_child','producer':'fixture_dep._native','phase':phase,
                      'attributes':['actual_export'],'class_binding':None}]
    result,_=dependency_fixture(tmp_path,'from fixture_dep import _native\nimport fixture_dep.native_child\nreturn {}',
                                native=True,mutate=mutate)
    if success:
        assert result.returncode==0,result.stderr
        assert json.loads(result.stdout)['dependencies']['exported_modules']==[
            {'name':'fixture_dep.native_child','producer':'fixture_dep._native'}]
    else:
        assert result.returncode!=0 and result.stdout==''
        assert 'Unregistered module cache entry: fixture_dep.native_child' in result.stderr,result.stderr


@pytest.mark.parametrize('target',['factory','method'])
def test_equal_but_unheld_generated_code_is_refused_before_capture(tmp_path,target):
    def mutate(deps,root):
        generated_profile(deps,root)
        path=root/'fixture_dep/one.py'
        code=path.read_text()
        if target=='factory':code=code.replace('install(sys.modules[__name__])',
            'install.__code__=install.__code__.replace()\ninstall(sys.modules[__name__])')
        else:code+='type(sys.modules[__name__]).answer.__code__=type(sys.modules[__name__]).answer.__code__.replace()\n'
        path.write_text(code)
        deps['roots'][0]['files']=[descriptor(root/v['path'],v['path']) for v in deps['roots'][0]['files']]
    result,_=dependency_fixture(tmp_path,'import fixture_dep.one\nreturn {}',mutate=mutate)
    assert result.returncode!=0 and result.stdout==''
    assert 'held' in result.stderr.lower() and ('factory' in result.stderr or 'methods' in result.stderr),result.stderr


def test_original_v1_physical_spec_name_contract_is_preserved(tmp_path):
    def mutate(deps,root):
        path=root/'fixture_dep/__init__.py'
        path.write_text(path.read_text()+'__spec__.name="foreign"\n')
        deps['roots'][0]['files']=[descriptor(root/v['path'],v['path']) for v in deps['roots'][0]['files']]
    result,_=dependency_fixture(tmp_path,'import fixture_dep\nreturn {}',mutate=mutate)
    assert result.returncode!=0 and result.stdout==''
    assert 'dependency' in result.stderr.lower() and 'spec' in result.stderr.lower(),result.stderr


@pytest.mark.parametrize('target',['ExportBindings.recheck','validate_profile'])
def test_support_dispatch_is_checked_before_new_profile_callbacks(tmp_path,target):
    body=('import fixture_dep\nimport palimpsest.puck_dependency_bindings as b\n'
          'b.'+target+' = lambda *args: set()\nreturn {}')
    result,_=dependency_fixture(tmp_path,body,mutate=lambda deps,root:upgrade(deps))
    assert result.returncode!=0 and result.stdout==''
    assert 'Authenticated function code binding changed' in result.stderr or 'Authenticated class binding changed' in result.stderr,result.stderr


@pytest.mark.parametrize('policy',['exact-file-fd-v1','held-directory-observed-v1'])
def test_new_origin_policy_does_not_allow_unregistered_native_helpers(tmp_path,policy):
    def mutate(deps,root):
        p=upgrade(deps);p['native_origins']=[{'name':'fixture_dep._native','policy':policy}]
    result,_=dependency_fixture(tmp_path,'from fixture_dep import _native\nreturn {}',
                                native=True,native_link='unregistered-absolute',mutate=mutate)
    assert result.returncode!=0 and result.stdout==''
    assert 'Unregistered native file image:' in result.stderr and 'libfixturehelper.so' in result.stderr,result.stderr


def test_candidate_covers_all_observed_exceptional_rows_without_runtime_authority():
    import hashlib
    from test_puck_worker_bootstrap import ROOT
    from palimpsest.puck_dependency_bindings import validate_profile
    candidate=json.loads((ROOT/'docs/plans/puck-v3-observed-import-profile-candidate.json').read_text())
    summary=json.loads((ROOT/'docs/reports/puck-v3-runtime-amendment-02/compatibility-observations.json').read_text())
    report=(ROOT/'docs/reports/puck-v3-runtime-amendment-02/observation-02/payload/imports.json').read_bytes()
    assert candidate['observation_report_sha256']==hashlib.sha256(report).hexdigest()==summary['report_sha256']
    profile=candidate['import_profile']
    declared={v['name'] for v in profile['exports']+profile['module_changes']}
    assert declared=={v['name'] for v in summary['numerical_exceptional_bindings']}
    assert len(declared)==52 and len(profile['exports'])==42 and len(profile['module_changes'])==10
    class_bound={v['name'] for v in profile['exports'] if v['class_binding'] is not None}
    class_bound.update(v['name'] for v in profile['module_changes'])
    assert class_bound==set(summary['numerical_module_subclasses'])
    # Schema validation uses authored declarations, not payload opens or imports.
    required={v['producer'] for v in profile['exports']}
    required.update(v['name'] for v in profile['module_changes']+profile['native_origins'])
    for row in profile['exports']+profile['module_changes']:
        binding=row['class_binding']
        if binding:
            required.add(binding['producer'])
            required.update(v['producer'] for v in binding.get('bases',[]))
    extension={v['name'] for v in profile['native_origins']}|{'torch._C'}
    validate_profile(profile,[{'name':name,'kind':'extension' if name in extension else 'python'}
                              for name in sorted(required)],[])
    assert all(candidate[k] is False for k in ('native_phase_qualified','held_runtime_qualified','collection_authorized','executable'))
    assert candidate['qualification_claims']==[]


@pytest.mark.parametrize('field',['module_loader','spec_loader'])
def test_loader_identity_cannot_be_replaced_by_equal_comparing_object(tmp_path,field):
    target='fixture_dep.__loader__' if field=='module_loader' else 'fixture_dep.__spec__.loader'
    body=('import fixture_dep\n'
          'class EqualLoader:\n    def __eq__(self,other): return True\n'
          +target+'=EqualLoader()\nreturn {}')
    result,_=dependency_fixture(tmp_path,body)
    assert result.returncode!=0 and result.stdout==''
    assert 'Held dependency module dispatch changed' in result.stderr,result.stderr



def proxy_profile(deps,root):
    profile=upgrade(deps)
    add_source(deps,root,'fixture_dep.wrapper',
        'import sys,types\n'
        'class Wrapper(types.ModuleType):\n'
        '    def __init__(self,name,delegate):\n'
        '        super().__init__(name)\n'
        '        self.delegate=delegate\n'
        '    def answer(self): return self.delegate.value\n'
        'value=51\noriginal=sys.modules[__name__]\n'
        'sys.modules[__name__]=Wrapper(__name__,original)\n')
    profile['module_changes']=[{'name':'fixture_dep.wrapper','kind':'replace',
                               'class_binding':direct('fixture_dep.wrapper','Wrapper')}]


def test_review_retained_original_metadata_is_bound_after_replacement(tmp_path):
    result,_=dependency_fixture(tmp_path,'import fixture_dep.wrapper as w\n'
        'w.delegate.__spec__.name="foreign"\nreturn {"answer":w.answer()}',mutate=proxy_profile)
    assert result.returncode!=0 and result.stdout==''
    assert 'dependency' in result.stderr.lower() and ('spec' in result.stderr or 'dispatch' in result.stderr),result.stderr


def test_review_proxy_delegate_cannot_switch_to_unrelated_module(tmp_path):
    result,_=dependency_fixture(tmp_path,'import fixture_dep.wrapper as w\nimport types\n'
        'w.delegate=types.ModuleType("foreign")\nw.delegate.value=99\nreturn {"answer":w.answer()}',
        mutate=proxy_profile)
    assert result.returncode!=0 and result.stdout==''
    assert 'dependency' in result.stderr.lower() and 'delegate' in result.stderr.lower(),result.stderr


def test_review_instance_shadow_cannot_authorize_foreign_export(tmp_path):
    body=('import fixture_dep.producer as p\nimport sys,types\n'
          'sys.modules["fixture_dep.virtual"]=p.namespace\nadmission.recheck()\n'
          'admission._dependencies.bindings.recheck=lambda: {"fixture_dep.virtual"}\n'
          'sys.modules["fixture_dep.virtual"]=types.ModuleType("foreign")\nreturn {}')
    result,_=dependency_fixture(tmp_path,body,mutate=fixture_profile)
    assert result.returncode!=0 and result.stdout==''
    assert 'dispatch' in result.stderr.lower(),result.stderr


@pytest.mark.parametrize('receiver',['imports','module_seal','class_seal'])
def test_review_other_helper_receivers_cannot_shadow_recheck(tmp_path,receiver):
    prefix=('import fixture_dep.producer as p\nimport sys\n'
            'sys.modules["fixture_dep.virtual"]=p.namespace\nadmission.recheck()\n')
    target={'imports':'admission._dependencies',
            'module_seal':'admission._dependencies.bindings.prepared["fixture_dep.virtual"][1]',
            'class_seal':'admission._dependencies.bindings.class_seals[0]'}[receiver]
    body=prefix+target+'.recheck=lambda *args: {"fixture_dep.virtual"}\nreturn {}'
    result,_=dependency_fixture(tmp_path,body,mutate=fixture_profile)
    assert result.returncode!=0 and result.stdout==''
    assert 'dispatch' in result.stderr.lower(),result.stderr
