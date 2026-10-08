"""Opt-in selected-profile admission and restored terminal proof; no physics."""
import copy
import importlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from scripts import memory_decision_pilot as p, memory_restore_diagnostic as d


def selected():
    assert importlib.util.find_spec('scripts.memory_selected_pilot'), 'Selected pilot admission is missing'
    return importlib.import_module('scripts.memory_selected_pilot')


def test_unknown_prerequisite_cannot_allocate_a_pilot(tmp_path):
    s = selected()
    with pytest.raises(ValueError):
        s.admit_prerequisites(tmp_path/'unregistered.json', tmp_path)
    assert not (tmp_path/'runs').exists()


def admitted_fixture(tmp_path,monkeypatch):
    s=selected()
    from test_memory_prerequisites_v2 import setup_campaign
    receipts={'neural-'+str(i):{'received_run_id':'source','applied_tick':i} for i in range(727)}
    m,path,root,reg,_,_=setup_campaign(tmp_path,monkeypatch,version='v3',source_receipts=receipts)
    identity={'pilot_driver_sha256':p.file_hash(Path(reg['repo'])/'scripts/memory_decision_pilot.py')}
    reg['source_identity']=identity;path.write_text(json.dumps(reg))
    monkeypatch.setattr(p,'source_identity',lambda repo,assets:
        {'pilot_driver_sha256':p.file_hash(Path(repo)/'scripts/memory_decision_pilot.py')})
    marker=Path(reg['control_root'])/'launched.json';value=p.read_json(marker)
    value.update(registration_sha256=p.file_hash(path),implementation_head='0'*40)
    marker.write_text(json.dumps(value))
    assert m.run(path)==0 and m.audit(path)==0
    index=Path(reg['publication_root'])/'publication-index.json'
    files=[]
    for base in (root,Path(reg['control_root']),Path(reg['publication_root'])):
        files.extend({'source':str(base/r['path']),'bytes':r['bytes'],'sha256':r['sha256']}
                     for r in p.hash_ledger(base))
    index.write_text(json.dumps({'files':files}))
    monkeypatch.setattr(s,'PREREQUISITE_REGISTRATION_SHA256',p.file_hash(path))
    monkeypatch.setattr(s,'PREREQUISITE_CLOSE_SHA256',p.file_hash(root/'scientific-close.json'))
    monkeypatch.setattr(s,'PREREQUISITE_INDEX_SHA256',p.file_hash(index))
    new=tmp_path/'new';(new/'scripts').mkdir(parents=True)
    worker=new/'scripts/memory_decision_pilot.py';worker.write_text('new explicit worker admission\n')
    monkeypatch.setattr(p,'__file__',str(worker))
    return s,path,root,reg,new


def test_only_pinned_independent_prerequisite_and_explicit_worker_derivation_admit(tmp_path,monkeypatch):
    s,path,root,reg,new=admitted_fixture(tmp_path,monkeypatch)
    result=s.admit_prerequisites(path,new)
    assert result['registration_sha256']==p.file_hash(path)
    assert result['close_sha256']==p.file_hash(root/'scientific-close.json')
    assert result['old_worker_sha256']==reg['source_identity']['pilot_driver_sha256']
    assert result['new_worker_sha256']==p.file_hash(new/'scripts/memory_decision_pilot.py')
    assert not (new/'runs').exists()
    (root/'stage/preflight.json').write_text('changed raw inventory')
    with pytest.raises(ValueError):s.admit_prerequisites(path,new)


@pytest.mark.parametrize('mutation',['close-pin','copied-success','source-drift','candidate-exclusion','missing-cell'])
def test_prerequisite_flags_never_replace_pins_inputs_and_complete_cells(tmp_path,monkeypatch,mutation):
    s,path,root,reg,new=admitted_fixture(tmp_path,monkeypatch)
    if mutation=='source-drift':
        monkeypatch.setattr(p,'source_identity',lambda *a:{'pilot_driver_sha256':'a'*64,'assets_sha256':'b'*64})
    else:
        target=root/'scientific-close.json';value=p.read_json(target)
        if mutation=='close-pin':value['status']='edited'
        elif mutation=='copied-success':value['immutable_inputs_and_raw_evidence_unchanged']=False
        elif mutation=='candidate-exclusion':value['candidate_comparison']['excluded_native_bytes_per_side']=128
        else:value['owners'].pop()
        target.write_text(json.dumps(value))
        if mutation!='close-pin':monkeypatch.setattr(s,'PREREQUISITE_CLOSE_SHA256',p.file_hash(target))
    with pytest.raises(ValueError):s.admit_prerequisites(path,new)
    assert not (new/'runs').exists()


def test_selected_protocol_admits_only_frozen_prefix_and_condition_bounds():
    protocol = getattr(p, 'SELECTED_PILOT_PROTOCOL_SHA256', None)
    assert protocol is not None, 'Separate selected-profile worker protocol is missing'
    assert p.owner_allocation('pilot-v2', 'prefix', protocol) == (360, 370)
    assert p.owner_allocation('pilot-v2', 'condition', protocol) == (120, 130)
    for stage, operation in [('pilot','condition'),('pilot-v2','repeat'),('travel-feasibility','prefix')]:
        with pytest.raises(ValueError): p.owner_allocation(stage,operation,protocol)
    with pytest.raises(ValueError):
        p.owner_allocation('pilot-v2','condition',p.TRAVEL_PROTOCOL_SHA256)
    assert p.stage_cap('pilot',None) == 4200


def test_restored_stall_uses_acquired_tick_and_inherited_counter():
    row = {'tick':727,'pose':np.array([0.,0.,0.]),'next_pose':np.array([0.,0.,0.]),
           'action':np.array([.1,0.])}
    outcome = {'reason':'stalled','episode':0,'steps':728}
    data = {'rows':[row], 'events':[{'kind':'episode_finished','outcome':outcome}]}
    report = {'outcome':outcome,'total_ticks':728,'final_phase':'terminated'}
    assert p.audit_native_prefix_terminal(data,report,start_tick=727,stall_steps=49) == 'stalled'
    with pytest.raises(ValueError):
        p.audit_native_prefix_terminal(data,report,start_tick=727,stall_steps=0)
    wrong = copy.deepcopy(data);wrong['rows'][0]['tick']=726
    with pytest.raises(ValueError):
        p.audit_native_prefix_terminal(wrong,report,start_tick=727,stall_steps=49)


def test_restored_time_limit_cannot_hide_missing_rows():
    rows = [{'tick':i,'pose':[0.,0.,0.],'next_pose':[.01,0.,0.],'action':[.1,0.]}
            for i in range(727,730)]
    outcome={'reason':'time_limit','episode':0,'steps':730}
    data={'rows':rows,'events':[{'kind':'episode_finished','outcome':outcome}]}
    report={'outcome':outcome,'total_ticks':730,'final_phase':'truncated'}
    assert p.audit_native_prefix_terminal(data,report,expected_cap=730,start_tick=727) == 'time_limit'
    data['rows'].pop(1)
    with pytest.raises(ValueError):
        p.audit_native_prefix_terminal(data,report,expected_cap=730,start_tick=727)


def test_condition_task_failure_uses_verified_source_stall_state():
    snapshot={'application':{'episode_step':727},
              'environment':{'values':{'_stall_steps':49,'_prev_xy':[0.,0.]}}}
    outcome={'reason':'stalled','episode':0,'steps':728}
    report={'goal':False,'outcome':outcome,'total_ticks':728,'final_phase':'terminated',
        'final_memory':{'supervisor':{'continuation_start_tick':727}}}
    data={'rows':[{'tick':727,'pose':[0.,0.,0.],'next_pose':[0.,0.,0.],'action':[.1,0.]}],
          'events':[{'kind':'episode_finished','outcome':outcome}]}
    assert p.audit_travel_task_failure(data,report,source_snapshot=snapshot)=='stalled'
    wrong=copy.deepcopy(snapshot);wrong['environment']['values']['_stall_steps']=0
    with pytest.raises(ValueError):p.audit_travel_task_failure(data,report,source_snapshot=wrong)
    wrong=copy.deepcopy(snapshot);wrong['application']['episode_step']=726
    with pytest.raises(ValueError):p.audit_travel_task_failure(data,report,source_snapshot=wrong)
    bad=copy.deepcopy(report);bad['final_phase']='paused';bad['outcome']=None
    with pytest.raises(ValueError):p.audit_travel_task_failure(data,bad,source_snapshot=snapshot)


def test_bounded_pair_publication_keeps_full_reports_outside_envelope(tmp_path,monkeypatch):
    s = selected()
    from palimpsest.storage import StorageBudget,StorageLimits
    storage=StorageBudget([tmp_path],StorageLimits(max_bytes=8*p.GiB,min_free_bytes=0))
    report={'run_id':'a'*32,'job_id':'case/own','status':'recorded','goal':False,
            'continuation_ticks':5,'raw_audit_pass':True,'final_memory':{'large':'x'*700000},
            'world_state':{'identity':'kept'},'supervision':{'status':'completed','returncode':0}}
    compact=s.retain_report(tmp_path,report,storage)
    assert len(p.canonical({'attempted':[compact]*30}))<p.MiB
    stored=p.read_json(compact['audit_path'])
    assert stored==report and compact['audit_sha256']==p.file_hash(compact['audit_path'])
    assert compact['goal'] is False and compact['continuation_ticks']==5


def test_pilot_pairs_use_all_six_selected_specs_and_keep_natural_failures(monkeypatch):
    selected()
    calls=[]
    def launch(stage,spec,plan,storage,deadline,*,operation,condition=None,source=None):
        assert stage=='pilot-v2' and spec['profile_sha256']==d.PROFILE
        calls.append(spec['id']+('/'+condition if condition else ''))
        return {'job_id':calls[-1],'run_id':str(len(calls)),'status':'recorded','condition':condition,
            'raw_audit_pass':True,'acquired':True,'invariant':'same','goal':condition!='swapped',
            'continuation_ticks':37,'path_length':4.,'trace_digest':'same',
            'route_commits':[{'route_id':'route-a','tick':12}], 'post_event_samples':[],
            'event_tick':10,'commitment_inputs':[[{'estimate':'open'}]],
            'first_commitment_blocked':False,'retreat_completed':False}
    monkeypatch.setattr(p,'launch_owner',launch)
    plan={'output':'unused','phase_root':'unused','source_identity':{},'geometry_valid':True,
          'protocol_sha256':p.SELECTED_PILOT_PROTOCOL_SHA256}
    result=p.execute_stage('pilot-v2',plan,None,None)
    assert len(calls)==30 and result['mandatory_pass'] is True
    assert len(result['pair_audits'])==6 and result['mechanism_observed'] is False
    assert all(a['scores']['swapped']==900 for a in result['pair_audits'])
    assert all(a['scores']['own']==37 for a in result['pair_audits'])


def test_source_failure_lists_every_remaining_slot_without_replacement(monkeypatch):
    selected()
    calls=[]
    def launch(stage,spec,*args,**kw):
        calls.append(spec['id'])
        return {'job_id':spec['id'],'status':'failed','raw_audit_pass':False,'acquired':False}
    monkeypatch.setattr(p,'launch_owner',launch)
    plan={'output':'unused','phase_root':'unused','source_identity':{},'geometry_valid':True,
          'protocol_sha256':p.SELECTED_PILOT_PROTOCOL_SHA256}
    result=p.execute_stage('pilot-v2',plan,None,None)
    assert calls==['local_cue-south'] and result['mandatory_pass'] is False
    assert len(result['unattempted'])==29


def registration_fixture(tmp_path,monkeypatch):
    s,path,root,baseline,repo=admitted_fixture(tmp_path,monkeypatch)
    names=['scripts/memory_selected_pilot.py','scripts/memory_restore_diagnostic.py',
        'scripts/memory_prerequisites_v2.py','scripts/memory_restore_offline_readout.py',
        'docs/plans/memory-decision-pilot-v2.md',
        'docs/reports/restore-qualification-v2-evidence/execute-restore-v2.py',
        'docs/reports/memory-decision-pilot-v2-evidence/register.py',
        'docs/reports/memory-decision-pilot-v2-evidence/execute-pilot.py',
        'docs/reports/memory-decision-pilot-v2-software-evidence/resource-preflight.json']
    for name in names:
        target=repo/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text('fixture '+name+'\n')
    (repo/'scripts/memory_restore_diagnostic.py').write_bytes(
        (Path(baseline['repo'])/'scripts/memory_restore_diagnostic.py').read_bytes())
    for name in ('memory_prerequisites_v2.py','memory_restore_offline_readout.py'):
        (repo/'scripts'/name).write_bytes((Path(baseline['repo'])/'scripts'/name).read_bytes())
    (repo/names[-1]).write_text(json.dumps({'projected_phase_bytes':8454943744,
        'aggregate_bytes':8*p.GiB,'headroom_bytes':64*p.MiB,'guarantees_all_owners':False,
        'uncompressed_nonraw_copy_allowance':1102671872}))
    monkeypatch.setattr(s,'__file__',str(repo/'scripts/memory_selected_pilot.py'))
    monkeypatch.setattr(d,'__file__',str(repo/'scripts/memory_restore_diagnostic.py'))
    assert callable(getattr(s,'build_registration',None)), 'Bounded pilot registration is missing'
    reg=s.build_registration(repo,path,stamp='fixture')
    regpath=Path(reg['publication_root'])/'registration.json';regpath.write_text(json.dumps(reg))
    return s,reg,regpath


def test_registration_freezes_thirty_unique_slots_without_allocating_runtime(tmp_path,monkeypatch):
    s,reg,path=registration_fixture(tmp_path,monkeypatch)
    s.validate_registration(reg)
    assert len(reg['owner_slots'])==30 and len({x['run_id'] for x in reg['owner_slots']})==30
    assert [x['job_id'] for x in reg['owner_slots'][:5]]==[
        'local_cue-south','local_cue-south/own','local_cue-south/swapped',
        'local_cue-south/no-U','local_cue-south/sham']
    assert reg['seconds_caps']==[6000,600] and reg['native_owners_max']==30
    assert not Path(reg['output']).exists() and not Path(reg['control_root']).exists()


@pytest.mark.parametrize('key,value',[('seconds_caps',[6001,600]),('corrective_studies',1),
    ('native_owners_max',31),('protocol_sha256',p.TRAVEL_PROTOCOL_SHA256)])
def test_registration_refuses_resource_or_protocol_extension(tmp_path,monkeypatch,key,value):
    s,reg,path=registration_fixture(tmp_path,monkeypatch);reg[key]=value
    with pytest.raises(ValueError):s.validate_registration(reg)


def test_worker_needs_committed_registration_and_exact_case_slot_before_allocation(tmp_path,monkeypatch):
    s,reg,path=registration_fixture(tmp_path,monkeypatch)
    plan={**reg,'output':str(Path(reg['output'])/'stage'),'phase_root':reg['output'],
        'pilot_registration_path':str(path),'pilot_registration_sha256':p.file_hash(path)}
    job=p.make_job('pilot-v2',reg['expected_specs'][0],plan,'prefix')
    assert p.validate_job(job)['run_id']==reg['owner_slots'][0]['run_id']
    assert not Path(reg['output']).exists()
    for key,value in [('run_id','f'*32),('pilot_registration_sha256','f'*64),
                      ('case',{**job['case'],'profile_sha256':'f'*64})]:
        bad=copy.deepcopy(job);bad[key]=value
        with pytest.raises(ValueError):p.validate_job(bad)
    bad=copy.deepcopy(job);bad.pop('pilot_registration_path')
    with pytest.raises(ValueError):p.validate_job(bad)
    assert not Path(reg['output']).exists()


def test_clock_refuses_rebased_or_late_independent_close(tmp_path,monkeypatch):
    s,reg,path=registration_fixture(tmp_path,monkeypatch)
    marker=Path(reg['control_root'])/'launched.json';marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({'started_monotonic':100.,'registration_sha256':p.file_hash(path)}))
    receipt={'started_monotonic':100.,'owner_deadline_monotonic':6100.,
        'global_deadline_monotonic':6700.,'readout_started_monotonic':1000.,
        'readout_deadline_monotonic':1600.}
    assert s.validate_clock(reg,path,receipt,now=1500.)==1600.
    with pytest.raises(ValueError):s.validate_clock(reg,path,receipt,now=1601.)
    receipt['readout_deadline_monotonic']=6700.
    with pytest.raises(ValueError):s.validate_clock(reg,path,receipt,now=1500.)


def pilot_fixture(tmp_path,monkeypatch,*,failure=None,large=False):
    """Native execution/replay are doubled; slots, files, scores and close are real."""
    import os,time
    from contextlib import nullcontext
    from palimpsest.snapshots import save_snapshot
    from palimpsest.storage import StorageBudget,StorageLimits
    s,reg,path=registration_fixture(tmp_path,monkeypatch);root=Path(reg['output'])
    control=Path(reg['control_root']);control.mkdir(parents=True)
    (control/'launched.json').write_text(json.dumps({'started_monotonic':time.monotonic(),
        'registration_sha256':p.file_hash(path)}))
    monkeypatch.setattr(s,'budget',lambda reg:StorageBudget(
        [reg[k] for k in ('output','control_root','publication_root')],
        StorageLimits(max_bytes=8*p.GiB,min_free_bytes=0,max_runs=30,max_snapshots=1),headroom_bytes=64*p.MiB))
    monkeypatch.setattr(StorageBudget,'lock',lambda self:nullcontext())
    monkeypatch.setattr(p,'preflight',lambda *a,**kw:{**reg,'output':str(root/'stage'),
        'phase_root':str(root),'geometry_valid':True})
    launched=[]
    def launch(stage,spec,plan,storage,deadline,*,operation=None,condition=None,source=None,**kw):
        assert stage=='pilot-v2'
        label=spec['id']+('/'+condition if condition else '')
        assert label not in launched
        if failure=='allocation' and len(launched)==1:raise RuntimeError('Refused before allocation')
        job=p.validate_job(p.make_job(stage,spec,plan,operation,condition,source))
        run=Path(job['output']);(run/'snapshots').mkdir(parents=True)
        state={'integration':{},'native_data':b'fixture','application':{'episode_step':727,
            'memory':{'u':{},'selector':{},'supervisor':{'phase':'await_decision'}},
            'receipts':{'neural-0':{'received_run_id':job['run_id']}}}}
        if source:state=d.read_snapshot(source['snapshot_path'])
        save_snapshot(state,run/'snapshots/initial.snp')
        owner={'run_id':job['run_id'],'pid':900000+len(launched),'pgid':900000+len(launched),
            'starttime':1,'process_namespace':os.readlink('/proc/self/ns/pid')}
        (run/'owner.json').write_text(json.dumps(owner))
        jobs=root/'stage/jobs';jobs.mkdir(exist_ok=True);(jobs/(job['run_id']+'.json')).write_text(json.dumps(job))
        supervision=root/'stage/supervision'/job['run_id'];supervision.mkdir(parents=True)
        supervised={'status':'completed','returncode':0,'elapsed_seconds':1.,
            'timeout_seconds':370 if operation=='prefix' else 130,'output':str(supervision)}
        (supervision/'supervisor.json').write_text(json.dumps(supervised))
        route='alternate' if condition in ('own','swapped','sham') else 'preferred'
        report={'job_id':label,'run_id':job['run_id'],'run':str(run),'operation':operation,
            'condition':condition,'status':'recorded','raw_audit_pass':True,'acquired':True,
            'goal':condition is not None,'continuation_ticks':10 if condition else 0,
            'snapshot_path':str(run/'snapshots/initial.snp'),'snapshot_sha256':p.file_hash(run/'snapshots/initial.snp'),
            'invariant':p.condition_digest(state),'wall_seconds':1.,'supervision':supervised,
            'total_ticks':737 if condition else 727,'trace_digest':route,
            'path_length':(1. if spec['kind']=='null' and condition=='no-U' else
                3. if condition=='no-U' or (spec['kind']=='null' and condition in ('own','sham')) else 2.),
            'route_commits':[{'tick':729,'route_id':route}],'post_event_samples':[730],
            'event_tick':728 if spec['kind']!='no-event' else None,
            'commitment_inputs':[[route]],'first_commitment_blocked':condition=='no-U',
            'retreat_completed':condition=='no-U','replans':int(condition=='no-U')}
        if large:report['final_memory']={'e':{'evidence':'x'*700000}}
        if failure=='own-sham' and condition=='sham':report['trace_digest']='different'
        if failure=='no-mechanism':
            report.update(trace_digest='same',path_length=2.,commitment_inputs=[['same']],
                route_commits=[{'tick':729,'route_id':'same'}],first_commitment_blocked=False)
        if failure=='prefix' and not launched:report.update(status='failed',raw_audit_pass=False,acquired=False)
        if failure=='condition' and len(launched)==1:report.update(status='failed',raw_audit_pass=False)
        (run/'worker-report.json').write_text(json.dumps(report));launched.append(label)
        return report
    monkeypatch.setattr(p,'launch_owner',launch)
    monkeypatch.setattr(p,'audit_run',lambda job,*a:p.read_json(Path(job['output'])/'worker-report.json'))
    return s,reg,path,root,launched


def test_complete_negative_mechanism_is_a_result_and_never_retried(tmp_path,monkeypatch):
    s,reg,path,root,launched=pilot_fixture(tmp_path,monkeypatch,failure='no-mechanism')
    assert s.run(path)==0 and len(launched)==30 and s.audit(path)==0
    close=p.read_json(root/'scientific-close.json')
    assert close['pilot_complete'] is True and close['mechanism_observed'] is False


def test_registration_cannot_derive_a_changed_diagnostic(tmp_path,monkeypatch):
    s,reg,path=registration_fixture(tmp_path,monkeypatch)
    (Path(reg['repo'])/'scripts/memory_restore_diagnostic.py').write_text('changed scientific normalizer')
    with pytest.raises(ValueError):s.build_registration(reg['repo'],reg['prerequisite']['registration_path'],stamp='altered')


def test_worker_rejects_expired_original_owner_allocation_before_output(tmp_path,monkeypatch):
    import time
    s,reg,path=registration_fixture(tmp_path,monkeypatch)
    marker=Path(reg['control_root'])/'launched.json';marker.parent.mkdir(parents=True)
    marker.write_text(json.dumps({'started_monotonic':time.monotonic()-6001,
        'registration_sha256':p.file_hash(path)}))
    plan={**reg,'output':str(Path(reg['output'])/'stage'),'phase_root':reg['output'],
        'pilot_registration_path':str(path),'pilot_registration_sha256':p.file_hash(path)}
    job=p.make_job('pilot-v2',reg['expected_specs'][0],plan,'prefix')
    with pytest.raises(TimeoutError):p.worker(job)
    assert not Path(job['output']).exists()


def test_thirty_slots_require_independent_close_and_keep_bounded_reports(tmp_path,monkeypatch):
    s,reg,path,root,launched=pilot_fixture(tmp_path,monkeypatch,large=True)
    assert callable(getattr(s,'run',None)) and callable(getattr(s,'audit',None)), 'Selected runner/close missing'
    assert s.run(path)==0
    before=p.read_json(root/'execution.json')
    assert launched==[row['job_id'] for row in reg['owner_slots']]
    assert before['pilot_complete'] is False and before['mandatory_pass'] is True
    assert (root/'execution.json').stat().st_size<p.MiB
    assert s.audit(path)==0
    close=p.read_json(root/'scientific-close.json')
    assert close['pilot_complete'] is True and close['mechanism_observed'] is True
    assert len(close['owners'])==30 and len(close['pair_audits'])==6
    assert close['r2_complete'] is False and close['held_out_used'] is False and close['qualification_claims']==[]
    assert (root/'scientific-close.json').stat().st_size<p.MiB
    assert p.read_json(root/'execution.json')==before
    assert len(list(Path(reg['publication_root']).glob('inline-audits/*.json')))==30
    with pytest.raises(FileExistsError):s.audit(path)


@pytest.mark.parametrize('failure,count',[('prefix',1),('condition',2),('own-sham',5),('allocation',1)])
def test_first_failure_stops_all_later_owners_and_retains_partial_close(tmp_path,monkeypatch,failure,count):
    s,reg,path,root,launched=pilot_fixture(tmp_path,monkeypatch,failure=failure)
    assert callable(getattr(s,'run',None)), 'Selected runner missing'
    assert s.run(path)==1 and len(launched)==count
    assert s.audit(path)==1
    close=p.read_json(root/'scientific-close.json')
    assert close['pilot_complete'] is False and len(close['unattempted'])==30-count
    assert len(close['owners'])==count
    for row in close['owners']:
        if row.get('raw_audit_pass') is not True:assert 'capped_ticks' not in row


@pytest.mark.parametrize('mutation',['raw','supervision','slot','source','extra-owner','cleanup','clock','input'])
def test_independent_close_rejects_tampered_evidence(tmp_path,monkeypatch,mutation):
    import time
    s,reg,path,root,launched=pilot_fixture(tmp_path,monkeypatch)
    assert callable(getattr(s,'run',None)), 'Selected runner missing'
    assert s.run(path)==0
    first=reg['owner_slots'][0]['run_id'];second=reg['owner_slots'][1]['run_id']
    if mutation=='raw':(root/'stage/runs'/first/'worker-report.json').write_text('{}')
    elif mutation=='supervision':(root/'stage/supervision'/first/'supervisor.json').write_text('{}')
    elif mutation=='slot':
        jobpath=root/'stage/jobs'/(first+'.json');job=p.read_json(jobpath);job['run_id']='f'*32;jobpath.write_text(json.dumps(job))
    elif mutation=='source':
        jobpath=root/'stage/jobs'/(second+'.json');job=p.read_json(jobpath);job['snapshot_sha256']='f'*64;jobpath.write_text(json.dumps(job))
    elif mutation=='extra-owner':
        extra=root/'stage/runs/extra';extra.mkdir();(extra/'owner.json').write_text(json.dumps({'run_id':'f'*32}))
    elif mutation=='input':Path(reg['contract']).write_text('altered')
    else:
        receipt=p.read_json(root/'execution.json')
        if mutation=='clock':receipt['readout_deadline_monotonic']=time.monotonic()+6600
        else:receipt['cleanup'][0]['status']='terminated-owned-worker'
        (root/'execution.json').write_text(json.dumps(receipt))
    assert s.audit(path)==1
    close=p.read_json(root/'scientific-close.json')
    assert close['pilot_complete'] is False and close['qualification_claims']==[]
    if mutation=='input':
        assert len(close['owners'])==30 and close['unattempted']==[]


def test_restored_terminal_binds_previous_xy_from_the_source():
    snapshot={'application':{'episode_step':727},'environment':{'values':{'_stall_steps':49,'_prev_xy':[1.,0.]}}}
    outcome={'reason':'stalled','episode':0,'steps':728}
    report={'goal':False,'total_ticks':728,'final_phase':'terminated','outcome':outcome,
        'final_memory':{'supervisor':{'continuation_start_tick':727}}}
    data={'events':[{'kind':'episode_finished','outcome':outcome}],
        'rows':[{'tick':727,'pose':[0.,0.,0.],'next_pose':[0.,0.,0.],'action':[.1,0.]}]}
    with pytest.raises(ValueError):p.audit_travel_task_failure(data,report,source_snapshot=snapshot)


@pytest.mark.parametrize('key',['python_sha256','host','platform'])
def test_same_versions_cannot_admit_a_different_prerequisite_runtime(tmp_path,monkeypatch,key):
    s,reg,path=registration_fixture(tmp_path,monkeypatch)
    runtime=copy.deepcopy(reg['runtime']);runtime[key]='changed'
    monkeypatch.setattr(d,'runtime_v2_identity',lambda:runtime)
    with pytest.raises(ValueError):s.build_registration(reg['repo'],reg['prerequisite']['registration_path'],stamp='changed')
    reg['runtime']=runtime;path.write_text(json.dumps(reg))
    with pytest.raises(ValueError):s.recheck_inputs(reg)


@pytest.mark.parametrize('name',['memory_prerequisites_v2.py','memory_restore_offline_readout.py'])
def test_current_prerequisite_helpers_are_pinned_and_cannot_be_derived(tmp_path,monkeypatch,name):
    s,reg,path=registration_fixture(tmp_path,monkeypatch)
    target=Path(reg['repo'])/'scripts'/name;target.write_text('changed admission helper')
    with pytest.raises(ValueError):s.recheck_inputs(reg)
    with pytest.raises(ValueError):s.build_registration(reg['repo'],reg['prerequisite']['registration_path'],stamp='changed')


def test_restored_stall_action_threshold_uses_the_native_float32_boundary():
    import numpy as np
    outcome={'reason':'time_limit','episode':0,'steps':777}
    report={'outcome':outcome,'total_ticks':777,'final_phase':'truncated'}
    rows=[{'tick':tick,'pose':[0.,0.,0.],'next_pose':[0.,0.,0.],
        'action':np.array([.05,0.],np.float32)} for tick in range(727,777)]
    data={'rows':rows,'events':[{'kind':'episode_finished','outcome':outcome}]}
    assert p.audit_native_prefix_terminal(data,report,start_tick=727,expected_cap=777)=='time_limit'
