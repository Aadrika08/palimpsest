"""Global cache-only modules need one native creator, never a name allowlist."""
import copy
import importlib.machinery
import json
from pathlib import Path
import subprocess
import sysconfig
import tempfile

import pytest

from test_puck_worker_bootstrap import descriptor
from test_puck_worker_dependencies import dependency_fixture


NAME = 'native_cache_fixture'


def profile():
    return {'kind': 'puck-producer-import-profile-v2', 'version': 2,
            'exports': [], 'module_changes': [], 'native_origins': [],
            'native_cache': [{'name': NAME, 'producer': 'fixture_dep._native', 'phase': 'module_exec',
                              'delegate_attributes': ['answer']}]}


def compile_native(root, relative, source):
    c = root / (relative + '.c'); c.write_text(source)
    target = root / ('fixture_dep/' + relative + importlib.machinery.EXTENSION_SUFFIXES[0])
    subprocess.run(['cc', '-shared', '-fPIC', '-I' + sysconfig.get_paths()['include'],
                    str(c), '-o', str(target)], check=True, capture_output=True, timeout=15)
    return target


def native_source(name='_native', phase='module_exec', *, after='', child=False, wrong_type=False, extra=False):
    cache = (f'PyObject* cache=PyDict_New();' if wrong_type else
             f'PyObject* cache=PyModule_New("{NAME}");')
    cache += f'if(!cache) return -1; if(PyDict_SetItemString(PyImport_GetModuleDict(),"{NAME}",cache)<0) return -1;'
    if not wrong_type:
        cache += 'PyObject* f=PyObject_GetAttrString(m,"answer"); if(!f || PyObject_SetAttrString(cache,"answer",f)<0) return -1; Py_DECREF(f);'
    if extra:
        cache += 'PyObject* extra=PyModule_New("undeclared_cache_fixture"); if(!extra || PyDict_SetItemString(PyImport_GetModuleDict(),"undeclared_cache_fixture",extra)<0) return -1; Py_DECREF(extra);'
    if child:
        cache += 'PyObject* child=PyImport_ImportModule("fixture_dep.child"); if(!child) return -1; Py_DECREF(child);'
    cache += after + 'Py_DECREF(cache); return 0;'
    prefix = ('#include <Python.h>\n'
              'static PyObject* answer(PyObject* s,PyObject* a){return PyLong_FromLong(47);}\n'
              'static PyMethodDef methods[]={{"answer",answer,METH_NOARGS,NULL},{NULL,NULL,0,NULL}};\n'
              'static int populate(PyObject* m){' + cache + '}\n')
    if phase == 'module_exec':
        return prefix + ('static PyModuleDef_Slot slots[]={{Py_mod_exec,populate},{0,NULL}};\n'
                         f'static struct PyModuleDef mod={{PyModuleDef_HEAD_INIT,"{name}",NULL,0,methods,slots,NULL,NULL,NULL}};\n'
                         f'PyMODINIT_FUNC PyInit_{name}(void){{return PyModuleDef_Init(&mod);}}\n')
    return prefix + (f'static struct PyModuleDef mod={{PyModuleDef_HEAD_INIT,"{name}",NULL,-1,methods}};\n'
                     f'PyMODINIT_FUNC PyInit_{name}(void){{PyObject* m=PyModule_Create(&mod);if(!m)return NULL;'
                     'if(populate(m)<0){Py_DECREF(m);return NULL;}return m;}\n')


def run(body, *, phase='module_exec', declared_phase=None, defect=None, after='', child=False, delegates=None):
    with tempfile.TemporaryDirectory(prefix='puck-native-cache-', dir='/tmp') as temp:
        def mutate(deps, root):
            p = profile(); p['native_cache'][0]['phase'] = declared_phase or phase
            if delegates is not None: p['native_cache'][0]['delegate_attributes'] = delegates
            deps.update(kind='puck-worker-dependencies-v3', version=3,
                        native_identity='tmpfs-raw-dev-inode-v1', import_profile=p)
            compile_native(root, '_native', native_source(phase=phase, after=after, child=child,
                           wrong_type=defect == 'nonmodule', extra=defect == 'extra'))
            if defect == 'missing':
                source = native_source(phase=phase)
                start = source.index('static int populate('); end = source.index('\n', start)
                compile_native(root, '_native', source[:start]+'static int populate(PyObject* m){return 0;}'+source[end:])
            if child:
                path = root / 'fixture_dep/child.py'; path.write_text('value=1\n')
                deps['modules'].append({'name': 'fixture_dep.child', 'root_index': 0,
                    'path': 'fixture_dep/child.py', 'kind': 'python', 'is_package': False})
            if defect == 'preexisting':
                (root / 'fixture_dep/__init__.py').write_text('import sys,types\nsys.modules["'+NAME+'"]=types.ModuleType("'+NAME+'")\n')
            if defect in ('physical-python', 'physical-cache', 'physical-native', 'physical-directory'):
                path = {'physical-python': NAME+'.py', 'physical-cache': '__pycache__/'+NAME+'.cpython-311.pyc',
                        'physical-native': NAME+importlib.machinery.EXTENSION_SUFFIXES[0],
                        'physical-directory': NAME}[defect]
                leaf = root / path; leaf.parent.mkdir(parents=True, exist_ok=True)
                if defect == 'physical-directory': leaf.mkdir()
                else: leaf.write_bytes(b'never execute this alternative')
            deps['roots'][0]['files'] = [descriptor(path, path.relative_to(root).as_posix())
                for path in sorted(root.rglob('*'), key=lambda p:p.relative_to(root).as_posix()) if path.is_file()]
        result, _ = dependency_fixture(Path(temp), body, native=True, mutate=mutate)
        return result


@pytest.mark.parametrize('phase', ['native_create', 'module_exec'])
def test_declared_native_creation_survives_reentrant_guard_and_binds_receipt(phase):
    result = run('from fixture_dep import _native\nimport sys\nreturn {"answer":sys.modules["'+NAME+'"].answer()}',
                 phase=phase, child=True)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['entry_result'] == {'answer': 47}
    assert receipt['dependencies']['native_cache_modules'] == [
        {'name': NAME, 'producer': 'fixture_dep._native', 'phase': phase,
         'delegate_attributes': ['answer']}]
    assert receipt['dependencies']['exported_modules'] == []
    assert receipt['runtime_qualified'] is receipt['native_authorized'] is receipt['collection_authorized'] is False


@pytest.mark.parametrize('defect', ['nonmodule', 'extra', 'preexisting', 'missing'])
def test_no_unbound_names_wrong_objects_or_preexisting_cache(defect):
    result = run('from fixture_dep import _native\nreturn {}', defect=defect)
    assert result.returncode != 0 and result.stdout == ''
    assert 'Native cache' in result.stderr or 'Unregistered module cache entry: undeclared_cache_fixture' in result.stderr, result.stderr


@pytest.mark.parametrize('actual,declared', [('native_create','module_exec'), ('module_exec','native_create')])
def test_exact_native_creation_phase_is_required(actual, declared):
    result = run('from fixture_dep import _native\nreturn {}', phase=actual, declared_phase=declared, child=True)
    assert result.returncode != 0 and result.stdout == ''
    assert 'Native cache' in result.stderr, result.stderr


@pytest.mark.parametrize('mutation', [
    'sys.modules["'+NAME+'"]=types.ModuleType("'+NAME+'")',
    'del sys.modules["'+NAME+'"]',
    'sys.modules["'+NAME+'"].__name__="changed"',
    'sys.modules["'+NAME+'"].answer=lambda:99',
    'sys.modules["'+NAME+'"].new_dispatch=lambda:99',
])
def test_cache_object_metadata_and_closed_dispatch_set_cannot_change(mutation):
    result = run('from fixture_dep import _native\nimport sys,types\n'+mutation+'\nreturn {}')
    assert result.returncode != 0 and result.stdout == ''
    assert any(x in result.stderr for x in ('Native cache','Held dependency delegate binding changed','Held dependency module dispatch changed')), result.stderr


def test_creator_may_append_dispatch_before_close_but_cannot_replace_captured_dispatch():
    add = 'PyObject* f2=PyObject_GetAttrString(m,"answer"); if(!f2 || PyObject_SetAttrString(cache,"late",f2)<0)return -1; Py_DECREF(f2);'
    result = run('from fixture_dep import _native\nreturn {}', after=add, child=True, delegates=['answer','late'])
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['dependencies']['native_cache_modules'][0]['delegate_attributes'] == ['answer','late']
    replace = 'PyObject* replacement=PyModule_New("'+NAME+'"); if(!replacement || PyDict_SetItemString(PyImport_GetModuleDict(),"'+NAME+'",replacement)<0)return -1; Py_DECREF(replacement);'
    result = run('from fixture_dep import _native\nreturn {}', after=replace, child=True)
    assert result.returncode != 0 and result.stdout == ''
    assert 'Native cache' in result.stderr, result.stderr
    result = run('from fixture_dep import _native\nreturn {}',
                 after='if(PyObject_SetAttrString(cache,"answer",Py_None)<0)return -1;', child=True)
    assert result.returncode != 0 and result.stdout == ''
    assert 'Held dependency delegate binding changed' in result.stderr, result.stderr


def test_missing_or_undeclared_dispatch_key_refuses_at_creator_close():
    result = run('from fixture_dep import _native\nreturn {}', delegates=['answer','missing'])
    assert result.returncode != 0 and result.stdout == ''
    assert 'Native cache dispatch' in result.stderr, result.stderr
    result = run('from fixture_dep import _native\nreturn {}', delegates=[])
    assert result.returncode != 0 and result.stdout == ''
    assert 'Native cache dispatch' in result.stderr, result.stderr


@pytest.mark.parametrize('defect', ['physical-python','physical-cache','physical-native','physical-directory'])
def test_physical_alternatives_refuse_before_entry(defect):
    result = run('raise AssertionError("ENTRY_STARTED")', defect=defect)
    assert result.returncode != 0 and result.stdout == ''
    assert 'ENTRY_STARTED' not in result.stderr
    assert 'Absent import' in result.stderr, result.stderr


@pytest.mark.parametrize('defect', ['profile-version','extra','name','dotted','stdlib','driver',
    'python-producer','unknown-producer','phase','duplicate','physical-overlap','export-overlap'])
def test_native_cache_schema_is_explicit_and_finite(defect):
    from palimpsest.puck_dependency_bindings import validate_profile
    p = profile(); r = p['native_cache'][0]
    modules = [{'name':'fixture_dep._native','kind':'extension'}, {'name':'fixture_dep','kind':'python'}]
    if defect == 'profile-version': p['version'] = True
    elif defect == 'extra': r['allow_unknown'] = True
    elif defect == 'name': r['name'] = 'native_*'
    elif defect == 'dotted': r['name'] = 'foreign.child'
    elif defect == 'stdlib': r['name'] = 'json'
    elif defect == 'driver': r['name'] = '__mp_main__'
    elif defect == 'python-producer': r['producer'] = 'fixture_dep'
    elif defect == 'unknown-producer': r['producer'] = 'absent'
    elif defect == 'phase': r['phase'] = 'anytime'
    elif defect == 'duplicate': p['native_cache'].append(copy.deepcopy(r))
    elif defect == 'physical-overlap': modules.append({'name':NAME,'kind':'python'})
    else: p['exports'] = [{'name':NAME,'producer':'fixture_dep._native','phase':'native_create','attributes':['child'],'class_binding':None}]
    with pytest.raises(ValueError): validate_profile(p, modules, [], allow_native_cache=True)


def test_legacy_profile_contract_does_not_accept_cache_binding_extension():
    from palimpsest.puck_dependency_bindings import validate_profile
    with pytest.raises(ValueError):
        validate_profile(profile(), [{'name':'fixture_dep._native','kind':'extension'}], [])


@pytest.mark.parametrize('helper_kind', ['native', 'python'])
def test_nested_initializer_cannot_be_misattributed_to_outer_creator(helper_kind):
    with tempfile.TemporaryDirectory(prefix='puck-cache-nested-', dir='/tmp') as temp:
        def mutate(deps, root):
            deps.update(kind='puck-worker-dependencies-v3', version=3,
                native_identity='tmpfs-raw-dev-inode-v1', import_profile=profile())
            child_name = '_childnative' if helper_kind == 'native' else 'child'
            source = native_source()
            start = source.index('static int populate('); end = source.index('\n', start)
            body = 'static int populate(PyObject* m){PyObject* c=PyImport_ImportModule("fixture_dep.'+child_name+'");if(!c)return -1;Py_DECREF(c);return 0;}'
            compile_native(root, '_native', source[:start]+body+source[end:])
            if helper_kind == 'native':
                leaf = compile_native(root, child_name, native_source(name=child_name))
                kind = 'extension'
            else:
                leaf = root / 'fixture_dep/child.py'
                leaf.write_text('import sys,types\nsys.modules["'+NAME+'"]=types.ModuleType("'+NAME+'")\n')
                kind = 'python'
            deps['modules'].append({'name':'fixture_dep.'+child_name,'root_index':0,
                'path':leaf.relative_to(root).as_posix(),'kind':kind,'is_package':False})
            deps['roots'][0]['files'] = [descriptor(p,p.relative_to(root).as_posix())
                for p in sorted(root.rglob('*'),key=lambda p:p.relative_to(root).as_posix()) if p.is_file()]
        result,_ = dependency_fixture(Path(temp),'from fixture_dep import _native\nreturn {}',native=True,mutate=mutate)
        assert result.returncode != 0 and result.stdout == ''
        assert 'Native cache entry appeared outside its creator phase' in result.stderr, result.stderr


def test_cache_declaration_does_not_allow_an_import_before_creation():
    result = run('import '+NAME+'\nreturn {}')
    assert result.returncode != 0 and result.stdout == ''
    assert 'Unregistered' in result.stderr, result.stderr


def test_terminal_receipt_requires_every_declared_cache_creator_to_complete():
    result = run('return {}')
    assert result.returncode != 0 and result.stdout == ''
    assert 'Native cache terminal completion is incomplete' in result.stderr, result.stderr


def test_declared_cache_cannot_also_be_a_negative_import():
    result = run('from fixture_dep import _native\nadmission._dependencies.provider.require_absent_imports(("'+NAME+'",))\nreturn {}')
    assert result.returncode != 0 and result.stdout == ''
    assert 'Absent import overlaps a registered module' in result.stderr, result.stderr
