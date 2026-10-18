"""Authored preparation03 → epoch14 (epoch11 policy, extended clocks) → audits; no vendors.

The scaled clock case clones the parent with qualification clocks divided by ten
(epoch11 18/19/20 s, epoch14 36/37/39 s) and gives the held mujoco import a 20 s
delay: epoch11 must stop it, epoch14 must not. Preparation clocks stay unscaled.
"""
import copy
import json
import os
import subprocess
import time

import pytest

from test_puck_cpu_held_amendment08 import QUALIFIER
from test_puck_cpu_held_amendment11 import HIDDEN11, ROSTER11
from test_puck_cpu_held_parent_integration import ROOT, canonical, digest, load, run_cli
from test_puck_cpu_held_preparation02_integration import authored_preparations, preparation03_fixture


AUTHORED_ROSTER11=[name for name in ROSTER11 if name!='numpy._distributor_init_local']
PROBED=['backports_abc','networkx','pandas','sklearn','tabulate']
CLOCKS14=dict(normal_seconds=360,child_hard_seconds=375,hard_seconds=390)


def qualification(api,root,env,case,epoch):
    config=api.configuration_template(phase='qualify',root=str(root),stage_parent=str(case['stage']),
        sources=copy.deepcopy(case['prepare']['sources']),inputs=env['updated_inputs'],
        negative_imports=list(AUTHORED_ROSTER11),preparation_acceptance=case['acceptance'])
    config.update(kind='puck-cpu-held-runtime-allocation-v'+str(epoch),version=epoch,allocation_id=epoch)
    if epoch==14:config['limits']=copy.deepcopy(api.QUALIFY14_LIMITS)
    return config


def test_authored14_runs_epoch11_policy_on_preparation03_with_extended_clocks(tmp_path):
    before=len(os.listdir('/proc/self/fd'))
    auditor_path=ROOT/'scripts/audit_puck_cpu_held_runtime.py'
    auditor=load(auditor_path,'cpu_authored_epoch14_auditor')
    with preparation03_fixture(tmp_path) as case:
        root,api,stage,prepbase=(case[k] for k in ('root','api','stage','prepbase'))
        historical_dep=(prepbase/'payload/dependencies.json').read_bytes()
        identities=[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        config=qualification(api,root,case,case,14)
        assert config['limits']=={**api.LIMITS['qualify'],**CLOCKS14}
        assert config['sources']==case['prepared']['sources']
        assert next(r for r in config['sources'] if r['path']==QUALIFIER)['sha256']==digest((ROOT/QUALIFIER).read_bytes())
        assert config['preparation_acceptance']['result']['path']=='runs/puck-cpu-held-preparation-03/result.json'
        prepared_bytes={str(p.relative_to(root)):p.read_bytes() for p in prepbase.rglob('*') if p.is_file()}
        code,stdout,stderr=run_cli(root,api,'qualify14',config)
        base=root/'runs/puck-cpu-held-qualification-14'
        raw=(base/'result.json').read_bytes() if (base/'result.json').exists() else b''
        assert code==0,(code,stdout,stderr,raw,(base/'logs/stderr.log').read_bytes() if (base/'logs/stderr.log').exists() else b'')
        result=json.loads(raw)
        assert stdout==raw and (result['kind'],result['version'],result['allocation_id'],result['status'])==(
            'puck-cpu-held-runtime-outcome-v14',14,14,'imports_completed')
        worker=json.loads((base/'logs/stdout.log').read_bytes())
        assert [(r['name'],r['version']) for r in worker['entry_result']['imports']]==list(api.VERSIONS.items())
        assert worker['entry_result']['qualification_version']==5
        assert worker['expected_missing_imports']==AUTHORED_ROSTER11 and worker['expected_hidden_imports']==HIDDEN11
        assert worker['denied_imports']==PROBED
        registration=json.loads((base/'control/worker-registration.json').read_bytes())
        assert registration['deadline_seconds']==360==api.QUALIFY14_WORKER_SECONDS
        assert registration['qualification']['kind']=='puck-held-runtime-import-qualification-v5'
        assert registration['qualification']['hidden_imports']==HIDDEN11
        current_dep=(base/'control/dependencies.json').read_bytes()
        assert json.loads(current_dep)['roots']==json.loads(historical_dep)['roots']
        configuration=root/'authored-qualify14-configuration.json'
        transport=root/'authored-qualify14-transport.json'
        report=auditor.audit(configuration,digest(configuration.read_bytes()),transport,
            digest(transport.read_bytes()),deadline=time.monotonic()+30)
        assert (report['kind'],report['version'],report['allocation_id'],report['status'])==(
            'puck-cpu-held-runtime-independent-audit-v14',14,14,'PASS')
        assert report['preparation_result_sha256']==digest(case['prepared_raw'])
        assert report['historical_source_epoch_sha256']==report['current_source_epoch_sha256']
        published=root/'authored-epoch14-cli-audit.json'
        command=[api.PYTHON,'-I','-S','-B',str(auditor_path),'--configuration',str(configuration),
            '--sha256',digest(configuration.read_bytes()),'--transport',str(transport),
            '--transport-sha256',digest(transport.read_bytes()),'--output',str(published)]
        process=subprocess.run(command,cwd=root,capture_output=True,timeout=30,
            env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'))
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==published.read_bytes() and json.loads(process.stdout)['version']==14
        for outcome in (result,report,json.loads(process.stdout)):
            assert all(outcome[key]==value for key,value in api.CLAIMS.items())
            assert outcome['closure']['active_children']==outcome['closure']['active_non_main_threads']==[]
        assert identities==[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        # The independent registration gate requires exactly the extended worker clock.
        sources={row['path']:(base/'worker-source'/row['path']).read_bytes() for row in registration['source_files']}
        target=base/'control/worker-registration.json';original=target.read_bytes()
        for change in (lambda v:v.pop('deadline_seconds'),lambda v:v.update(deadline_seconds=180)):
            changed=json.loads(original);change(changed)
            try:
                target.write_bytes(canonical(changed).rstrip(b'\n'))
                held=auditor.Held(time.monotonic()+30)
                try:
                    with pytest.raises(ValueError,match='^Exact worker registration differs$'):
                        auditor.worker(held,base,config,json.loads(current_dep),current_dep,sources)
                finally:held.close()
            finally:target.write_bytes(original)
        # Epoch11's identity and clocks cannot claim preparation03 or this outcome.
        legacy=dict(copy.deepcopy(config),kind='puck-cpu-held-runtime-allocation-v11',version=11,allocation_id=11,
                    limits=copy.deepcopy(api.LIMITS['qualify']))
        with pytest.raises(ValueError):api.validate_configuration(legacy)
        with pytest.raises(ValueError):auditor.configuration(legacy,True)
        for name,previous in prepared_bytes.items():assert (root/name).read_bytes()==previous
        code,_,stderr=run_cli(root,api,'qualify14-rerun',config)
        assert code!=0 and b'CPU allocation already reserved' in stderr
    assert len(os.listdir('/proc/self/fd'))==before


def scale_qualification_clocks(raw):
    old=b"LIMITS={phase:dict(normal_seconds=180,child_hard_seconds=190,hard_seconds=200,"
    new=(b"LIMITS={phase:dict(normal_seconds=180 if phase=='prepare' else 18,"
         b"child_hard_seconds=190 if phase=='prepare' else 19,hard_seconds=200 if phase=='prepare' else 20,")
    old14=b"QUALIFY14_LIMITS=dict(LIMITS['qualify'],normal_seconds=360,child_hard_seconds=375,hard_seconds=390)"
    new14=b"QUALIFY14_LIMITS=dict(LIMITS['qualify'],normal_seconds=36,child_hard_seconds=37,hard_seconds=39)"
    assert raw.count(old)==1 and raw.count(old14)==1
    changed=raw.replace(old,new).replace(old14,new14)
    assert changed.replace(new14,old14).replace(new,old)==raw
    return changed


def test_scaled_epoch14_clock_outlasts_a_held_import_that_epoch11_stops(tmp_path):
    with authored_preparations(tmp_path,(12,13),mutate_parent=scale_qualification_clocks,worker_delay_seconds=20) as env:
        root,api,cases=env['root'],env['api'],env['cases']
        assert {k:api.LIMITS['qualify'][k] for k in CLOCKS14}=={'normal_seconds':18,'child_hard_seconds':19,'hard_seconds':20}
        assert {k:api.QUALIFY14_LIMITS[k] for k in CLOCKS14}=={'normal_seconds':36,'child_hard_seconds':37,'hard_seconds':39}
        assert api.LIMITS['prepare']['normal_seconds']==180
        started=time.monotonic();code,stdout,stderr=run_cli(root,api,'qualify11',qualification(api,root,env,cases[12],11))
        stopped=time.monotonic()-started
        assert code!=0 and stdout==b'',(code,stdout,stderr)
        assert b'normal return deadline' in stderr or code<0,(code,stderr)
        assert stopped<22,stopped
        log=root/'runs/puck-cpu-held-qualification-11/logs/stderr.log'
        assert b'import.mujoco.enter' in log.read_bytes() and b'import.mujoco.returned' not in log.read_bytes()
        started=time.monotonic();code,stdout,stderr=run_cli(root,api,'qualify14',qualification(api,root,env,cases[13],14))
        elapsed=time.monotonic()-started
        raw=(root/'runs/puck-cpu-held-qualification-14/result.json').read_bytes()
        assert code==0,(code,stdout,stderr,raw)
        result=json.loads(raw)
        assert stdout==raw and (result['version'],result['status'])==(14,'imports_completed')
        assert 18<result['elapsed_seconds']<36 and elapsed<39,(result['elapsed_seconds'],elapsed)
        worker=json.loads((root/'runs/puck-cpu-held-qualification-14/logs/stdout.log').read_bytes())
        assert [r['name'] for r in worker['entry_result']['imports']]==['numpy','torch','torchvision','mujoco']
        assert next(r['seconds'] for r in worker['entry_result']['imports'] if r['name']=='mujoco')>=20
