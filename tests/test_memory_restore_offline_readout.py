"""Readout fixtures only: no historical PID probes or new native owners."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d
from palimpsest.snapshots import save_snapshot


def offline():
    spec = importlib.util.find_spec('scripts.memory_restore_offline_readout')
    assert spec is not None, 'Offline retained-pair reader is not implemented'
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def retained_pair(tmp_path, monkeypatch):
    stage = tmp_path/'retained/stage'; (stage/'jobs').mkdir(parents=True)
    plan = {'repo':str(Path(p.__file__).resolve().parents[1]), 'assets':str(tmp_path/'assets'),
        'history_root':str(tmp_path/'histories'),'output':str(stage),'phase_root':str(stage.parent),
        'source_identity':{},'protocol_sha256':p.TRAVEL_PROTOCOL_SHA256}
    initial = {'integration':np.array([1.,2.]),'native_data':b'trusted fixture',
        'application':{'source_run_id':'source','event_prefix':{},
            'memory':{'u':{},'selector':{},'m':{'facts':[]}},
            'receipts':{'old':{'received_run_id':'source','applied_tick':1}}}}
    source = stage/'source/snapshots/initial.snp'; source.parent.mkdir(parents=True)
    save_snapshot(initial,source)
    reference = {'snapshot_path':str(source),'snapshot_sha256':p.file_hash(source),
        'invariant':p.condition_digest(initial)}
    attempted, cleanup = [], []
    for index, spec in enumerate(p.travel_specs('travel-feasibility',d.PROFILE)[-2:]):
        job = p.make_job('travel-feasibility',spec,plan,'repeat',source=reference)
        run = Path(job['output']); (run/'snapshots').mkdir(parents=True)
        save_snapshot(initial,run/'snapshots/initial.snp')
        final = copy.deepcopy(initial); final['native_data'] += bytes([index])
        post = p.publish_repeat_state(final,{'old'},run,p.phase_budget(stage.parent))
        owner = {'run_id':job['run_id'],'pid':1000+index,'pgid':1000+index,'starttime':1}
        (run/'owner.json').write_text(json.dumps(owner))
        (stage/'jobs'/(job['run_id']+'.json')).write_text(json.dumps(job))
        report = {'job_id':spec['id'],'run_id':job['run_id'],'run':str(run),
            'status':'recorded','raw_audit_pass':True,'invariants_preserved':True,
            'continuation_ticks':5,'trace_digest':'a'*64,
            'snapshot_path':str(run/'snapshots/initial.snp'),**post,
            'supervision':{'status':'completed','returncode':0}}
        (run/'worker-report.json').write_text(json.dumps(report))
        attempted.append(report)
        cleanup.append({'owner':owner,'path':str(run/'owner.json'),'status':'already-exited'})
    receipt = {'status':'independent-readout-stop','attempted':attempted,'cleanup':cleanup,
        'native_prerequisites_passed':False,'qualification_claims':[]}
    close = stage.parent/'execution.json'; close.write_text(json.dumps(receipt))
    registration = {'retained_root':str(stage.parent),
        'failed_close':{'path':str(close),'sha256':p.file_hash(close)}}
    monkeypatch.setattr(p,'audit_run',lambda job,*args:p.read_json(Path(job['output'])/'worker-report.json'))
    monkeypatch.setattr(p,'read_raw',lambda *args:{'rows':[{}]*5})
    monkeypatch.setattr(d,'compare_native_states',lambda *args:{'equal':False,'physics_steps':0,'scope':'fixture'})
    monkeypatch.setattr(d,'owner_exited',lambda *args:pytest.fail('historical PID probed'))
    monkeypatch.setattr(d,'cleanup_owners',lambda *args:pytest.fail('historical owner cleanup attempted'))
    monkeypatch.setattr(p,'launch_owner',lambda *args,**kwargs:pytest.fail('new native owner launched'))
    return registration, receipt, close


def test_offline_pair_audits_retained_payloads_without_current_pid_probe(tmp_path,monkeypatch):
    module = offline(); registration,receipt,close = retained_pair(tmp_path,monkeypatch)
    result = module.audit_pair(registration,None)
    assert result['trace_equal'] is True
    assert result['comparison']['equal'] is False
    assert result['comparison']['differing_components'] == ['native_data']
    assert [row['raw_rows'] for row in result['owners']] == [5,5]
    assert result['owner_exit_evidence'] == 'recorded same-namespace cleanup only; current liveness unassessed'
    assert p.read_json(close) == receipt


@pytest.mark.parametrize('change',['cleanup','extra-job','missing-post','corrupt-post','raw-count'])
def test_offline_pair_refuses_unbound_or_incomplete_evidence(tmp_path,monkeypatch,change):
    module = offline(); registration,receipt,close = retained_pair(tmp_path,monkeypatch)
    root = Path(registration['retained_root'])
    if change == 'cleanup':
        receipt['cleanup'][0]['owner']['starttime'] += 1
        close.write_text(json.dumps(receipt)); registration['failed_close']['sha256']=p.file_hash(close)
    elif change == 'extra-job':
        jobfile = next((root/'stage/jobs').glob('*.json'))
        (jobfile.parent/('f'*32+'.json')).write_bytes(jobfile.read_bytes())
    elif change in ('missing-post','corrupt-post'):
        post = Path(receipt['attempted'][0]['post_snapshot_path'])
        if change == 'missing-post':post.unlink()
        else:post.write_bytes(b'corrupt')
    else:
        monkeypatch.setattr(p,'read_raw',lambda *args:{'rows':[{}]*4})
    with pytest.raises(ValueError):module.audit_pair(registration,None)


def test_inventory_change_is_refused(tmp_path):
    module = offline(); root=tmp_path/'input'; root.mkdir(); path=root/'data'; path.write_bytes(b'old')
    reference={'root':str(root),'files':p.hash_ledger(root)}
    path.write_bytes(b'new')
    with pytest.raises(ValueError):module.verify_inventory(reference,None)


def test_native_decoder_omits_owned_views_of_unpopulated_arena_fields():
    mujoco=pytest.importorskip('mujoco')
    model=mujoco.MjModel.from_xml_string('<mujoco><worldbody/></mujoco>')
    data=mujoco.MjData(model)
    # Artificial metadata exercises a null arena pointer with a nonzero view
    # shape. No physics, retained snapshot, or study state is involved.
    data.nefc=1
    assert data.efc_AR_rownnz.flags.owndata is True
    fields,omitted=d.native_fields({'native_data':data.__getstate__()})
    assert 'efc_AR_rownnz' not in fields
    assert 'efc_AR_rowadr' not in fields
    assert any(row['field']=='efc_AR_rownnz' and row.get('reason')=='owned NumPy array is not a view of native storage' for row in omitted)


@pytest.mark.parametrize('failure',['recheck','close-deadline'])
def test_failed_offline_close_cannot_publish_complete_readout(tmp_path,monkeypatch,failure):
    module=offline(); monkeypatch.setattr(module,'__file__',str(tmp_path/'scripts/offline.py'))
    root=tmp_path/'runs/offline'; path=tmp_path/'registration.json'
    path.write_text(json.dumps({'schema':'memory-restore-offline-registration-v1',
        'repo':str(tmp_path),'output':str(root),'seconds_cap':300,
        'assets':str(tmp_path/'assets'),'history_root':str(tmp_path/'histories'),
        'retained_root':str(tmp_path/'retained'),'implementation_commit':'fixture-head'}))
    def git(command,**kwargs):
        value='' if 'status' in command or 'diff' in command else 'fixture-head\n'
        return value if kwargs.get('text') else value.encode()
    monkeypatch.setattr(module.subprocess,'check_output',git)
    monkeypatch.setattr(module.shutil,'disk_usage',lambda path:SimpleNamespace(
        total=20*p.GiB,used=0,free=20*p.GiB))
    calls=[]
    def check(*args):
        calls.append(1)
        if failure=='recheck' and len(calls)>1:raise ValueError('Changed source')
    monkeypatch.setattr(module,'recheck_inputs',check)
    monkeypatch.setattr(module,'audit_pair',lambda *args:{'comparison':{'equal':False},'owners':[]})
    original=module.replace_control; published=[]
    def publish(target,value,storage):
        original(target,value,storage)
        if value.get('status')=='offline-audit-complete':published.append(1)
    monkeypatch.setattr(module,'replace_control',publish)
    monkeypatch.setattr(module.time,'monotonic',lambda:301. if failure=='close-deadline' and published else 0.)
    assert module.main(['--registration',str(path)])==1
    result=p.read_json(root/'execution.json')
    assert result['status']=='offline-readout-stop'
    assert result['offline_pair_audit_complete'] is False
    assert result['qualification_claims']==[]


def test_offline_launcher_keeps_real_child_admission_clean_and_marker_exclusive(tmp_path,monkeypatch):
    actual_repo=Path(__file__).resolve().parents[1]
    source=actual_repo/'docs/reports/memory-restore-offline-readout-evidence/execute-readout.py'
    spec=importlib.util.spec_from_file_location('offline_launcher',source)
    launcher=importlib.util.module_from_spec(spec);spec.loader.exec_module(launcher)
    evidence=tmp_path/'docs/reports/memory-restore-offline-readout-evidence';evidence.mkdir(parents=True)
    workspace=tmp_path/'.superpowers/sdd/memory-restore-offline-readout';workspace.mkdir(parents=True)
    old=tmp_path/'.superpowers/sdd/memory-restore-study-v2/diagnose';old.mkdir(parents=True)
    (old/'launched.json').write_text('original consumed native invocation\n')
    (tmp_path/'.gitignore').write_text('.superpowers/\nruns/\n')
    actual_run=subprocess.run
    actual_run(['git','init','-q',str(tmp_path)],check=True)
    def commit():
        actual_run(['git','-C',str(tmp_path),'add','.'],check=True)
        actual_run(['git','-C',str(tmp_path),'-c','user.name=Fixture',
            '-c','user.email=fixture@example.test','commit','-qm','fixture'],check=True)
    commit()
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=tmp_path,text=True).strip()
    registration=evidence/'registration.json'
    registration.write_text(json.dumps({'schema':'memory-restore-offline-registration-v1',
        'repo':str(tmp_path),'output':str(tmp_path/'runs/offline'),'retained_root':str(tmp_path/'retained'),
        'assets':str(tmp_path/'assets'),'history_root':str(tmp_path/'histories'),
        'python':sys.executable,'seconds_cap':300,'implementation_commit':head}))
    commit();monkeypatch.setattr(launcher,'__file__',str(evidence/'execute-readout.py'))
    calls=[]
    def child(command,**kwargs):
        if command[0]!='timeout':return actual_run(command,**kwargs)
        calls.append(command)
        assert command[3]=='290s'
        assert command[-4:-1]==['-m','scripts.memory_restore_offline_readout','--registration']
        bootstrap=(
            'import sys; sys.path.insert(0,'+repr(str(actual_repo))+'); '
            'from scripts import memory_restore_offline_readout as o; '
            'o.__file__='+repr(str(tmp_path/'scripts/offline.py'))+'\n'
            'def stop_before_analysis(*args):\n'
            '    print("production clean offline admission reached; no analysis",flush=True)\n'
            '    raise SystemExit(0)\n'
            'o.recheck_inputs=stop_before_analysis\n'
            'raise SystemExit(o.main(["--registration",'+repr(str(registration))+']))\n')
        env=dict(kwargs['env'],PYTHONPATH=str(actual_repo/'src')+':'+str(actual_repo))
        return actual_run(command[:4]+[sys.executable,'-c',bootstrap],**{**kwargs,'env':env})
    monkeypatch.setattr(launcher.subprocess,'run',child)
    assert launcher.main()==0
    assert (workspace/'offline-launched.json').is_file()
    assert not (tmp_path/'runs/offline').exists()
    assert 'production clean offline admission reached' in (evidence/'readout.log').read_text()
    assert (old/'launched.json').read_text()=='original consumed native invocation\n'
    commit()
    assert subprocess.check_output(['git','status','--porcelain'],cwd=tmp_path)==b''
    with pytest.raises(FileExistsError):launcher.main()
    assert len(calls)==1
