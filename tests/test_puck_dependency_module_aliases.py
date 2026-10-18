"""Declared module aliases: an extension registering itself under its compiled bare name.

scipy's ``scipy.sparse._csparsetools`` and ``scipy.ndimage._ni_label`` exec code
puts the module object into ``sys.modules`` under ``_csparsetools`` and
``_ni_label`` as well. A v2 profile may declare such a ``module_aliases`` row
(the bare name and its extension); the alias may appear only while that
extension's own exec is innermost, must be that very module object, is sealed
at first sight and must have appeared by terminal completion. These run the
real held bootstrap over authored C extensions.
"""
import copy
import json
from pathlib import Path
import tempfile

import pytest

from test_puck_native_cache_bindings import compile_native, descriptor, native_source, profile
from test_puck_worker_dependencies import dependency_fixture

ALIASES=[{'name':'_tools','target':'fixture_dep._tools'}]


def alias_source(name='_tools',alias='_tools',after=''):
    return ('#include <Python.h>\n'
            'static PyObject* f(PyObject* s,PyObject* a){return PyLong_FromLong(49);}\n'
            'static PyMethodDef methods[]={{"tool",f,METH_NOARGS,NULL},{NULL,NULL,0,NULL}};\n'
            'static int populate(PyObject* m){if(PyDict_SetItemString(PyImport_GetModuleDict(),"'+alias+'",m)<0)return -1;'
            +after+'return 0;}\n'
            'static PyModuleDef_Slot slots[]={{Py_mod_exec,populate},{0,NULL}};\n'
            'static struct PyModuleDef mod={PyModuleDef_HEAD_INIT,"'+name+'",NULL,0,methods,slots,NULL,NULL,NULL};\n'
            'PyMODINIT_FUNC PyInit_'+name+'(void){return PyModuleDef_Init(&mod);}\n')


def run(body,*,aliases=ALIASES,extensions=(('_tools',None),)):
    with tempfile.TemporaryDirectory(prefix='puck-module-alias-',dir='/tmp') as temp:
        def mutate(deps,root):
            p=profile()
            if aliases is not None:p['module_aliases']=copy.deepcopy(aliases)
            deps.update(kind='puck-worker-dependencies-v3',version=3,native_identity='tmpfs-raw-dev-inode-v1',import_profile=p)
            compile_native(root,'_native',native_source())
            for name,source in extensions:
                leaf=compile_native(root,name,source or alias_source(name))
                deps['modules'].append({'name':'fixture_dep.'+name,'root_index':0,'path':leaf.relative_to(root).as_posix(),
                                        'kind':'extension','is_package':False})
            deps['roots'][0]['files']=[descriptor(path,path.relative_to(root).as_posix())
                for path in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix()) if path.is_file()]
        result,_=dependency_fixture(Path(temp),body,native=True,mutate=mutate)
        return result


def test_a_declared_alias_registered_by_its_own_exec_is_sealed_and_receipted():
    result=run('from fixture_dep import _native\nfrom fixture_dep import _tools\nimport sys\n'
               'return {"same":sys.modules["_tools"] is _tools,"tool":sys.modules["_tools"].tool()}')
    assert result.returncode==0,result.stderr
    receipt=json.loads(result.stdout)
    assert receipt['entry_result']=={'same':True,'tool':49}
    assert receipt['dependencies']['module_aliases']==ALIASES


def test_an_undeclared_alias_is_an_unregistered_cache_entry():
    result=run('from fixture_dep import _native\nfrom fixture_dep import _tools\nreturn {}',aliases=None)
    assert result.returncode!=0 and result.stdout==''
    assert 'Unregistered module cache entry: _tools' in result.stderr,result.stderr


def test_an_alias_registered_by_another_extension_is_refused():
    other=alias_source('_other','_tools')
    result=run('from fixture_dep import _native\nfrom fixture_dep import _other\nfrom fixture_dep import _tools\nreturn {}',
               extensions=(('_tools',alias_source('_tools','_unused')),('_other',other)))
    assert result.returncode!=0 and result.stdout==''
    assert 'Dependency module alias appeared outside its own extension exec' in result.stderr,result.stderr


def test_a_sealed_alias_cannot_be_replaced():
    result=run('from fixture_dep import _native\nfrom fixture_dep import _tools\nimport sys,types\n'
               'sys.modules["_tools"]=types.ModuleType("_tools")\nreturn {}')
    assert result.returncode!=0 and result.stdout==''
    assert 'Dependency module alias changed or disappeared' in result.stderr,result.stderr


def test_a_declared_alias_that_never_appears_is_incomplete():
    result=run('from fixture_dep import _native\nreturn {}')
    assert result.returncode!=0 and result.stdout==''
    assert 'Dependency module alias terminal completion is incomplete' in result.stderr,result.stderr


@pytest.mark.parametrize('defect',['dotted','other-name','python-target','unknown-target','stdlib','module-overlap',
    'cache-overlap','unsorted','empty','extra-field','duplicate'])
def test_module_alias_schema_is_explicit_and_finite(defect):
    from palimpsest.puck_dependency_bindings import validate_profile
    p=profile();p['module_aliases']=[{'name':'_tools','target':'fixture_dep._tools'},{'name':'_zeta','target':'fixture_dep.sub._zeta'}]
    modules=[{'name':'fixture_dep._native','kind':'extension'},{'name':'fixture_dep._tools','kind':'extension'},
             {'name':'fixture_dep.sub._zeta','kind':'extension'},{'name':'fixture_dep','kind':'python'},
             {'name':'fixture_dep.helper','kind':'python'}]
    validate_profile(copy.deepcopy(p),modules,[],allow_native_cache=True)
    rows=p['module_aliases']
    if defect=='dotted':rows[0]['name']='a._tools'
    elif defect=='other-name':rows[0]['name']='_toolz'
    elif defect=='python-target':rows[0]={'name':'helper','target':'fixture_dep.helper'}
    elif defect=='unknown-target':rows[0]['target']='fixture_dep.absent._tools'
    elif defect=='stdlib':p['module_aliases']=[{'name':'json','target':'fixture_dep.json'}];modules.append({'name':'fixture_dep.json','kind':'extension'})
    elif defect=='module-overlap':modules.append({'name':'_tools','kind':'extension'})
    elif defect=='cache-overlap':p['native_cache'][0]['name']='_tools'
    elif defect=='unsorted':rows.reverse()
    elif defect=='empty':p['module_aliases']=[]
    elif defect=='extra-field':rows[0]['phase']='module_exec'
    else:rows[1]=dict(rows[0])
    with pytest.raises(ValueError):validate_profile(p,modules,[],allow_native_cache=True)


def test_legacy_profiles_cannot_declare_aliases():
    from palimpsest.puck_dependency_bindings import validate_profile
    legacy={'exports':[],'module_changes':[],'native_origins':[],'module_aliases':[{'name':'_tools','target':'fixture_dep._tools'}]}
    with pytest.raises(ValueError):
        validate_profile(legacy,[{'name':'fixture_dep._tools','kind':'extension'}],[],allow_native_cache=True)
