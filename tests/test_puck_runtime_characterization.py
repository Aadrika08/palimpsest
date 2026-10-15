"""Author-created cache/proxy and fresh-worker fixtures; no numerical imports."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import types

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
        if name=='torch':body+='import sys,types\nops=types.ModuleType("torch.ops")\nsys.modules["torch.ops"]=ops\n'
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
