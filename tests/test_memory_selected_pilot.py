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
