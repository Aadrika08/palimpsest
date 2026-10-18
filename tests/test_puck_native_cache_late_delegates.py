"""Declared late delegates: a later native producer may extend a shared cache module.

scipy's fused Cython modules add ``fused_cython_function`` to the shared
``_cython_3_0_12`` cache module after numpy.random's creator closed it. A
cache row may declare such keys as ``late_delegates``: each key may appear only
while one of its declared producer phases is innermost, and is sealed at that
producer's close. Rows without the field keep the closed-at-creator contract.
These run the real held bootstrap over authored C extensions.
"""
import copy
import json
from pathlib import Path
import tempfile

import pytest

from test_puck_native_cache_bindings import NAME, compile_native, descriptor, native_source, profile
from test_puck_worker_dependencies import dependency_fixture

LATE=[{'attribute':'fused','producers':[{'producer':'fixture_dep._fused','phase':'module_exec'}]}]


def late_source(name='_fused',attribute='fused',after=''):
    return ('#include <Python.h>\n'
            'static PyObject* fused(PyObject* s,PyObject* a){return PyLong_FromLong(48);}\n'
            'static PyMethodDef methods[]={{"fused",fused,METH_NOARGS,NULL},{NULL,NULL,0,NULL}};\n'
            'static int populate(PyObject* m){PyObject* cache=PyDict_GetItemString(PyImport_GetModuleDict(),"'+NAME+'");'
            'if(!cache){PyErr_SetString(PyExc_RuntimeError,"shared cache module is absent");return -1;}'
            'PyObject* f=PyObject_GetAttrString(m,"fused");if(!f||PyObject_SetAttrString(cache,"'+attribute+'",f)<0)return -1;'
            'Py_DECREF(f);'+after+'return 0;}\n'
            'static PyModuleDef_Slot slots[]={{Py_mod_exec,populate},{0,NULL}};\n'
            'static struct PyModuleDef mod={PyModuleDef_HEAD_INIT,"'+name+'",NULL,0,methods,slots,NULL,NULL,NULL};\n'
            'PyMODINIT_FUNC PyInit_'+name+'(void){return PyModuleDef_Init(&mod);}\n')


def nested_source(name,body=''):
    """A plain extension imported from C by a late producer's exec, as scipy cimports cython_lapack."""
    return ('#include <Python.h>\n'
            'static int populate(PyObject* m){'+body+'return 0;}\n'
            'static PyModuleDef_Slot slots[]={{Py_mod_exec,populate},{0,NULL}};\n'
            'static struct PyModuleDef mod={PyModuleDef_HEAD_INIT,"'+name+'",NULL,0,NULL,slots,NULL,NULL,NULL};\n'
            'PyMODINIT_FUNC PyInit_'+name+'(void){return PyModuleDef_Init(&mod);}\n')


IMPORT_NESTED='PyObject* n=PyImport_ImportModule("fixture_dep._nested");if(!n)return -1;Py_DECREF(n);'


def run(body,*,late=LATE,others=(),fused=None):
    with tempfile.TemporaryDirectory(prefix='puck-native-cache-late-',dir='/tmp') as temp:
        def mutate(deps,root):
            p=profile()
            if late is not None:p['native_cache'][0]['late_delegates']=copy.deepcopy(late)
            deps.update(kind='puck-worker-dependencies-v3',version=3,native_identity='tmpfs-raw-dev-inode-v1',import_profile=p)
            compile_native(root,'_native',native_source())
            for name,source in (('_fused',fused or late_source()),*others):
                leaf=compile_native(root,name,source)
                deps['modules'].append({'name':'fixture_dep.'+name,'root_index':0,'path':leaf.relative_to(root).as_posix(),
                                        'kind':'extension','is_package':False})
            deps['roots'][0]['files']=[descriptor(path,path.relative_to(root).as_posix())
                for path in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix()) if path.is_file()]
        result,_=dependency_fixture(Path(temp),body,native=True,mutate=mutate)
        return result


def test_a_declared_later_producer_extends_the_shared_cache_and_is_sealed():
    result=run('from fixture_dep import _native\nfrom fixture_dep import _fused\nimport sys\n'
               'return {"answer":sys.modules["'+NAME+'"].answer(),"fused":sys.modules["'+NAME+'"].fused()}')
    assert result.returncode==0,result.stderr
    receipt=json.loads(result.stdout)
    assert receipt['entry_result']=={'answer':47,'fused':48}
    assert receipt['dependencies']['native_cache_modules']==[{'name':NAME,'producer':'fixture_dep._native','phase':'module_exec',
        'delegate_attributes':['answer'],'late_delegates':LATE}]


def test_a_late_producer_may_import_nested_extensions_before_it_closes():
    # The key is first seen at the nested extension's create start, with _fused's exec innermost;
    # it stays pending through the nested phases and is sealed at _fused's own close.
    result=run('from fixture_dep import _native\nfrom fixture_dep import _fused\nimport sys\n'
               'return {"fused":sys.modules["'+NAME+'"].fused(),"nested":"fixture_dep._nested" in sys.modules}',
               fused=late_source(after=IMPORT_NESTED),others=(('_nested',nested_source('_nested')),))
    assert result.returncode==0,result.stderr
    receipt=json.loads(result.stdout)
    assert receipt['entry_result']=={'fused':48,'nested':True}
    assert receipt['dependencies']['native_cache_modules'][0]['late_delegates']==LATE


def test_a_pending_late_key_cannot_be_replaced_by_a_nested_phase():
    replace=('PyObject* c=PyDict_GetItemString(PyImport_GetModuleDict(),"'+NAME+'");'
             'PyObject* d=PyDict_GetItemString(PyModule_GetDict(c),"answer");'
             'if(!d||PyObject_SetAttrString(c,"fused",d)<0)return -1;')
    result=run('from fixture_dep import _native\nfrom fixture_dep import _fused\nreturn {}',
               fused=late_source(after=IMPORT_NESTED),others=(('_nested',nested_source('_nested',replace)),))
    assert result.returncode!=0 and result.stdout==''
    assert 'Native cache late delegate changed' in result.stderr,result.stderr


def test_an_undeclared_later_key_still_poisons_the_closed_cache():
    result=run('from fixture_dep import _native\nfrom fixture_dep import _fused\nreturn {}',late=None)
    assert result.returncode!=0 and result.stdout==''
    assert 'Native cache dispatch keys differ' in result.stderr,result.stderr


def test_a_later_key_from_an_undeclared_producer_is_refused():
    late=[{'attribute':'fused','producers':[{'producer':'fixture_dep._other','phase':'module_exec'}]}]
    other=('_other',native_source(name='_other').replace('PyObject* cache=PyModule_New("'+NAME+'");','PyObject* cache=PyModule_New("'+NAME+'_unused");')
           .replace('PyDict_SetItemString(PyImport_GetModuleDict(),"'+NAME+'",cache)','PyDict_SetItemString(PyDict_New(),"'+NAME+'",cache)'))
    result=run('from fixture_dep import _native\nfrom fixture_dep import _other\nfrom fixture_dep import _fused\nreturn {}',late=late,others=(other,))
    assert result.returncode!=0 and result.stdout==''
    assert 'Native cache late delegate appeared outside its declared producer' in result.stderr,result.stderr


def test_a_declared_later_key_that_never_appears_is_incomplete():
    result=run('from fixture_dep import _native\nreturn {}')
    assert result.returncode!=0 and result.stdout==''
    assert 'Native cache terminal completion is incomplete' in result.stderr,result.stderr


def test_a_sealed_later_key_cannot_be_replaced():
    result=run('from fixture_dep import _native\nfrom fixture_dep import _fused\nimport sys\n'
               'sys.modules["'+NAME+'"].fused=lambda:0\nreturn {}')
    assert result.returncode!=0 and result.stdout==''
    assert 'Native cache late delegate changed' in result.stderr or 'Native cache dispatch' in result.stderr,result.stderr


def test_a_later_key_at_the_wrong_phase_is_refused():
    late=[{'attribute':'fused','producers':[{'producer':'fixture_dep._fused','phase':'native_create'}]}]
    result=run('from fixture_dep import _native\nfrom fixture_dep import _fused\nreturn {}',late=late)
    assert result.returncode!=0 and result.stdout==''
    assert 'Native cache late delegate appeared outside its declared producer' in result.stderr,result.stderr


@pytest.mark.parametrize('defect',['overlap','duplicate','unsorted','empty','no-producers','python-producer','unknown-producer',
    'phase','extra-field','dunder','producer-duplicate'])
def test_late_delegate_schema_is_explicit_and_finite(defect):
    from palimpsest.puck_dependency_bindings import validate_profile
    p=profile();row=p['native_cache'][0]
    row['late_delegates']=[{'attribute':'fused','producers':[{'producer':'fixture_dep._fused','phase':'module_exec'}]},
                           {'attribute':'zeta','producers':[{'producer':'fixture_dep._fused','phase':'module_exec'}]}]
    modules=[{'name':'fixture_dep._native','kind':'extension'},{'name':'fixture_dep._fused','kind':'extension'},
             {'name':'fixture_dep','kind':'python'}]
    validate_profile(copy.deepcopy(p),modules,[],allow_native_cache=True)
    late=row['late_delegates']
    if defect=='overlap':late[0]['attribute']='answer'
    elif defect=='duplicate':late[1]['attribute']='fused'
    elif defect=='unsorted':late.reverse()
    elif defect=='empty':row['late_delegates']=[]
    elif defect=='no-producers':late[0]['producers']=[]
    elif defect=='python-producer':late[0]['producers'][0]['producer']='fixture_dep'
    elif defect=='unknown-producer':late[0]['producers'][0]['producer']='absent'
    elif defect=='phase':late[0]['producers'][0]['phase']='anytime'
    elif defect=='extra-field':late[0]['allow']=True
    elif defect=='dunder':late[0]['attribute']='__dict__'
    else:late[0]['producers'].append(dict(late[0]['producers'][0]))
    with pytest.raises(ValueError):validate_profile(p,modules,[],allow_native_cache=True)
