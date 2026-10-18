"""AUTHORED: read-only host-drift checks run before any one-shot output is reserved.

Characterization-04, preparation04 and allocation 16 re-hash the v6 native
leaves (and the EGL vendor JSON and trusted baseline) from their pinned inputs
before reserving their output, so host drift never consumes an allocation. A
driver loads each real parent from the authored project, makes every native
leaf look drifted and makes output reservation raise a sentinel.
"""
import json
import os
from pathlib import Path
import secrets
import shutil

import pytest

from puck_episode_authored import (EPISODE_PARENT, PYTHON, QUALIFIER, RUN_IDS, authored_scale, canonical, characterize,
                                   derive_candidate, episode_project, load, prepare04, preparation04_inputs, run, sha, write)

DRIVER='''import hashlib,importlib.util,json,sys,time
root,script,configuration,mode=sys.argv[1:5]
sys.path[:0]=[root+'/src',root+'/scripts']
import palimpsest.puck_cpu_registration as registration
import palimpsest.bounded_qualification as bounds
registration.native_leaf_row=lambda path,deadline,maximum=None:dict(size_bytes=-1,sha256='0'*64)
def reserved(*args,**kwargs):raise RuntimeError('SENTINEL output reserved before host checks')
bounds.reserve_output=reserved
spec=importlib.util.spec_from_file_location('preflight_parent',script);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
raw=open(configuration,'rb').read();config=json.loads(raw)
try:
    if mode=='characterization':
        config['_configuration_row']=dict(path=configuration[len(root)+1:],size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        m.execute(config,hashlib.sha256(raw).hexdigest(),time.monotonic())
    else:m.execute(config,raw,time.monotonic())
    print('NO ERROR')
except BaseException as error:print(type(error).__name__+': '+str(error))
'''


def drive(root,script,configuration,mode):
    driver=root/'docs/authored/preflight-driver.py';driver.parent.mkdir(parents=True,exist_ok=True);driver.write_text(DRIVER)
    code,stdout,stderr=run([PYTHON,'-I','-S','-B',str(driver),str(root),str(root/script),str(configuration),mode],root,300)
    return stdout.decode().strip(),stderr


@pytest.fixture(scope='module')
def prepared(tmp_path_factory):
    base=tmp_path_factory.mktemp('preflight')
    assert base.resolve().is_relative_to(Path(__file__).resolve().parents[1]/'runs'),'Use persistent runs/ basetemp'
    stage=Path('/tmp')/('palimpsest-puck-cpu-held-04-authored-'+secrets.token_hex(8))
    project=episode_project(base);authored_scale(project)
    try:yield prepare04(derive_candidate(characterize(project)),stage)
    finally:
        if os.path.lexists(stage):
            for parent,directories,_ in os.walk(stage):
                for name in directories:os.chmod(os.path.join(parent,name),0o700)
            shutil.rmtree(stage)


def test_characterization04_checks_host_drift_before_reserving(tmp_path):
    project=episode_project(tmp_path);root=project['root']
    parent=load(root/'scripts/characterize_puck_cpu_episode.py','preflight_characterization')
    raw=(json.dumps(parent.configuration(parent.source_rows()),sort_keys=True,indent=2)+'\n').encode()
    configuration=root/'docs/authored/preflight-characterization.json';write(root,'docs/authored/preflight-characterization.json',raw)
    outcome,_=drive(root,'scripts/characterize_puck_cpu_episode.py',configuration,'characterization')
    assert outcome.startswith('ValueError') and 'Native' in outcome and 'SENTINEL' not in outcome,outcome
    assert not (root/'runs/puck-cpu-runtime-characterization-04').exists()


def test_preparation04_checks_host_drift_before_reserving(prepared):
    root=prepared['root'];q=prepared['qualifier'];config=dict(prepared['preparation'])
    config['stage_parent']='/tmp/palimpsest-puck-cpu-held-04-authored-'+secrets.token_hex(8)
    configuration=root/'docs/authored/preflight-prepare04.json';configuration.write_bytes(q.canonical(config))
    outcome,_=drive(root,QUALIFIER,configuration,'preparation')
    assert outcome.startswith('ValueError') and 'native' in outcome.lower() and 'SENTINEL' not in outcome,outcome
    assert not os.path.lexists(config['stage_parent'])


def test_allocation16_checks_host_drift_before_reserving(prepared):
    root=prepared['root'];parent=load(root/EPISODE_PARENT,'preflight_episode_parent');q=prepared['qualifier']
    raw=(root/EPISODE_PARENT).read_bytes()
    sources=sorted(prepared['preparation']['sources']+[dict(path=EPISODE_PARENT,size_bytes=len(raw),sha256=sha(raw))],key=lambda r:r['path'])
    config=dict(kind=parent.KIND,version=16,allocation_id=16,root=str(root),stage_parent=str(prepared['stage']),sources=sources,
        inputs=prepared['inputs'],interpreter=dict(q.INTERPRETER),environment=dict(parent.ENVIRONMENT),expected_versions=dict(parent.VERSIONS),
        limits=dict(parent.LIMITS),negative_imports=list(parent.NEGATIVE_IMPORTS),hidden_imports=list(parent.HIDDEN_IMPORTS),
        claims=dict(parent.CLAIMS),preparation_acceptance=prepared['acceptance'],run_ids=dict(RUN_IDS))
    configuration=root/'docs/authored/preflight-episode16.json';configuration.write_bytes(canonical(config))
    outcome,_=drive(root,EPISODE_PARENT,configuration,'episode')
    assert outcome.startswith('ValueError') and 'Native' in outcome and 'SENTINEL' not in outcome,outcome
    assert not (root/'runs/puck-cpu-held-episode-16').exists()
