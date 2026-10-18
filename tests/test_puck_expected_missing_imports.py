"""Expected misses use authored dependency bytes and the real isolated worker."""
import json

import pytest

from test_puck_held_runtime_entry import qualify, setup
from test_puck_worker_bootstrap import descriptor
from test_puck_worker_dependencies import dependency_fixture


def policy(reg,source,names):
    qualify(reg,source)
    reg['qualification'].update(kind='puck-held-runtime-import-qualification-v2',
                                version=2,negative_imports=names)


def numpy_probe(deps,root,code):
    setup(deps,root)
    (root/'numpy/__init__.py').write_text('__version__="authored-numpy"\nimport multiprocessing\n'+code)
    deps['roots'][0]['files']=[descriptor(root/v['path'],v['path']) for v in deps['roots'][0]['files']]


@pytest.mark.parametrize('mode',['child','relative','top'])
def test_exact_declared_missing_imports_complete_the_fixed_entry(tmp_path,mode):
    name='absent_optional' if mode=='top' else 'numpy._distributor_init_local'
    code=('import importlib\ntry:\n importlib.import_module('+repr(name)+')\n'
          'except ModuleNotFoundError as error:\n'
          ' assert type(error) is ModuleNotFoundError and error.name=='+repr(name)+'\n'
          'else:\n raise AssertionError("MISSING_IMPORT_LOADED")\n')
    if mode=='relative':
        code+='try:\n from . import _distributor_init_local\nexcept ImportError:\n pass\nelse:\n raise AssertionError("RELATIVE_MISS_LOADED")\n'
    def change(reg,source):
        policy(reg,source,sorted([name,'org']))
        if mode=='top':
            ambient=tmp_path/'ambient';ambient.mkdir()
            (ambient/'absent_optional.py').write_text('raise AssertionError("AMBIENT_FALLBACK")\n')
            path=source/'src/palimpsest/puck_runtime_qualification.py'
            # Authored source changes the search path before the held entry.
            text=path.read_text().replace('def qualify(admission):',
                'def qualify(admission):\n    import sys\n    sys.path.append('+repr(str(ambient))+')')
            path.write_text(text)
            reg['source_files']=[descriptor(source/v['path'],v['path']) for v in reg['source_files']]
    result,_=dependency_fixture(tmp_path,'raise AssertionError("DEFAULT_ENTRY_RAN")',
        mutate=lambda deps,root:numpy_probe(deps,root,code),source_change=change)
    assert result.returncode==0,result.stderr
    receipt=json.loads(result.stdout)
    assert receipt['denied_imports']==sorted([name,'org'])
    assert receipt['expected_missing_imports']==sorted([name,'org'])
    assert receipt['entry_result']['status']=='imports_completed'
    assert receipt['runtime_qualified'] is receipt['collection_authorized'] is False


@pytest.mark.parametrize('names',[[],['org','org'],['org','absent_optional'],
    ['numpy.*','org'],['json.optional','org'],['palimpsest.optional','org'],
    ['__main__','org'],['_puck_held_file_bootstrap','org'],['n\u00e9gative','org'],
    ['x'*513],['org',1],None,'org', ['org','org.child'],
    ['missing_'+str(i).zfill(3) for i in range(129)]])
def test_missing_policy_refuses_invalid_or_conflicting_declarations_before_entry(tmp_path,names):
    result,_=dependency_fixture(tmp_path,'raise AssertionError("DEFAULT_ENTRY_RAN")',
        mutate=setup,source_change=lambda reg,source:policy(reg,source,names))
    assert result.returncode!=0 and result.stdout==''
    assert 'DEFAULT_ENTRY_RAN' not in result.stderr


@pytest.mark.parametrize('import_name',['numpy.optional_extra','foreign_optional'])
def test_caught_undeclared_miss_preserves_first_failure_under_new_policy(tmp_path,import_name):
    code=('import importlib\ntry:\n importlib.import_module('+repr(import_name)+')\n'
          'except ImportError:\n pass\n')
    result,_=dependency_fixture(tmp_path,'return {}',
        mutate=lambda deps,root:numpy_probe(deps,root,code),
        source_change=lambda reg,source:policy(reg,source,['numpy.optional','org']))
    assert result.returncode!=0 and result.stdout==''
    assert 'Unregistered local or external dependency import: '+import_name in result.stderr,result.stderr


def test_new_policy_refuses_an_existing_held_target_before_package_execution(tmp_path):
    result,_=dependency_fixture(tmp_path,'return {}',mutate=setup,
        source_change=lambda reg,source:policy(reg,source,['numpy','org']))
    assert result.returncode!=0 and result.stdout==''
    assert 'overlaps a registered module' in result.stderr,result.stderr


def test_legacy_qualification_descriptor_does_not_gain_extra_denials(tmp_path):
    def change(reg,source):
        qualify(reg,source);reg['qualification']['negative_imports']=['numpy.optional','org']
    result,_=dependency_fixture(tmp_path,'return {}',mutate=setup,source_change=change)
    assert result.returncode!=0 and result.stdout==''
    assert 'qualification' in result.stderr.lower(),result.stderr


def test_absence_exemption_cannot_use_a_shadowed_provider_callback(tmp_path):
    code=('import sys,importlib\n'
          'sys.meta_path[0].owner._dependencies.provider.require_absent_imports=lambda names:None\n'
          'try:\n importlib.import_module("numpy.optional")\nexcept ImportError:\n pass\n')
    result,_=dependency_fixture(tmp_path,'return {}',
        mutate=lambda deps,root:numpy_probe(deps,root,code),
        source_change=lambda reg,source:policy(reg,source,['numpy.optional','org']))
    assert result.returncode!=0 and result.stdout==''
    assert 'dispatch shadow changed' in result.stderr,result.stderr


def test_declared_miss_rechecks_the_live_namespace_after_admission(tmp_path):
    def mutate(deps,root):
        code=('import os,importlib\nos.mkdir('+repr(str(root/'numpy/optional'))+')\n'
              'try:\n importlib.import_module("numpy.optional")\nexcept ImportError:\n pass\n')
        numpy_probe(deps,root,code)
    result,_=dependency_fixture(tmp_path,'return {}',mutate=mutate,
        source_change=lambda reg,source:policy(reg,source,['numpy.optional','org']))
    assert result.returncode!=0 and result.stdout==''
    assert any(s in result.stderr for s in ('namespace changed','ancestor','directory')),result.stderr
