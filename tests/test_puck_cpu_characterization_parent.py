"""Authored-only CPU parent contracts and private namespace fixture."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/characterize_puck_cpu_runtime.py'


def api():
    assert SCRIPT.is_file(),'CPU characterization parent is missing'
    spec=importlib.util.spec_from_file_location('cpu_parent_fixture',SCRIPT)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def config(m):
    return dict(kind='puck-cpu-runtime-characterization-v1',version=1,output=m.OUTPUT,
        site_root=m.SITE,roles=dict(m.ROLES),limits=dict(m.LIMITS),environment=dict(m.ENVIRONMENT),
        expected_versions=dict(m.VERSIONS),sources=[dict(path=p) for p in m.SOURCES],inputs=[])


@pytest.mark.parametrize('defect',['authority','old-kind','versions','roles','limits','boolean-version'])
def test_fixed_cpu_configuration_refuses_drift(defect):
    m=api();value=config(m);m.validate_configuration(value)
    if defect=='authority':value['runtime_qualified']=True
    elif defect=='old-kind':value['kind']='puck-held-runtime-preparation-v1'
    elif defect=='versions':value['expected_versions']['torch']='2.9.0+cu128'
    elif defect=='roles':value['roles']['inventory']='wrong.json'
    elif defect=='limits':value['limits']['normal_seconds']=181
    else:value['version']=True
    with pytest.raises(ValueError):m.validate_configuration(value)


@pytest.mark.parametrize('defect',['partial','missing','oversized','outside','root-scope','errors'])
def test_incomplete_native_derivation_never_becomes_a_mount_set(defect):
    m=api();value=dict(kind='puck-cpu-characterization-native-metadata-v4',root_scope='installed_shared_objects_and_interpreter',errors=[],oversized_native_files=[],status='COMPLETE',required_missing_names=[],native_files=[dict(path='/usr/lib/libfixture.so',size_bytes=1,sha256='0'*64)],aliases=[])
    m.validate_native_metadata(value)
    if defect=='partial':value['status']='PARTIAL'
    elif defect=='missing':value['required_missing_names']=['missing.so']
    elif defect=='oversized':value['native_files'][0]['size_bytes']=64*1024**2+1
    elif defect=='root-scope':value['root_scope']='unassessed'
    elif defect=='errors':value['errors']=['incomplete required edge']
    else:value['native_files'][0]['path']='/home/visitor/private.so'
    with pytest.raises(ValueError):m.validate_native_metadata(value)


def test_namespace_mounts_site_readonly_and_only_selected_system_leaves(tmp_path):
    m=api();request=tmp_path/'request.json';request.write_bytes(b'{}\n')
    baseline=dict(python_prefix='/trusted/python',external_libraries=[],host_path_aliases=[])
    native=dict(native_files=[dict(path='/usr/lib/libfixture.so')],aliases=[])
    command=m.sandbox_command(baseline,native,tmp_path,request)
    assert ['--ro-bind',str(m.ROOT/m.SITE),str(m.ROOT/m.SITE)]==command[command.index(str(m.ROOT/m.SITE))-1:command.index(str(m.ROOT/m.SITE))+2]
    assert '--unshare-all' in command and '--share-net' not in command
    assert command.count('/usr/lib')==0
    assert 'pycache_prefix=/scratch/pycache' in command
    assert '--clearenv' in command and m.PYTHON in command
    assert '/usr/lib/libfixture.so' in command


def test_real_namespace_probe_and_four_authored_source_imports(tmp_path,monkeypatch):
    m=api();baseline=json.loads((ROOT/'docs/plans/puck-python-louvain-host-baseline-v1.json').read_bytes())
    site=tmp_path/'site';site.mkdir();payload=tmp_path/'payload';payload.mkdir()
    for name,version in m.VERSIONS.items():
        p=site/name;p.mkdir();(p/'__init__.py').write_text('__version__='+repr(version)+'\n')
    scripts=tmp_path/'scripts';scripts.mkdir()
    (scripts/'characterize_puck_runtime_imports.py').write_bytes((ROOT/m.WORKER).read_bytes())
    (tmp_path/'docs').mkdir()
    request=dict(kind='puck-runtime-import-characterization-v2',version=2,site_root=str(site),
        output_root='/output',environment=m.ENVIRONMENT,expected_versions=m.VERSIONS,pycache_prefix='/scratch/pycache')
    p=tmp_path/'request.json';p.write_text(json.dumps(request,sort_keys=True,separators=(',',':'))+'\n')
    monkeypatch.setattr(m,'ROOT',tmp_path);monkeypatch.setattr(m,'SITE','site')
    native=dict(native_files=[],aliases=[])
    for probe in (True,False):
        result=subprocess.run(m.sandbox_command(baseline,native,payload,p,probe=probe),capture_output=True,text=True,timeout=20)
        assert result.returncode==0,result.stderr
        if probe:assert json.loads(result.stdout)['network_isolated'] is True
    observed=json.loads((payload/'imports.json').read_bytes())
    assert observed['status']=='observed' and observed['versions']==m.VERSIONS
    assert [r['name'] for r in observed['imports']]==list(m.VERSIONS)
    assert observed['runtime_qualified'] is False and observed['native_authorized'] is False


@pytest.mark.parametrize('error_key',['error','error_type'])
def test_main_rejects_executor_record_with_late_custody_error(tmp_path,error_key):
    m=api();value=config(m);value['sources']=[]
    p=tmp_path/'configuration.json';raw=json.dumps(value).encode();p.write_bytes(raw)
    import hashlib
    code=f"""import importlib.util,json,sys
from pathlib import Path
s=importlib.util.spec_from_file_location('cpu_parent_boundary',{str(SCRIPT)!r})
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
m.ROOT=Path({str(tmp_path)!r});m.SOURCES=()
m.execute=lambda *_:dict(status='observed',**{{{error_key!r}:'authored late custody failure'}})
sys.argv=[str(m.__file__),'--configuration',{str(p)!r},'--sha256',{hashlib.sha256(raw).hexdigest()!r}]
raise SystemExit(m.main())
"""
    observed=subprocess.run([m.PYTHON,'-I','-S','-B','-c',code],capture_output=True,text=True,timeout=10,start_new_session=True)
    assert observed.returncode!=0,'an executor custody error became a normal successful return'
