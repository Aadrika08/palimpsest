"""Author-created cache/proxy and fresh-worker fixtures; no numerical imports."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest

ROOT=Path(__file__).absolute().parents[1]
SCRIPT=ROOT/'scripts/characterize_puck_runtime_imports.py'


def api():
    assert SCRIPT.is_file(), 'Bounded runtime characterization missing'
    spec=importlib.util.spec_from_file_location('characterize_fixture',SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def test_proxy_metadata_never_calls_framework_getattr():
    module=api()
    class Proxy(types.ModuleType):
        def __getattr__(self,name):raise AssertionError('Inspection created a virtual namespace: '+name)
    proxy=Proxy('fixture.ops');producer=types.ModuleType('fixture');producer.ops=proxy
    result=module.describe_cache({'fixture':producer,'fixture.ops':proxy})
    row=next(row for row in result['modules'] if row['name']=='fixture.ops')
    assert row['spec_name'] is None and row['file'] is None
    assert row['classification']=='virtual'
    assert row['exports']==[{'producer':'fixture','attribute':'ops'}]


def test_alias_keeps_cache_name_and_canonical_spec_distinct():
    module=api();value=types.ModuleType('fixture.real')
    value.__file__='/authored/real.py'
    value.__spec__=importlib.util.spec_from_loader('fixture.real',None,origin=value.__file__)
    result=module.describe_cache({'fixture.real':value,'fixture.alias':value})
    row=next(row for row in result['modules'] if row['name']=='fixture.alias')
    assert row['classification']=='alias' and row['spec_name']=='fixture.real'
    assert row['same_object_cache_names']==['fixture.alias','fixture.real']


def test_cache_bound_refuses_before_unbounded_inspection():
    module=api()
    try:module.describe_cache({f'fixture{i}':None for i in range(8193)})
    except ValueError as error:assert 'cache' in str(error)
    else:raise AssertionError('Unbounded cache accepted')


def launch(tmp_path,*,defect=None):
    module=api();site=tmp_path/'site';site.mkdir()
    for name,version in [('numpy','2.2.5'),('torch','2.9.0+fixture'),('mujoco','3.3.6')]:
        directory=site/name;directory.mkdir()
        body='__version__='+repr(version)+'\n'
        if name=='torch':
            body+='import sys,types\nops=types.ModuleType("torch.ops")\nsys.modules["torch.ops"]=ops\n'
            if defect=='import':body+='raise RuntimeError("authored import failure")\n'
            if defect=='environment':body+='import os\nos.environ["UNREGISTERED"]="changed"\n'
        (directory/'__init__.py').write_text(body)
    output=tmp_path/'output';output.mkdir()
    environment={'PYTHONDONTWRITEBYTECODE':'1','LC_ALL':'C.UTF-8','LANG':'C.UTF-8'}
    request={'kind':'puck-runtime-import-characterization-v1','version':1,
             'site_root':str(site),'output_root':str(output),'environment':environment}
    if defect=='schema':request['grant']=True
    payload=module.canonical(request);path=tmp_path/'request.json';path.write_bytes(payload)
    digest=module.sha(payload) if defect!='sha' else '0'*64
    result=subprocess.run([sys.executable,'-I','-B','-S',str(SCRIPT),str(path),digest],
        env=environment,capture_output=True,text=True,timeout=15,start_new_session=True)
    return result,output,request


def test_real_isolated_characterization_is_explicitly_not_runtime_qualification(tmp_path):
    result,output,request=launch(tmp_path)
    assert result.returncode==0,result.stderr
    report=json.loads((output/'imports.json').read_bytes())
    assert report['status']=='observed'
    assert report['versions']=={'numpy':'2.2.5','torch':'2.9.0+fixture','mujoco':'3.3.6'}
    assert [row['name'] for row in report['imports']]==['numpy','torch','mujoco']
    assert any(row['name']=='torch.ops' and row['exports'] for row in report['cache']['modules'])
    assert report['runtime_qualified'] is report['collection_authorized'] is report['executable'] is False
    assert report['qualification_claims']==[]
    assert len((output/'imports.json').read_bytes())<=1024**2


def test_bad_request_never_imports_numerical_packages(tmp_path):
    for defect in ('schema','sha'):
        directory=tmp_path/defect;directory.mkdir()
        result,output,_=launch(directory,defect=defect)
        assert result.returncode!=0 and result.stdout==''
        assert not (output/'imports.json').exists()


def test_failed_import_is_retained_and_does_not_advance_to_mujoco(tmp_path):
    result,output,_=launch(tmp_path,defect='import')
    assert result.returncode==1
    report=json.loads((output/'imports.json').read_bytes())
    assert report['status']=='failed'
    assert [row['name'] for row in report['imports']]==['numpy','torch']
    assert report['imports'][-1]['status']=='failed'
    assert report['error']['message']=='authored import failure'
    assert report['runtime_qualified'] is False


def test_environment_change_stops_before_next_numerical_import(tmp_path):
    result,output,_=launch(tmp_path,defect='environment')
    assert result.returncode==1
    report=json.loads((output/'imports.json').read_bytes())
    assert report['status']=='failed'
    assert report['error']['message']=='Exact environment changed during torch import'
    assert [row['name'] for row in report['imports']]==['numpy','torch']


def test_existing_report_is_never_overwritten(tmp_path):
    result,output,request=launch(tmp_path)
    assert result.returncode==0
    previous=(output/'imports.json').read_bytes()
    again=subprocess.run(result.args,env=request['environment'],capture_output=True,
                         text=True,timeout=15,start_new_session=True)
    assert again.returncode==1 and again.stdout==''
    assert 'already contains a report' in again.stderr
    assert (output/'imports.json').read_bytes()==previous


def test_module_attribute_budget_refuses_oversized_namespace():
    module=api();producer=types.ModuleType('fixture')
    producer.__dict__.update({f'edge{i}':None for i in range(262145)})
    with pytest.raises(ValueError,match='attribute edge budget'):
        module.describe_cache({'fixture':producer})


def test_map_observation_preserves_spaced_paths_and_groups_segments():
    module=api()
    raw=(b'100-200 r--p 0 08:01 42 /authored/a library.so\n'
         b'200-300 r-xp 1 08:01 42 /authored/a library.so\n'
         b'300-400 rw-p 0 00:00 0 [heap]\n')
    report=module.describe_maps(raw)
    assert report['images']==[{'device':'08:01','inode':42,
        'path':'/authored/a library.so','segments':2,'executable':True}]
    assert report['persistent_snapshot_only'] is True
    assert report['transient_anonymous_jit_closure_qualified'] is False


def test_maps_observation_refuses_byte_and_line_overflow():
    module=api()
    with pytest.raises(ValueError,match='byte budget'):
        module.describe_maps(b'x'*(4*1024**2+1))
    with pytest.raises(ValueError,match='line budget'):
        module.describe_maps(b'0-1 r--p 0 00:00 0\n'*65537)


def test_publication_refuses_oversized_report_without_creating_file(tmp_path):
    module=api()
    with pytest.raises(ValueError,match='one MiB'):
        module.publish(tmp_path,{'authored':'x'*(1024**2)})
    assert not (tmp_path/'imports.json').exists()


def test_request_refuses_oversized_or_symlinked_control_before_imports(tmp_path):
    module=api();path=tmp_path/'request.json';path.write_bytes(b'x'*65537)
    with pytest.raises(ValueError,match='bounded single-link'):
        module.request_at(path,'0'*64)
    link=tmp_path/'link.json';link.symlink_to(path)
    with pytest.raises(OSError):
        module.request_at(link,'0'*64)


def test_frozen_parent_runs_one_authored_child_and_refuses_reentry(tmp_path):
    import hashlib
    import shutil
    capsule=ROOT/'docs/reports/puck-v3-runtime-interop/characterization-parent.py'
    assert capsule.is_file(), 'Frozen bounded parent capsule missing'
    root=tmp_path/'authored';root.mkdir()
    paths=['scripts/characterize_puck_runtime_imports.py',
           'src/palimpsest/bounded_qualification.py',
           'src/palimpsest/evaluate.py', 'src/palimpsest/__init__.py',
           'docs/reports/puck-v3-runtime-interop/characterization-parent.py']
    sources=[]
    for name in paths:
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
        sources.append({'path':name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
    site=tmp_path/'site';site.mkdir()
    for name in ['numpy','torch','mujoco']:
        directory=site/name;directory.mkdir()
        (directory/'__init__.py').write_text('__version__="authored"\n')
    environment={'PYTHONDONTWRITEBYTECODE':'1','LC_ALL':'C.UTF-8','LANG':'C.UTF-8'}
    output=root/'runs/puck-runtime-import-characterization-01'
    request={'kind':'puck-runtime-import-characterization-v1','version':1,
             'site_root':str(site),'output_root':str(output/'payload'),'environment':environment}
    with open('/proc/self/exe','rb') as handle:
        interpreter_sha=hashlib.file_digest(handle,'sha256').hexdigest()
    freeze={'kind':'puck-runtime-import-characterization-freeze-v1','version':1,
            'root':str(root),'request':request,'sources':sources,
            'interpreter_sha256':interpreter_sha,
            'limits':{'normal_seconds':60,'hard_seconds':70,'rss_bytes':1073741824,
                      'output_bytes':67108864,'min_free_bytes':1073741824,'max_processes':1}}
    raw=api().canonical(freeze);path=tmp_path/'freeze.json';path.write_bytes(raw)
    command=[sys.executable,'-I','-B','-S',str(root/paths[-1]),str(path),
             hashlib.sha256(raw).hexdigest()]
    child=subprocess.run(command,capture_output=True,text=True,timeout=15,start_new_session=True)
    assert child.returncode==0,child.stderr
    supervision=json.loads((output/'supervision.json').read_bytes())
    assert supervision['status']=='completed' and supervision['returncode']==0
    assert supervision['matching_survivors']==[]
    assert supervision['runtime_qualified'] is supervision['collection_authorized'] is False
    assert json.loads((output/'payload/imports.json').read_bytes())['versions']=={
        'numpy':'authored','torch':'authored','mujoco':'authored'}
    before=(output/'supervision.json').read_bytes()
    again=subprocess.run(command,capture_output=True,text=True,timeout=15,start_new_session=True)
    assert again.returncode==1
    assert (output/'supervision.json').read_bytes()==before


def test_parent_read_does_not_mistake_access_time_update_for_input_drift(tmp_path):
    import os
    capsule=ROOT/'docs/reports/puck-v3-runtime-interop/characterization-parent.py'
    spec=importlib.util.spec_from_file_location('capsule_fixture',capsule)
    parent=importlib.util.module_from_spec(spec);spec.loader.exec_module(parent)
    path=tmp_path/'unchanged';path.write_bytes(b'authored input')
    os.utime(path,ns=(0,path.stat().st_mtime_ns))
    assert parent.bounded_read(path,1024)==b'authored input'
