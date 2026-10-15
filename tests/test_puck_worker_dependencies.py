"""Fresh child imports authored Python and a tiny C extension from held inputs."""
import importlib.machinery
import json
import os
from pathlib import Path
import subprocess
import sys
import sysconfig

import pytest
from test_puck_worker_bootstrap import fixture, descriptor, raw, sha, ROOT


def dependency_fixture(tmp_path, body, *, native=False, mutate=None):
    bootstrap, reg, manifest, script, script_sha = fixture(tmp_path, body)
    source = Path(reg['source_root'])
    for name in ('puck_dependency_files', 'puck_dependency_imports'):
        path = source / ('src/palimpsest/'+name+'.py')
        original = ROOT / ('src/palimpsest/'+name+'.py')
        assert original.is_file(), 'Held dependency importer missing: '+name
        path.write_bytes(original.read_bytes())
        reg['source_files'].append(descriptor(path, 'src/palimpsest/'+name+'.py'))
        reg['modules'].append({'name':'palimpsest.'+name, 'path':'src/palimpsest/'+name+'.py'})
    reg['source_files'].sort(key=lambda row:row['path'])
    package = tmp_path / 'dependency'; package.mkdir()
    (package/'fixture_dep').mkdir()
    (package/'fixture_dep/__init__.py').write_text('__version__="1.0"\nanswer=43\n')
    (package/'fixture_dep/data.txt').write_text('held resource\n')
    (package/'fixture_dep-1.0.dist-info').mkdir()
    (package/'fixture_dep-1.0.dist-info/METADATA').write_text('Metadata-Version: 2.1\nName: fixture-dep\nVersion: 1.0\n')
    modules = [{'name':'fixture_dep','root_index':0, 'path':'fixture_dep/__init__.py', 'kind':'python', 'is_package':True}]
    if native:
        c = package / 'native.c'
        c.write_text('#include <Python.h>\n'
            'static PyObject* answer(PyObject* s,PyObject* a){return PyLong_FromLong(47);}\n'
            'static PyMethodDef methods[]={{"answer",answer,METH_NOARGS,NULL},{NULL,NULL,0,NULL}};\n'
            'static struct PyModuleDef mod={PyModuleDef_HEAD_INIT,"_native",NULL,-1,methods};\n'
            'PyMODINIT_FUNC PyInit__native(void){return PyModule_Create(&mod);}\n')
        relative = 'fixture_dep/_native'+importlib.machinery.EXTENSION_SUFFIXES[0]
        subprocess.run(['cc','-shared','-fPIC','-I'+sysconfig.get_paths()['include'],str(c),'-o',str(package/relative)],
                       check=True,capture_output=True,timeout=15)
        modules.append({'name':'fixture_dep._native','root_index':0,'path':relative,'kind':'extension','is_package':False})
    files = sorted((p for p in package.rglob('*') if p.is_file()), key=lambda p:p.relative_to(package).as_posix())
    deps = {'kind':'puck-worker-dependencies-v1','version':1,
        'roots':[{'root':str(package),'kind':'package','files':[descriptor(p,p.relative_to(package).as_posix()) for p in files]}],
        'modules':modules,'namespaces':[],
        'distributions':[{'name':'fixture-dep','version':'1.0','root_index':0,'metadata_path':'fixture_dep-1.0.dist-info/METADATA'}]}
    if mutate: mutate(deps, package)
    dep_manifest = tmp_path/'dependencies.json'; payload = raw(deps); dep_manifest.write_bytes(payload)
    reg.update(kind='puck-worker-source-bootstrap-v2',version=2,
        dependencies={'path':str(dep_manifest),'size_bytes':len(payload),'sha256':sha(payload)})
    payload = raw(reg); manifest.write_bytes(payload)
    command = bootstrap.command(sys.executable,str(script),script_sha,str(manifest),sha(payload))
    return subprocess.run(command,cwd=reg['cwd'],env=reg['environment'],capture_output=True,
                          text=True,timeout=15,start_new_session=True), package


def test_python_dependency_resources_and_distribution_metadata_are_held(tmp_path):
    body = ('import fixture_dep\nimport importlib.resources,importlib.metadata\n'
        'return {"answer":fixture_dep.answer,"version":importlib.metadata.version("fixture-dep"),'
        '"resource":importlib.resources.files(fixture_dep).joinpath("data.txt").read_text()}')
    result, _ = dependency_fixture(tmp_path,body)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['entry_result'] == {'answer':43,'version':'1.0','resource':'held resource\n'}
    assert receipt['dependencies']['registration_sha256']
    assert receipt['dependencies_qualified'] is receipt['native_authorized'] is receipt['collection_authorized'] is False


def test_native_extension_initializes_from_held_file_and_is_observed(tmp_path):
    result, _ = dependency_fixture(tmp_path,'from fixture_dep import _native\nreturn {"answer":_native.answer()}',native=True)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt['entry_result'] == {'answer':47}
    assert any(row['name']=='fixture_dep._native' for row in receipt['dependencies']['loaded_modules'])
    assert receipt['dependencies']['images']['held_file_images']
    assert receipt['runtime_qualified'] is receipt['native_authorized'] is False


@pytest.mark.parametrize('defect', ['missing-module','version','extra-file','wrong-sha'])
def test_bad_dependency_admission_never_executes_entry(tmp_path,defect):
    def mutate(deps,root):
        if defect=='missing-module': deps['modules']=[]
        elif defect=='version': deps['distributions'][0]['version']='2.0'
        elif defect=='extra-file': (root/'unlisted.py').write_text('raise AssertionError("FOREIGN")')
        else: deps['roots'][0]['files'][0]['sha256']='0'*64
    result,_ = dependency_fixture(tmp_path,'import fixture_dep\nreturn {}',mutate=mutate)
    assert result.returncode != 0
    reasons = {'missing-module':'Unregistered', 'version':'Name or Version differs',
               'extra-file':'extra or missing files', 'wrong-sha':'SHA-256 or size differs'}
    assert reasons[defect] in result.stderr, result.stderr
    assert result.stdout == ''


def test_unregistered_import_has_no_ambient_fallback(tmp_path):
    result,_ = dependency_fixture(tmp_path,'import numpy\nreturn {}')
    assert result.returncode != 0
    assert 'Unregistered' in result.stderr
    assert result.stdout == ''
