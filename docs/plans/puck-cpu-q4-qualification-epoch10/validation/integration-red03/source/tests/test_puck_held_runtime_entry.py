"""A fixed held qualification entry with authored packages only."""
import json

import pytest
from test_puck_worker_dependencies import dependency_fixture
from test_puck_worker_bootstrap import descriptor

VERSIONS={'numpy':'authored-numpy','torch':'authored-torch','mujoco':'authored-mujoco'}


def setup(deps, root, defect=None):
    for name,version in VERSIONS.items():
        directory=root/name;directory.mkdir()
        code='__version__='+repr(version)+'\n'
        if name=='numpy':code+='import multiprocessing\n'
        if name=='torch' and defect=='wrong-version':code='__version__="wrong"\n'
        if name=='torch' and defect=='bad-alias':code+='import sys,types\nsys.modules["__mp_main__"]=types.ModuleType("foreign")\n'
        if name=='mujoco' and defect=='fail':code+='raise RuntimeError("AUTHORED_IMPORT_FAILURE")\n'
        if name=='mujoco' and defect=='environment':code+='import os\nos.environ["FOREIGN"]="x"\n'
        path=directory/'__init__.py';path.write_text(code)
        deps['roots'][0]['files'].append(descriptor(path,name+'/__init__.py'))
        deps['modules'].append({'name':name,'root_index':0,'path':name+'/__init__.py','kind':'python','is_package':True})
    deps['roots'][0]['files'].sort(key=lambda row:row['path'])


def qualify(reg,source):
    reg.update(kind='puck-worker-source-bootstrap-v3',version=3,
        qualification={'kind':'puck-held-runtime-import-qualification-v1','version':1,
            'expected_versions':dict(VERSIONS),'stdlib_cache_aliases':{'__mp_main__':'__main__'},'negative_imports':['org']})


def test_fixed_entry_runs_three_held_imports_and_binds_stdlib_main_alias(tmp_path):
    result,_=dependency_fixture(tmp_path,'raise AssertionError("DEFAULT_ENTRY_RAN")',
        mutate=setup,source_change=qualify)
    assert result.returncode==0,result.stderr
    receipt=json.loads(result.stdout);entry=receipt['entry_result']
    assert entry['kind']=='puck-held-runtime-import-qualification-result-v1'
    assert entry['status']=='imports_completed'
    assert {v['name']:v['version'] for v in entry['imports']}==VERSIONS
    assert [v['name'] for v in entry['imports']]==['numpy','torch','mujoco']
    assert entry['held_imports_observed'] is True
    assert receipt['stdlib_cache_aliases']=={'__mp_main__':'__main__'}
    assert receipt['runtime_qualified'] is receipt['dependencies_qualified'] is receipt['native_authorized'] is receipt['collection_authorized'] is False
    assert entry['qualification_claims']==[]


@pytest.mark.parametrize('defect,reason',[('wrong-version','version'),('bad-alias','alias'),
    ('fail','AUTHORED_IMPORT_FAILURE'),('environment','environment/cwd')])
def test_fixed_entry_retains_no_success_when_import_or_identity_gate_fails(tmp_path,defect,reason):
    result,_=dependency_fixture(tmp_path,'raise AssertionError("DEFAULT_ENTRY_RAN")',
        mutate=lambda deps,root:setup(deps,root,defect),source_change=qualify)
    assert result.returncode!=0 and result.stdout==''
    assert reason in result.stderr and 'DEFAULT_ENTRY_RAN' not in result.stderr,result.stderr


@pytest.mark.parametrize('defect',['unknown','version-bool','expected-names','bad-alias-name','bad-alias-target','extra-entry'])
def test_qualification_descriptor_is_fixed_and_strict_before_imports(tmp_path,defect):
    def change(reg,source):
        qualify(reg,source)
        q=reg['qualification']
        if defect=='unknown':q['extra']=True
        elif defect=='version-bool':q['version']=True
        elif defect=='expected-names':q['expected_versions']['arbitrary']='no'
        elif defect=='bad-alias-name':q['stdlib_cache_aliases']={'foreign':'__main__'}
        elif defect=='bad-alias-target':q['stdlib_cache_aliases']={'__mp_main__':'foreign'}
        else:q['entry']='arbitrary.code'
    result,_=dependency_fixture(tmp_path,'raise AssertionError("DEFAULT_ENTRY_RAN")',mutate=setup,source_change=change)
    assert result.returncode!=0 and result.stdout==''
    assert 'qualification' in result.stderr.lower(),result.stderr
    assert 'DEFAULT_ENTRY_RAN' not in result.stderr


def test_v2_stays_preflight_only_and_does_not_admit_stdlib_alias_implicitly(tmp_path):
    result,_=dependency_fixture(tmp_path,'import sys\nsys.modules["__mp_main__"]=sys.modules["__main__"]\nreturn {}')
    assert result.returncode!=0 and result.stdout==''
    assert 'Unregistered module cache entry: __mp_main__' in result.stderr,result.stderr


def test_first_failure_is_preserved_when_dependency_catches_import_error(tmp_path):
    def mutate(deps,root):
        setup(deps,root)
        path=root/'numpy/__init__.py'
        path.write_text('__version__="authored-numpy"\ntry:\n import foreign_optional\nexcept ImportError:\n pass\n')
        deps['roots'][0]['files']=[descriptor(root/v['path'],v['path']) for v in deps['roots'][0]['files']]
    result,_=dependency_fixture(tmp_path,'return {}',mutate=mutate,source_change=qualify)
    assert result.returncode!=0 and result.stdout==''
    assert 'foreign_optional' in result.stderr,result.stderr
