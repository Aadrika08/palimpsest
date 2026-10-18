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
        expected_versions=dict(m.VERSIONS),sources=[dict(path=p) for p in m.SOURCES],
        inputs=m.required_input_rows(m.read_prior_configuration()))


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


@pytest.mark.parametrize('defect',['partial','missing','oversized','outside','root-scope','errors','old-kind'])
def test_incomplete_native_derivation_never_becomes_a_mount_set(defect):
    m=api();value=dict(kind='puck-cpu-characterization-native-metadata-v5',root_scope='installed_shared_objects_and_interpreter',errors=[],oversized_native_files=[],status='COMPLETE',required_missing_names=[],native_files=[dict(path='/usr/lib/libfixture.so',size_bytes=1,sha256='0'*64)],aliases=[])
    m.validate_native_metadata(value)
    if defect=='partial':value['status']='PARTIAL'
    elif defect=='missing':value['required_missing_names']=['missing.so']
    elif defect=='oversized':value['native_files'][0]['size_bytes']=64*1024**2+1
    elif defect=='root-scope':value['root_scope']='unassessed'
    elif defect=='errors':value['errors']=['incomplete required edge']
    elif defect=='old-kind':value['kind']='puck-cpu-characterization-native-metadata-v4'
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
    prior=tmp_path/m.ROLES['prior_configuration'];prior.parent.mkdir(parents=True)
    prior.write_bytes((ROOT/m.ROLES['prior_configuration']).read_bytes())
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
    assert json.loads(observed.stdout)==dict(status='observed',**{error_key:'authored late custody failure'})


def prior_fixture(m):
    archive=ROOT/'docs/reports/puck-cpu-characterization-01'
    prior=json.loads((archive/'frozen-configuration.json').read_bytes())
    result=json.loads((archive/'raw/result.json').read_bytes())
    audit=json.loads((archive/'failure-audit-01.json').read_bytes())
    pins={row['path']:row for row in m.required_input_rows(prior)}
    return prior,result,audit,pins


def test_epoch02_keeps_the_profile_and_requires_exact_prior_input_closure():
    m=api();prior,result,audit,pins=prior_fixture(m)
    assert m.OUTPUT=='runs/puck-cpu-runtime-characterization-02'
    assert m.ROLES['native_metadata']=='docs/plans/puck-cpu-characterization-native-metadata-05.json'
    assert 'docs/plans/puck-cpu-characterization-v2.md' in m.SOURCES
    assert 'docs/plans/puck-cpu-characterization-v1.md' not in m.SOURCES
    assert m.LIMITS==prior['limits'] and m.ENVIRONMENT==prior['environment']
    assert m.VERSIONS==prior['expected_versions']
    assert len(pins)==42 and len(m.SOURCES)==14 and len(m.ROLES)==12
    assert sum(p.startswith(m.ARCHIVE+'/source/') for p in pins)==16
    assert sum(p.startswith(m.PRIOR_ARCHIVE+'/source/') for p in pins)==14
    m.validate_prior_characterization(prior,result,audit,pins)


@pytest.mark.parametrize('defect',['prior-role','prior-capsule','accepted-capsule','native-pin','prior-pin','extra-input'])
def test_configuration_refuses_incomplete_or_changed_prior_input_closure(defect):
    m=api();prior,_,_,_=prior_fixture(m);value=config(m)
    value['inputs']=m.required_input_rows(prior)
    m.validate_configuration(value)
    if defect in ('prior-role','prior-capsule','accepted-capsule'):
        path=(m.ROLES['prior_result'] if defect=='prior-role' else next(row['path'] for row in value['inputs'] if row['path'].startswith((m.PRIOR_ARCHIVE if defect=='prior-capsule' else m.ARCHIVE)+'/source/')))
        value['inputs']=[row for row in value['inputs'] if row['path']!=path]
    elif defect in ('native-pin','prior-pin'):
        path=m.ROLES['native_metadata' if defect=='native-pin' else 'prior_configuration']
        next(row for row in value['inputs'] if row['path']==path)['sha256']='0'*64
    else:value['inputs'].append(dict(path='authored-extra.json',size_bytes=1,sha256='0'*64))
    with pytest.raises(ValueError,match='input closure'):m.validate_configuration(value)


@pytest.mark.parametrize('defect',['success','authority','claims','children','descriptors','nonfinite-clock','late-clock','audit-status','audit-authority','audit-hash','worker-return','worker-failure','missing-worker-failure','configuration-hash','prior-capsule','source-list'])
def test_prior_characterization_requires_the_exact_normal_failed_epoch(defect):
    m=api();prior,result,audit,pins=prior_fixture(m)
    m.validate_prior_characterization(prior,result,audit,pins)
    if defect=='success':result['status']='observed'
    elif defect=='authority':result['runtime_qualified']=True
    elif defect=='claims':result['qualification_claims']=['authored claim']
    elif defect=='children':result['closure']['active_children']=['authored child']
    elif defect=='descriptors':result['closure']['fd_count_after']+=1
    elif defect=='nonfinite-clock':result['elapsed_seconds']=float('nan')
    elif defect=='late-clock':result['elapsed_seconds']=180
    elif defect=='audit-status':audit['status']='PASS'
    elif defect=='audit-authority':audit['native_qualified']=True
    elif defect=='audit-hash':audit['verified']['parent_result_sha256']='0'*64
    elif defect=='worker-return':audit['verified']['worker_returncode']=0
    elif defect=='worker-failure':audit['verified']['worker_failure']='hard deadline'
    elif defect=='missing-worker-failure':audit['verified'].pop('worker_failure')
    elif defect=='configuration-hash':pins[m.ROLES['prior_configuration']]['sha256']='0'*64
    elif defect=='prior-capsule':next(row for path,row in pins.items() if path.startswith(m.PRIOR_ARCHIVE+'/source/'))['sha256']='0'*64
    else:prior['sources']=prior['sources'][:-1]
    with pytest.raises(ValueError):m.validate_prior_characterization(prior,result,audit,pins)


def test_prior_configuration_reader_authenticates_source_bytes(monkeypatch):
    m=api();m.read_prior_configuration()
    monkeypatch.setattr(m,'read',lambda *_:b'{}\n')
    with pytest.raises(ValueError,match='prior configuration'):m.read_prior_configuration()
