"""Amended diagnostics and numbered development capsule; authored inputs only."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from test_puck_runtime_characterization import api, launch, ROOT


def test_environment_failure_retains_bounded_delta_and_partial_observations(tmp_path):
    result, output, _ = launch(tmp_path, defect='environment')
    assert result.returncode == 1
    report = json.loads((output/'imports.json').read_bytes())
    assert report['error']['message'] == 'Exact environment changed during torch import'
    assert report['environment_delta']['complete'] is True
    assert report['environment_delta']['added'] == [
        {'name':'UNREGISTERED','after_bytes':7,
         'after_sha256':hashlib.sha256(b'changed').hexdigest()}]
    assert report['environment_delta']['removed'] == report['environment_delta']['changed'] == []
    assert report['observation_scope'] == 'post_failure'
    assert any(row['name']=='torch.ops' for row in report['cache']['modules'])
    assert report['maps']['persistent_snapshot_only'] is True
    assert report['status']=='failed' and report['runtime_qualified'] is False


def test_unknown_environment_values_are_hashed_including_changed_and_removed():
    module = api()
    delta = module.environment_delta({'TOKEN':'old_secret','REMOVE':'gone_secret'},
                                    {'TOKEN':'new_secret','ADDED':'added_secret'})
    assert delta['complete'] is True
    assert delta['changed'] == [{'name':'TOKEN','before_bytes':10,'after_bytes':10,
        'before_sha256':hashlib.sha256(b'old_secret').hexdigest(),
        'after_sha256':hashlib.sha256(b'new_secret').hexdigest()}]
    assert delta['removed'][0]['name']=='REMOVE'
    assert delta['added'][0]['name']=='ADDED'
    raw=json.dumps(delta)
    for secret in ('old_secret','new_secret','gone_secret','added_secret'):
        assert secret not in raw


@pytest.mark.parametrize('after,reason', [
    ({f'name{i}':'x' for i in range(257)},'namespace_limit'),
    ({f'name{i}':'x' for i in range(129)},'change_limit'),
    ({'x'*257:'x'},'key_limit'),
    ({'fixture':'x'*4097},'value_limit'),
])
def test_environment_diagnostic_overflow_is_explicitly_incomplete(after,reason):
    report=api().environment_delta({},after)
    assert report['complete'] is False and report['reason']==reason
    assert report['after_count']==len(after)
    assert report['added']==report['changed']==report['removed']==[]


def test_secondary_cache_failure_preserves_primary_error_and_maps(tmp_path):
    result, output, _ = launch(tmp_path, defect='metadata-edge-failure')
    assert result.returncode==1
    report=json.loads((output/'imports.json').read_bytes())
    assert report['error']['message']=='Exact environment changed during torch import'
    assert report['cache'] is None and report['maps'] is not None
    assert any(row['stage']=='cache' and 'attribute edge budget' in row['message']
               for row in report['observation_errors'])
    assert report['environment_delta']['complete'] is True
    assert report['status']=='failed'


def test_report_overflow_preserves_primary_cause_and_environment_delta(tmp_path):
    result, output, _ = launch(tmp_path, defect='large-report')
    assert result.returncode==1
    raw=(output/'imports.json').read_bytes();assert len(raw)<=1024**2
    report=json.loads(raw)
    assert report['error']['message']=='Exact environment changed during torch import'
    assert report['environment_delta']['complete'] is True
    assert report['cache'] is report['maps'] is None
    assert any(row['stage']=='report' and row['observed_bytes']>1024**2
               for row in report['observation_errors'])
    assert report['status']=='failed'


def parent_case(tmp_path, *, defect=None):
    root=tmp_path/'authored';root.mkdir()
    capsule='docs/reports/puck-v3-runtime-amendment-02/characterization-parent.py'
    assert (ROOT/capsule).is_file(), 'Numbered development02 parent missing'
    paths=['scripts/characterize_puck_runtime_imports.py',
           'src/palimpsest/bounded_qualification.py','src/palimpsest/evaluate.py',
           'src/palimpsest/__init__.py',capsule]
    sources=[]
    for name in paths:
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,target)
        sources.append({'path':name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
    prior='docs/reports/puck-v3-runtime-interop/attempt-01/payload/imports.json'
    target=root/prior;target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/prior,target)
    site=tmp_path/'site';site.mkdir()
    for name in ('numpy','torch','mujoco'):
        directory=site/name;directory.mkdir()
        body='__version__="authored"\n'
        if name=='mujoco':body+='import os\nif not os.environ.get("PYOPENGL_PLATFORM"):os.environ["PYOPENGL_PLATFORM"]="egl"\n'
        (directory/'__init__.py').write_text(body)
    environment={'PYTHONDONTWRITEBYTECODE':'1','LC_ALL':'C.UTF-8','LANG':'C.UTF-8',
                 'PYOPENGL_PLATFORM':'egl'}
    if defect=='missing-egl':environment.pop('PYOPENGL_PLATFORM')
    output=root/'runs/puck-runtime-import-characterization-02'
    request={'kind':'puck-runtime-import-characterization-v1','version':1,
             'site_root':str(site),'output_root':str(output/'payload'),'environment':environment}
    with open('/proc/self/exe','rb') as handle:
        interpreter_sha=hashlib.file_digest(handle,'sha256').hexdigest()
    freeze={'kind':'puck-runtime-import-characterization-amendment-v2','version':2,
            'observation_id':2,'prior_failure':{'path':prior,
                'sha256':hashlib.sha256(target.read_bytes()).hexdigest()},
            'root':str(root),'request':request,'sources':sources,
            'interpreter_sha256':interpreter_sha,
            'limits':{'normal_seconds':60,'hard_seconds':70,'rss_bytes':1073741824,
                      'output_bytes':67108864,'min_free_bytes':1073741824,'max_processes':1}}
    if defect=='prior-sha':freeze['prior_failure']['sha256']='0'*64
    raw=api().canonical(freeze);path=tmp_path/'freeze.json';path.write_bytes(raw)
    command=[sys.executable,'-I','-B','-S',str(root/capsule),str(path),
             hashlib.sha256(raw).hexdigest()]
    child=subprocess.run(command,capture_output=True,text=True,timeout=15,start_new_session=True)
    return child,output,request,command


def test_numbered_parent_preserves_prior_failure_and_runs_once(tmp_path):
    child,output,request,command=parent_case(tmp_path)
    assert child.returncode==0,child.stderr
    result=json.loads((output/'payload/imports.json').read_bytes())
    assert result['status']=='observed' and result['environment_delta'] is None
    assert result['observation_scope']=='completed_imports'
    previous=(output/'supervision.json').read_bytes()
    assert json.loads(previous)['runtime_qualified'] is False
    again=subprocess.run(command,capture_output=True,text=True,timeout=15,start_new_session=True)
    assert again.returncode==1
    assert (output/'supervision.json').read_bytes()==previous
    old=ROOT/'docs/reports/puck-v3-runtime-interop/attempt-01/payload/imports.json'
    assert hashlib.sha256(old.read_bytes()).hexdigest()=='281330709018ec370ad84dc571e465f5e02cf4c528de1091d97d11a296082dc4'


@pytest.mark.parametrize('defect,reason',[('missing-egl','EGL environment'),('prior-sha','Prior failure SHA')])
def test_bad_amendment_never_launches_child(tmp_path,defect,reason):
    child,output,_,_=parent_case(tmp_path,defect=defect)
    assert child.returncode==1 and reason in child.stderr
    assert not output.exists()


def test_package_system_exit_zero_cannot_masquerade_as_success(tmp_path):
    result,output,_=launch(tmp_path,defect='system-exit')
    assert result.returncode==1
    report=json.loads((output/'imports.json').read_bytes())
    assert report['status']=='failed' and report['error']['type']=='builtins.SystemExit'
    assert report['observation_scope']=='post_failure'
    assert report['cache'] is not None and report['maps'] is not None


def test_environment_change_during_metadata_observation_cannot_pass(tmp_path,monkeypatch):
    import types
    module=api();environment=dict(os.environ)
    monkeypatch.setattr(sys,'path',list(sys.path))
    def imported(name):
        value=types.ModuleType(name);value.__version__='authored';return value
    monkeypatch.setattr(module,'importlib',types.SimpleNamespace(import_module=imported))
    monkeypatch.setattr(module,'describe_cache',lambda cache:{'modules':[]})
    calls=0
    def maps():
        nonlocal calls
        calls+=1
        if calls==2:monkeypatch.setenv('AUTHORED_LATE_MUTATION','changed')
        return {'images':[],'persistent_snapshot_only':True}
    monkeypatch.setattr(module,'mapped_images',maps)
    report=module.observe({'site_root':str(tmp_path),'environment':environment},'0'*64)
    assert report['status']=='failed'
    assert report['error']['message']=='Exact environment changed during observation'
    assert report['environment_delta']['added'][0]['name']=='AUTHORED_LATE_MUTATION'
