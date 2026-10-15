"""Real preparation/qualification parents with authored package inputs only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess

import pytest
from test_puck_worker_bootstrap import ROOT, descriptor
from test_puck_held_runtime_entry import VERSIONS

SCRIPT=ROOT/'scripts/qualify_puck_held_runtime.py'


def api():
    assert SCRIPT.is_file(),'Bounded held-runtime preparation/qualification parent missing'
    spec=importlib.util.spec_from_file_location('held_parent_api',SCRIPT)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def encoded(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def sha(raw):return hashlib.sha256(raw).hexdigest()


def freeze_file(root,mode,value):
    path=root/(mode+'-freeze.json');payload=encoded(value);path.write_bytes(payload)
    return path,sha(payload)


def run(root,freeze):
    module=api();path,digest=freeze
    return subprocess.run([module.PYTHON,'-I','-B','-S',str(root/'scripts/qualify_puck_held_runtime.py'),
        str(path),digest],capture_output=True,text=True,timeout=25,start_new_session=True)


def case(tmp_path):
    module=api();root=tmp_path/'authored';root.mkdir()
    for name in module.SOURCES:
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,path)
    site=tmp_path/'site';site.mkdir()
    rows=[]
    for name,version in VERSIONS.items():
        path=site/name/'__init__.py';path.parent.mkdir()
        path.write_text('__version__='+repr(version)+'\n'+('import multiprocessing\n' if name=='numpy' else ''))
        rows.append({'name':name,'file':str(path),'spec_name':name})
    observation={'kind':'puck-runtime-import-characterization-result-v2','version':2,'status':'observed',
        'cache':{'modules':rows},'maps':{'images':[]},'baseline_maps':{'images':[]},
        'environment_sha256':sha(encoded(module.ENVIRONMENT)),
        'runtime_qualified':False,'collection_authorized':False,'executable':False,'qualification_claims':[]}
    path=root/module.OBSERVATION;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(encoded(observation))
    candidate={'kind':'puck-observed-import-profile-candidate-v1','version':1,
        'observation_report_sha256':sha(path.read_bytes()),
        'import_profile':{'exports':[],'module_changes':[],'native_origins':[]},
        'native_phase_qualified':False,'held_runtime_qualified':False,'collection_authorized':False,
        'executable':False,'qualification_claims':[],'limitations':['authored fixture']}
    candidate_path=root/module.CANDIDATE;candidate_path.parent.mkdir(parents=True,exist_ok=True)
    candidate_path.write_bytes(encoded(candidate))
    common={'version':1,'allocation_id':1,'root':str(root),
        'sources':[descriptor(root/name,name) for name in module.SOURCES],
        'interpreter':{'path':module.PYTHON,'size_bytes':21662864,
                      'sha256':'572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a'},
        'environment':dict(module.ENVIRONMENT),'expected_versions':dict(VERSIONS)}
    prepare=dict(common,kind='puck-held-runtime-preparation-v1',limits=module.PREPARATION_LIMITS,
        site_root=str(site),observation=descriptor(path,module.OBSERVATION),
        candidate=descriptor(candidate_path,module.CANDIDATE))
    return module,root,site,common,prepare


def qualify_freeze(module,root,common):
    path=root/'runs/puck-held-runtime-preparation-01/preparation.json'
    return dict(common,kind='puck-held-runtime-qualification-v1',limits=module.QUALIFICATION_LIMITS,
                preparation=descriptor(path,'runs/puck-held-runtime-preparation-01/preparation.json'))


def test_prepare_then_separately_pinned_qualification_executes_real_held_worker(tmp_path):
    module,root,site,common,prepare=case(tmp_path)
    prep=run(root,freeze_file(root,'prepare',prepare))
    assert prep.returncode==0,prep.stderr
    prepared=root/'runs/puck-held-runtime-preparation-01'
    receipt=json.loads((prepared/'preparation.json').read_bytes())
    assert receipt['status']=='prepared' and receipt['runtime_qualified'] is False
    deps=(prepared/receipt['dependencies']['path']).read_bytes()
    assert sha(deps)==receipt['dependencies']['sha256']
    assert {r['name'] for r in json.loads(deps)['modules']}==set(VERSIONS)
    q=run(root,freeze_file(root,'qualify',qualify_freeze(module,root,common)))
    assert q.returncode==0,q.stderr
    output=root/'runs/puck-held-runtime-qualification-01'
    outcome=json.loads((output/'outcome.json').read_bytes())
    assert outcome['status']=='imports_completed' and outcome['runtime_qualified'] is False
    assert outcome['collection_authorized'] is outcome['executable'] is False
    assert outcome['supervision']['matching_survivors']==[]
    worker=json.loads((output/'outer/logs/stdout.log').read_bytes())
    assert {r['name']:r['version'] for r in worker['entry_result']['imports']}==VERSIONS
    assert worker['stdlib_cache_aliases']=={'__mp_main__':'__main__'}
    assert worker['denied_imports']==['org']


@pytest.mark.parametrize('mode',['prepare','qualify'])
def test_each_allocation_marker_is_one_shot_and_preserves_original_terminal(tmp_path,mode):
    module,root,site,common,prepare=case(tmp_path)
    first_freeze=freeze_file(root,'prepare',prepare)
    first=run(root,first_freeze);assert first.returncode==0,first.stderr
    if mode=='qualify':
        first_freeze=freeze_file(root,'qualify',qualify_freeze(module,root,common))
        first=run(root,first_freeze);assert first.returncode==0,first.stderr
    output=root/('runs/puck-held-runtime-preparation-01' if mode=='prepare' else 'runs/puck-held-runtime-qualification-01')
    terminal=output/('preparation.json' if mode=='prepare' else 'outcome.json');before=terminal.read_bytes()
    again=run(root,first_freeze)
    assert again.returncode!=0 and terminal.read_bytes()==before
    assert 'exist' in again.stderr.lower(),again.stderr


@pytest.mark.parametrize('defect',['site-symlink','unknown-cache','candidate-authority','source-sha','limits','environment'])
def test_preparation_refuses_bad_admission_or_staging_without_worker(tmp_path,defect):
    module,root,site,common,prepare=case(tmp_path)
    if defect=='site-symlink':(site/'link').symlink_to(site/'numpy/__init__.py')
    elif defect=='unknown-cache':
        path=root/module.OBSERVATION;x=json.loads(path.read_bytes())
        x['cache']['modules'].append({'name':'unknown','file':None,'spec_name':None})
        path.write_bytes(encoded(x));prepare['observation']=descriptor(path,module.OBSERVATION)
        cp=root/module.CANDIDATE;c=json.loads(cp.read_bytes());c['observation_report_sha256']=sha(path.read_bytes())
        cp.write_bytes(encoded(c));prepare['candidate']=descriptor(cp,module.CANDIDATE)
    elif defect=='candidate-authority':
        path=root/module.CANDIDATE;x=json.loads(path.read_bytes());x['executable']=True
        path.write_bytes(encoded(x));prepare['candidate']=descriptor(path,module.CANDIDATE)
    elif defect=='source-sha':prepare['sources'][0]['sha256']='0'*64
    elif defect=='limits':prepare['limits']=dict(prepare['limits'],normal_seconds=181)
    else:prepare['environment']=dict(prepare['environment'],EXTRA='bad')
    result=run(root,freeze_file(root,'prepare',prepare))
    assert result.returncode!=0 and not (root/'runs/puck-held-runtime-qualification-01').exists()
    output=root/'runs/puck-held-runtime-preparation-01'
    if output.exists():
        terminal=json.loads((output/'outcome.json').read_bytes());assert terminal['status']=='failed'
        assert terminal['runtime_qualified'] is terminal['collection_authorized'] is False


@pytest.mark.parametrize('defect',['dep-drift','source-drift','version','preparation-sha'])
def test_separate_qualification_rechecks_frozen_preparation_before_or_during_worker(tmp_path,defect):
    module,root,site,common,prepare=case(tmp_path)
    result=run(root,freeze_file(root,'prepare',prepare));assert result.returncode==0,result.stderr
    q=qualify_freeze(module,root,common);prepared=root/'runs/puck-held-runtime-preparation-01'
    if defect=='dep-drift':
        receipt=json.loads((prepared/'preparation.json').read_bytes());path=prepared/receipt['dependencies']['path']
        path.write_bytes(path.read_bytes()+b' ')
    elif defect=='source-drift':
        path=prepared/'source/src/palimpsest/puck_runtime_qualification.py';path.write_text('raise AssertionError("ALTERED")\n')
    elif defect=='version':(site/'torch/__init__.py').write_text('__version__="wrong"\n')
    else:q['preparation']['sha256']='0'*64
    result=run(root,freeze_file(root,'qualify',q));assert result.returncode!=0
    output=root/'runs/puck-held-runtime-qualification-01'
    if output.exists():
        outcome=json.loads((output/'outcome.json').read_bytes());assert outcome['status']=='failed'
        assert outcome['runtime_qualified'] is outcome['collection_authorized'] is False
