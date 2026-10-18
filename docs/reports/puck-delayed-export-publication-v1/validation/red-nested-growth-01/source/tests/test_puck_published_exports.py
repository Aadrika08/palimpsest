"""Delayed export publication through fresh authored Python workers only."""
import importlib.machinery
import json

import pytest

from test_puck_dependency_profile import add_source, upgrade
from test_puck_worker_bootstrap import descriptor
from test_puck_worker_dependencies import dependency_fixture


NAME='fixture_dep.published_child'
PRODUCER='fixture_dep.producer'
PHASE='module_exec_publish'
BODY='import fixture_dep.producer as producer\nimport sys\nreturn {"answer":sys.modules["'+NAME+'"].answer()}'
PREFIX=('import sys,types\n'
    'def __getattr__(name): raise AssertionError("OWNER_HOOK_RAN")\n'
    'def answer(): return 47\n'
    'child=types.ModuleType("'+NAME+'")\n'
    'child.answer=answer\n')
PUBLISH='sys.modules["'+NAME+'"]=child\n'
GUARD_ONE='import fixture_dep.helper_one\n'
GUARD_TWO='import fixture_dep.helper_two\n'


def row(delegates=None):
    return dict(name=NAME,producer=PRODUCER,phase=PHASE,attributes=['child'],
        class_binding=None,delegate_attributes=['answer'] if delegates is None else delegates)


def run(tmp_path,*,producer=None,body=BODY,delegates=None,defect=None,first_helper='value=1\n'):
    """No native loader or ambient package is used by these fixtures."""
    def mutate(deps,root):
        profile=upgrade(deps)
        profile.update(kind='puck-producer-import-profile-v2',version=2,native_cache=[])
        profile['exports']=[row(delegates)]
        deps.update(kind='puck-worker-dependencies-v3',version=3,
            native_identity='tmpfs-raw-dev-inode-v1')
        add_source(deps,root,PRODUCER,PREFIX+PUBLISH+GUARD_ONE if producer is None else producer)
        add_source(deps,root,'fixture_dep.helper_one',first_helper)
        add_source(deps,root,'fixture_dep.helper_two','value=2\n')
        declaration=profile['exports'][0]
        if defect=='ordinary-phase':
            declaration['phase']='module_exec';declaration.pop('delegate_attributes')
        elif defect=='dependency-v2':
            deps.update(kind='puck-worker-dependencies-v2',version=2);deps.pop('native_identity')
        elif defect=='legacy-profile':
            for key in ('kind','version','native_cache'):profile.pop(key)
        elif defect=='extension-producer':
            relative='fixture_dep/inert_native'+importlib.machinery.EXTENSION_SUFFIXES[0]
            path=root/relative;path.write_bytes(b'INERT: schema must refuse before any native loader')
            deps['roots'][0]['files'].append(descriptor(path,relative))
            deps['modules'].append(dict(name='fixture_dep.inert_native',root_index=0,path=relative,
                kind='extension',is_package=False))
            declaration['producer']='fixture_dep.inert_native'
        elif defect=='class-binding':
            declaration['class_binding']=dict(kind='direct',producer=PRODUCER,attributes=['SomeClass'])
        elif defect=='delegates-missing':declaration.pop('delegate_attributes')
        elif defect=='delegates-duplicate':declaration['delegate_attributes']=['answer','answer']
        elif defect=='delegates-unsorted':declaration['delegate_attributes']=['late','answer']
        elif defect=='delegates-overflow':declaration['delegate_attributes']=['key'+str(i).zfill(4) for i in range(4097)]
        elif defect=='preexisting':
            path=root/'fixture_dep/__init__.py'
            path.write_text(path.read_text()+'import sys,types\npreexisting=types.ModuleType("'+NAME+'")\n'
                'preexisting.answer=lambda:47\nsys.modules["'+NAME+'"]=preexisting\n')
            deps['roots'][0]['files']=[descriptor(path,'fixture_dep/__init__.py') if r['path']=='fixture_dep/__init__.py' else r
                for r in deps['roots'][0]['files']]
        deps['roots'][0]['files'].sort(key=lambda r:r['path'])
    result,_=dependency_fixture(tmp_path,body,mutate=mutate)
    return result


def refused(result):
    assert result.returncode!=0 and result.stdout=='',result.stdout+result.stderr
    assert 'OWNER_HOOK_RAN' not in result.stderr and 'CHILD_HOOK_RAN' not in result.stderr,result.stderr
    assert any(word in result.stderr.lower() for word in ('export','publication','published','profile','binding','cache')),result.stderr


def test_first_publication_survives_reentrant_guard_and_binds_legitimate_metadata(tmp_path):
    metadata=('import importlib.machinery\nchild.__file__=__file__\n'
        'child.__spec__=importlib.machinery.ModuleSpec("'+NAME+'",__loader__,origin=__file__)\n'
        'child.__loader__=__loader__\n')
    result=run(tmp_path,producer=PREFIX+metadata+PUBLISH+GUARD_ONE)
    assert result.returncode==0,result.stderr
    receipt=json.loads(result.stdout)
    assert receipt['entry_result']=={'answer':47}
    assert receipt['dependencies']['published_export_modules']==[
        dict(name=NAME,producer=PRODUCER,phase=PHASE,attributes=['child'],delegate_attributes=['answer'])]
    assert receipt['dependencies']['exported_modules']==[dict(name=NAME,producer=PRODUCER)]
    for value in (receipt,receipt['dependencies']):
        assert value['runtime_qualified'] is value['collection_authorized'] is value['executable'] is False
    assert receipt['native_authorized'] is receipt['dependencies_qualified'] is False


def test_declared_delegate_growth_is_captured_between_two_reentrant_guards(tmp_path):
    producer=PREFIX+PUBLISH+GUARD_ONE+'def late(): return 53\nchild.late=late\n'+GUARD_TWO
    body='import fixture_dep.producer as p\nreturn {"answer":p.child.answer(),"late":p.child.late()}'
    result=run(tmp_path,producer=producer,body=body,delegates=['answer','late'])
    assert result.returncode==0,result.stderr
    receipt=json.loads(result.stdout)
    assert receipt['entry_result']=={'answer':47,'late':53}
    assert receipt['dependencies']['published_export_modules']==[
        dict(name=NAME,producer=PRODUCER,phase=PHASE,attributes=['child'],delegate_attributes=['answer','late'])]


def test_ordinary_module_exec_export_cannot_authorize_early_cache_publication(tmp_path):
    result=run(tmp_path,defect='ordinary-phase')
    refused(result)
    assert 'Unregistered module cache entry: '+NAME in result.stderr,result.stderr


@pytest.mark.parametrize('defect',['dependency-v2','legacy-profile','extension-producer','class-binding',
    'delegates-missing','delegates-duplicate','delegates-unsorted','delegates-overflow'])
def test_publication_schema_refuses_before_entry_body(tmp_path,defect):
    result=run(tmp_path,defect=defect,body='raise AssertionError("ENTRY_BODY_RAN")')
    refused(result)
    assert 'ENTRY_BODY_RAN' not in result.stderr,result.stderr


@pytest.mark.parametrize('mutation',[
    'p.child=types.ModuleType("'+NAME+'")',
    'sys.modules["'+NAME+'"]=types.ModuleType("'+NAME+'")',
    'del sys.modules["'+NAME+'"]',
    'p.child.__name__="fixture_dep.changed"',
    'p.child.answer=lambda:99',
    'p.child.unknown=lambda:99',
    'p.child.__file__="changed-after-publication"',
])
def test_closed_publication_rejects_edge_cache_metadata_and_dispatch_drift(tmp_path,mutation):
    body='import fixture_dep.producer as p\nimport sys,types\n'+mutation+'\nreturn {}'
    refused(run(tmp_path,body=body))


def test_declared_growth_cannot_replace_a_previously_captured_delegate(tmp_path):
    producer=PREFIX+PUBLISH+GUARD_ONE+'def late(): return 53\nchild.late=late\nchild.answer=late\n'+GUARD_TWO
    refused(run(tmp_path,producer=producer,delegates=['answer','late']))


def test_first_publication_must_be_the_raw_producer_edge_object(tmp_path):
    producer=PREFIX+'foreign=types.ModuleType("'+NAME+'")\nforeign.answer=answer\n'
    producer+='sys.modules["'+NAME+'"]=foreign\n'+GUARD_ONE
    refused(run(tmp_path,producer=producer))


def test_publication_requires_plain_module_without_executing_subclass_hooks(tmp_path):
    producer=('import sys,types\nclass Child(types.ModuleType):\n'
        ' def __getattribute__(self,name): raise AssertionError("CHILD_HOOK_RAN")\n'
        'def answer(): return 47\nchild=Child("'+NAME+'")\nchild.answer=answer\n')+PUBLISH+GUARD_ONE
    refused(run(tmp_path,producer=producer))


def test_published_child_cannot_claim_a_package_search_path(tmp_path):
    refused(run(tmp_path,producer=PREFIX+'child.__path__=[]\n'+PUBLISH+GUARD_ONE))


def test_child_published_inside_a_nested_initializer_has_the_wrong_creator_phase(tmp_path):
    helper=('import sys\nowner=sys.modules["'+PRODUCER+'"]\n'
        'sys.modules["'+NAME+'"]=owner.child\n'+GUARD_TWO)
    refused(run(tmp_path,producer=PREFIX+GUARD_ONE,first_helper=helper))


def test_nested_initializer_cannot_supply_the_publishers_late_dispatch(tmp_path):
    helper=('import sys\nowner=sys.modules["'+PRODUCER+'"]\n'
        'def late(): return 53\nowner.child.late=late\n'+GUARD_TWO)
    refused(run(tmp_path,delegates=['answer','late'],first_helper=helper))


def test_module_created_by_an_earlier_initializer_is_preexisting(tmp_path):
    refused(run(tmp_path,defect='preexisting'))


def test_terminal_receipt_requires_the_declared_creator_to_run_and_close(tmp_path):
    refused(run(tmp_path,body='return {}'))


def test_creator_cannot_close_without_publishing_its_required_cache_entry(tmp_path):
    refused(run(tmp_path,producer=PREFIX+GUARD_ONE))


def test_creator_close_requires_the_complete_declared_delegate_set(tmp_path):
    refused(run(tmp_path,delegates=['answer','late']))
